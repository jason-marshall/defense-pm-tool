"""Activity endpoints with authentication."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import AuthorizationError, NotFoundError
from src.repositories.activity import ActivityRepository
from src.repositories.program import ProgramRepository
from src.repositories.wbs import WBSElementRepository
from src.schemas.activity import (
    ActivityCreate,
    ActivityListResponse,
    ActivityResponse,
    ActivityUpdate,
)

router = APIRouter()


def generate_activity_code(existing_codes: list[str], prefix: str = "A") -> str:
    """
    Generate next activity code based on existing codes.

    Args:
        existing_codes: List of existing activity codes in the program
        prefix: Prefix for the code (default "A")

    Returns:
        Generated code like "A-001", "A-002", etc.
    """
    if not existing_codes:
        return f"{prefix}-001"

    # Extract numbers and find max
    numbers = []
    for code in existing_codes:
        try:
            num = int(code.split("-")[-1])
            numbers.append(num)
        except (ValueError, IndexError):
            continue

    next_num = max(numbers, default=0) + 1
    return f"{prefix}-{next_num:03d}"


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    db: DbSession,
    current_user: CurrentUser,
    program_id: Annotated[UUID, Query(description="Filter by program ID")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ActivityListResponse:
    """List all activities for a program with pagination."""
    # Verify user has access to program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Check authorization (owner or admin)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to view this program's activities",
            "NOT_AUTHORIZED",
        )

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
    current_user: CurrentUser,
) -> ActivityResponse:
    """Get a single activity by ID."""
    repo = ActivityRepository(db)
    activity = await repo.get_by_id(activity_id)

    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")

    # Verify access through program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity.program_id)

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to view this activity",
            "NOT_AUTHORIZED",
        )

    return ActivityResponse.model_validate(activity)


@router.post("", response_model=ActivityResponse, status_code=201)
async def create_activity(
    activity_in: ActivityCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> ActivityResponse:
    """Create a new activity."""
    # Verify program exists and user has access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity_in.program_id)
    if not program:
        raise NotFoundError(
            f"Program {activity_in.program_id} not found",
            "PROGRAM_NOT_FOUND",
        )

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to add activities to this program",
            "NOT_AUTHORIZED",
        )

    # Verify WBS element exists and belongs to the same program
    wbs_repo = WBSElementRepository(db)
    wbs_element = await wbs_repo.get_by_id(activity_in.wbs_id)
    if not wbs_element:
        raise NotFoundError(
            f"WBS element {activity_in.wbs_id} not found",
            "WBS_NOT_FOUND",
        )
    if wbs_element.program_id != activity_in.program_id:
        raise AuthorizationError(
            "WBS element does not belong to the specified program",
            "WBS_PROGRAM_MISMATCH",
        )

    activity_repo = ActivityRepository(db)

    # Auto-generate code if not provided
    activity_data = activity_in.model_dump()
    if not activity_data.get("code"):
        existing = await activity_repo.get_by_program(activity_in.program_id)
        existing_codes = [a.code for a in existing if a.code]
        activity_data["code"] = generate_activity_code(existing_codes)

    activity = await activity_repo.create(activity_data)
    await db.commit()
    await db.refresh(activity)

    return ActivityResponse.model_validate(activity)


@router.patch("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: UUID,
    activity_in: ActivityUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ActivityResponse:
    """Update an existing activity."""
    repo = ActivityRepository(db)
    activity = await repo.get_by_id(activity_id)

    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")

    # Verify access through program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity.program_id)

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to modify this activity",
            "NOT_AUTHORIZED",
        )

    updated = await repo.update(
        activity,
        activity_in.model_dump(exclude_unset=True),
    )
    await db.commit()
    await db.refresh(updated)

    return ActivityResponse.model_validate(updated)


@router.delete("/{activity_id}", status_code=204)
async def delete_activity(
    activity_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete an activity."""
    repo = ActivityRepository(db)
    activity = await repo.get_by_id(activity_id)

    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")

    # Verify access through program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity.program_id)

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to delete this activity",
            "NOT_AUTHORIZED",
        )

    await repo.delete(activity.id)
    await db.commit()
