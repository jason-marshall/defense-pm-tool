"""Unit tests for optimized Monte Carlo engine."""

from uuid import uuid4

import numpy as np
import pytest

from src.services.monte_carlo import DistributionParams, DistributionType
from src.services.monte_carlo_optimized import (
    OptimizedNetworkMonteCarloEngine,
)


class MockActivity:
    """Mock activity for testing."""

    def __init__(self, id, duration):
        self.id = id
        self.duration = duration


class MockDependency:
    """Mock dependency for testing."""

    def __init__(self, predecessor_id, successor_id, lag=0):
        self.predecessor_id = predecessor_id
        self.successor_id = successor_id
        self.dependency_type = "FS"
        self.lag = lag


class TestOptimizedMonteCarloEngineBasic:
    """Basic tests for optimized Monte Carlo simulation."""

    def test_simple_chain_deterministic(self):
        """Should correctly simulate simple chain with fixed durations."""
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

        # Use constant distributions (min == mode == max)
        distributions = {
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=10,
                mode=10,
                max_value=10,
            ),
            b_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=5,
                max_value=5,
            ),
            c_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=8,
                mode=8,
                max_value=8,
            ),
        }

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=100)

        # Project duration should be 10 + 5 + 8 = 23 for all iterations
        assert output.project_duration_mean == pytest.approx(23.0, abs=0.1)
        assert output.project_duration_p50 == pytest.approx(23.0, abs=0.1)

    def test_simple_chain_variable(self):
        """Should correctly simulate simple chain with variable durations."""
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

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=500)

        # All activities should be 100% critical (single chain)
        for activity in activities:
            assert output.activity_criticality[activity.id] == 100.0

        # Project duration should have some variance
        assert output.project_duration_std > 0

    def test_parallel_activities(self):
        """Should correctly handle parallel activities."""
        start_id = uuid4()
        a_id, b_id = uuid4(), uuid4()
        end_id = uuid4()

        activities = [
            MockActivity(start_id, 0),
            MockActivity(a_id, 10),  # Longer path
            MockActivity(b_id, 5),  # Shorter path
            MockActivity(end_id, 0),
        ]

        dependencies = [
            MockDependency(start_id, a_id),
            MockDependency(start_id, b_id),
            MockDependency(a_id, end_id),
            MockDependency(b_id, end_id),
        ]

        # Make path A always longer
        distributions = {
            start_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=0,
                mode=0,
                max_value=0,
            ),
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=10,
                mode=10,
                max_value=10,
            ),
            b_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=5,
                max_value=5,
            ),
            end_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=0,
                mode=0,
                max_value=0,
            ),
        }

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=100)

        # Project duration should be 10 (longer path)
        assert output.project_duration_mean == pytest.approx(10.0, abs=0.1)

        # Activity A should be 100% critical, B should be 0%
        assert output.activity_criticality[a_id] == 100.0
        assert output.activity_criticality[b_id] == 0.0

    def test_parallel_activities_variable_criticality(self):
        """Should correctly calculate variable criticality for parallel paths."""
        start_id = uuid4()
        a_id, b_id = uuid4(), uuid4()
        end_id = uuid4()

        activities = [
            MockActivity(start_id, 0),
            MockActivity(a_id, 10),
            MockActivity(b_id, 10),  # Same base duration
            MockActivity(end_id, 0),
        ]

        dependencies = [
            MockDependency(start_id, a_id),
            MockDependency(start_id, b_id),
            MockDependency(a_id, end_id),
            MockDependency(b_id, end_id),
        ]

        # Both paths have overlapping ranges
        distributions = {
            start_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=0,
                mode=0,
                max_value=0,
            ),
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=8,
                mode=10,
                max_value=15,
            ),
            b_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=8,
                mode=10,
                max_value=15,
            ),
            end_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=0,
                mode=0,
                max_value=0,
            ),
        }

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=1000)

        # Both activities should have criticality > 0 and < 100
        # (each should be critical roughly 50% of the time)
        assert 20 < output.activity_criticality[a_id] < 80
        assert 20 < output.activity_criticality[b_id] < 80


