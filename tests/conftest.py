"""Test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models import User, UserRole
from app.services.auth_service import AuthService

# Test database (in-memory SQLite)
TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with a fresh database."""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def admin_user(db_session):
    """Create an admin user for testing."""
    return AuthService.create_user(
        db_session,
        email="admin@test.com",
        full_name="Test Admin",
        password="Admin@123",
        role=UserRole.ADMIN,
    )


@pytest.fixture
def verifier_user(db_session):
    """Create a verifier user for testing."""
    return AuthService.create_user(
        db_session,
        email="verifier@test.com",
        full_name="Test Verifier",
        password="Verifier@123",
        role=UserRole.VERIFIER,
    )


@pytest.fixture
def viewer_user(db_session):
    """Create a viewer user for testing."""
    return AuthService.create_user(
        db_session,
        email="viewer@test.com",
        full_name="Test Viewer",
        password="Viewer@123",
        role=UserRole.VIEWER,
    )


@pytest.fixture
def admin_token(client, admin_user):
    """Get JWT token for admin user."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.com", "password": "Admin@123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def verifier_token(client, verifier_user):
    """Get JWT token for verifier user."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "verifier@test.com", "password": "Verifier@123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def viewer_token(client, viewer_user):
    """Get JWT token for viewer user."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "viewer@test.com", "password": "Viewer@123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    """Auth headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def verifier_headers(verifier_token):
    """Auth headers for verifier user."""
    return {"Authorization": f"Bearer {verifier_token}"}


@pytest.fixture
def viewer_headers(viewer_token):
    """Auth headers for viewer user."""
    return {"Authorization": f"Bearer {viewer_token}"}


@pytest.fixture
def sample_qualification_data():
    """Sample qualification data for testing."""
    return {
        "title": "Bachelor of Science in Computer Science",
        "qualification_type": "degree",
        "issuing_institution": "Midlands State University",
        "holder_name": "John Doe",
        "holder_email": "john.doe@example.com",
        "holder_id_number": "ID123456",
        "date_issued": "2020-06-15T00:00:00",
        "registration_number": "CS2020/001",
        "serial_number": "MSU-CS-2020-001",
        "description": "Four-year undergraduate degree",
    }
