"""Skill and certification models for resource skills tracking."""

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.activity import Activity
    from src.models.program import Program
    from src.models.resource import Resource
    from src.models.user import User


class Skill(Base):
    """
    Represents a skill or certification definition.

    Skills can be global (program_id=NULL) or program-specific.
    When requires_certification is True, resources must provide
    certification proof and the certification can expire.

    Attributes:
        name: Skill name/description
        code: Unique skill code within program (or globally if no program)
        category: Skill category (Technical, Management, Certification, Safety)
        description: Detailed description
        is_active: Whether skill is currently active
        requires_certification: Whether formal certification is needed
        certification_expiry_months: Months until certification expires
        program_id: FK to program (NULL = global skill)
    """

    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Skill name/description",
    )

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Unique skill code within program",
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Technical",
        comment="Skill category (Technical, Management, Certification, Safety)",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed skill description",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether skill is currently active",
    )

    requires_certification: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether formal certification is needed",
    )

    certification_expiry_months: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Months until certification expires (NULL = no expiry)",
    )

    program_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="FK to program (NULL = global skill)",
    )

    # Relationships
    program: Mapped["Program | None"] = relationship(
        "Program",
        lazy="joined",
    )

    resource_skills: Mapped[list["ResourceSkill"]] = relationship(
        "ResourceSkill",
        back_populates="skill",
        cascade="all, delete-orphan",
    )

    skill_requirements: Mapped[list["SkillRequirement"]] = relationship(
        "SkillRequirement",
        back_populates="skill",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("program_id", "code", name="uq_skills_program_code"),
        Index(
            "ix_skills_active",
            "is_active",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"comment": "Skill and certification definitions"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<Skill(id={self.id}, code={self.code!r}, name={self.name!r}, "
            f"category={self.category!r})>"
        )


class ResourceSkill(Base):
    """
    Represents a resource's proficiency in a skill.

    Maps resources to skills with proficiency levels (1-5) and
    optional certification tracking.

    Attributes:
        resource_id: FK to resource
        skill_id: FK to skill
        proficiency_level: 1 (Novice) to 5 (Expert)
        is_certified: Whether resource has valid certification
        certification_date: Date certification was obtained
        certification_expires_at: When certification expires
        verified_by: User who verified the skill/certification
        verified_at: When verification occurred
        notes: Additional notes
    """

    __tablename__ = "resource_skills"

    resource_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to resource",
    )

    skill_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to skill",
    )

    proficiency_level: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
        comment="Proficiency level 1 (Novice) to 5 (Expert)",
    )

    is_certified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether resource has valid certification",
    )

    certification_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Date certification was obtained",
    )

    certification_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When certification expires",
    )

    verified_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who verified the skill/certification",
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When verification occurred",
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes",
    )

    # Relationships
    resource: Mapped["Resource"] = relationship(
        "Resource",
        back_populates="skills",
    )

    skill: Mapped["Skill"] = relationship(
        "Skill",
        back_populates="resource_skills",
        lazy="joined",
    )

    verifier: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[verified_by],
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint(
            "resource_id",
            "skill_id",
            name="uq_resource_skills_resource_skill",
        ),
        CheckConstraint(
            "proficiency_level >= 1 AND proficiency_level <= 5",
            name="ck_resource_skills_proficiency",
        ),
        Index(
            "ix_resource_skills_certified",
            "skill_id",
            "is_certified",
            postgresql_where=text("deleted_at IS NULL AND is_certified = true"),
        ),
        {"comment": "Resource-to-skill mapping with proficiency and certification"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<ResourceSkill(id={self.id}, resource_id={self.resource_id}, "
            f"skill_id={self.skill_id}, level={self.proficiency_level})>"
        )


class SkillRequirement(Base):
    """
    Represents a skill requirement for an activity.

    Activities can require specific skills at minimum proficiency levels.
    Mandatory requirements must be met; optional requirements are preferred.

    Attributes:
        activity_id: FK to activity
        skill_id: FK to required skill
        required_level: Minimum proficiency level (1-5)
        is_mandatory: Whether requirement must be met
    """

    __tablename__ = "skill_requirements"

    activity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to activity",
    )

    skill_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to required skill",
    )

    required_level: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
        comment="Minimum proficiency level (1-5)",
    )

    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether requirement must be met",
    )

    # Relationships
    activity: Mapped["Activity"] = relationship(
        "Activity",
        back_populates="skill_requirements",
    )

    skill: Mapped["Skill"] = relationship(
        "Skill",
        back_populates="skill_requirements",
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint(
            "activity_id",
            "skill_id",
            name="uq_skill_requirements_activity_skill",
        ),
        CheckConstraint(
            "required_level >= 1 AND required_level <= 5",
            name="ck_skill_requirements_level",
        ),
        {"comment": "Activity skill requirements for resource matching"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<SkillRequirement(id={self.id}, activity_id={self.activity_id}, "
            f"skill_id={self.skill_id}, level={self.required_level})>"
        )
