"""Unit tests for MS Project calendar import."""

from datetime import date, time
from decimal import Decimal
from pathlib import Path

import pytest

from src.services.calendar_import import (
    CalendarImportResult,
    ImportedCalendar,
    ImportedException,
    ImportedWeekDay,
    ImportedWorkingTime,
    MSProjectCalendarParser,
)


class TestImportedWorkingTime:
    """Tests for ImportedWorkingTime dataclass."""

    def test_hours_calculation_full_day(self):
        """Test hours calculation for full work period."""
        wt = ImportedWorkingTime(time(8, 0), time(17, 0))
        assert wt.hours == Decimal("9")

    def test_hours_calculation_half_day(self):
        """Test hours calculation for half day."""
        wt = ImportedWorkingTime(time(8, 0), time(12, 0))
        assert wt.hours == Decimal("4")

    def test_hours_calculation_with_minutes(self):
        """Test hours calculation with non-hour boundaries."""
        wt = ImportedWorkingTime(time(8, 30), time(12, 0))
        assert wt.hours == Decimal("3.5")


class TestImportedWeekDay:
    """Tests for ImportedWeekDay dataclass."""

    def test_python_weekday_conversion_monday(self):
        """Test MS Project Monday (2) to Python Monday (0)."""
        wd = ImportedWeekDay(day_type=2, is_working=True)
        assert wd.python_weekday == 0

    def test_python_weekday_conversion_sunday(self):
        """Test MS Project Sunday (1) to Python Sunday (6)."""
        wd = ImportedWeekDay(day_type=1, is_working=False)
        assert wd.python_weekday == 6

    def test_python_weekday_conversion_saturday(self):
        """Test MS Project Saturday (7) to Python Saturday (5)."""
        wd = ImportedWeekDay(day_type=7, is_working=False)
        assert wd.python_weekday == 5

    def test_iso_weekday_conversion_monday(self):
        """Test MS Project Monday (2) to ISO Monday (1)."""
        wd = ImportedWeekDay(day_type=2, is_working=True)
        assert wd.iso_weekday == 1

    def test_iso_weekday_conversion_sunday(self):
        """Test MS Project Sunday (1) to ISO Sunday (7)."""
        wd = ImportedWeekDay(day_type=1, is_working=False)
        assert wd.iso_weekday == 7

    def test_total_hours_working_day(self):
        """Test total hours for working day with multiple periods."""
        wd = ImportedWeekDay(
            day_type=2,
            is_working=True,
            working_times=[
                ImportedWorkingTime(time(8, 0), time(12, 0)),  # 4h
                ImportedWorkingTime(time(13, 0), time(17, 0)),  # 4h
            ],
        )
        assert wd.total_hours == Decimal("8")

    def test_total_hours_non_working_day(self):
        """Test total hours for non-working day is zero."""
        wd = ImportedWeekDay(day_type=1, is_working=False)
        assert wd.total_hours == Decimal("0")


class TestImportedException:
    """Tests for ImportedException dataclass."""

    def test_is_single_day_true(self):
        """Test single day exception detection."""
        exc = ImportedException(
            name="Holiday",
            from_date=date(2026, 12, 25),
            to_date=date(2026, 12, 25),
            is_working=False,
        )
        assert exc.is_single_day is True

    def test_is_single_day_false(self):
        """Test multi-day exception detection."""
        exc = ImportedException(
            name="Shutdown",
            from_date=date(2026, 12, 24),
            to_date=date(2026, 12, 26),
            is_working=False,
        )
        assert exc.is_single_day is False

    def test_duration_days(self):
        """Test duration calculation."""
        exc = ImportedException(
            name="Shutdown",
            from_date=date(2026, 12, 24),
            to_date=date(2026, 12, 26),
            is_working=False,
        )
        assert exc.duration_days == 3


