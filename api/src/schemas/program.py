"""Pydantic schemas for Program management.

This module provides schemas for:
- Program creation (ProgramCreate)
- Program updates (ProgramUpdate)
- Program API responses (ProgramResponse)
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.models.enums import ProgramStatus
from src.schemas.common import PaginatedResponse
from src.schemas.user import UserBriefResponse


class ProgramBase(BaseModel):
    """
    Base schema with common program fields.

    Provides field definitions shared across Create/Update/Response schemas.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name of the program",
        examples=["F-35 Lightning II Integration"],
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Detailed description of the program",
        examples=["Joint strike fighter integration program for multi-service deployment"],
    )
    contract_number: str | None = Field(
        default=None,
        max_length=100,
        description="Associated contract identifier",
        examples=["FA8611-20-C-1234"],
    )


class ProgramCreate(ProgramBase):
    """
    Schema for creating a new program.

    Requires schedule dates and validates date ordering.
    Owner is set from authenticated user context.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "F35-INT",
                "name": "F-35 Lightning II Integration",
                "description": "Joint strike fighter integration program",
                "contract_number": "FA8611-20-C-1234",
                "start_date": "2026-01-15",
                "end_date": "2028-12-31",
                "budget_at_completion": "15000000.00",
            }
        }
    )

    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique program code identifier",
        examples=["F35-INT", "NGAD-001"],
    )
    start_date: date = Field(
        ...,
        description="Planned program start date",
        examples=["2026-01-15"],
    )
    end_date: date = Field(
        ...,
        description="Planned program end date",
        examples=["2028-12-31"],
    )
    budget_at_completion: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="Total authorized budget (BAC)",
        examples=["15000000.00"],
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "ProgramCreate":
        """Validate that end_date is after start_date."""
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ProgramUpdate(BaseModel):
    """
    Schema for updating program details.

    All fields are optional - only provided fields are updated.
    Validates date consistency if both dates are provided.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "F-35 Lightning II Integration Phase 2",
                "description": "Updated program description",
                "status": "active",
            }
        }
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Display name of the program",
        examples=["F-35 Lightning II Integration Phase 2"],
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Detailed description of the program",
    )
    contract_number: str | None = Field(
        default=None,
        max_length=100,
        description="Associated contract identifier",
    )
    start_date: date | None = Field(
        default=None,
        description="Planned program start date",
    )
    end_date: date | None = Field(
        default=None,
        description="Planned program end date",
    )
    status: ProgramStatus | None = Field(
        default=None,
        description="Program lifecycle status",
        examples=["planning", "active", "complete", "on_hold"],
    )
    budget_at_completion: Decimal | None = Field(
        default=None,
        ge=0,
        description="Total authorized budget (BAC)",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "ProgramUpdate":
        """Validate date ordering if both dates are provided."""
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must be on or after start_date")
        return self


class ProgramStatusUpdate(BaseModel):
    """
    Schema for updating program status only.

    Separated for clarity in status transition operations.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "active",
            }
        }
    )

    status: ProgramStatus = Field(
        ...,
        description="New program status",
        examples=["planning", "active", "complete", "on_hold"],
    )


class ProgramResponse(BaseModel):
    """
    Schema for program data in API responses.

    Includes all program fields plus computed properties
    and nested owner information.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "code": "F35-INT",
                "name": "F-35 Lightning II Integration",
                "description": "Joint strike fighter integration program",
                "contract_number": "FA8611-20-C-1234",
                "start_date": "2026-01-15",
                "end_date": "2028-12-31",
                "status": "active",
                "budget_at_completion": "15000000.00",
                "owner": {
                    "id": "660e8400-e29b-41d4-a716-446655440001",
                    "email": "pm@example.com",
                    "full_name": "Jane Smith",
                },
                "created_at": "2026-01-08T12:00:00Z",
                "updated_at": "2026-01-08T12:00:00Z",
            }
        },
    )

    id: UUID = Field(
        ...,
        description="Unique program identifier",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    code: str = Field(
        ...,
        description="Unique program code identifier",
        examples=["F35-INT"],
    )
    name: str = Field(
        ...,
        description="Display name of the program",
        examples=["F-35 Lightning II Integration"],
    )
    description: str | None = Field(
        default=None,
        description="Detailed description",
    )
    contract_number: str | None = Field(
        default=None,
        description="Associated contract identifier",
        examples=["FA8611-20-C-1234"],
    )
    start_date: date = Field(
        ...,
        description="Planned program start date",
        examples=["2026-01-15"],
    )
    end_date: date = Field(
        ...,
        description="Planned program end date",
        examples=["2028-12-31"],
    )
    status: ProgramStatus = Field(
        ...,
        description="Current program lifecycle status",
        examples=["planning", "active", "complete", "on_hold"],
    )
    budget_at_completion: Decimal = Field(
        ...,
        description="Total authorized budget (BAC)",
        examples=["15000000.00"],
    )
    owner_id: UUID = Field(
        ...,
        description="ID of the program owner",
    )
    owner: UserBriefResponse | None = Field(
        default=None,
        description="Program owner details",
    )
    created_at: datetime = Field(
        ...,
        description="Program creation timestamp",
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
    )

    @property
    def duration_days(self) -> int:
        """Calculate program duration in days."""
        return (self.end_date - self.start_date).days


class ProgramBriefResponse(BaseModel):
    """
    Brief program response for embedding in other responses.

    Contains only essential identification fields.
    Used when including program info in activity/WBS responses.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "code": "F35-INT",
                "name": "F-35 Lightning II Integration",
                "status": "active",
            }
        },
    )

    id: UUID = Field(
        ...,
        description="Unique program identifier",
    )
    code: str = Field(
        ...,
        description="Unique program code identifier",
    )
    name: str = Field(
        ...,
        description="Display name of the program",
    )
    status: ProgramStatus = Field(
        ...,
        description="Current program status",
    )


class ProgramSummaryResponse(ProgramResponse):
    """
    Extended program response with summary statistics.

    Includes counts and rollup metrics for dashboard views.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    wbs_element_count: int = Field(
        default=0,
        description="Total number of WBS elements",
        examples=[25],
    )
    activity_count: int = Field(
        default=0,
        description="Total number of activities",
        examples=[150],
    )
    milestone_count: int = Field(
        default=0,
        description="Number of milestone activities",
        examples=[12],
    )
    percent_complete: Decimal = Field(
        default=Decimal("0.00"),
        description="Overall program completion percentage",
        examples=["45.50"],
    )


# Type alias for paginated program lists
ProgramListResponse = PaginatedResponse[ProgramResponse]
