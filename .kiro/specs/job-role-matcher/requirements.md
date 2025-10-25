# Requirements Document

## Introduction

The Job Role Matcher is a system that automatically discovers, filters, scores, and ranks senior-level job postings from target industrial and technology companies. The system evaluates each role against a structured career profile to identify the best-fit opportunities for leadership positions in digital transformation, advanced manufacturing, industrial AI, and related domains.

## Glossary

- **Job Role Matcher**: The complete system that scrapes, filters, scores, and presents job opportunities
- **Target Company**: A company from the predefined list that the system monitors for job postings
- **Job Posting**: A single role advertisement from a company's careers page or API
- **External ID**: The company's unique requisition ID or job identifier used for deduplication
- **Evaluation**: A scored assessment of how well a job posting matches the target profile
- **Admin Token**: A static authentication token required for write operations and sensitive endpoints
- **Fit Score**: A numerical value (0-100) representing overall match quality
- **Seniority Signal**: Keywords or phrases indicating leadership level (Director, VP, GM, etc.)
- **Scope Signal**: Keywords indicating P&L ownership, transformation mandate, or strategic responsibility
- **Domain Signal**: Keywords indicating industry relevance (IoT, ERP, batteries, manufacturing, etc.)
- **Geography Signal**: Keywords indicating multi-country or LATAM leadership scope
- **Action Label**: Classification of a job posting (APPLY, WATCH, SKIP)
- **Company Adapter**: A module that fetches job postings from a specific company's careers system
- **Scraper Layer**: The component responsible for retrieving raw job posting data
- **Scoring Engine**: The component that calculates fit scores based on profile matching rules
- **Dashboard**: The web interface displaying ranked job opportunities

## Requirements

### Requirement 1

**User Story:** As a senior executive seeking leadership roles, I want the system to monitor specific target companies, so that I discover relevant opportunities without manually checking each company's careers page.

#### Acceptance Criteria

1. THE Job Role Matcher SHALL retrieve job postings from at least 10 target companies including Siemens, Bosch, ABB, Schneider Electric, Honeywell, Rockwell Automation, Flex, Celestica, Continental, Tesla, NXP, GE Vernova, and Eaton
2. WHEN a target company provides a public JSON API, THE Job Role Matcher SHALL fetch job data via the API endpoint
3. WHEN a target company does not provide a public API, THE Job Role Matcher SHALL scrape job data from the HTML careers page
4. THE Job Role Matcher SHALL store each retrieved job posting with external ID, title, location, department, description text, URL, discovery date, and partial description flag
5. THE Job Role Matcher SHALL support scheduled execution by exposing a refresh endpoint that can be triggered by an external scheduler
6. THE Job Role Matcher SHALL provide a POST endpoint at /refresh that triggers an immediate fetch and rescore cycle for all companies
7. THE Job Role Matcher SHALL record last successful fetch timestamp per company
8. THE Job Role Matcher SHALL execute each Company Adapter independently and SHALL continue processing remaining adapters if one fails
9. THE Job Role Matcher SHALL record adapter status (OK or ERROR) and error message for each company after each refresh cycle
10. WHEN the Scraper Layer cannot retrieve the full description body for a job posting, THE Job Role Matcher SHALL store the posting with partial_description flag set to true
11. THE Job Role Matcher SHALL load the list of target companies and their adapter identifiers from a local configuration file at startup

### Requirement 2

**User Story:** As a senior executive, I want the system to filter out irrelevant roles before scoring, so that I only see positions matching my target seniority and domain.

#### Acceptance Criteria

1. THE Job Role Matcher SHALL exclude job postings that do not contain at least one seniority keyword from the set: "Director", "Senior Director", "Sr Director", "VP", "Vice President", "Head", "GM", "Managing Director"
2. THE Job Role Matcher SHALL tag domain relevance based on domain keywords but SHALL NOT exclude postings solely due to lack of domain keywords
3. THE Job Role Matcher SHALL parse the job title to extract the seniority level
4. THE Job Role Matcher SHALL mark filtered-out postings as inactive rather than deleting them
5. THE Job Role Matcher SHALL process only active job postings for scoring and display

### Requirement 3

**User Story:** As a senior executive with specific career strengths, I want each role scored against my profile dimensions, so that I can prioritize opportunities that leverage my experience.

#### Acceptance Criteria

1. THE Scoring Engine SHALL calculate a seniority score (0-30 points) where VP-level roles receive 30 points, Senior Director roles receive 25 points, Director roles receive 20 points, and other roles receive 0 points
2. THE Scoring Engine SHALL calculate a pnl_score (0-20 points) where postings mentioning P&L, profitability, cost reduction, budget control, or EBITDA receive 20 points, postings mentioning commercial growth or revenue targets receive 15 points, and other postings receive 0 points
3. THE Scoring Engine SHALL calculate a transformation mandate score (0-20 points) where postings mentioning digital transformation, ERP modernization, post-acquisition integration, operational transformation, or technology roadmap receive 20 points, and other postings receive 0 points
4. THE Scoring Engine SHALL calculate an industry match score (0-20 points) where postings mentioning industrial IoT, factory automation, electrification, EV batteries, energy systems, or regulated environments receive 20 points, adjacent enterprise software roles receive 10 points, and other postings receive 0 points
5. THE Scoring Engine SHALL calculate a geographic scope score (0-10 points) where postings requiring multi-country leadership or LATAM coordination receive 10 points, and other postings receive 0 points
6. THE Scoring Engine SHALL apply a -10 point penalty when the posting location is explicitly limited to geographies outside the preferred_geographies list defined in configuration
7. THE Scoring Engine SHALL sum all dimension scores to produce a total fit score between 0 and 100
8. THE Job Role Matcher SHALL load target companies, seniority keywords, domain keywords, geography preferences, and scoring weights from a configuration file

