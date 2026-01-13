"""Unit tests for exception classes."""

from uuid import uuid4

import pytest

from src.core.exceptions import (
    DomainError,
    NotFoundError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    CircularDependencyError,
    ScheduleCalculationError,
)


class TestDomainError:
    """Tests for base DomainError."""

    def test_create_domain_error(self):
        """Test creating a domain error."""
        error = DomainError(message="Test error", code="TEST_ERROR")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.code == "TEST_ERROR"

    def test_domain_error_inheritance(self):
        """Test DomainError is an Exception."""
        error = DomainError(message="Test", code="TEST")
        assert isinstance(error, Exception)


class TestNotFoundError:
    """Tests for NotFoundError."""

    def test_create_not_found_error(self):
        """Test creating a not found error."""
        error = NotFoundError(message="Program 123 not found")
        assert "Program" in str(error)
        assert "123" in str(error)

    def test_not_found_inheritance(self):
        """Test NotFoundError inherits from DomainError."""
        error = NotFoundError(message="User 456 not found")
        assert isinstance(error, DomainError)

    def test_not_found_default_code(self):
        """Test NotFoundError has default code."""
        error = NotFoundError(message="Not found")
        assert error.code == "NOT_FOUND"


class TestValidationError:
    """Tests for ValidationError."""

    def test_create_validation_error(self):
        """Test creating a validation error."""
        error = ValidationError(message="Invalid input")
        assert "Invalid input" in str(error)

    def test_validation_error_default_code(self):
        """Test validation error has default code."""
        error = ValidationError(message="Name is required")
        assert error.code == "VALIDATION_ERROR"
        assert isinstance(error, DomainError)


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_create_auth_error(self):
        """Test creating authentication error."""
        error = AuthenticationError(message="Invalid credentials")
        assert "Invalid credentials" in str(error)

    def test_auth_error_inheritance(self):
        """Test AuthenticationError inherits from DomainError."""
        error = AuthenticationError(message="Token expired")
        assert isinstance(error, DomainError)

    def test_auth_error_default_message(self):
        """Test AuthenticationError default message."""
        error = AuthenticationError()
        assert "Authentication required" in str(error)


class TestAuthorizationError:
    """Tests for AuthorizationError."""

    def test_create_authz_error(self):
        """Test creating authorization error."""
        error = AuthorizationError(message="Access denied")
        assert "Access denied" in str(error)

    def test_authz_error_inheritance(self):
        """Test AuthorizationError inherits from DomainError."""
        error = AuthorizationError(message="Insufficient permissions")
        assert isinstance(error, DomainError)

    def test_authz_error_default_message(self):
        """Test AuthorizationError default message."""
        error = AuthorizationError()
        assert "Permission denied" in str(error)


class TestConflictError:
    """Tests for ConflictError."""

    def test_create_conflict_error(self):
        """Test creating conflict error."""
        error = ConflictError(message="Resource already exists")
        assert "already exists" in str(error)

    def test_conflict_error_inheritance(self):
        """Test ConflictError inherits from DomainError."""
        error = ConflictError(message="Duplicate entry")
        assert isinstance(error, DomainError)

    def test_conflict_error_default_code(self):
        """Test ConflictError has default code."""
        error = ConflictError(message="Conflict")
        assert error.code == "CONFLICT"


class TestCircularDependencyError:
    """Tests for CircularDependencyError."""

    def test_create_circular_error(self):
        """Test creating circular dependency error."""
        ids = [uuid4(), uuid4(), uuid4()]
        error = CircularDependencyError(cycle_path=ids)
        assert "Circular dependency" in str(error)
        assert error.code == "CIRCULAR_DEPENDENCY"

    def test_circular_error_stores_path(self):
        """Test circular error stores cycle path."""
        ids = [uuid4(), uuid4()]
        error = CircularDependencyError(cycle_path=ids)
        assert error.cycle_path == ids


class TestScheduleCalculationError:
    """Tests for ScheduleCalculationError."""

    def test_create_schedule_error(self):
        """Test creating schedule calculation error."""
        error = ScheduleCalculationError(message="Calculation failed")
        assert "failed" in str(error)

    def test_schedule_error_default_code(self):
        """Test ScheduleCalculationError default code."""
        error = ScheduleCalculationError(message="Error")
        assert error.code == "SCHEDULE_CALCULATION_ERROR"
