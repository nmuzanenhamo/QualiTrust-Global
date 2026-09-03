"""Integration tests for authentication endpoints."""

from app.models import UserRole


class TestAuthEndpoints:
    """Integration tests for auth API endpoints."""

    def test_register_user(self, client):
        """Test user registration via API."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "full_name": "New User",
                "password": "Password123",
                "role": "viewer",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "viewer"
        assert "id" in data

    def test_register_duplicate_email(self, client, admin_user):
        """Test registering with duplicate email fails."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@test.com",
                "full_name": "Duplicate User",
                "password": "Password123",
                "role": "viewer",
            },
        )
        assert response.status_code == 400

    def test_login_success(self, client, admin_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com", "password": "Admin@123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, admin_user):
        """Test login with wrong password fails."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user fails."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent@test.com", "password": "password"},
        )
        assert response.status_code == 401

    def test_get_current_user(self, client, admin_headers):
        """Test getting current user info with valid token."""
        response = client.get("/api/v1/auth/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"

    def test_get_current_user_no_token(self, client):
        """Test accessing /me without token fails."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_refresh_token(self, client, admin_user):
        """Test refreshing an access token."""
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com", "password": "Admin@123"},
        )
        refresh_token = login_response.json()["refresh_token"]
        response = client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
