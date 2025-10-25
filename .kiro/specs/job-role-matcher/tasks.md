# Implementation Plan

This plan breaks down the job-role-matcher implementation into discrete, incremental coding tasks. Each task builds on previous work and references specific requirements from the requirements document.

## Phase 1: Core Infrastructure

- [ ] 1. Set up project structure and configuration
  - Create backend/ and frontend/ directories with proper Python/Node project structure
  - Create data/ directory for SQLite database
  - Set up .gitignore for data/, logs, and environment files
  - Create config.example.yaml with sample company entries and scoring weights
  - _Requirements: 1.11, 3.8_

- [x] 1.1 Implement configuration module
  - Create config.py with Pydantic models for Config, CompanyConfig, GeographyConfig, ScoringWeights
  - Implement load_config() function with YAML parsing and validation
  - Add error handling for missing or invalid config files
  - _Requirements: 1.11, 3.8_

- [x] 1.2 Create database schema
  - Write schema.sql with companies, job_postings, and evaluations tables
  - Include all indexes for performance (active flag, fit_score, company_id, job_id)
  - Add PRAGMA user_version for migration tracking
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 1.3 Implement database access layer
  - Create database.py with Database class
  - Implement _init_schema() with version checking
  - Implement transaction() context manager
  - Implement upsert_company() and get_company_id_by_name()
  - Implement update_company_status() and get_all_companies()
  - _Requirements: 6.1, 6.4, 6.5_

- [x] 1.4 Implement job posting database operations
  - Implement upsert_job_posting() with deduplication on company_id + external_id
  - Ensure user_review_status is preserved on updates
  - Implement mark_missing_jobs_inactive() with chunking for SQLite limit
  - Implement get_jobs_by_ids() for scoring touched jobs
  - _Requirements: 6.2, 6.4, 6.5, 6.7_

- [x] 1.5 Implement evaluation database operations
  - Implement insert_evaluation() with pruning to keep last 3 per job
  - Implement get_active_jobs_with_evaluations() with latest-evaluation-only join
  - Implement get_latest_evaluation() for detail view
  - Implement update_review_status()
  - Implement get_job_stats() for dashboard summary
  - _Requirements: 6.3, 6.6, 6.7_


## Phase 2: Scraper Layer

- [ ] 2. Implement base adapter interface and registry
  - Create scraper/base.py with BaseAdapter abstract class
  - Define RawJobPosting dataclass with external_id, title, location, description, url, partial_description
  - Create scraper/adapters/__init__.py with ADAPTERS registry
  - Implement get_adapter() function to look up adapters by name
  - Document adapter contract (must fill external_id, url, set partial_description flag)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.10_

- [ ] 2.1 Implement scraper runner with parallel execution
  - Create scraper/runner.py with ScraperRunner class
  - Implement refresh_all() with ThreadPoolExecutor (max_workers=4)
  - Use future.result(timeout=30) for timeout protection
  - Handle TimeoutError and general exceptions per company
  - Return RefreshResult with company results and touched_job_ids list
  - Add logging for each company result
  - _Requirements: 1.6, 1.7, 1.8, 1.9_

- [ ] 2.2 Implement _refresh_company() method
  - Call db.upsert_company() to get company_id from DB
  - Fetch jobs using adapter
  - Normalize descriptions with _normalize_text() (preserve paragraph breaks)
  - Wrap DB operations in transaction
  - Track new_count, updated_count, and touched_job_ids
  - Call mark_missing_jobs_inactive() with seen external_ids
  - Update company status (OK or ERROR)
  - _Requirements: 1.4, 1.8, 1.9, 6.4, 6.5_

- [ ] 2.3 Create sample adapters for 3 companies
  - Implement SiemensAdapter in scraper/adapters/siemens.py
  - Implement BoschAdapter in scraper/adapters/bosch.py
  - Implement ABBAdapter in scraper/adapters/abb.py
  - Each adapter should fetch from careers API or scrape HTML
  - Set partial_description=True if full text unavailable
  - Use requests with timeout=20 and proper User-Agent
  - Return empty list on failure with error logging
  - _Requirements: 1.1, 1.2, 1.3, 1.10_


