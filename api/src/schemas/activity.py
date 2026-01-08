"""Pydantic schemas for Activity."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from src.schemas.base import BaseSchema, IDMixin, TimestampMixin


class ActivityBase(BaseSchema):
    """Base schema for Activity."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    duration: int = Field(..., ge=0, description="Duration in working days")
    wbs_element_id: UUID | None = None
    budgeted_cost: Decimal = Field(default=Decimal("0.00"), ge=0)


class ActivityCreate(ActivityBase):
    """Schema for creating an Activity."""

    program_id: UUID


class ActivityUpdate(BaseSchema):
    """Schema for updating an Activity."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    duration: int | None = Field(default=None, ge=0)
    remaining_duration: int | None = Field(default=None, ge=0)
    actual_start: date | None = None
    actual_finish: date | None = None
    percent_complete: Decimal | None = Field(default=None, ge=0, le=100)
    budgeted_cost: Decimal | None = Field(default=None, ge=0)
    actual_cost: Decimal | None = Field(default=None, ge=0)
    wbs_element_id: UUID | None = None

    @field_validator("percent_complete")
    @classmethod
    def validate_percent(cls, v: Decimal | None) -> Decimal | None:
        """Validate percent complete is between 0 and 100."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError("percent_complete must be between 0 and 100")
        return v


class ScheduleResult(BaseSchema):
    """Schema for CPM schedule calculation results."""

    activity_id: UUID
    early_start: int  # Days from project start
    early_finish: int
    late_start: int
    late_finish: int
    total_float: int
    free_float: int
    is_critical: bool


class ActivityResponse(ActivityBase, IDMixin, TimestampMixin):
    """Schema for Activity response."""

    program_id: UUID
    remaining_duration: int | None = None
    early_start: date | None = None
    early_finish: date | None = None
    late_start: date | None = None
    late_finish: date | None = None
    actual_start: date | None = None
    actual_finish: date | None = None
    total_float: int | None = None
    free_float: int | None = None
    percent_complete: Decimal = Decimal("0.00")
    actual_cost: Decimal = Decimal("0.00")
    is_critical: bool = False


class ActivityListResponse(BaseSchema):
    """Schema for paginated list of activities."""

    items: list[ActivityResponse]
    total: int
    page: int
    page_size: int
