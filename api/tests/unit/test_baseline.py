"""Unit tests for Baseline model and repository."""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from src.models.baseline import Baseline


class TestBaselineModel:
    """Tests for Baseline model."""

    def test_baseline_creation(self):
        """Test creating a Baseline instance."""
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="Baseline 1",
            version=1,
            description="Test baseline",
            is_approved=False,
            total_bac=Decimal("100000.00"),
            activity_count=10,
            wbs_count=5,
            created_by_id=uuid4(),
        )

        assert baseline.name == "Baseline 1"
        assert baseline.version == 1
        assert baseline.is_approved is False
        assert baseline.total_bac == Decimal("100000.00")
        assert baseline.activity_count == 10

    def test_baseline_is_pmb_property(self):
        """Test is_pmb property returns is_approved value."""
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="PMB",
            version=1,
            is_approved=True,
            total_bac=Decimal("0.00"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
        )

        assert baseline.is_pmb is True

        baseline.is_approved = False
        assert baseline.is_pmb is False

    def test_baseline_has_schedule_data(self):
        """Test has_schedule_data property."""
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="Test",
            version=1,
            schedule_snapshot={"activities": []},
            is_approved=False,
            total_bac=Decimal("0.00"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
        )

        assert baseline.has_schedule_data is True

        baseline.schedule_snapshot = None
        assert baseline.has_schedule_data is False

    def test_baseline_has_cost_data(self):
        """Test has_cost_data property."""
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="Test",
            version=1,
            cost_snapshot={"total_bac": "100000.00"},
            is_approved=False,
            total_bac=Decimal("0.00"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
        )

        assert baseline.has_cost_data is True

        baseline.cost_snapshot = None
        assert baseline.has_cost_data is False

    def test_baseline_has_wbs_data(self):
        """Test has_wbs_data property."""
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="Test",
            version=1,
            wbs_snapshot={"wbs_elements": []},
            is_approved=False,
            total_bac=Decimal("0.00"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
        )

        assert baseline.has_wbs_data is True

        baseline.wbs_snapshot = None
        assert baseline.has_wbs_data is False

    def test_baseline_repr(self):
        """Test string representation."""
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="Q1 Baseline",
            version=3,
            is_approved=True,
            total_bac=Decimal("0.00"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
        )

        repr_str = repr(baseline)
        assert "Q1 Baseline" in repr_str
        assert "version=3" in repr_str
        assert "is_approved=True" in repr_str

    def test_baseline_defaults(self):
        """Test default values for optional fields."""
        baseline = Baseline(
            program_id=uuid4(),
            name="Test",
            version=1,  # Required for model
            is_approved=False,  # Required
            total_bac=Decimal("0.00"),  # Required
            activity_count=0,  # Required
            wbs_count=0,  # Required
            created_by_id=uuid4(),
        )

        # Optional fields should be None by default
        assert baseline.description is None
        assert baseline.schedule_snapshot is None
        assert baseline.cost_snapshot is None
        assert baseline.wbs_snapshot is None
        assert baseline.approved_at is None
        assert baseline.approved_by_id is None
        assert baseline.scheduled_finish is None


