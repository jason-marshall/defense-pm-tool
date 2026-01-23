"""Performance benchmarks for Week 11 targets.

Per Risk Mitigation Playbook Week 11 triggers:
- GREEN: Scenarios <10s
- YELLOW: Scenarios 10-30s
- RED: Scenarios >30s or corrupting baseline
"""

import time
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

import pytest

from src.services.cpm import CPMEngine
from src.services.monte_carlo import DistributionParams, DistributionType, MonteCarloEngine
from src.services.monte_carlo_cpm import (
    NetworkMonteCarloEngine,
    NetworkSimulationInput,
)
from src.services.scenario_simulation import ScenarioSimulationService


@dataclass
class MockActivity:
    """Mock activity for benchmarks."""

    id: any
    duration: int
    budgeted_cost: Decimal
    name: str
    code: str | None = None


@dataclass
class MockDependency:
    """Mock dependency for benchmarks."""

    id: any
    predecessor_id: any
    successor_id: any
    dependency_type: str
    lag: int


@dataclass
class MockScenario:
    """Mock scenario for benchmarks."""

    id: any
    name: str = "Test Scenario"


@dataclass
class MockScenarioChange:
    """Mock scenario change for benchmarks."""

    id: any
    entity_id: any
    entity_type: str
    change_type: str
    field_name: str | None
    old_value: any
    new_value: any


class TestScenarioPerformance:
    """Benchmark scenario simulation performance."""

    @pytest.fixture
    def sample_activities_100(self) -> list[MockActivity]:
        """Create 100 sample activities."""
        activities = []
        for i in range(100):
            act = MockActivity(
                id=uuid4(),
                code=f"ACT-{i:03d}",
                name=f"Activity {i}",
                duration=10 + (i % 20),
                budgeted_cost=Decimal("10000"),
            )
            activities.append(act)
        return activities

    @pytest.fixture
    def sample_activities_500(self) -> list[MockActivity]:
        """Create 500 sample activities."""
        activities = []
        for i in range(500):
            act = MockActivity(
                id=uuid4(),
                code=f"ACT-{i:03d}",
                name=f"Activity {i}",
                duration=10 + (i % 30),
                budgeted_cost=Decimal("10000"),
            )
            activities.append(act)
        return activities

    @pytest.fixture
    def chain_dependencies(self, sample_activities_100: list[MockActivity]) -> list[MockDependency]:
        """Create chain dependencies (A->B->C...)."""
        deps = []
        for i in range(1, len(sample_activities_100)):
            dep = MockDependency(
                id=uuid4(),
                predecessor_id=sample_activities_100[i - 1].id,
                successor_id=sample_activities_100[i].id,
                dependency_type="FS",
                lag=0,
            )
            deps.append(dep)
        return deps

    @pytest.fixture
    def chain_dependencies_500(
        self, sample_activities_500: list[MockActivity]
    ) -> list[MockDependency]:
        """Create chain dependencies for 500 activities."""
        deps = []
        for i in range(1, len(sample_activities_500)):
            dep = MockDependency(
                id=uuid4(),
                predecessor_id=sample_activities_500[i - 1].id,
                successor_id=sample_activities_500[i].id,
                dependency_type="FS",
                lag=0,
            )
            deps.append(dep)
        return deps

    @pytest.fixture
    def sample_changes(self, sample_activities_100: list[MockActivity]) -> list[MockScenarioChange]:
        """Create sample scenario changes (modify 10% of activities)."""
        changes = []
        for i in range(0, len(sample_activities_100), 10):
            change = MockScenarioChange(
                id=uuid4(),
                entity_id=sample_activities_100[i].id,
                entity_type="activity",
                change_type="update",
                field_name="duration",
                old_value=sample_activities_100[i].duration,
                new_value=sample_activities_100[i].duration + 5,
            )
            changes.append(change)
        return changes

    def test_scenario_apply_changes_under_100ms(
        self,
        sample_activities_100: list[MockActivity],
        chain_dependencies: list[MockDependency],
        sample_changes: list[MockScenarioChange],
    ) -> None:
        """Applying scenario changes should complete in <100ms for 100 activities."""
        scenario = MockScenario(id=uuid4())

        service = ScenarioSimulationService(
            activities=sample_activities_100,  # type: ignore
            dependencies=chain_dependencies,  # type: ignore
            scenario=scenario,  # type: ignore
            changes=sample_changes,  # type: ignore
        )

        start = time.perf_counter()
        modified = service.apply_changes()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(modified) == 100
        assert elapsed_ms < 100, f"Apply changes took {elapsed_ms:.2f}ms, target <100ms"
        print(f"\n  Apply changes (100 activities): {elapsed_ms:.2f}ms")

    def test_scenario_simulation_under_10s_100_activities(
        self,
        sample_activities_100: list[MockActivity],
        chain_dependencies: list[MockDependency],
        sample_changes: list[MockScenarioChange],
    ) -> None:
        """Scenario simulation should complete in <10s for 100 activities (1000 iterations)."""
        scenario = MockScenario(id=uuid4())

        service = ScenarioSimulationService(
            activities=sample_activities_100,  # type: ignore
            dependencies=chain_dependencies,  # type: ignore
            scenario=scenario,  # type: ignore
            changes=sample_changes,  # type: ignore
        )

        start = time.perf_counter()
        output = service.simulate(iterations=1000, seed=42)
        elapsed = time.perf_counter() - start

        assert output.iterations == 1000
        assert elapsed < 10, f"Simulation took {elapsed:.2f}s, target <10s (GREEN)"
        print(f"\n  Scenario simulation (100 activities, 1000 iter): {elapsed:.2f}s")

        # Check for YELLOW threshold
        if elapsed > 5:
            print("  WARNING: Approaching YELLOW threshold (>10s)")

    def test_scenario_simulation_500_activities(
        self,
        sample_activities_500: list[MockActivity],
        chain_dependencies_500: list[MockDependency],
    ) -> None:
        """Benchmark scenario simulation for 500 activities."""
        scenario = MockScenario(id=uuid4())

        # Create changes for 10% of activities
        changes = []
        for i in range(0, len(sample_activities_500), 10):
            change = MockScenarioChange(
                id=uuid4(),
                entity_id=sample_activities_500[i].id,
                entity_type="activity",
                change_type="update",
                field_name="duration",
                old_value=sample_activities_500[i].duration,
                new_value=sample_activities_500[i].duration + 5,
            )
            changes.append(change)

        service = ScenarioSimulationService(
            activities=sample_activities_500,  # type: ignore
            dependencies=chain_dependencies_500,  # type: ignore
            scenario=scenario,  # type: ignore
            changes=changes,  # type: ignore
        )

        start = time.perf_counter()
        output = service.simulate(iterations=500, seed=42)
        elapsed = time.perf_counter() - start

        print(f"\n  Scenario simulation (500 activities, 500 iter): {elapsed:.2f}s")

        # 500 activities should still complete in reasonable time
        assert elapsed < 30, f"Simulation took {elapsed:.2f}s, target <30s"


