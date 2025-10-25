# Job Role Matcher

Automated job discovery and evaluation system for senior leadership roles in industrial and technology companies.

## Overview

The Job Role Matcher automatically scrapes, filters, scores, and ranks job postings from target companies based on a structured career profile. It evaluates roles across multiple dimensions including seniority, P&L ownership, transformation mandate, industry match, and geographic scope.

## Features

- **Automated Scraping**: Monitors 13+ target companies for new job postings
- **Intelligent Scoring**: Evaluates roles across 5 dimensions with configurable weights
- **Action Recommendations**: Classifies jobs as APPLY, WATCH, or SKIP
- **Dashboard UI**: Clean interface for reviewing and triaging opportunities
- **Review Tracking**: Mark jobs as NEW, READ, or IGNORED
- **Detailed Analysis**: View fit breakdown, concerns, and full job descriptions

## Architecture

- **Backend**: FastAPI (Python) with SQLite database
- **Frontend**: Next.js 14 (TypeScript) with Tailwind CSS
- **Scraping**: Modular adapter system for each company
- **Scoring**: Keyword-based signal extraction with weighted scoring

## Quick Start

### Prerequisites

- Python 3.10+ with [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ with [pnpm](https://pnpm.io/) package manager

### Backend Setup

```bash
cd backend

# Create virtual environment with uv
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Create configuration
cp ../config.example.yaml ../config.yaml
# Edit config.yaml with your settings

# Run backend
uv run uvicorn main:app --reload
```

Backend will be available at http://localhost:8000

### Frontend Setup

```bash
cd frontend

# Install dependencies with pnpm
pnpm install

# Create environment file
cp .env.example .env.local
# Edit .env.local with your admin token

# Run frontend
pnpm dev
```

Frontend will be available at http://localhost:3000

## Configuration

Edit `config.yaml` to customize:

- **companies**: List of target companies with adapter names
- **seniority_keywords**: Keywords for detecting leadership levels
- **domain_keywords**: Keywords for industry matching
- **geography**: Preferred and banned locations
- **scoring_weights**: Weights for each scoring dimension (seniority, P&L, transformation, industry, geo)
- **admin_token**: Authentication token for protected endpoints

See `config.example.yaml` for the complete structure.

## Usage

1. **Initial Refresh**: Click "Refresh" in the dashboard to scrape jobs from all companies
2. **Review Jobs**: Browse the ranked list, sorted by fit score
3. **View Details**: Click a job to see full description, fit analysis, and concerns
4. **Triage**: Mark jobs as Read or Ignored to track your review progress
5. **Apply**: Use the "Open Original Posting" link to apply on company site

## Project Structure

```
job-role-matcher/
├── backend/              # FastAPI backend
│   ├── main.py          # App entry point
│   ├── config.py        # Configuration loading
│   ├── database.py      # Database access layer
│   ├── schema.sql       # Database schema
│   ├── scraper/         # Job scraping module
│   ├── scorer/          # Scoring engine
│   ├── api/             # API endpoints
│   └── tests/           # Unit tests
├── frontend/            # Next.js frontend
│   ├── app/            # Pages and routes
│   ├── components/     # React components
│   └── lib/            # Utilities and API client
├── data/               # SQLite database (gitignored)
├── config.yaml         # User configuration (gitignored)
└── config.example.yaml # Example configuration
```

## API Endpoints

- `GET /health` - Health check
- `GET /jobs` - List active jobs with evaluations
- `GET /jobs/{id}` - Get job detail (requires auth)
- `POST /refresh` - Trigger scraping and scoring (requires auth)
- `PATCH /jobs/{id}/review` - Update review status
- `GET /companies` - List companies with health status
- `GET /stats` - Get job statistics

## Development

### Backend

```bash
cd backend

# Run tests
uv run pytest

# Type checking
uv run mypy .

# Format code
uv run black .
```

### Frontend

```bash
cd frontend

# Type checking
pnpm tsc --noEmit

# Linting
pnpm lint

# Format code
pnpm format
```

## Deployment

See individual README files in `backend/` and `frontend/` for deployment options including:
- Local machine (systemd services)
- Single VPS with nginx
- Docker Compose

## Adding New Companies

1. Create a new adapter in `backend/scraper/adapters/`
2. Implement the `BaseAdapter` interface
3. Add company to `config.yaml` with adapter name
4. Test adapter against live careers page

See existing adapters for examples.

## Customizing Scoring

Edit `config.yaml` to adjust:
- Keyword lists for each dimension
- Scoring weights (must sum to 100)
- Geography preferences
- Action thresholds (in code: 75+ = APPLY, 60-74 = WATCH, <60 = SKIP)

## License

Private project for personal use.

## Support

For issues or questions, see the design document in `.kiro/specs/job-role-matcher/design.md`.
