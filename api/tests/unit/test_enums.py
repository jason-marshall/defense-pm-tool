"""Unit tests for model enums."""

import pytest

from src.models.enums import (
    ConstraintType,
    DependencyType,
    EVMethod,
    ProgramStatus,
    UserRole,
)


class TestDependencyType:
    """Tests for DependencyType enum."""

    def test_all_values(self) -> None:
        """Should have all four dependency types."""
        assert DependencyType.FS == "FS"
        assert DependencyType.FF == "FF"
        assert DependencyType.SS == "SS"
        assert DependencyType.SF == "SF"

    def test_full_name_property(self) -> None:
        """Should return descriptive full names."""
        assert DependencyType.FS.full_name == "Finish-to-Start"
        assert DependencyType.SS.full_name == "Start-to-Start"
        assert DependencyType.FF.full_name == "Finish-to-Finish"
        assert DependencyType.SF.full_name == "Start-to-Finish"

    def test_description_property(self) -> None:
        """Should return detailed descriptions."""
        assert "predecessor finishes" in DependencyType.FS.description
        assert "predecessor starts" in DependencyType.SS.description
        assert "predecessor finishes" in DependencyType.FF.description
        assert "predecessor starts" in DependencyType.SF.description

    def test_affects_start_property(self) -> None:
        """Should identify dependencies that affect successor start."""
        assert DependencyType.FS.affects_start is True
        assert DependencyType.SS.affects_start is True
        assert DependencyType.FF.affects_start is False
        assert DependencyType.SF.affects_start is False

    def test_affects_finish_property(self) -> None:
        """Should identify dependencies that affect successor finish."""
        assert DependencyType.FS.affects_finish is False
        assert DependencyType.SS.affects_finish is False
        assert DependencyType.FF.affects_finish is True
        assert DependencyType.SF.affects_finish is True

    def test_uses_predecessor_finish_property(self) -> None:
        """Should identify dependencies using predecessor finish."""
        assert DependencyType.FS.uses_predecessor_finish is True
        assert DependencyType.FF.uses_predecessor_finish is True
        assert DependencyType.SS.uses_predecessor_finish is False
        assert DependencyType.SF.uses_predecessor_finish is False

    def test_uses_predecessor_start_property(self) -> None:
        """Should identify dependencies using predecessor start."""
        assert DependencyType.SS.uses_predecessor_start is True
        assert DependencyType.SF.uses_predecessor_start is True
        assert DependencyType.FS.uses_predecessor_start is False
        assert DependencyType.FF.uses_predecessor_start is False


class TestConstraintType:
    """Tests for ConstraintType enum."""

    def test_all_values(self) -> None:
        """Should have all constraint types."""
        assert ConstraintType.ASAP == "asap"
        assert ConstraintType.ALAP == "alap"
        assert ConstraintType.SNET == "snet"
        assert ConstraintType.SNLT == "snlt"
        assert ConstraintType.FNET == "fnet"
        assert ConstraintType.FNLT == "fnlt"

    def test_full_name_property(self) -> None:
        """Should return descriptive full names."""
        assert ConstraintType.ASAP.full_name == "As Soon As Possible"
        assert ConstraintType.ALAP.full_name == "As Late As Possible"
        assert ConstraintType.SNET.full_name == "Start No Earlier Than"
        assert ConstraintType.SNLT.full_name == "Start No Later Than"
        assert ConstraintType.FNET.full_name == "Finish No Earlier Than"
        assert ConstraintType.FNLT.full_name == "Finish No Later Than"

    def test_requires_date_property(self) -> None:
        """Should identify constraints requiring a date."""
        assert ConstraintType.ASAP.requires_date is False
        assert ConstraintType.ALAP.requires_date is False
        assert ConstraintType.SNET.requires_date is True
        assert ConstraintType.SNLT.requires_date is True
        assert ConstraintType.FNET.requires_date is True
        assert ConstraintType.FNLT.requires_date is True

    def test_affects_start_property(self) -> None:
        """Should identify constraints affecting start date."""
        assert ConstraintType.SNET.affects_start is True
        assert ConstraintType.SNLT.affects_start is True
        assert ConstraintType.ASAP.affects_start is False
        assert ConstraintType.FNET.affects_start is False
        assert ConstraintType.FNLT.affects_start is False

    def test_affects_finish_property(self) -> None:
        """Should identify constraints affecting finish date."""
        assert ConstraintType.FNET.affects_finish is True
        assert ConstraintType.FNLT.affects_finish is True
        assert ConstraintType.ASAP.affects_finish is False
        assert ConstraintType.SNET.affects_finish is False
        assert ConstraintType.SNLT.affects_finish is False

    def test_is_no_earlier_than_property(self) -> None:
        """Should identify 'no earlier than' constraints."""
        assert ConstraintType.SNET.is_no_earlier_than is True
        assert ConstraintType.FNET.is_no_earlier_than is True
        assert ConstraintType.SNLT.is_no_earlier_than is False
        assert ConstraintType.FNLT.is_no_earlier_than is False
        assert ConstraintType.ASAP.is_no_earlier_than is False

    def test_is_no_later_than_property(self) -> None:
        """Should identify 'no later than' constraints."""
        assert ConstraintType.SNLT.is_no_later_than is True
        assert ConstraintType.FNLT.is_no_later_than is True
        assert ConstraintType.SNET.is_no_later_than is False
        assert ConstraintType.FNET.is_no_later_than is False
        assert ConstraintType.ALAP.is_no_later_than is False


