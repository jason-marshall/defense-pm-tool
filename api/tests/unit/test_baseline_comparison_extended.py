"""Extended unit tests for Baseline Comparison Service."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.activity import Activity
from src.models.baseline import Baseline
from src.models.wbs import WBSElement
from src.services.baseline_comparison import (
    ActivityVariance,
    BaselineComparisonService,
    ComparisonResult,
    WBSVariance,
    comparison_result_to_dict,
)


class TestBaselineComparisonServiceHelpers:
    """Tests for BaselineComparisonService helper methods."""

    def test_activity_modified_duration_change(self):
        """Test activity modified detection for duration change."""
        service = BaselineComparisonService(MagicMock())

        baseline_act = {
            "duration": 10,
            "budgeted_cost": "10000.00",
            "early_start": None,
            "early_finish": None,
            "is_critical": False,
        }

        current_act = MagicMock()
        current_act.duration = 15  # Changed
        current_act.budgeted_cost = Decimal("10000.00")
        current_act.early_start = None
        current_act.early_finish = None
        current_act.is_critical = False

        assert service._activity_modified(baseline_act, current_act) is True

    def test_activity_modified_bac_change(self):
        """Test activity modified detection for BAC change."""
        service = BaselineComparisonService(MagicMock())

        baseline_act = {
            "duration": 10,
            "budgeted_cost": "10000.00",
            "early_start": None,
            "early_finish": None,
            "is_critical": False,
        }

        current_act = MagicMock()
        current_act.duration = 10
        current_act.budgeted_cost = Decimal("12000.00")  # Changed
        current_act.early_start = None
        current_act.early_finish = None
        current_act.is_critical = False

        assert service._activity_modified(baseline_act, current_act) is True

    def test_activity_modified_date_change(self):
        """Test activity modified detection for date change."""
        service = BaselineComparisonService(MagicMock())

        baseline_act = {
            "duration": 10,
            "budgeted_cost": "10000.00",
            "early_start": "2026-01-01",
            "early_finish": "2026-01-15",
            "is_critical": False,
        }

        current_act = MagicMock()
        current_act.duration = 10
        current_act.budgeted_cost = Decimal("10000.00")
        current_act.early_start = date(2026, 1, 5)  # Changed
        current_act.early_finish = date(2026, 1, 15)
        current_act.is_critical = False

        assert service._activity_modified(baseline_act, current_act) is True

    def test_activity_modified_critical_change(self):
        """Test activity modified detection for critical path change."""
        service = BaselineComparisonService(MagicMock())

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
        current_act.is_critical = True  # Changed

        assert service._activity_modified(baseline_act, current_act) is True

    def test_activity_not_modified(self):
        """Test activity not modified when values match."""
        service = BaselineComparisonService(MagicMock())

        baseline_act = {
            "duration": 10,
            "budgeted_cost": "10000.00",
            "early_start": "2026-01-01",
            "early_finish": "2026-01-15",
            "is_critical": True,
        }

        current_act = MagicMock()
        current_act.duration = 10
        current_act.budgeted_cost = Decimal("10000.00")
        current_act.early_start = date(2026, 1, 1)
        current_act.early_finish = date(2026, 1, 15)
        current_act.is_critical = True

        assert service._activity_modified(baseline_act, current_act) is False

    def test_build_activity_variance(self):
        """Test building detailed activity variance."""
        service = BaselineComparisonService(MagicMock())

        baseline_act = {
            "id": str(uuid4()),
            "code": "ACT-001",
            "name": "Test Activity",
            "duration": 10,
            "budgeted_cost": "10000.00",
            "early_start": "2026-01-01",
            "early_finish": "2026-01-15",
            "is_critical": False,
        }

        current_act = MagicMock()
        current_act.id = uuid4()
        current_act.code = "ACT-001"
        current_act.name = "Test Activity"
        current_act.duration = 12
        current_act.budgeted_cost = Decimal("11000.00")
        current_act.early_start = date(2026, 1, 5)
        current_act.early_finish = date(2026, 1, 20)
        current_act.is_critical = True

        variance = service._build_activity_variance(baseline_act, current_act, "modified")

        assert variance.activity_code == "ACT-001"
        assert variance.change_type == "modified"
        assert variance.duration_baseline == 10
        assert variance.duration_current == 12
        assert variance.duration_variance == 2
        assert variance.bac_baseline == Decimal("10000.00")
        assert variance.bac_current == Decimal("11000.00")
        assert variance.bac_variance == Decimal("1000.00")
        assert variance.was_critical is False
        assert variance.is_critical is True
        assert variance.start_variance_days == 4
        assert variance.finish_variance_days == 5

    def test_calculate_summaries(self):
        """Test summary calculation."""
        service = BaselineComparisonService(MagicMock())

        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            total_bac_baseline=Decimal("100000.00"),
            total_bac_current=Decimal("120000.00"),
        )

        service._calculate_summaries(result)

        assert result.bac_variance == Decimal("20000.00")
        assert result.bac_variance_percent == Decimal("20.00")

    def test_calculate_summaries_zero_baseline(self):
        """Test summary calculation with zero baseline."""
        service = BaselineComparisonService(MagicMock())

        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            total_bac_baseline=Decimal("0.00"),
            total_bac_current=Decimal("50000.00"),
        )

        service._calculate_summaries(result)

        assert result.bac_variance == Decimal("50000.00")
        assert result.bac_variance_percent == Decimal("0.00")  # No division by zero


class TestActivityVarianceEdgeCases:
    """Test edge cases for ActivityVariance."""

    def test_variance_with_none_dates(self):
        """Test variance when dates are None."""
        variance = ActivityVariance(
            activity_id=str(uuid4()),
            activity_code="ACT-001",
            activity_name="Test",
            change_type="modified",
            duration_baseline=10,
            duration_current=10,
            start_baseline=None,
            start_current=None,
            finish_baseline=None,
            finish_current=None,
        )

        assert variance.start_variance_days is None
        assert variance.finish_variance_days is None

    def test_variance_with_partial_dates(self):
        """Test variance when only baseline has dates."""
        variance = ActivityVariance(
            activity_id=str(uuid4()),
            activity_code="ACT-001",
            activity_name="Test",
            change_type="modified",
            start_baseline=date(2026, 1, 1),
            start_current=None,
        )

        assert variance.start_baseline == date(2026, 1, 1)
        assert variance.start_current is None


class TestWBSVarianceEdgeCases:
    """Test edge cases for WBSVariance."""

    def test_wbs_variance_removed(self):
        """Test WBS variance for removed element."""
        variance = WBSVariance(
            wbs_id=str(uuid4()),
            wbs_code="1.1.1",
            wbs_name="Removed Package",
            change_type="removed",
            bac_baseline=Decimal("75000.00"),
            bac_current=None,
            bac_variance=None,
        )

        assert variance.change_type == "removed"
        assert variance.bac_current is None

    def test_wbs_variance_unchanged(self):
        """Test WBS variance for unchanged element."""
        variance = WBSVariance(
            wbs_id=str(uuid4()),
            wbs_code="1.2",
            wbs_name="Unchanged Package",
            change_type="unchanged",
            bac_baseline=Decimal("50000.00"),
            bac_current=Decimal("50000.00"),
            bac_variance=Decimal("0.00"),
        )

        assert variance.change_type == "unchanged"
        assert variance.bac_variance == Decimal("0.00")


class TestComparisonResultEdgeCases:
    """Test edge cases for ComparisonResult."""

    def test_empty_comparison_result(self):
        """Test comparison result with no data."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Empty Baseline",
            baseline_version=1,
            comparison_date=datetime.now(),
        )

        assert result.activities_baseline == 0
        assert result.activities_current == 0
        assert len(result.activity_variances) == 0
        assert len(result.wbs_variances) == 0
        assert result.bac_variance == Decimal("0.00")

    def test_comparison_result_with_large_variance_lists(self):
        """Test comparison result with many variances."""
        activity_variances = [
            ActivityVariance(
                activity_id=str(uuid4()),
                activity_code=f"ACT-{i:03d}",
                activity_name=f"Activity {i}",
                change_type="modified",
            )
            for i in range(100)
        ]

        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Large Baseline",
            baseline_version=1,
            comparison_date=datetime.now(),
            activity_variances=activity_variances,
        )

        assert len(result.activity_variances) == 100

    def test_comparison_result_critical_path_identical(self):
        """Test when critical path is identical."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            critical_path_baseline=["ACT-001", "ACT-002", "ACT-003"],
            critical_path_current=["ACT-001", "ACT-002", "ACT-003"],
            critical_path_changed=False,
        )

        assert result.critical_path_changed is False


class TestComparisonResultToDictEdgeCases:
    """Test edge cases for comparison_result_to_dict."""

    def test_dict_with_empty_lists(self):
        """Test conversion with empty lists."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
        )

        data = comparison_result_to_dict(result)

        assert data["activity_variances"] == []
        assert data["wbs_variances"] == []
        assert data["added_activity_codes"] == []
        assert data["removed_activity_codes"] == []
        assert data["modified_activity_codes"] == []

    def test_dict_with_null_bac_values(self):
        """Test conversion when BAC values are None."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            activity_variances=[
                ActivityVariance(
                    activity_id=str(uuid4()),
                    activity_code="ACT-001",
                    activity_name="Test",
                    change_type="added",
                    bac_baseline=None,
                    bac_current=Decimal("10000.00"),
                    bac_variance=None,
                ),
            ],
        )

        data = comparison_result_to_dict(result)

        variance = data["activity_variances"][0]
        assert variance["bac_baseline"] is None
        assert variance["bac_current"] == "10000.00"
        assert variance["bac_variance"] is None

    def test_dict_iso_format_dates(self):
        """Test that dates are properly ISO formatted."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime(2026, 1, 15, 14, 30, 45),
            project_finish_baseline=date(2026, 6, 30),
            project_finish_current=date(2026, 7, 15),
            activity_variances=[
                ActivityVariance(
                    activity_id=str(uuid4()),
                    activity_code="ACT-001",
                    activity_name="Test",
                    change_type="modified",
                    start_baseline=date(2026, 1, 1),
                    start_current=date(2026, 1, 10),
                    finish_baseline=date(2026, 2, 1),
                    finish_current=date(2026, 2, 15),
                ),
            ],
        )

        data = comparison_result_to_dict(result)

        assert data["comparison_date"] == "2026-01-15T14:30:45"
        assert data["project_finish_baseline"] == "2026-06-30"
        assert data["project_finish_current"] == "2026-07-15"

        variance = data["activity_variances"][0]
        assert variance["start_baseline"] == "2026-01-01"
        assert variance["start_current"] == "2026-01-10"
