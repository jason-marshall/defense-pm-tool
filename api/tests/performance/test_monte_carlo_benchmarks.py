"""Monte Carlo performance benchmarks for Week 7 optimization."""

import time
from uuid import uuid4

import pytest

from src.services.monte_carlo import (
    DistributionParams,
    DistributionType,
    MonteCarloEngine,
    SimulationInput,
)
from src.services.monte_carlo_cpm import (
    NetworkMonteCarloEngine,
    NetworkSimulationInput,
)


class MockActivity:
    """Mock activity for benchmarking."""

    def __init__(self, id, duration):
        self.id = id
        self.duration = duration


class MockDependency:
    """Mock dependency for benchmarking."""

    def __init__(self, predecessor_id, successor_id):
        self.predecessor_id = predecessor_id
        self.successor_id = successor_id
        self.dependency_type = "FS"
        self.lag = 0


class TestMonteCarloPerformanceBenchmarks:
    """Performance benchmarks for Monte Carlo optimization."""

    @pytest.mark.benchmark
    def test_basic_monte_carlo_1000_iterations_100_activities(self):
        """Baseline: Basic MC engine - 1000 iterations, 100 activities."""
        engine = MonteCarloEngine(seed=42)

        distributions = {
            uuid4(): DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5 + i,
                mode=10 + i,
                max_value=20 + i,
            )
            for i in range(100)
        }

        input_data = SimulationInput(
            activity_durations=distributions,
            iterations=1000,
        )

        start = time.perf_counter()
        output = engine.simulate(input_data)
        elapsed = time.perf_counter() - start

        print(f"\nBasic MC (100 activities, 1000 iter): {elapsed:.3f}s")
        assert output is not None
        assert elapsed < 5.0, f"Basic MC exceeded 5s target: {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_basic_monte_carlo_5000_iterations_100_activities(self):
        """Baseline: Basic MC engine - 5000 iterations, 100 activities."""
        engine = MonteCarloEngine(seed=42)

        distributions = {
            uuid4(): DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5 + i,
                mode=10 + i,
                max_value=20 + i,
            )
            for i in range(100)
        }

        input_data = SimulationInput(
            activity_durations=distributions,
            iterations=5000,
        )

        start = time.perf_counter()
        output = engine.simulate(input_data)
        elapsed = time.perf_counter() - start

        print(f"\nBasic MC (100 activities, 5000 iter): {elapsed:.3f}s")
        assert output is not None
        assert elapsed < 10.0, f"Basic MC exceeded 10s target: {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_network_monte_carlo_chain_50_activities(self):
        """Baseline: Network MC with 50-activity chain."""
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
            iterations=1000,
        )

        start = time.perf_counter()
        output = engine.simulate(input_data)
        elapsed = time.perf_counter() - start

        print(f"\nNetwork MC (50 chain, 1000 iter): {elapsed:.3f}s")
        assert output is not None
        # Network MC is slower due to CPM calculations per iteration
        assert elapsed < 30.0, f"Network MC exceeded 30s: {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_network_monte_carlo_chain_100_activities(self):
        """Baseline: Network MC with 100-activity chain."""
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
            iterations=500,
        )

        start = time.perf_counter()
        output = engine.simulate(input_data)
        elapsed = time.perf_counter() - start

        print(f"\nNetwork MC (100 chain, 500 iter): {elapsed:.3f}s")
        assert output is not None
        assert elapsed < 60.0, f"Network MC exceeded 60s: {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_network_monte_carlo_parallel_100_activities(self):
        """Baseline: Network MC with 100 parallel activities."""
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

        engine = NetworkMonteCarloEngine(seed=42)
        input_data = NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions=distributions,
            iterations=500,
        )

        start = time.perf_counter()
        output = engine.simulate(input_data)
        elapsed = time.perf_counter() - start

        print(f"\nNetwork MC (100 parallel, 500 iter): {elapsed:.3f}s")
        assert output is not None
        assert elapsed < 30.0, f"Network MC exceeded 30s: {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_network_monte_carlo_mixed_topology_75_activities(self):
        """Baseline: Network MC with mixed topology (chains + parallel)."""
        # Create a more realistic network with 75 activities
        # 3 parallel chains of 25 activities each
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

        engine = NetworkMonteCarloEngine(seed=42)
        input_data = NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions=distributions,
            iterations=1000,
        )

        start = time.perf_counter()
        output = engine.simulate(input_data)
        elapsed = time.perf_counter() - start

        print(f"\nNetwork MC (75 mixed topology, 1000 iter): {elapsed:.3f}s")
        assert output is not None
        assert elapsed < 60.0, f"Network MC exceeded 60s: {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_basic_monte_carlo_different_distributions(self):
        """Baseline: Basic MC with mixed distribution types."""
        engine = MonteCarloEngine(seed=42)

        distributions = {}

        # 25 triangular
        for i in range(25):
            distributions[uuid4()] = DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=5 + i,
                mode=10 + i,
                max_value=20 + i,
            )

        # 25 PERT
        for i in range(25):
            distributions[uuid4()] = DistributionParams(
                distribution=DistributionType.PERT,
                min_value=5 + i,
                mode=10 + i,
                max_value=20 + i,
            )

        # 25 normal
        for i in range(25):
            distributions[uuid4()] = DistributionParams(
                distribution=DistributionType.NORMAL,
                mean=10 + i,
                std=2.0,
            )

        # 25 uniform
        for i in range(25):
            distributions[uuid4()] = DistributionParams(
                distribution=DistributionType.UNIFORM,
                min_value=5 + i,
                max_value=20 + i,
            )

        input_data = SimulationInput(
            activity_durations=distributions,
            iterations=1000,
        )

        start = time.perf_counter()
        output = engine.simulate(input_data)
        elapsed = time.perf_counter() - start

        print(f"\nBasic MC (100 mixed distributions, 1000 iter): {elapsed:.3f}s")
        assert output is not None
        assert elapsed < 5.0, f"Basic MC exceeded 5s target: {elapsed:.3f}s"


