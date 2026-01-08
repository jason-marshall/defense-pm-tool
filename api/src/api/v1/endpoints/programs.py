"""Program endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.core.deps import get_db, DbSession
from src.core.exceptions import ConflictError, NotFoundError
from src.repositories.program import ProgramRepository
from src.schemas.program import (
    ProgramCreate,
    ProgramListResponse,
    ProgramResponse,
    ProgramUpdate,
)

router = APIRouter()


@router.get("", response_model=ProgramListResponse)
async def list_programs(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProgramListResponse:
    """List all programs with pagination."""
    repo = ProgramRepository(db)
    skip = (page - 1) * page_size

    programs = await repo.get_all(skip=skip, limit=page_size)
    total = await repo.count()

    return ProgramListResponse(
        items=[ProgramResponse.model_validate(p) for p in programs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{program_id}", response_model=ProgramResponse)
async def get_program(
    program_id: UUID,
    db: DbSession,
) -> ProgramResponse:
    """Get a single program by ID."""
    repo = ProgramRepository(db)
    program = await repo.get_by_id(program_id)

    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    return ProgramResponse.model_validate(program)


@router.post("", response_model=ProgramResponse, status_code=201)
async def create_program(
    program_in: ProgramCreate,
    db: DbSession,
) -> ProgramResponse:
    """Create a new program."""
    repo = ProgramRepository(db)

    # Check for duplicate code
    if await repo.code_exists(program_in.code):
        raise ConflictError(
            f"Program with code '{program_in.code}' already exists",
            "DUPLICATE_PROGRAM_CODE",
        )

    program = await repo.create(program_in.model_dump())
    await db.commit()

    return ProgramResponse.model_validate(program)


@router.patch("/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: UUID,
    program_in: ProgramUpdate,
    db: DbSession,
) -> ProgramResponse:
    """Update an existing program."""
    repo = ProgramRepository(db)
    program = await repo.get_by_id(program_id)

    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    updated = await repo.update(
        program,
        program_in.model_dump(exclude_unset=True),
    )
    await db.commit()

    return ProgramResponse.model_validate(updated)


@router.delete("/{program_id}", status_code=204)
async def delete_program(
    program_id: UUID,
    db: DbSession,
) -> None:
    """Delete a program."""
    repo = ProgramRepository(db)
    program = await repo.get_by_id(program_id)

    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    await repo.delete(program)
    await db.commit()
