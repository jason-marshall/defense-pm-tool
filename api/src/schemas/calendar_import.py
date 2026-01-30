"""Pydantic schemas for calendar import."""

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CalendarImportPreviewResponse(BaseModel):
    """Response schema for calendar import preview."""

    calendars: list[dict[str, Any]]
    resource_mappings: list[dict[str, Any]]
    total_holidays: int
    date_range_start: date
    date_range_end: date
    warnings: list[str]


class CalendarImportRequest(BaseModel):
    """Request schema for calendar import."""

    program_id: UUID
    start_date: date
    end_date: date
    resource_mapping: dict[str, UUID] | None = None


class CalendarImportResponse(BaseModel):
    """Response schema for calendar import."""

    success: bool
    resources_updated: int
    calendar_entries_created: int
    templates_created: int
    warnings: list[str]


class CalendarTemplateListResponse(BaseModel):
    """Response schema for listing calendar templates."""

    templates: list[dict[str, Any]]
    total: int