## Phase 3: Scoring Engine

- [ ] 3. Implement signal extraction module
  - Create scorer/signals.py with dataclasses for SenioritySignal, PnLSignal, TransformationSignal, IndustrySignal, GeoSignal
  - Create scorer/extractor.py with SignalExtractor class
  - Implement extract_seniority() parsing title for VP/Senior Director/Director keywords
  - Implement _extract_evidence() helper to capture text snippets around keywords (80 char window)
  - _Requirements: 3.1, 4.4_

- [ ] 3.1 Implement P&L and transformation signal extraction
  - Implement extract_pnl_signals() searching for P&L, profitability, EBITDA, budget control keywords
  - Distinguish strong keywords (20 pts) from medium keywords (15 pts)
  - Implement extract_transformation_signals() searching for digital transformation, ERP modernization, post-acquisition integration keywords
  - Capture evidence snippets for each signal
  - _Requirements: 3.2, 3.3_

- [ ] 3.2 Implement industry and geography signal extraction
  - Implement extract_industry_signals() searching for IoT, batteries, manufacturing automation, regulated environments keywords
  - Distinguish strong industry match (20 pts) from adjacent software (10 pts)
  - Implement extract_geo_signals() checking description and location for preferred/banned geographies
  - Set geo.score=10 if preferred geography found, geo.is_banned=True if banned geography found
  - _Requirements: 3.4, 3.5, 3.6_

- [ ] 3.3 Implement scoring engine
  - Create scorer/engine.py with ScoringEngine class
  - Implement score_job() method that extracts all signals
  - Calculate total score using config weights (normalize by max points per dimension)
  - Apply geography penalty if is_banned=True
  - Clamp total score to 0-100 range
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [ ] 3.4 Implement action determination and concern generation
  - Implement _determine_action() assigning APPLY (>=75), WATCH (60-74), SKIP (<60)
  - Implement _generate_concerns() creating concern objects with type and evidence
  - Check for: below target seniority, no P&L, no transformation mandate, no industry match, banned geography, incomplete description
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 3.5 Implement summary text generation
  - Implement _generate_summary() using fixed template structure
  - Identify top 2 strengths from dimension scores
  - Identify top 1 concern (gap)
  - Format as: "Role: [title] at [company] in [location]. Fit: [strengths]. Gap: [concern]. Action: [action]. Score: [score]."
  - _Requirements: 4.6_


## Phase 4: API Layer

- [ ] 4. Set up FastAPI application
  - Create main.py with FastAPI app initialization
  - Set up rotating file logger (10MB max, 5 backups)
  - Load config once at startup
  - Initialize Database instance
  - Add /health endpoint returning status and timestamp
  - _Requirements: 7.8_

- [ ] 4.1 Implement authentication middleware
  - Create api/auth.py with verify_token() dependency
  - Parse "Bearer <token>" from Authorization header
  - Compare token against config.admin_token
  - Raise 401 HTTPException if invalid
  - _Requirements: 7.4, 7.5_

- [ ] 4.2 Implement job listing endpoint
  - Create api/routes.py with GET /jobs endpoint
  - Accept min_action query parameter (APPLY, WATCH, or none)
  - Accept limit and offset for pagination (default 50)
  - Call db.get_active_jobs_with_evaluations()
  - Return JSON with jobs array, total count, limit, offset
  - Sort by fit_score DESC, date_found DESC
  - _Requirements: 7.1, 7.6, 5.2_

- [ ] 4.3 Implement job detail endpoint
  - Add GET /jobs/{id} endpoint with verify_token dependency
  - Call db.get_job_by_id() and db.get_latest_evaluation()
  - Return 404 if job not found
  - Return JSON with job and evaluation objects
  - _Requirements: 7.2, 7.4, 7.5_

