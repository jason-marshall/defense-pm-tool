"""Program endpoints with authentication and authorization."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.core.deps import DbSession, get_current_user
from src.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from src.models.user import User
from src.repositories.program import ProgramRepository
from src.schemas.errors import (
    AuthenticationErrorResponse,
    AuthorizationErrorResponse,
    ConflictErrorResponse,
    NotFoundErrorResponse,
    RateLimitErrorResponse,
    ValidationErrorResponse,
)
from src.schemas.program import (
    ProgramCreate,
    ProgramListResponse,
    ProgramResponse,
    ProgramUpdate,
)

router = APIRouter(tags=["Programs"])


@router.get(
    "",
    response_model=ProgramListResponse,
    summary="List Programs",
    responses={
        200: {"description": "List of programs retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def list_programs(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> ProgramListResponse:
    """
    List programs accessible to the current user.

    **Authorization:**
    - Admins can see all programs
    - Regular users only see programs they own

    **Pagination:**
    - Use `page` and `page_size` query parameters
    - Maximum 100 items per page

    **Rate limit:** 100/minute
    """
    repo = ProgramRepository(db)
    skip = (page - 1) * page_size

    programs, total = await repo.get_accessible_programs(
        user_id=current_user.id,
        is_admin=current_user.is_admin,
        skip=skip,
        limit=page_size,
    )

    return ProgramListResponse(
        items=[ProgramResponse.model_validate(p) for p in programs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{program_id}",
    response_model=ProgramResponse,
    summary="Get Program",
    responses={
        200: {"description": "Program details retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {
            "model": AuthorizationErrorResponse,
            "description": "Not authorized to view this program",
        },
        404: {"model": NotFoundErrorResponse, "description": "Program not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def get_program(
    program_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProgramResponse:
    """
    Get a single program by ID.

    **Authorization:**
    - Users can only view programs they own
    - Admins can view any program

    **Rate limit:** 100/minute
    """
    repo = ProgramRepository(db)
    program = await repo.get_by_id(program_id)

    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Authorization check
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to view this program",
            "PROGRAM_ACCESS_DENIED",
        )

    return ProgramResponse.model_validate(program)


@router.post(
    "",
    response_model=ProgramResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Program",
    responses={
        201: {"description": "Program created successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        409: {"model": ConflictErrorResponse, "description": "Program code already exists"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def create_program(
    program_in: ProgramCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProgramResponse:
    """
    Create a new program.

    **Authorization:**
    - Any authenticated user can create programs
    - The current user is automatically set as the program owner

    **Validation:**
    - Program code must be unique across all programs
    - Code is automatically uppercased
    - end_date must be after start_date

    **Rate limit:** 100/minute
    """
    repo = ProgramRepository(db)

    # Check for duplicate code
    if await repo.code_exists(program_in.code):
        raise ConflictError(
            f"Program with code '{program_in.code}' already exists",
            "DUPLICATE_PROGRAM_CODE",
        )

    # Create program with current user as owner
    program_data = program_in.model_dump()
    program_data["owner_id"] = current_user.id

    program = await repo.create(program_data)
    await db.commit()
    await db.refresh(program)

    return ProgramResponse.model_validate(program)


@router.patch(
    "/{program_id}",
    response_model=ProgramResponse,
    summary="Update Program",
    responses={
        200: {"description": "Program updated successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {
            "model": AuthorizationErrorResponse,
            "description": "Not authorized to modify this program",
        },
        404: {"model": NotFoundErrorResponse, "description": "Program not found"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def update_program(
    program_id: UUID,
    program_in: ProgramUpdate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProgramResponse:
    """
    Update an existing program.

    **Authorization:**
    - Users can only update programs they own
    - Admins can update any program

    **Partial update:**
    - Only fields included in the request body are updated
    - Omitted fields retain their current values

    **Rate limit:** 100/minute
    """
    repo = ProgramRepository(db)
    program = await repo.get_by_id(program_id)

    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Authorization check
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to modify this program",
            "PROGRAM_MODIFICATION_DENIED",
        )

    updated = await repo.update(
        program,
        program_in.model_dump(exclude_unset=True),
    )
    await db.commit()

    return ProgramResponse.model_validate(updated)


@router.delete(
    "/{program_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Program",
    responses={
        204: {"description": "Program deleted successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {
            "model": AuthorizationErrorResponse,
            "description": "Not authorized to delete this program",
        },
        404: {"model": NotFoundErrorResponse, "description": "Program not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def delete_program(
    program_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Delete a program (soft delete).

    **Authorization:**
    - Users can only delete programs they own
    - Admins can delete any program

    **Note:** This performs a soft delete - the program is marked as deleted
    but remains in the database for audit purposes.

    **Rate limit:** 100/minute
    """
    repo = ProgramRepository(db)
    program = await repo.get_by_id(program_id)

    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Authorization check
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to delete this program",
            "PROGRAM_DELETION_DENIED",
        )

    await repo.delete(program_id)
    await db.commit()
