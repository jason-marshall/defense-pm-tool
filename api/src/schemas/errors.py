"""Error response schemas for OpenAPI documentation.

Provides standardized error response models for consistent API error handling
and clear OpenAPI documentation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """Individual validation error detail."""

    loc: list[str | int] = Field(
        ...,
        description="Location of the error (e.g., ['body', 'name'])",
        examples=[["body", "name"]],
    )
    msg: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Field required"],
    )
    type: str = Field(
        ...,
        description="Error type identifier",
        examples=["value_error.missing"],
    )


class ErrorResponse(BaseModel):
    """Standard error response for domain errors."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Program not found",
                "code": "PROGRAM_NOT_FOUND",
            }
        }
    )

    detail: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Program not found", "Invalid credentials"],
    )
    code: str = Field(
        ...,
        description="Machine-readable error code",
        examples=["PROGRAM_NOT_FOUND", "INVALID_CREDENTIALS"],
    )


class ValidationErrorResponse(BaseModel):
    """Validation error response (422 Unprocessable Entity)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": [
                    {
                        "loc": ["body", "name"],
                        "msg": "Field required",
                        "type": "value_error.missing",
                    },
                    {
                        "loc": ["body", "start_date"],
                        "msg": "Invalid date format",
                        "type": "type_error.date",
                    },
                ]
            }
        }
    )

    detail: list[ErrorDetail] = Field(
        ...,
        description="List of validation errors with locations and messages",
    )


class RateLimitErrorResponse(BaseModel):
    """Rate limit exceeded response (429 Too Many Requests)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "rate_limit_exceeded",
                "message": "Rate limit exceeded: 10/minute",
                "retry_after": 60,
            }
        }
    )

    error: str = Field(
        default="rate_limit_exceeded",
        description="Error type identifier",
    )
    message: str = Field(
        ...,
        description="Rate limit message with limit details",
        examples=["Rate limit exceeded: 10/minute", "Rate limit exceeded: 100/minute"],
    )
    retry_after: int = Field(
        ...,
        description="Seconds to wait before retrying",
        examples=[60, 30],
    )


class AuthenticationErrorResponse(BaseModel):
    """Authentication error response (401 Unauthorized)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Invalid or expired token",
                "code": "INVALID_TOKEN",
            }
        }
    )

    detail: str = Field(
        ...,
        description="Authentication error message",
        examples=["Invalid or expired token", "Token has expired"],
    )
    code: str = Field(
        ...,
        description="Authentication error code",
        examples=["INVALID_TOKEN", "TOKEN_EXPIRED", "INVALID_CREDENTIALS"],
    )


class AuthorizationErrorResponse(BaseModel):
    """Authorization error response (403 Forbidden)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Access denied to this resource",
                "code": "ACCESS_DENIED",
            }
        }
    )

    detail: str = Field(
        ...,
        description="Authorization error message",
        examples=["Access denied to this resource", "Insufficient permissions"],
    )
    code: str = Field(
        ...,
        description="Authorization error code",
        examples=["ACCESS_DENIED", "INSUFFICIENT_PERMISSIONS"],
    )


class NotFoundErrorResponse(BaseModel):
    """Not found error response (404 Not Found)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Program 550e8400-e29b-41d4-a716-446655440000 not found",
                "code": "PROGRAM_NOT_FOUND",
            }
        }
    )

    detail: str = Field(
        ...,
        description="Resource not found message",
        examples=["Program not found", "Activity not found"],
    )
    code: str = Field(
        ...,
        description="Not found error code",
        examples=["PROGRAM_NOT_FOUND", "ACTIVITY_NOT_FOUND", "WBS_NOT_FOUND"],
    )


class ConflictErrorResponse(BaseModel):
    """Conflict error response (409 Conflict)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Program code F35-BLK4 already exists",
                "code": "DUPLICATE_CODE",
            }
        }
    )

    detail: str = Field(
        ...,
        description="Conflict error message",
        examples=["Program code already exists", "Email already registered"],
    )
    code: str = Field(
        ...,
        description="Conflict error code",
        examples=["DUPLICATE_CODE", "EMAIL_ALREADY_EXISTS"],
    )


class InternalErrorResponse(BaseModel):
    """Internal server error response (500 Internal Server Error)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "An unexpected error occurred",
                "code": "INTERNAL_SERVER_ERROR",
            }
        }
    )

    detail: str = Field(
        default="An unexpected error occurred",
        description="Internal error message",
    )
    code: str = Field(
        default="INTERNAL_SERVER_ERROR",
        description="Internal error code",
    )


# Common response dictionaries for endpoint documentation
COMMON_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {
        "model": AuthenticationErrorResponse,
        "description": "Not authenticated - Invalid or missing JWT token",
    },
    403: {
        "model": AuthorizationErrorResponse,
        "description": "Forbidden - Insufficient permissions for this resource",
    },
    404: {
        "model": NotFoundErrorResponse,
        "description": "Not found - Requested resource does not exist",
    },
    409: {
        "model": ConflictErrorResponse,
        "description": "Conflict - Resource already exists or state conflict",
    },
    422: {
        "model": ValidationErrorResponse,
        "description": "Validation error - Invalid request body or parameters",
    },
    429: {
        "model": RateLimitErrorResponse,
        "description": "Rate limit exceeded - Too many requests",
    },
    500: {
        "model": InternalErrorResponse,
        "description": "Internal server error - Unexpected error occurred",
    },
}
