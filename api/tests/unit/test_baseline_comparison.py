"""Unit tests for Baseline Comparison Service."""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from src.services.baseline_comparison import (
    ActivityVariance,
    ComparisonResult,
    WBSVariance,
    comparison_result_to_dict,
)


class TestActivityVariance:
    """Tests for ActivityVariance dataclass."""

    def test_activity_variance_creation(self):
        """Test creating an ActivityVariance."""
        variance = ActivityVariance(
            activity_id=str(uuid4()),
            activity_code="ACT-001",
            activity_name="Test Activity",
            change_type="modified",
            duration_baseline=10,
            duration_current=12,
            duration_variance=2,
            bac_baseline=Decimal("10000.00"),
            bac_current=Decimal("12000.00"),
            bac_variance=Decimal("2000.00"),
        )

        assert variance.activity_code == "ACT-001"
        assert variance.change_type == "modified"
        assert variance.duration_variance == 2
        assert variance.bac_variance == Decimal("2000.00")

    def test_activity_variance_added(self):
        """Test variance for added activity."""
        variance = ActivityVariance(
            activity_id=str(uuid4()),
            activity_code="ACT-NEW",
            activity_name="New Activity",
            change_type="added",
            duration_current=5,
            bac_current=Decimal("5000.00"),
            is_critical=False,
        )

        assert variance.change_type == "added"
        assert variance.duration_baseline is None
        assert variance.duration_current == 5
        assert variance.bac_baseline is None

    def test_activity_variance_removed(self):
        """Test variance for removed activity."""
        variance = ActivityVariance(
            activity_id=str(uuid4()),
            activity_code="ACT-OLD",
            activity_name="Removed Activity",
            change_type="removed",
            duration_baseline=8,
            bac_baseline=Decimal("8000.00"),
            was_critical=True,
        )

        assert variance.change_type == "removed"
        assert variance.duration_baseline == 8
        assert variance.duration_current is None
        assert variance.was_critical is True


class TestWBSVariance:
    """Tests for WBSVariance dataclass."""

    def test_wbs_variance_modified(self):
        """Test WBS variance for modified element."""
        variance = WBSVariance(
            wbs_id=str(uuid4()),
            wbs_code="1.1",
            wbs_name="Work Package 1",
            change_type="modified",
            bac_baseline=Decimal("50000.00"),
            bac_current=Decimal("55000.00"),
            bac_variance=Decimal("5000.00"),
        )

        assert variance.wbs_code == "1.1"
        assert variance.change_type == "modified"
        assert variance.bac_variance == Decimal("5000.00")

    def test_wbs_variance_added(self):
        """Test WBS variance for added element."""
        variance = WBSVariance(
            wbs_id=str(uuid4()),
            wbs_code="1.2",
            wbs_name="New Work Package",
            change_type="added",
            bac_current=Decimal("20000.00"),
        )

        assert variance.change_type == "added"
        assert variance.bac_baseline is None
        assert variance.bac_current == Decimal("20000.00")


