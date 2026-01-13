"""Unit tests for User schemas."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.schemas.user import UserCreate, UserUpdate, UserResponse
from src.models.enums import UserRole


class TestUserCreate:
    """Tests for UserCreate schema."""

    def test_create_user_minimal(self):
        """Test creating user with minimal fields."""
        user = UserCreate(
            email="test@example.com",
            password="SecurePassword123!",
            full_name="Test User",
        )
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"

    def test_create_user_with_all_fields(self):
        """Test creating user with all fields."""
        user = UserCreate(
            email="admin@example.com",
            password="SecurePassword123!",
            full_name="Admin User",
        )
        assert user.email == "admin@example.com"
        assert user.full_name == "Admin User"

    def test_create_user_invalid_email(self):
        """Test creating user with invalid email."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                password="SecurePassword123!",
                full_name="Test User",
            )

    def test_create_user_short_password(self):
        """Test creating user with too short password."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="short",
                full_name="Test User",
            )


class TestUserUpdate:
    """Tests for UserUpdate schema."""

    def test_update_user_full_name(self):
        """Test updating user full name."""
        update = UserUpdate(full_name="New Name")
        assert update.full_name == "New Name"

    def test_update_user_email(self):
        """Test updating user email."""
        update = UserUpdate(email="new@example.com")
        assert update.email == "new@example.com"

    def test_update_user_full_name_only(self):
        """Test updating only full name."""
        update = UserUpdate(full_name="Updated Name Only")
        assert update.full_name == "Updated Name Only"

    def test_update_user_partial(self):
        """Test partial user update."""
        update = UserUpdate(full_name="Only Name")
        assert update.full_name == "Only Name"
        # Other fields should be None for partial update
