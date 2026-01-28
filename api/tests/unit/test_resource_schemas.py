"""Unit tests for Resource, ResourceAssignment, and ResourceCalendar schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models.enums import ResourceType
from src.schemas.resource import (
    ResourceAssignmentBase,
    ResourceAssignmentCreate,
    ResourceAssignmentUpdate,
    ResourceBase,
    ResourceCalendarBase,
    ResourceCalendarBulkCreate,
    ResourceCalendarEntry,
    ResourceCreate,
    ResourceUpdate,
)

# =============================================================================
# Resource Schema Tests
# =============================================================================


class TestResourceBase:
    """Tests for ResourceBase schema."""

    def test_valid_resource(self) -> None:
        """Test creating a valid resource."""
        resource = ResourceBase(
            name="Senior Engineer",
            code="ENG-001",
            resource_type=ResourceType.LABOR,
            capacity_per_day=Decimal("8.0"),
            cost_rate=Decimal("150.00"),
        )
        assert resource.name == "Senior Engineer"
        assert resource.code == "ENG-001"
        assert resource.resource_type == ResourceType.LABOR
        assert resource.capacity_per_day == Decimal("8.0")
        assert resource.cost_rate == Decimal("150.00")

    def test_code_auto_uppercase(self) -> None:
        """Test that code is automatically uppercased."""
        resource = ResourceBase(name="Test Resource", code="eng-001")
        assert resource.code == "ENG-001"

    def test_code_with_numbers_and_underscores(self) -> None:
        """Test code with numbers and underscores."""
        resource = ResourceBase(name="Test", code="res_123_a")
        assert resource.code == "RES_123_A"

    def test_invalid_code_characters(self) -> None:
        """Test that invalid code characters are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceBase(name="Test", code="eng 001")  # space not allowed
        assert "string_pattern_mismatch" in str(exc_info.value)

    def test_invalid_code_special_chars(self) -> None:
        """Test that special characters in code are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceBase(name="Test", code="eng@001")
        assert "string_pattern_mismatch" in str(exc_info.value)

    def test_capacity_range_valid(self) -> None:
        """Test valid capacity values within range."""
        resource = ResourceBase(name="Test", code="T1", capacity_per_day=Decimal("0"))
        assert resource.capacity_per_day == Decimal("0")

        resource = ResourceBase(name="Test", code="T1", capacity_per_day=Decimal("24"))
        assert resource.capacity_per_day == Decimal("24")

    def test_capacity_below_minimum(self) -> None:
        """Test that capacity below 0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceBase(name="Test", code="T1", capacity_per_day=Decimal("-1"))
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_capacity_above_maximum(self) -> None:
        """Test that capacity above 24 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceBase(name="Test", code="T1", capacity_per_day=Decimal("25"))
        assert "less than or equal to 24" in str(exc_info.value)

    def test_cost_rate_negative_rejected(self) -> None:
        """Test that negative cost rate is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceBase(name="Test", code="T1", cost_rate=Decimal("-10"))
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_name_too_long(self) -> None:
        """Test that name exceeding 100 chars is rejected."""
        with pytest.raises(ValidationError):
            ResourceBase(name="x" * 101, code="T1")

    def test_code_too_long(self) -> None:
        """Test that code exceeding 50 chars is rejected."""
        with pytest.raises(ValidationError):
            ResourceBase(name="Test", code="X" * 51)

    def test_default_values(self) -> None:
        """Test that defaults are properly set."""
        resource = ResourceBase(name="Test", code="T1")
        assert resource.resource_type == ResourceType.LABOR
        assert resource.capacity_per_day == Decimal("8.0")
        assert resource.cost_rate is None
        assert resource.effective_date is None
        assert resource.is_active is True


class TestResourceCreate:
    """Tests for ResourceCreate schema."""

    def test_create_with_program_id(self) -> None:
        """Test creating resource with program ID."""
        program_id = uuid4()
        resource = ResourceCreate(
            name="Engineer",
            code="ENG-001",
            program_id=program_id,
        )
        assert resource.program_id == program_id


