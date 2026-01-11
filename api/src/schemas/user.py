"""Pydantic schemas for User authentication and management.

This module provides schemas for:
- User registration (UserCreate)
- User profile updates (UserUpdate)
- User API responses (UserResponse)
- Authentication (UserLogin, TokenResponse)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.models.enums import UserRole


class UserBase(BaseModel):
    """
    Base schema with common user fields.

    Used as foundation for Create/Update/Response schemas.
    """

    email: EmailStr = Field(
        ...,
        description="User's email address (used for login)",
        examples=["john.doe@example.com"],
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User's full display name",
        examples=["John Doe"],
    )


class UserCreate(UserBase):
    """
    Schema for creating a new user account.

    Includes password validation requirements:
    - Minimum 8 characters
    - Required for account creation
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "john.doe@example.com",
                "password": "SecureP@ss123",
                "full_name": "John Doe",
            }
        }
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (min 8 characters)",
        examples=["SecureP@ss123"],
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password meets basic security requirements.

        Requirements:
        - At least 8 characters (enforced by Field)
        - Not entirely whitespace
        """
        if not v or v.isspace():
            raise ValueError("Password cannot be empty or whitespace only")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Validate full name is not just whitespace."""
        if not v or v.isspace():
            raise ValueError("Full name cannot be empty or whitespace only")
        return v.strip()


class UserUpdate(BaseModel):
    """
    Schema for updating user profile.

    All fields are optional - only provided fields are updated.
    Password update requires meeting the same requirements as creation.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "John D. Doe",
                "email": "john.d.doe@example.com",
            }
        }
    )

    email: EmailStr | None = Field(
        default=None,
        description="New email address",
        examples=["john.d.doe@example.com"],
    )
    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="New display name",
        examples=["John D. Doe"],
    )
    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="New password (min 8 characters)",
        examples=["NewSecureP@ss456"],
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str | None) -> str | None:
        """Validate password if provided."""
        if v is not None and v.isspace():
            raise ValueError("Password cannot be whitespace only")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str | None) -> str | None:
        """Strip whitespace from full name if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Full name cannot be empty or whitespace only")
        return v


class UserRoleUpdate(BaseModel):
    """
    Schema for updating user role (admin only).

    Separated from UserUpdate as role changes are privileged operations.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "scheduler",
            }
        }
    )

    role: UserRole = Field(
        ...,
        description="New role for the user",
        examples=["scheduler", "program_manager", "admin"],
    )


class UserStatusUpdate(BaseModel):
    """
    Schema for activating/deactivating user accounts.

    Separated from UserUpdate as this is an admin operation.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_active": False,
            }
        }
    )

    is_active: bool = Field(
        ...,
        description="Whether the user account should be active",
        examples=[True, False],
    )


class UserResponse(BaseModel):
    """
    Schema for user data in API responses.

    Excludes sensitive fields (password hash).
    Includes all public profile and status information.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "role": "scheduler",
                "is_active": True,
                "created_at": "2026-01-08T12:00:00Z",
                "updated_at": "2026-01-08T12:00:00Z",
            }
        },
    )

    id: UUID = Field(
        ...,
        description="Unique user identifier",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["john.doe@example.com"],
    )
    full_name: str = Field(
        ...,
        description="User's display name",
        examples=["John Doe"],
    )
    role: UserRole = Field(
        ...,
        description="User's role for access control",
        examples=["viewer", "analyst", "scheduler", "program_manager", "admin"],
    )
    is_active: bool = Field(
        ...,
        description="Whether the account is active",
        examples=[True],
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp",
        examples=["2026-01-08T12:00:00Z"],
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
        examples=["2026-01-08T12:00:00Z"],
    )


class UserBriefResponse(BaseModel):
    """
    Brief user response for embedding in other responses.

    Contains only essential identification fields.
    Used when including user info in program/activity responses.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
            }
        },
    )

    id: UUID = Field(
        ...,
        description="Unique user identifier",
    )
    email: EmailStr = Field(
        ...,
        description="User's email address",
    )
    full_name: str = Field(
        ...,
        description="User's display name",
    )


# ============================================================================
# Authentication Schemas
# ============================================================================


class UserLogin(BaseModel):
    """
    Schema for user login request.

    Accepts email and password for authentication.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "john.doe@example.com",
                "password": "SecureP@ss123",
            }
        }
    )

    email: EmailStr = Field(
        ...,
        description="Email address for login",
        examples=["john.doe@example.com"],
    )
    password: str = Field(
        ...,
        description="User password",
        examples=["SecureP@ss123"],
    )


class TokenResponse(BaseModel):
    """
    Schema for JWT token response after successful authentication.

    Returns access token for API authentication.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 900,
            }
        }
    )

    access_token: str = Field(
        ...,
        description="JWT access token for API authentication",
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
        examples=["bearer"],
    )
    expires_in: int = Field(
        ...,
        description="Token expiration time in seconds",
        examples=[900],
    )


class TokenPayload(BaseModel):
    """
    Schema for JWT token payload data.

    Used internally for token creation/validation.
    """

    sub: UUID = Field(
        ...,
        description="Subject (user ID)",
    )
    role: UserRole = Field(
        ...,
        description="User role at time of token creation",
    )
    exp: int = Field(
        ...,
        description="Expiration timestamp (Unix epoch)",
    )


class RefreshTokenRequest(BaseModel):
    """
    Schema for refresh token request.

    Used to exchange a refresh token for a new access token.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    )

    refresh_token: str = Field(
        ...,
        description="Refresh token to exchange for new access token",
    )


class TokenPairResponse(BaseModel):
    """
    Schema for token pair response (access + refresh).

    Returned after successful login.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 900,
            }
        }
    )

    access_token: str = Field(
        ...,
        description="JWT access token for API authentication",
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token for obtaining new access tokens",
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
        examples=["bearer"],
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        examples=[900],
    )