class TestBaselineSchemas:
    """Tests for Baseline Pydantic schemas."""

    def test_baseline_create_validation(self):
        """Test BaselineCreate schema validation."""
        from src.schemas.baseline import BaselineCreate

        data = BaselineCreate(
            program_id=uuid4(),
            name="Test Baseline",
            description="Test description",
            include_schedule=True,
            include_cost=True,
            include_wbs=True,
        )

        assert data.name == "Test Baseline"
        assert data.include_schedule is True

    def test_baseline_create_defaults(self):
        """Test BaselineCreate schema defaults."""
        from src.schemas.baseline import BaselineCreate

        data = BaselineCreate(
            program_id=uuid4(),
            name="Test",
        )

        assert data.include_schedule is True
        assert data.include_cost is True
        assert data.include_wbs is True

    def test_baseline_update_optional_fields(self):
        """Test BaselineUpdate schema allows partial updates."""
        from src.schemas.baseline import BaselineUpdate

        # Only name
        data1 = BaselineUpdate(name="New Name")
        assert data1.name == "New Name"
        assert data1.description is None

        # Only description
        data2 = BaselineUpdate(description="New Description")
        assert data2.name is None
        assert data2.description == "New Description"

    def test_baseline_summary_from_model(self):
        """Test BaselineSummary can be created from model."""
        from src.schemas.baseline import BaselineSummary

        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="Test",
            version=1,
            description="Desc",
            is_approved=True,
            approved_at=datetime.now(),
            total_bac=Decimal("50000.00"),
            scheduled_finish=date(2026, 12, 31),
            activity_count=20,
            wbs_count=8,
            created_by_id=uuid4(),
        )
        baseline.created_at = datetime.now()

        summary = BaselineSummary.model_validate(baseline)
        assert summary.name == "Test"
        assert summary.version == 1
        assert summary.is_approved is True
        assert summary.total_bac == Decimal("50000.00")

    def test_baseline_comparison_schema(self):
        """Test BaselineComparison schema."""
        from src.schemas.baseline import BaselineComparison

        comparison = BaselineComparison(
            baseline_id=uuid4(),
            baseline_name="Q1 2026",
            baseline_version=1,
            comparison_date=datetime.now(),
            activities_added=["ACT-001", "ACT-002"],
            activities_removed=["ACT-OLD"],
            bac_variance=Decimal("10000.00"),
            schedule_days_variance=5,
        )

        assert len(comparison.activities_added) == 2
        assert comparison.bac_variance == Decimal("10000.00")
        assert comparison.schedule_days_variance == 5


class TestScheduleSnapshot:
    """Tests for schedule snapshot schemas."""

    def test_activity_snapshot_schema(self):
        """Test ActivitySnapshot schema."""
        from src.schemas.baseline import ActivitySnapshot

        snapshot = ActivitySnapshot(
            id=uuid4(),
            code="ACT-001",
            name="Activity 1",
            duration=10,
            planned_start=date(2026, 1, 1),
            planned_finish=date(2026, 1, 15),
            early_start=date(2026, 1, 1),
            early_finish=date(2026, 1, 15),
            late_start=date(2026, 1, 5),
            late_finish=date(2026, 1, 20),
            total_float=5,
            is_critical=False,
            budgeted_cost=Decimal("10000.00"),
            percent_complete=Decimal("50.00"),
            ev_method="percent_complete",
        )

        assert snapshot.code == "ACT-001"
        assert snapshot.duration == 10
        assert snapshot.is_critical is False

    def test_dependency_snapshot_schema(self):
        """Test DependencySnapshot schema."""
        from src.schemas.baseline import DependencySnapshot

        snapshot = DependencySnapshot(
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type="FS",
            lag=0,
        )

        assert snapshot.dependency_type == "FS"
        assert snapshot.lag == 0

    def test_schedule_snapshot_schema(self):
        """Test ScheduleSnapshot schema."""
        from src.schemas.baseline import ScheduleSnapshot

        snapshot = ScheduleSnapshot(
            activities=[],
            dependencies=[],
            critical_path_ids=[uuid4()],
            project_duration=60,
            project_finish=date(2026, 3, 1),
        )

        assert snapshot.project_duration == 60
        assert len(snapshot.critical_path_ids) == 1


class TestCostSnapshot:
    """Tests for cost snapshot schemas."""

    def test_wbs_snapshot_schema(self):
        """Test WBSSnapshot schema."""
        from src.schemas.baseline import WBSSnapshot

        snapshot = WBSSnapshot(
            id=uuid4(),
            wbs_code="1.1",
            name="Work Package 1",
            parent_id=uuid4(),
            path="1.1",
            budgeted_cost=Decimal("25000.00"),
        )

        assert snapshot.wbs_code == "1.1"
        assert snapshot.budgeted_cost == Decimal("25000.00")

    def test_cost_snapshot_schema(self):
        """Test CostSnapshot schema."""
        from src.schemas.baseline import CostSnapshot

        snapshot = CostSnapshot(
            wbs_elements=[],
            total_bac=Decimal("100000.00"),
            time_phased_bcws={"2026-01": Decimal("10000.00")},
        )

        assert snapshot.total_bac == Decimal("100000.00")
        assert "2026-01" in snapshot.time_phased_bcws
