"""API endpoints for calendar import."""

from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import get_current_user, get_db
from src.core.exceptions import ValidationError
from src.models.user import User
from src.schemas.calendar_import import (
    CalendarImportPreviewResponse,
    CalendarImportResponse,
)
from src.services.calendar_import_service import CalendarImportService

router = APIRouter(prefix="/calendars", tags=["Calendar Import"])


@router.post("/import/preview", response_model=CalendarImportPreviewResponse)
async def preview_calendar_import(
    program_id: UUID,
    file: UploadFile = File(...),
    start_date: date = Query(..., description="Start of date range for calendar generation"),
    end_date: date = Query(..., description="End of date range for calendar generation"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarImportPreviewResponse:
    """
    Preview calendar import from MS Project XML.

    Shows what calendars will be imported and how they map to existing resources.
    Does not make any changes to the database.
    """
    if not file.filename or not file.filename.endswith(".xml"):
        raise ValidationError("File must be XML format", "INVALID_FILE_TYPE")

    if end_date < start_date:
        raise ValidationError("End date must be after start date", "INVALID_DATE_RANGE")

    # Save uploaded file temporarily
    with NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        service = CalendarImportService(db)
        preview = await service.preview_import(
            file_path=tmp_path,
            program_id=program_id,
            date_range_start=start_date,
            date_range_end=end_date,
        )

        return CalendarImportPreviewResponse(
            calendars=preview.calendars,
            resource_mappings=preview.resource_mappings,
            total_holidays=preview.total_holidays,
            date_range_start=preview.date_range_start,
            date_range_end=preview.date_range_end,
            warnings=preview.warnings,
        )
    finally:
        tmp_path.unlink()


@router.post("/import", response_model=CalendarImportResponse)
async def import_calendars(
    program_id: UUID,
    file: UploadFile = File(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarImportResponse:
    """
    Import calendars from MS Project XML and apply to resources.

    Creates calendar templates and generates calendar entries for all
    matching resources in the specified date range.
    """
    if not file.filename or not file.filename.endswith(".xml"):
        raise ValidationError("File must be XML format", "INVALID_FILE_TYPE")

    # Save uploaded file temporarily
    with NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        service = CalendarImportService(db)
        result = await service.import_calendars(
            file_path=tmp_path,
            program_id=program_id,
            date_range_start=start_date,
            date_range_end=end_date,
        )

        return CalendarImportResponse(
            success=True,
            resources_updated=result.resources_updated,
            calendar_entries_created=result.calendar_entries_created,
            templates_created=result.templates_created,
            warnings=result.warnings,
        )
    finally:
        tmp_path.unlink()
