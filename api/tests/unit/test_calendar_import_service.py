"""Unit tests for CalendarImportService."""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.calendar_import_service import (
    CalendarApplyResult,
    CalendarImportPreview,
    CalendarImportService,
)


class TestCalendarApplyResult:
    """Tests for CalendarApplyResult dataclass."""

    def test_result_creation(self):
        """Test basic result creation."""
        result = CalendarApplyResult(
            resources_updated=5,
            calendar_entries_created=150,
            templates_created=2,
            warnings=["Warning 1"],
        )

        assert result.resources_updated == 5
        assert result.calendar_entries_created == 150
        assert result.templates_created == 2
        assert len(result.warnings) == 1

    def test_result_default_warnings(self):
        """Test default empty warnings list."""
        result = CalendarApplyResult(
            resources_updated=0,
            calendar_entries_created=0,
            templates_created=0,
        )

        assert result.warnings == []

    def test_result_zero_values(self):
        """Test result with no changes."""
        result = CalendarApplyResult(
            resources_updated=0,
            calendar_entries_created=0,
            templates_created=0,
            warnings=[],
        )

        assert result.resources_updated == 0
        assert result.calendar_entries_created == 0
        assert result.templates_created == 0


class TestCalendarImportPreview:
    """Tests for CalendarImportPreview dataclass."""

    def test_preview_creation(self):
        """Test basic preview creation."""
        preview = CalendarImportPreview(
            calendars=[
                {
                    "uid": 1,
                    "name": "Standard",
                    "is_base": True,
                    "working_days": [1, 2, 3, 4, 5],
                    "hours_per_day": 8.0,
                    "holidays": 10,
                }
            ],
            resource_mappings=[
                {
                    "ms_project_resource": "Engineer",
                    "matched_resource_id": str(uuid4()),
                    "matched_resource_name": "Engineer A",
                    "calendar_name": "Standard",
                }
            ],
            total_holidays=10,
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 12, 31),
            warnings=[],
        )

        assert len(preview.calendars) == 1
        assert preview.calendars[0]["name"] == "Standard"
        assert len(preview.resource_mappings) == 1
        assert preview.total_holidays == 10

    def test_preview_with_warnings(self):
        """Test preview with import warnings."""
        preview = CalendarImportPreview(
            calendars=[],
            resource_mappings=[],
            total_holidays=0,
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 1, 31),
            warnings=["Calendar X not found", "Resource Y skipped"],
        )

        assert len(preview.warnings) == 2

    def test_preview_unmatched_resources(self):
        """Test preview with unmatched resources."""
        preview = CalendarImportPreview(
            calendars=[],
            resource_mappings=[
                {
                    "ms_project_resource": "Unknown Engineer",
                    "matched_resource_id": None,
                    "matched_resource_name": None,
                    "calendar_name": "Standard",
                }
            ],
            total_holidays=0,
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 1, 31),
        )

        assert preview.resource_mappings[0]["matched_resource_id"] is None


class TestCalendarImportServiceInit:
    """Tests for CalendarImportService initialization."""

    def test_service_initialization(self):
        """Test service initializes with database session."""
        mock_db = MagicMock()
        service = CalendarImportService(mock_db)

        assert service.db == mock_db


class TestCalendarImportServicePreview:
    """Tests for preview_import method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return CalendarImportService(mock_db)

    @pytest.fixture
    def sample_xml_file(self, tmp_path):
        """Create sample MS Project XML file."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Calendars>
    <Calendar>
      <UID>1</UID>
      <Name>Standard</Name>
      <IsBaseCalendar>1</IsBaseCalendar>
      <WeekDays>
        <WeekDay>
          <DayType>2</DayType>
          <DayWorking>1</DayWorking>
          <WorkingTimes>
            <WorkingTime>
              <FromTime>08:00:00</FromTime>
              <ToTime>17:00:00</ToTime>
            </WorkingTime>
          </WorkingTimes>
        </WeekDay>
      </WeekDays>
      <Exceptions>
        <Exception>
          <Name>Holiday</Name>
          <Type>2</Type>
          <TimePeriod>
            <FromDate>2026-12-25T00:00:00</FromDate>
            <ToDate>2026-12-25T23:59:59</ToDate>
          </TimePeriod>
        </Exception>
      </Exceptions>
    </Calendar>
  </Calendars>
  <Resources>
    <Resource>
      <UID>1</UID>
      <Name>Engineer</Name>
      <CalendarUID>1</CalendarUID>
    </Resource>
  </Resources>
