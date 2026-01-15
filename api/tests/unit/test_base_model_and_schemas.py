"""Unit tests for base model and schema functionality."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.models.activity import Activity
from src.models.dependency import Dependency
from src.models.enums import (
    ActivityStatus,
    ConstraintType,
    DependencyType,
    EVMethod,
    ProgramStatus,
)
from src.models.evms_period import EVMSPeriod, PeriodStatus
from src.models.program import Program
from src.models.user import User
from src.models.wbs import WBSElement


class TestBaseModelTableName:
    """Tests for Base model __tablename__ auto-generation."""

    def test_activity_tablename(self):
        """Activity should pluralize to activities."""
        assert Activity.__tablename__ == "activities"

    def test_user_tablename(self):
        """User should pluralize to users."""
        assert User.__tablename__ == "users"

    def test_program_tablename(self):
        """Program should pluralize to programs."""
        assert Program.__tablename__ == "programs"

    def test_dependency_tablename(self):
        """Dependency should pluralize to dependencies."""
        assert Dependency.__tablename__ == "dependencies"

    def test_wbs_element_tablename(self):
        """WBSElement should convert to wbs_elements."""
        assert WBSElement.__tablename__ == "wbs_elements"

    def test_evms_period_tablename(self):
        """EVMSPeriod should convert correctly."""
        assert EVMSPeriod.__tablename__ == "evms_periods"


class TestBaseModelProperties:
    """Tests for Base model properties and methods."""

    def test_is_deleted_when_null(self):
        """Should return False when deleted_at is None."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
            deleted_at=None,
        )
        assert activity.is_deleted is False

    def test_is_deleted_when_set(self):
        """Should return True when deleted_at is set."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
            deleted_at=datetime.now(),
        )
        assert activity.is_deleted is True

    def test_soft_delete_sets_deleted_at(self):
        """soft_delete should set deleted_at timestamp."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
        )
        assert activity.deleted_at is None

        activity.soft_delete()

        assert activity.deleted_at is not None
        assert activity.is_deleted is True

    def test_restore_clears_deleted_at(self):
        """restore should clear deleted_at timestamp."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
            deleted_at=datetime.now(),
        )
        assert activity.is_deleted is True

        activity.restore()

        assert activity.deleted_at is None
        assert activity.is_deleted is False

    def test_base_repr(self):
        """Should generate debug string with class name and id."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
        )
        repr_str = repr(activity)
        assert "Activity" in repr_str


class TestEnumValues:
    """Tests for enum values and properties."""

    def test_program_status_values(self):
        """Test ProgramStatus enum values."""
        assert ProgramStatus.PLANNING.value == "planning"
        assert ProgramStatus.ACTIVE.value == "active"
        assert ProgramStatus.ON_HOLD.value == "on_hold"
        assert ProgramStatus.COMPLETE.value == "complete"
        assert ProgramStatus.CANCELLED.value == "cancelled"

    def test_program_status_is_active(self):
        """Test is_active property."""
        assert ProgramStatus.PLANNING.is_active is True
        assert ProgramStatus.ACTIVE.is_active is True
        assert ProgramStatus.ON_HOLD.is_active is False

    def test_program_status_is_terminal(self):
        """Test is_terminal property."""
        assert ProgramStatus.COMPLETE.is_terminal is True
        assert ProgramStatus.CANCELLED.is_terminal is True
        assert ProgramStatus.PLANNING.is_terminal is False
        assert ProgramStatus.ACTIVE.is_terminal is False

    def test_program_status_display_name(self):
        """Test display_name property."""
        assert ProgramStatus.ON_HOLD.display_name == "On Hold"
        assert ProgramStatus.PLANNING.display_name == "Planning"

    def test_program_status_transitions(self):
        """Test can_transition_to method."""
        assert ProgramStatus.PLANNING.can_transition_to(ProgramStatus.ACTIVE) is True
        assert ProgramStatus.PLANNING.can_transition_to(ProgramStatus.COMPLETE) is False
        assert ProgramStatus.ACTIVE.can_transition_to(ProgramStatus.COMPLETE) is True
        assert ProgramStatus.COMPLETE.can_transition_to(ProgramStatus.ACTIVE) is False

    def test_dependency_type_values(self):
        """Test DependencyType enum values."""
        assert DependencyType.FS.value == "FS"
        assert DependencyType.SS.value == "SS"
        assert DependencyType.FF.value == "FF"
        assert DependencyType.SF.value == "SF"

    def test_constraint_type_values(self):
        """Test ConstraintType enum values (lowercase)."""
        assert ConstraintType.ASAP.value == "asap"
        assert ConstraintType.ALAP.value == "alap"
        assert ConstraintType.SNET.value == "snet"
        assert ConstraintType.FNLT.value == "fnlt"

    def test_activity_status_values(self):
        """Test ActivityStatus enum values."""
        assert ActivityStatus.NOT_STARTED.value == "not_started"
        assert ActivityStatus.IN_PROGRESS.value == "in_progress"
        assert ActivityStatus.COMPLETE.value == "complete"
        assert ActivityStatus.ON_HOLD.value == "on_hold"

    def test_ev_method_values(self):
        """Test EVMethod enum values."""
        assert EVMethod.PERCENT_COMPLETE.value == "percent_complete"
        assert EVMethod.FIFTY_FIFTY.value == "50/50"
        assert EVMethod.ZERO_HUNDRED.value == "0/100"
        assert EVMethod.LOE.value == "loe"
        assert EVMethod.APPORTIONED.value == "apportioned"