class TestResourceUpdate:
    """Tests for ResourceUpdate schema."""

    def test_partial_update(self) -> None:
        """Test partial update with only some fields."""
        update = ResourceUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.code is None
        assert update.resource_type is None

    def test_update_code_uppercase(self) -> None:
        """Test that code is uppercased in update."""
        update = ResourceUpdate(code="new-code")
        assert update.code == "NEW-CODE"

    def test_update_invalid_code(self) -> None:
        """Test that invalid code in update is rejected."""
        with pytest.raises(ValidationError):
            ResourceUpdate(code="invalid code")


# =============================================================================
# Resource Assignment Schema Tests
# =============================================================================


class TestResourceAssignmentBase:
    """Tests for ResourceAssignmentBase schema."""

    def test_valid_assignment(self) -> None:
        """Test creating a valid assignment."""
        assignment = ResourceAssignmentBase(
            units=Decimal("1.0"),
            start_date=date(2024, 1, 1),
            finish_date=date(2024, 1, 31),
        )
        assert assignment.units == Decimal("1.0")
        assert assignment.start_date == date(2024, 1, 1)
        assert assignment.finish_date == date(2024, 1, 31)

    def test_units_range_valid(self) -> None:
        """Test valid units values within range."""
        assignment = ResourceAssignmentBase(units=Decimal("0"))
        assert assignment.units == Decimal("0")

        assignment = ResourceAssignmentBase(units=Decimal("10"))
        assert assignment.units == Decimal("10")

    def test_units_below_minimum(self) -> None:
        """Test that units below 0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceAssignmentBase(units=Decimal("-0.1"))
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_units_above_maximum(self) -> None:
        """Test that units above 10 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceAssignmentBase(units=Decimal("10.1"))
        assert "less than or equal to 10" in str(exc_info.value)

    def test_date_validation_valid(self) -> None:
        """Test that valid date range is accepted."""
        assignment = ResourceAssignmentBase(
            start_date=date(2024, 1, 1),
            finish_date=date(2024, 1, 1),  # same day is valid
        )
        assert assignment.start_date == assignment.finish_date

    def test_date_validation_invalid(self) -> None:
        """Test that finish_date < start_date is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceAssignmentBase(
                start_date=date(2024, 1, 31),
                finish_date=date(2024, 1, 1),
            )
        assert "finish_date must be greater than or equal to start_date" in str(exc_info.value)

    def test_dates_optional(self) -> None:
        """Test that dates can be omitted."""
        assignment = ResourceAssignmentBase()
        assert assignment.start_date is None
        assert assignment.finish_date is None


class TestResourceAssignmentCreate:
    """Tests for ResourceAssignmentCreate schema."""

    def test_create_assignment(self) -> None:
        """Test creating an assignment with IDs."""
        activity_id = uuid4()
        resource_id = uuid4()
        assignment = ResourceAssignmentCreate(
            activity_id=activity_id,
            resource_id=resource_id,
            units=Decimal("0.5"),
        )
        assert assignment.activity_id == activity_id
        assert assignment.resource_id == resource_id
        assert assignment.units == Decimal("0.5")


class TestResourceAssignmentUpdate:
    """Tests for ResourceAssignmentUpdate schema."""

    def test_partial_update(self) -> None:
        """Test partial update of assignment."""
        update = ResourceAssignmentUpdate(units=Decimal("2.0"))
        assert update.units == Decimal("2.0")
        assert update.start_date is None

    def test_update_date_validation(self) -> None:
        """Test date validation in update."""
        with pytest.raises(ValidationError):
            ResourceAssignmentUpdate(
                start_date=date(2024, 12, 31),
                finish_date=date(2024, 1, 1),
            )


# =============================================================================
# Resource Calendar Schema Tests
# =============================================================================


class TestResourceCalendarBase:
    """Tests for ResourceCalendarBase schema."""

    def test_valid_calendar_entry(self) -> None:
        """Test creating a valid calendar entry."""
        entry = ResourceCalendarBase(
            calendar_date=date(2024, 1, 15),
            available_hours=Decimal("8.0"),
            is_working_day=True,
        )
        assert entry.calendar_date == date(2024, 1, 15)
        assert entry.available_hours == Decimal("8.0")
        assert entry.is_working_day is True

    def test_hours_range_valid(self) -> None:
        """Test valid hours values within range."""
        entry = ResourceCalendarBase(calendar_date=date(2024, 1, 1), available_hours=Decimal("0"))
        assert entry.available_hours == Decimal("0")

        entry = ResourceCalendarBase(calendar_date=date(2024, 1, 1), available_hours=Decimal("24"))
        assert entry.available_hours == Decimal("24")

    def test_hours_below_minimum(self) -> None:
        """Test that hours below 0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceCalendarBase(calendar_date=date(2024, 1, 1), available_hours=Decimal("-1"))
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_hours_above_maximum(self) -> None:
        """Test that hours above 24 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceCalendarBase(calendar_date=date(2024, 1, 1), available_hours=Decimal("25"))
        assert "less than or equal to 24" in str(exc_info.value)

    def test_non_working_day(self) -> None:
        """Test non-working day entry."""
        entry = ResourceCalendarBase(
            calendar_date=date(2024, 1, 1),
            available_hours=Decimal("0"),
            is_working_day=False,
        )
        assert entry.is_working_day is False


class TestResourceCalendarBulkCreate:
    """Tests for ResourceCalendarBulkCreate schema."""

    def test_valid_bulk_create(self) -> None:
        """Test creating multiple calendar entries."""
        resource_id = uuid4()
        bulk = ResourceCalendarBulkCreate(
            resource_id=resource_id,
            entries=[
                ResourceCalendarEntry(calendar_date=date(2024, 1, 1)),
                ResourceCalendarEntry(calendar_date=date(2024, 1, 2)),
                ResourceCalendarEntry(calendar_date=date(2024, 1, 3)),
            ],
        )
        assert bulk.resource_id == resource_id
        assert len(bulk.entries) == 3

    def test_bulk_create_max_limit(self) -> None:
        """Test that bulk create is limited to 366 entries."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceCalendarBulkCreate(
                resource_id=uuid4(),
                entries=[
                    ResourceCalendarEntry(
                        calendar_date=date(2024, 1, 1) + __import__("datetime").timedelta(days=i)
                    )
                    for i in range(367)
                ],
            )
        assert "at most 366" in str(exc_info.value).lower()

    def test_bulk_create_empty_rejected(self) -> None:
        """Test that empty entries list is rejected."""
        with pytest.raises(ValidationError):
            ResourceCalendarBulkCreate(resource_id=uuid4(), entries=[])

    def test_duplicate_dates_rejected(self) -> None:
        """Test that duplicate dates in bulk create are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceCalendarBulkCreate(
                resource_id=uuid4(),
                entries=[
                    ResourceCalendarEntry(calendar_date=date(2024, 1, 1)),
                    ResourceCalendarEntry(calendar_date=date(2024, 1, 1)),  # duplicate
                ],
            )
        assert "Duplicate dates" in str(exc_info.value)


# =============================================================================
# Resource Type Enum Tests
# =============================================================================


class TestResourceType:
    """Tests for ResourceType enum."""

    def test_labor_type(self) -> None:
        """Test LABOR resource type."""
        assert ResourceType.LABOR.value == "labor"
        assert ResourceType.LABOR.is_time_based is True
        assert ResourceType.LABOR.supports_leveling is True

    def test_equipment_type(self) -> None:
        """Test EQUIPMENT resource type."""
        assert ResourceType.EQUIPMENT.value == "equipment"
        assert ResourceType.EQUIPMENT.is_time_based is True
        assert ResourceType.EQUIPMENT.supports_leveling is True

    def test_material_type(self) -> None:
        """Test MATERIAL resource type."""
        assert ResourceType.MATERIAL.value == "material"
        assert ResourceType.MATERIAL.is_time_based is False
        assert ResourceType.MATERIAL.supports_leveling is False

    def test_display_name(self) -> None:
        """Test display name formatting."""
        assert ResourceType.LABOR.display_name == "Labor"
        assert ResourceType.EQUIPMENT.display_name == "Equipment"
        assert ResourceType.MATERIAL.display_name == "Material"
