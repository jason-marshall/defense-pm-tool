"""Service for importing calendars and applying to resources."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.calendar_template import CalendarTemplate, CalendarTemplateHoliday
from src.models.resource import Resource, ResourceCalendar
from src.services.calendar_import import (
    ImportedCalendar,
    MSProjectCalendarParser,
)


@dataclass
class CalendarApplyResult:
    """Result of applying calendar to resources."""

    resources_updated: int
    calendar_entries_created: int
    templates_created: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class CalendarImportPreview:
    """Preview of what will be imported."""

    calendars: list[dict[str, Any]]  # Calendar summaries
    resource_mappings: list[dict[str, Any]]  # Resource -> Calendar mappings
    total_holidays: int
    date_range_start: date
    date_range_end: date
    warnings: list[str] = field(default_factory=list)


class CalendarImportService:
    """
    Service for importing MS Project calendars.

    Workflow:
    1. Parse MS Project XML for calendar data
    2. Preview what will be imported
    3. Create calendar templates from base calendars
    4. Generate calendar entries for specified date range
    5. Apply calendars to matching resources
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def preview_import(
        self,
        file_path: Path,
        program_id: UUID,
        date_range_start: date,
        date_range_end: date,
    ) -> CalendarImportPreview:
        """
        Preview calendar import without making changes.
        """
        parser = MSProjectCalendarParser(file_path)
        result = parser.parse()

        # Get existing resources to show potential mappings
        resources = await self._get_program_resources(program_id)
        resource_names = {r.name.lower(): r for r in resources}

        calendar_summaries = []
        for cal in result.calendars:
            calendar_summaries.append(
                {
                    "uid": cal.uid,
                    "name": cal.name,
                    "is_base": cal.is_base_calendar,
                    "working_days": cal.working_days_list,
                    "hours_per_day": float(cal.default_hours_per_day),
                    "holidays": len(cal.exceptions),
                }
            )

        resource_mappings = []
        for res_cal in result.resource_calendars:
            # Try to match by name
            matched_resource = resource_names.get(res_cal.resource_name.lower())
            calendar = next((c for c in result.calendars if c.uid == res_cal.calendar_uid), None)

            resource_mappings.append(
                {
                    "ms_project_resource": res_cal.resource_name,
                    "matched_resource_id": str(matched_resource.id) if matched_resource else None,
                    "matched_resource_name": matched_resource.name if matched_resource else None,
                    "calendar_name": calendar.name if calendar else "Default",
                }
            )

        total_holidays = sum(len(c.exceptions) for c in result.calendars)

        return CalendarImportPreview(
            calendars=calendar_summaries,
            resource_mappings=resource_mappings,
            total_holidays=total_holidays,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            warnings=result.warnings,
        )

    async def import_calendars(
        self,
        file_path: Path,
        program_id: UUID,
        date_range_start: date,
        date_range_end: date,
        resource_mapping: dict[str, UUID] | None = None,
    ) -> CalendarApplyResult:
        """
        Import calendars from MS Project and apply to resources.

        Args:
            file_path: Path to MS Project XML file
            program_id: Program to import into
            date_range_start: Start of date range for calendar generation
            date_range_end: End of date range for calendar generation
            resource_mapping: Optional explicit mapping of MS Project resource names to resource IDs
        """
        warnings: list[str] = []

        # Parse file
        parser = MSProjectCalendarParser(file_path)
        result = parser.parse()
        warnings.extend(result.warnings)

        # Create templates from base calendars
        import_id = uuid4()
        template_map: dict[int, CalendarTemplate] = {}

        for cal in result.calendars:
            if cal.is_base_calendar:
                template = await self._create_template_from_calendar(program_id, cal, import_id)
                template_map[cal.uid] = template

        # Get resources
        resources = await self._get_program_resources(program_id)
        resource_names = {r.name.lower(): r for r in resources}
        resource_ids = {r.id: r for r in resources}

        # Apply calendars to resources
        entries_created = 0
        resources_updated = 0

        for res_cal in result.resource_calendars:
            # Find target resource
            target_resource = None

            if resource_mapping and res_cal.resource_name in resource_mapping:
                target_id = resource_mapping[res_cal.resource_name]
                target_resource = resource_ids.get(target_id)
            else:
                target_resource = resource_names.get(res_cal.resource_name.lower())

            if not target_resource:
                warnings.append(f"Resource '{res_cal.resource_name}' not found, skipping")
                continue

            # Find calendar (may be derived from base)
            calendar = self._resolve_calendar(res_cal.calendar_uid, result.calendars)
            if not calendar:
                warnings.append(
                    f"Calendar {res_cal.calendar_uid} not found for '{res_cal.resource_name}'"
                )
                continue

            # Assign template to resource
            if calendar.uid in template_map:
                target_resource.calendar_template_id = template_map[calendar.uid].id

            # Generate calendar entries
            entries = await self._generate_calendar_entries(
                target_resource.id,
                calendar,
                date_range_start,
                date_range_end,
                import_id,
            )
            entries_created += len(entries)
            resources_updated += 1

        await self.db.commit()

        return CalendarApplyResult(
            resources_updated=resources_updated,
            calendar_entries_created=entries_created,
            templates_created=len(template_map),
            warnings=warnings,
        )

    async def _get_program_resources(self, program_id: UUID) -> list[Resource]:
        """Get all resources for a program."""
        query = (
            select(Resource)
            .where(Resource.program_id == program_id)
            .where(Resource.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _create_template_from_calendar(
        self,
        program_id: UUID,
        calendar: ImportedCalendar,
        import_id: UUID,
    ) -> CalendarTemplate:
        """Create a CalendarTemplate from imported calendar."""
        template = CalendarTemplate(
            program_id=program_id,
            name=calendar.name,
            description=f"Imported from MS Project (import {import_id})",
            hours_per_day=calendar.default_hours_per_day,
            working_days=calendar.working_days_list,
            is_default=False,
        )
        self.db.add(template)
        await self.db.flush()  # Get ID

        # Add holidays
        for exc in calendar.exceptions:
            if not exc.is_working:  # Only non-working exceptions are holidays
                holiday = CalendarTemplateHoliday(
                    template_id=template.id,
                    holiday_date=exc.from_date,
                    name=exc.name,
                    recurring_yearly=False,
                )
                self.db.add(holiday)

        return template

    def _resolve_calendar(
        self,
        calendar_uid: int | None,
        calendars: list[ImportedCalendar],
    ) -> ImportedCalendar | None:
        """Resolve calendar, following base calendar chain if needed."""
        if calendar_uid is None:
            # Return first base calendar
            return next((c for c in calendars if c.is_base_calendar), None)

        calendar = next((c for c in calendars if c.uid == calendar_uid), None)
        if calendar is None:
            return None

        # If this calendar has a base, merge with base
        if calendar.base_calendar_uid:
            base = self._resolve_calendar(calendar.base_calendar_uid, calendars)
            if base:
                # Merge: use this calendar's overrides with base's defaults
                return calendar  # Simplified: just use derived calendar

        return calendar

    async def _generate_calendar_entries(
        self,
        resource_id: UUID,
        calendar: ImportedCalendar,
        start_date: date,
        end_date: date,
        import_id: UUID,
    ) -> list[ResourceCalendar]:
        """Generate calendar entries for a resource based on imported calendar."""
        entries: list[ResourceCalendar] = []
        current = start_date

        # Build exception lookup
        exceptions_by_date: dict[date, tuple[bool, Decimal]] = {}
        for exc in calendar.exceptions:
            exc_date = exc.from_date
            while exc_date <= exc.to_date:
                hours = (
                    sum((wt.hours for wt in exc.working_times), Decimal("0"))
                    if exc.is_working
                    else Decimal("0")
                )
                exceptions_by_date[exc_date] = (exc.is_working, hours)
                exc_date += timedelta(days=1)

        # Build weekday lookup (Python weekday -> working info)
        weekday_info: dict[int, tuple[bool, Decimal]] = {}
        for wd in calendar.week_days:
            weekday_info[wd.python_weekday] = (wd.is_working, wd.total_hours)

        while current <= end_date:
            # Check exception first
            if current in exceptions_by_date:
                is_working, hours = exceptions_by_date[current]
            elif current.weekday() in weekday_info:
                is_working, hours = weekday_info[current.weekday()]
            else:
                # Default: non-working
                is_working, hours = False, Decimal("0")

            entry = ResourceCalendar(
                resource_id=resource_id,
                calendar_date=current,
                available_hours=hours,
                is_working_day=is_working,
                source="import",
                import_id=import_id,
            )
            self.db.add(entry)
            entries.append(entry)

            current += timedelta(days=1)

        return entries