class TestCPMPerformance:
    """Benchmark CPM calculation performance."""

    @pytest.fixture
    def activities_1000(self) -> list[MockActivity]:
        """Create 1000 sample activities."""
        return [
            MockActivity(
                id=uuid4(),
                code=f"ACT-{i:04d}",
                name=f"Activity {i}",
                duration=5 + (i % 25),
                budgeted_cost=Decimal("5000"),
            )
            for i in range(1000)
        ]

    @pytest.fixture
    def chain_deps_1000(self, activities_1000: list[MockActivity]) -> list[MockDependency]:
        """Create chain dependencies for 1000 activities."""
        return [
            MockDependency(
                id=uuid4(),
                predecessor_id=activities_1000[i - 1].id,
                successor_id=activities_1000[i].id,
                dependency_type="FS",
                lag=0,
            )
            for i in range(1, 1000)
        ]

    def test_cpm_1000_activities_under_500ms(
        self,
        activities_1000: list[MockActivity],
        chain_deps_1000: list[MockDependency],
    ) -> None:
        """CPM calculation should complete in <500ms for 1000 activities."""
        engine = CPMEngine(activities_1000, chain_deps_1000)  # type: ignore

        start = time.perf_counter()
        results = engine.calculate()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(results) == 1000
        assert elapsed_ms < 500, f"CPM took {elapsed_ms:.2f}ms, target <500ms"
        print(f"\n  CPM calculation (1000 activities): {elapsed_ms:.2f}ms")


