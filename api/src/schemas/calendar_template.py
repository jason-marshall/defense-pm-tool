"""Pydantic schemas for calendar templates.

These schemas handle validation and serialization for calendar template
CRUD operations and API responses.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class CalendarTemplateHolidayBase(BaseModel):
    """Base schema for calendar template holidays."""

    holiday_date: date
    name: str = Field(..., min_length=1, max_length=100)
    recurring_yearly: bool = False


class CalendarTemplateHolidayCreate(CalendarTemplateHolidayBase):
    """Schema for creating a holiday within a template."""

    pass


class CalendarTemplateHolidayUpdate(BaseModel):
    """Schema for updating a holiday."""

    holiday_date: date | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    recurring_yearly: bool | None = None


class CalendarTemplateHolidayResponse(CalendarTemplateHolidayBase):
    """Schema for holiday API responses."""

    id: UUID
    template_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CalendarTemplateBase(BaseModel):
    """Base schema for calendar templates."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    hours_per_day: Decimal = Field(default=Decimal("8.0"), ge=Decimal("0"), le=Decimal("24"))
    working_days: list[int] = Field(default=[1, 2, 3, 4, 5])
    is_default: bool = False

    @field_validator("working_days")
    @classmethod
    def validate_working_days(cls, v: list[int]) -> list[int]:
        """Validate working days are valid day numbers (1-7)."""
        if not v:
            raise ValueError("working_days cannot be empty")
        for day in v:
            if day < 1 or day > 7:
                raise ValueError(f"Invalid day number {day}. Must be 1-7 (Monday-Sunday)")
        # Remove duplicates and sort
        return sorted(set(v))


class CalendarTemplateCreate(CalendarTemplateBase):
    """Schema for creating a calendar template."""

    holidays: list[CalendarTemplateHolidayCreate] = Field(default_factory=list)


class CalendarTemplateUpdate(BaseModel):
    """Schema for updating a calendar template."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    hours_per_day: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("24"))
    working_days: list[int] | None = None
    is_default: bool | None = None

    @field_validator("working_days")
    @classmethod
    def validate_working_days(cls, v: list[int] | None) -> list[int] | None:
        """Validate working days are valid day numbers (1-7)."""
        if v is None:
            return v
        if not v:
            raise ValueError("working_days cannot be empty")
        for day in v:
            if day < 1 or day > 7:
                raise ValueError(f"Invalid day number {day}. Must be 1-7 (Monday-Sunday)")
        return sorted(set(v))


class CalendarTemplateResponse(CalendarTemplateBase):
    """Schema for calendar template API responses."""

    id: UUID
    program_id: UUID
    holidays: list[CalendarTemplateHolidayResponse] = []
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CalendarTemplateListResponse(BaseModel):
    """Schema for paginated calendar template list responses."""

    items: list[CalendarTemplateResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class CalendarTemplateSummary(BaseModel):
    """Minimal template info for dropdowns and references."""

    id: UUID
    name: str
    hours_per_day: Decimal
    working_days: list[int]
    is_default: bool

    model_config = ConfigDict(from_attributes=True)


class ApplyTemplateRequest(BaseModel):
    """Schema for applying a template to resources."""

    resource_ids: list[UUID] = Field(..., min_length=1)
    overwrite_existing: bool = Field(
        default=False,
        description="If True, overwrite existing calendar entries for these resources",
    )
    start_date: date = Field(..., description="Start date for generated calendar entries")
    end_date: date = Field(..., description="End date for generated calendar entries")

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: date, info: ValidationInfo) -> date:
        """Ensure end_date is after start_date."""
        start = info.data.get("start_date") if info.data else None
        if start and v < start:
            raise ValueError("end_date must be on or after start_date")
        return v


class ApplyTemplateResponse(BaseModel):
    """Response from applying a template to resources."""

    template_id: UUID
    resources_updated: int
    calendar_entries_created: int
    start_date: date
    end_date: date
