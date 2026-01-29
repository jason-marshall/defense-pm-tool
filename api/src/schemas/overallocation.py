"""Pydantic schemas for over-allocation detection.

Provides response schemas for over-allocation periods and program reports.
"""

from __future__ import annotations

from datetime import date  # noqa: TC003 - Required at runtime for Pydantic
from decimal import Decimal
from typing import Annotated
from uuid import UUID  # noqa: TC003 - Required at runtime for Pydantic

from pydantic import BaseModel, ConfigDict, Field


class OverallocationPeriodResponse(BaseModel):
    """Response schema for a single over-allocation period."""

    model_config = ConfigDict(from_attributes=True)

    resource_id: UUID = Field(description="UUID of the over-allocated resource")
    resource_code: str = Field(description="Resource code for display")
    resource_name: str = Field(description="Resource name for display")
    start_date: date = Field(description="First day of over-allocation period")
    end_date: date = Field(description="Last day of over-allocation period (inclusive)")
    duration_days: int = Field(ge=1, description="Number of days in the period")
    peak_assigned: Annotated[
        Decimal, Field(ge=Decimal("0"), description="Maximum assigned hours during period")
    ]
    peak_available: Annotated[
        Decimal, Field(ge=Decimal("0"), description="Available hours on peak day")
    ]
    peak_excess: Annotated[Decimal, Field(description="Maximum excess (assigned - available)")]
    severity: str = Field(description="Severity classification: 'low', 'medium', or 'high'")
    affected_activities: list[UUID] = Field(
        default_factory=list,
        description="Activity IDs contributing to over-allocation",
    )


class ProgramOverallocationReportResponse(BaseModel):
    """Response schema for program-wide over-allocation report."""

    model_config = ConfigDict(from_attributes=True)

    program_id: UUID = Field(description="UUID of the analyzed program")
    analysis_start: date = Field(description="Start date of analysis period")
    analysis_end: date = Field(description="End date of analysis period")
    total_overallocations: int = Field(ge=0, description="Total number of over-allocation periods")
    resources_affected: int = Field(ge=0, description="Number of resources with over-allocations")
    total_affected_days: int = Field(
        ge=0, description="Total days with over-allocation across all resources"
    )
    has_high_severity: bool = Field(description="Whether any period has high severity")
    critical_path_affected: bool = Field(
        description="Whether any critical path activities are affected"
    )
    periods: list[OverallocationPeriodResponse] = Field(
        default_factory=list, description="All over-allocation periods"
    )


class ResourceOverallocationQuery(BaseModel):
    """Query parameters for resource over-allocation endpoint."""

    start_date: date = Field(description="Start of analysis period")
    end_date: date = Field(description="End of analysis period")


class ProgramOverallocationQuery(BaseModel):
    """Query parameters for program over-allocation endpoint."""

    start_date: date | None = Field(
        default=None, description="Start of analysis period (defaults to program start)"
    )
    end_date: date | None = Field(
        default=None, description="End of analysis period (defaults to program end)"
    )