class TestImportedCalendar:
    """Tests for ImportedCalendar dataclass."""

    def test_working_days_list(self):
        """Test working days list extraction in ISO format."""
        cal = ImportedCalendar(
            uid=1,
            name="Standard",
            is_base_calendar=True,
            base_calendar_uid=None,
            week_days=[
                ImportedWeekDay(day_type=1, is_working=False),  # Sunday
                ImportedWeekDay(day_type=2, is_working=True),  # Monday
                ImportedWeekDay(day_type=3, is_working=True),  # Tuesday
                ImportedWeekDay(day_type=4, is_working=True),  # Wednesday
                ImportedWeekDay(day_type=5, is_working=True),  # Thursday
                ImportedWeekDay(day_type=6, is_working=True),  # Friday
                ImportedWeekDay(day_type=7, is_working=False),  # Saturday
            ],
        )
        # ISO format: 1=Monday, 5=Friday
        assert cal.working_days_list == [1, 2, 3, 4, 5]

    def test_default_hours_per_day(self):
        """Test average hours calculation."""
        cal = ImportedCalendar(
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
                ImportedWeekDay(
                    day_type=3,
                    is_working=True,
                    working_times=[
                        ImportedWorkingTime(time(8, 0), time(12, 0)),
                        ImportedWorkingTime(time(13, 0), time(17, 0)),
                    ],
                ),
            ],
        )
        assert cal.default_hours_per_day == Decimal("8.00")

    def test_default_hours_no_working_days(self):
        """Test default hours when no working days defined."""
        cal = ImportedCalendar(
            uid=1,
            name="Empty",
            is_base_calendar=True,
            base_calendar_uid=None,
            week_days=[],
        )
        assert cal.default_hours_per_day == Decimal("8.0")

    def test_holidays_filter(self):
        """Test filtering non-working exceptions."""
        cal = ImportedCalendar(
            uid=1,
            name="Standard",
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
                    name="Makeup Day",
                    from_date=date(2026, 12, 28),
                    to_date=date(2026, 12, 28),
                    is_working=True,
                ),
            ],
        )
        holidays = cal.holidays
        assert len(holidays) == 1
        assert holidays[0].name == "Christmas"


class TestCalendarImportResult:
    """Tests for CalendarImportResult dataclass."""

    def test_base_calendars_filter(self):
        """Test filtering base calendars."""
        result = CalendarImportResult(
            calendars=[
                ImportedCalendar(
                    uid=1,
                    name="Standard",
                    is_base_calendar=True,
                    base_calendar_uid=None,
                ),
                ImportedCalendar(
                    uid=2,
                    name="Night Shift",
                    is_base_calendar=False,
                    base_calendar_uid=1,
                ),
            ],
            resource_calendars=[],
        )
        base = result.base_calendars
        assert len(base) == 1
        assert base[0].name == "Standard"

    def test_get_calendar_by_uid(self):
        """Test finding calendar by UID."""
        result = CalendarImportResult(
            calendars=[
                ImportedCalendar(
                    uid=1,
                    name="Standard",
                    is_base_calendar=True,
                    base_calendar_uid=None,
                ),
                ImportedCalendar(
                    uid=2,
                    name="Night Shift",
                    is_base_calendar=False,
                    base_calendar_uid=1,
                ),
            ],
            resource_calendars=[],
        )
        cal = result.get_calendar_by_uid(2)
        assert cal is not None
        assert cal.name == "Night Shift"

    def test_get_calendar_by_uid_not_found(self):
        """Test finding non-existent calendar."""
        result = CalendarImportResult(calendars=[], resource_calendars=[])
        assert result.get_calendar_by_uid(999) is None


