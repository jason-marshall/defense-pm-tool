"""Unit tests for Activity CRUD operations."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from src.models.activity import Activity
from src.models.enums import ConstraintType
from src.schemas.activity import ActivityCreate, ActivityUpdate


class TestActivityModel:
    """Tests for Activity model."""

    def test_activity_properties(self):
        """Test Activity computed properties."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Test",
            code="T-001",
            duration=10,
            percent_complete=Decimal("50.00"),
            budgeted_cost=Decimal("10000.00"),
            actual_cost=Decimal("4500.00"),
        )

        assert activity.remaining_duration == 5
        assert activity.earned_value == Decimal("5000.00")
        assert not activity.is_completed
        assert not activity.is_started  # actual_start is None

    def test_activity_is_started(self):
        """Test is_started property when actual_start is set."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Test",
            code="T-001",
            duration=10,
            actual_start=date(2026, 1, 15),
            percent_complete=Decimal("25.00"),
        )

        assert activity.is_started
        assert not activity.is_completed
        assert activity.is_in_progress

    def test_activity_is_completed_by_percent(self):
        """Test is_completed when percent_complete is 100."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Test",
            code="T-001",
            duration=10,
            percent_complete=Decimal("100.00"),
        )

        assert activity.is_completed
        assert activity.remaining_duration == 0

    def test_activity_is_completed_by_actual_finish(self):
        """Test is_completed when actual_finish is set."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Test",
            code="T-001",
            duration=10,
            actual_finish=date(2026, 1, 20),
            percent_complete=Decimal("80.00"),
        )

        assert activity.is_completed

    def test_milestone_has_zero_duration(self):
        """Milestone should have duration 0."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Milestone",
            code="M-001",
            duration=0,
            is_milestone=True,
        )
        assert activity.is_milestone
        assert activity.duration == 0

    def test_earned_value_calculation(self):
        """Test earned value (BCWP) calculation."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Test",
            code="T-001",
            duration=10,
            budgeted_cost=Decimal("50000.00"),
            percent_complete=Decimal("30.00"),
        )

        expected_ev = Decimal("50000.00") * Decimal("30.00") / Decimal("100.00")
        assert activity.earned_value == expected_ev

    def test_remaining_duration_at_zero_progress(self):
        """Test remaining duration at 0% complete."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Test",
            code="T-001",
            duration=20,
            percent_complete=Decimal("0.00"),
        )

        assert activity.remaining_duration == 20


class TestActivityCreate:
    """Tests for ActivityCreate schema."""

    def test_valid_activity(self):
        """Should create activity with valid data."""
        data = ActivityCreate(
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Design Review",
            code="DR-001",
            duration=5,
            budgeted_cost=Decimal("10000.00"),
        )
        assert data.name == "Design Review"
        assert data.duration == 5

    def test_milestone_forces_zero_duration(self):
        """Milestone should force duration to 0."""
        data = ActivityCreate(
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Phase Complete",
            code="M-001",
            duration=5,
            is_milestone=True,
        )
        assert data.duration == 0
        assert data.is_milestone

    def test_constraint_date_required_for_snet(self):
        """SNET constraint requires date."""
        with pytest.raises(ValueError, match="constraint_date is required"):
            ActivityCreate(
                program_id=uuid4(),
                wbs_id=uuid4(),
                name="Test",
                code="T-001",
                constraint_type=ConstraintType.SNET,
            )

    def test_constraint_date_required_for_snlt(self):
        """SNLT constraint requires date."""
        with pytest.raises(ValueError, match="constraint_date is required"):
            ActivityCreate(
                program_id=uuid4(),
                wbs_id=uuid4(),
                name="Test",
                code="T-001",
                constraint_type=ConstraintType.SNLT,
            )

    def test_constraint_date_required_for_fnet(self):
        """FNET constraint requires date."""
        with pytest.raises(ValueError, match="constraint_date is required"):
            ActivityCreate(
                program_id=uuid4(),
                wbs_id=uuid4(),
                name="Test",
                code="T-001",
                constraint_type=ConstraintType.FNET,
            )

    def test_constraint_date_required_for_fnlt(self):
        """FNLT constraint requires date."""
        with pytest.raises(ValueError, match="constraint_date is required"):
            ActivityCreate(
                program_id=uuid4(),
                wbs_id=uuid4(),
                name="Test",
                code="T-001",
                constraint_type=ConstraintType.FNLT,
            )

    def test_asap_does_not_require_date(self):
        """ASAP constraint does not require date."""
        data = ActivityCreate(
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Test",
            code="T-001",
            constraint_type=ConstraintType.ASAP,
        )
        assert data.constraint_type == ConstraintType.ASAP
        assert data.constraint_date is None

    def test_alap_does_not_require_date(self):
        """ALAP constraint does not require date."""
        data = ActivityCreate(
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Test",
            code="T-001",
            constraint_type=ConstraintType.ALAP,
        )
        assert data.constraint_type == ConstraintType.ALAP
        assert data.constraint_date is None

    def test_snet_with_constraint_date(self):
        """SNET constraint with date should be valid."""
        data = ActivityCreate(
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Test",
            code="T-001",
            constraint_type=ConstraintType.SNET,
            constraint_date=date(2026, 3, 15),
        )
        assert data.constraint_type == ConstraintType.SNET
        assert data.constraint_date == date(2026, 3, 15)

    def test_default_values(self):
        """Test default values for optional fields."""
        data = ActivityCreate(
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Test",
            code="T-001",
        )
        assert data.duration == 0
        assert data.is_milestone is False
        assert data.constraint_type == ConstraintType.ASAP
        assert data.budgeted_cost == Decimal("0.00")


class TestActivityUpdate:
    """Tests for ActivityUpdate schema."""

    def test_partial_update(self):
        """Should allow partial updates."""
        data = ActivityUpdate(name="Updated Name")
        assert data.name == "Updated Name"
        assert data.duration is None

    def test_percent_complete_range_upper_bound(self):
        """Percent complete cannot exceed 100."""
        with pytest.raises(ValueError):
            ActivityUpdate(percent_complete=Decimal("150.00"))

    def test_percent_complete_range_lower_bound(self):
        """Percent complete cannot be negative."""
        with pytest.raises(ValueError):
            ActivityUpdate(percent_complete=Decimal("-10.00"))

    def test_percent_complete_valid_range(self):
        """Percent complete within valid range should work."""
        data = ActivityUpdate(percent_complete=Decimal("75.50"))
        assert data.percent_complete == Decimal("75.50")

    def test_milestone_forces_zero_duration_in_update(self):
        """When is_milestone is True in update, duration should be 0."""
        data = ActivityUpdate(is_milestone=True, duration=10)
        assert data.duration == 0
        assert data.is_milestone is True

    def test_duration_update_without_milestone(self):
        """Can update duration without affecting milestone status."""
        data = ActivityUpdate(duration=15)
        assert data.duration == 15
        assert data.is_milestone is None

    def test_all_fields_update(self):
        """Test updating all fields at once."""
        data = ActivityUpdate(
            name="Updated Activity",
            description="Updated description",
            duration=20,
            percent_complete=Decimal("50.00"),
            budgeted_cost=Decimal("25000.00"),
            actual_cost=Decimal("12000.00"),
            actual_start=date(2026, 2, 1),
        )
        assert data.name == "Updated Activity"
        assert data.duration == 20
        assert data.percent_complete == Decimal("50.00")
        assert data.actual_start == date(2026, 2, 1)
