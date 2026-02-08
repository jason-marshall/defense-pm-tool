"""Import/Export endpoints for schedule data."""

import csv
import io
import tempfile
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from src.repositories.activity import ActivityRepository
from src.repositories.program import ProgramRepository
from src.repositories.resource import ResourceRepository
from src.repositories.wbs import WBSElementRepository
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
    export_type: Annotated[
        str,
        Query(description="Export type: activities, resources, wbs, or all"),
    ] = "activities",
) -> StreamingResponse:
    """
    Export program data as CSV.

    Supports exporting activities, resources, WBS elements, or all combined
    into a multi-sheet ZIP-like format (separate CSV sections).

    Args:
        program_id: Program to export
        db: Database session
        current_user: Authenticated user
        export_type: What to export (activities, resources, wbs, all)

    Returns:
        CSV file as streaming download
    """
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found")
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    valid_types = {"activities", "resources", "wbs", "all"}
    if export_type not in valid_types:
        raise ValidationError(
            f"Invalid export_type '{export_type}'. Must be one of: {', '.join(sorted(valid_types))}"
        )

    output = io.StringIO()
    writer = csv.writer(output)

    if export_type in ("activities", "all"):
        await _write_activities_csv(
            writer, program_id, db, include_header_label=export_type == "all"
        )

    if export_type in ("resources", "all"):
        if export_type == "all":
            writer.writerow([])  # Blank separator
        await _write_resources_csv(
            writer, program_id, db, include_header_label=export_type == "all"
        )

    if export_type in ("wbs", "all"):
        if export_type == "all":
            writer.writerow([])  # Blank separator
        await _write_wbs_csv(writer, program_id, db, include_header_label=export_type == "all")

    output.seek(0)
    filename = f"{program.code or program.name}_export_{export_type}.csv"
    # Sanitize filename
    filename = "".join(c for c in filename if c.isalnum() or c in "._- ")

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _write_activities_csv(
    writer: Any,
    program_id: UUID,
    db: Any,
    include_header_label: bool = False,
) -> None:
    """Write activities section to CSV."""
    if include_header_label:
        writer.writerow(["## Activities"])

    writer.writerow(
        [
            "Code",
            "Name",
            "Duration (days)",
            "Percent Complete",
            "Planned Start",
            "Planned Finish",
            "Early Start",
            "Early Finish",
            "Late Start",
            "Late Finish",
            "Total Float",
            "Free Float",
            "Is Critical",
            "Is Milestone",
            "Constraint Type",
            "Constraint Date",
            "Budgeted Cost",
            "Actual Cost",
            "EV Method",
        ]
    )

    activity_repo = ActivityRepository(db)
    activities = await activity_repo.get_by_program(program_id, limit=10000)

    for act in activities:
        writer.writerow(
            [
                act.code,
                act.name,
                act.duration,
                str(act.percent_complete) if act.percent_complete is not None else "",
                act.planned_start.isoformat() if act.planned_start else "",
                act.planned_finish.isoformat() if act.planned_finish else "",
                act.early_start.isoformat() if act.early_start else "",
                act.early_finish.isoformat() if act.early_finish else "",
                act.late_start.isoformat() if act.late_start else "",
                act.late_finish.isoformat() if act.late_finish else "",
                act.total_float if act.total_float is not None else "",
                act.free_float if act.free_float is not None else "",
                act.is_critical,
                act.is_milestone,
                act.constraint_type.value if act.constraint_type else "",
                act.constraint_date.isoformat() if act.constraint_date else "",
                str(act.budgeted_cost) if act.budgeted_cost is not None else "",
                str(act.actual_cost) if act.actual_cost is not None else "",
                act.ev_method or "",
            ]
        )


async def _write_resources_csv(
    writer: Any,
    program_id: UUID,
    db: Any,
    include_header_label: bool = False,
) -> None:
    """Write resources section to CSV."""
    if include_header_label:
        writer.writerow(["## Resources"])

    writer.writerow(
        [
            "Code",
            "Name",
            "Type",
            "Capacity (hrs/day)",
            "Cost Rate",
            "Is Active",
            "Effective Date",
        ]
    )

    resource_repo = ResourceRepository(db)
    resources, _total = await resource_repo.get_by_program(program_id, limit=10000)

    for res in resources:
        writer.writerow(
            [
                res.code,
                res.name,
                res.resource_type.value if res.resource_type else "",
                str(res.capacity_per_day) if res.capacity_per_day is not None else "",
                str(res.cost_rate) if res.cost_rate is not None else "",
                res.is_active,
                res.effective_date.isoformat() if res.effective_date else "",
            ]
        )


async def _write_wbs_csv(
    writer: Any,
    program_id: UUID,
    db: Any,
    include_header_label: bool = False,
) -> None:
    """Write WBS elements section to CSV."""
    if include_header_label:
        writer.writerow(["## WBS Elements"])

    writer.writerow(
        [
            "WBS Code",
            "Name",
            "Level",
            "Path",
            "Is Control Account",
            "Budget at Completion",
            "Description",
        ]
    )

    wbs_repo = WBSElementRepository(db)
    elements = await wbs_repo.get_by_program(program_id, limit=10000)

    for elem in elements:
        writer.writerow(
            [
                elem.wbs_code,
                elem.name,
                elem.level,
                elem.path,
                elem.is_control_account,
                str(elem.budget_at_completion) if elem.budget_at_completion is not None else "",
                elem.description or "",
            ]
        )
