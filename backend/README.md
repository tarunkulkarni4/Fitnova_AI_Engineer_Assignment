# FitNova AI Sales Intelligence Platform — Backend Foundation

This is the FastAPI backend foundation for **FitNova AI Sales Intelligence Platform**, an AI-powered sales call analysis system that transcribes conversations, evaluates performance, detects Objections/Compliance Issues, and provides insights through dashboard panels.

---

## Folder Structure

The project is structured according to clean architecture principles:

```
backend/
├── alembic/                  # Alembic database migration scripts
├── alembic.ini               # Alembic configuration
├── app/
│   ├── api/                  # API presentation layer
│   │   ├── routes/           # Endpoint route controllers (e.g., health.py)
│   │   └── router.py         # Root routers aggregator
│   ├── core/                 # Core system files (settings, logging setups)
│   │   ├── config.py         # Pydantic Settings configuration manager
│   │   └── logging.py        # Loguru logger setup
│   ├── database/             # Database persistence settings
│   │   ├── base.py           # SQLAlchemy declarative Base class
│   │   └── database.py       # Session maker and dependency helpers
│   ├── models/               # SQLAlchemy models (for future entities)
│   ├── schemas/              # Pydantic validation schemas
│   ├── services/             # Core business logic services
│   │   ├── upload_service.py # Audio file upload handling
│   │   ├── call_service.py   # Call records database interfaces
│   │   ├── processing_service.py # Coordinates background jobs state
│   │   ├── transcript_service.py # Handles dialog segment manipulation
│   │   ├── analysis_service.py # Triggers quality audits and scores
│   │   └── feedback_service.py # Handles manual reviewer overrides
│   ├── adapters/             # Telephony and external integrations adapters
│   ├── workers/              # Asynchronous background task workers
│   ├── prompts/              # System/evaluation prompt definitions
│   ├── storage/              # Local storage subfolders
│   │   ├── audio/            # Raw call recording files
│   │   ├── transcripts/      # Saved transcript documents
│   │   └── exports/          # Generated summary report exports
│   ├── utils/                # Helper tools and utility modules
│   ├── ai/                   # AI analysis and transcription engines
│   ├── pipelines/            # Pipeline execution flows
│   └── main.py               # FastAPI entrypoint application
├── Dockerfile                # Production Docker build configuration
├── docker-compose.yml        # Docker compose configuration (DB & Web services)
├── requirements.txt          # Package dependencies lists
└── .env.example              # Environment variables template
```

---

## Environment Variables

Copy `.env.example` to `.env` inside the `backend` folder and populate it with relevant configuration settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_NAME` | Name of the backend application | `FitNova AI Backend` |
| `VERSION` | API version designation | `1.0.0` |
| `API_V1_STR` | Root path prefix for API endpoints | `/api/v1` |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `BACKEND_CORS_ORIGINS` | Permissible origins for CORS (JSON array of strings) | `["*"]` |
| `POSTGRES_SERVER` | Hostname of the Postgres instance | `localhost` |
| `POSTGRES_USER` | Username for Postgres authentication | `postgres` |
| `POSTGRES_PASSWORD` | Password for Postgres authentication | `postgrespassword` |
| `POSTGRES_DB` | Target database name | `fitnova` |
| `POSTGRES_PORT` | Port of the Postgres instance | `5432` |
| `DATABASE_URL` | Complete connection string (overrides separate variables) | *Derived automatically* |

---

## Installation

### Prerequisites
- Python 3.12 (Python 3.11+ is supported locally)
- PostgreSQL (if running locally without Docker)
- Docker and Docker Compose (optional)

### Setup Local Environment
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

---

## Running Locally

To run the application locally on `http://localhost:8000`:
```bash
uvicorn app.main:app --reload
```

---

## Running with Docker

To spin up the PostgreSQL database and FastAPI backend services together using Docker Compose:

1. Ensure Docker is running.
2. Build and start the containers:
   ```bash
   docker compose up --build
   ```
3. The app is accessible at `http://localhost:8000`.

---

## API Documentation

- **Swagger UI Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Endpoint Example

#### Health Check
- **URL**: `/api/v1/health`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "status": "healthy",
    "service": "FitNova AI Backend",
    "version": "1.0.0"
  }
  ```
