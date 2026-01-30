"""Add resource cost tracking fields.

Revision ID: 010_resource_costs
Revises: 009_api_keys
Create Date: 2026-02-XX

Adds:
- Material quantity fields to resources
- Cost tracking fields to resource_assignments
- resource_cost_entries table for detailed tracking
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "010_resource_costs"
down_revision = "009_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add resource cost and material quantity tracking."""
    # Add material quantity fields to resources
    op.add_column(
        "resources",
        sa.Column(
            "quantity_unit",
            sa.String(50),
            nullable=True,
            comment="Unit of measurement for materials (e.g., 'units', 'kg', 'meters')",
        ),
    )
    op.add_column(
        "resources",
        sa.Column(
            "unit_cost",
            sa.Numeric(12, 2),
            nullable=True,
            comment="Cost per unit for MATERIAL type resources",
        ),
    )
    op.add_column(
        "resources",
        sa.Column(
            "quantity_available",
            sa.Numeric(15, 2),
            nullable=True,
            comment="Total available quantity for MATERIAL type",
        ),
    )

    # Add cost tracking fields to resource_assignments
    op.add_column(
        "resource_assignments",
        sa.Column(
            "planned_hours",
            sa.Numeric(10, 2),
            nullable=True,
            comment="Planned hours for this assignment",
        ),
    )
    op.add_column(
        "resource_assignments",
        sa.Column(
            "actual_hours",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
            comment="Actual hours worked",
        ),
    )
    op.add_column(
        "resource_assignments",
        sa.Column(
            "planned_cost",
            sa.Numeric(15, 2),
            nullable=True,
            comment="Planned cost (planned_hours * cost_rate)",
        ),
    )
    op.add_column(
        "resource_assignments",
        sa.Column(
            "actual_cost",
            sa.Numeric(15, 2),
            nullable=False,
            server_default="0",
            comment="Actual cost incurred",
        ),
    )

    # Add material quantity fields to resource_assignments
    op.add_column(
        "resource_assignments",
        sa.Column(
            "quantity_assigned",
            sa.Numeric(15, 2),
            nullable=True,
            comment="Quantity assigned for MATERIAL type",
        ),
    )
    op.add_column(
        "resource_assignments",
        sa.Column(
            "quantity_consumed",
            sa.Numeric(15, 2),
            nullable=False,
            server_default="0",
            comment="Quantity consumed for MATERIAL type",
        ),
    )

    # Create resource_cost_entries table for detailed cost tracking
    op.create_table(
        "resource_cost_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "assignment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("resource_assignments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column(
            "hours_worked",
            sa.Numeric(6, 2),
            nullable=False,
            server_default="0",
            comment="Hours worked on this date",
        ),
        sa.Column(
            "cost_incurred",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
            comment="Cost incurred on this date",
        ),
        sa.Column(
            "quantity_used",
            sa.Numeric(15, 2),
            nullable=True,
            comment="Quantity used for MATERIAL type resources",
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Indexes for resource_cost_entries
    op.create_index(
        "ix_resource_cost_entries_assignment_id",
        "resource_cost_entries",
        ["assignment_id"],
    )
    op.create_index(
        "ix_resource_cost_entries_entry_date",
        "resource_cost_entries",
        ["entry_date"],
    )
    op.create_index(
        "ix_resource_cost_entries_assignment_date",
        "resource_cost_entries",
        ["assignment_id", "entry_date"],
    )


def downgrade() -> None:
    """Remove resource cost tracking."""
    # Drop resource_cost_entries table
    op.drop_index("ix_resource_cost_entries_assignment_date")
    op.drop_index("ix_resource_cost_entries_entry_date")
    op.drop_index("ix_resource_cost_entries_assignment_id")
    op.drop_table("resource_cost_entries")

    # Remove columns from resource_assignments
    op.drop_column("resource_assignments", "quantity_consumed")
    op.drop_column("resource_assignments", "quantity_assigned")
    op.drop_column("resource_assignments", "actual_cost")
    op.drop_column("resource_assignments", "planned_cost")
    op.drop_column("resource_assignments", "actual_hours")
    op.drop_column("resource_assignments", "planned_hours")

    # Remove columns from resources
    op.drop_column("resources", "quantity_available")
    op.drop_column("resources", "unit_cost")
    op.drop_column("resources", "quantity_unit")
