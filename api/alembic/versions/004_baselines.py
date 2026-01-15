"""Create baselines table for EVMS baseline management.

Revision ID: 004_baselines
Revises: 003_ev_methods
Create Date: 2026-01-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "004_baselines"
down_revision = "003_ev_methods"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create baselines table."""
    op.create_table(
        "baselines",
        # Primary key and audit columns (from Base)
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),

        # Foreign keys
        sa.Column(
            "program_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="FK to parent program",
        ),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="User who created the baseline",
        ),
        sa.Column(
            "approved_by_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="User who approved the baseline",
        ),

        # Basic fields
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Descriptive name for this baseline",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            default=1,
            comment="Version number (auto-incremented per program)",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Optional detailed description",
        ),

        # Snapshot data (JSON)
        sa.Column(
            "schedule_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="JSON snapshot of activities and dependencies",
        ),
        sa.Column(
            "cost_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="JSON snapshot of cost data by WBS",
        ),
        sa.Column(
            "wbs_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="JSON snapshot of WBS hierarchy",
        ),

        # Approval tracking
        sa.Column(
            "is_approved",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether this baseline is approved as PMB",
        ),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when approved",
        ),

        # Summary metrics
        sa.Column(
            "total_bac",
            sa.Numeric(precision=15, scale=2),
            nullable=False,
            server_default="0.00",
            comment="Total Budget at Completion from snapshot",
        ),
        sa.Column(
            "scheduled_finish",
            sa.Date(),
            nullable=True,
            comment="Scheduled completion date from snapshot",
        ),
        sa.Column(
            "activity_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of activities in snapshot",
        ),
        sa.Column(
            "wbs_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of WBS elements in snapshot",
        ),

        # Primary key
        sa.PrimaryKeyConstraint("id"),

        # Foreign key constraints
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
            name="fk_baselines_program_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_baselines_created_by_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"],
            ["users.id"],
            name="fk_baselines_approved_by_id",
            ondelete="SET NULL",
        ),

        # Unique constraints
        sa.UniqueConstraint(
            "program_id",
            "version",
            name="uq_baselines_program_version",
        ),

        # Table comment
        comment="Program baselines for EVMS performance measurement",
    )

    # Create indexes
    op.create_index(
        "ix_baselines_program_id",
        "baselines",
        ["program_id"],
    )
    op.create_index(
        "ix_baselines_is_approved",
        "baselines",
        ["program_id", "is_approved"],
        postgresql_where="is_approved = true AND deleted_at IS NULL",
    )
    op.create_index(
        "ix_baselines_latest",
        "baselines",
        ["program_id", "version"],
    )


def downgrade() -> None:
    """Drop baselines table."""
    op.drop_index("ix_baselines_latest", table_name="baselines")
    op.drop_index("ix_baselines_is_approved", table_name="baselines")
    op.drop_index("ix_baselines_program_id", table_name="baselines")
    op.drop_table("baselines")
