"""WBS Element endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.core.deps import DbSession
from src.core.exceptions import NotFoundError
from src.repositories.program import ProgramRepository
from src.repositories.wbs import WBSElementRepository
from src.schemas.errors import (
    AuthenticationErrorResponse,
    NotFoundErrorResponse,
    RateLimitErrorResponse,
    ValidationErrorResponse,
)
from src.schemas.wbs import (
    WBSElementCreate,
    WBSElementResponse,
    WBSElementTreeResponse,
    WBSElementUpdate,
    WBSListResponse,
)

router = APIRouter(tags=["WBS"])


@router.get(
    "",
    response_model=WBSListResponse,
    summary="List WBS Elements",
    responses={
        200: {"description": "WBS elements retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def list_wbs_elements(
    db: DbSession,
    program_id: Annotated[UUID, Query(description="Filter by program ID")],
) -> WBSListResponse:
    """List all WBS elements for a program."""
    repo = WBSElementRepository(db)
    elements = await repo.get_by_program(program_id)

    return WBSListResponse(
        items=[WBSElementResponse.model_validate(e) for e in elements],
        total=len(elements),
        page=1,
        page_size=len(elements) if elements else 1,
    )


@router.get(
    "/tree",
    response_model=list[WBSElementTreeResponse],
    summary="Get WBS Tree",
    responses={
        200: {"description": "WBS tree retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def get_wbs_tree(
    db: DbSession,
    program_id: Annotated[UUID, Query(description="Program ID")],
) -> list[WBSElementTreeResponse]:
    """Get WBS elements as a hierarchical tree structure."""
    repo = WBSElementRepository(db)
    tree = await repo.get_tree(program_id)

    return [WBSElementTreeResponse.model_validate(e) for e in tree]


@router.get(
    "/{element_id}",
    response_model=WBSElementResponse,
    summary="Get WBS Element",
    responses={
        200: {"description": "WBS element retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "WBS element not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def get_wbs_element(
    element_id: UUID,
    db: DbSession,
) -> WBSElementResponse:
    """Get a single WBS element by ID."""
    repo = WBSElementRepository(db)
    element = await repo.get_by_id(element_id)

    if not element:
        raise NotFoundError(f"WBS element {element_id} not found", "WBS_NOT_FOUND")

    return WBSElementResponse.model_validate(element)


@router.post(
    "",
    response_model=WBSElementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create WBS Element",
    responses={
        201: {"description": "WBS element created successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Program or parent WBS not found"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def create_wbs_element(
    element_in: WBSElementCreate,
    db: DbSession,
) -> WBSElementResponse:
    """Create a new WBS element."""
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(element_in.program_id)
    if not program:
        raise NotFoundError(
            f"Program {element_in.program_id} not found",
            "PROGRAM_NOT_FOUND",
        )

    wbs_repo = WBSElementRepository(db)

    # Get wbs_code - auto-generate if not provided
    wbs_code = element_in.wbs_code
    if not wbs_code:
        wbs_code = await _generate_wbs_code(wbs_repo, element_in.program_id, element_in.parent_id)

    # Build path based on parent
    if element_in.parent_id:
        parent = await wbs_repo.get_by_id(element_in.parent_id)
        if not parent:
            raise NotFoundError(
                f"Parent WBS element {element_in.parent_id} not found",
                "PARENT_WBS_NOT_FOUND",
            )
        path = f"{parent.path}.{wbs_code}"
        level = parent.level + 1
    else:
        path = wbs_code
        level = 1

    element_data = element_in.model_dump()
    element_data["wbs_code"] = wbs_code
    element_data["path"] = path
    element_data["level"] = level

    element = await wbs_repo.create(element_data)
    await db.commit()

    return WBSElementResponse.model_validate(element)


@router.patch(
    "/{element_id}",
    response_model=WBSElementResponse,
    summary="Update WBS Element",
    responses={
        200: {"description": "WBS element updated successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "WBS element not found"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def update_wbs_element(
    element_id: UUID,
    element_in: WBSElementUpdate,
    db: DbSession,
) -> WBSElementResponse:
    """Update an existing WBS element."""
    repo = WBSElementRepository(db)
    element = await repo.get_by_id(element_id)

    if not element:
        raise NotFoundError(f"WBS element {element_id} not found", "WBS_NOT_FOUND")

    updated = await repo.update(
        element,
        element_in.model_dump(exclude_unset=True),
    )
    await db.commit()

    return WBSElementResponse.model_validate(updated)


@router.delete(
    "/{element_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete WBS Element",
    responses={
        204: {"description": "WBS element deleted successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "WBS element not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def delete_wbs_element(
    element_id: UUID,
    db: DbSession,
) -> None:
    """Delete a WBS element and all its children."""
    repo = WBSElementRepository(db)
    element = await repo.get_by_id(element_id)

    if not element:
        raise NotFoundError(f"WBS element {element_id} not found", "WBS_NOT_FOUND")

    await repo.delete(element.id)
    await db.commit()


async def _generate_wbs_code(
    repo: WBSElementRepository,
    program_id: UUID,
    parent_id: UUID | None,
) -> str:
    """Auto-generate a hierarchical WBS code.

    For root elements: finds the next available integer (1, 2, 3...).
    For child elements: appends the next available sub-number to parent's code
    (e.g., parent "1.2" -> child "1.2.1", "1.2.2", etc.).

    Args:
        repo: WBS element repository
        program_id: Program ID for the new element
        parent_id: Parent element ID (None for root)

    Returns:
        Auto-generated WBS code string
    """
    if parent_id:
        parent = await repo.get_by_id(parent_id)
        if not parent:
            raise NotFoundError(
                f"Parent WBS element {parent_id} not found",
                "PARENT_WBS_NOT_FOUND",
            )
        siblings = await repo.get_children(parent_id)
        parent_code = parent.wbs_code
    else:
        siblings = await repo.get_root_elements(program_id)
        parent_code = ""

    # Find the highest existing numeric suffix among siblings
    max_num = 0
    for sibling in siblings:
        code = sibling.wbs_code
        # Extract the last segment of the code
        if parent_code:
            suffix = code[len(parent_code) + 1:] if code.startswith(parent_code + ".") else code
        else:
            suffix = code

        # Try to parse the suffix as integer
        try:
            num = int(suffix)
            max_num = max(max_num, num)
        except ValueError:
            continue

    next_num = max_num + 1

    if parent_code:
        return f"{parent_code}.{next_num}"
    return str(next_num)
