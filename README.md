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

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Register a new user |
| POST | /api/v1/auth/login | Login and get JWT token |
| GET | /api/v1/qualifications | List/search qualifications |
| POST | /api/v1/qualifications | Register a qualification |
| GET | /api/v1/qualifications/{id} | Get a specific qualification |
| PUT | /api/v1/qualifications/{id} | Update a qualification |
| DELETE | /api/v1/qualifications/{id} | Soft delete a qualification |
| POST | /api/v1/qualifications/{id}/verify | Verify a qualification |
| GET | /api/v1/audit-logs | Query audit history |
| GET | /api/v1/ai/analyze | AI-powered credential analysis |
| GET | /metrics | Prometheus metrics |
| GET | /health | Health check |

## Team

| Member | Role | Responsibility |
|--------|------|----------------|
| Ngonidzashe Muzanenhamo | Tech Lead / DevOps | CI/CD, Docker, deployment |
| Loreen Venge | Backend Developer | Core API, database models |
| Judah T Chisare | QA / Testing Engineer | Unit tests, integration tests |
| Nyasha A Madziwanzira | Security & AI Engineer | Auth, blockchain, AI, monitoring |

## License

This project is part of MIM736 - Software Engineering assignment at Midlands State University.
