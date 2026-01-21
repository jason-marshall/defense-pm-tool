"""Unit tests for scenario promotion service.

Tests cover:
- Scenario validation (exists, not promoted, not archived)
- Baseline creation with correct snapshots
- Change application to snapshots
- Error handling
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.services.scenario_promotion import (
    BaselineCreationError,
    PromotionError,
    PromotionResult,
    ScenarioNotEligibleError,
    ScenarioNotFoundError,
    ScenarioPromotionService,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_scenario():
    """Create a mock scenario for testing."""
    scenario = MagicMock()
    scenario.id = uuid4()
    scenario.program_id = uuid4()
    scenario.baseline_id = None
    scenario.name = "Test Scenario"
    scenario.description = "Test description"
    scenario.status = "active"
    scenario.is_active = True
    scenario.created_by_id = uuid4()
    scenario.promoted_at = None
    scenario.promoted_baseline_id = None
    return scenario


@pytest.fixture
def mock_activity():
    """Create a mock activity."""
    activity = MagicMock()
    activity.id = uuid4()
    activity.code = "ACT-001"
    activity.name = "Test Activity"
    activity.duration = 10
    activity.early_start = datetime(2024, 1, 1, tzinfo=UTC)
    activity.early_finish = datetime(2024, 1, 11, tzinfo=UTC)
    activity.late_start = datetime(2024, 1, 1, tzinfo=UTC)
    activity.late_finish = datetime(2024, 1, 11, tzinfo=UTC)
    activity.total_float = 0
    activity.is_critical = True
    activity.budgeted_cost = Decimal("10000.00")
    activity.percent_complete = Decimal("50.0")
    return activity


@pytest.fixture
def mock_wbs_element():
    """Create a mock WBS element."""
    wbs = MagicMock()
    wbs.id = uuid4()
    wbs.wbs_code = "1.1"
    wbs.name = "Work Package 1"
    wbs.level = 2
    wbs.path = "1.1"
    wbs.budget_at_completion = Decimal("50000.00")
    return wbs


@pytest.fixture
def mock_change():
    """Create a mock scenario change."""
    change = MagicMock()
    change.id = uuid4()
    change.scenario_id = uuid4()
    change.entity_type = "activity"
    change.entity_id = uuid4()
    change.change_type = "update"
    change.field_name = "duration"
    change.old_value = {"value": 10}
    change.new_value = {"value": 15}
    return change


@pytest.fixture
def mock_baseline():
    """Create a mock baseline."""
    baseline = MagicMock()
    baseline.id = uuid4()
    baseline.program_id = uuid4()
    baseline.name = "Promoted Baseline"
    baseline.version = 2
    return baseline


@pytest.fixture
def promotion_service():
    """Create a promotion service with mocked repositories."""
    scenario_repo = AsyncMock()
    baseline_repo = AsyncMock()
    activity_repo = AsyncMock()
    wbs_repo = AsyncMock()

    # Set up session mock on baseline_repo
    baseline_repo.session = MagicMock()
    baseline_repo.session.add = MagicMock()
    baseline_repo.session.flush = AsyncMock()

    return ScenarioPromotionService(
        scenario_repo=scenario_repo,
        baseline_repo=baseline_repo,
        activity_repo=activity_repo,
        wbs_repo=wbs_repo,
    )


# =============================================================================
# Test: PromotionError Classes
# =============================================================================


class TestPromotionErrorClasses:
    """Tests for custom exception classes."""

    def test_promotion_error_with_details(self):
        """Should store message, code, and details."""
        error = PromotionError(
            message="Test error",
            code="TEST_ERROR",
            details={"key": "value"},
        )
        assert error.message == "Test error"
        assert error.code == "TEST_ERROR"
        assert error.details == {"key": "value"}
        assert str(error) == "Test error"

    def test_promotion_error_without_details(self):
        """Should default details to empty dict."""
        error = PromotionError("Test error", "TEST_ERROR")
        assert error.details == {}

    def test_scenario_not_found_error(self):
        """Should inherit from PromotionError."""
        error = ScenarioNotFoundError("Not found", "NOT_FOUND")
        assert isinstance(error, PromotionError)

    def test_scenario_not_eligible_error(self):
        """Should inherit from PromotionError."""
        error = ScenarioNotEligibleError("Not eligible", "NOT_ELIGIBLE")
        assert isinstance(error, PromotionError)

    def test_baseline_creation_error(self):
        """Should inherit from PromotionError."""
        error = BaselineCreationError("Creation failed", "CREATION_FAILED")
        assert isinstance(error, PromotionError)


# =============================================================================
# Test: PromotionResult
# =============================================================================


class TestPromotionResult:
    """Tests for PromotionResult dataclass."""

    def test_successful_result(self):
        """Should store all success fields."""
        scenario_id = uuid4()
        baseline_id = uuid4()

        result = PromotionResult(
            success=True,
            scenario_id=scenario_id,
            baseline_id=baseline_id,
            baseline_name="New Baseline",
            baseline_version=2,
            changes_count=5,
            duration_ms=150,
        )

        assert result.success is True
        assert result.scenario_id == scenario_id
        assert result.baseline_id == baseline_id
        assert result.baseline_name == "New Baseline"
        assert result.baseline_version == 2
        assert result.changes_count == 5
        assert result.duration_ms == 150
        assert result.error_message is None

    def test_failed_result(self):
        """Should store error message on failure."""
        scenario_id = uuid4()

        result = PromotionResult(
            success=False,
            scenario_id=scenario_id,
            error_message="Promotion failed",
        )

        assert result.success is False
        assert result.error_message == "Promotion failed"
        assert result.baseline_id is None


# =============================================================================
# Test: Scenario Validation
# =============================================================================


class TestScenarioValidation:
    """Tests for scenario eligibility validation."""

    @pytest.mark.asyncio
    async def test_scenario_not_found_raises_error(self, promotion_service):
        """Should raise ScenarioNotFoundError when scenario doesn't exist."""
        promotion_service.scenario_repo.get.return_value = None

        with pytest.raises(ScenarioNotFoundError) as exc_info:
            await promotion_service._get_and_validate_scenario(uuid4())

        assert exc_info.value.code == "SCENARIO_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_already_promoted_raises_error(self, promotion_service, mock_scenario):
        """Should raise error when scenario already promoted."""
        mock_scenario.status = "promoted"
        mock_scenario.promoted_at = datetime.now(UTC)
        promotion_service.scenario_repo.get.return_value = mock_scenario

        with pytest.raises(ScenarioNotEligibleError) as exc_info:
            await promotion_service._get_and_validate_scenario(mock_scenario.id)

        assert exc_info.value.code == "ALREADY_PROMOTED"

    @pytest.mark.asyncio
    async def test_archived_scenario_raises_error(self, promotion_service, mock_scenario):
        """Should raise error when scenario is archived."""
        mock_scenario.status = "archived"
        promotion_service.scenario_repo.get.return_value = mock_scenario

        with pytest.raises(ScenarioNotEligibleError) as exc_info:
            await promotion_service._get_and_validate_scenario(mock_scenario.id)

        assert exc_info.value.code == "SCENARIO_ARCHIVED"

    @pytest.mark.asyncio
    async def test_valid_scenario_returns_scenario(self, promotion_service, mock_scenario):
        """Should return scenario when validation passes."""
        promotion_service.scenario_repo.get.return_value = mock_scenario

        result = await promotion_service._get_and_validate_scenario(mock_scenario.id)

        assert result == mock_scenario