class TestComparisonResult:
    """Tests for ComparisonResult dataclass."""

    def test_comparison_result_creation(self):
        """Test creating a ComparisonResult."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Q1 2026 Baseline",
            baseline_version=1,
            comparison_date=datetime.now(),
        )

        assert result.baseline_name == "Q1 2026 Baseline"
        assert result.baseline_version == 1
        assert result.bac_variance == Decimal("0.00")
        assert result.schedule_variance_days == 0
        assert len(result.activity_variances) == 0

    def test_comparison_result_with_variances(self):
        """Test ComparisonResult with variance data."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test Baseline",
            baseline_version=2,
            comparison_date=datetime.now(),
            total_bac_baseline=Decimal("100000.00"),
            total_bac_current=Decimal("110000.00"),
            bac_variance=Decimal("10000.00"),
            bac_variance_percent=Decimal("10.00"),
            project_finish_baseline=date(2026, 6, 30),
            project_finish_current=date(2026, 7, 15),
            schedule_variance_days=15,
            activities_baseline=20,
            activities_current=22,
            activities_added=3,
            activities_removed=1,
            activities_modified=5,
            activities_unchanged=14,
        )

        assert result.total_bac_baseline == Decimal("100000.00")
        assert result.bac_variance == Decimal("10000.00")
        assert result.schedule_variance_days == 15
        assert result.activities_added == 3
        assert result.activities_removed == 1

    def test_comparison_result_critical_path_changed(self):
        """Test critical path change detection."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            critical_path_baseline=["ACT-001", "ACT-002", "ACT-003"],
            critical_path_current=["ACT-001", "ACT-004", "ACT-003"],
            critical_path_changed=True,
        )

        assert result.critical_path_changed is True
        assert "ACT-002" in result.critical_path_baseline
        assert "ACT-004" in result.critical_path_current


class TestComparisonResultToDict:
    """Tests for comparison_result_to_dict function."""

    def test_basic_conversion(self):
        """Test basic result to dict conversion."""
        baseline_id = uuid4()
        result = ComparisonResult(
            baseline_id=baseline_id,
            baseline_name="Test Baseline",
            baseline_version=1,
            comparison_date=datetime(2026, 1, 15, 10, 30, 0),
            total_bac_baseline=Decimal("100000.00"),
            total_bac_current=Decimal("105000.00"),
            bac_variance=Decimal("5000.00"),
            bac_variance_percent=Decimal("5.00"),
            schedule_variance_days=10,
        )

        data = comparison_result_to_dict(result)

        assert data["baseline_id"] == str(baseline_id)
        assert data["baseline_name"] == "Test Baseline"
        assert data["baseline_version"] == 1
        assert data["total_bac_baseline"] == "100000.00"
        assert data["bac_variance"] == "5000.00"
        assert data["schedule_variance_days"] == 10

    def test_conversion_with_dates(self):
        """Test conversion with date fields."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            project_finish_baseline=date(2026, 6, 30),
            project_finish_current=date(2026, 7, 15),
        )

        data = comparison_result_to_dict(result)

        assert data["project_finish_baseline"] == "2026-06-30"
        assert data["project_finish_current"] == "2026-07-15"

    def test_conversion_with_null_dates(self):
        """Test conversion when dates are None."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
        )

        data = comparison_result_to_dict(result)

        assert data["project_finish_baseline"] is None
        assert data["project_finish_current"] is None

    def test_conversion_with_activity_variances(self):
        """Test conversion includes activity variance details."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            activity_variances=[
                ActivityVariance(
                    activity_id=str(uuid4()),
                    activity_code="ACT-001",
                    activity_name="Activity 1",
                    change_type="modified",
                    duration_baseline=10,
                    duration_current=12,
                    duration_variance=2,
                    start_baseline=date(2026, 1, 1),
                    start_current=date(2026, 1, 5),
                    start_variance_days=4,
                    bac_baseline=Decimal("10000.00"),
                    bac_current=Decimal("11000.00"),
                    bac_variance=Decimal("1000.00"),
                ),
            ],
        )

        data = comparison_result_to_dict(result)

        assert len(data["activity_variances"]) == 1
        variance = data["activity_variances"][0]
        assert variance["activity_code"] == "ACT-001"
        assert variance["change_type"] == "modified"
        assert variance["duration_variance"] == 2
        assert variance["start_variance_days"] == 4
        assert variance["bac_variance"] == "1000.00"

    def test_conversion_with_wbs_variances(self):
        """Test conversion includes WBS variance details."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            wbs_variances=[
                WBSVariance(
                    wbs_id=str(uuid4()),
                    wbs_code="1.1",
                    wbs_name="Work Package 1",
                    change_type="modified",
                    bac_baseline=Decimal("50000.00"),
                    bac_current=Decimal("55000.00"),
                    bac_variance=Decimal("5000.00"),
                ),
            ],
        )

        data = comparison_result_to_dict(result)

        assert len(data["wbs_variances"]) == 1
        variance = data["wbs_variances"][0]
        assert variance["wbs_code"] == "1.1"
        assert variance["change_type"] == "modified"
        assert variance["bac_variance"] == "5000.00"

    def test_conversion_with_code_lists(self):
        """Test conversion includes activity code lists."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            added_activity_codes=["ACT-NEW-1", "ACT-NEW-2"],
            removed_activity_codes=["ACT-OLD"],
            modified_activity_codes=["ACT-001", "ACT-002"],
        )

        data = comparison_result_to_dict(result)

        assert data["added_activity_codes"] == ["ACT-NEW-1", "ACT-NEW-2"]
        assert data["removed_activity_codes"] == ["ACT-OLD"]
        assert data["modified_activity_codes"] == ["ACT-001", "ACT-002"]

    def test_conversion_with_critical_path(self):
        """Test conversion includes critical path data."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            critical_path_baseline=["ACT-001", "ACT-002"],
            critical_path_current=["ACT-001", "ACT-003"],
            critical_path_changed=True,
        )

        data = comparison_result_to_dict(result)

        assert data["critical_path_baseline"] == ["ACT-001", "ACT-002"]
        assert data["critical_path_current"] == ["ACT-001", "ACT-003"]
        assert data["critical_path_changed"] is True


class TestComparisonResultSummary:
    """Tests for comparison result summary calculations."""

    def test_positive_bac_variance(self):
        """Test positive BAC variance (cost overrun)."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            total_bac_baseline=Decimal("100000.00"),
            total_bac_current=Decimal("120000.00"),
            bac_variance=Decimal("20000.00"),
            bac_variance_percent=Decimal("20.00"),
        )

        assert result.bac_variance == Decimal("20000.00")
        assert result.bac_variance_percent == Decimal("20.00")

    def test_negative_bac_variance(self):
        """Test negative BAC variance (under budget)."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            total_bac_baseline=Decimal("100000.00"),
            total_bac_current=Decimal("90000.00"),
            bac_variance=Decimal("-10000.00"),
            bac_variance_percent=Decimal("-10.00"),
        )

        assert result.bac_variance == Decimal("-10000.00")
        assert result.bac_variance_percent == Decimal("-10.00")

    def test_schedule_slip(self):
        """Test positive schedule variance (slip)."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            project_finish_baseline=date(2026, 6, 30),
            project_finish_current=date(2026, 7, 31),
            schedule_variance_days=31,
        )

        assert result.schedule_variance_days == 31  # 31 days late

    def test_schedule_ahead(self):
        """Test negative schedule variance (ahead of schedule)."""
        result = ComparisonResult(
            baseline_id=uuid4(),
            baseline_name="Test",
            baseline_version=1,
            comparison_date=datetime.now(),
            project_finish_baseline=date(2026, 6, 30),
            project_finish_current=date(2026, 6, 15),
            schedule_variance_days=-15,
        )

        assert result.schedule_variance_days == -15  # 15 days early
