"""Add EVMS period tracking tables.

Revision ID: 002_evms_periods
Revises: 001_initial_schema
Create Date: 2026-01-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002_evms_periods"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create EVMS period tracking tables."""
    # Create period_status enum
    period_status_enum = postgresql.ENUM(
        "draft",
        "submitted",
        "approved",
        "rejected",
        name="period_status",
        create_type=False,  # We create it explicitly below
    )
    period_status_enum.create(op.get_bind(), checkfirst=True)

    # Create evms_periods table
    op.create_table(
        "evms_periods",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "program_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("period_name", sa.String(100), nullable=False),
        sa.Column(
            "status",
            period_status_enum,
            server_default="draft",
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "cumulative_bcws",
            sa.Numeric(precision=15, scale=2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "cumulative_bcwp",
            sa.Numeric(precision=15, scale=2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "cumulative_acwp",
            sa.Numeric(precision=15, scale=2),
            server_default="0.00",
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "program_id",
            "period_start",
            "period_end",
            name="uq_evms_periods_program_dates",
        ),
        comment="EVMS reporting periods",
    )

    # Create indexes for evms_periods
    op.create_index(
        "ix_evms_periods_program_id",
        "evms_periods",
        ["program_id"],
    )
    op.create_index(
        "ix_evms_periods_period_start",
        "evms_periods",
        ["period_start"],
    )
    op.create_index(
        "ix_evms_periods_period_end",
        "evms_periods",
        ["period_end"],
    )
    op.create_index(
        "ix_evms_periods_status",
        "evms_periods",
        ["status"],
    )
    op.create_index(
        "ix_evms_periods_program_status",
        "evms_periods",
        ["program_id", "status"],
    )

    # Create evms_period_data table
    op.create_table(
        "evms_period_data",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "period_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "wbs_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "bcws",
            sa.Numeric(precision=15, scale=2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "bcwp",
            sa.Numeric(precision=15, scale=2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "acwp",
            sa.Numeric(precision=15, scale=2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "cumulative_bcws",
            sa.Numeric(precision=15, scale=2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "cumulative_bcwp",
            sa.Numeric(precision=15, scale=2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "cumulative_acwp",
            sa.Numeric(precision=15, scale=2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "cv",
            sa.Numeric(precision=15, scale=2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "sv",
            sa.Numeric(precision=15, scale=2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "cpi",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
        sa.Column(
            "spi",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["period_id"],
            ["evms_periods.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["wbs_id"],
            ["wbs_elements.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "period_id",
            "wbs_id",
            name="uq_evms_period_data_period_wbs",
        ),
        comment="EVMS data per WBS element per period",
    )

    # Create indexes for evms_period_data
    op.create_index(
        "ix_evms_period_data_period_id",
        "evms_period_data",
        ["period_id"],
    )
    op.create_index(
        "ix_evms_period_data_wbs_id",
        "evms_period_data",
        ["wbs_id"],
    )
    op.create_index(
        "ix_evms_period_data_wbs",
        "evms_period_data",
        ["wbs_id", "period_id"],
    )


def downgrade() -> None:
    """Remove EVMS period tracking tables."""
    # Drop evms_period_data table
    op.drop_index("ix_evms_period_data_wbs", table_name="evms_period_data")
    op.drop_index("ix_evms_period_data_wbs_id", table_name="evms_period_data")
    op.drop_index("ix_evms_period_data_period_id", table_name="evms_period_data")
    op.drop_table("evms_period_data")

    # Drop evms_periods table
    op.drop_index("ix_evms_periods_program_status", table_name="evms_periods")
    op.drop_index("ix_evms_periods_status", table_name="evms_periods")
    op.drop_index("ix_evms_periods_period_end", table_name="evms_periods")
    op.drop_index("ix_evms_periods_period_start", table_name="evms_periods")
    op.drop_index("ix_evms_periods_program_id", table_name="evms_periods")
    op.drop_table("evms_periods")

    # Drop period_status enum
    period_status_enum = postgresql.ENUM(
        "draft",
        "submitted",
        "approved",
        "rejected",
        name="period_status",
    )
    period_status_enum.drop(op.get_bind(), checkfirst=True)
