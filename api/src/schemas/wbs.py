"""Pydantic schemas for WBS Element."""

from decimal import Decimal
from uuid import UUID

from pydantic import Field

from src.schemas.base import BaseSchema, IDMixin, TimestampMixin


class WBSElementBase(BaseSchema):
    """Base schema for WBS Element."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    budgeted_cost: Decimal = Field(default=Decimal("0.00"), ge=0)


class WBSElementCreate(WBSElementBase):
    """Schema for creating a WBS Element."""

    program_id: UUID
    parent_id: UUID | None = None


class WBSElementUpdate(BaseSchema):
    """Schema for updating a WBS Element."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    budgeted_cost: Decimal | None = Field(default=None, ge=0)


class WBSElementResponse(WBSElementBase, IDMixin, TimestampMixin):
    """Schema for WBS Element response."""

    program_id: UUID
    parent_id: UUID | None = None
    path: str
    level: int


class WBSElementTreeResponse(WBSElementResponse):
    """Schema for WBS Element with children (tree structure)."""

    children: list["WBSElementTreeResponse"] = []


class WBSListResponse(BaseSchema):
    """Schema for list of WBS elements."""

    items: list[WBSElementResponse]
    total: int
