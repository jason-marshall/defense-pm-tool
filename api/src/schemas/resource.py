"""Pydantic schemas for Resource, ResourceAssignment, and ResourceCalendar.

Provides validation and serialization for resource management:
- Resource: Labor, Equipment, Material with capacity and cost rates
- ResourceAssignment: Activity to resource allocation
- ResourceCalendar: Per-resource availability by date
"""

from __future__ import annotations

import re
from datetime import date  # noqa: TC003 - Required at runtime for Pydantic
from decimal import Decimal
from typing import Annotated
from uuid import UUID  # noqa: TC003 - Required at runtime for Pydantic

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.models.enums import ResourceType

# =============================================================================
# Resource Schemas
# =============================================================================


class ResourceBase(BaseModel):
    """Base schema for resource with validation."""

    name: Annotated[str, Field(min_length=1, max_length=100, description="Resource name")]
    code: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            pattern=r"^[A-Z0-9\-_]+$",
            description="Unique code (uppercase alphanumeric, hyphens, underscores)",
        ),
    ]
    resource_type: ResourceType = Field(
        default=ResourceType.LABOR,
        description="Resource classification",
    )
    capacity_per_day: Annotated[
        Decimal,
        Field(
            default=Decimal("8.0"),
            ge=Decimal("0"),
            le=Decimal("24"),
            description="Available hours per day (0-24)",
        ),
    ]
    cost_rate: Annotated[
        Decimal | None,
        Field(default=None, ge=Decimal("0"), description="Hourly cost rate"),
    ] = None
    effective_date: date | None = Field(
        default=None,
        description="Date when resource becomes available",
    )
    is_active: bool = Field(default=True, description="Whether resource is active")

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


class ResourceCreate(ResourceBase):
    """Schema for creating a new resource."""

    program_id: UUID = Field(description="Program this resource belongs to")


class ResourceUpdate(BaseModel):
    """Schema for updating a resource. All fields optional."""

    name: Annotated[str | None, Field(min_length=1, max_length=100)] = None
    code: Annotated[str | None, Field(min_length=1, max_length=50)] = None
    resource_type: ResourceType | None = None
    capacity_per_day: Annotated[
        Decimal | None, Field(ge=Decimal("0"), le=Decimal("24"))
    ] = None
    cost_rate: Annotated[Decimal | None, Field(ge=Decimal("0"))] = None
    effective_date: date | None = None
    is_active: bool | None = None

    @field_validator("code", mode="before")
    @classmethod
    def uppercase_code(cls, v: str | None) -> str | None:
        """Convert code to uppercase if provided."""
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("code", mode="after")
    @classmethod
    def validate_code_pattern(cls, v: str | None) -> str | None:
        """Validate code matches required pattern if provided."""
        if v is not None and not re.match(r"^[A-Z0-9\-_]+$", v):
            msg = "Code must contain only uppercase letters, numbers, hyphens, and underscores"
            raise ValueError(msg)
        return v


class ResourceResponse(ResourceBase):
    """Schema for resource response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    created_at: date
    updated_at: date | None = None


class ResourceListResponse(BaseModel):
    """Paginated list of resources."""

    items: list[ResourceResponse]
    total: int = Field(ge=0, description="Total number of resources")
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Items per page")
    pages: int = Field(ge=0, description="Total number of pages")


class ResourceSummary(BaseModel):
    """Lightweight resource summary for embedding."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    resource_type: ResourceType


# =============================================================================
# Resource Assignment Schemas
# =============================================================================


class ResourceAssignmentBase(BaseModel):
    """Base schema for resource assignment."""

    units: Annotated[
        Decimal,
        Field(
            default=Decimal("1.0"),
            ge=Decimal("0"),
            le=Decimal("10"),
            description="Allocation units (0-10, where 1.0 = 100%)",
        ),
    ]
    start_date: date | None = Field(
        default=None,
        description="Assignment start date (defaults to activity start)",
    )
    finish_date: date | None = Field(
        default=None,
        description="Assignment finish date (defaults to activity finish)",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> ResourceAssignmentBase:
        """Validate finish_date >= start_date."""
        if self.start_date and self.finish_date and self.finish_date < self.start_date:
            msg = "finish_date must be greater than or equal to start_date"
            raise ValueError(msg)
        return self


class ResourceAssignmentCreate(ResourceAssignmentBase):
    """Schema for creating a resource assignment."""

    activity_id: UUID = Field(description="Activity to assign resource to")
    resource_id: UUID = Field(description="Resource to assign")


class ResourceAssignmentUpdate(BaseModel):
    """Schema for updating a resource assignment."""

    units: Annotated[Decimal | None, Field(ge=Decimal("0"), le=Decimal("10"))] = None
    start_date: date | None = None
    finish_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> ResourceAssignmentUpdate:
        """Validate finish_date >= start_date if both provided."""
        if self.start_date and self.finish_date and self.finish_date < self.start_date:
            msg = "finish_date must be greater than or equal to start_date"
            raise ValueError(msg)
        return self


class ResourceAssignmentResponse(ResourceAssignmentBase):
    """Schema for resource assignment response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    activity_id: UUID
    resource_id: UUID
    resource: ResourceSummary | None = None


class ResourceAssignmentListResponse(BaseModel):
    """List of resource assignments."""

    items: list[ResourceAssignmentResponse]
    total: int = Field(ge=0)


# =============================================================================
# Resource Calendar Schemas
# =============================================================================


class ResourceCalendarBase(BaseModel):
    """Base schema for resource calendar entry."""

    calendar_date: date = Field(description="Calendar date")
    available_hours: Annotated[
        Decimal,
        Field(
            default=Decimal("8.0"),
            ge=Decimal("0"),
            le=Decimal("24"),
            description="Available hours on this date (0-24)",
        ),
    ]
    is_working_day: bool = Field(
        default=True,
        description="Whether this is a working day",
    )


class ResourceCalendarCreate(ResourceCalendarBase):
    """Schema for creating a calendar entry."""

    resource_id: UUID = Field(description="Resource this calendar entry belongs to")


class ResourceCalendarEntry(BaseModel):
    """Single calendar entry for bulk operations."""

    calendar_date: date
    available_hours: Annotated[
        Decimal, Field(default=Decimal("8.0"), ge=Decimal("0"), le=Decimal("24"))
    ]
    is_working_day: bool = True


class ResourceCalendarBulkCreate(BaseModel):
    """Schema for bulk creating calendar entries."""

    resource_id: UUID = Field(description="Resource to create calendar entries for")
    entries: Annotated[
        list[ResourceCalendarEntry],
        Field(min_length=1, max_length=366, description="Calendar entries (max 366)"),
    ]

    @field_validator("entries")
    @classmethod
    def validate_unique_dates(
        cls, v: list[ResourceCalendarEntry]
    ) -> list[ResourceCalendarEntry]:
        """Ensure no duplicate dates in entries."""
        dates = [entry.calendar_date for entry in v]
        if len(dates) != len(set(dates)):
            msg = "Duplicate dates are not allowed in calendar entries"
            raise ValueError(msg)
        return v


class ResourceCalendarResponse(ResourceCalendarBase):
    """Schema for calendar entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resource_id: UUID


class ResourceCalendarRangeResponse(BaseModel):
    """Schema for calendar range query response."""

    resource_id: UUID
    start_date: date
    end_date: date
    entries: list[ResourceCalendarResponse]
    working_days: int = Field(ge=0, description="Total working days in range")
    total_hours: Decimal = Field(ge=Decimal("0"), description="Total available hours")
