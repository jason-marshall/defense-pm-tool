"""Pydantic schemas for Skill, ResourceSkill, and SkillRequirement.

Provides validation and serialization for resource skill tracking:
- Skill: Skill/certification definitions
- ResourceSkill: Resource-to-skill proficiency mapping
- SkillRequirement: Activity skill requirements
"""

from __future__ import annotations

import re
from datetime import date, datetime  # noqa: TC003 - Required at runtime for Pydantic
from typing import Annotated
from uuid import UUID  # noqa: TC003 - Required at runtime for Pydantic

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Valid skill categories
SKILL_CATEGORIES = ("Technical", "Management", "Certification", "Safety")


# =============================================================================
# Skill Schemas
# =============================================================================


class SkillBase(BaseModel):
    """Base schema for skill with validation."""

    name: Annotated[str, Field(min_length=1, max_length=100, description="Skill name")]
    code: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            pattern=r"^[A-Z0-9\-_]+$",
            description="Unique code (uppercase alphanumeric, hyphens, underscores)",
        ),
    ]
    category: Annotated[
        str,
        Field(
            default="Technical",
            max_length=50,
            description="Skill category",
        ),
    ]
    description: str | None = Field(default=None, description="Detailed description")
    is_active: bool = Field(default=True, description="Whether skill is active")
    requires_certification: bool = Field(
        default=False, description="Whether formal certification is needed"
    )
    certification_expiry_months: Annotated[
        int | None,
        Field(default=None, ge=1, le=120, description="Months until certification expires"),
    ] = None

    @field_validator("code", mode="before")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        """Convert code to uppercase."""
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("code", mode="after")
    @classmethod
    def validate_code_pattern(cls, v: str) -> str:
        """Validate code matches required pattern."""
        if not re.match(r"^[A-Z0-9\-_]+$", v):
            msg = "Code must contain only uppercase letters, numbers, hyphens, and underscores"
            raise ValueError(msg)
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category is one of the allowed values."""
        if v not in SKILL_CATEGORIES:
            msg = f"Category must be one of: {', '.join(SKILL_CATEGORIES)}"
            raise ValueError(msg)
        return v


class SkillCreate(SkillBase):
    """Schema for creating a new skill."""

    program_id: UUID | None = Field(default=None, description="Program ID (NULL = global skill)")


class SkillUpdate(BaseModel):
    """Schema for updating a skill. All fields optional."""

    name: Annotated[str | None, Field(min_length=1, max_length=100)] = None
    code: Annotated[str | None, Field(min_length=1, max_length=50)] = None
    category: Annotated[str | None, Field(max_length=50)] = None
    description: str | None = None
    is_active: bool | None = None
    requires_certification: bool | None = None
    certification_expiry_months: Annotated[int | None, Field(ge=1, le=120)] = None

    @field_validator("code", mode="before")
    @classmethod
    def uppercase_code(cls, v: str | None) -> str | None:
        """Convert code to uppercase if provided."""
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        """Validate category if provided."""
        if v is not None and v not in SKILL_CATEGORIES:
            msg = f"Category must be one of: {', '.join(SKILL_CATEGORIES)}"
            raise ValueError(msg)
        return v


class SkillResponse(SkillBase):
    """Schema for skill response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None


class SkillListResponse(BaseModel):
    """Paginated list of skills."""

    items: list[SkillResponse]
    total: int = Field(ge=0, description="Total number of skills")
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Items per page")


# =============================================================================
# Resource Skill Schemas
# =============================================================================


class ResourceSkillCreate(BaseModel):
    """Schema for assigning a skill to a resource."""

    skill_id: UUID = Field(description="Skill to assign")
    proficiency_level: Annotated[
        int,
        Field(default=1, ge=1, le=5, description="Proficiency level (1=Novice, 5=Expert)"),
    ]
    is_certified: bool = Field(default=False, description="Whether resource is certified")
    certification_date: date | None = Field(
        default=None, description="Date certification was obtained"
    )
    notes: str | None = Field(default=None, max_length=1000, description="Additional notes")


class ResourceSkillUpdate(BaseModel):
    """Schema for updating a resource skill."""

    proficiency_level: Annotated[int | None, Field(ge=1, le=5)] = None
    is_certified: bool | None = None
    certification_date: date | None = None
    notes: str | None = None


class ResourceSkillResponse(BaseModel):
    """Schema for resource skill response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resource_id: UUID
    skill_id: UUID
    proficiency_level: int
    is_certified: bool
    certification_date: date | None = None
    certification_expires_at: datetime | None = None
    verified_by: UUID | None = None
    verified_at: datetime | None = None
    notes: str | None = None
    skill: SkillResponse | None = None


# =============================================================================
# Skill Requirement Schemas
# =============================================================================


class SkillRequirementCreate(BaseModel):
    """Schema for adding a skill requirement to an activity."""

    skill_id: UUID = Field(description="Required skill")
    required_level: Annotated[
        int,
        Field(default=1, ge=1, le=5, description="Minimum proficiency level required"),
    ]
    is_mandatory: bool = Field(default=True, description="Whether requirement is mandatory")


class SkillRequirementResponse(BaseModel):
    """Schema for skill requirement response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    activity_id: UUID
    skill_id: UUID
    required_level: int
    is_mandatory: bool
    skill: SkillResponse | None = None
