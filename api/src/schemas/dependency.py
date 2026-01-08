"""Pydantic schemas for Dependency."""

from uuid import UUID

from pydantic import Field, field_validator

from src.models.dependency import DependencyType
from src.schemas.base import BaseSchema, IDMixin, TimestampMixin


class DependencyBase(BaseSchema):
    """Base schema for Dependency."""

    predecessor_id: UUID
    successor_id: UUID
    dependency_type: DependencyType = Field(default=DependencyType.FS)
    lag: int = Field(
        default=0,
        description="Lag in working days (positive=delay, negative=lead)",
    )

    @field_validator("successor_id")
    @classmethod
    def predecessor_not_equal_successor(cls, v: UUID, info) -> UUID:
        """Validate that predecessor and successor are different."""
        if "predecessor_id" in info.data and v == info.data["predecessor_id"]:
            raise ValueError("An activity cannot depend on itself")
        return v


class DependencyCreate(DependencyBase):
    """Schema for creating a Dependency."""

    pass


class DependencyResponse(DependencyBase, IDMixin, TimestampMixin):
    """Schema for Dependency response."""

    pass


class DependencyListResponse(BaseSchema):
    """Schema for list of dependencies."""

    items: list[DependencyResponse]
    total: int