</Project>"""
        xml_file = tmp_path / "test_calendar.xml"
        xml_file.write_text(xml_content)
        return xml_file

    @pytest.mark.asyncio
    async def test_preview_import_basic(self, service, mock_db, sample_xml_file):
        """Test basic preview functionality."""
        program_id = uuid4()

        # Mock empty resources
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        preview = await service.preview_import(
            sample_xml_file,
            program_id,
            date(2026, 1, 1),
            date(2026, 12, 31),
        )

        assert len(preview.calendars) == 1
        assert preview.calendars[0]["name"] == "Standard"
        assert preview.calendars[0]["is_base"] is True
        assert preview.total_holidays == 1

    @pytest.mark.asyncio
    async def test_preview_import_with_matching_resource(self, service, mock_db, sample_xml_file):
        """Test preview matches resources by name."""
        program_id = uuid4()
        resource_id = uuid4()

        # Mock matching resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.name = "Engineer"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_resource]
        mock_db.execute.return_value = mock_result

        preview = await service.preview_import(
            sample_xml_file,
            program_id,
            date(2026, 1, 1),
            date(2026, 12, 31),
        )

        assert len(preview.resource_mappings) == 1
        assert preview.resource_mappings[0]["ms_project_resource"] == "Engineer"
        assert preview.resource_mappings[0]["matched_resource_id"] == str(resource_id)
        assert preview.resource_mappings[0]["matched_resource_name"] == "Engineer"


class TestCalendarImportServiceImport:
    """Tests for import_calendars method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return CalendarImportService(mock_db)

    @pytest.fixture
    def sample_xml_file(self, tmp_path):
        """Create sample MS Project XML file."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Calendars>
    <Calendar>
      <UID>1</UID>
      <Name>Standard</Name>
      <IsBaseCalendar>1</IsBaseCalendar>
      <WeekDays>
        <WeekDay>
          <DayType>2</DayType>
          <DayWorking>1</DayWorking>
          <WorkingTimes>
            <WorkingTime>
              <FromTime>08:00:00</FromTime>
              <ToTime>17:00:00</ToTime>
            </WorkingTime>
          </WorkingTimes>
        </WeekDay>
      </WeekDays>
    </Calendar>
  </Calendars>
  <Resources>
    <Resource>
      <UID>1</UID>
      <Name>Engineer</Name>
      <CalendarUID>1</CalendarUID>
    </Resource>
  </Resources>
</Project>"""
        xml_file = tmp_path / "import_test.xml"
        xml_file.write_text(xml_content)
        return xml_file

    @pytest.mark.asyncio
    async def test_import_calendars_no_matching_resources(self, service, mock_db, sample_xml_file):
        """Test import when no resources match."""
        program_id = uuid4()

        # Mock empty resources
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.import_calendars(
            sample_xml_file,
            program_id,
            date(2026, 1, 1),
            date(2026, 1, 7),
        )

        assert result.resources_updated == 0
        assert result.templates_created == 1  # Base calendar creates template
        assert "not found" in result.warnings[0].lower()

    @pytest.mark.asyncio
    async def test_import_calendars_with_matching_resource(self, service, mock_db, sample_xml_file):
        """Test import with matching resource."""
        program_id = uuid4()
        resource_id = uuid4()

        # Mock matching resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.name = "Engineer"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_resource]
        mock_db.execute.return_value = mock_result

        result = await service.import_calendars(
            sample_xml_file,
            program_id,
            date(2026, 1, 1),
            date(2026, 1, 7),
        )

        assert result.resources_updated == 1
        assert result.templates_created == 1
        # 7 days of calendar entries
        assert result.calendar_entries_created == 7


