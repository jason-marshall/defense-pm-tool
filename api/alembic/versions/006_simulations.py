"""Add simulation tables for Monte Carlo analysis.

Revision ID: 006
Revises: 005
Create Date: 2026-01-14

Creates:
- simulation_configs: Monte Carlo simulation configuration
- simulation_results: Simulation execution results

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create simulation_configs table
    op.create_table(
        "simulation_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "program_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="FK to parent program",
        ),
        sa.Column(
            "scenario_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Optional scenario to simulate",
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
            comment="Simulation configuration name",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Detailed description of simulation purpose",
        ),
        sa.Column(
            "iterations",
            sa.Integer(),
            nullable=False,
            server_default="1000",
            comment="Number of Monte Carlo iterations",
        ),
        sa.Column(
            "activity_distributions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="Activity duration distribution parameters",
        ),
        sa.Column(
            "cost_distributions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Cost distribution parameters (optional)",
        ),
        sa.Column(
            "correlation_matrix",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Correlation coefficients between activities (optional)",
        ),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="User who created the simulation config",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
            name="fk_simulation_configs_program_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.id"],
            name="fk_simulation_configs_scenario_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_simulation_configs_created_by_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Monte Carlo simulation configurations",
    )

    # Create indexes for simulation_configs
    op.create_index(
        "ix_simulation_configs_program_id",
        "simulation_configs",
        ["program_id"],
    )
    op.create_index(
        "ix_simulation_configs_scenario_id",
        "simulation_configs",
        ["scenario_id"],
    )
    op.create_index(
        "ix_simulation_configs_program",
        "simulation_configs",
        ["program_id", "deleted_at"],
    )

    # Create simulation_results table
    op.create_table(
        "simulation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "config_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="FK to simulation configuration",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
            comment="Simulation status (pending, running, completed, failed)",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When simulation started",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When simulation completed",
        ),
        sa.Column(
            "iterations_completed",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of iterations completed so far",
        ),
        sa.Column(
            "duration_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Duration distribution: p10, p50, p80, p90, mean, std",
        ),
        sa.Column(
            "cost_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Cost distribution: p10, p50, p80, p90, mean, std",
        ),
        sa.Column(
            "duration_histogram",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Duration histogram (bins and counts)",
        ),
        sa.Column(
            "cost_histogram",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Cost histogram (bins and counts)",
        ),
        sa.Column(
            "activity_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Per-activity statistics (criticality index, etc.)",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error message if simulation failed",
        ),
        sa.Column(
            "random_seed",
            sa.Integer(),
            nullable=True,
            comment="Random seed used (for reproducibility)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["config_id"],
            ["simulation_configs.id"],
            name="fk_simulation_results_config_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Monte Carlo simulation results",
    )

    # Create indexes for simulation_results
    op.create_index(
        "ix_simulation_results_config_id",
        "simulation_results",
        ["config_id"],
    )
    op.create_index(
        "ix_simulation_results_status",
        "simulation_results",
        ["status"],
    )
    op.create_index(
        "ix_simulation_results_config_status",
        "simulation_results",
        ["config_id", "status"],
    )


def downgrade() -> None:
    # Drop simulation_results table
    op.drop_index("ix_simulation_results_config_status", table_name="simulation_results")
    op.drop_index("ix_simulation_results_status", table_name="simulation_results")
    op.drop_index("ix_simulation_results_config_id", table_name="simulation_results")
    op.drop_table("simulation_results")

    # Drop simulation_configs table
    op.drop_index("ix_simulation_configs_program", table_name="simulation_configs")
    op.drop_index("ix_simulation_configs_scenario_id", table_name="simulation_configs")
    op.drop_index("ix_simulation_configs_program_id", table_name="simulation_configs")
    op.drop_table("simulation_configs")
