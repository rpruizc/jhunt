-- Job Role Matcher Database Schema
-- SQLite database for storing companies, job postings, and evaluations

-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    careers_url TEXT NOT NULL,
    adapter TEXT NOT NULL,
    last_successful_fetch TIMESTAMP,
    adapter_status TEXT CHECK(adapter_status IN ('OK', 'ERROR')),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job postings table
CREATE TABLE IF NOT EXISTS job_postings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT NOT NULL,
    company_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    location TEXT NOT NULL,
    department TEXT,
    seniority_level TEXT,
    description TEXT NOT NULL,
    url TEXT NOT NULL,
    date_found TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    partial_description BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    user_review_status TEXT DEFAULT 'NEW' CHECK(user_review_status IN ('NEW', 'READ', 'IGNORED')),
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, external_id)
);

-- Evaluations table
CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    fit_score INTEGER NOT NULL,
    seniority_score INTEGER NOT NULL,
    pnl_score INTEGER NOT NULL,
    transformation_score INTEGER NOT NULL,
    industry_score INTEGER NOT NULL,
    geo_score INTEGER NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('APPLY', 'WATCH', 'SKIP')),
    summary TEXT NOT NULL,
    concerns TEXT NOT NULL,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES job_postings(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_job_postings_active ON job_postings(active);
CREATE INDEX IF NOT EXISTS idx_job_postings_company ON job_postings(company_id);
CREATE INDEX IF NOT EXISTS idx_job_postings_external_id ON job_postings(company_id, external_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_job ON evaluations(job_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_score ON evaluations(fit_score DESC);
CREATE INDEX IF NOT EXISTS idx_evaluations_created ON evaluations(job_id, created_at DESC);
