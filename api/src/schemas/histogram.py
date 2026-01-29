"""Pydantic schemas for resource histogram API."""

from __future__ import annotations

from datetime import date  # noqa: TC003
from decimal import Decimal  # noqa: TC003
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field

from src.models.enums import ResourceType  # noqa: TC001


class HistogramDataPointResponse(BaseModel):
    """Response schema for a single histogram data point.

    Attributes:
        date: The date for this data point
        available_hours: Hours available on this day/week
        assigned_hours: Hours assigned on this day/week
        utilization_percent: Utilization as percentage (0-100+)
        is_overallocated: True if assigned > available
    """

    date: date
    available_hours: Decimal
    assigned_hours: Decimal
    utilization_percent: Decimal
    is_overallocated: bool


class ResourceHistogramResponse(BaseModel):
    """Response schema for single resource histogram.

    Attributes:
        resource_id: UUID of the resource
        resource_code: Resource code for display
        resource_name: Resource name for display
        resource_type: Type of resource
        start_date: Start of histogram period
        end_date: End of histogram period
        data_points: List of data points
        peak_utilization: Maximum utilization percentage
        peak_date: Date of peak utilization
        average_utilization: Average utilization over period
        overallocated_days: Number of days with over-allocation
        total_available_hours: Sum of available hours
        total_assigned_hours: Sum of assigned hours
    """

    resource_id: UUID
    resource_code: str
    resource_name: str
    resource_type: ResourceType
    start_date: date
    end_date: date
    data_points: list[HistogramDataPointResponse]
    peak_utilization: Decimal
    peak_date: date | None
    average_utilization: Decimal
    overallocated_days: int
    total_available_hours: Decimal
    total_assigned_hours: Decimal

    model_config = {"from_attributes": True}


class ProgramHistogramSummaryResponse(BaseModel):
    """Response schema for program histogram summary.

    Attributes:
        program_id: UUID of the program
        start_date: Start of analysis period
        end_date: End of analysis period
        resource_count: Number of resources in histogram
        total_overallocated_days: Sum of overallocated days across resources
        resources_with_overallocation: Count of resources with over-allocation
    """

    program_id: UUID
    start_date: date
    end_date: date
    resource_count: int
    total_overallocated_days: int
    resources_with_overallocation: int

    model_config = {"from_attributes": True}


class ProgramHistogramResponse(BaseModel):
    """Response schema for program-wide histogram.

    Attributes:
        summary: Summary statistics for the program
        histograms: List of resource histograms
    """

    summary: ProgramHistogramSummaryResponse
    histograms: list[ResourceHistogramResponse] = Field(default_factory=list)