- [ ] 4.4 Implement refresh endpoint
  - Add POST /refresh endpoint with verify_token dependency, status_code=202
  - Track start time for duration calculation
  - Create ScraperRunner and call refresh_all()
  - Get touched jobs by IDs and score them with ScoringEngine
  - Insert evaluations for all touched jobs
  - Return JSON with timestamp, duration_sec, per-company results, totals
  - _Requirements: 1.6, 7.3, 7.4, 7.9_

- [ ] 4.5 Implement review status and utility endpoints
  - Add PATCH /jobs/{id}/review endpoint (status_code=204)
  - Validate status is NEW, READ, or IGNORED
  - Call db.update_review_status()
  - Add GET /companies endpoint returning all companies with health status
  - Add GET /stats endpoint returning job counts by action label
  - _Requirements: 6.7, 7.8_


## Phase 5: Frontend Dashboard

- [ ] 5. Set up Next.js project structure
  - Initialize Next.js 14 project with TypeScript and Tailwind CSS
  - Create app/layout.tsx with basic HTML structure
  - Create app/globals.css with Tailwind imports
  - Configure tailwind.config.js with color scheme
  - Create .env.example with API_URL and ADMIN_TOKEN placeholders
  - _Requirements: 5.1_

- [ ] 5.1 Create API client module
  - Create lib/api.ts with API client functions
  - Implement fetchJobs(minAction?) calling GET /jobs
  - Implement fetchJobDetail(id) proxied through Next.js API route
  - Implement triggerRefresh() proxied through Next.js API route
  - Implement updateReviewStatus(id, status) calling PATCH /jobs/{id}/review
  - _Requirements: 7.1, 7.2, 7.3_

- [ ] 5.2 Create Next.js API routes for token injection
  - Create app/api/jobs/[id]/route.ts proxying to backend with admin token
  - Create app/api/refresh/route.ts proxying to backend with admin token
  - Read ADMIN_TOKEN from server-side environment variable
  - Never expose token to client
  - _Requirements: 7.4, 7.5_

- [ ] 5.3 Implement dashboard page
  - Create app/page.tsx with Dashboard component
  - Import useRouter from next/navigation
  - Implement state for jobs list, hideSkip filter, loading
  - Fetch jobs on mount and when hideSkip changes
  - Render table with columns: Score, Title, Company, Location, Action
  - Show NEW badge for user_review_status="NEW"
  - Color-code action badges (green=APPLY, yellow=WATCH, gray=SKIP)
  - Make rows clickable to navigate to detail page
  - _Requirements: 5.1, 5.2, 5.3, 5.6_

- [ ] 5.4 Implement refresh button and controls
  - Add Refresh button that calls triggerRefresh()
  - Show loading state during refresh
  - Log per-company results to console (or show toast)
  - Add "Hide SKIP" checkbox toggle
  - Refetch jobs after successful refresh
  - _Requirements: 5.1, 5.3_

- [ ] 5.5 Create job detail page
  - Create app/jobs/[id]/page.tsx with JobDetail component
  - Import useRouter and Link from Next.js
  - Fetch job detail on mount
  - Display job title, company, location, and fit score in header
  - Show action badge with color coding
  - _Requirements: 5.4_

- [ ] 5.6 Implement fit analysis section
  - Display summary text from evaluation
  - Create ScoreCard component showing individual dimension scores
  - Render 5 score cards: Seniority, P&L, Transform, Industry, Geo
  - Show score/max with percentage bar
  - Guard against divide-by-zero in percentage calculation
  - _Requirements: 5.4_

- [ ] 5.7 Implement concerns and description sections
  - Render concerns list with type and evidence for each concern
  - Show warning banner if partial_description=true
  - Display full job description with preserved line breaks (whitespace-pre-wrap)
  - Add "Open Original Posting" link opening in new tab
  - Add "Mark as Read" and "Ignore" buttons calling updateReviewStatus()
  - Navigate back to dashboard after status update
  - _Requirements: 5.4, 4.5_


