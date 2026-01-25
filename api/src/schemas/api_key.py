"""Pydantic schemas for API key management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    """Schema for creating a new API key."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable name for the key",
        examples=["CI/CD Pipeline", "Monitoring Service"],
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional description of key purpose",
        examples=["Used by GitHub Actions for deployment"],
    )
    scopes: list[str] | None = Field(
        default=None,
        description="Optional list of allowed scopes (empty = full access)",
        examples=[["programs:read", "activities:read"]],
    )
    expires_in_days: int | None = Field(
        default=365,
        ge=1,
        le=3650,
        description="Days until key expires (1-3650, or null for never)",
        examples=[365, 90, 30],
    )


class APIKeyResponse(BaseModel):
    """Schema for API key response (without the actual key)."""

    id: UUID = Field(..., description="Unique identifier")
    name: str = Field(..., description="Key name")
    description: str | None = Field(default=None, description="Key description")
    key_prefix: str = Field(
        ...,
        description="Key prefix for identification (e.g., 'dpm_a1b2c3d4')",
    )
    scopes: str | None = Field(default=None, description="Comma-separated scopes")
    is_active: bool = Field(..., description="Whether key is active")
    expires_at: datetime | None = Field(default=None, description="Expiration timestamp")
    last_used_at: datetime | None = Field(default=None, description="Last time key was used")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    model_config = {"from_attributes": True}


class APIKeyCreatedResponse(BaseModel):
    """Schema for newly created API key (includes the actual key).

    WARNING: The 'key' field is only returned once at creation.
    Store it securely - it cannot be retrieved later!
    """

    id: UUID = Field(..., description="Unique identifier")
    name: str = Field(..., description="Key name")
    key_prefix: str = Field(..., description="Key prefix for identification")
    key: str = Field(
        ...,
        description="Full API key - STORE THIS SECURELY! Cannot be retrieved again.",
    )
    expires_at: datetime | None = Field(default=None, description="Expiration timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    message: str = Field(
        default="Store this key securely - it cannot be retrieved again.",
        description="Important message about key security",
    )

    model_config = {"from_attributes": True}


class APIKeyListResponse(BaseModel):
    """Schema for list of API keys."""

    items: list[APIKeyResponse] = Field(..., description="List of API keys")
    total: int = Field(..., description="Total number of keys")


class APIKeyVerifyRequest(BaseModel):
    """Schema for verifying an API key (for testing)."""

    key: str = Field(
        ...,
        min_length=20,
        description="Full API key to verify",
    )


class APIKeyVerifyResponse(BaseModel):
    """Schema for API key verification response."""

    valid: bool = Field(..., description="Whether key is valid")
    key_prefix: str | None = Field(default=None, description="Key prefix if valid")
    user_id: UUID | None = Field(default=None, description="User ID if valid")
    expires_at: datetime | None = Field(default=None, description="Expiration timestamp if valid")