class TestActivityModelProperties:
    """Tests for Activity model computed properties."""

    def test_activity_has_budgeted_cost(self):
        """Test activity with budgeted cost."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=10,
            budgeted_cost=Decimal("1000.00"),
        )
        assert activity.budgeted_cost == Decimal("1000.00")

    def test_activity_float_values(self):
        """Test activity float values."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=10,
            total_float=5,
            free_float=2,
        )
        assert activity.total_float == 5
        assert activity.free_float == 2

    def test_activity_is_critical(self):
        """Test activity is_critical flag."""
        critical_activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Critical",
            duration=10,
            is_critical=True,
        )
        assert critical_activity.is_critical is True

        non_critical = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-002",
            name="Non-Critical",
            duration=5,
            is_critical=False,
        )
        assert non_critical.is_critical is False

    def test_activity_constraint_type(self):
        """Test activity constraint type."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=10,
            constraint_type=ConstraintType.SNET,
        )
        assert activity.constraint_type == ConstraintType.SNET


class TestProgramModelProperties:
    """Tests for Program model properties."""

    def test_program_status(self):
        """Test program with status."""
        program = Program(
            id=uuid4(),
            code="PROG-001",
            name="Test Program",
            owner_id=uuid4(),
            status=ProgramStatus.PLANNING,
        )
        assert program.status == ProgramStatus.PLANNING

    def test_program_repr(self):
        """Test program string representation."""
        program = Program(
            id=uuid4(),
            code="PROG-001",
            name="Test Program",
            owner_id=uuid4(),
            status=ProgramStatus.ACTIVE,
        )
        repr_str = repr(program)
        assert "Program" in repr_str
        assert "PROG-001" in repr_str


class TestWBSModelProperties:
    """Tests for WBS model properties."""

    def test_wbs_element_level(self):
        """Test WBS element level property."""
        wbs = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1.2.3",
            name="Work Package",
            path="1.2.3",
            level=3,
        )
        assert wbs.level == 3

    def test_wbs_element_repr(self):
        """Test WBSElement string representation."""
        wbs = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1.1",
            name="Phase 1",
            path="1.1",
        )
        repr_str = repr(wbs)
        assert "WBSElement" in repr_str


class TestEVMSPeriodModel:
    """Tests for EVMSPeriod model properties."""

    def test_evms_period_values(self):
        """Test EVMSPeriod values."""
        period = EVMSPeriod(
            id=uuid4(),
            program_id=uuid4(),
            period_start=datetime.now().date(),
            period_end=(datetime.now() + timedelta(days=7)).date(),
            period_name="Period 1",
            cumulative_bcws=Decimal("1000.00"),
            cumulative_bcwp=Decimal("800.00"),
            cumulative_acwp=Decimal("900.00"),
        )
        assert period.cumulative_bcws == Decimal("1000.00")
        assert period.cumulative_bcwp == Decimal("800.00")
        assert period.cumulative_acwp == Decimal("900.00")

    def test_evms_period_repr(self):
        """Test EVMSPeriod string representation."""
        period = EVMSPeriod(
            id=uuid4(),
            program_id=uuid4(),
            period_start=datetime.now().date(),
            period_end=(datetime.now() + timedelta(days=7)).date(),
            period_name="Period 1",
            status=PeriodStatus.DRAFT,
            cumulative_bcws=Decimal("1000.00"),
        )
        repr_str = repr(period)
        assert "EVMSPeriod" in repr_str
