"""Unit tests for ScenarioApplyService.

Tests cover:
- Confirm requirement for applying changes
- Scenario validation (exists, not promoted, not archived)
- Applying activity, WBS, and dependency changes
- Partial failure handling
- Value extraction from wrapped formats
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.services.scenario_apply import (
    ApplyChangesError,
    ApplyResult,
    ChangeApplicationError,
    ScenarioApplyService,
    ScenarioNotFoundError,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_repos():
    """Create mock repositories."""
    return {
        "scenario_repo": AsyncMock(),
        "activity_repo": AsyncMock(),
        "wbs_repo": AsyncMock(),
        "dependency_repo": AsyncMock(),
    }


@pytest.fixture
def service(mock_repos):
    """Create service with mocked dependencies."""
    return ScenarioApplyService(**mock_repos)


@pytest.fixture
def sample_scenario():
    """Create sample active scenario."""
    scenario = MagicMock()
    scenario.id = uuid4()
    scenario.program_id = uuid4()
    scenario.status = "active"
    return scenario


@pytest.fixture
def sample_activity_change():
    """Create sample activity change."""
    change = MagicMock()
    change.entity_type = "activity"
    change.entity_id = uuid4()
    change.change_type = "update"
    change.field_name = "duration"
    change.new_value = 15
    return change


@pytest.fixture
def sample_wbs_change():
    """Create sample WBS change."""
    change = MagicMock()
    change.entity_type = "wbs"
    change.entity_id = uuid4()
    change.change_type = "update"
    change.field_name = "name"
    change.new_value = "Updated WBS Name"
    return change


@pytest.fixture
def sample_dependency_change():
    """Create sample dependency change."""
    change = MagicMock()
    change.entity_type = "dependency"
    change.entity_id = uuid4()
    change.change_type = "delete"
    change.field_name = None
    change.new_value = None
    return change


# =============================================================================
# Test: ApplyChangesError Classes
# =============================================================================


class TestApplyChangesErrorClasses:
    """Tests for custom exception classes."""

    def test_apply_changes_error_with_details(self):
        """Should store message, code, and details."""
        error = ApplyChangesError(
            message="Test error",
            code="TEST_ERROR",
            details={"key": "value"},
        )
        assert error.message == "Test error"
        assert error.code == "TEST_ERROR"
        assert error.details == {"key": "value"}
        assert str(error) == "Test error"

    def test_apply_changes_error_without_details(self):
        """Should default details to empty dict."""
        error = ApplyChangesError("Test error", "TEST_ERROR")
        assert error.details == {}

    def test_scenario_not_found_error(self):
        """Should inherit from ApplyChangesError."""
        error = ScenarioNotFoundError("Not found", "NOT_FOUND")
        assert isinstance(error, ApplyChangesError)

    def test_change_application_error(self):
        """Should inherit from ApplyChangesError."""
        error = ChangeApplicationError("Application failed", "APP_FAILED")
        assert isinstance(error, ApplyChangesError)


# =============================================================================
# Test: ApplyResult
# =============================================================================


class TestApplyResult:
    """Tests for ApplyResult dataclass."""

    def test_successful_result(self):
        """Should store all success fields."""
        scenario_id = uuid4()

        result = ApplyResult(
            success=True,
            scenario_id=scenario_id,
            changes_applied=5,
            changes_failed=0,
            activities_modified=3,
            wbs_modified=1,
            dependencies_modified=1,
            duration_ms=100,
        )

        assert result.success is True
        assert result.scenario_id == scenario_id
        assert result.changes_applied == 5
        assert result.changes_failed == 0
        assert result.activities_modified == 3
        assert result.wbs_modified == 1
        assert result.dependencies_modified == 1
        assert result.errors == []

    def test_partial_failure_result(self):
        """Should store errors on partial failure."""
        scenario_id = uuid4()

        result = ApplyResult(
            success=False,
            scenario_id=scenario_id,
            changes_applied=2,
            changes_failed=1,
            errors=["Activity not found"],
        )

        assert result.success is False
        assert result.changes_applied == 2
        assert result.changes_failed == 1
        assert len(result.errors) == 1


# =============================================================================
# Test: Confirm Requirement
# =============================================================================


class TestConfirmRequirement:
    """Tests for confirm flag requirement."""

    @pytest.mark.asyncio
    async def test_apply_requires_confirm(self, service, mock_repos, sample_scenario):
        """Should require confirm=True to apply."""
        mock_repos["scenario_repo"].get.return_value = sample_scenario

        with pytest.raises(ApplyChangesError) as exc:
            await service.apply_changes(
                scenario_id=sample_scenario.id,
                confirm=False,
            )

        assert exc.value.code == "CONFIRM_REQUIRED"

    @pytest.mark.asyncio
    async def test_apply_with_confirm_proceeds(self, service, mock_repos, sample_scenario):
        """Should proceed when confirm=True."""
        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = []

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True


# =============================================================================
# Test: Scenario Validation
# =============================================================================


class TestScenarioValidation:
    """Tests for scenario eligibility validation."""

    @pytest.mark.asyncio
    async def test_scenario_not_found_raises_error(self, service, mock_repos):
        """Should raise error for non-existent scenario."""
        mock_repos["scenario_repo"].get.return_value = None

        with pytest.raises(ScenarioNotFoundError):
            await service.apply_changes(
                scenario_id=uuid4(),
                confirm=True,
            )

    @pytest.mark.asyncio
    async def test_promoted_scenario_raises_error(self, service, mock_repos, sample_scenario):
        """Should reject applying from promoted scenario."""
        sample_scenario.status = "promoted"
        mock_repos["scenario_repo"].get.return_value = sample_scenario

        with pytest.raises(ApplyChangesError) as exc:
            await service.apply_changes(
                scenario_id=sample_scenario.id,
                confirm=True,
            )

        assert exc.value.code == "ALREADY_PROMOTED"

    @pytest.mark.asyncio
    async def test_archived_scenario_raises_error(self, service, mock_repos, sample_scenario):
        """Should reject applying from archived scenario."""
        sample_scenario.status = "archived"
        mock_repos["scenario_repo"].get.return_value = sample_scenario

        with pytest.raises(ApplyChangesError) as exc:
            await service.apply_changes(
                scenario_id=sample_scenario.id,
                confirm=True,
            )

        assert exc.value.code == "SCENARIO_ARCHIVED"

    @pytest.mark.asyncio
    async def test_active_scenario_is_valid(self, service, mock_repos, sample_scenario):
        """Should accept active scenario."""
        sample_scenario.status = "active"
        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = []

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_draft_scenario_is_valid(self, service, mock_repos, sample_scenario):
        """Should accept draft scenario."""
        sample_scenario.status = "draft"
        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = []

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True


# =============================================================================
# Test: Empty Changes
# =============================================================================


class TestEmptyChanges:
    """Tests for scenarios with no changes."""

    @pytest.mark.asyncio
    async def test_apply_empty_changes(self, service, mock_repos, sample_scenario):
        """Should handle scenario with no changes."""
        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = []

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True
        assert result.changes_applied == 0
        assert result.changes_failed == 0


# =============================================================================
# Test: Activity Changes
# =============================================================================


class TestActivityChanges:
    """Tests for applying activity changes."""

    @pytest.mark.asyncio
    async def test_apply_activity_update(
        self, service, mock_repos, sample_scenario, sample_activity_change
    ):
        """Should apply activity duration change."""
        mock_activity = MagicMock()
        mock_activity.id = sample_activity_change.entity_id

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [sample_activity_change]
        mock_repos["activity_repo"].get_by_id.return_value = mock_activity

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True
        assert result.changes_applied == 1
        assert result.activities_modified == 1

        mock_repos["activity_repo"].update.assert_called_once()
        mock_repos["scenario_repo"].archive.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_activity_update_with_wrapped_value(
        self, service, mock_repos, sample_scenario, sample_activity_change
    ):
        """Should extract value from wrapped format."""
        sample_activity_change.new_value = {"value": 20}
        mock_activity = MagicMock()
        mock_activity.id = sample_activity_change.entity_id

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [sample_activity_change]
        mock_repos["activity_repo"].get_by_id.return_value = mock_activity

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True
        # Verify the update was called with unwrapped value
        call_args = mock_repos["activity_repo"].update.call_args
        assert call_args[0][1]["duration"] == 20

    @pytest.mark.asyncio
    async def test_apply_activity_delete(
        self, service, mock_repos, sample_scenario, sample_activity_change
    ):
        """Should delete activity."""
        sample_activity_change.change_type = "delete"

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [sample_activity_change]

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True
        assert result.changes_applied == 1
        mock_repos["activity_repo"].delete.assert_called_once_with(sample_activity_change.entity_id)

    @pytest.mark.asyncio
    async def test_apply_activity_not_found(
        self, service, mock_repos, sample_scenario, sample_activity_change
    ):
        """Should fail when activity not found for update."""
        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [sample_activity_change]
        mock_repos["activity_repo"].get_by_id.return_value = None

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is False
        assert result.changes_failed == 1
        assert len(result.errors) == 1


# =============================================================================
# Test: WBS Changes
# =============================================================================


class TestWBSChanges:
    """Tests for applying WBS changes."""

    @pytest.mark.asyncio
    async def test_apply_wbs_update(self, service, mock_repos, sample_scenario, sample_wbs_change):
        """Should apply WBS name change."""
        mock_wbs = MagicMock()
        mock_wbs.id = sample_wbs_change.entity_id

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [sample_wbs_change]
        mock_repos["wbs_repo"].get_by_id.return_value = mock_wbs

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True
        assert result.changes_applied == 1
        assert result.wbs_modified == 1

        mock_repos["wbs_repo"].update.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_wbs_delete(self, service, mock_repos, sample_scenario, sample_wbs_change):
        """Should delete WBS element."""
        sample_wbs_change.change_type = "delete"

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [sample_wbs_change]

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True
        mock_repos["wbs_repo"].delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_wbs_not_found(
        self, service, mock_repos, sample_scenario, sample_wbs_change
    ):
        """Should fail when WBS not found for update."""
        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [sample_wbs_change]
        mock_repos["wbs_repo"].get_by_id.return_value = None

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is False
        assert result.changes_failed == 1


# =============================================================================
# Test: Dependency Changes
# =============================================================================


class TestDependencyChanges:
    """Tests for applying dependency changes."""

    @pytest.mark.asyncio
    async def test_apply_dependency_delete(
        self, service, mock_repos, sample_scenario, sample_dependency_change
    ):
        """Should delete dependency."""
        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [sample_dependency_change]

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True
        assert result.changes_applied == 1
        assert result.dependencies_modified == 1
        mock_repos["dependency_repo"].delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_dependency_create(
        self, service, mock_repos, sample_scenario, sample_dependency_change
    ):
        """Should create new dependency."""
        sample_dependency_change.change_type = "create"
        sample_dependency_change.new_value = {
            "predecessor_id": str(uuid4()),
            "successor_id": str(uuid4()),
            "dependency_type": "FS",
            "lag": 0,
        }

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [sample_dependency_change]

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True
        mock_repos["dependency_repo"].create.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_dependency_update(
        self, service, mock_repos, sample_scenario, sample_dependency_change
    ):
        """Should update existing dependency."""
        sample_dependency_change.change_type = "update"
        sample_dependency_change.field_name = "lag"
        sample_dependency_change.new_value = 5

        mock_dependency = MagicMock()
        mock_dependency.id = sample_dependency_change.entity_id

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [sample_dependency_change]
        mock_repos["dependency_repo"].get_by_id.return_value = mock_dependency

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True
        mock_repos["dependency_repo"].update.assert_called_once()


# =============================================================================
# Test: Partial Failure
# =============================================================================


class TestPartialFailure:
    """Tests for partial failure scenarios."""

    @pytest.mark.asyncio
    async def test_partial_failure_multiple_changes(self, service, mock_repos, sample_scenario):
        """Should report partial failure when some changes fail."""
        change1 = MagicMock()
        change1.entity_type = "activity"
        change1.entity_id = uuid4()
        change1.change_type = "update"
        change1.field_name = "duration"
        change1.new_value = 10

        change2 = MagicMock()
        change2.entity_type = "activity"
        change2.entity_id = uuid4()
        change2.change_type = "update"
        change2.field_name = "duration"
        change2.new_value = 20

        # First activity exists, second doesn't
        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [change1, change2]
        mock_repos["activity_repo"].get_by_id.side_effect = [
            MagicMock(),  # First exists
            None,  # Second doesn't
        ]

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is False
        assert result.changes_applied == 1
        assert result.changes_failed == 1
        assert len(result.errors) == 1

        # Should not archive on partial failure
        mock_repos["scenario_repo"].archive.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_entity_changes(self, service, mock_repos, sample_scenario):
        """Should handle changes to multiple entity types."""
        activity_change = MagicMock()
        activity_change.entity_type = "activity"
        activity_change.entity_id = uuid4()
        activity_change.change_type = "update"
        activity_change.field_name = "duration"
        activity_change.new_value = 10

        wbs_change = MagicMock()
        wbs_change.entity_type = "wbs"
        wbs_change.entity_id = uuid4()
        wbs_change.change_type = "update"
        wbs_change.field_name = "name"
        wbs_change.new_value = "New Name"

        dep_change = MagicMock()
        dep_change.entity_type = "dependency"
        dep_change.entity_id = uuid4()
        dep_change.change_type = "delete"

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [
            activity_change,
            wbs_change,
            dep_change,
        ]
        mock_repos["activity_repo"].get_by_id.return_value = MagicMock()
        mock_repos["wbs_repo"].get_by_id.return_value = MagicMock()

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True
        assert result.changes_applied == 3
        assert result.activities_modified == 1
        assert result.wbs_modified == 1
        assert result.dependencies_modified == 1


# =============================================================================
# Test: Archiving
# =============================================================================


class TestArchiving:
    """Tests for scenario archiving after successful apply."""

    @pytest.mark.asyncio
    async def test_archives_on_success(
        self, service, mock_repos, sample_scenario, sample_activity_change
    ):
        """Should archive scenario after successful apply."""
        mock_activity = MagicMock()

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [sample_activity_change]
        mock_repos["activity_repo"].get_by_id.return_value = mock_activity

        await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        mock_repos["scenario_repo"].archive.assert_called_once_with(sample_scenario.id)

    @pytest.mark.asyncio
    async def test_no_archive_on_failure(self, service, mock_repos, sample_scenario):
        """Should not archive scenario on failure."""
        change = MagicMock()
        change.entity_type = "activity"
        change.entity_id = uuid4()
        change.change_type = "update"
        change.field_name = "duration"
        change.new_value = 10

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [change]
        mock_repos["activity_repo"].get_by_id.return_value = None

        await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        mock_repos["scenario_repo"].archive.assert_not_called()


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and less common scenarios."""

    @pytest.mark.asyncio
    async def test_unknown_entity_type_skipped(self, service, mock_repos, sample_scenario):
        """Should skip changes with unknown entity types."""
        change = MagicMock()
        change.entity_type = "unknown_entity"
        change.entity_id = uuid4()
        change.change_type = "update"

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [change]

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True
        assert result.changes_applied == 0
        assert result.changes_failed == 0

    @pytest.mark.asyncio
    async def test_dependency_update_with_wrapped_value(self, service, mock_repos, sample_scenario):
        """Should extract wrapped value for dependency update."""
        change = MagicMock()
        change.entity_type = "dependency"
        change.entity_id = uuid4()
        change.change_type = "update"
        change.field_name = "lag"
        change.new_value = {"value": 10}

        mock_dependency = MagicMock()
        mock_dependency.id = change.entity_id

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [change]
        mock_repos["dependency_repo"].get_by_id.return_value = mock_dependency

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True
        call_args = mock_repos["dependency_repo"].update.call_args
        assert call_args[0][1]["lag"] == 10

    @pytest.mark.asyncio
    async def test_dependency_update_not_found(self, service, mock_repos, sample_scenario):
        """Should fail when dependency not found for update."""
        change = MagicMock()
        change.entity_type = "dependency"
        change.entity_id = uuid4()
        change.change_type = "update"
        change.field_name = "lag"
        change.new_value = 5

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [change]
        mock_repos["dependency_repo"].get_by_id.return_value = None

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is False
        assert result.changes_failed == 1
        assert "Dependency" in result.errors[0]

    @pytest.mark.asyncio
    async def test_wbs_update_with_wrapped_value(
        self, service, mock_repos, sample_scenario, sample_wbs_change
    ):
        """Should extract wrapped value for WBS update."""
        sample_wbs_change.new_value = {"value": "Wrapped WBS Name"}
        mock_wbs = MagicMock()
        mock_wbs.id = sample_wbs_change.entity_id

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [sample_wbs_change]
        mock_repos["wbs_repo"].get_by_id.return_value = mock_wbs

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        assert result.success is True
        call_args = mock_repos["wbs_repo"].update.call_args
        assert call_args[0][1]["name"] == "Wrapped WBS Name"

    @pytest.mark.asyncio
    async def test_dependency_create_with_non_dict_value(
        self, service, mock_repos, sample_scenario
    ):
        """Should handle non-dict new_value for dependency create."""
        change = MagicMock()
        change.entity_type = "dependency"
        change.entity_id = uuid4()
        change.change_type = "create"
        change.new_value = "not a dict"  # Invalid create data

        mock_repos["scenario_repo"].get.return_value = sample_scenario
        mock_repos["scenario_repo"].get_changes.return_value = [change]

        result = await service.apply_changes(
            scenario_id=sample_scenario.id,
            confirm=True,
        )

        # Should succeed but not call create since new_value is not a dict
        assert result.success is True
        mock_repos["dependency_repo"].create.assert_not_called()
