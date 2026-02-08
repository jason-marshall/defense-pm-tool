"""API Key management service."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select

from src.models.api_key import APIKey, generate_api_key

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class APIKeyService:
    """Service for API key management.

    Handles creation, verification, and revocation of API keys.
    Keys are stored securely using SHA-256 hashing.

    Usage:
        service = APIKeyService(session)

        # Create a new key
        api_key, plain_key = await service.create_key(
            user_id=user.id,
            name="CI/CD Pipeline",
            expires_in_days=365,
        )
        # Store plain_key securely - it cannot be retrieved later!

        # Verify a key
        api_key = await service.verify_key(plain_key)
        if api_key:
            user = api_key.user
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the API key service.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key for secure storage.

        Args:
            key: Plain text API key.

        Returns:
            SHA-256 hex digest of the key.
        """
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def extract_prefix(key: str) -> str:
        """Extract prefix from API key for identification.

        Args:
            key: Full API key (dpm_xxxx_secret).

        Returns:
            Key prefix (dpm_xxxx).
        """
        parts = key.split("_")
        if len(parts) >= 2:
            return f"{parts[0]}_{parts[1]}"
        return key[:12]

    async def create_key(
        self,
        user_id: UUID,
        name: str,
        description: str | None = None,
        scopes: list[str] | None = None,
        expires_in_days: int | None = 365,
    ) -> tuple[APIKey, str]:
        """Create a new API key.

        Args:
            user_id: ID of the user who owns this key.
            name: Human-readable name for the key.
            description: Optional description of key purpose.
            scopes: Optional list of allowed scopes.
            expires_in_days: Days until key expires (None = never).

        Returns:
            Tuple of (APIKey model, plain text key).

        Note:
            The plain text key is only returned once and cannot be
            retrieved later. Store it securely!
        """
        # Generate key
        plain_key = generate_api_key()
        prefix = self.extract_prefix(plain_key)
        key_hash = self.hash_key(plain_key)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        # Create model
        api_key = APIKey(
            user_id=str(user_id),
            name=name,
            description=description,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=",".join(scopes) if scopes else None,
            expires_at=expires_at,
        )

        self.session.add(api_key)
        await self.session.flush()

        logger.info(
            "api_key_created",
            user_id=str(user_id),
            key_prefix=prefix,
            name=name,
            expires_at=str(expires_at) if expires_at else "never",
        )

        return api_key, plain_key

    async def verify_key(self, key: str) -> APIKey | None:
        """Verify an API key and return the associated model.

        Args:
            key: Plain text API key to verify.

        Returns:
            APIKey model if valid, None otherwise.

        Note:
            Returns None if key is invalid, expired, or inactive.
            Updates last_used_at timestamp on successful verification.
        """
        prefix = self.extract_prefix(key)
        key_hash = self.hash_key(key)

        # Find by prefix first (indexed), then verify hash
        stmt = select(APIKey).where(
            APIKey.key_prefix == prefix,
            APIKey.is_active == True,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        api_key = result.scalar_one_or_none()

        if not api_key:
            logger.warning("api_key_not_found", prefix=prefix)
            return None

        # Verify hash using constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(api_key.key_hash, key_hash):
            logger.warning("api_key_invalid_hash", prefix=prefix)
            return None

        # Check expiration
        if api_key.is_expired():
            logger.warning("api_key_expired", prefix=prefix)
            return None

        # Update last used timestamp
        api_key.last_used_at = datetime.now(UTC)

        logger.debug("api_key_verified", prefix=prefix, user_id=api_key.user_id)

        return api_key

    async def revoke_key(self, key_id: UUID, user_id: UUID | None = None) -> bool:
        """Revoke an API key.

        Args:
            key_id: ID of the key to revoke.
            user_id: Optional user ID to verify ownership.

        Returns:
            True if key was revoked, False if not found.
        """
        stmt = select(APIKey).where(APIKey.id == str(key_id))
        if user_id:
            stmt = stmt.where(APIKey.user_id == str(user_id))

        result = await self.session.execute(stmt)
        api_key = result.scalar_one_or_none()

        if not api_key:
            return False

        api_key.is_active = False

        logger.info(
            "api_key_revoked",
            key_id=str(key_id),
            prefix=api_key.key_prefix,
            user_id=api_key.user_id,
        )

        return True

    async def list_keys(self, user_id: UUID, include_inactive: bool = False) -> list[APIKey]:
        """List all API keys for a user.

        Args:
            user_id: ID of the user.
            include_inactive: Whether to include revoked keys.

        Returns:
            List of APIKey models.
        """
        stmt = select(APIKey).where(APIKey.user_id == str(user_id))

        if not include_inactive:
            stmt = stmt.where(APIKey.is_active == True)  # noqa: E712

        stmt = stmt.order_by(APIKey.created_at.desc())

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_key_by_id(self, key_id: UUID, user_id: UUID | None = None) -> APIKey | None:
        """Get an API key by ID.

        Args:
            key_id: ID of the key.
            user_id: Optional user ID to verify ownership.

        Returns:
            APIKey model if found, None otherwise.
        """
        stmt = select(APIKey).where(APIKey.id == str(key_id))
        if user_id:
            stmt = stmt.where(APIKey.user_id == str(user_id))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
