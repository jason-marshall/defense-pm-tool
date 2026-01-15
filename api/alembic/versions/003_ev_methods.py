"""Add EV method fields to activities table.

Revision ID: 003_ev_methods
Revises: 002_evms_periods
Create Date: 2026-01-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003_ev_methods"
down_revision = "002_evms_periods"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add EV method columns to activities table."""
    # Add ev_method column with default value
    op.add_column(
        "activities",
        sa.Column(
            "ev_method",
            sa.String(30),
            nullable=False,
            server_default="percent_complete",
            comment="Earned value calculation method",
        ),
    )

    # Add milestones_json column for milestone-weight method
    op.add_column(
        "activities",
        sa.Column(
            "milestones_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Milestone definitions for weighted EV method",
        ),
    )


def downgrade() -> None:
    """Remove EV method columns from activities table."""
    op.drop_column("activities", "milestones_json")
    op.drop_column("activities", "ev_method")
