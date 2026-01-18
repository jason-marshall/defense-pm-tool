"""Week 9: Variance explanations and report audit trail.

Revision ID: 007
Revises: 006
Create Date: 2026-01-17

Creates:
- variance_explanations: Track variance explanations per DFARS
- report_audit: Report generation audit trail
- management_reserve_log: MR change tracking for Format 5
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # VarianceExplanation table - tracks explanations for significant variances
    op.create_table(
        "variance_explanations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "program_id", UUID(as_uuid=True), sa.ForeignKey("programs.id"), nullable=False
        ),
        sa.Column("wbs_id", UUID(as_uuid=True), sa.ForeignKey("wbs.id"), nullable=True),
        sa.Column(
            "period_id", UUID(as_uuid=True), sa.ForeignKey("evms_periods.id"), nullable=True
        ),
        sa.Column(
            "variance_type", sa.String(20), nullable=False
        ),  # 'schedule' or 'cost'
        sa.Column("variance_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("variance_percent", sa.Numeric(8, 4), nullable=False),
        sa.Column("explanation", sa.Text, nullable=False),
        sa.Column("corrective_action", sa.Text, nullable=True),
        sa.Column("expected_resolution", sa.Date, nullable=True),
        sa.Column(
            "created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "ix_variance_explanations_program", "variance_explanations", ["program_id"]
    )
    op.create_index(
        "ix_variance_explanations_period", "variance_explanations", ["period_id"]
    )
    op.create_index(
        "ix_variance_explanations_wbs", "variance_explanations", ["wbs_id"]
    )

    # ReportAudit table - tracks all report generations for audit trail
    op.create_table(
        "report_audit",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_type", sa.String(50), nullable=False
        ),  # 'cpr_format_1', 'cpr_format_3', 'cpr_format_5', etc.
        sa.Column(
            "program_id", UUID(as_uuid=True), sa.ForeignKey("programs.id"), nullable=False
        ),
        sa.Column(
            "generated_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("generated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("parameters", JSONB, nullable=True),  # Report generation parameters
        sa.Column("file_path", sa.String(500), nullable=True),  # Path to generated file
        sa.Column("file_format", sa.String(20), nullable=True),  # 'json', 'html', 'pdf'
        sa.Column("file_size", sa.Integer, nullable=True),  # File size in bytes
        sa.Column("checksum", sa.String(64), nullable=True),  # SHA256 checksum
    )
    op.create_index("ix_report_audit_program", "report_audit", ["program_id"])
    op.create_index("ix_report_audit_type", "report_audit", ["report_type"])
    op.create_index("ix_report_audit_generated_at", "report_audit", ["generated_at"])

    # ManagementReserveLog table - tracks MR changes for CPR Format 5
    op.create_table(
        "management_reserve_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "program_id", UUID(as_uuid=True), sa.ForeignKey("programs.id"), nullable=False
        ),
        sa.Column(
            "period_id", UUID(as_uuid=True), sa.ForeignKey("evms_periods.id"), nullable=True
        ),
        sa.Column("beginning_mr", sa.Numeric(15, 2), nullable=False),
        sa.Column("changes_in", sa.Numeric(15, 2), server_default="0"),
        sa.Column("changes_out", sa.Numeric(15, 2), server_default="0"),
        sa.Column("ending_mr", sa.Numeric(15, 2), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column(
            "approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_mr_log_program", "management_reserve_log", ["program_id"])
    op.create_index("ix_mr_log_period", "management_reserve_log", ["period_id"])


def downgrade() -> None:
    op.drop_table("management_reserve_log")
    op.drop_table("report_audit")
    op.drop_table("variance_explanations")
