"""MS Project calendar import service.

Parses calendar definitions and resource-calendar assignments from
MS Project XML files for import into the system.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import ClassVar

from src.core.exceptions import ValidationError


@dataclass
class ImportedWorkingTime:
    """Working time period within a day."""

    from_time: time
    to_time: time

    @property
    def hours(self) -> Decimal:
        """Calculate hours in this working period."""
        from_minutes = self.from_time.hour * 60 + self.from_time.minute
        to_minutes = self.to_time.hour * 60 + self.to_time.minute
        return Decimal(str((to_minutes - from_minutes) / 60))


@dataclass
class ImportedWeekDay:
    """Week day definition from MS Project.

    Attributes:
        day_type: MS Project day type (1=Sunday, 2=Monday, ..., 7=Saturday)
        is_working: Whether this is a working day
        working_times: List of working time periods for this day
    """

    day_type: int  # 1=Sunday, 2=Monday, ..., 7=Saturday
    is_working: bool
    working_times: list[ImportedWorkingTime] = field(default_factory=list)

    @property
    def python_weekday(self) -> int:
        """Convert to Python weekday (0=Monday, 6=Sunday).

        MS Project: 1=Sunday, 2=Monday, ..., 7=Saturday
        Python: 0=Monday, 1=Tuesday, ..., 6=Sunday
        """
        return (self.day_type - 2) % 7

    @property
    def iso_weekday(self) -> int:
        """Convert to ISO weekday (1=Monday, 7=Sunday).

        MS Project: 1=Sunday, 2=Monday, ..., 7=Saturday
        ISO: 1=Monday, 2=Tuesday, ..., 7=Sunday
        """
        if self.day_type == 1:  # Sunday
            return 7
        return self.day_type - 1

    @property
    def total_hours(self) -> Decimal:
        """Total working hours for this day."""
        if not self.is_working:
            return Decimal("0")
        return sum((wt.hours for wt in self.working_times), Decimal("0"))


@dataclass
class ImportedException:
    """Calendar exception (holiday or special working day).

    Attributes:
        name: Name of the exception (e.g., "Christmas")
        from_date: Start date of the exception period
        to_date: End date of the exception period (inclusive)
        is_working: True for working day, False for non-working (holiday)
        working_times: Working time periods if this is a working exception
    """

    name: str
    from_date: date
    to_date: date
    is_working: bool  # True = working day, False = non-working (holiday)
    working_times: list[ImportedWorkingTime] = field(default_factory=list)

    @property
    def is_single_day(self) -> bool:
        """Check if this exception covers only one day."""
        return self.from_date == self.to_date

    @property
    def duration_days(self) -> int:
        """Number of days covered by this exception."""
        return (self.to_date - self.from_date).days + 1


@dataclass
class ImportedCalendar:
    """Parsed calendar from MS Project XML.

    Attributes:
        uid: MS Project unique identifier
        name: Calendar name
        is_base_calendar: True if this is a base/standard calendar
        base_calendar_uid: UID of parent calendar (for derived calendars)
        week_days: List of week day definitions
        exceptions: List of calendar exceptions (holidays, special days)
    """

    uid: int
    name: str
    is_base_calendar: bool
    base_calendar_uid: int | None
    week_days: list[ImportedWeekDay] = field(default_factory=list)
    exceptions: list[ImportedException] = field(default_factory=list)

    @property
    def working_days_list(self) -> list[int]:
        """Get list of working day numbers in ISO format (1=Monday, 7=Sunday)."""
        return sorted([wd.iso_weekday for wd in self.week_days if wd.is_working])

    @property
    def default_hours_per_day(self) -> Decimal:
        """Get average working hours per working day."""
        working_days = [wd for wd in self.week_days if wd.is_working]
        if not working_days:
            return Decimal("8.0")
        total = sum((wd.total_hours for wd in working_days), Decimal("0"))
        return (total / len(working_days)).quantize(Decimal("0.01"))

    @property
    def holidays(self) -> list[ImportedException]:
        """Get non-working exceptions (holidays)."""
        return [exc for exc in self.exceptions if not exc.is_working]


@dataclass
class ImportedResourceCalendar:
    """Resource with calendar assignment from MS Project.

    Attributes:
        resource_uid: MS Project resource UID
        resource_name: Resource name
        calendar_uid: UID of assigned calendar (None if using default)
    """

    resource_uid: int
    resource_name: str
    calendar_uid: int | None


@dataclass
class CalendarImportResult:
    """Result of calendar import parsing.

    Attributes:
        calendars: List of parsed calendars
        resource_calendars: List of resource-calendar assignments
        warnings: List of non-fatal warnings during parsing
    """

    calendars: list[ImportedCalendar]
    resource_calendars: list[ImportedResourceCalendar]
    warnings: list[str] = field(default_factory=list)

    @property
    def base_calendars(self) -> list[ImportedCalendar]:
        """Get only base/standard calendars."""
        return [cal for cal in self.calendars if cal.is_base_calendar]

    def get_calendar_by_uid(self, uid: int) -> ImportedCalendar | None:
        """Find calendar by its UID."""
        for cal in self.calendars:
            if cal.uid == uid:
                return cal
        return None


class MSProjectCalendarParser:
    """Parser for MS Project XML calendar data.

    Extracts calendar definitions and resource-calendar assignments
    from MS Project XML files.

    Example usage:
        parser = MSProjectCalendarParser("project.xml")
        result = parser.parse()

        for calendar in result.calendars:
            print(f"{calendar.name}: {calendar.working_days_list}")
            print(f"  Hours/day: {calendar.default_hours_per_day}")
            for holiday in calendar.holidays:
                print(f"  Holiday: {holiday.name} on {holiday.from_date}")
    """

    NAMESPACE: ClassVar[dict[str, str]] = {"msp": "http://schemas.microsoft.com/project"}

    def __init__(self, file_path: str | Path) -> None:
        """Initialize parser with file path.

        Args:
            file_path: Path to MS Project XML file
        """
        self.file_path = Path(file_path)
        self.warnings: list[str] = []

    def _find_element(self, parent: ET.Element, tag: str) -> ET.Element | None:
        """Find element with or without namespace.

        Args:
            parent: Parent element to search in
            tag: Tag name to find

        Returns:
            Found element or None
        """
        # Try with namespace
        elem = parent.find(f"msp:{tag}", self.NAMESPACE)
        if elem is not None:
            return elem
        # Try without namespace
        return parent.find(tag)

    def _find_all_elements(self, parent: ET.Element, tag: str) -> list[ET.Element]:
        """Find all elements with or without namespace.

        Args:
            parent: Parent element to search in
            tag: Tag name to find

        Returns:
            List of found elements
        """
        # Try with namespace
        elements = parent.findall(f"msp:{tag}", self.NAMESPACE)
        if elements:
            return elements
        # Try without namespace
        return parent.findall(tag)

    def _get_text(self, parent: ET.Element, tag: str, default: str = "") -> str:
        """Get text content of child element.

        Args:
            parent: Parent element
            tag: Child tag name
            default: Default value if not found

        Returns:
            Text content or default
        """
        elem = self._find_element(parent, tag)
        return elem.text if elem is not None and elem.text else default

    def _get_int(self, parent: ET.Element, tag: str, default: int = 0) -> int:
        """Get integer value of child element.

        Args:
            parent: Parent element
            tag: Child tag name
            default: Default value if not found or invalid

        Returns:
            Integer value or default
        """
        text = self._get_text(parent, tag)
        try:
            return int(text) if text else default
        except ValueError:
            return default

    def _get_bool(self, parent: ET.Element, tag: str) -> bool:
        """Get boolean value (0/1 or true/false).

        Args:
            parent: Parent element
            tag: Child tag name

        Returns:
            Boolean value (False if not found)
        """
        text = self._get_text(parent, tag, "0").lower()
        return text in ("1", "true", "yes")

    def _parse_time(self, time_str: str) -> time | None:
        """Parse time string from MS Project.

        Args:
            time_str: Time string in HH:MM:SS format

        Returns:
            time object or None if invalid
        """
        if not time_str:
            return None
        try:
            # Handle HH:MM:SS format
            parts = time_str.split(":")
            return time(
                int(parts[0]),
                int(parts[1]),
                int(parts[2]) if len(parts) > 2 else 0,
            )
        except (ValueError, IndexError):
            return None

    def _parse_datetime(self, dt_str: str) -> datetime | None:
        """Parse datetime string from MS Project.

        Args:
            dt_str: Datetime string in ISO format

        Returns:
            datetime object or None if invalid
        """
        if not dt_str:
            return None
        try:
            # Handle various ISO formats
            dt_str = dt_str.replace("Z", "+00:00")
            # Remove timezone if present for simpler parsing
            if "+" in dt_str:
                dt_str = dt_str.split("+")[0]
            elif dt_str.endswith("Z"):
                dt_str = dt_str[:-1]
            return datetime.fromisoformat(dt_str)
        except ValueError:
            return None

    def _parse_working_times(self, parent: ET.Element) -> list[ImportedWorkingTime]:
        """Parse working times from WeekDay or Exception element.

        Args:
            parent: Parent element containing WorkingTimes

        Returns:
            List of ImportedWorkingTime objects
        """
        working_times: list[ImportedWorkingTime] = []

        wt_container = self._find_element(parent, "WorkingTimes")
        if wt_container is None:
            return working_times

        for wt_elem in self._find_all_elements(wt_container, "WorkingTime"):
            from_str = self._get_text(wt_elem, "FromTime")
            to_str = self._get_text(wt_elem, "ToTime")

            from_time = self._parse_time(from_str)
            to_time = self._parse_time(to_str)

            if from_time and to_time:
                working_times.append(ImportedWorkingTime(from_time, to_time))

        return working_times

    def _parse_week_days(self, calendar_elem: ET.Element) -> list[ImportedWeekDay]:
        """Parse week day definitions from calendar.

        Args:
            calendar_elem: Calendar element

        Returns:
            List of ImportedWeekDay objects
        """
        week_days: list[ImportedWeekDay] = []

        wd_container = self._find_element(calendar_elem, "WeekDays")
        if wd_container is None:
            return week_days

        for wd_elem in self._find_all_elements(wd_container, "WeekDay"):
            day_type = self._get_int(wd_elem, "DayType")
            is_working = self._get_bool(wd_elem, "DayWorking")
            working_times = self._parse_working_times(wd_elem) if is_working else []

            if day_type > 0:
                week_days.append(ImportedWeekDay(day_type, is_working, working_times))

        return week_days

    def _parse_exceptions(self, calendar_elem: ET.Element) -> list[ImportedException]:
        """Parse calendar exceptions (holidays, special days).

        Args:
            calendar_elem: Calendar element

        Returns:
            List of ImportedException objects
        """
        exceptions: list[ImportedException] = []

        exc_container = self._find_element(calendar_elem, "Exceptions")
        if exc_container is None:
            return exceptions

        for exc_elem in self._find_all_elements(exc_container, "Exception"):
            name = self._get_text(exc_elem, "Name", "Exception")
            exc_type = self._get_int(exc_elem, "Type", 2)  # 1=Working, 2=Non-working
            is_working = exc_type == 1

            # Get date range from TimePeriod
            time_period = self._find_element(exc_elem, "TimePeriod")
            if time_period is not None:
                from_dt = self._parse_datetime(self._get_text(time_period, "FromDate"))
                to_dt = self._parse_datetime(self._get_text(time_period, "ToDate"))

                if from_dt and to_dt:
                    working_times = self._parse_working_times(exc_elem) if is_working else []
                    exceptions.append(
                        ImportedException(
                            name=name,
                            from_date=from_dt.date(),
                            to_date=to_dt.date(),
                            is_working=is_working,
                            working_times=working_times,
                        )
                    )

        return exceptions

    def _parse_calendar(self, calendar_elem: ET.Element) -> ImportedCalendar:
        """Parse a single calendar element.

        Args:
            calendar_elem: Calendar XML element

        Returns:
            ImportedCalendar object
        """
        uid = self._get_int(calendar_elem, "UID")
        name = self._get_text(calendar_elem, "Name", f"Calendar {uid}")
        is_base = self._get_bool(calendar_elem, "IsBaseCalendar")
        base_uid_text = self._get_text(calendar_elem, "BaseCalendarUID")
        base_uid = int(base_uid_text) if base_uid_text and base_uid_text != "-1" else None

        week_days = self._parse_week_days(calendar_elem)
        exceptions = self._parse_exceptions(calendar_elem)

        return ImportedCalendar(
            uid=uid,
            name=name,
            is_base_calendar=is_base,
            base_calendar_uid=base_uid,
            week_days=week_days,
            exceptions=exceptions,
        )

    def _parse_resource_calendars(self, root: ET.Element) -> list[ImportedResourceCalendar]:
        """Parse resource-calendar assignments.

        Args:
            root: Root XML element

        Returns:
            List of ImportedResourceCalendar objects
        """
        resource_calendars: list[ImportedResourceCalendar] = []

        resources_elem = self._find_element(root, "Resources")
        if resources_elem is None:
            return resource_calendars

        for res_elem in self._find_all_elements(resources_elem, "Resource"):
            uid = self._get_int(res_elem, "UID")
            name = self._get_text(res_elem, "Name", f"Resource {uid}")

            cal_uid_text = self._get_text(res_elem, "CalendarUID")
            cal_uid = int(cal_uid_text) if cal_uid_text and cal_uid_text != "-1" else None

            if uid > 0:  # Skip null resource (UID=0)
                resource_calendars.append(ImportedResourceCalendar(uid, name, cal_uid))

        return resource_calendars

    def parse(self) -> CalendarImportResult:
        """Parse MS Project XML file for calendar data.

        Returns:
            CalendarImportResult with parsed calendars and resource assignments

        Raises:
            ValidationError: If XML is invalid or cannot be parsed
        """
        if not self.file_path.exists():
            raise ValidationError(f"File not found: {self.file_path}", "FILE_NOT_FOUND")

        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
        except ET.ParseError as e:
            raise ValidationError(f"Invalid XML: {e}", "INVALID_XML") from e

        calendars = []

        calendars_elem = self._find_element(root, "Calendars")
        if calendars_elem is not None:
            for cal_elem in self._find_all_elements(calendars_elem, "Calendar"):
                try:
                    calendar = self._parse_calendar(cal_elem)
                    calendars.append(calendar)
                except Exception as e:
                    self.warnings.append(f"Failed to parse calendar: {e}")

        resource_calendars = self._parse_resource_calendars(root)

        return CalendarImportResult(
            calendars=calendars,
            resource_calendars=resource_calendars,
            warnings=self.warnings,
        )

    def parse_string(self, xml_content: str) -> CalendarImportResult:
        """Parse MS Project XML from string.

        Args:
            xml_content: XML content as string

        Returns:
            CalendarImportResult with parsed calendars and resource assignments

        Raises:
            ValidationError: If XML is invalid or cannot be parsed
        """
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise ValidationError(f"Invalid XML: {e}", "INVALID_XML") from e

        calendars = []

        calendars_elem = self._find_element(root, "Calendars")
        if calendars_elem is not None:
            for cal_elem in self._find_all_elements(calendars_elem, "Calendar"):
                try:
                    calendar = self._parse_calendar(cal_elem)
                    calendars.append(calendar)
                except Exception as e:
                    self.warnings.append(f"Failed to parse calendar: {e}")

        resource_calendars = self._parse_resource_calendars(root)

        return CalendarImportResult(
            calendars=calendars,
            resource_calendars=resource_calendars,
            warnings=self.warnings,
        )
