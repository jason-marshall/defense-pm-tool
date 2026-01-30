"""Resource pools for cross-program resource sharing.

Revision ID: 013
Revises: 010
Create Date: 2026-01-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create resource pool tables."""
    # Create pool_access_level enum
    pool_access_level = postgresql.ENUM(
        "OWNER",
        "ADMIN",
        "MEMBER",
        "VIEWER",
        name="pool_access_level",
        create_type=True,
    )
    pool_access_level.create(op.get_bind())

    # Create resource_pools table
    op.create_table(
        "resource_pools",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "owner_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_resource_pools_code"),
        comment="Shared resource pools across programs",
    )
    op.create_index("ix_resource_pools_owner_id", "resource_pools", ["owner_id"])
    op.create_index("ix_resource_pools_is_active", "resource_pools", ["is_active"])

    # Create resource_pool_members table
    op.create_table(
        "resource_pool_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "pool_id",
            sa.UUID(),
            sa.ForeignKey("resource_pools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "resource_id",
            sa.UUID(),
            sa.ForeignKey("resources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "allocation_percentage",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            default=100.0,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pool_id", "resource_id", name="uq_resource_pool_members_pool_resource"
        ),
        sa.CheckConstraint(
            "allocation_percentage >= 0 AND allocation_percentage <= 100",
            name="ck_resource_pool_members_allocation",
        ),
        comment="Resources belonging to pools",
    )
    op.create_index("ix_resource_pool_members_pool_id", "resource_pool_members", ["pool_id"])
    op.create_index(
        "ix_resource_pool_members_resource_id", "resource_pool_members", ["resource_id"]
    )

    # Create resource_pool_access table
    op.create_table(
        "resource_pool_access",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "pool_id",
            sa.UUID(),
            sa.ForeignKey("resource_pools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "program_id",
            sa.UUID(),
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "access_level",
            pool_access_level,
            nullable=False,
            default="VIEWER",
        ),
        sa.Column(
            "granted_by",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pool_id", "program_id", name="uq_resource_pool_access_pool_program"),
        comment="Program access to resource pools",
    )
    op.create_index("ix_resource_pool_access_pool_id", "resource_pool_access", ["pool_id"])
    op.create_index("ix_resource_pool_access_program_id", "resource_pool_access", ["program_id"])


def downgrade() -> None:
    """Drop resource pool tables."""
    op.drop_table("resource_pool_access")
    op.drop_table("resource_pool_members")
    op.drop_table("resource_pools")

    # Drop enum
    pool_access_level = postgresql.ENUM(
        "OWNER",
        "ADMIN",
        "MEMBER",
        "VIEWER",
        name="pool_access_level",
    )
    pool_access_level.drop(op.get_bind())