class TestCalendarImportServiceHelpers:
    """Tests for internal helper methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return CalendarImportService(mock_db)

    @pytest.mark.asyncio
    async def test_get_program_resources(self, service, mock_db):
        """Test fetching program resources."""
        program_id = uuid4()

        mock_resource1 = MagicMock()
        mock_resource1.id = uuid4()
        mock_resource1.name = "Resource 1"

        mock_resource2 = MagicMock()
        mock_resource2.id = uuid4()
        mock_resource2.name = "Resource 2"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_resource1, mock_resource2]
        mock_db.execute.return_value = mock_result

        resources = await service._get_program_resources(program_id)

        assert len(resources) == 2

    def test_resolve_calendar_direct(self, service):
        """Test resolving calendar directly by UID."""
        from src.services.calendar_import import ImportedCalendar

        calendars = [
            ImportedCalendar(uid=1, name="Standard", is_base_calendar=True, base_calendar_uid=None),
            ImportedCalendar(uid=2, name="Night", is_base_calendar=False, base_calendar_uid=1),
        ]

        result = service._resolve_calendar(1, calendars)
        assert result is not None
        assert result.name == "Standard"

    def test_resolve_calendar_none_returns_base(self, service):
        """Test resolving None returns first base calendar."""
        from src.services.calendar_import import ImportedCalendar

        calendars = [
            ImportedCalendar(uid=1, name="Standard", is_base_calendar=True, base_calendar_uid=None),
            ImportedCalendar(uid=2, name="Night", is_base_calendar=False, base_calendar_uid=1),
        ]

        result = service._resolve_calendar(None, calendars)
        assert result is not None
        assert result.name == "Standard"

    def test_resolve_calendar_not_found(self, service):
        """Test resolving non-existent calendar returns None."""
        from src.services.calendar_import import ImportedCalendar

        calendars = [
            ImportedCalendar(uid=1, name="Standard", is_base_calendar=True, base_calendar_uid=None),
        ]

        result = service._resolve_calendar(999, calendars)
        assert result is None

    def test_resolve_calendar_with_base(self, service):
        """Test resolving derived calendar."""
        from src.services.calendar_import import ImportedCalendar

        calendars = [
            ImportedCalendar(uid=1, name="Standard", is_base_calendar=True, base_calendar_uid=None),
            ImportedCalendar(uid=2, name="Night", is_base_calendar=False, base_calendar_uid=1),
        ]

        result = service._resolve_calendar(2, calendars)
        assert result is not None
        assert result.name == "Night"


class TestCalendarImportServiceGenerateEntries:
    """Tests for _generate_calendar_entries method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return CalendarImportService(mock_db)

    @pytest.mark.asyncio
    async def test_generate_entries_single_day(self, service, mock_db):
        """Test generating entries for single day."""
        from datetime import time
        from src.services.calendar_import import (
            ImportedCalendar,
            ImportedWeekDay,
            ImportedWorkingTime,
        )

        resource_id = uuid4()
        import_id = uuid4()

        calendar = ImportedCalendar(
            uid=1,
            name="Standard",
            is_base_calendar=True,
            base_calendar_uid=None,
            week_days=[
                ImportedWeekDay(
                    day_type=2,  # Monday
                    is_working=True,
                    working_times=[ImportedWorkingTime(time(8, 0), time(17, 0))],
                ),
            ],
        )

        entries = await service._generate_calendar_entries(
            resource_id,
            calendar,
            date(2026, 1, 5),  # Monday
            date(2026, 1, 5),
            import_id,
        )

        assert len(entries) == 1
        assert entries[0].is_working_day is True
        assert entries[0].available_hours == Decimal("9")

    @pytest.mark.asyncio
    async def test_generate_entries_week(self, service, mock_db):
        """Test generating entries for a week."""
        from datetime import time
        from src.services.calendar_import import (
            ImportedCalendar,
            ImportedWeekDay,
            ImportedWorkingTime,
        )

        resource_id = uuid4()
        import_id = uuid4()

        # Standard calendar - Mon-Fri working
        week_days = []
        for day in range(1, 8):
            is_working = 2 <= day <= 6  # Mon=2, Fri=6
            wd = ImportedWeekDay(
                day_type=day,
                is_working=is_working,
                working_times=[ImportedWorkingTime(time(8, 0), time(17, 0))] if is_working else [],
            )
            week_days.append(wd)

        calendar = ImportedCalendar(
            uid=1,
            name="Standard",
            is_base_calendar=True,
            base_calendar_uid=None,
            week_days=week_days,
        )

        # Monday to Sunday (7 days)
        entries = await service._generate_calendar_entries(
            resource_id,
            calendar,
            date(2026, 1, 5),  # Monday
            date(2026, 1, 11),  # Sunday
            import_id,
        )

        assert len(entries) == 7
        working_days = [e for e in entries if e.is_working_day]
        assert len(working_days) == 5  # Mon-Fri

    @pytest.mark.asyncio
    async def test_generate_entries_with_exception(self, service, mock_db):
        """Test generating entries with holiday exception."""
        from datetime import time
        from src.services.calendar_import import (
            ImportedCalendar,
            ImportedException,
            ImportedWeekDay,
            ImportedWorkingTime,
        )

        resource_id = uuid4()
        import_id = uuid4()

        calendar = ImportedCalendar(
            uid=1,
            name="Standard",
            is_base_calendar=True,
            base_calendar_uid=None,
            week_days=[
                ImportedWeekDay(
                    day_type=2,
                    is_working=True,
                    working_times=[ImportedWorkingTime(time(8, 0), time(17, 0))],
                ),
            ],
            exceptions=[
                ImportedException(
                    name="Holiday",
                    from_date=date(2026, 1, 5),  # Monday
                    to_date=date(2026, 1, 5),
                    is_working=False,
                ),
            ],
        )

        entries = await service._generate_calendar_entries(
            resource_id,
            calendar,
            date(2026, 1, 5),
            date(2026, 1, 5),
            import_id,
        )

        assert len(entries) == 1
        # Exception overrides working day
        assert entries[0].is_working_day is False
        assert entries[0].available_hours == Decimal("0")

    @pytest.mark.asyncio
    async def test_generate_entries_working_exception(self, service, mock_db):
        """Test generating entries with working exception (overtime)."""
        from datetime import time
        from src.services.calendar_import import (
            ImportedCalendar,
            ImportedException,
            ImportedWeekDay,
            ImportedWorkingTime,
        )

        resource_id = uuid4()
        import_id = uuid4()

        calendar = ImportedCalendar(
            uid=1,
            name="Standard",
            is_base_calendar=True,
            base_calendar_uid=None,
            week_days=[
                ImportedWeekDay(day_type=7, is_working=False),  # Saturday non-working
            ],
            exceptions=[
                ImportedException(
                    name="Saturday OT",
                    from_date=date(2026, 1, 10),  # Saturday
                    to_date=date(2026, 1, 10),
                    is_working=True,
                    working_times=[ImportedWorkingTime(time(9, 0), time(13, 0))],
                ),
            ],
        )

        entries = await service._generate_calendar_entries(
            resource_id,
            calendar,
            date(2026, 1, 10),
            date(2026, 1, 10),
            import_id,
        )

        assert len(entries) == 1
        assert entries[0].is_working_day is True
        assert entries[0].available_hours == Decimal("4")

    @pytest.mark.asyncio
    async def test_generate_entries_default_non_working(self, service, mock_db):
        """Test default to non-working when day not defined."""
        from src.services.calendar_import import ImportedCalendar

        resource_id = uuid4()
        import_id = uuid4()

        # Calendar with no week day definitions
        calendar = ImportedCalendar(
            uid=1,
            name="Empty",
            is_base_calendar=True,
            base_calendar_uid=None,
            week_days=[],
        )

        entries = await service._generate_calendar_entries(
            resource_id,
            calendar,
            date(2026, 1, 5),
            date(2026, 1, 5),
            import_id,
        )

        assert len(entries) == 1
        assert entries[0].is_working_day is False
        assert entries[0].available_hours == Decimal("0")


