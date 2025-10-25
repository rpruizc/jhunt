"""
Database access layer for Job Role Matcher.
Provides methods for interacting with SQLite database.
"""

import sqlite3
import json
import os
from contextlib import contextmanager
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime


class Database:
    """Database access layer for job postings and evaluations."""
    
    def __init__(self, db_path: str = "data/jobs.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self):
        """
        Create tables if they don't exist.
        Use PRAGMA user_version for schema migration tracking.
        """
        current_version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        
        if current_version == 0:
            # Read and execute schema file
            schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
            with open(schema_path, 'r') as f:
                self.conn.executescript(f.read())
            self.conn.execute("PRAGMA user_version = 1")
            self.conn.commit()
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        try:
            self.conn.execute("BEGIN")
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
    
    # Company operations
    
    def upsert_company(self, company_config) -> int:
        """
        Insert or update company record.
        
        Args:
            company_config: CompanyConfig object with name, careers_url, adapter
            
        Returns:
            company_id from database
        """
        existing = self.conn.execute(
            "SELECT id FROM companies WHERE name = ?",
            (company_config.name,)
        ).fetchone()
        
        if existing:
            self.conn.execute("""
                UPDATE companies 
                SET careers_url = ?, adapter = ?
                WHERE id = ?
            """, (company_config.careers_url, company_config.adapter, existing['id']))
            self.conn.commit()
            return existing['id']
        else:
            cursor = self.conn.execute("""
                INSERT INTO companies (name, careers_url, adapter)
                VALUES (?, ?, ?)
            """, (company_config.name, company_config.careers_url, company_config.adapter))
            self.conn.commit()
            return cursor.lastrowid
    
    def get_company_id_by_name(self, name: str) -> Optional[int]:
        """
        Get company ID by name.
        
        Args:
            name: Company name
            
        Returns:
            Company ID or None if not found
        """
        row = self.conn.execute(
            "SELECT id FROM companies WHERE name = ?",
            (name,)
        ).fetchone()
        return row['id'] if row else None
    
    def update_company_status(self, company_id: int, status: str, error: Optional[str]):
        """
        Update adapter status after scrape attempt.
        
        Args:
            company_id: Company ID
            status: 'OK' or 'ERROR'
            error: Error message if status is ERROR, None otherwise
        """
        self.conn.execute("""
            UPDATE companies 
            SET adapter_status = ?, 
                error_message = ?, 
                last_successful_fetch = CASE WHEN ? = 'OK' THEN CURRENT_TIMESTAMP ELSE last_successful_fetch END
            WHERE id = ?
        """, (status, error, status, company_id))
        self.conn.commit()
    
    def get_all_companies(self) -> List[Dict[str, Any]]:
        """
        Get all companies with health status.
        
        Returns:
            List of company dictionaries
        """
        rows = self.conn.execute("""
            SELECT id, name, adapter_status, error_message, last_successful_fetch
            FROM companies
            ORDER BY name
        """)
        return [dict(row) for row in rows]

    # Job posting operations
    
    def upsert_job_posting(self, company_id: int, raw_job) -> Tuple[int, bool]:
        """
        Insert or update job posting.
        Preserves user_review_status on update.
        
        Args:
            company_id: Company ID
            raw_job: RawJobPosting object with external_id, title, location, etc.
            
        Returns:
            Tuple of (job_id, is_new)
        """
        existing = self.conn.execute(
            "SELECT id, user_review_status FROM job_postings WHERE company_id = ? AND external_id = ?",
            (company_id, raw_job.external_id)
        ).fetchone()
        
        if existing:
            # Update existing, preserve review status
            self.conn.execute("""
                UPDATE job_postings 
                SET title = ?, location = ?, department = ?, description = ?,
                    url = ?, last_seen_at = CURRENT_TIMESTAMP, active = TRUE,
                    partial_description = ?
                WHERE id = ?
            """, (raw_job.title, raw_job.location, raw_job.department,
                  raw_job.description, raw_job.url, raw_job.partial_description,
                  existing['id']))
            self.conn.commit()
            return (existing['id'], False)
        else:
            # Insert new
            cursor = self.conn.execute("""
                INSERT INTO job_postings 
                (external_id, company_id, title, location, department, description, url, partial_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (raw_job.external_id, company_id, raw_job.title, raw_job.location,
                  raw_job.department, raw_job.description, raw_job.url, raw_job.partial_description))
            self.conn.commit()
            return (cursor.lastrowid, True)
    
    def mark_missing_jobs_inactive(self, company_id: int, seen_external_ids: List[str]):
        """
        Mark jobs not in seen list as inactive.
        Chunked to avoid SQLite's 999 parameter limit.
        
        Args:
            company_id: Company ID
            seen_external_ids: List of external IDs that were seen in latest scrape
        """
        if not seen_external_ids:
            # Mark all jobs inactive if no jobs seen
            self.conn.execute(
                "UPDATE job_postings SET active = FALSE WHERE company_id = ? AND active = TRUE",
                (company_id,)
            )
            self.conn.commit()
            return
        
        # Process in chunks of 900 to stay under SQLite limit
        chunk_size = 900
        for i in range(0, len(seen_external_ids), chunk_size):
            chunk = seen_external_ids[i:i + chunk_size]
            placeholders = ','.join('?' * len(chunk))
            self.conn.execute(f"""
                UPDATE job_postings 
                SET active = FALSE 
                WHERE company_id = ? AND external_id NOT IN ({placeholders}) AND active = TRUE
            """, [company_id] + chunk)
        self.conn.commit()
    
    def get_jobs_by_ids(self, job_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get jobs by ID list.
        Used to score touched jobs after refresh.
        
        Args:
            job_ids: List of job IDs
            
        Returns:
            List of job dictionaries with company_name
        """
        if not job_ids:
            return []
        
        placeholders = ','.join('?' * len(job_ids))
        rows = self.conn.execute(f"""
            SELECT j.*, c.name as company_name
            FROM job_postings j
            JOIN companies c ON j.company_id = c.id
            WHERE j.id IN ({placeholders})
        """, job_ids)
        return [dict(row) for row in rows]

    # Evaluation operations
    
    def insert_evaluation(self, evaluation):
        """
        Insert new evaluation record.
        Prune old evaluations to keep last 3 per job.
        
        Args:
            evaluation: Evaluation object with job_id, scores, action, summary, concerns
        """
        # Serialize concerns to JSON
        concerns_json = json.dumps(evaluation.concerns) if hasattr(evaluation, 'concerns') else '[]'
        
        self.conn.execute("""
            INSERT INTO evaluations
            (job_id, fit_score, seniority_score, pnl_score, transformation_score,
             industry_score, geo_score, action, summary, concerns)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (evaluation.job_id, evaluation.fit_score, evaluation.seniority_score,
              evaluation.pnl_score, evaluation.transformation_score,
              evaluation.industry_score, evaluation.geo_score,
              evaluation.action, evaluation.summary, concerns_json))
        
        # Keep only last 3 evaluations per job
        self.conn.execute("""
            DELETE FROM evaluations
            WHERE job_id = ? AND id NOT IN (
                SELECT id FROM evaluations
                WHERE job_id = ?
                ORDER BY created_at DESC
                LIMIT 3
            )
        """, (evaluation.job_id, evaluation.job_id))
        
        self.conn.commit()
    
    def get_active_jobs_with_evaluations(
        self, 
        min_action: Optional[str] = None, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get active jobs with latest evaluation only.
        Sorted by score descending, then date_found descending for ties.
        
        Args:
            min_action: Filter by action ('APPLY' or 'WATCH')
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of job dictionaries with evaluation data
        """
        query = """
            SELECT 
                j.id, j.title, c.name as company_name, j.location, j.url,
                j.user_review_status,
                e.fit_score, e.action, e.summary
            FROM job_postings j
            JOIN companies c ON j.company_id = c.id
            LEFT JOIN (
                SELECT e1.*
                FROM evaluations e1
                JOIN (
                    SELECT job_id, MAX(created_at) AS max_created
                    FROM evaluations
                    GROUP BY job_id
                ) latest
                ON e1.job_id = latest.job_id
                AND e1.created_at = latest.max_created
            ) e ON j.id = e.job_id
            WHERE j.active = TRUE
        """
        
        params = []
        if min_action == "APPLY":
            query += " AND e.action = 'APPLY'"
        elif min_action == "WATCH":
            query += " AND e.action IN ('APPLY', 'WATCH')"
        
        query += " ORDER BY e.fit_score DESC, j.date_found DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = self.conn.execute(query, params)
        return [dict(row) for row in rows]
    
    def get_job_by_id(self, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Get full job details.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job dictionary with company_name or None if not found
        """
        row = self.conn.execute("""
            SELECT j.*, c.name as company_name
            FROM job_postings j
            JOIN companies c ON j.company_id = c.id
            WHERE j.id = ?
        """, (job_id,)).fetchone()
        
        return dict(row) if row else None
    
    def get_latest_evaluation(self, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Get most recent evaluation for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Evaluation dictionary with concerns parsed from JSON or None if not found
        """
        row = self.conn.execute("""
            SELECT * FROM evaluations
            WHERE job_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (job_id,)).fetchone()
        
        if row:
            eval_dict = dict(row)
            # Parse concerns from JSON
            eval_dict['concerns'] = json.loads(eval_dict['concerns'])
            return eval_dict
        return None
    
    def update_review_status(self, job_id: int, status: str):
        """
        Update user review status.
        
        Args:
            job_id: Job ID
            status: New status ('NEW', 'READ', or 'IGNORED')
        """
        self.conn.execute(
            "UPDATE job_postings SET user_review_status = ? WHERE id = ?",
            (status, job_id)
        )
        self.conn.commit()
    
    def get_job_stats(self) -> Dict[str, int]:
        """
        Get counts of jobs by action label.
        
        Returns:
            Dictionary with counts for apply, watch, skip, and total
        """
        rows = self.conn.execute("""
            SELECT e.action, COUNT(*) as count
            FROM job_postings j
            JOIN (
                SELECT e1.*
                FROM evaluations e1
                JOIN (
                    SELECT job_id, MAX(created_at) AS max_created
                    FROM evaluations
                    GROUP BY job_id
                ) latest
                ON e1.job_id = latest.job_id
                AND e1.created_at = latest.max_created
            ) e ON j.id = e.job_id
            WHERE j.active = TRUE
            GROUP BY e.action
        """)
        stats = {row['action']: row['count'] for row in rows}
        return {
            "apply": stats.get("APPLY", 0),
            "watch": stats.get("WATCH", 0),
            "skip": stats.get("SKIP", 0),
            "total": sum(stats.values())
        }
    
    def count_active_jobs(self, min_action: Optional[str] = None) -> int:
        """
        Count active jobs with optional action filter.
        
        Args:
            min_action: Filter by action ('APPLY' or 'WATCH')
            
        Returns:
            Count of matching jobs
        """
        query = """
            SELECT COUNT(*) as count
            FROM job_postings j
            LEFT JOIN (
                SELECT e1.*
                FROM evaluations e1
                JOIN (
                    SELECT job_id, MAX(created_at) AS max_created
                    FROM evaluations
                    GROUP BY job_id
                ) latest
                ON e1.job_id = latest.job_id
                AND e1.created_at = latest.max_created
            ) e ON j.id = e.job_id
            WHERE j.active = TRUE
        """
        
        params = []
        if min_action == "APPLY":
            query += " AND e.action = 'APPLY'"
        elif min_action == "WATCH":
            query += " AND e.action IN ('APPLY', 'WATCH')"
        
        row = self.conn.execute(query, params).fetchone()
        return row['count'] if row else 0
