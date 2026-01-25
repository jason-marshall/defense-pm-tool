"""Add API keys table for service account authentication.

Revision ID: 009
Revises: 008
Create Date: 2026-01-24

Creates:
- api_keys: API key storage with hashed values
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create api_keys table."""
    op.create_table(
        "api_keys",
        # Primary key
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        # Foreign key to users
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Key identification
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        # Security - only store prefix and hash
        sa.Column("key_prefix", sa.String(20), nullable=False, unique=True),
        sa.Column("key_hash", sa.String(128), nullable=False),
        # Permissions
        sa.Column("scopes", sa.Text, nullable=True),
        # Lifecycle
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            onupdate=sa.func.now(),
            nullable=True,
        ),
    )

    # Indexes for efficient lookups
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"], unique=True)
    op.create_index("ix_api_keys_is_active", "api_keys", ["is_active"])


def downgrade() -> None:
    """Drop api_keys table."""
    op.drop_index("ix_api_keys_is_active", table_name="api_keys")
    op.drop_index("ix_api_keys_key_prefix", table_name="api_keys")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")
