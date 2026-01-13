"""Unit tests for core auth module."""

import pytest

from src.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_different_hash(self):
        """Test that hashing the same password twice gives different hashes."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        # bcrypt generates unique salts, so hashes should be different
        assert hash1 != hash2

    def test_hash_password_produces_valid_hash(self):
        """Test that hash is a valid bcrypt hash."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        # bcrypt hashes start with $2b$
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password("WrongPassword", hashed) is False

    def test_verify_password_empty_password(self):
        """Test verifying with empty password."""
        hashed = hash_password("TestPassword123!")
        assert verify_password("", hashed) is False

    def test_hash_special_characters(self):
        """Test hashing password with special characters."""
        password = "Test!@#$%^&*()_+-=[]{}|;':\",./<>?"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_hash_unicode_password(self):
        """Test hashing password with unicode characters."""
        password = "Test密码пароль"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True


class TestTokenCreation:
    """Tests for JWT token creation."""

    def test_create_access_token(self):
        """Test creating an access token."""
        data = {"sub": "user@example.com"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0
        # JWT has 3 parts separated by dots
        parts = token.split(".")
        assert len(parts) == 3

    def test_create_refresh_token(self):
        """Test creating a refresh token."""
        data = {"sub": "user@example.com"}
        token = create_refresh_token(data)
        assert isinstance(token, str)
        assert len(token) > 0
        parts = token.split(".")
        assert len(parts) == 3

    def test_tokens_are_different(self):
        """Test that access and refresh tokens are different."""
        data = {"sub": "user@example.com"}
        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)
        assert access_token != refresh_token

    def test_token_with_additional_data(self):
        """Test creating token with additional claims."""
        data = {"sub": "user@example.com", "role": "admin", "user_id": "123"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0