class TestOptimizedMonteCarloPerformance:
    """Performance benchmarks for optimized Monte Carlo engine."""

    @pytest.mark.benchmark
    def test_optimized_network_mc_100_chain_1000_iter(self):
        """Optimized: Network MC with 100-activity chain, 1000 iterations."""
        from src.services.monte_carlo_optimized import OptimizedNetworkMonteCarloEngine

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

        start = time.perf_counter()
        output = engine.simulate(activities, dependencies, distributions, iterations=1000)
        elapsed = time.perf_counter() - start

        print(f"\nOptimized MC (100 chain, 1000 iter): {elapsed:.3f}s")
        assert output is not None
        assert elapsed < 5.0, f"Optimized MC exceeded 5s target: {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_optimized_network_mc_100_parallel_1000_iter(self):
        """Optimized: Network MC with 100 parallel activities, 1000 iterations."""
        from src.services.monte_carlo_optimized import OptimizedNetworkMonteCarloEngine

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

        start = time.perf_counter()
        output = engine.simulate(activities, dependencies, distributions, iterations=1000)
        elapsed = time.perf_counter() - start

        print(f"\nOptimized MC (100 parallel, 1000 iter): {elapsed:.3f}s")
        assert output is not None
        assert elapsed < 5.0, f"Optimized MC exceeded 5s target: {elapsed:.3f}s"

    @pytest.mark.benchmark
    def test_comparison_original_vs_optimized(self):
        """Compare original vs optimized engines side-by-side."""
        from src.services.monte_carlo_optimized import OptimizedNetworkMonteCarloEngine

        # Create 50-activity chain
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

        # Run original engine
        original_engine = NetworkMonteCarloEngine(seed=42)
        original_input = NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions=distributions,
            iterations=500,
        )

        start = time.perf_counter()
        original_output = original_engine.simulate(original_input)
        original_elapsed = time.perf_counter() - start

        # Run optimized engine
        optimized_engine = OptimizedNetworkMonteCarloEngine(seed=42)

        start = time.perf_counter()
        optimized_output = optimized_engine.simulate(
            activities, dependencies, distributions, iterations=500
        )
        optimized_elapsed = time.perf_counter() - start

        print("\n=== Comparison (50 chain, 500 iter) ===")
        print(f"Original: {original_elapsed:.3f}s")
        print(f"Optimized: {optimized_elapsed:.3f}s")
        print(f"Speedup: {original_elapsed / optimized_elapsed:.1f}x")

        # Results should be similar (same seed)
        assert (
            abs(original_output.project_duration_mean - optimized_output.project_duration_mean)
            < 1.0
        )

        # Optimized should be faster
        assert optimized_elapsed < original_elapsed
