"""Unit tests for network-aware Monte Carlo simulation."""

from uuid import uuid4

import numpy as np

from src.services.monte_carlo import DistributionParams, DistributionType
from src.services.monte_carlo_cpm import (
    NetworkMonteCarloEngine,
    NetworkSimulationInput,
    NetworkSimulationOutput,
    SimulatedActivity,
)


class MockActivity:
    """Mock activity for testing."""

    def __init__(self, id, duration):
        self.id = id
        self.duration = duration


class MockDependency:
    """Mock dependency for testing."""

    def __init__(self, predecessor_id, successor_id, dependency_type="FS", lag=0):
        self.predecessor_id = predecessor_id
        self.successor_id = successor_id
        self.dependency_type = dependency_type
        self.lag = lag


class TestSimulatedActivity:
    """Tests for SimulatedActivity dataclass."""

    def test_create_activity(self) -> None:
        """Should create activity with given values."""
        act_id = uuid4()
        activity = SimulatedActivity(id=act_id, duration=10)
        assert activity.id == act_id
        assert activity.duration == 10

    def test_rounds_duration(self) -> None:
        """Should round duration to integer."""
        act_id = uuid4()
        activity = SimulatedActivity(id=act_id, duration=10.7)
        assert activity.duration == 11

    def test_negative_duration_becomes_zero(self) -> None:
        """Should clamp negative duration to zero."""
        act_id = uuid4()
        activity = SimulatedActivity(id=act_id, duration=-5)
        assert activity.duration == 0


