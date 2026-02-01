"""Unit tests for calendar template model."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest


class TestCalendarTemplateIsWorkingDay:
    """Tests for CalendarTemplate.is_working_day method."""

    def test_weekday_in_working_days(self):
        """Test that weekdays in working_days return True."""
        from src.models.calendar_template import CalendarTemplate

        template = CalendarTemplate(
            id=uuid4(),
            program_id=uuid4(),
            name="Standard 5-Day",
            working_days=[1, 2, 3, 4, 5],  # Mon-Fri
            hours_per_day=Decimal("8.0"),
        )
        template.holidays = []

        # Monday (weekday 0 + 1 = 1) should be working
        assert template.is_working_day(date(2026, 1, 5)) is True  # Monday

        # Tuesday (weekday 1 + 1 = 2)
        assert template.is_working_day(date(2026, 1, 6)) is True  # Tuesday

    def test_weekend_not_in_working_days(self):
        """Test that weekend days return False."""
        from src.models.calendar_template import CalendarTemplate

        template = CalendarTemplate(
            id=uuid4(),
            program_id=uuid4(),
            name="Standard 5-Day",
            working_days=[1, 2, 3, 4, 5],  # Mon-Fri
            hours_per_day=Decimal("8.0"),
        )
        template.holidays = []

        # Saturday (weekday 5 + 1 = 6) should not be working
        assert template.is_working_day(date(2026, 1, 3)) is False  # Saturday

        # Sunday (weekday 6 + 1 = 7)
        assert template.is_working_day(date(2026, 1, 4)) is False  # Sunday

    def test_24_7_operations(self):
        """Test 7-day work week template."""
        from src.models.calendar_template import CalendarTemplate

        template = CalendarTemplate(
            id=uuid4(),
            program_id=uuid4(),
            name="24/7 Operations",
            working_days=[1, 2, 3, 4, 5, 6, 7],  # All days
            hours_per_day=Decimal("24.0"),
        )
        template.holidays = []

        # All days should be working
        assert template.is_working_day(date(2026, 1, 3)) is True  # Saturday
        assert template.is_working_day(date(2026, 1, 4)) is True  # Sunday
        assert template.is_working_day(date(2026, 1, 5)) is True  # Monday

    def test_specific_holiday(self):
        """Test that specific holiday dates return False."""
        from src.models.calendar_template import CalendarTemplate

        template = CalendarTemplate(
            id=uuid4(),
            program_id=uuid4(),
            name="Standard 5-Day",
            working_days=[1, 2, 3, 4, 5],
            hours_per_day=Decimal("8.0"),
        )

        # Create a simple holiday-like object
        class MockHoliday:
            def __init__(self, hdate, recurring):
                self.holiday_date = hdate
                self.recurring_yearly = recurring

        holiday = MockHoliday(date(2026, 1, 1), False)  # New Year's Day (Thursday)

        # Directly set the internal list to avoid SQLAlchemy collection mechanics
        object.__setattr__(template, "_holidays_list", [holiday])
        template.__dict__["holidays"] = [holiday]

        # New Year's Day should not be working even though Thursday
        assert template.is_working_day(date(2026, 1, 1)) is False

        # Day after should still be working
        assert template.is_working_day(date(2026, 1, 2)) is True

    def test_recurring_yearly_holiday(self):
        """Test that recurring holidays return False in different years."""
        from src.models.calendar_template import CalendarTemplate

        template = CalendarTemplate(
            id=uuid4(),
            program_id=uuid4(),
            name="Standard 5-Day",
            working_days=[1, 2, 3, 4, 5],
            hours_per_day=Decimal("8.0"),
        )

        # Create a simple holiday-like object
        class MockHoliday:
            def __init__(self, hdate, recurring):
                self.holiday_date = hdate
                self.recurring_yearly = recurring

        # Christmas (Dec 25) - recurring
        holiday = MockHoliday(date(2025, 12, 25), True)  # Set for 2025

        template.__dict__["holidays"] = [holiday]

        # Christmas 2026 (Friday) - should not be working
        assert template.is_working_day(date(2026, 12, 25)) is False

        # Christmas 2027 (Saturday) - not in working_days anyway
        assert template.is_working_day(date(2027, 12, 25)) is False

    def test_multiple_holidays(self):
        """Test template with multiple holidays."""
        from src.models.calendar_template import CalendarTemplate

        template = CalendarTemplate(
            id=uuid4(),
            program_id=uuid4(),
            name="Standard 5-Day",
            working_days=[1, 2, 3, 4, 5],
            hours_per_day=Decimal("8.0"),
        )

        # Create simple holiday-like objects
        class MockHoliday:
            def __init__(self, hdate, recurring):
                self.holiday_date = hdate
                self.recurring_yearly = recurring

        # New Year's (recurring)
        new_year = MockHoliday(date(2026, 1, 1), True)

        # Independence Day (recurring)
        july_4 = MockHoliday(date(2026, 7, 4), True)

        # Company event (not recurring)
        event = MockHoliday(date(2026, 3, 15), False)

        template.__dict__["holidays"] = [new_year, july_4, event]

        assert template.is_working_day(date(2026, 1, 1)) is False
        assert template.is_working_day(date(2027, 1, 1)) is False  # Recurring
        assert template.is_working_day(date(2027, 3, 15)) is True  # Not recurring


class TestCalendarTemplateGetAvailableHours:
    """Tests for CalendarTemplate.get_available_hours method."""

    def test_working_day_returns_hours(self):
        """Test that working days return hours_per_day."""
        from src.models.calendar_template import CalendarTemplate

        template = CalendarTemplate(
            id=uuid4(),
            program_id=uuid4(),
            name="Standard 5-Day",
            working_days=[1, 2, 3, 4, 5],
            hours_per_day=Decimal("8.0"),
        )
        template.holidays = []

        # Monday should return 8 hours
        hours = template.get_available_hours(date(2026, 1, 5))
        assert hours == Decimal("8.0")

    def test_non_working_day_returns_zero(self):
        """Test that non-working days return zero hours."""
        from src.models.calendar_template import CalendarTemplate

        template = CalendarTemplate(
            id=uuid4(),
            program_id=uuid4(),
            name="Standard 5-Day",
            working_days=[1, 2, 3, 4, 5],
            hours_per_day=Decimal("8.0"),
        )
        template.holidays = []

        # Saturday should return 0 hours
        hours = template.get_available_hours(date(2026, 1, 3))
        assert hours == Decimal("0")

    def test_holiday_returns_zero(self):
        """Test that holidays return zero hours."""
        from src.models.calendar_template import CalendarTemplate

        template = CalendarTemplate(
            id=uuid4(),
            program_id=uuid4(),
            name="Standard 5-Day",
            working_days=[1, 2, 3, 4, 5],
            hours_per_day=Decimal("8.0"),
        )

        class MockHoliday:
            def __init__(self, hdate, recurring):
                self.holiday_date = hdate
                self.recurring_yearly = recurring

        holiday = MockHoliday(date(2026, 1, 1), False)
        template.__dict__["holidays"] = [holiday]

        hours = template.get_available_hours(date(2026, 1, 1))
        assert hours == Decimal("0")

    def test_custom_hours_per_day(self):
        """Test with custom hours_per_day."""
        from src.models.calendar_template import CalendarTemplate

        template = CalendarTemplate(
            id=uuid4(),
            program_id=uuid4(),
            name="Part Time",
            working_days=[1, 2, 3, 4, 5],
            hours_per_day=Decimal("4.5"),
        )
        template.holidays = []

        hours = template.get_available_hours(date(2026, 1, 5))
        assert hours == Decimal("4.5")

    def test_24_hour_operations(self):
        """Test 24-hour operations template."""
        from src.models.calendar_template import CalendarTemplate

        template = CalendarTemplate(
            id=uuid4(),
            program_id=uuid4(),
            name="24/7 Operations",
            working_days=[1, 2, 3, 4, 5, 6, 7],
            hours_per_day=Decimal("24.0"),
        )
        template.holidays = []

        # All days should return 24 hours
        for i in range(7):
            hours = template.get_available_hours(date(2026, 1, 5 + i))
            assert hours == Decimal("24.0")


class TestCalendarTemplateHoliday:
    """Tests for CalendarTemplateHoliday model."""

    def test_holiday_attributes(self):
        """Test holiday has correct attributes."""
        from src.models.calendar_template import CalendarTemplateHoliday

        template_id = uuid4()
        holiday = CalendarTemplateHoliday(
            id=uuid4(),
            template_id=template_id,
            holiday_date=date(2026, 12, 25),
            name="Christmas Day",
            recurring_yearly=True,
        )

        assert holiday.template_id == template_id
        assert holiday.holiday_date == date(2026, 12, 25)
        assert holiday.name == "Christmas Day"
        assert holiday.recurring_yearly is True

    def test_non_recurring_holiday(self):
        """Test non-recurring holiday."""
        from src.models.calendar_template import CalendarTemplateHoliday

        holiday = CalendarTemplateHoliday(
            id=uuid4(),
            template_id=uuid4(),
            holiday_date=date(2026, 5, 20),
            name="Company Foundation Day",
            recurring_yearly=False,
        )

        assert holiday.recurring_yearly is False
