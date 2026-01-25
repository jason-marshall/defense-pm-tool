"""API Key management endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import NotFoundError
from src.schemas.api_key import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyListResponse,
    APIKeyResponse,
)
from src.schemas.errors import (
    AuthenticationErrorResponse,
    NotFoundErrorResponse,
    RateLimitErrorResponse,
    ValidationErrorResponse,
)
from src.services.api_key_service import APIKeyService

router = APIRouter(tags=["API Keys"])


@router.post(
    "",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API Key",
    responses={
        201: {"description": "API key created successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def create_api_key(
    data: APIKeyCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> APIKeyCreatedResponse:
    """
    Create a new API key.

    **IMPORTANT**: The API key value is only returned once in this response.
    Store it securely - it cannot be retrieved later.

    API keys provide an alternative to JWT tokens for:
    - CI/CD integrations
    - Service accounts
    - Long-running scripts
    - Automation tools

    **Scopes** (optional):
    - If no scopes specified, key has full access
    - If scopes specified, key is limited to those operations

    **Expiration**:
    - Default: 365 days
    - Set expires_in_days to null for no expiration
    """
    service = APIKeyService(db)
    api_key, plain_key = await service.create_key(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        scopes=data.scopes,
        expires_in_days=data.expires_in_days,
    )
    await db.commit()

    return APIKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        key=plain_key,  # Only time this is returned!
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        message="Store this key securely - it cannot be retrieved again.",
    )


@router.get(
    "",
    response_model=APIKeyListResponse,
    summary="List API Keys",
    responses={
        200: {"description": "API keys retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def list_api_keys(
    db: DbSession,
    current_user: CurrentUser,
) -> APIKeyListResponse:
    """
    List all active API keys for the current user.

    Note: The actual key values are not returned, only prefixes for identification.
    """
    service = APIKeyService(db)
    keys = await service.list_keys(current_user.id)

    return APIKeyListResponse(
        items=[APIKeyResponse.model_validate(k) for k in keys],
        total=len(keys),
    )


@router.get(
    "/{key_id}",
    response_model=APIKeyResponse,
    summary="Get API Key",
    responses={
        200: {"description": "API key retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "API key not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def get_api_key(
    key_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> APIKeyResponse:
    """
    Get details of a specific API key.

    Note: The actual key value is not returned, only the prefix for identification.
    """
    service = APIKeyService(db)
    api_key = await service.get_key_by_id(key_id, current_user.id)

    if not api_key:
        raise NotFoundError(f"API key {key_id} not found", "API_KEY_NOT_FOUND")

    return APIKeyResponse.model_validate(api_key)


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API Key",
    responses={
        204: {"description": "API key revoked successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "API key not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def revoke_api_key(
    key_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """
    Revoke an API key.

    Once revoked, the key can no longer be used for authentication.
    This action cannot be undone.
    """
    service = APIKeyService(db)
    success = await service.revoke_key(key_id, current_user.id)

    if not success:
        raise NotFoundError(f"API key {key_id} not found", "API_KEY_NOT_FOUND")

    await db.commit()