# =============================================================================
# Test: Build Schedule Snapshot
# =============================================================================


class TestBuildScheduleSnapshot:
    """Tests for schedule snapshot building."""

    def test_build_schedule_snapshot_basic(self, promotion_service, mock_activity):
        """Should build snapshot with activity data."""
        activities = [mock_activity]
        changes = []

        snapshot = promotion_service._build_schedule_snapshot(activities, changes)

        assert "activities" in snapshot
        assert "snapshot_at" in snapshot
        assert len(snapshot["activities"]) == 1

        activity_data = snapshot["activities"][0]
        assert activity_data["id"] == str(mock_activity.id)
        assert activity_data["code"] == "ACT-001"
        assert activity_data["name"] == "Test Activity"
        assert activity_data["duration"] == 10
        assert activity_data["is_critical"] is True

    def test_build_schedule_snapshot_applies_changes(
        self, promotion_service, mock_activity, mock_change
    ):
        """Should apply changes to activity data."""
        mock_change.entity_id = mock_activity.id
        mock_change.field_name = "duration"
        mock_change.new_value = {"value": 20}

        activities = [mock_activity]
        changes = [mock_change]

        snapshot = promotion_service._build_schedule_snapshot(activities, changes)

        activity_data = snapshot["activities"][0]
        assert activity_data["duration"] == 20

    def test_build_schedule_snapshot_handles_simple_values(
        self, promotion_service, mock_activity, mock_change
    ):
        """Should handle new_value without dict wrapper."""
        mock_change.entity_id = mock_activity.id
        mock_change.field_name = "name"
        mock_change.new_value = "Updated Activity Name"

        activities = [mock_activity]
        changes = [mock_change]

        snapshot = promotion_service._build_schedule_snapshot(activities, changes)

        activity_data = snapshot["activities"][0]
        assert activity_data["name"] == "Updated Activity Name"

    def test_build_schedule_snapshot_ignores_non_activity_changes(
        self, promotion_service, mock_activity, mock_change
    ):
        """Should not apply non-activity changes."""
        mock_change.entity_type = "wbs"

        activities = [mock_activity]
        changes = [mock_change]

        snapshot = promotion_service._build_schedule_snapshot(activities, changes)

        activity_data = snapshot["activities"][0]
        # Duration should remain original
        assert activity_data["duration"] == 10

    def test_build_schedule_snapshot_with_null_dates(self, promotion_service):
        """Should handle activities with null dates."""
        activity = MagicMock()
        activity.id = uuid4()
        activity.code = "ACT-002"
        activity.name = "Activity No Dates"
        activity.duration = 5
        activity.early_start = None
        activity.early_finish = None
        activity.late_start = None
        activity.late_finish = None
        activity.total_float = None
        activity.is_critical = False
        activity.budgeted_cost = None
        activity.percent_complete = None

        snapshot = promotion_service._build_schedule_snapshot([activity], [])

        activity_data = snapshot["activities"][0]
        assert activity_data["early_start"] is None
        assert activity_data["budgeted_cost"] == "0"
        assert activity_data["percent_complete"] == "0"


