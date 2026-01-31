"""Unit tests for calendar template schemas - Coverage improvement."""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.schemas.calendar_template import (
    ApplyTemplateRequest,
    ApplyTemplateResponse,
    CalendarTemplateBase,
    CalendarTemplateCreate,
    CalendarTemplateHolidayBase,
    CalendarTemplateHolidayCreate,
    CalendarTemplateHolidayResponse,
    CalendarTemplateHolidayUpdate,
    CalendarTemplateListResponse,
    CalendarTemplateResponse,
    CalendarTemplateSummary,
    CalendarTemplateUpdate,
)


class TestCalendarTemplateHolidayBase:
    """Tests for CalendarTemplateHolidayBase schema."""

    def test_valid_holiday(self):
        """Should create holiday with valid data."""
        holiday = CalendarTemplateHolidayBase(
            holiday_date=date(2026, 12, 25),
            name="Christmas Day",
            recurring_yearly=True,
        )
        assert holiday.holiday_date == date(2026, 12, 25)
        assert holiday.name == "Christmas Day"
        assert holiday.recurring_yearly is True

    def test_default_recurring(self):
        """Should default recurring_yearly to False."""
        holiday = CalendarTemplateHolidayBase(
            holiday_date=date(2026, 7, 4),
            name="Independence Day",
        )
        assert holiday.recurring_yearly is False

    def test_name_min_length(self):
        """Should reject empty name."""
        with pytest.raises(ValidationError) as exc_info:
            CalendarTemplateHolidayBase(
                holiday_date=date(2026, 1, 1),
                name="",
            )
        assert "string_too_short" in str(exc_info.value)

    def test_name_max_length(self):
        """Should reject name longer than 100 characters."""
        with pytest.raises(ValidationError) as exc_info:
            CalendarTemplateHolidayBase(
                holiday_date=date(2026, 1, 1),
                name="x" * 101,
            )
        assert "string_too_long" in str(exc_info.value)


class TestCalendarTemplateHolidayCreate:
    """Tests for CalendarTemplateHolidayCreate schema."""

    def test_create_inherits_base(self):
        """Should inherit all fields from base."""
        holiday = CalendarTemplateHolidayCreate(
            holiday_date=date(2026, 11, 28),
            name="Thanksgiving",
            recurring_yearly=True,
        )
        assert holiday.holiday_date == date(2026, 11, 28)
        assert holiday.name == "Thanksgiving"


class TestCalendarTemplateHolidayUpdate:
    """Tests for CalendarTemplateHolidayUpdate schema."""

    def test_all_fields_optional(self):
        """Should allow all fields to be None."""
        update = CalendarTemplateHolidayUpdate()
        assert update.holiday_date is None
        assert update.name is None
        assert update.recurring_yearly is None

    def test_partial_update(self):
        """Should allow partial updates."""
        update = CalendarTemplateHolidayUpdate(name="New Year's Day")
        assert update.name == "New Year's Day"
        assert update.holiday_date is None


class TestCalendarTemplateHolidayResponse:
    """Tests for CalendarTemplateHolidayResponse schema."""

    def test_response_fields(self):
        """Should include all response fields."""
        response = CalendarTemplateHolidayResponse(
            id=uuid4(),
            template_id=uuid4(),
            holiday_date=date(2026, 1, 1),
            name="New Year",
            recurring_yearly=True,
            created_at=datetime.now(),
        )
        assert response.id is not None
        assert response.template_id is not None


class TestCalendarTemplateBase:
    """Tests for CalendarTemplateBase schema."""

    def test_valid_template(self):
        """Should create template with valid data."""
        template = CalendarTemplateBase(
            name="Standard Calendar",
            description="Default working calendar",
            hours_per_day=Decimal("8.0"),
            working_days=[1, 2, 3, 4, 5],
            is_default=True,
        )
        assert template.name == "Standard Calendar"
        assert template.hours_per_day == Decimal("8.0")
        assert template.working_days == [1, 2, 3, 4, 5]
        assert template.is_default is True

    def test_default_values(self):
        """Should use default values."""
        template = CalendarTemplateBase(name="Test")
        assert template.description is None
        assert template.hours_per_day == Decimal("8.0")
        assert template.working_days == [1, 2, 3, 4, 5]
        assert template.is_default is False

    def test_working_days_validation_empty(self):
        """Should reject empty working_days."""
        with pytest.raises(ValidationError) as exc_info:
            CalendarTemplateBase(name="Test", working_days=[])
        assert "cannot be empty" in str(exc_info.value)

    def test_working_days_validation_invalid_day(self):
        """Should reject invalid day numbers."""
        with pytest.raises(ValidationError) as exc_info:
            CalendarTemplateBase(name="Test", working_days=[0, 1, 2])
        assert "Invalid day number" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            CalendarTemplateBase(name="Test", working_days=[1, 8])
        assert "Invalid day number" in str(exc_info.value)

    def test_working_days_removes_duplicates(self):
        """Should remove duplicates and sort."""
        template = CalendarTemplateBase(name="Test", working_days=[5, 1, 3, 1, 5])
        assert template.working_days == [1, 3, 5]

    def test_hours_per_day_bounds(self):
        """Should validate hours_per_day bounds."""
        # Valid boundary values
        template = CalendarTemplateBase(name="Test", hours_per_day=Decimal("0"))
        assert template.hours_per_day == Decimal("0")

        template = CalendarTemplateBase(name="Test", hours_per_day=Decimal("24"))
        assert template.hours_per_day == Decimal("24")

        # Invalid values
        with pytest.raises(ValidationError):
            CalendarTemplateBase(name="Test", hours_per_day=Decimal("-1"))

        with pytest.raises(ValidationError):
            CalendarTemplateBase(name="Test", hours_per_day=Decimal("25"))

    def test_name_validation(self):
        """Should validate name length."""
        with pytest.raises(ValidationError):
            CalendarTemplateBase(name="")

        with pytest.raises(ValidationError):
            CalendarTemplateBase(name="x" * 101)


