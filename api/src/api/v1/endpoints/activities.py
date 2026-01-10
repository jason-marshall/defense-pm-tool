"""Activity endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from src.core.deps import DbSession
from src.core.exceptions import NotFoundError
from src.repositories.activity import ActivityRepository
from src.repositories.program import ProgramRepository
from src.schemas.activity import (
    ActivityCreate,
    ActivityListResponse,
    ActivityResponse,
    ActivityUpdate,
)

router = APIRouter()


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    db: DbSession,
    program_id: Annotated[UUID, Query(description="Filter by program ID")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ActivityListResponse:
    """List all activities for a program with pagination."""
    repo = ActivityRepository(db)
    skip = (page - 1) * page_size

    activities = await repo.get_by_program(program_id, skip=skip, limit=page_size)
    total = await repo.count(filters={"program_id": program_id})

    return ActivityListResponse(
        items=[ActivityResponse.model_validate(a) for a in activities],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: UUID,
    db: DbSession,
) -> ActivityResponse:
    """Get a single activity by ID."""
    repo = ActivityRepository(db)
    activity = await repo.get_by_id(activity_id)

    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")

    return ActivityResponse.model_validate(activity)


@router.post("", response_model=ActivityResponse, status_code=201)
async def create_activity(
    activity_in: ActivityCreate,
    db: DbSession,
) -> ActivityResponse:
    """Create a new activity."""
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity_in.program_id)
    if not program:
        raise NotFoundError(
            f"Program {activity_in.program_id} not found",
            "PROGRAM_NOT_FOUND",
        )

    activity_repo = ActivityRepository(db)
    activity = await activity_repo.create(activity_in.model_dump())
    await db.commit()

    return ActivityResponse.model_validate(activity)


@router.patch("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: UUID,
    activity_in: ActivityUpdate,
    db: DbSession,
) -> ActivityResponse:
    """Update an existing activity."""
    repo = ActivityRepository(db)
    activity = await repo.get_by_id(activity_id)

    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")

    updated = await repo.update(
        activity,
        activity_in.model_dump(exclude_unset=True),
    )
    await db.commit()

    return ActivityResponse.model_validate(updated)


@router.delete("/{activity_id}", status_code=204)
async def delete_activity(
    activity_id: UUID,
    db: DbSession,
) -> None:
    """Delete an activity."""
    repo = ActivityRepository(db)
    activity = await repo.get_by_id(activity_id)

    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")

    await repo.delete(activity)
    await db.commit()