# =============================================================================
# Test: Build WBS Snapshot
# =============================================================================


class TestBuildWBSSnapshot:
    """Tests for WBS snapshot building."""

    def test_build_wbs_snapshot_basic(self, promotion_service, mock_wbs_element):
        """Should build snapshot with WBS data."""
        wbs_elements = [mock_wbs_element]
        changes = []

        snapshot = promotion_service._build_wbs_snapshot(wbs_elements, changes)

        assert "elements" in snapshot
        assert "snapshot_at" in snapshot
        assert len(snapshot["elements"]) == 1

        wbs_data = snapshot["elements"][0]
        assert wbs_data["id"] == str(mock_wbs_element.id)
        assert wbs_data["code"] == "1.1"
        assert wbs_data["name"] == "Work Package 1"
        assert wbs_data["level"] == 2

    def test_build_wbs_snapshot_applies_changes(
        self, promotion_service, mock_wbs_element, mock_change
    ):
        """Should apply changes to WBS data."""
        mock_change.entity_type = "wbs"
        mock_change.entity_id = mock_wbs_element.id
        mock_change.field_name = "name"
        mock_change.new_value = {"value": "Updated WBS Name"}

        wbs_elements = [mock_wbs_element]
        changes = [mock_change]

        snapshot = promotion_service._build_wbs_snapshot(wbs_elements, changes)

        wbs_data = snapshot["elements"][0]
        assert wbs_data["name"] == "Updated WBS Name"


