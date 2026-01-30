"""API endpoints for parallel resource leveling."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from src.core.deps import CurrentUser, DbSession
from src.repositories.program import ProgramRepository
from src.schemas.leveling import (
    ActivityShiftResponse,
    AlgorithmMetrics,
    LevelingComparisonResponse,
    LevelingOptionsRequest,
    ParallelLevelingResultResponse,
)
from src.services.parallel_leveling import ParallelLevelingResult, ParallelLevelingService
from src.services.resource_leveling import (
    LevelingOptions,
    LevelingResult,
    ResourceLevelingService,
)

router = APIRouter(prefix="/programs", tags=["Parallel Leveling"])


def _convert_parallel_result_to_response(
    result: ParallelLevelingResult,
) -> ParallelLevelingResultResponse:
    """Convert ParallelLevelingResult dataclass to response schema."""
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

    return ParallelLevelingResultResponse(
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
        conflicts_resolved=result.conflicts_resolved,
        resources_processed=result.resources_processed,
    )


@router.post(
    "/{program_id}/level-parallel",
    response_model=ParallelLevelingResultResponse,
    summary="Run parallel resource leveling",
)
async def run_parallel_leveling(
    program_id: UUID,
    options: LevelingOptionsRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ParallelLevelingResultResponse:
    """Run parallel resource leveling algorithm on program.

    Parallel leveling considers all resources simultaneously to find
    a globally better solution than serial leveling. It uses a conflict
    matrix approach to process all overallocations at once.

    Key differences from serial leveling:
    - Builds complete conflict matrix upfront
    - Processes conflicts in priority order (date, then severity)
    - Uses multi-factor activity priority scoring
    - Often finds better solutions for complex schedules

    Args:
        program_id: UUID of the program to level
        options: Leveling configuration options
        db: Database session
        current_user: Authenticated user

    Returns:
        ParallelLevelingResultResponse with proposed shifts

    Raises:
        HTTPException: 404 if program not found
    """
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Run parallel leveling
    service = ParallelLevelingService(db)
    leveling_options = LevelingOptions(
        preserve_critical_path=options.preserve_critical_path,
        max_iterations=options.max_iterations,
        target_resources=options.target_resources,
        level_within_float=options.level_within_float,
    )
    result = await service.level_program(program_id, leveling_options)

    return _convert_parallel_result_to_response(result)


@router.get(
    "/{program_id}/level-parallel/preview",
    response_model=ParallelLevelingResultResponse,
    summary="Preview parallel resource leveling",
)
async def preview_parallel_leveling(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    preserve_critical_path: bool = Query(default=True),
    level_within_float: bool = Query(default=True),
    max_iterations: int = Query(default=100, ge=1, le=1000),
    target_resources: list[UUID] | None = Query(default=None),
) -> ParallelLevelingResultResponse:
    """Preview parallel resource leveling without applying changes.

    Same as POST /level-parallel but as GET for easier testing.

    Args:
        program_id: UUID of the program to level
        preserve_critical_path: Don't delay critical activities
        level_within_float: Only delay within float
        max_iterations: Maximum iterations
        target_resources: Specific resources to level
        db: Database session
        current_user: Authenticated user

    Returns:
        ParallelLevelingResultResponse with proposed shifts

    Raises:
        HTTPException: 404 if program not found
    """
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Run parallel leveling
    service = ParallelLevelingService(db)
    leveling_options = LevelingOptions(
        preserve_critical_path=preserve_critical_path,
        max_iterations=max_iterations,
        target_resources=target_resources,
        level_within_float=level_within_float,
    )
    result = await service.level_program(program_id, leveling_options)

    return _convert_parallel_result_to_response(result)


@router.get(
    "/{program_id}/level/compare",
    response_model=LevelingComparisonResponse,
    summary="Compare leveling algorithms",
)
async def compare_leveling_algorithms(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    preserve_critical_path: bool = Query(default=True),
    level_within_float: bool = Query(default=True),
    max_iterations: int = Query(default=100, ge=1, le=1000),
) -> LevelingComparisonResponse:
    """Compare serial and parallel leveling results.

    Runs both algorithms with the same options and returns comparison
    metrics without applying any changes. Use this to determine which
    algorithm produces better results for your specific schedule.

    The recommendation is based on:
    1. Schedule extension (fewer days = better)
    2. Success rate (resolved all conflicts)
    3. Number of activities shifted (fewer = less disruption)

    Args:
        program_id: UUID of the program to compare
        preserve_critical_path: Don't delay critical activities
        level_within_float: Only delay within float
        max_iterations: Maximum iterations for each algorithm
        db: Database session
        current_user: Authenticated user

    Returns:
        LevelingComparisonResponse with metrics from both algorithms

    Raises:
        HTTPException: 404 if program not found
    """
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    options = LevelingOptions(
        preserve_critical_path=preserve_critical_path,
        max_iterations=max_iterations,
        level_within_float=level_within_float,
    )

    # Run serial leveling
    serial_service = ResourceLevelingService(db)
    serial_result = await serial_service.level_program(program_id, options)

    # Run parallel leveling
    parallel_service = ParallelLevelingService(db)
    parallel_result = await parallel_service.level_program(program_id, options)

    # Build metrics
    serial_metrics = AlgorithmMetrics(
        success=serial_result.success,
        iterations=serial_result.iterations_used,
        activities_shifted=serial_result.activities_shifted,
        schedule_extension_days=serial_result.schedule_extension_days,
        remaining_conflicts=serial_result.remaining_overallocations,
    )

    parallel_metrics = AlgorithmMetrics(
        success=parallel_result.success,
        iterations=parallel_result.iterations_used,
        activities_shifted=parallel_result.activities_shifted,
        schedule_extension_days=parallel_result.schedule_extension_days,
        remaining_conflicts=parallel_result.remaining_overallocations,
    )

    # Determine recommendation
    recommendation = _determine_recommendation(serial_result, parallel_result)

    # Calculate improvement metrics
    improvement = {
        "extension_days_saved": (
            serial_result.schedule_extension_days - parallel_result.schedule_extension_days
        ),
        "fewer_shifts": (serial_result.activities_shifted - parallel_result.activities_shifted),
        "fewer_iterations": (serial_result.iterations_used - parallel_result.iterations_used),
    }

    return LevelingComparisonResponse(
        serial=serial_metrics,
        parallel=parallel_metrics,
        recommendation=recommendation,
        improvement=improvement,
    )


def _determine_recommendation(
    serial_result: LevelingResult,
    parallel_result: ParallelLevelingResult,
) -> str:  # noqa: PLR0911
    """Determine which algorithm to recommend based on results.

    Priority order:
    1. Both successful - prefer shorter schedule
    2. One successful - prefer successful one
    3. Both failed - prefer fewer remaining conflicts

    Args:
        serial_result: Result from serial leveling
        parallel_result: Result from parallel leveling

    Returns:
        "parallel" or "serial" recommendation
    """
    # Both successful - compare schedule extension
    if serial_result.success and parallel_result.success:
        if parallel_result.schedule_extension_days < serial_result.schedule_extension_days:
            return "parallel"
        if serial_result.schedule_extension_days < parallel_result.schedule_extension_days:
            return "serial"
        # Tie - prefer fewer shifts (less disruption)
        if parallel_result.activities_shifted <= serial_result.activities_shifted:
            return "parallel"
        return "serial"

    # Only one successful
    if parallel_result.success and not serial_result.success:
        return "parallel"
    if serial_result.success and not parallel_result.success:
        return "serial"

    # Both failed - prefer fewer remaining conflicts
    if parallel_result.remaining_overallocations < serial_result.remaining_overallocations:
        return "parallel"
    if serial_result.remaining_overallocations < parallel_result.remaining_overallocations:
        return "serial"

    # Tie in failures - prefer shorter extension
    if parallel_result.schedule_extension_days <= serial_result.schedule_extension_days:
        return "parallel"
    return "serial"
