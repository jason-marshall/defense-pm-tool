"""API Key model for service account authentication."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.user import User


def generate_api_key_prefix() -> str:
    """Generate a readable prefix for API keys.

    Returns:
        String prefix like 'dpm_a1b2c3d4'
    """
    return f"dpm_{secrets.token_hex(4)}"


def generate_api_key() -> str:
    """Generate a secure API key (prefix_secret).

    Returns:
        Full API key like 'dpm_a1b2c3d4_<48-char-hex-secret>'
    """
    prefix = generate_api_key_prefix()
    # Use token_hex to avoid underscores in the secret part
    secret = secrets.token_hex(24)
    return f"{prefix}_{secret}"


class APIKey(Base):
    """API Key for service account authentication.

    API keys provide an alternative to JWT tokens for:
    - CI/CD integrations
    - Service accounts
    - Long-running scripts
    - Automation tools

    Security:
    - Keys are stored as hashed values (only prefix visible)
    - Plain text key is only returned once at creation
    - Keys can have scopes to limit access
    - Keys can be set to expire

    Attributes:
        user_id: Owner of the API key
        name: Human-readable name for the key
        description: Optional description of key purpose
        key_prefix: Visible prefix for identification (e.g., 'dpm_a1b2c3d4')
        key_hash: SHA-256 hash of the full key
        scopes: Comma-separated list of allowed scopes
        is_active: Whether key is currently active
        expires_at: Optional expiration timestamp
        last_used_at: Last time the key was used
    """

    __tablename__ = "api_keys"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Only store prefix (for identification) and hash (for verification)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    # Permissions and scope
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)  # Comma-separated

    # Lifecycle
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="api_keys")

    def is_expired(self) -> bool:
        """Check if the API key has expired.

        Returns:
            True if key has expired, False otherwise.
        """
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired).

        Returns:
            True if key is active and not expired.
        """
        return self.is_active and not self.is_expired()

    def get_scopes(self) -> list[str]:
        """Get list of scopes for this key.

        Returns:
            List of scope strings, or empty list if no scopes.
        """
        if not self.scopes:
            return []
        return [s.strip() for s in self.scopes.split(",") if s.strip()]

    def has_scope(self, scope: str) -> bool:
        """Check if key has a specific scope.

        Args:
            scope: The scope to check for.

        Returns:
            True if key has the scope or has no scope restrictions.
        """
        scopes = self.get_scopes()
        # If no scopes defined, key has full access
        if not scopes:
            return True
        return scope in scopes