# =============================================================================
# Test: Build Cost Snapshot
# =============================================================================


class TestBuildCostSnapshot:
    """Tests for cost snapshot building."""

    def test_build_cost_snapshot_basic(self, promotion_service, mock_wbs_element):
        """Should build snapshot with cost data."""
        wbs_elements = [mock_wbs_element]
        changes = []

        snapshot = promotion_service._build_cost_snapshot(wbs_elements, changes)

        assert "by_wbs" in snapshot
        assert "total_bac" in snapshot
        assert "snapshot_at" in snapshot

        assert str(mock_wbs_element.id) in snapshot["by_wbs"]
        assert snapshot["total_bac"] == "50000.00"

    def test_build_cost_snapshot_applies_budget_changes(
        self, promotion_service, mock_wbs_element, mock_change
    ):
        """Should apply budget changes."""
        mock_change.entity_type = "wbs"
        mock_change.entity_id = mock_wbs_element.id
        mock_change.field_name = "budget_at_completion"
        mock_change.new_value = {"value": "75000.00"}

        wbs_elements = [mock_wbs_element]
        changes = [mock_change]

        snapshot = promotion_service._build_cost_snapshot(wbs_elements, changes)

        assert snapshot["total_bac"] == "75000.00"

    def test_build_cost_snapshot_handles_simple_values(
        self, promotion_service, mock_wbs_element, mock_change
    ):
        """Should handle new_value without dict wrapper."""
        mock_change.entity_type = "wbs"
        mock_change.entity_id = mock_wbs_element.id
        mock_change.field_name = "budgeted_cost"
        mock_change.new_value = "60000.00"

        wbs_elements = [mock_wbs_element]
        changes = [mock_change]

        snapshot = promotion_service._build_cost_snapshot(wbs_elements, changes)

        assert snapshot["total_bac"] == "60000.00"

    def test_build_cost_snapshot_sums_multiple_wbs(self, promotion_service):
        """Should sum costs from multiple WBS elements."""
        wbs1 = MagicMock()
        wbs1.id = uuid4()
        wbs1.budget_at_completion = Decimal("25000.00")

        wbs2 = MagicMock()
        wbs2.id = uuid4()
        wbs2.budget_at_completion = Decimal("35000.00")

        snapshot = promotion_service._build_cost_snapshot([wbs1, wbs2], [])

        assert snapshot["total_bac"] == "60000.00"


# =============================================================================
# Test: Full Promotion Workflow
# =============================================================================