class TestNetworkSimulationInput:
    """Tests for NetworkSimulationInput dataclass."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        input_data = NetworkSimulationInput(
            activities=[],
            dependencies=[],
            duration_distributions={},
        )
        assert input_data.iterations == 1000
        assert input_data.seed is None

    def test_custom_values(self) -> None:
        """Should accept custom values."""
        input_data = NetworkSimulationInput(
            activities=[],
            dependencies=[],
            duration_distributions={},
            iterations=500,
            seed=42,
        )
        assert input_data.iterations == 500
        assert input_data.seed == 42


class TestNetworkMonteCarloEngine:
    """Tests for network-aware Monte Carlo simulation."""

    def test_simple_chain(self) -> None:
        """Should simulate a simple A -> B -> C chain."""
        a_id, b_id, c_id = uuid4(), uuid4(), uuid4()

        activities = [
            MockActivity(a_id, 10),
            MockActivity(b_id, 5),
            MockActivity(c_id, 8),
        ]

        dependencies = [
            MockDependency(a_id, b_id),
            MockDependency(b_id, c_id),
        ]

        distributions = {
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=8,
                mode=10,
                max_value=15,
            ),
            b_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=3,
                mode=5,
                max_value=8,
            ),
            c_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=6,
                mode=8,
                max_value=12,
            ),
        }

        engine = NetworkMonteCarloEngine(seed=42)
        input_data = NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions=distributions,
            iterations=100,
        )

        output = engine.simulate(input_data)

        # Project duration should be sum of durations (17-35 range)
        assert 17 <= output.project_duration_p10 <= output.project_duration_p90 <= 35
        assert output.project_duration_mean >= output.project_duration_p10
        assert output.project_duration_mean <= output.project_duration_p90

        # All activities should be 100% critical (single chain)
        for activity in activities:
            assert output.activity_criticality[activity.id] == 100.0

    def test_parallel_paths(self) -> None:
        """Should track criticality on parallel paths."""
        start_id = uuid4()
        a_id, b_id = uuid4(), uuid4()  # Parallel
        end_id = uuid4()

        activities = [
            MockActivity(start_id, 0),
            MockActivity(a_id, 10),  # Path A: longer
            MockActivity(b_id, 5),  # Path B: shorter
            MockActivity(end_id, 0),
        ]

        dependencies = [
            MockDependency(start_id, a_id),
            MockDependency(start_id, b_id),
            MockDependency(a_id, end_id),
            MockDependency(b_id, end_id),
        ]

        # Path A has high uncertainty, Path B has low
        distributions = {
            start_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=0,
                mode=0,
                max_value=0,
            ),
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=10,
                max_value=20,
            ),
            b_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=4,
                mode=5,
                max_value=6,
            ),
            end_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=0,
                mode=0,
                max_value=0,
            ),
        }

        engine = NetworkMonteCarloEngine(seed=42)
        input_data = NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions=distributions,
            iterations=500,
        )

        output = engine.simulate(input_data)

        # Path A should be critical more often (longer expected duration)
        assert output.activity_criticality[a_id] > output.activity_criticality[b_id]

        # Start and end should be 100% critical (always on path)
        assert output.activity_criticality[start_id] == 100.0
        assert output.activity_criticality[end_id] == 100.0

    def test_sensitivity_analysis(self) -> None:
        """Should calculate sensitivity (correlation with project duration)."""
        a_id, b_id = uuid4(), uuid4()

        activities = [
            MockActivity(a_id, 10),
            MockActivity(b_id, 5),
        ]

        dependencies = [
            MockDependency(a_id, b_id),
        ]

        # A has high variance, B has low variance
        distributions = {
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=10,
                max_value=20,
            ),
            b_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=4,
                mode=5,
                max_value=6,
            ),
        }

        engine = NetworkMonteCarloEngine(seed=42)
        input_data = NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions=distributions,
            iterations=500,
        )

        output = engine.simulate(input_data)

        # Activity A should have higher sensitivity (more variance)
        assert output.sensitivity[a_id] > output.sensitivity[b_id]

        # Both should be positive (both contribute to duration)
        assert output.sensitivity[a_id] > 0
        assert output.sensitivity[b_id] > 0

    def test_activity_finish_distributions(self) -> None:
        """Should calculate finish date distributions per activity."""
        a_id, b_id = uuid4(), uuid4()

        activities = [
            MockActivity(a_id, 10),
            MockActivity(b_id, 5),
        ]

        dependencies = [
            MockDependency(a_id, b_id),
        ]

        distributions = {
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=8,
                mode=10,
                max_value=12,
            ),
            b_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=4,
                mode=5,
                max_value=6,
            ),
        }

        engine = NetworkMonteCarloEngine(seed=42)
        input_data = NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions=distributions,
            iterations=200,
        )

        output = engine.simulate(input_data)

        # Check finish distribution for activity A
        a_finish = output.activity_finish_distributions[a_id]
        assert "p10" in a_finish
        assert "p50" in a_finish
        assert "p90" in a_finish
        assert "mean" in a_finish
        assert "std" in a_finish
        assert a_finish["p10"] <= a_finish["p50"] <= a_finish["p90"]

        # B's finish should be later than A's (B depends on A)
        b_finish = output.activity_finish_distributions[b_id]
        assert b_finish["p50"] > a_finish["p50"]

    def test_no_distribution_uses_base_duration(self) -> None:
        """Should use base duration when no distribution specified."""
        a_id, b_id = uuid4(), uuid4()

        activities = [
            MockActivity(a_id, 10),
            MockActivity(b_id, 5),
        ]

        dependencies = [
            MockDependency(a_id, b_id),
        ]

        # Only A has a distribution
        distributions = {
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=8,
                mode=10,
                max_value=12,
            ),
        }

        engine = NetworkMonteCarloEngine(seed=42)
        input_data = NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions=distributions,
            iterations=100,
        )

        output = engine.simulate(input_data)

        # B's finish should have low variance (fixed duration)
        b_finish = output.activity_finish_distributions[b_id]
        # All iterations should have B finish at same time relative to A
        assert b_finish["std"] < 2.0  # Some variance from A, but limited

    def test_histogram_generation(self) -> None:
        """Should generate histogram data for visualization."""
        a_id = uuid4()

        activities = [MockActivity(a_id, 10)]
        dependencies = []

        distributions = {
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=10,
                max_value=20,
            ),
        }

        engine = NetworkMonteCarloEngine(seed=42)
        input_data = NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions=distributions,
            iterations=100,
        )

        output = engine.simulate(input_data)

        assert output.duration_histogram_bins is not None
        assert output.duration_histogram_counts is not None
        assert len(output.duration_histogram_counts) == len(output.duration_histogram_bins) - 1

    def test_reproducibility_with_seed(self) -> None:
        """Should produce same results with same seed."""
        a_id = uuid4()

        activities = [MockActivity(a_id, 10)]
        dependencies = []

        distributions = {
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=10,
                max_value=20,
            ),
        }

        input_data = NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions=distributions,
            iterations=100,
            seed=42,
        )

        engine1 = NetworkMonteCarloEngine(seed=42)
        output1 = engine1.simulate(input_data)

        engine2 = NetworkMonteCarloEngine(seed=42)
        output2 = engine2.simulate(input_data)

        assert output1.project_duration_mean == output2.project_duration_mean
        assert output1.project_duration_p50 == output2.project_duration_p50

    def test_different_distribution_types(self) -> None:
        """Should support all distribution types."""
        a_id, b_id, c_id, d_id = uuid4(), uuid4(), uuid4(), uuid4()

        activities = [
            MockActivity(a_id, 10),
            MockActivity(b_id, 10),
            MockActivity(c_id, 10),
            MockActivity(d_id, 10),
        ]

        dependencies = [
            MockDependency(a_id, b_id),
            MockDependency(b_id, c_id),
            MockDependency(c_id, d_id),
        ]

        distributions = {
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=8,
                mode=10,
                max_value=12,
            ),
            b_id: DistributionParams(
                distribution=DistributionType.PERT,
                min_value=8,
                mode=10,
                max_value=12,
            ),
            c_id: DistributionParams(
                distribution=DistributionType.NORMAL,
                mean=10,
                std=2,
            ),
            d_id: DistributionParams(
                distribution=DistributionType.UNIFORM,
                min_value=8,
                max_value=12,
            ),
        }

        engine = NetworkMonteCarloEngine(seed=42)
        input_data = NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions=distributions,
            iterations=100,
        )

        output = engine.simulate(input_data)

        # Should complete without error
        assert output.iterations == 100
        assert output.project_duration_mean > 0


class TestNetworkMonteCarloPerformance:
    """Performance tests for network Monte Carlo."""

    def test_performance_50_activities(self) -> None:
        """Should complete 500 iterations with 50 activities quickly."""
        # Create chain of 50 activities
        activities = []
        dependencies = []
        distributions = {}

        prev_id = None
        for _ in range(50):
            act_id = uuid4()
            activities.append(MockActivity(act_id, 5))
            distributions[act_id] = DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=3,
                mode=5,
                max_value=8,
            )

            if prev_id:
                dependencies.append(MockDependency(prev_id, act_id))
            prev_id = act_id

        engine = NetworkMonteCarloEngine(seed=42)
        input_data = NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions=distributions,
            iterations=500,
        )

        output = engine.simulate(input_data)

        # Should complete within 15 seconds
        assert output.elapsed_seconds < 15.0
        assert output.iterations == 500

    def test_performance_100_activities(self) -> None:
        """Should complete 1000 iterations with 100 activities in <30s."""
        # Create chain of 100 activities
        activities = []
        dependencies = []
        distributions = {}

        prev_id = None
        for _ in range(100):
            act_id = uuid4()
            activities.append(MockActivity(act_id, 5))
            distributions[act_id] = DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=3,
                mode=5,
                max_value=8,
            )

            if prev_id:
                dependencies.append(MockDependency(prev_id, act_id))
            prev_id = act_id

        engine = NetworkMonteCarloEngine(seed=42)
        input_data = NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions=distributions,
            iterations=1000,
        )

        output = engine.simulate(input_data)

        # Should complete within 30 seconds
        assert output.elapsed_seconds < 30.0
        assert output.iterations == 1000


class TestNetworkSimulationOutput:
    """Tests for NetworkSimulationOutput dataclass."""

    def test_output_fields(self) -> None:
        """Should have all expected fields."""
        output = NetworkSimulationOutput(
            project_duration_samples=np.array([10, 11, 12]),
            project_duration_p10=10.0,
            project_duration_p50=11.0,
            project_duration_p80=11.5,
            project_duration_p90=12.0,
            project_duration_mean=11.0,
            project_duration_std=1.0,
            project_duration_min=10.0,
            project_duration_max=12.0,
            iterations=100,
            elapsed_seconds=0.5,
        )

        assert len(output.project_duration_samples) == 3
        assert output.project_duration_p50 == 11.0
        assert output.iterations == 100
        assert output.activity_criticality == {}
        assert output.sensitivity == {}
