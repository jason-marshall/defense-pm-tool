"""Unit tests for BaselineComparisonService comparison methods."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.activity import Activity
from src.models.baseline import Baseline
from src.models.wbs import WBSElement
from src.services.baseline_comparison import (
    BaselineComparisonService,
    ComparisonResult,
)


class TestBaselineComparisonServiceCompare:
    """Tests for the main compare method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        return BaselineComparisonService(mock_session)

    @pytest.mark.asyncio
    async def test_compare_no_snapshots(self, service, mock_session):
        """Should return basic result when baseline has no snapshots."""
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="Empty Baseline",
            version=1,
            is_approved=False,
            total_bac=Decimal("0"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
            schedule_snapshot=None,
            cost_snapshot=None,
            wbs_snapshot=None,
        )

        # Mock empty activity/WBS queries
        mock_act_result = MagicMock()
        mock_act_result.scalars.return_value.all.return_value = []
        mock_wbs_result = MagicMock()
        mock_wbs_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [mock_act_result, mock_wbs_result]

        result = await service.compare_to_current(baseline)

        assert result.baseline_name == "Empty Baseline"
        assert result.baseline_version == 1
        assert result.bac_variance == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_compare_with_schedule_snapshot(self, service, mock_session):
        """Should compare schedule when snapshot exists."""
        program_id = uuid4()
        act_id = str(uuid4())
        baseline = Baseline(
            id=uuid4(),
            program_id=program_id,
            name="Schedule Baseline",
            version=1,
            is_approved=False,
            total_bac=Decimal("10000"),
            activity_count=1,
            wbs_count=0,
            created_by_id=uuid4(),
            schedule_snapshot={
                "activities": [
                    {
                        "id": act_id,
                        "code": "ACT-001",
                        "name": "Activity 1",
                        "duration": 10,
                        "budgeted_cost": "10000.00",
                        "early_start": "2026-01-01",
                        "early_finish": "2026-01-15",
                        "is_critical": True,
                    }
                ],
                "critical_path_ids": [act_id],
                "project_finish": "2026-01-15",
            },
            cost_snapshot=None,
            wbs_snapshot=None,
        )

        # Current activity (modified)
        current_activity = MagicMock(spec=Activity)
        current_activity.id = uuid4()
        current_activity.code = "ACT-001"
        current_activity.name = "Activity 1"
        current_activity.duration = 15  # Changed from 10
        current_activity.budgeted_cost = Decimal("12000.00")  # Changed
        current_activity.early_start = date(2026, 1, 1)
        current_activity.early_finish = date(2026, 1, 20)  # Changed
        current_activity.is_critical = True

        mock_act_result = MagicMock()
        mock_act_result.scalars.return_value.all.return_value = [current_activity]
        mock_wbs_result = MagicMock()
        mock_wbs_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [mock_act_result, mock_wbs_result]

        result = await service.compare_to_current(baseline, include_details=True)

        assert result.activities_baseline == 1
        assert result.activities_current == 1
        assert result.activities_modified == 1
        assert result.schedule_variance_days == 5  # 5 days later

    @pytest.mark.asyncio
    async def test_compare_with_added_activities(self, service, mock_session):
        """Should detect added activities."""
        program_id = uuid4()
        baseline = Baseline(
            id=uuid4(),
            program_id=program_id,
            name="Baseline",
            version=1,
            is_approved=False,
            total_bac=Decimal("0"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
            schedule_snapshot={
                "activities": [],
                "critical_path_ids": [],
            },
        )

        # New activity not in baseline
        new_activity = MagicMock(spec=Activity)
        new_activity.id = uuid4()
        new_activity.code = "ACT-NEW"
        new_activity.name = "New Activity"
        new_activity.duration = 5
        new_activity.budgeted_cost = Decimal("5000.00")
        new_activity.early_start = date(2026, 1, 1)
        new_activity.early_finish = date(2026, 1, 6)
        new_activity.is_critical = False

        mock_act_result = MagicMock()
        mock_act_result.scalars.return_value.all.return_value = [new_activity]
        mock_wbs_result = MagicMock()
        mock_wbs_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [mock_act_result, mock_wbs_result]

        result = await service.compare_to_current(baseline, include_details=True)

        assert result.activities_added == 1
        assert "ACT-NEW" in result.added_activity_codes

    @pytest.mark.asyncio
    async def test_compare_with_removed_activities(self, service, mock_session):
        """Should detect removed activities."""
        program_id = uuid4()
        act_id = str(uuid4())
        baseline = Baseline(
            id=uuid4(),
            program_id=program_id,
            name="Baseline",
            version=1,
            is_approved=False,
            total_bac=Decimal("5000"),
            activity_count=1,
            wbs_count=0,
            created_by_id=uuid4(),
            schedule_snapshot={
                "activities": [
                    {
                        "id": act_id,
                        "code": "ACT-OLD",
                        "name": "Old Activity",
                        "duration": 5,
                        "budgeted_cost": "5000.00",
                        "early_start": "2026-01-01",
                        "early_finish": "2026-01-06",
                        "is_critical": False,
                    }
                ],
                "critical_path_ids": [],
            },
        )

        # No current activities
        mock_act_result = MagicMock()
        mock_act_result.scalars.return_value.all.return_value = []
        mock_wbs_result = MagicMock()
        mock_wbs_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [mock_act_result, mock_wbs_result]

        result = await service.compare_to_current(baseline, include_details=True)

        assert result.activities_removed == 1
        assert "ACT-OLD" in result.removed_activity_codes


class TestBaselineComparisonServiceGetCurrentActivities:
    """Tests for _get_current_activities method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        return BaselineComparisonService(mock_session)

    @pytest.mark.asyncio
    async def test_get_current_activities_returns_dict(self, service, mock_session):
        """Should return activities indexed by code."""
        program_id = uuid4()
        activities = []
        for i in range(3):
            act = MagicMock(spec=Activity)
            act.code = f"ACT-{i:03d}"
            activities.append(act)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = activities
        mock_session.execute.return_value = mock_result

        result = await service._get_current_activities(program_id)

        assert len(result) == 3
        assert "ACT-000" in result
        assert "ACT-001" in result
        assert "ACT-002" in result

    @pytest.mark.asyncio
    async def test_get_current_activities_empty(self, service, mock_session):
        """Should return empty dict when no activities."""
        program_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await service._get_current_activities(program_id)

        assert result == {}


class TestBaselineComparisonServiceGetCurrentWbs:
    """Tests for _get_current_wbs method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        return BaselineComparisonService(mock_session)

    @pytest.mark.asyncio
    async def test_get_current_wbs_returns_dict(self, service, mock_session):
        """Should return WBS elements indexed by code."""
        program_id = uuid4()
        elements = []
        for i in range(3):
            wbs = MagicMock(spec=WBSElement)
            wbs.wbs_code = f"1.{i}"
            elements.append(wbs)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = elements
        mock_session.execute.return_value = mock_result

        result = await service._get_current_wbs(program_id)

        assert len(result) == 3
        assert "1.0" in result
        assert "1.1" in result

    @pytest.mark.asyncio
    async def test_get_current_wbs_empty(self, service, mock_session):
        """Should return empty dict when no WBS elements."""
        program_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await service._get_current_wbs(program_id)

        assert result == {}


class TestBaselineComparisonServiceCompareSchedule:
    """Tests for _compare_schedule method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        return BaselineComparisonService(mock_session)

    @pytest.mark.asyncio
    async def test_compare_schedule_no_snapshot(self, service):
        """Should return early when no snapshot."""
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="Test",
            version=1,
            is_approved=False,
            total_bac=Decimal("0"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
            schedule_snapshot=None,
        )

        result = ComparisonResult(
            baseline_id=baseline.id,
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
        )

        await service._compare_schedule(baseline, {}, result, False)

        assert result.activities_baseline == 0

    @pytest.mark.asyncio
    async def test_compare_schedule_critical_path_unchanged(self, service):
        """Should detect when critical path is unchanged."""
        act_id = str(uuid4())
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="Test",
            version=1,
            is_approved=False,
            total_bac=Decimal("10000"),
            activity_count=1,
            wbs_count=0,
            created_by_id=uuid4(),
            schedule_snapshot={
                "activities": [
                    {
                        "id": act_id,
                        "code": "ACT-001",
                        "name": "Activity",
                        "duration": 10,
                        "budgeted_cost": "10000.00",
                        "early_start": None,
                        "early_finish": None,
                        "is_critical": True,
                    }
                ],
                "critical_path_ids": [act_id],
            },
        )

        current_act = MagicMock(spec=Activity)
        current_act.code = "ACT-001"
        current_act.duration = 10
        current_act.budgeted_cost = Decimal("10000.00")
        current_act.early_start = None
        current_act.early_finish = None
        current_act.is_critical = True

        result = ComparisonResult(
            baseline_id=baseline.id,
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
        )

        await service._compare_schedule(baseline, {"ACT-001": current_act}, result, False)

        assert result.critical_path_changed is False
        assert result.activities_unchanged == 1


class TestBaselineComparisonServiceCompareCostWbs:
    """Tests for _compare_cost_wbs method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        return BaselineComparisonService(mock_session)

    @pytest.mark.asyncio
    async def test_compare_cost_wbs_no_snapshot(self, service):
        """Should return early when no WBS/cost snapshot."""
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="Test",
            version=1,
            is_approved=False,
            total_bac=Decimal("0"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
            cost_snapshot=None,
            wbs_snapshot=None,
        )

        result = ComparisonResult(
            baseline_id=baseline.id,
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
        )

        await service._compare_cost_wbs(baseline, {}, result, False)

        assert result.wbs_baseline == 0

    @pytest.mark.asyncio
    async def test_compare_cost_wbs_with_wbs_snapshot(self, service):
        """Should compare WBS from wbs_snapshot."""
        wbs_id = str(uuid4())
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="Test",
            version=1,
            is_approved=False,
            total_bac=Decimal("50000"),
            activity_count=0,
            wbs_count=1,
            created_by_id=uuid4(),
            wbs_snapshot={
                "wbs_elements": [
                    {
                        "id": wbs_id,
                        "wbs_code": "1.1",
                        "name": "Work Package",
                        "budgeted_cost": "50000.00",
                    }
                ]
            },
        )

        current_wbs = MagicMock(spec=WBSElement)
        current_wbs.wbs_code = "1.1"
        current_wbs.budget_at_completion = Decimal("50000.00")

        result = ComparisonResult(
            baseline_id=baseline.id,
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
        )

        await service._compare_cost_wbs(baseline, {"1.1": current_wbs}, result, False)

        assert result.wbs_baseline == 1
        assert result.wbs_current == 1

    @pytest.mark.asyncio
    async def test_compare_cost_wbs_with_cost_snapshot(self, service):
        """Should compare WBS from cost_snapshot."""
        wbs_id = str(uuid4())
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="Test",
            version=1,
            is_approved=False,
            total_bac=Decimal("75000"),
            activity_count=0,
            wbs_count=1,
            created_by_id=uuid4(),
            cost_snapshot={
                "wbs_elements": [
                    {
                        "id": wbs_id,
                        "wbs_code": "1.2",
                        "name": "Control Account",
                        "budgeted_cost": "75000.00",
                    }
                ],
                "total_bac": "75000.00",
            },
        )

        result = ComparisonResult(
            baseline_id=baseline.id,
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
        )

        await service._compare_cost_wbs(baseline, {}, result, False)

        assert result.wbs_baseline == 1
        assert result.wbs_removed == 1


