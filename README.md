# Qualification Verification System

A DevOps-enabled Qualification Verification System built with FastAPI, featuring blockchain-based credential verification, JWT authentication, AI-powered fraud detection, and real-time monitoring.

## Features

- **Qualification Management:** Register, search, update, and retrieve qualification records
- **Verification Engine:** Blockchain-based (SHA-256 hash chaining) authenticity verification
- **Audit Logging:** Immutable, append-only audit trail for all verification activities
- **Authentication & Security:** JWT-based auth with role-based access control (RBAC)
- **AI Verification Assistant:** OpenAI-powered anomaly detection for fraudulent credentials
- **Monitoring:** Prometheus metrics with Grafana dashboards
- **DevOps:** Full CI/CD pipeline with GitHub Actions, Docker containerization, and cloud deployment

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** SQLite (dev) / PostgreSQL (production) via SQLAlchemy ORM
- **CI/CD:** GitHub Actions
- **Containerization:** Docker + Docker Compose
- **Testing:** pytest, pytest-asyncio, pytest-cov
- **Static Analysis:** Ruff, Bandit, Radon

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd qualification-verification-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Running the Application

```bash
# Development mode (SQLite)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000
Swagger docs at http://localhost:8000/docs

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run only unit tests
pytest tests/unit

# Run only integration tests
pytest tests/integration
```

### Static Analysis

```bash
# Linting
ruff check app/

# Security scan
bandit -r app/

# Complexity analysis
radon cc app/ -s
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build
```

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | /api/v1/auth/register | Register a new user | No |
| POST | /api/v1/auth/login | Login and get JWT token | No |
| POST | /api/v1/auth/refresh | Refresh access token | No (refresh token) |
| GET | /api/v1/auth/me | Get current user info | Yes |

### Qualifications

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| GET | /api/v1/qualifications/ | Search qualifications | Any authenticated |
| POST | /api/v1/qualifications/ | Register a qualification | Verifier/Admin |
| GET | /api/v1/qualifications/{id} | Get a specific qualification | Any authenticated |
| PUT | /api/v1/qualifications/{id} | Update a qualification | Verifier/Admin |
| DELETE | /api/v1/qualifications/{id} | Soft delete a qualification | Verifier/Admin |

### Verification

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| POST | /api/v1/qualifications/{id}/verify | Verify a qualification | Verifier/Admin |
| GET | /api/v1/qualifications/{id}/verifications | Get verification history | Verifier/Admin |

### AI Analysis

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| POST | /api/v1/ai/analyze/{id} | AI credential analysis | Verifier/Admin |

### Audit Logs

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| GET | /api/v1/audit-logs/ | Search audit logs | Any authenticated |
| GET | /api/v1/audit-logs/{id} | Get specific audit log | Any authenticated |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /metrics | Prometheus metrics endpoint |
| GET | /health | Health check endpoint |
| GET | /docs | Swagger UI (interactive API docs) |

## User Roles

| Role | Permissions |
|------|------------|
| Admin | Full access to all endpoints |
| Verifier | Register, update, delete, and verify qualifications |
| Viewer | Read-only access to qualifications and audit logs |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | sqlite:///./qualification_verification.db | Database connection string |
| SECRET_KEY | dev-secret-key-change-in-production | JWT signing key |
| ALGORITHM | HS256 | JWT algorithm |
| ACCESS_TOKEN_EXPIRE_MINUTES | 30 | Access token expiry |
| REFRESH_TOKEN_EXPIRE_MINUTES | 1440 | Refresh token expiry |
| RATE_LIMIT_PER_MINUTE | 60 | Rate limit threshold |
| OPENAI_API_KEY | (empty) | OpenAI API key for AI features |
| DEBUG | True | Debug mode flag |

## Docker Services

| Service | Port | Description |
|---------|------|-------------|
| app | 8000 | FastAPI application |
| db | 5432 | PostgreSQL database |
| prometheus | 9090 | Metrics collection |
| grafana | 3000 | Monitoring dashboard (admin/admin) |

## Team

| Member | Role | Responsibility |
|--------|------|----------------|
| Ngonidzashe Muzanenhamo | Tech Lead / DevOps | CI/CD, Docker, deployment |
| Loreen Venge | Backend Developer | Core API, database models |
| Judah T Chisare | QA / Testing Engineer | Unit tests, integration tests |
| Nyasha A Madziwanzira | Security & AI Engineer | Auth, blockchain, AI, monitoring |

## License

This project is part of MIM736 - Software Engineering assignment at Midlands State University.