### Requirement 4

**User Story:** As a senior executive evaluating opportunities, I want each role labeled with a recommended action, so that I know which roles to apply to immediately versus monitor.

#### Acceptance Criteria

1. WHEN a job posting has a fit score of 75 or higher, THE Job Role Matcher SHALL assign the action label "APPLY"
2. WHEN a job posting has a fit score between 60 and 74 inclusive, THE Job Role Matcher SHALL assign the action label "WATCH"
3. WHEN a job posting has a fit score below 60, THE Job Role Matcher SHALL assign the action label "SKIP"
4. THE Job Role Matcher SHALL generate a concerns array where each concern includes a short reason string sourced from the job description
5. WHEN a job posting has partial_description flag set to true, THE Evaluation SHALL include concern "Incomplete description"
6. THE Job Role Matcher SHALL generate summary text using the fixed structure: "Role: [title] at [company] in [location]. Fit: [top 2 aligned strengths]. Gap: [top 1 concern]. Action: [APPLY|WATCH|SKIP]. Score: [fit score]."

### Requirement 5

**User Story:** As a senior executive reviewing opportunities daily, I want a dashboard showing ranked roles with key information, so that I can quickly identify the best matches.

#### Acceptance Criteria

1. THE Dashboard SHALL display a table with columns for fit score, job title, company name, location, action label, and fit summary
2. THE Dashboard SHALL sort job postings by fit score in descending order by default
3. THE Dashboard SHALL allow filtering to hide postings with action label "SKIP"
4. WHEN a user clicks a job title, THE Dashboard SHALL navigate to a detail view showing the full job description, fit analysis, concerns, and a link to the original posting
5. THE Dashboard SHALL visually distinguish action labels using color-coded badges
6. THE Dashboard SHALL visually tag postings with user_review_status "NEW"

### Requirement 6

**User Story:** As a senior executive, I want the system to persist job postings and evaluations in a database, so that I can track opportunities over time and see historical data.

#### Acceptance Criteria

1. THE Job Role Matcher SHALL store company records with id, name, careers URL, adapter identifier, last successful fetch timestamp, adapter status, and error message
2. THE Job Role Matcher SHALL store job posting records with id, external ID, company reference, title, location, department, seniority level, description text, URL, discovery date, last seen date, partial description flag, active status, and user_review_status
3. THE Job Role Matcher SHALL store evaluation records with id, job posting reference, fit score, seniority score, pnl_score, transformation score, industry match score, geographic score, concerns array, summary text, and action label
4. WHEN a job posting with the same company ID and external ID is found in a subsequent scrape, THE Job Role Matcher SHALL update the existing record
5. WHEN a previously seen job posting is not found in a subsequent scrape, THE Job Role Matcher SHALL mark the posting as inactive
6. THE Job Role Matcher SHALL create new evaluation records when job postings are re-scored
7. THE Job Role Matcher SHALL include a user_review_status field on job posting records with allowed values "NEW", "READ", "IGNORED", default "NEW", and this field SHALL NOT be overwritten by scraping

**Note:** For initial deployment, the database MAY be implemented as a single local SQLite file. All schema requirements in this section apply regardless of backing store.

### Requirement 7

**User Story:** As a senior executive, I want the system to expose job data via API endpoints, so that the frontend can retrieve and display opportunities efficiently.

#### Acceptance Criteria

1. THE Job Role Matcher SHALL provide a GET endpoint at /jobs that returns all active job postings with their evaluations sorted by fit score descending
2. THE Job Role Matcher SHALL provide a GET endpoint at /jobs/{id} that returns a single job posting with full description text and evaluation details
3. THE Job Role Matcher SHALL provide a POST endpoint at /refresh that triggers immediate scraping and scoring for all companies
4. THE Job Role Matcher SHALL require an admin token for the /refresh endpoint and all detail endpoints
5. THE Job Role Matcher SHALL require an admin token for any endpoint that returns full job description text
6. THE Job Role Matcher SHALL return job data in JSON format
7. THE Job Role Matcher SHALL include pagination parameters for the /jobs endpoint when the result set exceeds 50 records
8. THE Job Role Matcher SHALL return appropriate HTTP status codes for success and error conditions
9. THE Job Role Matcher SHALL return, in the response body of /refresh, per-company results including company id, adapter status, error message if any, number of new jobs, and number of updated jobs
