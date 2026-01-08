"""Pydantic schemas for Program."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from src.schemas.base import BaseSchema, IDMixin, TimestampMixin


class ProgramBase(BaseSchema):
    """Base schema for Program."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    planned_start_date: date
    planned_end_date: date
    budget_at_completion: Decimal = Field(default=Decimal("0.00"), ge=0)
    contract_number: str | None = Field(default=None, max_length=100)
    contract_type: str | None = Field(default=None, max_length=50)

    @field_validator("planned_end_date")
    @classmethod
    def end_date_after_start(cls, v: date, info) -> date:
        """Validate that end date is after start date."""
        if "planned_start_date" in info.data and v < info.data["planned_start_date"]:
            raise ValueError("planned_end_date must be after planned_start_date")
        return v


class ProgramCreate(ProgramBase):
    """Schema for creating a Program."""

    pass


class ProgramUpdate(BaseSchema):
    """Schema for updating a Program."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    actual_start_date: date | None = None
    actual_end_date: date | None = None
    budget_at_completion: Decimal | None = Field(default=None, ge=0)
    contract_number: str | None = Field(default=None, max_length=100)
    contract_type: str | None = Field(default=None, max_length=50)


class ProgramResponse(ProgramBase, IDMixin, TimestampMixin):
    """Schema for Program response."""

    actual_start_date: date | None = None
    actual_end_date: date | None = None


class ProgramListResponse(BaseSchema):
    """Schema for paginated list of programs."""

    items: list[ProgramResponse]
    total: int
    page: int
    page_size: int
