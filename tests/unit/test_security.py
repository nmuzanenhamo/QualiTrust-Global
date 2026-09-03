"""Unit tests for the security module."""

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_hash(self):
        """Test that hash_password returns a hashed string."""
        hashed = hash_password("testpassword123")
        assert hashed != "testpassword123"
        assert hashed.startswith("$2b$")

    def test_hash_password_different_inputs(self):
        """Test that different passwords produce different hashes."""
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password."""
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for incorrect password."""
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False


class TestJWTTokens:
    """Tests for JWT token creation and decoding."""

    def test_create_access_token(self):
        """Test that access token is created and decodable."""
        data = {"sub": "1", "email": "test@test.com", "role": "admin"}
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload is not None
        assert payload["email"] == "test@test.com"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        """Test that refresh token is created and decodable."""
        data = {"sub": "1", "email": "test@test.com", "role": "admin"}
        token = create_refresh_token(data)
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        """Test that decoding an invalid token returns None."""
        result = decode_token("invalid.token.here")
        assert result is None