class TestEVMethod:
    """Tests for EVMethod enum."""

    def test_all_values(self) -> None:
        """Should have all EV methods."""
        assert EVMethod.ZERO_HUNDRED == "0/100"
        assert EVMethod.FIFTY_FIFTY == "50/50"
        assert EVMethod.PERCENT_COMPLETE == "percent_complete"
        assert EVMethod.MILESTONE_WEIGHT == "milestone_weight"
        assert EVMethod.LOE == "loe"
        assert EVMethod.APPORTIONED == "apportioned"

    def test_display_name_property(self) -> None:
        """Should return display names."""
        assert "0/100" in EVMethod.ZERO_HUNDRED.display_name
        assert "50/50" in EVMethod.FIFTY_FIFTY.display_name
        assert "Percent" in EVMethod.PERCENT_COMPLETE.display_name
        assert "Milestone" in EVMethod.MILESTONE_WEIGHT.display_name
        assert "Level of Effort" in EVMethod.LOE.display_name
        assert "Apportioned" in EVMethod.APPORTIONED.display_name

    def test_description_property(self) -> None:
        """Should return method descriptions."""
        assert "0%" in EVMethod.ZERO_HUNDRED.description
        assert "50%" in EVMethod.FIFTY_FIFTY.description
        assert "percent" in EVMethod.PERCENT_COMPLETE.description.lower()
        assert "milestone" in EVMethod.MILESTONE_WEIGHT.description.lower()
        assert "BCWS" in EVMethod.LOE.description or "planned" in EVMethod.LOE.description.lower()
        assert (
            "related" in EVMethod.APPORTIONED.description.lower()
            or "base" in EVMethod.APPORTIONED.description.lower()
        )

    def test_recommended_duration_property(self) -> None:
        """Should return recommended durations."""
        assert "month" in EVMethod.ZERO_HUNDRED.recommended_duration.lower()
        assert "month" in EVMethod.FIFTY_FIFTY.recommended_duration.lower()
        assert "any" in EVMethod.PERCENT_COMPLETE.recommended_duration.lower()
        assert "month" in EVMethod.MILESTONE_WEIGHT.recommended_duration.lower()
        assert (
            "any" in EVMethod.LOE.recommended_duration.lower()
            or "support" in EVMethod.LOE.recommended_duration.lower()
        )

    def test_requires_milestones_property(self) -> None:
        """Should identify methods requiring milestones."""
        assert EVMethod.MILESTONE_WEIGHT.requires_milestones is True
        assert EVMethod.ZERO_HUNDRED.requires_milestones is False
        assert EVMethod.FIFTY_FIFTY.requires_milestones is False
        assert EVMethod.PERCENT_COMPLETE.requires_milestones is False
        assert EVMethod.LOE.requires_milestones is False

    def test_requires_base_activity_property(self) -> None:
        """Should identify methods requiring base activity."""
        assert EVMethod.APPORTIONED.requires_base_activity is True
        assert EVMethod.ZERO_HUNDRED.requires_base_activity is False
        assert EVMethod.MILESTONE_WEIGHT.requires_base_activity is False