class TestMonteCarloPerformance:
    """Benchmark Monte Carlo simulation performance."""

    def test_monte_carlo_1000_iter_under_5s(self) -> None:
        """Monte Carlo should complete 1000 iterations in <5s."""
        from src.services.monte_carlo import SimulationInput

        engine = MonteCarloEngine(seed=42)

        # Create 100 distributions as a dict mapping UUID to DistributionParams
        activity_durations: dict = {}
        for i in range(100):
            base = 10 + i
            activity_durations[uuid4()] = DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=base * 0.8,
                mode=float(base),
                max_value=base * 1.2,
            )

        sim_input = SimulationInput(
            activity_durations=activity_durations,
            iterations=1000,
            seed=42,
        )

        start = time.perf_counter()
        output = engine.simulate(sim_input)
        elapsed = time.perf_counter() - start

        assert output.iterations == 1000
        assert elapsed < 5, f"Monte Carlo took {elapsed:.2f}s, target <5s"
        print(f"\n  Monte Carlo (100 activities, 1000 iter): {elapsed:.2f}s")

    def test_network_monte_carlo_under_10s(self) -> None:
        """Network Monte Carlo should complete in <10s for 100 activities (GREEN threshold)."""
        # Create 100 activities
        activities = [
            MockActivity(
                id=uuid4(),
                code=f"ACT-{i:03d}",
                name=f"Activity {i}",
                duration=10 + (i % 15),
                budgeted_cost=Decimal("10000"),
            )
            for i in range(100)
        ]

        # Create chain dependencies
        dependencies = [
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[i - 1].id,
                successor_id=activities[i].id,
                dependency_type="FS",
                lag=0,
            )
            for i in range(1, 100)
        ]

        # Create distributions
        distributions = {}
        for act in activities:
            base = float(act.duration)
            distributions[act.id] = DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=base * 0.8,
                mode=base,
                max_value=base * 1.2,
            )

        engine = NetworkMonteCarloEngine(seed=42)
        sim_input = NetworkSimulationInput(
            activities=activities,  # type: ignore
            dependencies=dependencies,  # type: ignore
            duration_distributions=distributions,
            iterations=1000,
            seed=42,
        )

        start = time.perf_counter()
        output = engine.simulate(sim_input)
        elapsed = time.perf_counter() - start

        assert output.iterations == 1000
        assert elapsed < 10, f"Network Monte Carlo took {elapsed:.2f}s, target <10s (GREEN)"
        print(f"\n  Network Monte Carlo (100 activities, 1000 iter): {elapsed:.2f}s")


class TestDashboardPerformance:
    """Benchmark dashboard-related performance."""

    def test_evms_calculations_under_100ms(self) -> None:
        """EVMS calculations should complete in <100ms for 1000 items."""
        from src.services.evms import EVMSCalculator

        start = time.perf_counter()

        # Simulate 1000 EVMS calculations
        for i in range(1000):
            bcws = Decimal(str(10000 + i * 100))
            bcwp = Decimal(str(9500 + i * 95))
            acwp = Decimal(str(9800 + i * 98))
            bac = Decimal("1000000")

            _ = EVMSCalculator.calculate_cost_variance(bcwp, acwp)
            _ = EVMSCalculator.calculate_schedule_variance(bcwp, bcws)
            _ = EVMSCalculator.calculate_cpi(bcwp, acwp)
            _ = EVMSCalculator.calculate_spi(bcwp, bcws)
            _ = EVMSCalculator.calculate_eac(bac, acwp, bcwp, "cpi")

        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"EVMS calculations took {elapsed_ms:.2f}ms, target <100ms"
        print(f"\n  EVMS calculations (1000 items): {elapsed_ms:.2f}ms")


class TestPerformanceSummary:
    """Summary test that outputs all performance metrics."""

    def test_performance_summary(self) -> None:
        """Generate performance summary for Week 11 review."""
        results = []

        # CPM benchmark
        activities = [
            MockActivity(
                id=uuid4(),
                code=f"A{i}",
                name=f"Act {i}",
                duration=10,
                budgeted_cost=Decimal("1000"),
            )
            for i in range(100)
        ]
        deps = [
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[i - 1].id,
                successor_id=activities[i].id,
                dependency_type="FS",
                lag=0,
            )
            for i in range(1, 100)
        ]

        engine = CPMEngine(activities, deps)  # type: ignore
        start = time.perf_counter()
        engine.calculate()
        cpm_time = (time.perf_counter() - start) * 1000
        results.append(("CPM (100 activities)", f"{cpm_time:.2f}ms", "<50ms", cpm_time < 50))

        # Scenario simulation benchmark
        scenario = MockScenario(id=uuid4())
        changes: list[MockScenarioChange] = []

        service = ScenarioSimulationService(
            activities=activities,  # type: ignore
            dependencies=deps,  # type: ignore
            scenario=scenario,  # type: ignore
            changes=changes,
        )

        start = time.perf_counter()
        service.simulate(iterations=1000, seed=42)
        sim_time = time.perf_counter() - start
        results.append(
            ("Scenario sim (100 act, 1000 iter)", f"{sim_time:.2f}s", "<10s", sim_time < 10)
        )

        # Print summary
        print("\n" + "=" * 70)
        print("PERFORMANCE SUMMARY - Week 11 Targets")
        print("=" * 70)
        print(f"{'Operation':<40} {'Actual':<12} {'Target':<12} {'Status'}")
        print("-" * 70)

        for name, actual, target, passed in results:
            status = "[PASS] GREEN" if passed else "[FAIL] RED"
            print(f"{name:<40} {actual:<12} {target:<12} {status}")

        print("=" * 70)

        # All benchmarks should pass
        assert all(r[3] for r in results), "Some benchmarks failed targets"
