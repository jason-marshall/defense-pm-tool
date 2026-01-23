"""API endpoints for Baseline management."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import NotFoundError, ValidationError
from src.repositories.baseline import BaselineRepository
from src.repositories.program import ProgramRepository
from src.schemas.baseline import (
    BaselineApprove,
    BaselineCreate,
    BaselineListResponse,
    BaselineResponse,
    BaselineSummary,
    BaselineUpdate,
)
from src.schemas.errors import (
    AuthenticationErrorResponse,
    NotFoundErrorResponse,
    RateLimitErrorResponse,
    ValidationErrorResponse,
)

router = APIRouter(prefix="/baselines", tags=["Baselines"])

# Note: DbSession and CurrentUser imported from src.core.deps


@router.get(
    "",
    response_model=BaselineListResponse,
    summary="List Baselines",
    responses={
        200: {"description": "Baselines retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Program not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def list_baselines(
    db: DbSession,
    current_user: CurrentUser,
    program_id: UUID = Query(..., description="Program ID to list baselines for"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
) -> BaselineListResponse:
    """
    List all baselines for a program.

    Returns baselines ordered by version (newest first), without
    snapshot data for faster response.
    """
    # Verify program exists and user has access
    program_repo = ProgramRepository(db)
    program = await program_repo.get(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    repo = BaselineRepository(db)
    skip = (page - 1) * per_page

    baselines = await repo.get_by_program(program_id, skip=skip, limit=per_page)
    total = await repo.count_by_program(program_id)

    return BaselineListResponse(
        items=[BaselineSummary.model_validate(b) for b in baselines],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 1,
    )


@router.post(
    "",
    response_model=BaselineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Baseline",
    responses={
        201: {"description": "Baseline created successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Program not found"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def create_baseline(
    db: DbSession,
    current_user: CurrentUser,
    baseline_data: BaselineCreate,
) -> BaselineResponse:
    """
    Create a new baseline snapshot for a program.

    This captures the current state of the program's schedule,
    cost, and WBS data into an immutable baseline record.

    The baseline version is automatically incremented.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get(baseline_data.program_id)
    if not program:
        raise NotFoundError(
            f"Program {baseline_data.program_id} not found",
            "PROGRAM_NOT_FOUND",
        )

    repo = BaselineRepository(db)
    baseline = await repo.create_snapshot(
        program_id=baseline_data.program_id,
        name=baseline_data.name,
        description=baseline_data.description,
        created_by_id=current_user.id,
        include_schedule=baseline_data.include_schedule,
        include_cost=baseline_data.include_cost,
        include_wbs=baseline_data.include_wbs,
    )

    await db.commit()
    await db.refresh(baseline)

    return BaselineResponse.model_validate(baseline)


