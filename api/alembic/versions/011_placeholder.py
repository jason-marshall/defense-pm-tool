"""Placeholder migration to maintain sequential numbering.

Revision ID: 011_placeholder
Revises: 010_resource_costs
Create Date: 2026-02-08

NOTE: This is a no-op migration that fills the numbering gap between
010_resource_costs and 012_calendar_templates. Weeks 17-20 were developed
in parallel branches. This placeholder maintains a clean sequential chain.
"""

from collections.abc import Sequence

from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "011_placeholder"
down_revision: str | None = "010_resource_costs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op placeholder migration."""
    pass


def downgrade() -> None:
    """No-op placeholder migration."""
    pass
