"""Common Pydantic schemas for shared types and responses.

This module provides:
- Generic paginated response wrapper
- Standard error response format
- Reusable field types and validators
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# Type variable for generic paginated responses
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic wrapper for paginated API responses.

    Provides consistent pagination structure across all list endpoints.
    Use with any response schema type.

    Example:
        PaginatedResponse[UserResponse] for paginated user lists
        PaginatedResponse[ActivityResponse] for paginated activity lists
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "pages": 5,
            }
        }
    )

    items: list[T] = Field(
        ...,
        description="List of items for the current page",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of items across all pages",
        examples=[100],
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number (1-indexed)",
        examples=[1],
    )
    page_size: int = Field(
        ...,
        ge=1,
        le=100,
        description="Number of items per page",
        examples=[20],
    )

    @property
    def pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        """Check if there are more pages after current."""
        return self.page < self.pages

    @property
    def has_previous(self) -> bool:
        """Check if there are pages before current."""
        return self.page > 1


class FieldError(BaseModel):
    """
    Schema for individual field validation errors.

    Used within ErrorResponse to provide detailed field-level error info.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "email",
                "message": "Invalid email format",
                "type": "value_error",
            }
        }
    )

    field: str = Field(
        ...,
        description="Name of the field with the error",
        examples=["email", "duration", "start_date"],
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Invalid email format", "Value must be >= 0"],
    )
    type: str | None = Field(
        default=None,
        description="Error type identifier",
        examples=["value_error", "type_error", "missing"],
    )


class ErrorResponse(BaseModel):
    """
    Standard error response format for API errors.

    Provides consistent error structure across all endpoints
    with support for field-level validation errors.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Validation error",
                "error_code": "VALIDATION_ERROR",
                "field_errors": [
                    {
                        "field": "email",
                        "message": "Invalid email format",
                        "type": "value_error",
                    }
                ],
            }
        }
    )

    detail: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Resource not found", "Validation error", "Unauthorized"],
    )
    error_code: str = Field(
        ...,
        description="Machine-readable error code for client handling",
        examples=[
            "NOT_FOUND",
            "VALIDATION_ERROR",
            "UNAUTHORIZED",
            "CIRCULAR_DEPENDENCY",
        ],
    )
    field_errors: list[FieldError] | None = Field(
        default=None,
        description="List of field-level errors (for validation errors)",
    )


class HealthResponse(BaseModel):
    """Health check response schema."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "database": "connected",
            }
        }
    )

    status: str = Field(
        ...,
        description="Overall health status",
        examples=["healthy", "degraded", "unhealthy"],
    )
    version: str = Field(
        ...,
        description="API version",
        examples=["0.1.0"],
    )
    database: str = Field(
        ...,
        description="Database connection status",
        examples=["connected", "disconnected"],
    )


class MessageResponse(BaseModel):
    """Simple message response for operations without data return."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Operation completed successfully",
            }
        }
    )

    message: str = Field(
        ...,
        description="Status message",
        examples=["Resource deleted successfully", "Operation completed"],
    )
