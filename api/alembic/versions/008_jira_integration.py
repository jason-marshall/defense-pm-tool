"""Week 10: Jira integration tables.

Revision ID: 008
Revises: 007
Create Date: 2026-01-18

Creates:
- jira_integrations: Connection configuration per program
- jira_mappings: WBS/Activity to Issue mappings
- jira_sync_logs: Sync operation audit trail
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "008_jira_integration"
down_revision = "007_variance_and_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # JiraIntegration table - stores connection configuration per program
    op.create_table(
        "jira_integrations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "program_id",
            UUID(as_uuid=True),
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("jira_url", sa.String(255), nullable=False),
        sa.Column("project_key", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("api_token_encrypted", sa.LargeBinary, nullable=False),
        sa.Column("sync_enabled", sa.Boolean, default=True, nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_status", sa.String(20), default="active", nullable=False),
        sa.Column("epic_custom_field", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_jira_integrations_program",
        "jira_integrations",
        ["program_id"],
    )

    # JiraMapping table - maps WBS/Activity to Jira issues
    op.create_table(
        "jira_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "integration_id",
            UUID(as_uuid=True),
            sa.ForeignKey("jira_integrations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column(
            "wbs_id",
            UUID(as_uuid=True),
            sa.ForeignKey("wbs_elements.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "activity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("activities.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("jira_issue_key", sa.String(50), nullable=False),
        sa.Column("jira_issue_id", sa.String(50), nullable=True),
        sa.Column("sync_direction", sa.String(20), default="to_jira", nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_jira_updated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_jira_mappings_integration",
        "jira_mappings",
        ["integration_id"],
    )
    op.create_index(
        "ix_jira_mappings_wbs",
        "jira_mappings",
        ["wbs_id"],
    )
    op.create_index(
        "ix_jira_mappings_activity",
        "jira_mappings",
        ["activity_id"],
    )
    op.create_index(
        "ix_jira_mappings_issue_key",
        "jira_mappings",
        ["jira_issue_key"],
    )

    # Unique constraints for mappings
    op.create_unique_constraint(
        "uq_jira_mapping_wbs",
        "jira_mappings",
        ["integration_id", "entity_type", "wbs_id"],
    )
    op.create_unique_constraint(
        "uq_jira_mapping_activity",
        "jira_mappings",
        ["integration_id", "entity_type", "activity_id"],
    )
    op.create_unique_constraint(
        "uq_jira_mapping_issue",
        "jira_mappings",
        ["integration_id", "jira_issue_key"],
    )

    # JiraSyncLog table - audit trail for sync operations
    op.create_table(
        "jira_sync_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "integration_id",
            UUID(as_uuid=True),
            sa.ForeignKey("jira_integrations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mapping_id",
            UUID(as_uuid=True),
            sa.ForeignKey("jira_mappings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sync_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("items_synced", sa.Integer, default=0, nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_jira_sync_logs_integration",
        "jira_sync_logs",
        ["integration_id"],
    )
    op.create_index(
        "ix_jira_sync_logs_created",
        "jira_sync_logs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("jira_sync_logs")
    op.drop_table("jira_mappings")
    op.drop_table("jira_integrations")
