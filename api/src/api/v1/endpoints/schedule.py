"""Schedule and CPM calculation endpoints."""

from uuid import UUID

from fastapi import APIRouter

from src.core.deps import DbSession
from src.core.exceptions import NotFoundError
from src.repositories.activity import ActivityRepository
from src.repositories.dependency import DependencyRepository
from src.repositories.program import ProgramRepository
from src.schemas.activity import ScheduleResult
from src.services.cpm import CPMEngine

router = APIRouter()


@router.post("/calculate/{program_id}", response_model=list[ScheduleResult])
async def calculate_schedule(
    program_id: UUID,
    db: DbSession,
) -> list[ScheduleResult]:
    """
    Calculate the CPM schedule for a program.

    Performs forward and backward pass calculations to determine:
    - Early Start (ES) and Early Finish (EF)
    - Late Start (LS) and Late Finish (LF)
    - Total Float and Free Float
    - Critical Path

    Returns schedule results for all activities.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Get all activities with dependencies
    activity_repo = ActivityRepository(db)
    activities = await activity_repo.get_all_with_dependencies(program_id)

    if not activities:
        return []

    # Get all dependencies for the program
    dep_repo = DependencyRepository(db)
    all_dependencies = []
    for activity in activities:
        deps = await dep_repo.get_successors(activity.id)
        all_dependencies.extend(deps)

    # Run CPM calculation
    engine = CPMEngine(activities, all_dependencies)
    results = engine.calculate()

    # Update activities with calculated values
    for activity in activities:
        result = results[activity.id]
        activity.early_start = None  # Convert to date if needed
        activity.early_finish = None
        activity.late_start = None
        activity.late_finish = None
        activity.total_float = result.total_float
        activity.free_float = result.free_float

    await db.commit()

    # Return results as schema objects
    return [
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


@router.get("/critical-path/{program_id}", response_model=list[UUID])
async def get_critical_path(
    program_id: UUID,
    db: DbSession,
) -> list[UUID]:
    """
    Get the critical path for a program.

    Returns a list of activity IDs that form the critical path
    (activities with zero total float).
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    activity_repo = ActivityRepository(db)
    critical_activities = await activity_repo.get_critical_path(program_id)

    return [a.id for a in critical_activities]


@router.get("/duration/{program_id}", response_model=dict[str, int])
async def get_project_duration(
    program_id: UUID,
    db: DbSession,
) -> dict[str, int]:
    """
    Get the total project duration in working days.

    Calculates the schedule if not already calculated.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Get all activities with dependencies
    activity_repo = ActivityRepository(db)
    activities = await activity_repo.get_all_with_dependencies(program_id)

    if not activities:
        return {"duration": 0}

    # Get all dependencies
    dep_repo = DependencyRepository(db)
    all_dependencies = []
    for activity in activities:
        deps = await dep_repo.get_successors(activity.id)
        all_dependencies.extend(deps)

    # Calculate schedule
    engine = CPMEngine(activities, all_dependencies)
    engine.calculate()

    return {"duration": engine.get_project_duration()}
