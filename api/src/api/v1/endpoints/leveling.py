"""API endpoints for resource leveling."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from src.core.deps import CurrentUser, DbSession
from src.repositories.activity import ActivityRepository
from src.repositories.program import ProgramRepository
from src.schemas.leveling import (
    ActivityShiftResponse,
    LevelingApplyRequest,
    LevelingApplyResponse,
    LevelingOptionsRequest,
    LevelingResultResponse,
)
from src.services.resource_leveling import (
    LevelingOptions,
    LevelingResult,
    ResourceLevelingService,
)

if TYPE_CHECKING:
    from datetime import date

router = APIRouter(prefix="/programs", tags=["leveling"])


def _convert_result_to_response(
    result: LevelingResult,
) -> LevelingResultResponse:
    """Convert LevelingResult dataclass to response schema."""
    shifts = [
        ActivityShiftResponse(
            activity_id=s.activity_id,
            activity_code=s.activity_code,
            original_start=s.original_start,
            original_finish=s.original_finish,
            new_start=s.new_start,
            new_finish=s.new_finish,
            delay_days=s.delay_days,
            reason=s.reason,
        )
        for s in result.shifts
    ]

    return LevelingResultResponse(
        program_id=result.program_id,
        success=result.success,
        iterations_used=result.iterations_used,
        activities_shifted=result.activities_shifted,
        shifts=shifts,
        remaining_overallocations=result.remaining_overallocations,
        new_project_finish=result.new_project_finish,
        original_project_finish=result.original_project_finish,
        schedule_extension_days=result.schedule_extension_days,
        warnings=result.warnings,
    )


@router.post(
    "/{program_id}/level",
    response_model=LevelingResultResponse,
    summary="Run resource leveling",
)
async def level_program_resources(
    program_id: UUID,
    options: LevelingOptionsRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> LevelingResultResponse:
    """Run resource leveling algorithm on program.

    Returns proposed activity shifts without applying them.
    Use /level/apply to apply selected shifts.

    Args:
        program_id: UUID of the program to level
        options: Leveling configuration options
        db: Database session
        current_user: Authenticated user

    Returns:
        LevelingResultResponse with proposed shifts

    Raises:
        HTTPException: 404 if program not found
    """
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Run leveling
    service = ResourceLevelingService(db)
    leveling_options = LevelingOptions(
        preserve_critical_path=options.preserve_critical_path,
        max_iterations=options.max_iterations,
        target_resources=options.target_resources,
        level_within_float=options.level_within_float,
    )
    result = await service.level_program(program_id, leveling_options)

    return _convert_result_to_response(result)


@router.get(
    "/{program_id}/level/preview",
    response_model=LevelingResultResponse,
    summary="Preview resource leveling",
)
async def preview_leveling(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    preserve_critical_path: bool = Query(default=True),
    level_within_float: bool = Query(default=True),
    max_iterations: int = Query(default=100, ge=1, le=1000),
    target_resources: list[UUID] | None = Query(default=None),
) -> LevelingResultResponse:
    """Preview resource leveling without applying changes.

    Same as POST /level but as GET for easier testing.

    Args:
        program_id: UUID of the program to level
        preserve_critical_path: Don't delay critical activities
        level_within_float: Only delay within float
        max_iterations: Maximum iterations
        target_resources: Specific resources to level
        db: Database session
        current_user: Authenticated user

    Returns:
        LevelingResultResponse with proposed shifts

    Raises:
        HTTPException: 404 if program not found
    """
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Run leveling
    service = ResourceLevelingService(db)
    leveling_options = LevelingOptions(
        preserve_critical_path=preserve_critical_path,
        max_iterations=max_iterations,
        target_resources=target_resources,
        level_within_float=level_within_float,
    )
    result = await service.level_program(program_id, leveling_options)

    return _convert_result_to_response(result)


@router.post(
    "/{program_id}/level/apply",
    response_model=LevelingApplyResponse,
    summary="Apply leveling shifts",
)
async def apply_leveling_shifts(
    program_id: UUID,
    request: LevelingApplyRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> LevelingApplyResponse:
    """Apply selected activity shifts from leveling result.

    Updates activity planned_start and planned_finish dates.
    Only applies shifts for activity IDs in the request.

    Args:
        program_id: UUID of the program
        request: List of activity IDs to apply shifts for
        db: Database session
        current_user: Authenticated user

    Returns:
        LevelingApplyResponse with counts and new finish date

    Raises:
        HTTPException: 404 if program not found
    """
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # First run leveling to get the shifts
    service = ResourceLevelingService(db)
    result = await service.level_program(program_id)

    # Filter shifts to only those requested
    shifts_to_apply = {s.activity_id: s for s in result.shifts}
    requested_ids = set(request.shifts)

    applied_count = 0
    skipped_count = 0
    new_finish: date = result.original_project_finish

    activity_repo = ActivityRepository(db)

    for activity_id in requested_ids:
        if activity_id in shifts_to_apply:
            shift = shifts_to_apply[activity_id]
            activity = await activity_repo.get_by_id(activity_id)

            if activity:
                activity.planned_start = shift.new_start
                activity.planned_finish = shift.new_finish
                await db.flush()
                applied_count += 1

                new_finish = max(new_finish, shift.new_finish)
        else:
            skipped_count += 1

    await db.commit()

    return LevelingApplyResponse(
        applied_count=applied_count,
        skipped_count=skipped_count,
        new_project_finish=new_finish,
    )