class TestOptimizedMonteCarloEngineDistributions:
    """Tests for different distribution types."""

    def test_triangular_distribution(self):
        """Should correctly sample from triangular distribution."""
        act_id = uuid4()
        activities = [MockActivity(act_id, 10)]
        dependencies = []

        distributions = {
            act_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=10,
                max_value=20,
            ),
        }

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=1000)

        # Mean should be approximately (5 + 10 + 20) / 3 = 11.67 for triangular
        assert 10 < output.project_duration_mean < 13

    def test_pert_distribution(self):
        """Should correctly sample from PERT distribution."""
        act_id = uuid4()
        activities = [MockActivity(act_id, 10)]
        dependencies = []

        distributions = {
            act_id: DistributionParams(
                distribution=DistributionType.PERT,
                min_value=5,
                mode=10,
                max_value=20,
            ),
        }

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=1000)

        # PERT mean = (5 + 4*10 + 20) / 6 = 10.83
        assert 9 < output.project_duration_mean < 12

    def test_normal_distribution(self):
        """Should correctly sample from normal distribution."""
        act_id = uuid4()
        activities = [MockActivity(act_id, 10)]
        dependencies = []

        distributions = {
            act_id: DistributionParams(
                distribution=DistributionType.NORMAL,
                mean=10.0,
                std=2.0,
            ),
        }

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=1000)

        # Mean should be approximately 10
        assert 9 < output.project_duration_mean < 11
        # Std should be approximately 2
        assert 1.5 < output.project_duration_std < 2.5

    def test_uniform_distribution(self):
        """Should correctly sample from uniform distribution."""
        act_id = uuid4()
        activities = [MockActivity(act_id, 10)]
        dependencies = []

        distributions = {
            act_id: DistributionParams(
                distribution=DistributionType.UNIFORM,
                min_value=5,
                max_value=15,
            ),
        }

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=1000)

        # Mean should be approximately (5 + 15) / 2 = 10
        assert 9 < output.project_duration_mean < 11


class TestOptimizedMonteCarloEngineOutput:
    """Tests for output statistics and metrics."""

    def test_output_contains_all_percentiles(self):
        """Should calculate all standard percentiles."""
        act_id = uuid4()
        activities = [MockActivity(act_id, 10)]
        dependencies = []

        distributions = {
            act_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=10,
                max_value=20,
            ),
        }

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=500)

        assert output.project_duration_p10 is not None
        assert output.project_duration_p50 is not None
        assert output.project_duration_p80 is not None
        assert output.project_duration_p90 is not None
        assert output.project_duration_p10 < output.project_duration_p50
        assert output.project_duration_p50 < output.project_duration_p90

    def test_output_contains_histogram(self):
        """Should generate histogram data."""
        act_id = uuid4()
        activities = [MockActivity(act_id, 10)]
        dependencies = []

        distributions = {
            act_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=10,
                max_value=20,
            ),
        }

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=500)

        assert output.duration_histogram_bins is not None
        assert output.duration_histogram_counts is not None
        assert len(output.duration_histogram_bins) > 0
        assert len(output.duration_histogram_counts) > 0

    def test_output_contains_sensitivity(self):
        """Should calculate sensitivity for each activity."""
        a_id, b_id = uuid4(), uuid4()
        activities = [MockActivity(a_id, 10), MockActivity(b_id, 5)]

        dependencies = [MockDependency(a_id, b_id)]

        distributions = {
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=10,
                max_value=20,
            ),
            b_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=3,
                mode=5,
                max_value=8,
            ),
        }

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=500)

        assert a_id in output.sensitivity
        assert b_id in output.sensitivity
        # Both activities should have positive correlation with project duration
        assert output.sensitivity[a_id] > 0
        assert output.sensitivity[b_id] > 0

    def test_output_contains_activity_finish_distributions(self):
        """Should calculate finish distributions for each activity."""
        a_id, b_id = uuid4(), uuid4()
        activities = [MockActivity(a_id, 10), MockActivity(b_id, 5)]

        dependencies = [MockDependency(a_id, b_id)]

        distributions = {
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=10,
                max_value=20,
            ),
            b_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=3,
                mode=5,
                max_value=8,
            ),
        }

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=500)

        assert a_id in output.activity_finish_distributions
        assert b_id in output.activity_finish_distributions

        a_dist = output.activity_finish_distributions[a_id]
        assert "p10" in a_dist
        assert "p50" in a_dist
        assert "p90" in a_dist
        assert "mean" in a_dist
        assert "std" in a_dist


class TestOptimizedMonteCarloEngineLag:
    """Tests for lag handling."""

    def test_positive_lag(self):
        """Should correctly handle positive lag."""
        a_id, b_id = uuid4(), uuid4()
        activities = [MockActivity(a_id, 10), MockActivity(b_id, 5)]

        dependencies = [MockDependency(a_id, b_id, lag=3)]

        distributions = {
            a_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=10,
                mode=10,
                max_value=10,
            ),
            b_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=5,
                max_value=5,
            ),
        }

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=100)

        # A finishes at 10, B starts at 10+3=13, finishes at 18
        assert output.project_duration_mean == pytest.approx(18.0, abs=0.1)


