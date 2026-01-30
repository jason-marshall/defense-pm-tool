"""Add calendar templates and enhance calendar support.

Revision ID: 012_calendar_templates
Revises: 010_resources
Create Date: 2026-02-01

NOTE: This migration runs PARALLEL with 011_resource_costs (Week 17).
Both migrations have 010_resources as parent. Alembic handles this via
multiple heads that merge in the next migration.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

# revision identifiers, used by Alembic.
revision = "012_calendar_templates"
down_revision = "010_resources"  # Same parent as Week 17's migration
branch_labels = ("calendar",)  # Branch label for parallel development
depends_on = None


def upgrade() -> None:
    """Create calendar template tables and enhance calendar support."""
    # Create calendar templates table
    op.create_table(
        "resource_calendar_templates",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "program_id",
            UUID(as_uuid=True),
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "hours_per_day",
            sa.Numeric(precision=4, scale=2),
            nullable=False,
            server_default="8.0",
        ),
        sa.Column(
            "working_days",
            ARRAY(sa.Integer),
            nullable=False,
            server_default="{1,2,3,4,5}",
        ),  # Mon-Fri (1=Monday, 7=Sunday)
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create template holidays table
    op.create_table(
        "calendar_template_holidays",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("resource_calendar_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("holiday_date", sa.Date, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "recurring_yearly", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Add template reference to resources
    op.add_column(
        "resources",
        sa.Column(
            "calendar_template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("resource_calendar_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Add source tracking to resource_calendars
    op.add_column(
        "resource_calendars",
        sa.Column("source", sa.String(20), nullable=True, server_default="manual"),
    )
    op.add_column(
        "resource_calendars",
        sa.Column("import_id", UUID(as_uuid=True), nullable=True),
    )

    # Indexes
    op.create_index(
        "ix_calendar_templates_program_id",
        "resource_calendar_templates",
        ["program_id"],
    )
    op.create_index(
        "ix_calendar_templates_deleted_at",
        "resource_calendar_templates",
        ["deleted_at"],
    )
    op.create_index(
        "ix_calendar_template_holidays_template_id",
        "calendar_template_holidays",
        ["template_id"],
    )
    op.create_index(
        "ix_calendar_template_holidays_date",
        "calendar_template_holidays",
        ["holiday_date"],
    )
    op.create_index(
        "ix_resources_calendar_template_id",
        "resources",
        ["calendar_template_id"],
    )


def downgrade() -> None:
    """Remove calendar template tables and columns."""
    op.drop_index("ix_resources_calendar_template_id", table_name="resources")
    op.drop_index(
        "ix_calendar_template_holidays_date", table_name="calendar_template_holidays"
    )
    op.drop_index(
        "ix_calendar_template_holidays_template_id",
        table_name="calendar_template_holidays",
    )
    op.drop_index(
        "ix_calendar_templates_deleted_at", table_name="resource_calendar_templates"
    )
    op.drop_index(
        "ix_calendar_templates_program_id", table_name="resource_calendar_templates"
    )
    op.drop_column("resource_calendars", "import_id")
    op.drop_column("resource_calendars", "source")
    op.drop_column("resources", "calendar_template_id")
    op.drop_table("calendar_template_holidays")
    op.drop_table("resource_calendar_templates")
