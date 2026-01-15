"""Performance benchmark tests for baseline establishment."""

import time
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.models.enums import DependencyType
from src.services.cpm import CPMEngine
from src.services.evms import EVMSCalculator


@dataclass
class MockActivity:
    """Mock activity for performance testing."""

    id: UUID
    program_id: UUID
    wbs_id: UUID
    code: str
    name: str
    duration: int


@dataclass
class MockDependency:
    """Mock dependency for performance testing."""

    id: UUID
    predecessor_id: UUID
    successor_id: UUID
    dependency_type: str
    lag: int


class TestPerformanceBenchmarks:
    """Performance benchmarks for Week 4 optimization baseline."""

    def create_activities(self, count: int, program_id: UUID | None = None) -> list[MockActivity]:
        """Create test activities."""
        program_id = program_id or uuid4()
        wbs_id = uuid4()
        return [
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code=f"A-{i:04d}",
                name=f"Activity {i}",
                duration=5 + (i % 10),
            )
            for i in range(count)
        ]

    def create_chain_dependencies(self, activities: list[MockActivity]) -> list[MockDependency]:
        """Create sequential dependencies (chain topology)."""
        deps = []
        for i in range(len(activities) - 1):
            deps.append(
                MockDependency(
                    id=uuid4(),
                    predecessor_id=activities[i].id,
                    successor_id=activities[i + 1].id,
                    dependency_type=DependencyType.FS.value,
                    lag=0,
                )
            )
        return deps

    def create_parallel_dependencies(
        self, activities: list[MockActivity], parallel_count: int = 10
    ) -> list[MockDependency]:
        """Create parallel dependencies (fan-out/fan-in topology)."""
        deps = []
        chunk_size = len(activities) // parallel_count

        for i in range(parallel_count):
            start_idx = i * chunk_size
            end_idx = (i + 1) * chunk_size if i < parallel_count - 1 else len(activities)

            # Chain within each parallel path
            for j in range(start_idx, end_idx - 1):
                deps.append(
                    MockDependency(
                        id=uuid4(),
                        predecessor_id=activities[j].id,
                        successor_id=activities[j + 1].id,
                        dependency_type=DependencyType.FS.value,
                        lag=0,
                    )
                )

        return deps

    @pytest.mark.benchmark
    def test_cpm_100_activities_chain(self):
        """Benchmark: CPM with 100 activities in chain topology."""
        activities = self.create_activities(100)
        dependencies = self.create_chain_dependencies(activities)

        start = time.perf_counter()
        engine = CPMEngine(activities, dependencies)
        results = engine.calculate()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify correctness
        assert len(results) == 100
        # Should complete in <50ms
        assert elapsed_ms < 50, f"CPM 100 took {elapsed_ms:.2f}ms, expected <50ms"
        print(f"\nCPM 100 activities (chain): {elapsed_ms:.2f}ms")

    @pytest.mark.benchmark
    def test_cpm_500_activities_chain(self):
        """Benchmark: CPM with 500 activities in chain topology."""
        activities = self.create_activities(500)
        dependencies = self.create_chain_dependencies(activities)

        start = time.perf_counter()
        engine = CPMEngine(activities, dependencies)
        results = engine.calculate()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(results) == 500
        # Target: <200ms
        assert elapsed_ms < 200, f"CPM 500 took {elapsed_ms:.2f}ms, expected <200ms"
        print(f"\nCPM 500 activities (chain): {elapsed_ms:.2f}ms")

    @pytest.mark.benchmark
    def test_cpm_1000_activities_chain(self):
        """Benchmark: CPM with 1000 activities (target <500ms)."""
        activities = self.create_activities(1000)
        dependencies = self.create_chain_dependencies(activities)

        start = time.perf_counter()
        engine = CPMEngine(activities, dependencies)
        results = engine.calculate()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(results) == 1000
        # Target: <500ms
        assert elapsed_ms < 500, f"CPM 1000 took {elapsed_ms:.2f}ms, expected <500ms"
        print(f"\nCPM 1000 activities (chain): {elapsed_ms:.2f}ms")

    @pytest.mark.benchmark
    def test_cpm_1000_activities_parallel(self):
        """Benchmark: CPM with 1000 activities in parallel topology."""
        activities = self.create_activities(1000)
        dependencies = self.create_parallel_dependencies(activities, parallel_count=10)

        start = time.perf_counter()
        engine = CPMEngine(activities, dependencies)
        results = engine.calculate()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(results) == 1000
        # Target: <500ms
        assert elapsed_ms < 500, f"CPM 1000 parallel took {elapsed_ms:.2f}ms, expected <500ms"
        print(f"\nCPM 1000 activities (parallel): {elapsed_ms:.2f}ms")

    @pytest.mark.benchmark
    def test_cpm_2000_activities_chain(self):
        """Benchmark: CPM with 2000 activities (target <1000ms)."""
        activities = self.create_activities(2000)
        dependencies = self.create_chain_dependencies(activities)

        start = time.perf_counter()
        engine = CPMEngine(activities, dependencies)
        results = engine.calculate()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(results) == 2000
        # Target: <1000ms
        assert elapsed_ms < 1000, f"CPM 2000 took {elapsed_ms:.2f}ms, expected <1000ms"
        print(f"\nCPM 2000 activities (chain): {elapsed_ms:.2f}ms")

    @pytest.mark.benchmark
    def test_cpm_5000_activities_chain(self):
        """Benchmark: CPM with 5000 activities (target <2000ms)."""
        activities = self.create_activities(5000)
        dependencies = self.create_chain_dependencies(activities)

        start = time.perf_counter()
        engine = CPMEngine(activities, dependencies)
        results = engine.calculate()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(results) == 5000
        # Target: <2000ms
        assert elapsed_ms < 2000, f"CPM 5000 took {elapsed_ms:.2f}ms, expected <2000ms"
        print(f"\nCPM 5000 activities (chain): {elapsed_ms:.2f}ms")

    @pytest.mark.benchmark
    def test_graph_construction_1000(self):
        """Benchmark: Graph construction time for 1000 activities."""
        activities = self.create_activities(1000)
        dependencies = self.create_chain_dependencies(activities)

        start = time.perf_counter()
        CPMEngine(activities, dependencies)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Target: Graph construction <100ms
        assert elapsed_ms < 100, f"Graph construction took {elapsed_ms:.2f}ms, expected <100ms"
        print(f"\nGraph construction (1000 nodes): {elapsed_ms:.2f}ms")


class TestEVMSPerformance:
    """Performance benchmarks for EVMS calculations."""

    @pytest.mark.benchmark
    def test_evms_calculations_batch(self):
        """Benchmark: EVMS metric calculations for batch of data."""
        # Simulate calculating metrics for 1000 WBS elements
        count = 1000
        bcws_values = [Decimal(f"{(i + 1) * 1000}.00") for i in range(count)]
        bcwp_values = [Decimal(f"{(i + 1) * 950}.00") for i in range(count)]
        acwp_values = [Decimal(f"{(i + 1) * 980}.00") for i in range(count)]

        start = time.perf_counter()
        for i in range(count):
            EVMSCalculator.calculate_cpi(bcwp_values[i], acwp_values[i])
            EVMSCalculator.calculate_spi(bcwp_values[i], bcws_values[i])
            EVMSCalculator.calculate_cost_variance(bcwp_values[i], acwp_values[i])
            EVMSCalculator.calculate_schedule_variance(bcwp_values[i], bcws_values[i])
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Target: <100ms for 1000 calculations
        assert elapsed_ms < 100, f"EVMS batch took {elapsed_ms:.2f}ms, expected <100ms"
        print(f"\nEVMS calculations (1000 items): {elapsed_ms:.2f}ms")
