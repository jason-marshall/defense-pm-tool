"""Resource skills and certification tracking.

Revision ID: 014
Revises: 013
Create Date: 2026-02-07

Adds:
- skills table for skill/certification definitions
- resource_skills table for resource-to-skill mapping
- skill_requirements table for activity skill requirements
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create skill-related tables."""
    # Skills table
    op.create_table(
        "skills",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="Technical"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("requires_certification", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("certification_expiry_months", sa.SmallInteger, nullable=True),
        sa.Column("program_id", UUID(as_uuid=True), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        comment="Skill and certification definitions",
    )

    op.create_index("ix_skills_name", "skills", ["name"])
    op.create_index("ix_skills_code", "skills", ["code"])
    op.create_index("ix_skills_program_id", "skills", ["program_id"])
    op.create_index("ix_skills_category", "skills", ["category"])
    op.create_index("ix_skills_deleted_at", "skills", ["deleted_at"])
    op.create_unique_constraint(
        "uq_skills_program_code",
        "skills",
        ["program_id", "code"],
    )

    # Resource skills table (resource-to-skill mapping)
    op.create_table(
        "resource_skills",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("resource_id", UUID(as_uuid=True), sa.ForeignKey("resources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proficiency_level", sa.SmallInteger, nullable=False, server_default=sa.text("1")),
        sa.Column("is_certified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("certification_date", sa.Date, nullable=True),
        sa.Column("certification_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "proficiency_level >= 1 AND proficiency_level <= 5",
            name="ck_resource_skills_proficiency",
        ),
        comment="Resource-to-skill mapping with proficiency and certification",
    )

    op.create_index("ix_resource_skills_resource_id", "resource_skills", ["resource_id"])
    op.create_index("ix_resource_skills_skill_id", "resource_skills", ["skill_id"])
    op.create_index("ix_resource_skills_deleted_at", "resource_skills", ["deleted_at"])
    op.create_unique_constraint(
        "uq_resource_skills_resource_skill",
        "resource_skills",
        ["resource_id", "skill_id"],
    )

    # Skill requirements table (activity skill requirements)
    op.create_table(
        "skill_requirements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("activity_id", UUID(as_uuid=True), sa.ForeignKey("activities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("required_level", sa.SmallInteger, nullable=False, server_default=sa.text("1")),
        sa.Column("is_mandatory", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "required_level >= 1 AND required_level <= 5",
            name="ck_skill_requirements_level",
        ),
        comment="Activity skill requirements for resource matching",
    )

    op.create_index("ix_skill_requirements_activity_id", "skill_requirements", ["activity_id"])
    op.create_index("ix_skill_requirements_skill_id", "skill_requirements", ["skill_id"])
    op.create_index("ix_skill_requirements_deleted_at", "skill_requirements", ["deleted_at"])
    op.create_unique_constraint(
        "uq_skill_requirements_activity_skill",
        "skill_requirements",
        ["activity_id", "skill_id"],
    )


def downgrade() -> None:
    """Drop skill-related tables."""
    op.drop_table("skill_requirements")
    op.drop_table("resource_skills")
    op.drop_table("skills")