class TestBaselineComparisonServiceActivityModifiedEdgeCases:
    """Edge case tests for _activity_modified method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        return BaselineComparisonService(mock_session)

    def test_activity_modified_none_dates_in_baseline(self, service):
        """Should NOT detect change when baseline has None dates.

        The logic only compares dates if BOTH baseline and current have dates.
        """
        baseline_act = {
            "duration": 10,
            "budgeted_cost": "10000.00",
            "early_start": None,
            "early_finish": None,
            "is_critical": False,
        }

        current_act = MagicMock()
        current_act.duration = 10
        current_act.budgeted_cost = Decimal("10000.00")
        current_act.early_start = date(2026, 1, 1)  # Now has a date
        current_act.early_finish = date(2026, 1, 15)
        current_act.is_critical = False

        # No change detected because baseline doesn't have dates to compare
        result = service._activity_modified(baseline_act, current_act)
        assert result is False

    def test_activity_modified_both_none_dates(self, service):
        """Should not detect change when both have None dates."""
        baseline_act = {
            "duration": 10,
            "budgeted_cost": "10000.00",
            "early_start": None,
            "early_finish": None,
            "is_critical": False,
        }

        current_act = MagicMock()
        current_act.duration = 10
        current_act.budgeted_cost = Decimal("10000.00")
        current_act.early_start = None
        current_act.early_finish = None
        current_act.is_critical = False

        result = service._activity_modified(baseline_act, current_act)
        assert result is False


class TestComparisonResultCalculations:
    """Tests for _calculate_summaries and related calculations."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        return BaselineComparisonService(mock_session)

    def test_calculate_summaries_with_values(self, service):
        """Should calculate variance and percentage correctly."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            total_bac_baseline=Decimal("100000.00"),
            total_bac_current=Decimal("110000.00"),
        )

        service._calculate_summaries(result)

        assert result.bac_variance == Decimal("10000.00")
        assert result.bac_variance_percent == Decimal("10.00")

    def test_calculate_summaries_negative_variance(self, service):
        """Should calculate negative variance."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            total_bac_baseline=Decimal("100000.00"),
            total_bac_current=Decimal("90000.00"),
        )

        service._calculate_summaries(result)

        assert result.bac_variance == Decimal("-10000.00")
        assert result.bac_variance_percent == Decimal("-10.00")

    def test_calculate_summaries_zero_baseline(self, service):
        """Should handle zero baseline BAC."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            total_bac_baseline=Decimal("0.00"),
            total_bac_current=Decimal("50000.00"),
        )

        service._calculate_summaries(result)

        # Should not divide by zero
        assert result.bac_variance == Decimal("50000.00")
        assert result.bac_variance_percent == Decimal("0.00")
