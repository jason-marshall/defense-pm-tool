"""Pydantic schemas for EVMS Period management.

This module provides schemas for:
- EVMS period creation (EVMSPeriodCreate)
- EVMS period updates (EVMSPeriodUpdate)
- EVMS period responses (EVMSPeriodResponse)
- EVMS period data management
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from src.models.evms_period import PeriodStatus
from src.schemas.common import PaginatedResponse


class EVMSPeriodDataBase(BaseModel):
    """Base schema for EVMS period data fields."""

    wbs_id: UUID = Field(
        ...,
        description="ID of the WBS element",
    )
    bcws: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="Budgeted Cost of Work Scheduled (period)",
    )
    bcwp: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="Budgeted Cost of Work Performed (period)",
    )
    acwp: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="Actual Cost of Work Performed (period)",
    )


class EVMSPeriodDataCreate(EVMSPeriodDataBase):
    """Schema for creating EVMS period data."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "wbs_id": "660e8400-e29b-41d4-a716-446655440001",
                "bcws": "50000.00",
                "bcwp": "45000.00",
                "acwp": "48000.00",
            }
        }
    )


class EVMSPeriodDataUpdate(BaseModel):
    """Schema for updating EVMS period data."""

    bcws: Decimal | None = Field(
        default=None,
        ge=0,
        description="Budgeted Cost of Work Scheduled (period)",
    )
    bcwp: Decimal | None = Field(
        default=None,
        ge=0,
        description="Budgeted Cost of Work Performed (period)",
    )
    acwp: Decimal | None = Field(
        default=None,
        ge=0,
        description="Actual Cost of Work Performed (period)",
    )


class EVMSPeriodDataResponse(BaseModel):
    """Schema for EVMS period data in API responses."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440002",
                "period_id": "880e8400-e29b-41d4-a716-446655440003",
                "wbs_id": "660e8400-e29b-41d4-a716-446655440001",
                "bcws": "50000.00",
                "bcwp": "45000.00",
                "acwp": "48000.00",
                "cumulative_bcws": "150000.00",
                "cumulative_bcwp": "135000.00",
                "cumulative_acwp": "144000.00",
                "cv": "-9000.00",
                "sv": "-15000.00",
                "cpi": "0.94",
                "spi": "0.90",
            }
        },
    )

    id: UUID
    period_id: UUID
    wbs_id: UUID
    bcws: Decimal
    bcwp: Decimal
    acwp: Decimal
    cumulative_bcws: Decimal
    cumulative_bcwp: Decimal
    cumulative_acwp: Decimal
    cv: Decimal
    sv: Decimal
    cpi: Decimal | None
    spi: Decimal | None
    created_at: datetime
    updated_at: datetime


class EVMSPeriodBase(BaseModel):
    """Base schema for EVMS period fields."""

    period_start: date = Field(
        ...,
        description="Start date of the reporting period",
    )
    period_end: date = Field(
        ...,
        description="End date of the reporting period",
    )
    period_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable period name",
    )
    notes: str | None = Field(
        default=None,
        max_length=5000,
        description="Optional notes about this period",
    )


class EVMSPeriodCreate(EVMSPeriodBase):
    """Schema for creating a new EVMS period."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "program_id": "550e8400-e29b-41d4-a716-446655440000",
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
                "period_name": "January 2026",
                "notes": "First reporting period",
            }
        }
    )

    program_id: UUID = Field(
        ...,
        description="ID of the parent program",
    )

    @field_validator("period_end")
    @classmethod
    def end_after_start(cls, v: date, info: ValidationInfo) -> date:
        """Validate period_end is after period_start."""
        if "period_start" in info.data and v < info.data["period_start"]:
            raise ValueError("period_end must be after period_start")
        return v


class EVMSPeriodUpdate(BaseModel):
    """Schema for updating an EVMS period."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period_name": "January 2026 (Revised)",
                "status": "submitted",
                "notes": "Updated with final actuals",
            }
        }
    )

    period_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Human-readable period name",
    )
    status: PeriodStatus | None = Field(
        default=None,
        description="Period status",
    )
    notes: str | None = Field(
        default=None,
        max_length=5000,
        description="Optional notes about this period",
    )


class EVMSPeriodResponse(BaseModel):
    """Schema for EVMS period in API responses."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "880e8400-e29b-41d4-a716-446655440003",
                "program_id": "550e8400-e29b-41d4-a716-446655440000",
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
                "period_name": "January 2026",
                "status": "draft",
                "notes": "First reporting period",
                "cumulative_bcws": "150000.00",
                "cumulative_bcwp": "135000.00",
                "cumulative_acwp": "144000.00",
                "created_at": "2026-01-08T12:00:00Z",
                "updated_at": "2026-01-08T12:00:00Z",
            }
        },
    )

    id: UUID
    program_id: UUID
    period_start: date
    period_end: date
    period_name: str
    status: PeriodStatus
    notes: str | None
    cumulative_bcws: Decimal
    cumulative_bcwp: Decimal
    cumulative_acwp: Decimal
    created_at: datetime
    updated_at: datetime

    @property
    def cost_variance(self) -> Decimal:
        """Calculate Cost Variance (CV = BCWP - ACWP)."""
        return self.cumulative_bcwp - self.cumulative_acwp

    @property
    def schedule_variance(self) -> Decimal:
        """Calculate Schedule Variance (SV = BCWP - BCWS)."""
        return self.cumulative_bcwp - self.cumulative_bcws


class EVMSPeriodWithDataResponse(EVMSPeriodResponse):
    """EVMS period response with period data included."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    period_data: list[EVMSPeriodDataResponse] = Field(
        default_factory=list,
        description="EVMS data for each WBS element",
    )


class EVMSSummaryResponse(BaseModel):
    """Summary of EVMS metrics for a program."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "program_id": "550e8400-e29b-41d4-a716-446655440000",
                "as_of_date": "2026-01-31",
                "bac": "1000000.00",
                "bcws": "150000.00",
                "bcwp": "135000.00",
                "acwp": "144000.00",
                "cv": "-9000.00",
                "sv": "-15000.00",
                "cpi": "0.94",
                "spi": "0.90",
                "eac": "1063829.79",
                "etc": "919829.79",
                "vac": "-63829.79",
                "tcpi": "1.07",
                "percent_complete": "13.50",
            }
        }
    )

    program_id: UUID
    as_of_date: date
    bac: Decimal = Field(description="Budget at Completion")
    bcws: Decimal = Field(description="Budgeted Cost of Work Scheduled")
    bcwp: Decimal = Field(description="Budgeted Cost of Work Performed")
    acwp: Decimal = Field(description="Actual Cost of Work Performed")
    cv: Decimal = Field(description="Cost Variance")
    sv: Decimal = Field(description="Schedule Variance")
    cpi: Decimal | None = Field(description="Cost Performance Index")
    spi: Decimal | None = Field(description="Schedule Performance Index")
    eac: Decimal | None = Field(description="Estimate at Completion")
    etc: Decimal | None = Field(description="Estimate to Complete")
    vac: Decimal | None = Field(description="Variance at Completion")
    tcpi: Decimal | None = Field(description="To-Complete Performance Index")
    percent_complete: Decimal = Field(description="Percent Complete (BCWP/BAC)")


# Type aliases for list responses
EVMSPeriodListResponse = PaginatedResponse[EVMSPeriodResponse]
EVMSPeriodDataListResponse = PaginatedResponse[EVMSPeriodDataResponse]
