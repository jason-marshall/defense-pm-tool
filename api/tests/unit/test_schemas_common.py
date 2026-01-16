"""Unit tests for common schemas."""

from src.schemas.common import (
    ErrorResponse,
    FieldError,
    HealthResponse,
    MessageResponse,
    PaginatedResponse,
)


class TestPaginatedResponse:
    """Tests for PaginatedResponse schema."""

    def test_pages_calculation(self):
        """Test pages property calculation."""
        response = PaginatedResponse[str](
            items=["a", "b", "c"],
            total=100,
            page=1,
            page_size=20,
        )
        assert response.pages == 5

    def test_pages_with_exact_division(self):
        """Test pages with exact division."""
        response = PaginatedResponse[str](
            items=[],
            total=40,
            page=1,
            page_size=10,
        )
        assert response.pages == 4

    def test_pages_with_remainder(self):
        """Test pages with remainder."""
        response = PaginatedResponse[str](
            items=[],
            total=45,
            page=1,
            page_size=10,
        )
        assert response.pages == 5

    def test_pages_zero_total(self):
        """Test pages with zero total items."""
        response = PaginatedResponse[str](
            items=[],
            total=0,
            page=1,
            page_size=10,
        )
        assert response.pages == 0

    def test_has_next_true(self):
        """Test has_next when more pages exist."""
        response = PaginatedResponse[str](
            items=["a"],
            total=50,
            page=1,
            page_size=10,
        )
        assert response.has_next is True

    def test_has_next_false(self):
        """Test has_next on last page."""
        response = PaginatedResponse[str](
            items=["a"],
            total=50,
            page=5,
            page_size=10,
        )
        assert response.has_next is False

    def test_has_next_single_page(self):
        """Test has_next with single page."""
        response = PaginatedResponse[str](
            items=["a", "b"],
            total=2,
            page=1,
            page_size=10,
        )
        assert response.has_next is False

    def test_has_previous_true(self):
        """Test has_previous when previous pages exist."""
        response = PaginatedResponse[str](
            items=["a"],
            total=50,
            page=3,
            page_size=10,
        )
        assert response.has_previous is True

    def test_has_previous_false(self):
        """Test has_previous on first page."""
        response = PaginatedResponse[str](
            items=["a"],
            total=50,
            page=1,
            page_size=10,
        )
        assert response.has_previous is False


class TestFieldError:
    """Tests for FieldError schema."""

    def test_field_error_basic(self):
        """Test basic field error."""
        error = FieldError(
            field="email",
            message="Invalid email format",
        )
        assert error.field == "email"
        assert error.message == "Invalid email format"
        assert error.type is None

    def test_field_error_with_type(self):
        """Test field error with type."""
        error = FieldError(
            field="duration",
            message="Value must be >= 0",
            type="value_error",
        )
        assert error.type == "value_error"


class TestErrorResponse:
    """Tests for ErrorResponse schema."""

    def test_error_response_basic(self):
        """Test basic error response."""
        error = ErrorResponse(
            detail="Not found",
            error_code="NOT_FOUND",
        )
        assert error.detail == "Not found"
        assert error.error_code == "NOT_FOUND"
        assert error.field_errors is None

    def test_error_response_with_field_errors(self):
        """Test error response with field errors."""
        error = ErrorResponse(
            detail="Validation error",
            error_code="VALIDATION_ERROR",
            field_errors=[
                FieldError(field="email", message="Invalid format"),
                FieldError(field="name", message="Required"),
            ],
        )
        assert len(error.field_errors) == 2
        assert error.field_errors[0].field == "email"


class TestHealthResponse:
    """Tests for HealthResponse schema."""

    def test_health_response(self):
        """Test health response."""
        response = HealthResponse(
            status="healthy",
            version="0.1.0",
            database="connected",
        )
        assert response.status == "healthy"
        assert response.version == "0.1.0"
        assert response.database == "connected"


class TestMessageResponse:
    """Tests for MessageResponse schema."""

    def test_message_response(self):
        """Test message response."""
        response = MessageResponse(message="Operation completed successfully")
        assert response.message == "Operation completed successfully"
