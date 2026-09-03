"""Unit tests for the AuthService."""

import pytest

from app.models import UserRole
from app.services.auth_service import AuthService


class TestAuthService:
    """Tests for AuthService methods."""

    def test_create_user_success(self, db_session):
        """Test successful user creation."""
        user = AuthService.create_user(
            db_session,
            email="newuser@test.com",
            full_name="New User",
            password="Password123",
        )
        assert user.id is not None
        assert user.email == "newuser@test.com"
        assert user.full_name == "New User"
        assert user.hashed_password != "Password123"
        assert user.role == UserRole.VIEWER
        assert user.is_active is True

    def test_create_user_duplicate_email(self, db_session):
        """Test that creating a user with duplicate email raises ValueError."""
        AuthService.create_user(
            db_session,
            email="dup@test.com",
            full_name="First User",
            password="Password123",
        )
        with pytest.raises(ValueError, match="already exists"):
            AuthService.create_user(
                db_session,
                email="dup@test.com",
                full_name="Second User",
                password="Password456",
            )

    def test_authenticate_user_success(self, db_session):
        """Test successful authentication."""
        AuthService.create_user(
            db_session,
            email="auth@test.com",
            full_name="Auth User",
            password="Password123",
        )
        user = AuthService.authenticate_user(db_session, "auth@test.com", "Password123")
        assert user is not None
        assert user.email == "auth@test.com"

    def test_authenticate_user_wrong_password(self, db_session):
        """Test authentication with wrong password returns None."""
        AuthService.create_user(
            db_session,
            email="auth2@test.com",
            full_name="Auth User 2",
            password="Password123",
        )
        user = AuthService.authenticate_user(db_session, "auth2@test.com", "wrong")
        assert user is None

    def test_authenticate_user_nonexistent(self, db_session):
        """Test authentication with nonexistent email returns None."""
        user = AuthService.authenticate_user(db_session, "nonexistent@test.com", "password")
        assert user is None

    def test_get_user_by_email(self, db_session):
        """Test getting user by email."""
        AuthService.create_user(
            db_session,
            email="find@test.com",
            full_name="Find Me",
            password="Password123",
        )
        user = AuthService.get_user_by_email(db_session, "find@test.com")
        assert user is not None
        assert user.full_name == "Find Me"

    def test_get_user_by_id(self, db_session):
        """Test getting user by ID."""
        created = AuthService.create_user(
            db_session,
            email="byid@test.com",
            full_name="By ID",
            password="Password123",
        )
        user = AuthService.get_user_by_id(db_session, created.id)
        assert user is not None
        assert user.email == "byid@test.com"

    def test_update_user_role(self, db_session):
        """Test updating user role."""
        user = AuthService.create_user(
            db_session,
            email="role@test.com",
            full_name="Role User",
            password="Password123",
        )
        updated = AuthService.update_user_role(db_session, user.id, UserRole.ADMIN)
        assert updated.role == UserRole.ADMIN

    def test_deactivate_user(self, db_session):
        """Test deactivating a user."""
        user = AuthService.create_user(
            db_session,
            email="deact@test.com",
            full_name="Deact User",
            password="Password123",
        )
        deactivated = AuthService.deactivate_user(db_session, user.id)
        assert deactivated.is_active is False