class TestOptimizedMonteCarloEnginePerformance:
    """Performance tests for optimized Monte Carlo simulation."""

    def test_performance_1000_iterations_50_chain(self):
        """Should complete 1000 iterations with 50-activity chain in <5s."""
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

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=1000)

        assert output.elapsed_seconds < 5.0, f"Exceeded 5s target: {output.elapsed_seconds:.3f}s"
        assert output.iterations == 1000

    def test_performance_1000_iterations_100_chain(self):
        """Should complete 1000 iterations with 100-activity chain in <5s."""
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

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=1000)

        assert output.elapsed_seconds < 5.0, f"Exceeded 5s target: {output.elapsed_seconds:.3f}s"
        assert output.iterations == 1000

    def test_performance_1000_iterations_100_parallel(self):
        """Should complete 1000 iterations with 100 parallel activities in <5s."""
        start_id = uuid4()
        end_id = uuid4()

        activities = [MockActivity(start_id, 0)]
        dependencies = []
        distributions = {
            start_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=0,
                mode=0,
                max_value=0,
            ),
        }

        # 100 parallel activities
        for i in range(100):
            act_id = uuid4()
            activities.append(MockActivity(act_id, 10))
            distributions[act_id] = DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5 + i % 10,
                mode=10 + i % 10,
                max_value=20 + i % 10,
            )
            dependencies.append(MockDependency(start_id, act_id))
            dependencies.append(MockDependency(act_id, end_id))

        activities.append(MockActivity(end_id, 0))
        distributions[end_id] = DistributionParams(
            distribution=DistributionType.TRIANGULAR,
            min_value=0,
            mode=0,
            max_value=0,
        )

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=1000)

        assert output.elapsed_seconds < 5.0, f"Exceeded 5s target: {output.elapsed_seconds:.3f}s"
        assert output.iterations == 1000

    def test_performance_comparison_print(self):
        """Print performance comparison (not a pass/fail test)."""
        # Create 75-activity mixed topology (3 chains of 25)
        activities = []
        dependencies = []
        distributions = {}

        start_id = uuid4()
        end_id = uuid4()

        activities.append(MockActivity(start_id, 0))
        distributions[start_id] = DistributionParams(
            distribution=DistributionType.TRIANGULAR,
            min_value=0,
            mode=0,
            max_value=0,
        )

        chain_ends = []
        for chain in range(3):
            prev_id = start_id
            for _ in range(25):
                act_id = uuid4()
                activities.append(MockActivity(act_id, 5 + chain))
                distributions[act_id] = DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=3 + chain,
                    mode=5 + chain,
                    max_value=8 + chain,
                )
                dependencies.append(MockDependency(prev_id, act_id))
                prev_id = act_id
            chain_ends.append(prev_id)

        activities.append(MockActivity(end_id, 0))
        distributions[end_id] = DistributionParams(
            distribution=DistributionType.TRIANGULAR,
            min_value=0,
            mode=0,
            max_value=0,
        )

        for chain_end in chain_ends:
            dependencies.append(MockDependency(chain_end, end_id))

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=1000)

        print(f"\nOptimized MC (75 mixed topology, 1000 iter): {output.elapsed_seconds:.3f}s")
        assert output.elapsed_seconds < 5.0


class TestOptimizedMonteCarloEngineEdgeCases:
    """Edge case tests for optimized Monte Carlo engine."""

    def test_single_activity(self):
        """Should handle single activity with no dependencies."""
        act_id = uuid4()
        activities = [MockActivity(act_id, 10)]
        dependencies = []

        distributions = {
            act_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=10,
                max_value=15,
            ),
        }

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=100)

        assert output.activity_criticality[act_id] == 100.0
        assert output.iterations == 100

    def test_no_distribution_uses_base_duration(self):
        """Should use base duration when no distribution provided."""
        act_id = uuid4()
        activities = [MockActivity(act_id, 10)]
        dependencies = []
        distributions = {}  # No distribution

        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(activities, dependencies, distributions, iterations=100)

        # All iterations should have duration 10
        assert output.project_duration_mean == 10.0
        assert output.project_duration_std == 0.0

    def test_reproducibility_with_seed(self):
        """Should produce same results with same seed."""
        act_id = uuid4()
        activities = [MockActivity(act_id, 10)]
        dependencies = []

        distributions = {
            act_id: DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5,
                mode=10,
                max_value=15,
            ),
        }

        engine1 = OptimizedNetworkMonteCarloEngine(seed=42)
        output1 = engine1.simulate(activities, dependencies, distributions, iterations=100)

        engine2 = OptimizedNetworkMonteCarloEngine(seed=42)
        output2 = engine2.simulate(activities, dependencies, distributions, iterations=100)

        assert output1.project_duration_mean == output2.project_duration_mean
        np.testing.assert_array_almost_equal(
            output1.project_duration_samples, output2.project_duration_samples
        )
