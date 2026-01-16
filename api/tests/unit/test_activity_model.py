"""Unit tests for Activity model."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from src.models.activity import Activity
from src.models.enums import ActivityStatus, ConstraintType


class TestActivityModel:
    """Tests for Activity model class."""

    def test_activity_status_default(self):
        """Test default activity status."""
        assert ActivityStatus.NOT_STARTED.value == "not_started"

    def test_activity_constraint_types(self):
        """Test constraint type enum values."""
        assert ConstraintType.ASAP.value == "asap"
        assert ConstraintType.ALAP.value == "alap"

    def test_activity_status_values(self):
        """Test all activity status values."""
        assert ActivityStatus.NOT_STARTED.value == "not_started"
        assert ActivityStatus.IN_PROGRESS.value == "in_progress"
        assert ActivityStatus.COMPLETE.value == "complete"
        assert ActivityStatus.ON_HOLD.value == "on_hold"


class TestActivityEnumMethods:
    """Tests for Activity-related enum methods."""

    def test_constraint_type_asap(self):
        """Test ASAP constraint."""
        constraint = ConstraintType.ASAP
        assert constraint.value == "asap"

    def test_constraint_type_alap(self):
        """Test ALAP constraint."""
        constraint = ConstraintType.ALAP
        assert constraint.value == "alap"

    def test_activity_status_from_string(self):
        """Test creating status from string."""
        status = ActivityStatus("in_progress")
        assert status == ActivityStatus.IN_PROGRESS

    def test_constraint_from_string(self):
        """Test creating constraint from string."""
        constraint = ConstraintType("asap")
        assert constraint == ConstraintType.ASAP


class TestActivityEarnedValue:
    """Tests for Activity earned value calculation."""

    def test_earned_value_zero_percent(self) -> None:
        """Should return zero when percent complete is zero."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test Activity",
            duration=10,
            budgeted_cost=Decimal("10000.00"),
            percent_complete=Decimal("0"),
        )
        assert activity.earned_value == Decimal("0")

    def test_earned_value_fifty_percent(self) -> None:
        """Should return half budgeted cost at 50% complete."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test Activity",
            duration=10,
            budgeted_cost=Decimal("10000.00"),
            percent_complete=Decimal("50"),
        )
        assert activity.earned_value == Decimal("5000.00")

    def test_earned_value_hundred_percent(self) -> None:
        """Should return full budgeted cost at 100% complete."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test Activity",
            duration=10,
            budgeted_cost=Decimal("10000.00"),
            percent_complete=Decimal("100"),
        )
        assert activity.earned_value == Decimal("10000.00")


class TestActivityCalculateFloat:
    """Tests for Activity float calculation."""

    def test_calculate_float_with_dates(self) -> None:
        """Should calculate total float when dates are set."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test Activity",
            duration=5,
        )
        activity.early_start = date(2026, 1, 1)
        activity.late_start = date(2026, 1, 6)

        activity.calculate_float()

        assert activity.total_float == 5
        assert activity.is_critical is False

    def test_calculate_float_critical(self) -> None:
        """Should mark as critical when float is zero."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Critical Activity",
            duration=5,
        )
        activity.early_start = date(2026, 1, 1)
        activity.late_start = date(2026, 1, 1)  # Same date = 0 float

        activity.calculate_float()

        assert activity.total_float == 0
        assert activity.is_critical is True

    def test_calculate_float_no_dates(self) -> None:
        """Should not raise when dates are None."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test Activity",
            duration=5,
        )
        activity.early_start = None
        activity.late_start = None

        # Should not raise
        activity.calculate_float()

        # Float should remain unchanged (is_critical stays None)
        assert activity.is_critical is None
