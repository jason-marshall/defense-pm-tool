"""Create scenarios and scenario_changes tables.

Revision ID: 005_scenarios
Revises: 004_baselines
Create Date: 2026-01-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "005_scenarios"
down_revision = "004_baselines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create scenarios and scenario_changes tables."""
    # Create scenarios table
    op.create_table(
        "scenarios",
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
            "baseline_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="FK to reference baseline",
        ),
        sa.Column(
            "parent_scenario_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="FK to parent scenario",
        ),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="User who created the scenario",
        ),
        sa.Column(
            "promoted_baseline_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="FK to resulting baseline if promoted",
        ),

        # Basic fields
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Scenario name",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Detailed description",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="draft",
            comment="Status (draft, active, promoted, archived)",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether scenario is actively being used",
        ),

        # JSON data
        sa.Column(
            "changes_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="JSON array of delta changes",
        ),
        sa.Column(
            "results_cache",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Cached CPM calculation results",
        ),

        # Promotion tracking
        sa.Column(
            "promoted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When promoted to baseline",
        ),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
            name="fk_scenarios_program_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["baseline_id"],
            ["baselines.id"],
            name="fk_scenarios_baseline_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parent_scenario_id"],
            ["scenarios.id"],
            name="fk_scenarios_parent_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_scenarios_created_by_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["promoted_baseline_id"],
            ["baselines.id"],
            name="fk_scenarios_promoted_baseline_id",
            ondelete="SET NULL",
        ),

        comment="What-if scenarios for program planning",
    )

    # Create indexes for scenarios
    op.create_index(
        "ix_scenarios_program_id",
        "scenarios",
        ["program_id"],
    )
    op.create_index(
        "ix_scenarios_baseline_id",
        "scenarios",
        ["baseline_id"],
    )
    op.create_index(
        "ix_scenarios_parent_id",
        "scenarios",
        ["parent_scenario_id"],
    )
    op.create_index(
        "ix_scenarios_status",
        "scenarios",
        ["program_id", "status"],
    )
    op.create_index(
        "ix_scenarios_active",
        "scenarios",
        ["program_id", "is_active"],
        postgresql_where="is_active = true AND deleted_at IS NULL",
    )

    # Create scenario_changes table
    op.create_table(
        "scenario_changes",
        # Primary key and audit columns
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

        # Foreign key to scenario
        sa.Column(
            "scenario_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="FK to parent scenario",
        ),

        # Entity identification
        sa.Column(
            "entity_type",
            sa.String(20),
            nullable=False,
            comment="Entity type (activity, dependency, wbs)",
        ),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="ID of entity being changed",
        ),
        sa.Column(
            "entity_code",
            sa.String(100),
            nullable=True,
            comment="Code/identifier of entity",
        ),

        # Change details
        sa.Column(
            "change_type",
            sa.String(20),
            nullable=False,
            comment="Change type (create, update, delete)",
        ),
        sa.Column(
            "field_name",
            sa.String(100),
            nullable=True,
            comment="Field name being changed",
        ),
        sa.Column(
            "old_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Previous value",
        ),
        sa.Column(
            "new_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="New value",
        ),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.id"],
            name="fk_scenario_changes_scenario_id",
            ondelete="CASCADE",
        ),

        comment="Individual changes within scenarios",
    )

    # Create indexes for scenario_changes
    op.create_index(
        "ix_scenario_changes_scenario_id",
        "scenario_changes",
        ["scenario_id"],
    )
    op.create_index(
        "ix_scenario_changes_entity_type",
        "scenario_changes",
        ["entity_type"],
    )
    op.create_index(
        "ix_scenario_changes_entity",
        "scenario_changes",
        ["scenario_id", "entity_type", "entity_id"],
    )


def downgrade() -> None:
    """Drop scenarios and scenario_changes tables."""
    # Drop scenario_changes first (foreign key dependency)
    op.drop_index("ix_scenario_changes_entity", table_name="scenario_changes")
    op.drop_index("ix_scenario_changes_entity_type", table_name="scenario_changes")
    op.drop_index("ix_scenario_changes_scenario_id", table_name="scenario_changes")
    op.drop_table("scenario_changes")

    # Drop scenarios
    op.drop_index("ix_scenarios_active", table_name="scenarios")
    op.drop_index("ix_scenarios_status", table_name="scenarios")
    op.drop_index("ix_scenarios_parent_id", table_name="scenarios")
    op.drop_index("ix_scenarios_baseline_id", table_name="scenarios")
    op.drop_index("ix_scenarios_program_id", table_name="scenarios")
    op.drop_table("scenarios")
