"""Unit tests for models and enums."""

import pytest

from src.models.enums import (
    ActivityStatus,
    ConstraintType,
    DependencyType,
    ProgramStatus,
    UserRole,
)
from src.models.evms_period import PeriodStatus


class TestActivityStatusEnum:
    """Tests for ActivityStatus enum."""

    def test_not_started_status(self):
        """Test NOT_STARTED status."""
        status = ActivityStatus.NOT_STARTED
        assert status.value == "not_started"

    def test_in_progress_status(self):
        """Test IN_PROGRESS status."""
        status = ActivityStatus.IN_PROGRESS
        assert status.value == "in_progress"

    def test_complete_status(self):
        """Test COMPLETE status."""
        status = ActivityStatus.COMPLETE
        assert status.value == "complete"

    def test_on_hold_status(self):
        """Test ON_HOLD status."""
        status = ActivityStatus.ON_HOLD
        assert status.value == "on_hold"

    def test_status_from_string(self):
        """Test creating status from string."""
        status = ActivityStatus("not_started")
        assert status == ActivityStatus.NOT_STARTED


class TestDependencyTypeEnum:
    """Tests for DependencyType enum."""

    def test_finish_to_start(self):
        """Test FS dependency type."""
        dep_type = DependencyType.FS
        assert dep_type.value == "FS"

    def test_start_to_start(self):
        """Test SS dependency type."""
        dep_type = DependencyType.SS
        assert dep_type.value == "SS"

    def test_finish_to_finish(self):
        """Test FF dependency type."""
        dep_type = DependencyType.FF
        assert dep_type.value == "FF"

    def test_start_to_finish(self):
        """Test SF dependency type."""
        dep_type = DependencyType.SF
        assert dep_type.value == "SF"

    def test_dependency_from_string(self):
        """Test creating dependency type from string."""
        dep_type = DependencyType("FS")
        assert dep_type == DependencyType.FS


class TestUserRoleEnum:
    """Tests for UserRole enum."""

    def test_admin_role(self):
        """Test ADMIN role."""
        role = UserRole.ADMIN
        assert role.value == "admin"

    def test_program_manager_role(self):
        """Test PROGRAM_MANAGER role."""
        role = UserRole.PROGRAM_MANAGER
        assert role.value == "program_manager"

    def test_analyst_role(self):
        """Test ANALYST role."""
        role = UserRole.ANALYST
        assert role.value == "analyst"

    def test_viewer_role(self):
        """Test VIEWER role."""
        role = UserRole.VIEWER
        assert role.value == "viewer"


class TestPeriodStatusEnum:
    """Tests for PeriodStatus enum."""

    def test_draft_status(self):
        """Test DRAFT status."""
        status = PeriodStatus.DRAFT
        assert status.value == "draft"

    def test_submitted_status(self):
        """Test SUBMITTED status."""
        status = PeriodStatus.SUBMITTED
        assert status.value == "submitted"

    def test_approved_status(self):
        """Test APPROVED status."""
        status = PeriodStatus.APPROVED
        assert status.value == "approved"

    def test_rejected_status(self):
        """Test REJECTED status."""
        status = PeriodStatus.REJECTED
        assert status.value == "rejected"


class TestEnumEquality:
    """Tests for enum equality comparisons."""

    def test_activity_status_equality(self):
        """Test activity status equality."""
        status1 = ActivityStatus.IN_PROGRESS
        status2 = ActivityStatus.IN_PROGRESS
        assert status1 == status2

    def test_activity_status_inequality(self):
        """Test activity status inequality."""
        status1 = ActivityStatus.IN_PROGRESS
        status2 = ActivityStatus.COMPLETE
        assert status1 != status2

    def test_dependency_type_equality(self):
        """Test dependency type equality."""
        type1 = DependencyType.FS
        type2 = DependencyType.FS
        assert type1 == type2

    def test_user_role_equality(self):
        """Test user role equality."""
        role1 = UserRole.ADMIN
        role2 = UserRole.ADMIN
        assert role1 == role2