class TestMSProjectCalendarParser:
    """Tests for MSProjectCalendarParser."""

    @pytest.fixture
    def sample_calendar_xml(self, tmp_path: Path) -> Path:
        """Create sample MS Project XML with calendars."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Calendars>
    <Calendar>
      <UID>1</UID>
      <Name>Standard</Name>
      <IsBaseCalendar>1</IsBaseCalendar>
      <WeekDays>
        <WeekDay>
          <DayType>1</DayType>
          <DayWorking>0</DayWorking>
        </WeekDay>
        <WeekDay>
          <DayType>2</DayType>
          <DayWorking>1</DayWorking>
          <WorkingTimes>
            <WorkingTime>
              <FromTime>08:00:00</FromTime>
              <ToTime>12:00:00</ToTime>
            </WorkingTime>
            <WorkingTime>
              <FromTime>13:00:00</FromTime>
              <ToTime>17:00:00</ToTime>
            </WorkingTime>
          </WorkingTimes>
        </WeekDay>
        <WeekDay>
          <DayType>7</DayType>
          <DayWorking>0</DayWorking>
        </WeekDay>
      </WeekDays>
      <Exceptions>
        <Exception>
          <Name>Christmas</Name>
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
      <UID>0</UID>
      <Name></Name>
    </Resource>
    <Resource>
      <UID>1</UID>
      <Name>Engineer</Name>
      <CalendarUID>1</CalendarUID>
    </Resource>
    <Resource>
      <UID>2</UID>
      <Name>Technician</Name>
      <CalendarUID>-1</CalendarUID>
    </Resource>
  </Resources>
</Project>"""

        xml_file = tmp_path / "calendar_test.xml"
        xml_file.write_text(xml_content)
        return xml_file

    @pytest.fixture
    def sample_no_namespace_xml(self, tmp_path: Path) -> Path:
        """Create sample XML without namespace."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Calendars>
    <Calendar>
      <UID>1</UID>
      <Name>Standard</Name>
      <IsBaseCalendar>true</IsBaseCalendar>
      <WeekDays>
        <WeekDay>
          <DayType>2</DayType>
          <DayWorking>1</DayWorking>
          <WorkingTimes>
            <WorkingTime>
              <FromTime>09:00:00</FromTime>
              <ToTime>18:00:00</ToTime>
            </WorkingTime>
          </WorkingTimes>
        </WeekDay>
      </WeekDays>
    </Calendar>
  </Calendars>
</Project>"""

        xml_file = tmp_path / "no_namespace.xml"
        xml_file.write_text(xml_content)
        return xml_file

    def test_parse_calendar_basic(self, sample_calendar_xml: Path):
        """Test basic calendar parsing."""
        parser = MSProjectCalendarParser(sample_calendar_xml)
        result = parser.parse()

        assert len(result.calendars) == 1
        cal = result.calendars[0]
        assert cal.name == "Standard"
        assert cal.is_base_calendar is True
        assert cal.uid == 1

    def test_parse_week_days(self, sample_calendar_xml: Path):
        """Test week day parsing."""
        parser = MSProjectCalendarParser(sample_calendar_xml)
        result = parser.parse()

        cal = result.calendars[0]
        assert len(cal.week_days) == 3

        # Sunday (non-working)
        sunday = next(wd for wd in cal.week_days if wd.day_type == 1)
        assert sunday.is_working is False

        # Monday (working)
        monday = next(wd for wd in cal.week_days if wd.day_type == 2)
        assert monday.is_working is True
        assert len(monday.working_times) == 2

        # Saturday (non-working)
        saturday = next(wd for wd in cal.week_days if wd.day_type == 7)
        assert saturday.is_working is False

    def test_parse_working_hours(self, sample_calendar_xml: Path):
        """Test working hours calculation."""
        parser = MSProjectCalendarParser(sample_calendar_xml)
        result = parser.parse()

        cal = result.calendars[0]
        monday = next(wd for wd in cal.week_days if wd.day_type == 2)

        # 8:00-12:00 (4h) + 13:00-17:00 (4h) = 8h
        assert monday.total_hours == Decimal("8")

    def test_parse_exceptions(self, sample_calendar_xml: Path):
        """Test calendar exception parsing."""
        parser = MSProjectCalendarParser(sample_calendar_xml)
        result = parser.parse()

        cal = result.calendars[0]
        assert len(cal.exceptions) == 1

        christmas = cal.exceptions[0]
        assert christmas.name == "Christmas"
        assert christmas.is_working is False
        assert christmas.from_date == date(2026, 12, 25)

    def test_parse_resource_calendars(self, sample_calendar_xml: Path):
        """Test resource-calendar assignment parsing."""
        parser = MSProjectCalendarParser(sample_calendar_xml)
        result = parser.parse()

        # Should skip UID=0 (null resource)
        assert len(result.resource_calendars) == 2

        engineer = next(rc for rc in result.resource_calendars if rc.resource_name == "Engineer")
        assert engineer.calendar_uid == 1

        technician = next(
            rc for rc in result.resource_calendars if rc.resource_name == "Technician"
        )
        assert technician.calendar_uid is None  # -1 means no calendar

    def test_parse_without_namespace(self, sample_no_namespace_xml: Path):
        """Test parsing XML without namespace."""
        parser = MSProjectCalendarParser(sample_no_namespace_xml)
        result = parser.parse()

        assert len(result.calendars) == 1
        cal = result.calendars[0]
        assert cal.name == "Standard"
        assert cal.is_base_calendar is True

    def test_parse_string(self, sample_calendar_xml: Path):
        """Test parsing from string content."""
        xml_content = sample_calendar_xml.read_text()

        parser = MSProjectCalendarParser(sample_calendar_xml)
        result = parser.parse_string(xml_content)

        assert len(result.calendars) == 1
        assert result.calendars[0].name == "Standard"

    def test_parse_invalid_xml(self, tmp_path: Path):
        """Test handling invalid XML."""
        invalid_file = tmp_path / "invalid.xml"
        invalid_file.write_text("not valid xml <<<<")

        parser = MSProjectCalendarParser(invalid_file)
        with pytest.raises(Exception) as exc_info:
            parser.parse()
        assert "Invalid XML" in str(exc_info.value)

    def test_parse_file_not_found(self, tmp_path: Path):
        """Test handling missing file."""
        parser = MSProjectCalendarParser(tmp_path / "nonexistent.xml")
        with pytest.raises(Exception) as exc_info:
            parser.parse()
        assert "not found" in str(exc_info.value).lower()

    def test_parse_empty_calendars(self, tmp_path: Path):
        """Test parsing XML with no calendars."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Name>Empty Project</Name>
</Project>"""

        xml_file = tmp_path / "empty.xml"
        xml_file.write_text(xml_content)

        parser = MSProjectCalendarParser(xml_file)
        result = parser.parse()

        assert len(result.calendars) == 0
        assert len(result.resource_calendars) == 0