@router.get(
    "/{baseline_id}",
    response_model=BaselineResponse,
    summary="Get Baseline",
    responses={
        200: {"description": "Baseline retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Baseline not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def get_baseline(
    db: DbSession,
    current_user: CurrentUser,
    baseline_id: UUID,
    include_snapshots: bool = Query(True, description="Include full snapshot data in response"),
) -> BaselineResponse:
    """
    Get a specific baseline by ID.

    Use include_snapshots=false for faster response when only
    metadata is needed.
    """
    repo = BaselineRepository(db)
    baseline = await repo.get(baseline_id)

    if not baseline:
        raise NotFoundError(f"Baseline {baseline_id} not found", "BASELINE_NOT_FOUND")

    response = BaselineResponse.model_validate(baseline)

    # Optionally exclude snapshot data
    if not include_snapshots:
        response.schedule_snapshot = None
        response.cost_snapshot = None
        response.wbs_snapshot = None

    return response


@router.patch(
    "/{baseline_id}",
    response_model=BaselineResponse,
    summary="Update Baseline",
    responses={
        200: {"description": "Baseline updated successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Baseline not found"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def update_baseline(
    db: DbSession,
    current_user: CurrentUser,
    baseline_id: UUID,
    update_data: BaselineUpdate,
) -> BaselineResponse:
    """
    Update baseline metadata (name/description only).

    Snapshot data cannot be modified - baselines are immutable.
    To capture new data, create a new baseline.
    """
    repo = BaselineRepository(db)
    baseline = await repo.get(baseline_id)

    if not baseline:
        raise NotFoundError(f"Baseline {baseline_id} not found", "BASELINE_NOT_FOUND")

    # Update only allowed fields
    update_dict = update_data.model_dump(exclude_unset=True)
    if update_dict:
        for key, value in update_dict.items():
            setattr(baseline, key, value)

    await db.commit()
    await db.refresh(baseline)

    return BaselineResponse.model_validate(baseline)


@router.delete(
    "/{baseline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Baseline",
    responses={
        204: {"description": "Baseline deleted successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Baseline not found"},
        422: {"model": ValidationErrorResponse, "description": "Cannot delete approved baseline"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def delete_baseline(
    db: DbSession,
    current_user: CurrentUser,
    baseline_id: UUID,
) -> None:
    """
    Soft delete a baseline.

    Approved baselines cannot be deleted - unapprove first.
    """
    repo = BaselineRepository(db)
    baseline = await repo.get(baseline_id)

    if not baseline:
        raise NotFoundError(f"Baseline {baseline_id} not found", "BASELINE_NOT_FOUND")

    if baseline.is_approved:
        raise ValidationError(
            "Cannot delete approved baseline. Unapprove first.",
            "APPROVED_BASELINE_DELETE",
        )

    await repo.delete(baseline_id)
    await db.commit()


@router.post(
    "/{baseline_id}/approve",
    response_model=BaselineResponse,
    summary="Approve Baseline",
    responses={
        200: {"description": "Baseline approved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Baseline not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def approve_baseline(
    db: DbSession,
    current_user: CurrentUser,
    baseline_id: UUID,
    approval_data: BaselineApprove | None = None,
) -> BaselineResponse:
    """
    Approve a baseline as the Performance Measurement Baseline (PMB).

    Only one baseline per program can be approved at a time.
    Approving a new baseline automatically unapproves the previous one.
    """
    repo = BaselineRepository(db)
    baseline = await repo.approve_baseline(baseline_id, current_user.id)

    if not baseline:
        raise NotFoundError(f"Baseline {baseline_id} not found", "BASELINE_NOT_FOUND")

    await db.commit()
    await db.refresh(baseline)

    return BaselineResponse.model_validate(baseline)


@router.post(
    "/{baseline_id}/unapprove",
    response_model=BaselineResponse,
    summary="Unapprove Baseline",
    responses={
        200: {"description": "Baseline unapproved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Baseline not found"},
        422: {"model": ValidationErrorResponse, "description": "Baseline is not approved"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def unapprove_baseline(
    db: DbSession,
    current_user: CurrentUser,
    baseline_id: UUID,
) -> BaselineResponse:
    """
    Remove approval from a baseline.

    This removes the PMB designation from the baseline.
    """
    repo = BaselineRepository(db)
    baseline = await repo.get(baseline_id)

    if not baseline:
        raise NotFoundError(f"Baseline {baseline_id} not found", "BASELINE_NOT_FOUND")

    if not baseline.is_approved:
        raise ValidationError(
            "Baseline is not currently approved",
            "BASELINE_NOT_APPROVED",
        )

    baseline.is_approved = False
    baseline.approved_at = None
    baseline.approved_by_id = None

    await db.commit()
    await db.refresh(baseline)

    return BaselineResponse.model_validate(baseline)


@router.get(
    "/{baseline_id}/compare",
    summary="Compare Baseline",
    responses={
        200: {"description": "Baseline comparison returned successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Baseline not found"},
        422: {"model": ValidationErrorResponse, "description": "Baseline has no snapshot data"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def compare_baseline(
    db: DbSession,
    current_user: CurrentUser,
    baseline_id: UUID,
    include_details: bool = Query(True, description="Include detailed activity/WBS variances"),
) -> dict[str, Any]:
    """
    Compare a baseline to the current program state.

    Returns variance analysis including:
    - Schedule variance (project finish, activity dates)
    - Cost variance (BAC changes)
    - Scope changes (activities/WBS added, removed, modified)
    - Critical path changes

    Use include_details=false for summary only (faster response).
    """
    from src.services.baseline_comparison import (
        BaselineComparisonService,
        comparison_result_to_dict,
    )

    repo = BaselineRepository(db)
    baseline = await repo.get(baseline_id)

    if not baseline:
        raise NotFoundError(f"Baseline {baseline_id} not found", "BASELINE_NOT_FOUND")

    if not baseline.schedule_snapshot and not baseline.cost_snapshot:
        raise ValidationError(
            "Baseline has no snapshot data to compare",
            "BASELINE_NO_SNAPSHOT",
        )

    service = BaselineComparisonService(db)
    result = await service.compare_to_current(baseline, include_details)

    return comparison_result_to_dict(result)


@router.get(
    "/program/{program_id}/approved",
    response_model=BaselineResponse | None,
    summary="Get Approved Baseline",
    responses={
        200: {"description": "Approved baseline returned (or null if none)"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Program not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def get_approved_baseline(
    db: DbSession,
    current_user: CurrentUser,
    program_id: UUID,
) -> BaselineResponse | None:
    """
    Get the approved (PMB) baseline for a program.

    Returns null if no baseline is currently approved.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    repo = BaselineRepository(db)
    baseline = await repo.get_approved_baseline(program_id)

    if not baseline:
        return None

    return BaselineResponse.model_validate(baseline)