class TestEnumIteration:
    """Tests for enum iteration."""

    def test_iterate_activity_statuses(self):
        """Test iterating over activity statuses."""
        statuses = list(ActivityStatus)
        assert len(statuses) >= 4
        assert ActivityStatus.NOT_STARTED in statuses
        assert ActivityStatus.COMPLETE in statuses

    def test_iterate_dependency_types(self):
        """Test iterating over dependency types."""
        types = list(DependencyType)
        assert len(types) == 4
        assert DependencyType.FS in types
        assert DependencyType.SS in types
        assert DependencyType.FF in types
        assert DependencyType.SF in types

    def test_iterate_user_roles(self):
        """Test iterating over user roles."""
        roles = list(UserRole)
        assert len(roles) >= 4
        assert UserRole.ADMIN in roles
        assert UserRole.VIEWER in roles


class TestEnumStringConversion:
    """Tests for enum string representation."""

    def test_activity_status_str(self):
        """Test activity status string value."""
        assert ActivityStatus.NOT_STARTED.value == "not_started"
        assert ActivityStatus.IN_PROGRESS.value == "in_progress"

    def test_dependency_type_str(self):
        """Test dependency type string value."""
        assert DependencyType.FS.value == "FS"
        assert DependencyType.SS.value == "SS"

    def test_user_role_str(self):
        """Test user role string value."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.PROGRAM_MANAGER.value == "program_manager"


class TestEnumMembership:
    """Tests for enum membership checking."""

    def test_value_in_activity_status(self):
        """Test checking if value is valid activity status."""
        valid_values = [e.value for e in ActivityStatus]
        assert "not_started" in valid_values
        assert "invalid_status" not in valid_values

    def test_value_in_dependency_type(self):
        """Test checking if value is valid dependency type."""
        valid_values = [e.value for e in DependencyType]
        assert "FS" in valid_values
        assert "XX" not in valid_values

    def test_value_in_user_role(self):
        """Test checking if value is valid user role."""
        valid_values = [e.value for e in UserRole]
        assert "admin" in valid_values
        assert "superuser" not in valid_values


class TestUserRoleHelpers:
    """Tests for UserRole helper methods."""

    def test_has_permission_higher_role(self):
        """Test admin has permission for viewer."""
        assert UserRole.ADMIN.has_permission(UserRole.VIEWER) is True

    def test_has_permission_same_role(self):
        """Test viewer has permission for viewer."""
        assert UserRole.VIEWER.has_permission(UserRole.VIEWER) is True

    def test_has_permission_lower_role(self):
        """Test viewer does not have permission for admin."""
        assert UserRole.VIEWER.has_permission(UserRole.ADMIN) is False

    def test_level_property(self):
        """Test level property returns correct hierarchy."""
        assert UserRole.VIEWER.level == 1
        assert UserRole.ANALYST.level == 2
        assert UserRole.SCHEDULER.level == 3
        assert UserRole.PROGRAM_MANAGER.level == 4
        assert UserRole.ADMIN.level == 5

    def test_display_name(self):
        """Test display name formatting."""
        assert UserRole.PROGRAM_MANAGER.display_name == "Program Manager"
        assert UserRole.ADMIN.display_name == "Admin"

    def test_from_level_valid(self):
        """Test getting role from valid level."""
        assert UserRole.from_level(1) == UserRole.VIEWER
        assert UserRole.from_level(5) == UserRole.ADMIN

    def test_from_level_invalid(self):
        """Test getting role from invalid level raises error."""
        with pytest.raises(ValueError):
            UserRole.from_level(0)
        with pytest.raises(ValueError):
            UserRole.from_level(6)

    def test_get_hierarchy(self):
        """Test hierarchy dictionary."""
        hierarchy = UserRole.get_hierarchy()
        assert len(hierarchy) == 5
        assert hierarchy[UserRole.ADMIN] == 5


class TestProgramStatusHelpers:
    """Tests for ProgramStatus helper methods."""

    def test_is_editable_planning(self):
        """Test planning status is editable."""
        assert ProgramStatus.PLANNING.is_editable is True

    def test_is_editable_active(self):
        """Test active status is editable."""
        assert ProgramStatus.ACTIVE.is_editable is True

    def test_is_editable_complete(self):
        """Test complete status is not editable."""
        assert ProgramStatus.COMPLETE.is_editable is False

    def test_is_editable_cancelled(self):
        """Test cancelled status is not editable."""
        assert ProgramStatus.CANCELLED.is_editable is False

    def test_is_active_states(self):
        """Test is_active property."""
        assert ProgramStatus.PLANNING.is_active is True
        assert ProgramStatus.ACTIVE.is_active is True
        assert ProgramStatus.ON_HOLD.is_active is False
        assert ProgramStatus.COMPLETE.is_active is False

    def test_is_terminal_states(self):
        """Test is_terminal property."""
        assert ProgramStatus.COMPLETE.is_terminal is True
        assert ProgramStatus.CANCELLED.is_terminal is True
        assert ProgramStatus.ACTIVE.is_terminal is False
        assert ProgramStatus.PLANNING.is_terminal is False

    def test_display_name(self):
        """Test display name formatting."""
        assert ProgramStatus.ON_HOLD.display_name == "On Hold"
        assert ProgramStatus.ACTIVE.display_name == "Active"

    def test_can_transition_from_planning(self):
        """Test valid transitions from planning."""
        assert ProgramStatus.PLANNING.can_transition_to(ProgramStatus.ACTIVE) is True
        assert ProgramStatus.PLANNING.can_transition_to(ProgramStatus.ON_HOLD) is True
        assert ProgramStatus.PLANNING.can_transition_to(ProgramStatus.COMPLETE) is False

    def test_can_transition_from_active(self):
        """Test valid transitions from active."""
        assert ProgramStatus.ACTIVE.can_transition_to(ProgramStatus.COMPLETE) is True
        assert ProgramStatus.ACTIVE.can_transition_to(ProgramStatus.ON_HOLD) is True
        assert ProgramStatus.ACTIVE.can_transition_to(ProgramStatus.PLANNING) is False

    def test_can_transition_from_complete(self):
        """Test no transitions from complete."""
        assert ProgramStatus.COMPLETE.can_transition_to(ProgramStatus.ACTIVE) is False
        assert ProgramStatus.COMPLETE.can_transition_to(ProgramStatus.PLANNING) is False

    def test_can_transition_from_on_hold(self):
        """Test valid transitions from on_hold."""
        assert ProgramStatus.ON_HOLD.can_transition_to(ProgramStatus.ACTIVE) is True
        assert ProgramStatus.ON_HOLD.can_transition_to(ProgramStatus.CANCELLED) is True


class TestDependencyTypeHelpers:
    """Tests for DependencyType helper methods."""

    def test_full_name_fs(self):
        """Test full name for FS."""
        assert DependencyType.FS.full_name == "Finish-to-Start"

    def test_full_name_ss(self):
        """Test full name for SS."""
        assert DependencyType.SS.full_name == "Start-to-Start"

    def test_full_name_ff(self):
        """Test full name for FF."""
        assert DependencyType.FF.full_name == "Finish-to-Finish"

    def test_full_name_sf(self):
        """Test full name for SF."""
        assert DependencyType.SF.full_name == "Start-to-Finish"


class TestConstraintTypeEnum:
    """Tests for ConstraintType enum."""

    def test_as_soon_as_possible(self):
        """Test ASAP constraint."""
        constraint = ConstraintType.ASAP
        assert constraint.value == "asap"

    def test_as_late_as_possible(self):
        """Test ALAP constraint."""
        constraint = ConstraintType.ALAP
        assert constraint.value == "alap"

    def test_constraint_type_iteration(self):
        """Test iterating constraint types."""
        types = list(ConstraintType)
        assert len(types) >= 2
        assert ConstraintType.ASAP in types
        assert ConstraintType.ALAP in types
