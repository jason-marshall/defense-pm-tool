"""Pydantic schemas for Baseline model."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaselineBase(BaseModel):
    """Base schema for Baseline with shared fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Baseline name")
    description: str | None = Field(
        default=None, max_length=5000, description="Baseline description"
    )


class BaselineCreate(BaselineBase):
    """Schema for creating a new baseline snapshot."""

    program_id: UUID = Field(..., description="Program ID to create baseline for")
    include_schedule: bool = Field(default=True, description="Include schedule snapshot")
    include_cost: bool = Field(default=True, description="Include cost snapshot")
    include_wbs: bool = Field(default=True, description="Include WBS snapshot")


class BaselineUpdate(BaseModel):
    """Schema for updating baseline metadata (limited fields)."""

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Updated name")
    description: str | None = Field(
        default=None, max_length=5000, description="Updated description"
    )


class BaselineApprove(BaseModel):
    """Schema for approving a baseline as PMB."""

    approval_notes: str | None = Field(
        default=None, max_length=1000, description="Optional approval notes"
    )


class BaselineSummary(BaseModel):
    """Lightweight baseline response without snapshot data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    name: str
    version: int
    description: str | None
    is_approved: bool
    approved_at: datetime | None
    total_bac: Decimal
    scheduled_finish: date | None
    activity_count: int
    wbs_count: int
    created_at: datetime
    created_by_id: UUID


class BaselineResponse(BaselineSummary):
    """Full baseline response including snapshot data."""

    schedule_snapshot: dict[str, Any] | None = Field(
        default=None, description="Schedule data snapshot"
    )
    cost_snapshot: dict[str, Any] | None = Field(default=None, description="Cost data snapshot")
    wbs_snapshot: dict[str, Any] | None = Field(default=None, description="WBS hierarchy snapshot")
    approved_by_id: UUID | None = None
    updated_at: datetime | None = None


class BaselineListResponse(BaseModel):
    """Paginated list of baselines."""

    items: list[BaselineSummary]
    total: int
    page: int
    per_page: int
    pages: int


# Snapshot schemas for structured data


class ActivitySnapshot(BaseModel):
    """Schema for activity data in baseline snapshot."""

    id: UUID
    code: str
    name: str
    duration: int
    planned_start: date | None
    planned_finish: date | None
    early_start: date | None
    early_finish: date | None
    late_start: date | None
    late_finish: date | None
    total_float: int | None
    is_critical: bool
    budgeted_cost: Decimal
    percent_complete: Decimal
    ev_method: str


class DependencySnapshot(BaseModel):
    """Schema for dependency data in baseline snapshot."""

    predecessor_id: UUID
    successor_id: UUID
    dependency_type: str
    lag: int


class ScheduleSnapshot(BaseModel):
    """Complete schedule snapshot structure."""

    activities: list[ActivitySnapshot]
    dependencies: list[DependencySnapshot]
    critical_path_ids: list[UUID]
    project_duration: int | None
    project_finish: date | None


class WBSSnapshot(BaseModel):
    """Schema for WBS element in baseline snapshot."""

    id: UUID
    wbs_code: str
    name: str
    parent_id: UUID | None
    path: str
    budgeted_cost: Decimal


class CostSnapshot(BaseModel):
    """Cost data snapshot structure."""

    wbs_elements: list[WBSSnapshot]
    total_bac: Decimal
    time_phased_bcws: dict[str, Decimal] | None = Field(default=None, description="BCWS by period")


class BaselineComparison(BaseModel):
    """Schema for baseline comparison results."""

    baseline_id: UUID
    baseline_name: str
    baseline_version: int
    comparison_date: datetime

    # Schedule variances
    schedule_variance: dict[str, Any] = Field(
        default_factory=dict, description="Schedule variance details"
    )

    # Cost variances
    cost_variance: dict[str, Any] = Field(default_factory=dict, description="Cost variance details")

    # Activity changes
    activities_added: list[str] = Field(
        default_factory=list, description="Activity codes added since baseline"
    )
    activities_removed: list[str] = Field(
        default_factory=list, description="Activity codes removed since baseline"
    )
    activities_modified: list[str] = Field(
        default_factory=list, description="Activity codes modified since baseline"
    )

    # Summary metrics
    bac_variance: Decimal = Field(default=Decimal("0.00"), description="BAC change from baseline")
    schedule_days_variance: int = Field(default=0, description="Schedule days change from baseline")
