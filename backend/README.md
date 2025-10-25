# Job Role Matcher - Backend

FastAPI backend for the Job Role Matcher system.

## Setup

1. Create a virtual environment using uv:
```bash
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies using uv:
```bash
uv pip install -r requirements.txt
```

3. Create configuration file:
```bash
cp ../config.example.yaml ../config.yaml
# Edit config.yaml with your settings
```

## Running

Development mode with auto-reload:
```bash
uv run uvicorn main:app --reload
```

Production mode:
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

API documentation (auto-generated) at http://localhost:8000/docs

## Project Structure

```
backend/
├── main.py              # FastAPI app entry point
├── config.py            # Configuration loading
├── database.py          # Database access layer
├── schema.sql           # Database schema
├── scraper/             # Job scraping module
│   ├── base.py          # Base adapter interface
│   ├── runner.py        # Scraper runner
│   └── adapters/        # Company-specific adapters
├── scorer/              # Scoring engine
│   ├── engine.py        # Main scoring logic
│   ├── extractor.py     # Signal extraction
│   └── signals.py       # Signal dataclasses
├── api/                 # API endpoints
│   ├── routes.py        # Route definitions
│   └── auth.py          # Authentication
└── tests/               # Unit tests
```

## Configuration

The system is configured via `config.yaml` in the project root. See `config.example.yaml` for the structure.

Key configuration sections:
- `admin_token`: Authentication token for protected endpoints
- `companies`: List of target companies with adapter names
- `seniority_keywords`: Keywords for seniority detection
- `domain_keywords`: Keywords for industry matching
- `geography`: Preferred and banned locations
- `scoring_weights`: Weights for each scoring dimension

## Database

The system uses SQLite for data storage. The database file is created automatically at `data/jobs.db`.

Schema includes:
- `companies`: Target companies and adapter status
- `job_postings`: Job listings with metadata
- `evaluations`: Scoring results for each job

## API Endpoints

- `GET /health` - Health check
- `GET /jobs` - List active jobs with evaluations
- `GET /jobs/{id}` - Get job detail (requires auth)
- `POST /refresh` - Trigger scraping and scoring (requires auth)
- `PATCH /jobs/{id}/review` - Update review status
- `GET /companies` - List companies with health status
- `GET /stats` - Get job statistics

## Development

Run tests:
```bash
uv run pytest
```

Check types:
```bash
uv run mypy .
```

Format code:
```bash
uv run black .
```