class TestCalendarTemplateCreate:
    """Tests for CalendarTemplateCreate schema."""

    def test_create_with_holidays(self):
        """Should accept holidays list."""
        template = CalendarTemplateCreate(
            name="Test Calendar",
            holidays=[
                CalendarTemplateHolidayCreate(
                    holiday_date=date(2026, 12, 25),
                    name="Christmas",
                )
            ],
        )
        assert len(template.holidays) == 1
        assert template.holidays[0].name == "Christmas"

    def test_create_empty_holidays(self):
        """Should default to empty holidays list."""
        template = CalendarTemplateCreate(name="Test")
        assert template.holidays == []


class TestCalendarTemplateUpdate:
    """Tests for CalendarTemplateUpdate schema."""

    def test_all_optional(self):
        """Should allow all fields optional."""
        update = CalendarTemplateUpdate()
        assert update.name is None
        assert update.description is None
        assert update.hours_per_day is None
        assert update.working_days is None
        assert update.is_default is None

    def test_working_days_validation(self):
        """Should validate working_days when provided."""
        # Valid
        update = CalendarTemplateUpdate(working_days=[1, 2, 3])
        assert update.working_days == [1, 2, 3]

        # None is allowed
        update = CalendarTemplateUpdate(working_days=None)
        assert update.working_days is None

        # Empty list is invalid
        with pytest.raises(ValidationError) as exc_info:
            CalendarTemplateUpdate(working_days=[])
        assert "cannot be empty" in str(exc_info.value)

        # Invalid day numbers
        with pytest.raises(ValidationError) as exc_info:
            CalendarTemplateUpdate(working_days=[0])
        assert "Invalid day number" in str(exc_info.value)


class TestCalendarTemplateResponse:
    """Tests for CalendarTemplateResponse schema."""

    def test_response_with_holidays(self):
        """Should include holidays in response."""
        template_id = uuid4()
        program_id = uuid4()
        now = datetime.now()

        response = CalendarTemplateResponse(
            id=template_id,
            program_id=program_id,
            name="Test Template",
            hours_per_day=Decimal("8.0"),
            working_days=[1, 2, 3, 4, 5],
            is_default=False,
            holidays=[
                CalendarTemplateHolidayResponse(
                    id=uuid4(),
                    template_id=template_id,
                    holiday_date=date(2026, 1, 1),
                    name="New Year",
                    recurring_yearly=True,
                    created_at=now,
                )
            ],
            created_at=now,
            updated_at=None,
        )
        assert response.id == template_id
        assert len(response.holidays) == 1


class TestCalendarTemplateListResponse:
    """Tests for CalendarTemplateListResponse schema."""

    def test_list_response(self):
        """Should handle paginated list."""
        response = CalendarTemplateListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            has_more=False,
        )
        assert response.total == 0
        assert response.page == 1
        assert response.has_more is False


class TestCalendarTemplateSummary:
    """Tests for CalendarTemplateSummary schema."""

    def test_summary_fields(self):
        """Should include summary fields."""
        summary = CalendarTemplateSummary(
            id=uuid4(),
            name="Standard",
            hours_per_day=Decimal("8.0"),
            working_days=[1, 2, 3, 4, 5],
            is_default=True,
        )
        assert summary.name == "Standard"
        assert summary.is_default is True


class TestApplyTemplateRequest:
    """Tests for ApplyTemplateRequest schema."""

    def test_valid_request(self):
        """Should accept valid request."""
        request = ApplyTemplateRequest(
            resource_ids=[uuid4(), uuid4()],
            overwrite_existing=True,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        assert len(request.resource_ids) == 2
        assert request.overwrite_existing is True

    def test_resource_ids_required(self):
        """Should require at least one resource ID."""
        with pytest.raises(ValidationError) as exc_info:
            ApplyTemplateRequest(
                resource_ids=[],
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            )
        assert "too_short" in str(exc_info.value)

    def test_date_validation(self):
        """Should validate end_date is after start_date."""
        with pytest.raises(ValidationError) as exc_info:
            ApplyTemplateRequest(
                resource_ids=[uuid4()],
                start_date=date(2026, 12, 31),
                end_date=date(2026, 1, 1),
            )
        assert "end_date must be on or after start_date" in str(exc_info.value)

    def test_same_date_allowed(self):
        """Should allow same start and end date."""
        request = ApplyTemplateRequest(
            resource_ids=[uuid4()],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
        )
        assert request.start_date == request.end_date


class TestApplyTemplateResponse:
    """Tests for ApplyTemplateResponse schema."""

    def test_response_fields(self):
        """Should include all response fields."""
        response = ApplyTemplateResponse(
            template_id=uuid4(),
            resources_updated=5,
            calendar_entries_created=100,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        assert response.resources_updated == 5
        assert response.calendar_entries_created == 100
