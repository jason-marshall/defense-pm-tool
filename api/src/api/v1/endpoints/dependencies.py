"""Dependency endpoints."""

from uuid import UUID

from fastapi import APIRouter

from src.core.deps import DbSession
from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.repositories.activity import ActivityRepository
from src.repositories.dependency import DependencyRepository
from src.schemas.dependency import (
    DependencyCreate,
    DependencyListResponse,
    DependencyResponse,
)

router = APIRouter()


@router.get("/activity/{activity_id}", response_model=DependencyListResponse)
async def list_dependencies_for_activity(
    activity_id: UUID,
    db: DbSession,
) -> DependencyListResponse:
    """List all dependencies for an activity (both predecessor and successor)."""
    repo = DependencyRepository(db)
    dependencies = await repo.get_for_activity(activity_id)

    return DependencyListResponse(
        items=[DependencyResponse.model_validate(d) for d in dependencies],
        total=len(dependencies),
    )


@router.get("/{dependency_id}", response_model=DependencyResponse)
async def get_dependency(
    dependency_id: UUID,
    db: DbSession,
) -> DependencyResponse:
    """Get a single dependency by ID."""
    repo = DependencyRepository(db)
    dependency = await repo.get_by_id(dependency_id)

    if not dependency:
        raise NotFoundError(
            f"Dependency {dependency_id} not found",
            "DEPENDENCY_NOT_FOUND",
        )

    return DependencyResponse.model_validate(dependency)


@router.post("", response_model=DependencyResponse, status_code=201)
async def create_dependency(
    dependency_in: DependencyCreate,
    db: DbSession,
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

    # Check for duplicate dependency
    if await dep_repo.dependency_exists(
        dependency_in.predecessor_id,
        dependency_in.successor_id,
    ):
        raise ConflictError(
            "Dependency already exists between these activities",
            "DUPLICATE_DEPENDENCY",
        )

    dependency = await dep_repo.create(dependency_in.model_dump())
    await db.commit()

    return DependencyResponse.model_validate(dependency)


@router.delete("/{dependency_id}", status_code=204)
async def delete_dependency(
    dependency_id: UUID,
    db: DbSession,
) -> None:
    """Delete a dependency."""
    repo = DependencyRepository(db)
    dependency = await repo.get_by_id(dependency_id)

    if not dependency:
        raise NotFoundError(
            f"Dependency {dependency_id} not found",
            "DEPENDENCY_NOT_FOUND",
        )

    await repo.delete(dependency)
    await db.commit()