class TestMSProjectCalendarParserEdgeCases:
    """Edge case tests for calendar parser."""

    def test_parse_working_exception(self, tmp_path: Path):
        """Test parsing working day exception (overtime)."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Calendars>
    <Calendar>
      <UID>1</UID>
      <Name>Standard</Name>
      <IsBaseCalendar>1</IsBaseCalendar>
      <Exceptions>
        <Exception>
          <Name>Saturday Overtime</Name>
          <Type>1</Type>
          <TimePeriod>
            <FromDate>2026-01-10T00:00:00</FromDate>
            <ToDate>2026-01-10T23:59:59</ToDate>
          </TimePeriod>
          <WorkingTimes>
            <WorkingTime>
              <FromTime>09:00:00</FromTime>
              <ToTime>13:00:00</ToTime>
            </WorkingTime>
          </WorkingTimes>
        </Exception>
      </Exceptions>
    </Calendar>
  </Calendars>
</Project>"""

        xml_file = tmp_path / "working_exception.xml"
        xml_file.write_text(xml_content)

        parser = MSProjectCalendarParser(xml_file)
        result = parser.parse()

        cal = result.calendars[0]
        assert len(cal.exceptions) == 1

        overtime = cal.exceptions[0]
        assert overtime.name == "Saturday Overtime"
        assert overtime.is_working is True
        assert len(overtime.working_times) == 1
        assert overtime.working_times[0].hours == Decimal("4")

    def test_parse_derived_calendar(self, tmp_path: Path):
        """Test parsing calendar derived from base."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Calendars>
    <Calendar>
      <UID>1</UID>
      <Name>Standard</Name>
      <IsBaseCalendar>1</IsBaseCalendar>
    </Calendar>
    <Calendar>
      <UID>2</UID>
      <Name>Night Shift</Name>
      <IsBaseCalendar>0</IsBaseCalendar>
      <BaseCalendarUID>1</BaseCalendarUID>
    </Calendar>
  </Calendars>
</Project>"""

        xml_file = tmp_path / "derived.xml"
        xml_file.write_text(xml_content)

        parser = MSProjectCalendarParser(xml_file)
        result = parser.parse()

        assert len(result.calendars) == 2

        night_shift = result.get_calendar_by_uid(2)
        assert night_shift is not None
        assert night_shift.is_base_calendar is False
        assert night_shift.base_calendar_uid == 1

    def test_parse_multi_day_exception(self, tmp_path: Path):
        """Test parsing multi-day exception (shutdown period)."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Calendars>
    <Calendar>
      <UID>1</UID>
      <Name>Standard</Name>
      <IsBaseCalendar>1</IsBaseCalendar>
      <Exceptions>
        <Exception>
          <Name>Holiday Shutdown</Name>
          <Type>2</Type>
          <TimePeriod>
            <FromDate>2026-12-24T00:00:00</FromDate>
            <ToDate>2027-01-02T23:59:59</ToDate>
          </TimePeriod>
        </Exception>
      </Exceptions>
    </Calendar>
  </Calendars>
</Project>"""

        xml_file = tmp_path / "shutdown.xml"
        xml_file.write_text(xml_content)

        parser = MSProjectCalendarParser(xml_file)
        result = parser.parse()

        cal = result.calendars[0]
        shutdown = cal.exceptions[0]

        assert shutdown.from_date == date(2026, 12, 24)
        assert shutdown.to_date == date(2027, 1, 2)
        assert shutdown.is_single_day is False
        assert shutdown.duration_days == 10
