"""Dependency endpoints with authentication and cycle detection."""

from uuid import UUID

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import (
    AuthorizationError,
    CircularDependencyError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.models.dependency import Dependency as DependencyModel
from src.repositories.activity import ActivityRepository
from src.repositories.dependency import DependencyRepository
from src.repositories.program import ProgramRepository
from src.schemas.dependency import (
    DependencyCreate,
    DependencyListResponse,
    DependencyResponse,
    DependencyUpdate,
)
from src.services.cpm import CPMEngine

router = APIRouter()


async def would_create_cycle(
    db: AsyncSession,
    program_id: UUID,
    predecessor_id: UUID,
    successor_id: UUID,
) -> tuple[bool, list[UUID] | None]:
    """
    Check if adding this dependency would create a cycle.

    Args:
        db: Database session
        program_id: ID of the program containing the activities
        predecessor_id: ID of the predecessor activity
        successor_id: ID of the successor activity

    Returns:
        Tuple of (would_create_cycle, cycle_path)
    """
    activity_repo = ActivityRepository(db)
    dep_repo = DependencyRepository(db)

    # Get all activities for the program
    activities = await activity_repo.get_by_program(program_id, limit=10000)

    if not activities:
        return False, None

    # Get existing dependencies
    all_deps = await dep_repo.get_by_program(program_id)

    # Create temporary dependency for testing
    temp_dep = DependencyModel(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        predecessor_id=predecessor_id,
        successor_id=successor_id,
        dependency_type="FS",
        lag=0,
    )

    # Test with CPM engine's cycle detection
    try:
        engine = CPMEngine(activities, [*list(all_deps), temp_dep])
        cycle = engine._detect_cycles()
        if cycle:
            return True, cycle
        return False, None
    except CircularDependencyError as e:
        return True, e.cycle_path


@router.get("/activity/{activity_id}", response_model=DependencyListResponse)
async def list_dependencies_for_activity(
    activity_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> DependencyListResponse:
    """List all dependencies for an activity (both predecessor and successor)."""
    # Verify activity exists and user has access
    activity_repo = ActivityRepository(db)
    activity = await activity_repo.get_by_id(activity_id)

    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")

    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity.program_id)

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to view dependencies for this activity",
            "NOT_AUTHORIZED",
        )

    repo = DependencyRepository(db)
    dependencies = await repo.get_for_activity(activity_id)

    return DependencyListResponse(
        items=[DependencyResponse.from_orm_safe(d) for d in dependencies],
        total=len(dependencies),
        page=1,
        page_size=len(dependencies) if dependencies else 50,
    )


@router.get("/program/{program_id}", response_model=DependencyListResponse)
async def list_dependencies_for_program(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> DependencyListResponse:
    """List all dependencies for a program."""
    # Verify program exists and user has access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to view dependencies for this program",
            "NOT_AUTHORIZED",
        )

    dep_repo = DependencyRepository(db)
    dependencies = await dep_repo.get_by_program(program_id)

    return DependencyListResponse(
        items=[DependencyResponse.from_orm_safe(d) for d in dependencies],
        total=len(dependencies),
        page=1,
        page_size=len(dependencies) if dependencies else 50,
    )


@router.get("/{dependency_id}", response_model=DependencyResponse)
async def get_dependency(
    dependency_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> DependencyResponse:
    """Get a single dependency by ID."""
    repo = DependencyRepository(db)
    dependency = await repo.get_by_id(dependency_id)

    if not dependency:
        raise NotFoundError(
            f"Dependency {dependency_id} not found",
            "DEPENDENCY_NOT_FOUND",
        )

    # Verify access through predecessor activity's program
    activity_repo = ActivityRepository(db)
    predecessor = await activity_repo.get_by_id(dependency.predecessor_id)

    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(predecessor.program_id)

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to view this dependency",
            "NOT_AUTHORIZED",
        )

    return DependencyResponse.from_orm_safe(dependency)


@router.post("", response_model=DependencyResponse, status_code=201)
async def create_dependency(
    dependency_in: DependencyCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> DependencyResponse:
    """Create a new dependency between two activities."""
    activity_repo = ActivityRepository(db)
    dep_repo = DependencyRepository(db)

    # Verify predecessor exists
    predecessor = await activity_repo.get_by_id(dependency_in.predecessor_id)
    if not predecessor:
        raise NotFoundError(
            f"Predecessor activity {dependency_in.predecessor_id} not found",
            "PREDECESSOR_NOT_FOUND",
        )

    # Verify successor exists
    successor = await activity_repo.get_by_id(dependency_in.successor_id)
    if not successor:
        raise NotFoundError(
            f"Successor activity {dependency_in.successor_id} not found",
            "SUCCESSOR_NOT_FOUND",
        )

    # Verify activities belong to same program
    if predecessor.program_id != successor.program_id:
        raise ValidationError(
            "Predecessor and successor must belong to the same program",
            "CROSS_PROGRAM_DEPENDENCY",
        )

    # Verify user has access to the program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(predecessor.program_id)

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to create dependencies for this program",
            "NOT_AUTHORIZED",
        )

    # Check for duplicate dependency
    if await dep_repo.dependency_exists(
        dependency_in.predecessor_id,
        dependency_in.successor_id,
    ):
        raise ConflictError(
            "Dependency already exists between these activities",
            "DUPLICATE_DEPENDENCY",
        )

    # Check for cycle BEFORE creating dependency
    would_cycle, cycle_path = await would_create_cycle(
        db,
        predecessor.program_id,
        dependency_in.predecessor_id,
        dependency_in.successor_id,
    )

    if would_cycle:
        raise CircularDependencyError(cycle_path or [])

    dependency = await dep_repo.create(dependency_in.model_dump())
    await db.commit()
    await db.refresh(dependency)

    return DependencyResponse.from_orm_safe(dependency)


@router.patch("/{dependency_id}", response_model=DependencyResponse)
async def update_dependency(
    dependency_id: UUID,
    dependency_in: DependencyUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> DependencyResponse:
    """Update an existing dependency (type and lag only)."""
    repo = DependencyRepository(db)
    dependency = await repo.get_by_id(dependency_id)

    if not dependency:
        raise NotFoundError(
            f"Dependency {dependency_id} not found",
            "DEPENDENCY_NOT_FOUND",
        )

    # Verify access through predecessor activity's program
    activity_repo = ActivityRepository(db)
    predecessor = await activity_repo.get_by_id(dependency.predecessor_id)

    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(predecessor.program_id)

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to modify this dependency",
            "NOT_AUTHORIZED",
        )

    updated = await repo.update(
        dependency,
        dependency_in.model_dump(exclude_unset=True),
    )
    await db.commit()
    await db.refresh(updated)

    return DependencyResponse.from_orm_safe(updated)


@router.delete("/{dependency_id}", status_code=204)
async def delete_dependency(
    dependency_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete a dependency."""
    repo = DependencyRepository(db)
    dependency = await repo.get_by_id(dependency_id)

    if not dependency:
        raise NotFoundError(
            f"Dependency {dependency_id} not found",
            "DEPENDENCY_NOT_FOUND",
        )

    # Verify access through predecessor activity's program
    activity_repo = ActivityRepository(db)
    predecessor = await activity_repo.get_by_id(dependency.predecessor_id)

    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(predecessor.program_id)

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to delete this dependency",
            "NOT_AUTHORIZED",
        )

    await repo.delete(dependency.id)
    await db.commit()