## Phase 6: Adapter Expansion

- [ ] 6. Implement adapters for remaining target companies
  - Create adapters for Schneider Electric, Honeywell, Rockwell Automation
  - Create adapters for Flex, Celestica, Continental
  - Create adapters for Tesla, NXP, GE Vernova, Eaton
  - Follow template adapter pattern for consistency
  - Test each adapter against live careers page
  - Handle rate limiting with retries and backoff
  - Document any company-specific quirks or limitations
  - _Requirements: 1.1, 1.2, 1.3_


## Phase 7: Testing and Validation

- [ ]* 7. Write unit tests for scoring engine
  - Create tests/test_scorer.py
  - Write golden test for perfect-fit VP role (must score APPLY with fit_score >= 75)
  - Test signal extraction with sample job descriptions
  - Test score calculation for each dimension
  - Test action label assignment at boundary thresholds (75, 60)
  - Test concern generation with evidence
  - Test summary text formatting
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 4.6_

- [ ]* 7.1 Write unit tests for database layer
  - Create tests/test_database.py
  - Test upsert logic for companies and jobs (new vs existing)
  - Test deduplication on company_id + external_id
  - Test user_review_status preservation on update
  - Test mark_missing_jobs_inactive with chunking
  - Test latest-evaluation-only join in get_active_jobs_with_evaluations
  - Test query filters (min_action, pagination)
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.7_

- [ ]* 7.2 Write integration tests for API endpoints
  - Create tests/test_api.py
  - Test GET /jobs with filters and pagination
  - Test GET /jobs/{id} with valid and invalid IDs
  - Test POST /refresh trigger
  - Test authentication on protected endpoints (401 without token)
  - Test PATCH /jobs/{id}/review with valid and invalid statuses
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.8_

- [ ]* 7.3 Create test fixtures and mock adapters
  - Create tests/fixtures/sample_jobs.py with high/mid/low scoring job descriptions
  - Create mock adapters returning predictable data for CI/CD
  - Test scraper runner with mock adapters
  - Verify parallel execution and timeout handling
  - Verify adapter failure isolation
  - _Requirements: 1.8, 1.9_


## Phase 8: Deployment and Documentation

- [ ] 8. Create deployment configuration
  - Write Dockerfile for backend with Python 3.10+ base image
  - Write Dockerfile for frontend with Node.js base image
  - Create docker-compose.yml with backend, frontend, and cron services
  - Configure volume mounts for data/ directory and config.yaml
  - Add restart: unless-stopped and healthcheck to services
  - Set up environment variables for ADMIN_TOKEN
  - _Requirements: 7.8_

- [ ] 8.1 Write project documentation
  - Create backend/README.md with setup instructions, API documentation, adapter contract
  - Create frontend/README.md with setup instructions and component overview
  - Create root README.md with project overview, architecture diagram, deployment options
  - Document config.yaml structure and all available options
  - Document security considerations (admin token, /jobs endpoint exposure)
  - Document backup strategy for SQLite database
  - _Requirements: 1.11, 3.8, 7.4, 7.5_

- [ ] 8.2 Set up local development environment
  - Create requirements.txt with all Python dependencies
  - Create package.json with all Node dependencies
  - Write setup scripts for initializing database and config
  - Test local development workflow (backend + frontend running simultaneously)
  - Document common development tasks (running tests, adding adapters, tuning scores)
  - _Requirements: 1.11_

- [ ] 8.3 Configure logging and monitoring
  - Verify rotating file handler is working (job_matcher.log)
  - Add per-company scrape summary to logs
  - Test health check endpoint
  - Document how to monitor adapter failures
  - Document how to check last_successful_fetch timestamps
  - _Requirements: 1.7, 1.9_

