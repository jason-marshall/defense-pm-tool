"""Pydantic schemas for resource leveling API."""

from __future__ import annotations

from datetime import date  # noqa: TC003
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field


class LevelingOptionsRequest(BaseModel):
    """Request schema for leveling options.

    Attributes:
        preserve_critical_path: If True, never delay critical path activities
        max_iterations: Maximum leveling iterations (1-1000)
        target_resources: Specific resources to level (None = all)
        level_within_float: If True, only delay within total float
    """

    preserve_critical_path: bool = True
    max_iterations: int = Field(default=100, ge=1, le=1000)
    target_resources: list[UUID] | None = None
    level_within_float: bool = True


class ActivityShiftResponse(BaseModel):
    """Response schema for a single activity shift.

    Attributes:
        activity_id: UUID of the shifted activity
        activity_code: Activity code for display
        original_start: Original start date
        original_finish: Original finish date
        new_start: New start date after leveling
        new_finish: New finish date after leveling
        delay_days: Number of days delayed
        reason: Explanation for the delay
    """

    activity_id: UUID
    activity_code: str
    original_start: date
    original_finish: date
    new_start: date
    new_finish: date
    delay_days: int
    reason: str


class LevelingResultResponse(BaseModel):
    """Response schema for leveling result.

    Attributes:
        program_id: UUID of the leveled program
        success: True if all over-allocations resolved
        iterations_used: Number of leveling iterations performed
        activities_shifted: Count of activities that were delayed
        shifts: List of all activity shifts made
        remaining_overallocations: Count of unresolved over-allocations
        new_project_finish: Project finish date after leveling
        original_project_finish: Project finish date before leveling
        schedule_extension_days: Days added to project duration
        warnings: List of warning messages
    """

    program_id: UUID
    success: bool
    iterations_used: int
    activities_shifted: int
    shifts: list[ActivityShiftResponse]
    remaining_overallocations: int
    new_project_finish: date
    original_project_finish: date
    schedule_extension_days: int
    warnings: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class LevelingApplyRequest(BaseModel):
    """Request schema for applying leveling shifts.

    Attributes:
        shifts: List of activity IDs to apply shifts for
    """

    shifts: list[UUID]


class LevelingApplyResponse(BaseModel):
    """Response schema for apply operation.

    Attributes:
        applied_count: Number of activities updated
        skipped_count: Number of activities skipped
        new_project_finish: New project finish date after applying
    """

    applied_count: int
    skipped_count: int
    new_project_finish: date
