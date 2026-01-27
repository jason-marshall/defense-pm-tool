"""Resource management endpoints with authentication."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.models.enums import ResourceType
from src.models.resource import Resource
from src.repositories.activity import ActivityRepository
from src.repositories.program import ProgramRepository
from src.repositories.resource import (
    ResourceAssignmentRepository,
    ResourceCalendarRepository,
    ResourceRepository,
)
from src.schemas.common import MessageResponse
from src.schemas.errors import (
    AuthenticationErrorResponse,
    AuthorizationErrorResponse,
    ConflictErrorResponse,
    NotFoundErrorResponse,
    RateLimitErrorResponse,
    ValidationErrorResponse,
)
from src.schemas.resource import (
    ResourceAssignmentCreate,
    ResourceAssignmentListResponse,
    ResourceAssignmentResponse,
    ResourceAssignmentUpdate,
    ResourceCalendarBulkCreate,
    ResourceCalendarRangeResponse,
    ResourceCalendarResponse,
    ResourceCreate,
    ResourceListResponse,
    ResourceResponse,
    ResourceUpdate,
)

# =============================================================================
# Resources Router
# =============================================================================

router = APIRouter(prefix="/resources", tags=["Resources"])


async def _verify_program_access(
    db: DbSession,
    program_id: UUID,
    current_user: CurrentUser,
) -> None:
    """Verify user has access to the program."""
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to access this program's resources",
            "NOT_AUTHORIZED",
        )


async def _get_resource_with_access(
    db: DbSession,
    resource_id: UUID,
    current_user: CurrentUser,
) -> Resource:
    """Get resource and verify access."""
    repo = ResourceRepository(db)
    resource = await repo.get_by_id(resource_id)

    if not resource:
        raise NotFoundError(f"Resource {resource_id} not found", "RESOURCE_NOT_FOUND")

    await _verify_program_access(db, resource.program_id, current_user)
    return resource


# =============================================================================
# Resource CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Resource",
    responses={
        201: {"description": "Resource created successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Program not found"},
        409: {"model": ConflictErrorResponse, "description": "Resource code already exists"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def create_resource(
    resource_in: ResourceCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> ResourceResponse:
    """
    Create a new resource.

    **Authorization:**
    - Users can only create resources in programs they own
    - Admins can create resources in any program

    **Validation:**
    - Resource code must be unique within the program
    """
    await _verify_program_access(db, resource_in.program_id, current_user)

    repo = ResourceRepository(db)

    # Check for duplicate code
    if await repo.code_exists(resource_in.program_id, resource_in.code):
        raise ConflictError(
            f"Resource code '{resource_in.code}' already exists in this program",
            "DUPLICATE_RESOURCE_CODE",
        )

    resource = await repo.create(resource_in.model_dump())
    await db.commit()

    return ResourceResponse.model_validate(resource)


@router.get(
    "",
    response_model=ResourceListResponse,
    summary="List Resources",
    responses={
        200: {"description": "Resources list retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Program not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def list_resources(
    db: DbSession,
    current_user: CurrentUser,
    program_id: Annotated[UUID, Query(description="Filter by program ID (required)")],
    resource_type: Annotated[
        ResourceType | None, Query(description="Filter by resource type")
    ] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active status")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
) -> ResourceListResponse:
    """
    List all resources for a program with pagination and filters.

    **Authorization:**
    - Users can only view resources from programs they own
    - Admins can view resources from any program
    """
    await _verify_program_access(db, program_id, current_user)

    repo = ResourceRepository(db)
    skip = (page - 1) * page_size

    resources, total = await repo.get_by_program(
        program_id,
        resource_type=resource_type,
        is_active=is_active,
        skip=skip,
        limit=page_size,
    )

    pages = (total + page_size - 1) // page_size if total > 0 else 0

    return ResourceListResponse(
        items=[ResourceResponse.model_validate(r) for r in resources],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{resource_id}",
    response_model=ResourceResponse,
    summary="Get Resource",
    responses={
        200: {"description": "Resource retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Resource not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def get_resource(
    resource_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ResourceResponse:
    """
    Get a single resource by ID.

    **Authorization:**
    - Users can only view resources from programs they own
    - Admins can view any resource
    """
    resource = await _get_resource_with_access(db, resource_id, current_user)
    return ResourceResponse.model_validate(resource)


@router.put(
    "/{resource_id}",
    response_model=ResourceResponse,
    summary="Update Resource",
    responses={
        200: {"description": "Resource updated successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Resource not found"},
        409: {"model": ConflictErrorResponse, "description": "Resource code already exists"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def update_resource(
    resource_id: UUID,
    resource_in: ResourceUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ResourceResponse:
    """
    Update an existing resource.

    **Authorization:**
    - Users can only update resources in programs they own
    - Admins can update any resource

    **Validation:**
    - If changing code, it must be unique within the program
    """
    resource = await _get_resource_with_access(db, resource_id, current_user)

    repo = ResourceRepository(db)

    # Check for duplicate code if changing
    if (
        resource_in.code
        and resource_in.code.upper() != resource.code
        and await repo.code_exists(resource.program_id, resource_in.code, exclude_id=resource_id)
    ):
        raise ConflictError(
            f"Resource code '{resource_in.code}' already exists in this program",
            "DUPLICATE_RESOURCE_CODE",
        )

    update_data = resource_in.model_dump(exclude_unset=True)
    updated = await repo.update(resource, update_data)
    await db.commit()

    return ResourceResponse.model_validate(updated)


@router.delete(
    "/{resource_id}",
    response_model=MessageResponse,
    summary="Delete Resource",
    responses={
        200: {"description": "Resource deleted successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Resource not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def delete_resource(
    resource_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> MessageResponse:
    """
    Soft delete a resource.

    **Authorization:**
    - Users can only delete resources in programs they own
    - Admins can delete any resource

    **Note:** This cascades to assignments and calendar entries.
    """
    await _get_resource_with_access(db, resource_id, current_user)

    repo = ResourceRepository(db)
    await repo.delete(resource_id)
    await db.commit()

    return MessageResponse(message="Resource deleted successfully")


# =============================================================================
# Resource Assignment Endpoints (nested under resource)
# =============================================================================


@router.post(
    "/{resource_id}/assignments",
    response_model=ResourceAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Resource Assignment",
    responses={
        201: {"description": "Assignment created successfully"},
        400: {"model": ValidationErrorResponse, "description": "Invalid assignment"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Resource or activity not found"},
        409: {"model": ConflictErrorResponse, "description": "Assignment already exists"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def create_assignment(
    resource_id: UUID,
    assignment_in: ResourceAssignmentCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> ResourceAssignmentResponse:
    """
    Create a resource assignment.

    **Authorization:**
    - Users can only create assignments in programs they own
    - Admins can create assignments in any program

    **Validation:**
    - Resource and activity must be in the same program
    - No duplicate assignments (same activity + resource)
    """
    # Verify resource access
    resource = await _get_resource_with_access(db, resource_id, current_user)

    # Override resource_id from path
    if assignment_in.resource_id != resource_id:
        assignment_in = assignment_in.model_copy(update={"resource_id": resource_id})

    # Verify activity exists and is in same program
    activity_repo = ActivityRepository(db)
    activity = await activity_repo.get_by_id(assignment_in.activity_id)

    if not activity:
        raise NotFoundError(f"Activity {assignment_in.activity_id} not found", "ACTIVITY_NOT_FOUND")

    if activity.program_id != resource.program_id:
        raise ValidationError(
            "Activity and resource must be in the same program",
            "CROSS_PROGRAM_ASSIGNMENT",
        )

    # Check for duplicate assignment
    assignment_repo = ResourceAssignmentRepository(db)
    if await assignment_repo.assignment_exists(assignment_in.activity_id, resource_id):
        raise ConflictError(
            "Assignment already exists for this activity and resource",
            "DUPLICATE_ASSIGNMENT",
        )

    assignment = await assignment_repo.create(assignment_in.model_dump())
    await db.commit()

    # Reload with resource for response
    await db.refresh(assignment)
    return ResourceAssignmentResponse.model_validate(assignment)


@router.get(
    "/{resource_id}/assignments",
    response_model=ResourceAssignmentListResponse,
    summary="List Resource Assignments",
    responses={
        200: {"description": "Assignments retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Resource not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def list_resource_assignments(
    resource_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    start_date: Annotated[date | None, Query(description="Filter by start date")] = None,
    end_date: Annotated[date | None, Query(description="Filter by end date")] = None,
) -> ResourceAssignmentListResponse:
    """
    List all assignments for a resource.

    **Authorization:**
    - Users can only view assignments from programs they own
    - Admins can view any assignments
    """
    await _get_resource_with_access(db, resource_id, current_user)

    repo = ResourceAssignmentRepository(db)
    assignments = await repo.get_by_resource(resource_id, start_date=start_date, end_date=end_date)

    return ResourceAssignmentListResponse(
        items=[ResourceAssignmentResponse.model_validate(a) for a in assignments],
        total=len(assignments),
    )


# =============================================================================
# Resource Calendar Endpoints
# =============================================================================


@router.get(
    "/{resource_id}/calendar",
    response_model=ResourceCalendarRangeResponse,
    summary="Get Resource Calendar",
    responses={
        200: {"description": "Calendar retrieved successfully"},
        400: {"model": ValidationErrorResponse, "description": "Invalid date range"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Resource not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def get_resource_calendar(
    resource_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    start_date: Annotated[date, Query(description="Start date (required)")],
    end_date: Annotated[date, Query(description="End date (required)")],
) -> ResourceCalendarRangeResponse:
    """
    Get calendar entries for a resource within a date range.

    **Authorization:**
    - Users can only view calendars from programs they own
    - Admins can view any calendars
    """
    if end_date < start_date:
        raise ValidationError(
            "end_date must be greater than or equal to start_date",
            "INVALID_DATE_RANGE",
        )

    await _get_resource_with_access(db, resource_id, current_user)

    repo = ResourceCalendarRepository(db)
    entries = await repo.get_for_date_range(resource_id, start_date, end_date)
    working_days = await repo.get_working_days_count(resource_id, start_date, end_date)
    total_hours = await repo.get_total_hours(resource_id, start_date, end_date)

    return ResourceCalendarRangeResponse(
        resource_id=resource_id,
        start_date=start_date,
        end_date=end_date,
        entries=[ResourceCalendarResponse.model_validate(e) for e in entries],
        working_days=working_days,
        total_hours=total_hours,
    )


@router.post(
    "/{resource_id}/calendar",
    response_model=list[ResourceCalendarResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk Create Calendar Entries",
    responses={
        201: {"description": "Calendar entries created successfully"},
        400: {"model": ValidationErrorResponse, "description": "Invalid entries"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Resource not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def create_calendar_entries(
    resource_id: UUID,
    calendar_in: ResourceCalendarBulkCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> list[ResourceCalendarResponse]:
    """
    Bulk create calendar entries for a resource.

    **Authorization:**
    - Users can only create calendars in programs they own
    - Admins can create calendars in any program

    **Note:** Existing entries for the same dates will be replaced.
    """
    await _get_resource_with_access(db, resource_id, current_user)

    # Override resource_id from path
    if calendar_in.resource_id != resource_id:
        calendar_in = calendar_in.model_copy(update={"resource_id": resource_id})

    repo = ResourceCalendarRepository(db)

    # Delete existing entries for these dates
    dates = [e.calendar_date for e in calendar_in.entries]
    if dates:
        min_date = min(dates)
        max_date = max(dates)
        await repo.delete_range(resource_id, min_date, max_date)

    # Create new entries
    entries_data = [
        {
            "resource_id": resource_id,
            "calendar_date": e.calendar_date,
            "available_hours": e.available_hours,
            "is_working_day": e.is_working_day,
        }
        for e in calendar_in.entries
    ]

    entries = await repo.bulk_create_entries(entries_data)
    await db.commit()

    return [ResourceCalendarResponse.model_validate(e) for e in entries]


@router.delete(
    "/{resource_id}/calendar",
    response_model=MessageResponse,
    summary="Delete Calendar Range",
    responses={
        200: {"description": "Calendar entries deleted successfully"},
        400: {"model": ValidationErrorResponse, "description": "Invalid date range"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Resource not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def delete_calendar_range(
    resource_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    start_date: Annotated[date, Query(description="Start date (required)")],
    end_date: Annotated[date, Query(description="End date (required)")],
) -> MessageResponse:
    """
    Delete calendar entries for a resource within a date range.

    **Authorization:**
    - Users can only delete calendars from programs they own
    - Admins can delete any calendars
    """
    if end_date < start_date:
        raise ValidationError(
            "end_date must be greater than or equal to start_date",
            "INVALID_DATE_RANGE",
        )

    await _get_resource_with_access(db, resource_id, current_user)

    repo = ResourceCalendarRepository(db)
    deleted_count = await repo.delete_range(resource_id, start_date, end_date)
    await db.commit()

    return MessageResponse(message=f"Deleted {deleted_count} calendar entries")


# =============================================================================
# Assignments Router (standalone)
# =============================================================================

assignments_router = APIRouter(prefix="/assignments", tags=["Resource Assignments"])


@assignments_router.get(
    "/{assignment_id}",
    response_model=ResourceAssignmentResponse,
    summary="Get Assignment",
    responses={
        200: {"description": "Assignment retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Assignment not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def get_assignment(
    assignment_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ResourceAssignmentResponse:
    """
    Get a single assignment by ID.

    **Authorization:**
    - Users can only view assignments from programs they own
    - Admins can view any assignment
    """
    repo = ResourceAssignmentRepository(db)
    assignment = await repo.get_by_id(assignment_id)

    if not assignment:
        raise NotFoundError(f"Assignment {assignment_id} not found", "ASSIGNMENT_NOT_FOUND")

    # Verify access through resource
    resource_repo = ResourceRepository(db)
    resource = await resource_repo.get_by_id(assignment.resource_id)
    if resource:
        await _verify_program_access(db, resource.program_id, current_user)

    return ResourceAssignmentResponse.model_validate(assignment)


@assignments_router.put(
    "/{assignment_id}",
    response_model=ResourceAssignmentResponse,
    summary="Update Assignment",
    responses={
        200: {"description": "Assignment updated successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Assignment not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def update_assignment(
    assignment_id: UUID,
    assignment_in: ResourceAssignmentUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ResourceAssignmentResponse:
    """
    Update an existing assignment.

    **Authorization:**
    - Users can only update assignments in programs they own
    - Admins can update any assignment
    """
    repo = ResourceAssignmentRepository(db)
    assignment = await repo.get_by_id(assignment_id)

    if not assignment:
        raise NotFoundError(f"Assignment {assignment_id} not found", "ASSIGNMENT_NOT_FOUND")

    # Verify access through resource
    resource_repo = ResourceRepository(db)
    resource = await resource_repo.get_by_id(assignment.resource_id)
    if resource:
        await _verify_program_access(db, resource.program_id, current_user)

    update_data = assignment_in.model_dump(exclude_unset=True)
    updated = await repo.update(assignment, update_data)
    await db.commit()

    return ResourceAssignmentResponse.model_validate(updated)


@assignments_router.delete(
    "/{assignment_id}",
    response_model=MessageResponse,
    summary="Delete Assignment",
    responses={
        200: {"description": "Assignment deleted successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Assignment not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def delete_assignment(
    assignment_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> MessageResponse:
    """
    Delete an assignment.

    **Authorization:**
    - Users can only delete assignments in programs they own
    - Admins can delete any assignment
    """
    repo = ResourceAssignmentRepository(db)
    assignment = await repo.get_by_id(assignment_id)

    if not assignment:
        raise NotFoundError(f"Assignment {assignment_id} not found", "ASSIGNMENT_NOT_FOUND")

    # Verify access through resource
    resource_repo = ResourceRepository(db)
    resource = await resource_repo.get_by_id(assignment.resource_id)
    if resource:
        await _verify_program_access(db, resource.program_id, current_user)

    await repo.delete(assignment_id)
    await db.commit()

    return MessageResponse(message="Assignment deleted successfully")
