"""
Scraper runner with parallel execution.

Coordinates scraping across multiple company adapters with timeout protection
and failure isolation.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import List, Optional
import logging
from bs4 import BeautifulSoup

from scraper.adapters import get_adapter

logger = logging.getLogger(__name__)


@dataclass
class CompanyResult:
    """Result of scraping a single company."""
    company_id: int
    company_name: str
    status: str  # 'OK' or 'ERROR'
    error_message: Optional[str]
    new_count: int
    updated_count: int
    touched_job_ids: List[int]


@dataclass
class RefreshResult:
    """Result of refreshing all companies."""
    company_results: List[CompanyResult]
    touched_job_ids: List[int]


class ScraperRunner:
    """
    Coordinates scraping across multiple companies with parallel execution.
    
    Features:
    - Parallel execution with ThreadPoolExecutor
    - Timeout protection per company (30 seconds)
    - Failure isolation (one company failure doesn't affect others)
    - Automatic status tracking in database
    """
    
    def __init__(self, config, db):
        """
        Initialize scraper runner.
        
        Args:
            config: Config object with companies list
            db: Database instance
        """
        self.config = config
        self.db = db
        self.timeout = 30  # seconds per adapter
        self.max_workers = 4  # parallel workers
    
    def refresh_all(self) -> RefreshResult:
        """
        Run all company adapters in parallel with timeout.
        Continue on individual failures.
        
        Returns:
            RefreshResult with per-company results and touched job IDs
        """
        results = []
        touched_job_ids = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all company refresh tasks
            future_map = {
                executor.submit(self._refresh_company, company): company
                for company in self.config.companies
            }
            
            # Collect results as they complete
            for future, company in future_map.items():
                try:
                    result = future.result(timeout=self.timeout)
                    results.append(result)
                    touched_job_ids.extend(result.touched_job_ids)
                    logger.info(
                        f"[{result.company_name}] status={result.status} "
                        f"new={result.new_count} updated={result.updated_count}"
                    )
                except FuturesTimeoutError:
                    # Handle timeout
                    company_id = self.db.get_company_id_by_name(company.name)
                    if company_id:
                        self.db.update_company_status(company_id, "ERROR", "Timeout")
                    error_result = CompanyResult(
                        company_id=company_id,
                        company_name=company.name,
                        status="ERROR",
                        error_message="Timeout",
                        new_count=0,
                        updated_count=0,
                        touched_job_ids=[]
                    )
                    results.append(error_result)
                    logger.error(f"[{company.name}] Timeout after {self.timeout}s")
                except Exception as e:
                    # Handle other exceptions
                    company_id = self.db.get_company_id_by_name(company.name)
                    if company_id:
                        self.db.update_company_status(company_id, "ERROR", str(e))
                    error_result = CompanyResult(
                        company_id=company_id,
                        company_name=company.name,
                        status="ERROR",
                        error_message=str(e),
                        new_count=0,
                        updated_count=0,
                        touched_job_ids=[]
                    )
                    results.append(error_result)
                    logger.error(f"[{company.name}] Error: {str(e)}")
        
        return RefreshResult(results, touched_job_ids)
    
    def _refresh_company(self, company_config) -> CompanyResult:
        """
        Fetch jobs for one company.
        Update DB with new/updated postings in transaction.
        Mark missing postings as inactive.
        Strip HTML and preserve paragraph breaks.
        
        Args:
            company_config: CompanyConfig object
            
        Returns:
            CompanyResult with status and counts
        """
        # Upsert company to get DB ID
        company_id = self.db.upsert_company(company_config)
        
        try:
            # Fetch jobs using adapter
            adapter = get_adapter(company_config)
            raw_jobs = adapter.fetch_jobs()
            
            # Normalize descriptions
            for job in raw_jobs:
                job.description = self._normalize_text(job.description)
            
            # Update DB in transaction
            touched_job_ids = []
            new_count = 0
            updated_count = 0
            seen_ids = []
            
            with self.db.transaction():
                for raw_job in raw_jobs:
                    job_id, is_new = self.db.upsert_job_posting(company_id, raw_job)
                    touched_job_ids.append(job_id)
                    seen_ids.append(raw_job.external_id)
                    if is_new:
                        new_count += 1
                    else:
                        updated_count += 1
                
                # Mark missing jobs inactive (chunked for SQLite limit)
                self.db.mark_missing_jobs_inactive(company_id, seen_ids)
            
            # Update company status
            self.db.update_company_status(company_id, "OK", None)
            
            return CompanyResult(
                company_id=company_id,
                company_name=company_config.name,
                status="OK",
                error_message=None,
                new_count=new_count,
                updated_count=updated_count,
                touched_job_ids=touched_job_ids
            )
        
        except Exception as e:
            # Update company status on error
            self.db.update_company_status(company_id, "ERROR", str(e))
            raise
    
    def _normalize_text(self, html: str) -> str:
        """
        Strip HTML tags and preserve paragraph breaks.
        Maintains readability in UI while enabling keyword search.
        
        Args:
            html: HTML text (may contain tags)
            
        Returns:
            Plain text with preserved paragraph breaks
        """
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text("\n")
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join([l for l in lines if l])
