# System Architecture

## Overview

The Qualification Verification System (QVS) is a DevOps-enabled web application built with FastAPI that provides secure, scalable, and maintainable qualification verification services. The system uses a layered architecture with clear separation of concerns.

## Architecture Diagram

```
+-----------------------------------------------------------+
|                      Client Layer                          |
|  Web Browser / API Client / Swagger UI (/docs)            |
+-----------------------------------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|                    API Gateway Layer                       |
|  FastAPI Application + CORS + Metrics Middleware           |
+-----------------------------------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|                    Router Layer (Controllers)              |
|  +---------+  +-------------+  +--------------+           |
|  |  Auth   |  | Qualifications| | Verification |           |
|  | Router  |  |    Router     | |    Router    |           |
|  +---------+  +-------------+  +--------------+           |
|  +---------+  +-------------+  +--------------+           |
|  |  Audit  |  |     AI      |  |  Monitoring  |           |
|  | Router  |  |   Router    |  |   (Metrics)  |           |
|  +---------+  +-------------+  +--------------+           |
+-----------------------------------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|                    Service Layer (Business Logic)          |
|  +---------+  +-------------+  +--------------+           |
|  |  Auth   |  | Qualification| | Verification |           |
|  | Service |  |   Service    | |   Service    |           |
|  +---------+  +-------------+  +--------------+           |
|  +---------+  +-------------+  +--------------+           |
|  |  Audit  |  |     AI      |  | Blockchain   |           |
|  | Service |  |   Service   |  |   Service    |           |
|  +---------+  +-------------+  +--------------+           |
|  +--------------+                                        |
|  | Monitoring   |                                        |
|  |   Service    |                                        |
|  +--------------+                                        |
+-----------------------------------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|                    Data Layer (Models & DB)                |
|  +---------------------------------------------------+   |
|  |              SQLAlchemy ORM (Base)                 |   |
|  +---------------------------------------------------+   |
|  |  User  |  Qualification  |  VerificationRecord  |   |
|  |         AuditLog                                  |   |
|  +---------------------------------------------------+   |
+-----------------------------------------------------------+
                            |
              +-------------+-------------+
              |                           |
    +---------v---------+       +---------v---------+
    |    SQLite (Dev)   |       | PostgreSQL (Prod) |
    +-------------------+       +-------------------+
```

## Component Descriptions

### 1. API Gateway Layer
- **FastAPI Application**: Main entry point handling HTTP requests
- **CORS Middleware**: Cross-origin resource sharing configuration
- **Metrics Middleware**: Automatic Prometheus metrics collection for all requests

### 2. Router Layer
Handles HTTP request/response mapping and delegates to services:
- **Auth Router**: User registration, login, token refresh, user info
- **Qualifications Router**: CRUD operations for qualification records
- **Verification Router**: Qualification authenticity verification
- **Audit Router**: Audit log querying and retrieval
- **AI Router**: AI-powered credential analysis

### 3. Service Layer
Contains business logic and data manipulation:
- **AuthService**: User creation, authentication, role management
- **QualificationService**: CRUD with search, pagination, soft delete
- **VerificationService**: Orchestrates verification with blockchain
- **BlockchainService**: SHA-256 hash chaining for credential integrity
- **AuditService**: Immutable audit trail logging
- **AIService**: OpenAI integration with heuristic fallback
- **MonitoringService**: Prometheus metrics recording

### 4. Data Layer
- **SQLAlchemy ORM**: Database abstraction supporting SQLite and PostgreSQL
- **Models**: User, Qualification, VerificationRecord, AuditLog
- **Pydantic Schemas**: Input validation and response serialization

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | FastAPI | Async API with auto-documentation |
| ORM | SQLAlchemy 2.0 | Database abstraction |
| Database (Dev) | SQLite | Local development |
| Database (Prod) | PostgreSQL | Production database |
| Authentication | python-jose (JWT) | Token-based auth |
| Password Hashing | passlib (bcrypt) | Secure password storage |
| Metrics | prometheus-client | System monitoring |
| AI Integration | OpenAI API | Fraud detection |
| CI/CD | GitHub Actions | Automated pipeline |
| Containerization | Docker | Deployment packaging |
| Cloud Platform | Render | Production hosting |

## Security Architecture

- **JWT Tokens**: Short-lived access tokens (30 min) + refresh tokens (24 hours)
- **RBAC**: Three roles (Admin, Verifier, Viewer) with endpoint-level enforcement
- **Password Security**: bcrypt hashing with automatic salt generation
- **Input Validation**: Pydantic schemas for all request bodies
- **Rate Limiting**: Configurable rate limiting per user
- **CORS**: Configurable allowed origins

## Blockchain Verification

The system implements a lightweight blockchain for credential integrity:

1. Each qualification is hashed using SHA-256
2. Each credential hash includes the previous credential's hash (chaining)
3. Verification checks both the hash validity and chain integrity
4. Tampering with any credential breaks the chain and fails verification

## DevOps Pipeline

```
Developer -> Git Push -> GitHub -> Actions CI -> Build -> Test -> Coverage -> Security Scan
                                                                              |
                                                                              v
                                                                    Docker Build -> Push -> Deploy
```

### CI Pipeline (on PR):
1. Lint with Ruff
2. Security scan with Bandit
3. Complexity analysis with Radon
4. Run unit tests
5. Run integration tests
6. Check coverage >= 80%

### CD Pipeline (on merge to main):
1. Build Docker image (multi-stage)
2. Push to Docker Hub
3. Deploy to Render cloud platform
