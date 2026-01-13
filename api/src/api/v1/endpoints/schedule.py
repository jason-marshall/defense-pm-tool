"""Schedule and CPM calculation endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from src.core.cache import CacheKeys, cache_manager, compute_activities_hash
from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import AuthorizationError, NotFoundError
from src.repositories.activity import ActivityRepository
from src.repositories.dependency import DependencyRepository
from src.repositories.program import ProgramRepository
from src.schemas.activity import (
    ActivityBriefResponse,
    CriticalPathResponse,
    ScheduleResult,
)
from src.services.cpm import CPMEngine

router = APIRouter()


@router.post("/calculate/{program_id}", response_model=list[ScheduleResult])
async def calculate_schedule(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    force_recalculate: Annotated[
        bool, Query(description="Force recalculation ignoring cache")
    ] = False,
) -> list[ScheduleResult]:
    """
    Calculate the CPM schedule for a program.

    Performs forward and backward pass calculations to determine:
    - Early Start (ES) and Early Finish (EF)
    - Late Start (LS) and Late Finish (LF)
    - Total Float and Free Float
    - Critical Path

    Results are cached based on activity/dependency hash.
    Returns schedule results for all activities.
    """
    # Verify program exists and user has access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to calculate schedule for this program",
            "NOT_AUTHORIZED",
        )

    # Get all activities for the program
    activity_repo = ActivityRepository(db)
    activities = await activity_repo.get_by_program(program_id, limit=10000)

    if not activities:
        return []

    # Get all dependencies for the program
    dep_repo = DependencyRepository(db)
    all_dependencies = await dep_repo.get_by_program(program_id)

    # Compute hash for cache key
    activities_data = [
        {
            "id": str(a.id),
            "duration": a.duration,
        }
        for a in activities
    ]
    deps_data = [
        {
            "pred": str(d.predecessor_id),
            "succ": str(d.successor_id),
            "type": d.dependency_type,
            "lag": d.lag,
        }
        for d in all_dependencies
    ]
    data_hash = compute_activities_hash(activities_data + deps_data)
    cache_key = CacheKeys.cpm_key(str(program_id), data_hash)

    # Try to get from cache (unless force_recalculate)
    if not force_recalculate:
        cached = await cache_manager.get(cache_key)
        if cached:
            # Return cached results (already in schema format)
            return [ScheduleResult(**r) for r in cached]

    # Run CPM calculation
    engine = CPMEngine(activities, all_dependencies)
    results = engine.calculate()

    # Update activities with calculated values
    for activity in activities:
        if activity.id in results:
            result = results[activity.id]
            activity.total_float = result.total_float
            activity.free_float = result.free_float
            activity.is_critical = result.is_critical

    await db.commit()

    # Convert results to schema objects
    result_list = [
        ScheduleResult(
            activity_id=r.activity_id,
            early_start=r.early_start,
            early_finish=r.early_finish,
            late_start=r.late_start,
            late_finish=r.late_finish,
            total_float=r.total_float,
            free_float=r.free_float,
            is_critical=r.is_critical,
        )
        for r in results.values()
    ]

    # Cache the results
    await cache_manager.set(
        cache_key,
        [r.model_dump() for r in result_list],
        ttl=CacheKeys.CPM_TTL,
    )

    return result_list


@router.get("/critical-path/{program_id}", response_model=CriticalPathResponse)
async def get_critical_path(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> CriticalPathResponse:
    """
    Get the critical path for a program.

    Returns activities on the critical path and project duration.
    """
    # Verify program exists and user has access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to view critical path for this program",
            "NOT_AUTHORIZED",
        )

    activity_repo = ActivityRepository(db)

    # Get all activities
    all_activities = await activity_repo.get_by_program(program_id, limit=10000)
    critical_activities = await activity_repo.get_critical_path(program_id)

    # Calculate project duration from critical activities
    project_duration = 0
    if critical_activities:
        project_duration = sum(a.duration for a in critical_activities)

    return CriticalPathResponse(
        project_duration=project_duration,
        critical_activities=[ActivityBriefResponse.model_validate(a) for a in critical_activities],
        total_activities=len(all_activities),
        critical_count=len(critical_activities),
    )


@router.get("/duration/{program_id}", response_model=dict[str, int])
async def get_project_duration(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, int]:
    """
    Get the total project duration in working days.

    Calculates the schedule if not already calculated.
    """
    # Verify program exists and user has access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to view project duration for this program",
            "NOT_AUTHORIZED",
        )

    # Get all activities for the program
    activity_repo = ActivityRepository(db)
    activities = await activity_repo.get_by_program(program_id, limit=10000)

    if not activities:
        return {"duration": 0}

    # Get all dependencies
    dep_repo = DependencyRepository(db)
    all_dependencies = await dep_repo.get_by_program(program_id)

    # Calculate schedule
    engine = CPMEngine(activities, all_dependencies)
    engine.calculate()

    return {"duration": engine.get_project_duration()}
