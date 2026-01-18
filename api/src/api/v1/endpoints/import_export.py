"""Import/Export endpoints for schedule data."""

import tempfile
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile
from pydantic import BaseModel

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from src.repositories.program import ProgramRepository
from src.services.msproject_import import (
    MSProjectImporter,
    import_msproject_to_program,
)

router = APIRouter()


class ImportPreviewTask(BaseModel):
    """Task preview information."""

    name: str
    wbs: str
    duration_hours: float
    is_milestone: bool
    predecessors: int


class ImportPreviewResponse(BaseModel):
    """Response for import preview."""

    preview: bool = True
    project_name: str
    start_date: str
    finish_date: str
    task_count: int
    tasks: list[ImportPreviewTask]
    warnings: list[str]


class ImportResultResponse(BaseModel):
    """Response for import result."""

    success: bool
    program_id: str
    tasks_imported: int
    dependencies_imported: int
    wbs_elements_created: int
    warnings: list[str]
    errors: list[str]


@router.post(
    "/msproject/{program_id}",
    response_model=ImportResultResponse | ImportPreviewResponse,
)
async def import_msproject(
    program_id: UUID,
    file: Annotated[UploadFile, File(description="MS Project XML file")],
    db: DbSession,
    current_user: CurrentUser,
    preview: Annotated[bool, Query(description="Preview only, don't save")] = False,
) -> ImportResultResponse | ImportPreviewResponse:
    """
    Import MS Project XML file into a program.

    Supported formats:
    - MS Project 2010-2021 XML export (.xml)

    Imported data:
    - Tasks (as activities)
    - Predecessor links (as dependencies)
    - WBS structure
    - Milestones
    - Constraints

    Not imported (logged as warnings):
    - Resources and assignments
    - Calendars
    - Custom fields
    - Cost data

    Args:
        program_id: Target program ID
        file: MS Project XML file
        db: Database session
        current_user: Authenticated user
        preview: If True, only parse and preview without saving

    Returns:
        Import result or preview data
    """
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found")
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    # Validate file
    if not file.filename:
        raise ValidationError("No filename provided")

    if not file.filename.lower().endswith(".xml"):
        raise ValidationError("File must be MS Project XML format (.xml)")

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Parse file
        importer = MSProjectImporter(tmp_path)
        project = importer.parse()

        if preview:
            # Return preview only
            return ImportPreviewResponse(
                preview=True,
                project_name=project.name,
                start_date=project.start_date.isoformat(),
                finish_date=project.finish_date.isoformat(),
                task_count=len(project.tasks),
                tasks=[
                    ImportPreviewTask(
                        name=t.name,
                        wbs=t.wbs,
                        duration_hours=t.duration_hours,
                        is_milestone=t.is_milestone,
                        predecessors=len(t.predecessors),
                    )
                    for t in project.tasks[:20]  # First 20 only
                ],
                warnings=project.warnings,
            )

        # Reset importer for actual import
        importer = MSProjectImporter(tmp_path)

        # Import data
        stats = await import_msproject_to_program(
            importer,
            program_id,
            db,
        )

        return ImportResultResponse(
            success=True,
            program_id=str(program_id),
            tasks_imported=stats["tasks_imported"],
            dependencies_imported=stats["dependencies_imported"],
            wbs_elements_created=stats["wbs_elements_created"],
            warnings=stats["warnings"],
            errors=stats["errors"],
        )

    finally:
        # Clean up temp file
        tmp_path.unlink(missing_ok=True)


@router.get("/export/{program_id}/csv")
async def export_csv(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Export program schedule as CSV.

    Returns a download URL for the CSV file.
    """
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found")
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    # TODO: Implement CSV export
    return {
        "message": "CSV export not yet implemented",
        "program_id": str(program_id),
    }