class TestPromotionWorkflow:
    """Tests for the complete promotion workflow."""

    @pytest.mark.asyncio
    async def test_successful_promotion(
        self,
        promotion_service,
        mock_scenario,
        mock_activity,
        mock_wbs_element,
    ):
        """Should complete full promotion workflow."""
        # Set up mocks
        promotion_service.scenario_repo.get.return_value = mock_scenario
        promotion_service.scenario_repo.get_changes.return_value = []
        promotion_service.activity_repo.get_by_program.return_value = [mock_activity]
        promotion_service.wbs_repo.get_by_program.return_value = [mock_wbs_element]
        promotion_service.baseline_repo.get_by_program.return_value = []  # First baseline
        promotion_service.scenario_repo.mark_promoted = AsyncMock()

        result = await promotion_service.promote_scenario(
            scenario_id=mock_scenario.id,
            baseline_name="Promoted Baseline",
            baseline_description="Created from scenario",
            created_by_id=mock_scenario.created_by_id,
        )

        assert result.success is True
        assert result.scenario_id == mock_scenario.id
        assert result.baseline_name == "Promoted Baseline"
        assert result.baseline_version == 1  # First baseline
        assert result.changes_count == 0

        # Verify mark_promoted was called
        promotion_service.scenario_repo.mark_promoted.assert_called_once()

    @pytest.mark.asyncio
    async def test_promotion_with_changes(
        self,
        promotion_service,
        mock_scenario,
        mock_activity,
        mock_wbs_element,
        mock_change,
    ):
        """Should apply changes during promotion."""
        mock_change.entity_id = mock_activity.id

        promotion_service.scenario_repo.get.return_value = mock_scenario
        promotion_service.scenario_repo.get_changes.return_value = [mock_change]
        promotion_service.activity_repo.get_by_program.return_value = [mock_activity]
        promotion_service.wbs_repo.get_by_program.return_value = [mock_wbs_element]
        promotion_service.baseline_repo.get_by_program.return_value = []
        promotion_service.scenario_repo.mark_promoted = AsyncMock()

        result = await promotion_service.promote_scenario(
            scenario_id=mock_scenario.id,
            baseline_name="Promoted Baseline",
            created_by_id=mock_scenario.created_by_id,
        )

        assert result.success is True
        assert result.changes_count == 1

    @pytest.mark.asyncio
    async def test_promotion_increments_version(
        self,
        promotion_service,
        mock_scenario,
        mock_activity,
        mock_wbs_element,
    ):
        """Should increment baseline version correctly."""
        existing_baselines = [MagicMock(), MagicMock()]  # 2 existing baselines

        promotion_service.scenario_repo.get.return_value = mock_scenario
        promotion_service.scenario_repo.get_changes.return_value = []
        promotion_service.activity_repo.get_by_program.return_value = [mock_activity]
        promotion_service.wbs_repo.get_by_program.return_value = [mock_wbs_element]
        promotion_service.baseline_repo.get_by_program.return_value = existing_baselines
        promotion_service.scenario_repo.mark_promoted = AsyncMock()

        result = await promotion_service.promote_scenario(
            scenario_id=mock_scenario.id,
            baseline_name="Third Baseline",
            created_by_id=mock_scenario.created_by_id,
        )

        assert result.baseline_version == 3  # Third baseline

    @pytest.mark.asyncio
    async def test_promotion_handles_unexpected_error(
        self,
        promotion_service,
        mock_scenario,
    ):
        """Should wrap unexpected errors in BaselineCreationError."""
        promotion_service.scenario_repo.get.return_value = mock_scenario
        promotion_service.scenario_repo.get_changes.side_effect = Exception("Database error")

        with pytest.raises(BaselineCreationError) as exc_info:
            await promotion_service.promote_scenario(
                scenario_id=mock_scenario.id,
                baseline_name="Failed Baseline",
                created_by_id=mock_scenario.created_by_id,
            )

        assert "Database error" in str(exc_info.value.message)
        assert exc_info.value.code == "BASELINE_CREATION_FAILED"

    @pytest.mark.asyncio
    async def test_promotion_propagates_not_found_error(self, promotion_service):
        """Should propagate ScenarioNotFoundError."""
        promotion_service.scenario_repo.get.return_value = None

        with pytest.raises(ScenarioNotFoundError):
            await promotion_service.promote_scenario(
                scenario_id=uuid4(),
                baseline_name="Failed Baseline",
                created_by_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_promotion_propagates_not_eligible_error(self, promotion_service, mock_scenario):
        """Should propagate ScenarioNotEligibleError."""
        mock_scenario.status = "promoted"
        promotion_service.scenario_repo.get.return_value = mock_scenario

        with pytest.raises(ScenarioNotEligibleError):
            await promotion_service.promote_scenario(
                scenario_id=mock_scenario.id,
                baseline_name="Failed Baseline",
                created_by_id=uuid4(),
            )
