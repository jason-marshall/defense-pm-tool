"""Unit tests for Scenario Simulation service."""

from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np

from src.services.monte_carlo import DistributionParams, DistributionType
from src.services.monte_carlo_cpm import NetworkSimulationOutput
from src.services.scenario_simulation import (
    ModifiedActivity,
    ScenarioComparisonResult,
    ScenarioSimulationService,
    build_scenario_distributions,
    compare_scenario_simulations,
)


class TestModifiedActivity:
    """Tests for ModifiedActivity dataclass."""

    def test_create_modified_activity(self):
        """Should create modified activity with all fields."""
        activity = ModifiedActivity(
            id=uuid4(),
            duration=10,
            budgeted_cost=Decimal("50000"),
            name="Test Activity",
            code="TA-001",
        )

        assert activity.duration == 10
        assert activity.budgeted_cost == Decimal("50000")
        assert activity.name == "Test Activity"
        assert activity.code == "TA-001"

    def test_create_modified_activity_without_code(self):
        """Should create modified activity without code."""
        activity = ModifiedActivity(
            id=uuid4(),
            duration=5,
            budgeted_cost=Decimal("10000"),
            name="Task",
        )

        assert activity.code is None


class TestScenarioComparisonResult:
    """Tests for ScenarioComparisonResult dataclass."""

    def test_create_comparison_result(self):
        """Should create comparison result with all fields."""
        result = ScenarioComparisonResult(
            p50_delta=-5.0,
            p90_delta=-7.0,
            mean_delta=-5.5,
            std_delta=-2.0,
            risk_improved=True,
            criticality_changes={uuid4(): 5.0, uuid4(): -3.0},
            summary="Scenario reduces duration by 5.5 days and reduces risk",
        )

        assert result.p50_delta == -5.0
        assert result.p90_delta == -7.0
        assert result.risk_improved is True


class MockActivity:
    """Mock Activity for testing."""

    def __init__(
        self,
        id=None,
        duration: int = 10,
        budgeted_cost: Decimal = Decimal("10000"),
        name: str = "Test",
        code: str = "T-001",
    ):
        self.id = id or uuid4()
        self.duration = duration
        self.budgeted_cost = budgeted_cost
        self.name = name
        self.code = code


class MockDependency:
    """Mock Dependency for testing."""

    def __init__(self, predecessor_id, successor_id, dependency_type="FS", lag=0):
        self.predecessor_id = predecessor_id
        self.successor_id = successor_id
        self.dependency_type = dependency_type
        self.lag = lag


class MockScenario:
    """Mock Scenario for testing."""

    def __init__(self, name="Test Scenario"):
        self.id = uuid4()
        self.name = name
        self.program_id = uuid4()


class MockScenarioChange:
    """Mock ScenarioChange for testing."""

    def __init__(
        self,
        entity_type: str = "activity",
        entity_id=None,
        change_type: str = "update",
        field_name: str | None = None,
        old_value=None,
        new_value=None,
    ):
        self.id = uuid4()
        self.entity_type = entity_type
        self.entity_id = entity_id or uuid4()
        self.change_type = change_type
        self.field_name = field_name
        self.old_value = old_value
        self.new_value = new_value