class TestCalendarImportServiceCreateTemplate:
    """Tests for _create_template_from_calendar method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return CalendarImportService(mock_db)

    @pytest.mark.asyncio
    async def test_create_template_basic(self, service, mock_db):
        """Test creating template from calendar."""
        from datetime import time
        from src.services.calendar_import import (
            ImportedCalendar,
            ImportedWeekDay,
            ImportedWorkingTime,
        )

        program_id = uuid4()
        import_id = uuid4()

        calendar = ImportedCalendar(
            uid=1,
            name="Standard",
            is_base_calendar=True,
            base_calendar_uid=None,
            week_days=[
                ImportedWeekDay(
                    day_type=2,
                    is_working=True,
                    working_times=[
                        ImportedWorkingTime(time(8, 0), time(12, 0)),
                        ImportedWorkingTime(time(13, 0), time(17, 0)),
                    ],
                ),
            ],
        )

        template = await service._create_template_from_calendar(
            program_id, calendar, import_id
        )

        assert template.name == "Standard"
        assert template.program_id == program_id
        assert "import" in template.description.lower()
        mock_db.add.assert_called()
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_create_template_with_holidays(self, service, mock_db):
        """Test creating template with holidays."""
        from src.services.calendar_import import (
            ImportedCalendar,
            ImportedException,
        )

        program_id = uuid4()
        import_id = uuid4()

        calendar = ImportedCalendar(
            uid=1,
            name="With Holidays",
            is_base_calendar=True,
            base_calendar_uid=None,
            exceptions=[
                ImportedException(
                    name="Christmas",
                    from_date=date(2026, 12, 25),
                    to_date=date(2026, 12, 25),
                    is_working=False,
                ),
                ImportedException(
                    name="Overtime",
                    from_date=date(2026, 1, 10),
                    to_date=date(2026, 1, 10),
                    is_working=True,  # Working exception - not a holiday
                ),
            ],
        )

        await service._create_template_from_calendar(program_id, calendar, import_id)

        # Should add template + 1 holiday (Christmas, not Overtime)
        # First call is template, subsequent calls are holidays
        add_calls = mock_db.add.call_count
        assert add_calls >= 2  # Template + at least 1 holiday
