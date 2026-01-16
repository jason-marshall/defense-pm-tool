"""Additional unit tests for API endpoint coverage."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from src.models.activity import Activity
from src.models.baseline import Baseline
from src.models.dependency import Dependency, DependencyType
from src.models.scenario import ChangeType, EntityType, Scenario, ScenarioChange, ScenarioStatus
from src.models.simulation import SimulationConfig, SimulationResult, SimulationStatus
from src.models.wbs import WBSElement


class TestModelReprMethods:
    """Tests for model __repr__ methods."""

    def test_activity_repr(self):
        """Test Activity string representation."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test Activity",
            duration=10,
        )
        repr_str = repr(activity)
        assert "Activity" in repr_str
        assert "ACT-001" in repr_str

    def test_dependency_repr(self):
        """Test Dependency string representation."""
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=0,
        )
        repr_str = repr(dep)
        assert "Dependency" in repr_str

    def test_wbs_element_repr(self):
        """Test WBSElement string representation."""
        wbs = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1.1",
            name="Work Package",
            path="1.1",
        )
        repr_str = repr(wbs)
        assert "WBSElement" in repr_str

    def test_simulation_config_repr(self):
        """Test SimulationConfig string representation."""
        config = SimulationConfig(
            id=uuid4(),
            program_id=uuid4(),
            name="Monte Carlo Sim",
            iterations=1000,
            activity_distributions={},
            created_by_id=uuid4(),
        )
        repr_str = repr(config)
        assert "SimulationConfig" in repr_str
        assert "Monte Carlo Sim" in repr_str

    def test_simulation_result_repr(self):
        """Test SimulationResult string representation."""
        result = SimulationResult(
            id=uuid4(),
            config_id=uuid4(),
            status=SimulationStatus.COMPLETED,
        )
        repr_str = repr(result)
        assert "SimulationResult" in repr_str


class TestModelProperties:
    """Tests for model computed properties."""

    def test_dependency_type_values(self):
        """Test DependencyType enum values."""
        assert DependencyType.FS == "FS"
        assert DependencyType.SS == "SS"
        assert DependencyType.FF == "FF"
        assert DependencyType.SF == "SF"

    def test_simulation_status_values(self):
        """Test SimulationStatus enum values."""
        assert SimulationStatus.PENDING == "pending"
        assert SimulationStatus.RUNNING == "running"
        assert SimulationStatus.COMPLETED == "completed"
        assert SimulationStatus.FAILED == "failed"


class TestActivityScheduleProperties:
    """Tests for Activity schedule-related properties."""

    def test_activity_float_calculations(self):
        """Test total float and free float."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=10,
            early_start=date(2026, 1, 1),
            early_finish=date(2026, 1, 15),
            late_start=date(2026, 1, 5),
            late_finish=date(2026, 1, 20),
            total_float=4,
            free_float=2,
        )

        assert activity.total_float == 4
        assert activity.free_float == 2

    def test_activity_is_critical(self):
        """Test is_critical property."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Critical Task",
            duration=10,
            total_float=0,
            is_critical=True,
        )

        assert activity.is_critical is True


class TestBaselineProperties:
    """Tests for Baseline model properties."""

    def test_baseline_is_pmb(self):
        """Test is_pmb property."""
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="PMB Baseline",
            version=1,
            is_approved=True,
            total_bac=Decimal("100000.00"),
            activity_count=50,
            wbs_count=10,
            created_by_id=uuid4(),
        )

        assert baseline.is_pmb is True

        baseline.is_approved = False
        assert baseline.is_pmb is False

    def test_baseline_has_data_properties(self):
        """Test has_schedule/cost/wbs_data properties."""
        baseline = Baseline(
            id=uuid4(),
            program_id=uuid4(),
            name="Full Baseline",
            version=1,
            is_approved=False,
            total_bac=Decimal("0.00"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
            schedule_snapshot={"activities": []},
            cost_snapshot={"total_bac": "0.00"},
            wbs_snapshot={"wbs_elements": []},
        )

        assert baseline.has_schedule_data is True
        assert baseline.has_cost_data is True
        assert baseline.has_wbs_data is True


class TestScenarioProperties:
    """Tests for Scenario model properties."""

    def test_scenario_is_draft(self):
        """Test is_draft property."""
        scenario = Scenario(
            id=uuid4(),
            program_id=uuid4(),
            name="Draft Scenario",
            status=ScenarioStatus.DRAFT,
            created_by_id=uuid4(),
        )

        assert scenario.is_draft is True

        scenario.status = ScenarioStatus.ACTIVE
        assert scenario.is_draft is False

    def test_scenario_is_promoted(self):
        """Test is_promoted property."""
        scenario = Scenario(
            id=uuid4(),
            program_id=uuid4(),
            name="Promoted Scenario",
            status=ScenarioStatus.PROMOTED,
            created_by_id=uuid4(),
        )

        assert scenario.is_promoted is True

    def test_scenario_has_cached_results(self):
        """Test has_cached_results property."""
        scenario = Scenario(
            id=uuid4(),
            program_id=uuid4(),
            name="Cached Scenario",
            status=ScenarioStatus.DRAFT,
            created_by_id=uuid4(),
            results_cache=None,
        )

        assert scenario.has_cached_results is False

        scenario.results_cache = {"duration": 100}
        assert scenario.has_cached_results is True


class TestScenarioChangeProperties:
    """Tests for ScenarioChange model properties."""

    def test_change_is_create(self):
        """Test is_create property."""
        change = ScenarioChange(
            id=uuid4(),
            scenario_id=uuid4(),
            entity_type=EntityType.ACTIVITY,
            entity_id=uuid4(),
            change_type=ChangeType.CREATE,
        )

        assert change.is_create is True
        assert change.is_update is False
        assert change.is_delete is False

    def test_change_is_update(self):
        """Test is_update property."""
        change = ScenarioChange(
            id=uuid4(),
            scenario_id=uuid4(),
            entity_type=EntityType.DEPENDENCY,
            entity_id=uuid4(),
            change_type=ChangeType.UPDATE,
        )

        assert change.is_create is False
        assert change.is_update is True
        assert change.is_delete is False

    def test_change_is_delete(self):
        """Test is_delete property."""
        change = ScenarioChange(
            id=uuid4(),
            scenario_id=uuid4(),
            entity_type=EntityType.WBS,
            entity_id=uuid4(),
            change_type=ChangeType.DELETE,
        )

        assert change.is_create is False
        assert change.is_update is False
        assert change.is_delete is True


class TestSimulationProperties:
    """Tests for Simulation model properties."""

    def test_simulation_config_activity_count(self):
        """Test activity_count property."""
        config = SimulationConfig(
            id=uuid4(),
            program_id=uuid4(),
            name="Simulation",
            iterations=1000,
            activity_distributions={
                str(uuid4()): {"distribution": "triangular"},
                str(uuid4()): {"distribution": "normal"},
            },
            created_by_id=uuid4(),
        )

        assert config.activity_count == 2

    def test_simulation_result_is_completed(self):
        """Test status check properties."""
        result = SimulationResult(
            id=uuid4(),
            config_id=uuid4(),
            status=SimulationStatus.COMPLETED,
        )

        assert result.status == SimulationStatus.COMPLETED

        result.status = SimulationStatus.FAILED
        assert result.status == SimulationStatus.FAILED