class TestScenarioSimulationService:
    """Tests for ScenarioSimulationService."""

    def test_init(self):
        """Should initialize service with all components."""
        activities = [MockActivity()]
        dependencies = []
        scenario = MockScenario()
        changes = []

        service = ScenarioSimulationService(
            activities=activities,
            dependencies=dependencies,
            scenario=scenario,
            changes=changes,
        )

        assert service.base_activities == activities
        assert service.dependencies == dependencies
        assert service.scenario == scenario
        assert service.changes == changes

    def test_apply_changes_no_changes(self):
        """Should return unchanged activities when no changes."""
        activity = MockActivity(duration=10, budgeted_cost=Decimal("10000"))
        activities = [activity]

        service = ScenarioSimulationService(
            activities=activities,
            dependencies=[],
            scenario=MockScenario(),
            changes=[],
        )

        modified = service.apply_changes()

        assert len(modified) == 1
        assert modified[0].duration == 10
        assert modified[0].budgeted_cost == Decimal("10000")

    def test_apply_changes_duration_update(self):
        """Should apply duration change to activity."""
        activity = MockActivity(duration=10)

        change = MockScenarioChange(
            entity_type="activity",
            entity_id=activity.id,
            change_type="update",
            field_name="duration",
            new_value=15,
        )

        service = ScenarioSimulationService(
            activities=[activity],
            dependencies=[],
            scenario=MockScenario(),
            changes=[change],
        )

        modified = service.apply_changes()

        assert len(modified) == 1
        assert modified[0].duration == 15

    def test_apply_changes_budgeted_cost_update(self):
        """Should apply budgeted cost change to activity."""
        activity = MockActivity(budgeted_cost=Decimal("10000"))

        change = MockScenarioChange(
            entity_type="activity",
            entity_id=activity.id,
            change_type="update",
            field_name="budgeted_cost",
            new_value="15000",
        )

        service = ScenarioSimulationService(
            activities=[activity],
            dependencies=[],
            scenario=MockScenario(),
            changes=[change],
        )

        modified = service.apply_changes()

        assert len(modified) == 1
        assert modified[0].budgeted_cost == Decimal("15000")

    def test_apply_changes_name_update(self):
        """Should apply name change to activity."""
        activity = MockActivity(name="Old Name")

        change = MockScenarioChange(
            entity_type="activity",
            entity_id=activity.id,
            change_type="update",
            field_name="name",
            new_value="New Name",
        )

        service = ScenarioSimulationService(
            activities=[activity],
            dependencies=[],
            scenario=MockScenario(),
            changes=[change],
        )

        modified = service.apply_changes()

        assert len(modified) == 1
        assert modified[0].name == "New Name"

    def test_apply_changes_delete(self):
        """Should set duration to 0 for deleted activity."""
        activity = MockActivity(duration=10)

        change = MockScenarioChange(
            entity_type="activity",
            entity_id=activity.id,
            change_type="delete",
        )

        service = ScenarioSimulationService(
            activities=[activity],
            dependencies=[],
            scenario=MockScenario(),
            changes=[change],
        )

        modified = service.apply_changes()

        assert len(modified) == 1
        assert modified[0].duration == 0

    def test_apply_changes_json_wrapped_value(self):
        """Should handle JSON-wrapped values in changes."""
        activity = MockActivity(duration=10)

        change = MockScenarioChange(
            entity_type="activity",
            entity_id=activity.id,
            change_type="update",
            field_name="duration",
            new_value={"value": 20},
        )

        service = ScenarioSimulationService(
            activities=[activity],
            dependencies=[],
            scenario=MockScenario(),
            changes=[change],
        )

        modified = service.apply_changes()

        assert modified[0].duration == 20

    def test_apply_changes_ignores_non_activity_changes(self):
        """Should ignore non-activity changes."""
        activity = MockActivity(duration=10)

        change = MockScenarioChange(
            entity_type="dependency",  # Not activity
            entity_id=activity.id,
            change_type="update",
            field_name="duration",
            new_value=20,
        )

        service = ScenarioSimulationService(
            activities=[activity],
            dependencies=[],
            scenario=MockScenario(),
            changes=[change],
        )

        modified = service.apply_changes()

        # Duration unchanged because change is for dependency
        assert modified[0].duration == 10

    def test_apply_changes_multiple_activities(self):
        """Should apply changes to multiple activities."""
        activity1 = MockActivity(duration=10, name="Activity 1")
        activity2 = MockActivity(duration=20, name="Activity 2")

        change1 = MockScenarioChange(
            entity_type="activity",
            entity_id=activity1.id,
            change_type="update",
            field_name="duration",
            new_value=15,
        )

        change2 = MockScenarioChange(
            entity_type="activity",
            entity_id=activity2.id,
            change_type="update",
            field_name="duration",
            new_value=25,
        )

        service = ScenarioSimulationService(
            activities=[activity1, activity2],
            dependencies=[],
            scenario=MockScenario(),
            changes=[change1, change2],
        )

        modified = service.apply_changes()

        assert len(modified) == 2
        # Find the modified activities by ID
        mod1 = next(m for m in modified if m.id == activity1.id)
        mod2 = next(m for m in modified if m.id == activity2.id)
        assert mod1.duration == 15
        assert mod2.duration == 25

    def test_build_change_map_caching(self):
        """Should cache the change map."""
        activity = MockActivity()
        change = MockScenarioChange(entity_type="activity", entity_id=activity.id)

        service = ScenarioSimulationService(
            activities=[activity],
            dependencies=[],
            scenario=MockScenario(),
            changes=[change],
        )

        # First call builds map
        map1 = service._build_change_map()
        # Second call returns cached map
        map2 = service._build_change_map()

        assert map1 is map2

    def test_build_default_distributions(self):
        """Should build default triangular distributions."""
        activity1 = ModifiedActivity(
            id=uuid4(), duration=10, budgeted_cost=Decimal("10000"), name="A"
        )
        activity2 = ModifiedActivity(
            id=uuid4(), duration=20, budgeted_cost=Decimal("20000"), name="B"
        )

        service = ScenarioSimulationService(
            activities=[],
            dependencies=[],
            scenario=MockScenario(),
            changes=[],
        )

        distributions = service._build_default_distributions([activity1, activity2])

        assert activity1.id in distributions
        assert activity2.id in distributions

        dist1 = distributions[activity1.id]
        assert dist1.distribution == DistributionType.TRIANGULAR
        assert dist1.min_value == 8.0  # 10 * 0.8
        assert dist1.mode == 10.0
        assert dist1.max_value == 12.0  # 10 * 1.2

    def test_build_default_distributions_skips_zero_duration(self):
        """Should skip activities with zero duration."""
        activity = ModifiedActivity(
            id=uuid4(), duration=0, budgeted_cost=Decimal("10000"), name="A"
        )

        service = ScenarioSimulationService(
            activities=[],
            dependencies=[],
            scenario=MockScenario(),
            changes=[],
        )

        distributions = service._build_default_distributions([activity])

        assert activity.id not in distributions

    def test_update_distributions_for_changes(self):
        """Should update distributions for changed activities."""
        activity_id = uuid4()
        activity = ModifiedActivity(
            id=activity_id, duration=15, budgeted_cost=Decimal("10000"), name="A"
        )

        change = MockScenarioChange(
            entity_type="activity",
            entity_id=activity_id,
            change_type="update",
            field_name="duration",
            new_value=15,
        )

        service = ScenarioSimulationService(
            activities=[],
            dependencies=[],
            scenario=MockScenario(),
            changes=[change],
        )

        # Initial distribution with old duration
        initial_dist = {
            activity_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=8.0,
                mode=10.0,
                max_value=12.0,
            )
        }

        updated = service._update_distributions_for_changes(initial_dist, [activity])

        # Should be updated to reflect new duration of 15
        assert updated[activity_id].mode == 15.0
        assert updated[activity_id].min_value == 12.0  # 15 * 0.8
        assert updated[activity_id].max_value == 18.0  # 15 * 1.2

    @patch("src.services.scenario_simulation.NetworkMonteCarloEngine")
    def test_simulate_calls_engine(self, mock_engine_class):
        """Should call Monte Carlo engine with modified activities."""
        # Setup mock
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_output = MagicMock(spec=NetworkSimulationOutput)
        mock_output.project_duration_samples = np.array([100.0])
        mock_engine.simulate.return_value = mock_output

        activity = MockActivity(duration=10)

        service = ScenarioSimulationService(
            activities=[activity],
            dependencies=[],
            scenario=MockScenario(),
            changes=[],
        )

        result = service.simulate(iterations=100, seed=42)

        assert result is mock_output
        mock_engine_class.assert_called_once_with(seed=42)
        mock_engine.simulate.assert_called_once()

    @patch("src.services.scenario_simulation.NetworkMonteCarloEngine")
    def test_simulate_with_custom_distributions(self, mock_engine_class):
        """Should use custom distributions when provided."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_output = MagicMock(spec=NetworkSimulationOutput)
        mock_engine.simulate.return_value = mock_output

        activity = MockActivity(duration=10)

        custom_dist = {
            activity.id: DistributionParams(
                distribution=DistributionType.PERT,
                min_value=5.0,
                mode=10.0,
                max_value=20.0,
            )
        }

        service = ScenarioSimulationService(
            activities=[activity],
            dependencies=[],
            scenario=MockScenario(),
            changes=[],
        )

        service.simulate(distributions=custom_dist, iterations=100)

        # Verify the engine was called
        mock_engine.simulate.assert_called_once()
        call_args = mock_engine.simulate.call_args[0][0]
        assert activity.id in call_args.duration_distributions


class TestCompareScenarioSimulations:
    """Tests for compare_scenario_simulations function."""

    def _create_mock_output(
        self,
        p50: float = 100.0,
        p90: float = 120.0,
        mean: float = 105.0,
        std: float = 15.0,
        criticality: dict | None = None,
    ):
        """Create a mock NetworkSimulationOutput."""
        output = MagicMock(spec=NetworkSimulationOutput)
        output.project_duration_p50 = p50
        output.project_duration_p90 = p90
        output.project_duration_mean = mean
        output.project_duration_std = std
        output.activity_criticality = criticality or {}
        return output

    def test_compare_duration_reduction(self):
        """Should detect duration reduction."""
        baseline = self._create_mock_output(p50=100.0, p90=120.0, mean=105.0)
        scenario = self._create_mock_output(p50=90.0, p90=110.0, mean=95.0)

        result = compare_scenario_simulations(baseline, scenario)

        assert result.p50_delta == -10.0
        assert result.p90_delta == -10.0
        assert result.mean_delta == -10.0
        assert "reduces duration" in result.summary

    def test_compare_duration_increase(self):
        """Should detect duration increase."""
        baseline = self._create_mock_output(p50=100.0, mean=105.0)
        scenario = self._create_mock_output(p50=110.0, mean=115.0)

        result = compare_scenario_simulations(baseline, scenario)

        assert result.p50_delta == 10.0
        assert result.mean_delta == 10.0
        assert "increases duration" in result.summary

    def test_compare_no_change(self):
        """Should detect no change."""
        baseline = self._create_mock_output(p50=100.0, mean=100.0)
        scenario = self._create_mock_output(p50=100.0, mean=100.0)

        result = compare_scenario_simulations(baseline, scenario)

        assert result.mean_delta == 0.0
        assert "no change to duration" in result.summary

    def test_compare_risk_improved(self):
        """Should detect risk improvement (lower std)."""
        baseline = self._create_mock_output(std=20.0)
        scenario = self._create_mock_output(std=15.0)

        result = compare_scenario_simulations(baseline, scenario)

        assert result.std_delta == -5.0
        assert result.risk_improved is True
        assert "reduces risk" in result.summary

    def test_compare_risk_increased(self):
        """Should detect risk increase (higher std)."""
        baseline = self._create_mock_output(std=15.0)
        scenario = self._create_mock_output(std=20.0)

        result = compare_scenario_simulations(baseline, scenario)

        assert result.std_delta == 5.0
        assert result.risk_improved is False
        assert "increases risk" in result.summary

    def test_compare_criticality_changes(self):
        """Should calculate criticality changes."""
        act_id_1 = uuid4()
        act_id_2 = uuid4()
        act_id_3 = uuid4()

        baseline = self._create_mock_output(criticality={act_id_1: 50.0, act_id_2: 30.0})
        scenario = self._create_mock_output(
            criticality={act_id_1: 60.0, act_id_3: 20.0}  # act_id_2 removed, act_id_3 new
        )

        result = compare_scenario_simulations(baseline, scenario)

        assert act_id_1 in result.criticality_changes
        assert result.criticality_changes[act_id_1] == 10.0  # 60 - 50
        assert act_id_2 in result.criticality_changes
        assert result.criticality_changes[act_id_2] == -30.0  # 0 - 30
        assert act_id_3 in result.criticality_changes
        assert result.criticality_changes[act_id_3] == 20.0  # 20 - 0


class TestBuildScenarioDistributions:
    """Tests for build_scenario_distributions helper."""

    def test_build_from_activity_objects(self):
        """Should build distributions from activity objects."""
        activities = [
            MockActivity(duration=10),
            MockActivity(duration=20),
        ]

        distributions = build_scenario_distributions(activities)

        assert len(distributions) == 2
        for activity in activities:
            assert activity.id in distributions
            dist = distributions[activity.id]
            assert dist.distribution == DistributionType.TRIANGULAR

    def test_build_from_dict_activities(self):
        """Should build distributions from activity dicts."""
        id1 = uuid4()
        id2 = uuid4()
        activities = [
            {"id": id1, "duration": 10},
            {"id": id2, "duration": 20},
        ]

        distributions = build_scenario_distributions(activities)

        assert id1 in distributions
        assert id2 in distributions

    def test_build_skips_zero_duration(self):
        """Should skip activities with zero duration."""
        activities = [
            MockActivity(duration=0),
            MockActivity(duration=10),
        ]

        distributions = build_scenario_distributions(activities)

        assert len(distributions) == 1

    def test_build_with_custom_distributions(self):
        """Should use custom distributions when provided."""
        activity = MockActivity(duration=10)
        custom = {
            activity.id: {
                "distribution": "pert",
                "min_value": 5.0,
                "mode": 10.0,
                "max_value": 20.0,
            }
        }

        distributions = build_scenario_distributions([activity], custom_distributions=custom)

        dist = distributions[activity.id]
        assert dist.distribution == DistributionType.PERT
        assert dist.min_value == 5.0
        assert dist.mode == 10.0
        assert dist.max_value == 20.0

    def test_build_with_custom_uncertainty_factor(self):
        """Should respect custom uncertainty factor."""
        activity = MockActivity(duration=10)

        distributions = build_scenario_distributions([activity], uncertainty_factor=0.3)

        dist = distributions[activity.id]
        assert dist.min_value == 7.0  # 10 * 0.7
        assert dist.max_value == 13.0  # 10 * 1.3

    def test_build_handles_none_duration(self):
        """Should skip activities with None duration."""

        class ActivityWithNone:
            id = uuid4()
            duration = None

        distributions = build_scenario_distributions([ActivityWithNone()])

        assert len(distributions) == 0

    def test_build_handles_dict_without_duration(self):
        """Should skip dicts without duration key."""
        activities = [
            {"id": uuid4()},  # No duration
        ]

        distributions = build_scenario_distributions(activities)

        assert len(distributions) == 0