class TestProgramStatus:
    """Tests for ProgramStatus enum."""

    def test_all_values(self) -> None:
        """Should have all program statuses."""
        assert ProgramStatus.PLANNING == "planning"
        assert ProgramStatus.ACTIVE == "active"
        assert ProgramStatus.ON_HOLD == "on_hold"
        assert ProgramStatus.COMPLETE == "complete"
        assert ProgramStatus.CANCELLED == "cancelled"

    def test_is_active_property(self) -> None:
        """Should identify active statuses."""
        assert ProgramStatus.ACTIVE.is_active is True
        assert ProgramStatus.PLANNING.is_active is True
        assert ProgramStatus.ON_HOLD.is_active is False
        assert ProgramStatus.COMPLETE.is_active is False
        assert ProgramStatus.CANCELLED.is_active is False

    def test_is_editable_property(self) -> None:
        """Should identify editable statuses."""
        assert ProgramStatus.PLANNING.is_editable is True
        assert ProgramStatus.ACTIVE.is_editable is True
        assert ProgramStatus.ON_HOLD.is_editable is False
        assert ProgramStatus.COMPLETE.is_editable is False
        assert ProgramStatus.CANCELLED.is_editable is False

    def test_is_terminal_property(self) -> None:
        """Should identify terminal statuses."""
        assert ProgramStatus.COMPLETE.is_terminal is True
        assert ProgramStatus.CANCELLED.is_terminal is True
        assert ProgramStatus.PLANNING.is_terminal is False
        assert ProgramStatus.ACTIVE.is_terminal is False
        assert ProgramStatus.ON_HOLD.is_terminal is False

    def test_display_name_property(self) -> None:
        """Should return human-readable names."""
        assert ProgramStatus.PLANNING.display_name == "Planning"
        assert ProgramStatus.ACTIVE.display_name == "Active"
        assert ProgramStatus.ON_HOLD.display_name == "On Hold"

    def test_can_transition_to_method(self) -> None:
        """Should validate status transitions."""
        # From PLANNING
        assert ProgramStatus.PLANNING.can_transition_to(ProgramStatus.ACTIVE) is True
        assert ProgramStatus.PLANNING.can_transition_to(ProgramStatus.CANCELLED) is True
        assert ProgramStatus.PLANNING.can_transition_to(ProgramStatus.COMPLETE) is False

        # From ACTIVE
        assert ProgramStatus.ACTIVE.can_transition_to(ProgramStatus.ON_HOLD) is True
        assert ProgramStatus.ACTIVE.can_transition_to(ProgramStatus.COMPLETE) is True
        assert ProgramStatus.ACTIVE.can_transition_to(ProgramStatus.CANCELLED) is True
        assert ProgramStatus.ACTIVE.can_transition_to(ProgramStatus.PLANNING) is False

        # From COMPLETE (terminal)
        assert ProgramStatus.COMPLETE.can_transition_to(ProgramStatus.ACTIVE) is False
        assert ProgramStatus.COMPLETE.can_transition_to(ProgramStatus.PLANNING) is False

        # From CANCELLED (terminal)
        assert ProgramStatus.CANCELLED.can_transition_to(ProgramStatus.ACTIVE) is False

        # From ON_HOLD
        assert ProgramStatus.ON_HOLD.can_transition_to(ProgramStatus.ACTIVE) is True
        assert ProgramStatus.ON_HOLD.can_transition_to(ProgramStatus.CANCELLED) is True


class TestUserRole:
    """Tests for UserRole enum."""

    def test_all_values(self) -> None:
        """Should have all user roles."""
        assert UserRole.VIEWER == "viewer"
        assert UserRole.ANALYST == "analyst"
        assert UserRole.SCHEDULER == "scheduler"
        assert UserRole.PROGRAM_MANAGER == "program_manager"
        assert UserRole.ADMIN == "admin"

    def test_hierarchy(self) -> None:
        """Should have correct hierarchy levels."""
        hierarchy = UserRole.get_hierarchy()
        assert hierarchy[UserRole.VIEWER] == 1
        assert hierarchy[UserRole.ANALYST] == 2
        assert hierarchy[UserRole.SCHEDULER] == 3
        assert hierarchy[UserRole.PROGRAM_MANAGER] == 4
        assert hierarchy[UserRole.ADMIN] == 5

    def test_level_property(self) -> None:
        """Should return correct level for each role."""
        assert UserRole.VIEWER.level == 1
        assert UserRole.ADMIN.level == 5

    def test_has_permission(self) -> None:
        """Should correctly check permissions."""
        # Admin has all permissions
        assert UserRole.ADMIN.has_permission(UserRole.VIEWER) is True
        assert UserRole.ADMIN.has_permission(UserRole.ADMIN) is True

        # Viewer only has viewer permission
        assert UserRole.VIEWER.has_permission(UserRole.VIEWER) is True
        assert UserRole.VIEWER.has_permission(UserRole.ANALYST) is False
        assert UserRole.VIEWER.has_permission(UserRole.ADMIN) is False

        # Mid-level role
        assert UserRole.SCHEDULER.has_permission(UserRole.VIEWER) is True
        assert UserRole.SCHEDULER.has_permission(UserRole.SCHEDULER) is True
        assert UserRole.SCHEDULER.has_permission(UserRole.ADMIN) is False

    def test_display_name_property(self) -> None:
        """Should return human-readable names."""
        assert UserRole.VIEWER.display_name == "Viewer"
        assert UserRole.PROGRAM_MANAGER.display_name == "Program Manager"
        assert UserRole.ADMIN.display_name == "Admin"

    def test_from_level(self) -> None:
        """Should get role from level."""
        assert UserRole.from_level(1) == UserRole.VIEWER
        assert UserRole.from_level(5) == UserRole.ADMIN

    def test_from_level_invalid(self) -> None:
        """Should raise for invalid level."""
        with pytest.raises(ValueError, match="Invalid role level"):
            UserRole.from_level(99)
