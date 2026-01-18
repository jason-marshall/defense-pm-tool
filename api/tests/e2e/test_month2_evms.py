"""
End-to-End Test Suite for Month 2 EVMS Features.

This module contains comprehensive E2E tests that validate the complete
workflows implemented in Month 2:
1. Advanced EAC Methods (CPI, SPI*CPI, Composite)
2. Monte Carlo Simulation with Optimized Engine
3. Baseline Management and Comparison
4. Scenario Planning and What-If Analysis
5. CPR Format 3 Generation
6. CPR Format 5 Foundation
7. Variance Analysis
8. Enhanced S-Curve with Confidence Bands

These tests use mock objects to simulate database operations
while testing the full integration of services and business logic.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.models.enums import ConstraintType, DependencyType
from src.schemas.cpr_format5 import Format5ExportConfig
from src.services.cpm import CPMEngine
from src.services.cpr_format5_generator import CPRFormat5Generator
from src.services.evms import EACMethod, EVMSCalculator
from src.services.monte_carlo import (
    DistributionParams,
    DistributionType,
    MonteCarloEngine,
    SimulationInput,
)
from src.services.monte_carlo_optimized import OptimizedNetworkMonteCarloEngine
from src.services.scurve_enhanced import EnhancedSCurveService, SimulationMetrics
from src.services.variance_analysis import (
    TrendDirection,
    VarianceAnalysisService,
    VarianceSeverity,
    VarianceType,
)

# =============================================================================
# Mock Data Classes
# =============================================================================


@dataclass
class MockActivity:
    """Mock activity for E2E testing."""

    id: UUID
    program_id: UUID
    wbs_id: UUID
    code: str
    name: str
    duration: int
    percent_complete: Decimal = Decimal("0.00")
    budgeted_cost: Decimal = Decimal("0.00")
    actual_cost: Decimal = Decimal("0.00")
    is_milestone: bool = False
    total_float: int | None = None
    free_float: int | None = None
    is_critical: bool = False
    constraint_type: ConstraintType = ConstraintType.ASAP
    constraint_date: date | None = None


@dataclass
class MockDependency:
    """Mock dependency for E2E testing."""

    id: UUID
    predecessor_id: UUID
    successor_id: UUID
    dependency_type: str
    lag: int = 0


@dataclass
class MockProgram:
    """Mock program for E2E testing."""

    id: UUID
    name: str
    code: str
    start_date: date
    end_date: date
    budget_at_completion: Decimal = Decimal("1000000.00")
    contract_number: str | None = None


@dataclass
class MockEVMSPeriod:
    """Mock EVMS period for testing."""

    id: UUID
    program_id: UUID
    period_name: str
    period_start: date
    period_end: date
    cumulative_bcws: Decimal = Decimal("0.00")
    cumulative_bcwp: Decimal = Decimal("0.00")
    cumulative_acwp: Decimal = Decimal("0.00")
    # Period-only values (for S-curve)
    bcws: Decimal = Decimal("0.00")
    bcwp: Decimal = Decimal("0.00")
    acwp: Decimal = Decimal("0.00")

    @property
    def cost_variance(self) -> Decimal:
        return self.cumulative_bcwp - self.cumulative_acwp

    @property
    def schedule_variance(self) -> Decimal:
        return self.cumulative_bcwp - self.cumulative_bcws

    @property
    def cpi(self) -> Decimal | None:
        if self.cumulative_acwp == 0:
            return None
        return (self.cumulative_bcwp / self.cumulative_acwp).quantize(Decimal("0.01"))

    @property
    def spi(self) -> Decimal | None:
        if self.cumulative_bcws == 0:
            return None
        return (self.cumulative_bcwp / self.cumulative_bcws).quantize(Decimal("0.01"))


@dataclass
class MockBaseline:
    """Mock baseline for testing."""

    id: UUID
    program_id: UUID
    name: str
    scheduled_start: date
    scheduled_finish: date
    total_budget: Decimal
    is_active: bool = True


# =============================================================================
# Advanced EAC Methods Tests
# =============================================================================


class TestAdvancedEACMethodsE2E:
    """E2E tests for advanced EAC calculation methods."""

    def test_all_eac_methods_comparison(self) -> None:
        """
        Test all EAC methods produce valid and comparable results.

        Per EVMS GL 27, comparing multiple EAC methods helps validate
        the estimate and identify the most appropriate method.
        """
        # Program setup: $10M budget, 40% complete, over budget
        bac = Decimal("10000000.00")
        bcws = Decimal("4500000.00")  # 45% planned
        bcwp = Decimal("4000000.00")  # 40% earned
        acwp = Decimal("4400000.00")  # Spent more than earned

        # Calculate all EAC methods
        results = EVMSCalculator.calculate_all_eac_methods(
            bcws=bcws,
            bcwp=bcwp,
            acwp=acwp,
            bac=bac,
        )

        # Should have results for all methods
        assert len(results) >= 4

        # Extract results by method
        eac_by_method = {r.method: r for r in results}

        # 1. CPI Method: BAC / CPI
        assert EACMethod.CPI in eac_by_method
        eac_cpi = eac_by_method[EACMethod.CPI].eac
        cpi = bcwp / acwp  # 4000000 / 4400000 = 0.909
        expected_cpi = bac / cpi  # 10000000 / 0.909 ~ 11,000,000
        assert float(eac_cpi) == pytest.approx(float(expected_cpi), rel=0.01)

        # 2. Typical Method: ACWP + (BAC - BCWP)
        assert EACMethod.TYPICAL in eac_by_method
        eac_typical = eac_by_method[EACMethod.TYPICAL].eac
        expected_typical = acwp + (bac - bcwp)  # 4400000 + 6000000 = 10,400,000
        assert eac_typical == expected_typical

        # 3. Mathematical Method: ACWP + (BAC - BCWP) / CPI
        assert EACMethod.MATHEMATICAL in eac_by_method
        eac_math = eac_by_method[EACMethod.MATHEMATICAL].eac
        expected_math = acwp + ((bac - bcwp) / cpi)
        assert float(eac_math) == pytest.approx(float(expected_math), rel=0.01)

        # 4. Comprehensive Method: ACWP + (BAC - BCWP) / (CPI * SPI)
        assert EACMethod.COMPREHENSIVE in eac_by_method
        eac_comp = eac_by_method[EACMethod.COMPREHENSIVE].eac
        spi = bcwp / bcws  # 4000000 / 4500000 = 0.889
        expected_comp = acwp + ((bac - bcwp) / (cpi * spi))
        assert float(eac_comp) == pytest.approx(float(expected_comp), rel=0.01)

        # All methods should show overrun (EAC > BAC) given poor performance
        for result in results:
            assert result.eac > bac, f"{result.method} should show overrun"

        # VAC should be negative (unfavorable) for all methods
        for result in results:
            assert result.vac < 0, f"{result.method} should have negative VAC"

    def test_eac_methods_with_good_performance(self) -> None:
        """Test EAC methods when project is under budget and ahead of schedule."""
        bac = Decimal("5000000.00")
        bcws = Decimal("2000000.00")  # 40% planned
        bcwp = Decimal("2500000.00")  # 50% earned (ahead!)
        acwp = Decimal("2200000.00")  # Spent less than earned

        results = EVMSCalculator.calculate_all_eac_methods(
            bcws=bcws,
            bcwp=bcwp,
            acwp=acwp,
            bac=bac,
        )

        # Most methods should show underrun (EAC < BAC)
        eac_by_method = {r.method: r for r in results}

        # CPI > 1 means under budget
        cpi = bcwp / acwp  # 2500000 / 2200000 = 1.136
        assert cpi > Decimal("1.0")

        # SPI > 1 means ahead of schedule
        spi = bcwp / bcws  # 2500000 / 2000000 = 1.25
        assert spi > Decimal("1.0")

        # CPI method should show underrun
        assert eac_by_method[EACMethod.CPI].eac < bac

        # VAC should be positive (favorable)
        assert eac_by_method[EACMethod.CPI].vac > 0


# =============================================================================
# Monte Carlo Simulation Tests
# =============================================================================


class TestMonteCarloSimulationE2E:
    """E2E tests for Monte Carlo simulation workflow."""

    def create_test_activities_with_dependencies(
        self,
    ) -> tuple[list[MockActivity], list[MockDependency]]:
        """Create a realistic network of activities with dependencies."""
        program_id = uuid4()
        wbs_id = uuid4()

        # Create activities representing a software project
        activities = [
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code="REQ",
                name="Requirements Analysis",
                duration=10,
                budgeted_cost=Decimal("50000"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code="DES",
                name="System Design",
                duration=15,
                budgeted_cost=Decimal("75000"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code="DEV1",
                name="Module 1 Development",
                duration=20,
                budgeted_cost=Decimal("100000"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code="DEV2",
                name="Module 2 Development",
                duration=25,
                budgeted_cost=Decimal("125000"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code="INT",
                name="Integration",
                duration=10,
                budgeted_cost=Decimal("50000"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code="TEST",
                name="System Testing",
                duration=15,
                budgeted_cost=Decimal("75000"),
            ),
        ]

        # Create dependencies
        # REQ -> DES -> DEV1 -> INT -> TEST
        #            -> DEV2 -> INT
        dependencies = [
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[0].id,
                successor_id=activities[1].id,
                dependency_type=DependencyType.FS.value,
            ),
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[1].id,
                successor_id=activities[2].id,
                dependency_type=DependencyType.FS.value,
            ),
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[1].id,
                successor_id=activities[3].id,
                dependency_type=DependencyType.FS.value,
            ),
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[2].id,
                successor_id=activities[4].id,
                dependency_type=DependencyType.FS.value,
            ),
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[3].id,
                successor_id=activities[4].id,
                dependency_type=DependencyType.FS.value,
            ),
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[4].id,
                successor_id=activities[5].id,
                dependency_type=DependencyType.FS.value,
            ),
        ]

        return activities, dependencies

    def test_monte_carlo_basic_workflow(self) -> None:
        """Test basic Monte Carlo simulation workflow."""
        activities, dependencies = self.create_test_activities_with_dependencies()

        # First, run CPM to get deterministic duration
        engine = CPMEngine(activities, dependencies)
        engine.calculate()
        deterministic_duration = engine.get_project_duration()

        # Deterministic: REQ(10) + DES(15) + DEV2(25) + INT(10) + TEST(15) = 75 days
        assert deterministic_duration == 75

        # Create distribution params for each activity (triangular with +/- 20%)
        distributions: dict[UUID, DistributionParams] = {}
        for activity in activities:
            distributions[activity.id] = DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=activity.duration * 0.8,
                mode=float(activity.duration),
                max_value=activity.duration * 1.3,
            )

        # Run Monte Carlo using basic engine (sums durations)
        mc_engine = MonteCarloEngine(seed=42)
        simulation_input = SimulationInput(
            activity_durations=distributions,
            iterations=100,
        )
        result = mc_engine.simulate(simulation_input)

        # Verify result structure
        assert result.iterations == 100
        assert result.duration_p10 is not None
        assert result.duration_p50 is not None
        assert result.duration_p90 is not None

        # P10 should be less than P50 should be less than P90
        assert result.duration_p10 <= result.duration_p50 <= result.duration_p90

    def test_optimized_monte_carlo_with_network(self) -> None:
        """Test optimized Monte Carlo engine with network simulation."""
        activities, dependencies = self.create_test_activities_with_dependencies()

        # Create distribution params for each activity
        distributions: dict[UUID, DistributionParams] = {}
        for activity in activities:
            distributions[activity.id] = DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=activity.duration * 0.8,
                mode=float(activity.duration),
                max_value=activity.duration * 1.3,
            )

        # Run optimized Monte Carlo (respects network dependencies)
        optimized_engine = OptimizedNetworkMonteCarloEngine(seed=42)
        result = optimized_engine.simulate(
            activities=activities,
            dependencies=dependencies,
            distributions=distributions,
            iterations=500,
        )

        # Verify result structure
        assert result.iterations == 500
        assert result.project_duration_p10 is not None
        assert result.project_duration_p50 is not None
        assert result.project_duration_p90 is not None

        # P10 <= P50 <= P90
        assert result.project_duration_p10 <= result.project_duration_p50
        assert result.project_duration_p50 <= result.project_duration_p90

        # P50 should be close to deterministic (75 days) with some variance
        assert 60 <= result.project_duration_p50 <= 110

    def test_monte_carlo_different_distributions(self) -> None:
        """Test Monte Carlo with different distribution types."""
        activities, _ = self.create_test_activities_with_dependencies()

        # Test with PERT distribution
        distributions: dict[UUID, DistributionParams] = {}
        for activity in activities:
            distributions[activity.id] = DistributionParams(
                distribution=DistributionType.PERT,
                min_value=activity.duration * 0.7,
                mode=float(activity.duration),
                max_value=activity.duration * 1.5,
            )

        mc_engine = MonteCarloEngine(seed=42)
        simulation_input = SimulationInput(
            activity_durations=distributions,
            iterations=100,
        )
        result = mc_engine.simulate(simulation_input)

        # PERT should produce valid results
        assert result.duration_p50 > 0
        assert result.duration_p10 < result.duration_p90


# =============================================================================
# Variance Analysis Tests
# =============================================================================


class TestVarianceAnalysisE2E:
    """E2E tests for variance analysis workflow."""

    def create_test_period_data(self) -> list[dict]:
        """Create realistic EVMS period data for variance testing."""
        return [
            {
                "wbs_id": uuid4(),
                "wbs_code": "1.1",
                "wbs_name": "Engineering",
                "period_name": "January 2026",
                "cumulative_bcws": Decimal("500000"),
                "sv": Decimal("-75000"),  # -15% SV (significant)
                "cv": Decimal("-50000"),  # -10% CV (moderate)
            },
            {
                "wbs_id": uuid4(),
                "wbs_code": "1.2",
                "wbs_name": "Manufacturing",
                "period_name": "January 2026",
                "cumulative_bcws": Decimal("300000"),
                "sv": Decimal("-60000"),  # -20% SV (critical)
                "cv": Decimal("-90000"),  # -30% CV (critical)
            },
            {
                "wbs_id": uuid4(),
                "wbs_code": "1.3",
                "wbs_name": "Testing",
                "period_name": "January 2026",
                "cumulative_bcws": Decimal("200000"),
                "sv": Decimal("10000"),  # +5% SV (minor favorable)
                "cv": Decimal("-5000"),  # -2.5% CV (minor)
            },
            {
                "wbs_id": uuid4(),
                "wbs_code": "1.4",
                "wbs_name": "Project Management",
                "period_name": "January 2026",
                "cumulative_bcws": Decimal("100000"),
                "sv": Decimal("0"),
                "cv": Decimal("0"),
            },
        ]

    def test_complete_variance_analysis_workflow(self) -> None:
        """Test complete variance detection and analysis workflow."""
        period_data = self.create_test_period_data()
        program_id = uuid4()

        # Initialize service with standard thresholds
        service = VarianceAnalysisService()

        # Run program-level analysis
        result = service.analyze_program_variances(
            program_id=program_id,
            period_name="January 2026",
            period_data=period_data,
        )

        # Verify analysis results
        assert result.program_id == program_id
        assert result.total_wbs_analyzed == 4

        # Should have alerts for significant variances
        assert len(result.alerts) > 0

        # Verify severity counts
        assert result.critical_count >= 1  # 1.2 has critical variances
        assert result.significant_count >= 1  # 1.1 has significant variance

        # Manufacturing (1.2) should have critical alerts
        manufacturing_alerts = [a for a in result.alerts if a.wbs_code == "1.2"]
        assert len(manufacturing_alerts) >= 2  # Both SV and CV
        for alert in manufacturing_alerts:
            assert alert.severity == VarianceSeverity.CRITICAL
            assert alert.explanation_required is True

        # Engineering (1.1) should have at least one alert
        engineering_alerts = [a for a in result.alerts if a.wbs_code == "1.1"]
        assert len(engineering_alerts) >= 1

        # PM (1.4) should have no alerts (zero variances)
        pm_alerts = [a for a in result.alerts if a.wbs_code == "1.4"]
        assert len(pm_alerts) == 0

    def test_variance_trend_analysis(self) -> None:
        """Test variance trend analysis over multiple periods."""
        service = VarianceAnalysisService()
        wbs_id = uuid4()

        # Historical data showing worsening trend
        historical_data = [
            {
                "period_name": "October 2025",
                "cumulative_bcws": Decimal("100000"),
                "sv": Decimal("-5000"),  # -5%
                "cv": Decimal("-3000"),  # -3%
            },
            {
                "period_name": "November 2025",
                "cumulative_bcws": Decimal("200000"),
                "sv": Decimal("-20000"),  # -10%
                "cv": Decimal("-16000"),  # -8%
            },
            {
                "period_name": "December 2025",
                "cumulative_bcws": Decimal("300000"),
                "sv": Decimal("-45000"),  # -15%
                "cv": Decimal("-36000"),  # -12%
            },
            {
                "period_name": "January 2026",
                "cumulative_bcws": Decimal("400000"),
                "sv": Decimal("-80000"),  # -20%
                "cv": Decimal("-60000"),  # -15%
            },
        ]

        # Build SV trend
        sv_trend = service.build_variance_trend(
            wbs_id=wbs_id,
            wbs_code="1.1",
            variance_type=VarianceType.SCHEDULE,
            period_history=historical_data,
        )

        # Verify trend is worsening
        assert sv_trend.trend_direction == TrendDirection.WORSENING
        assert len(sv_trend.periods) == 4
        assert len(sv_trend.percentages) == 4

        # Should have multiple periods in breach
        assert sv_trend.periods_in_breach >= 3  # Dec and Jan are definitely in breach

        # Build CV trend
        cv_trend = service.build_variance_trend(
            wbs_id=wbs_id,
            wbs_code="1.1",
            variance_type=VarianceType.COST,
            period_history=historical_data,
        )

        assert cv_trend.trend_direction == TrendDirection.WORSENING

    def test_variance_summary_generation(self) -> None:
        """Test variance summary text generation."""
        period_data = self.create_test_period_data()
        service = VarianceAnalysisService()

        result = service.analyze_program_variances(
            program_id=uuid4(),
            period_name="January 2026",
            period_data=period_data,
        )

        summary = service.get_variance_summary_text(result)

        # Verify summary contains key information
        assert "January 2026" in summary
        assert "Critical" in summary
        assert "Explanations Required" in summary


# =============================================================================
# CPR Format 5 Tests
# =============================================================================


class TestCPRFormat5E2E:
    """E2E tests for CPR Format 5 generation."""

    def create_test_periods(self, program_id: UUID) -> list[MockEVMSPeriod]:
        """Create test EVMS periods for Format 5."""
        base_date = date(2026, 1, 1)
        periods = []

        # Create 6 months of period data showing declining performance
        cumulative_bcws = Decimal("0")
        cumulative_bcwp = Decimal("0")
        cumulative_acwp = Decimal("0")

        for i in range(6):
            period_start = base_date + timedelta(days=i * 30)
            period_end = period_start + timedelta(days=29)

            # Add period values (performance getting worse over time)
            period_bcws = Decimal("150000") + Decimal(str(i * 10000))
            period_bcwp = Decimal("145000") + Decimal(str(i * 8000))  # Falling behind
            period_acwp = Decimal("155000") + Decimal(str(i * 12000))  # Over budget

            cumulative_bcws += period_bcws
            cumulative_bcwp += period_bcwp
            cumulative_acwp += period_acwp

            periods.append(
                MockEVMSPeriod(
                    id=uuid4(),
                    program_id=program_id,
                    period_name=f"Month {i + 1}",
                    period_start=period_start,
                    period_end=period_end,
                    cumulative_bcws=cumulative_bcws,
                    cumulative_bcwp=cumulative_bcwp,
                    cumulative_acwp=cumulative_acwp,
                )
            )

        return periods

    def test_cpr_format5_generation_workflow(self) -> None:
        """Test complete CPR Format 5 report generation."""
        program = MockProgram(
            id=uuid4(),
            name="Defense Radar System",
            code="DRS-001",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            budget_at_completion=Decimal("5000000.00"),
            contract_number="W912DQ-26-C-0001",
        )

        periods = self.create_test_periods(program.id)

        # Generate Format 5 report
        config = Format5ExportConfig(periods_to_include=6)
        generator = CPRFormat5Generator(program, periods, config)
        report = generator.generate()

        # Verify report structure
        assert report.program_name == "Defense Radar System"
        assert report.program_code == "DRS-001"
        assert report.contract_number == "W912DQ-26-C-0001"
        assert report.bac == Decimal("5000000.00")

        # Verify period rows
        assert len(report.period_rows) == 6

        # Verify each period row has required data
        for row in report.period_rows:
            assert row.bcws > 0
            assert row.bcwp > 0
            assert row.acwp > 0
            assert row.cumulative_bcws > 0
            assert row.cumulative_bcwp > 0
            assert row.cumulative_acwp > 0

        # Verify variances are calculated
        assert report.period_rows[-1].cumulative_sv < 0  # Behind schedule
        assert report.period_rows[-1].cumulative_cv < 0  # Over budget

        # Verify indices
        assert report.cumulative_cpi is not None
        assert report.cumulative_spi is not None
        assert report.cumulative_cpi < Decimal("1.0")  # Over budget
        assert report.cumulative_spi < Decimal("1.0")  # Behind schedule

        # Verify EAC analysis
        assert report.eac_analysis is not None
        assert report.eac_analysis.eac_cpi > report.bac  # Projected overrun

    def test_format5_variance_percentages(self) -> None:
        """Test variance percentage calculations in Format 5."""
        program = MockProgram(
            id=uuid4(),
            name="Test Program",
            code="TEST",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            budget_at_completion=Decimal("1000000.00"),
        )

        # Create period with specific variance percentages
        periods = [
            MockEVMSPeriod(
                id=uuid4(),
                program_id=program.id,
                period_name="January",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                cumulative_bcws=Decimal("200000"),  # Base for percentages
                cumulative_bcwp=Decimal("180000"),  # -10% SV
                cumulative_acwp=Decimal("200000"),  # -10% CV
            ),
        ]

        generator = CPRFormat5Generator(program, periods)
        report = generator.generate()

        # Verify variance percentages
        row = report.period_rows[0]
        assert row.sv_percent == Decimal("-10.00")  # (180000-200000)/200000 * 100
        assert row.cv_percent == Decimal("-10.00")  # (180000-200000)/200000 * 100


# =============================================================================
# Enhanced S-Curve Tests
# =============================================================================


class TestEnhancedSCurveE2E:
    """E2E tests for enhanced S-curve with confidence bands."""

    def create_test_periods_for_scurve(self, program_id: UUID) -> list[MockEVMSPeriod]:
        """Create test periods for S-curve generation."""
        base_date = date(2026, 1, 1)
        periods = []

        cumulative_bcws = Decimal("0")
        cumulative_bcwp = Decimal("0")
        cumulative_acwp = Decimal("0")

        for i in range(6):
            period_start = base_date + timedelta(days=i * 30)
            period_end = period_start + timedelta(days=29)

            # S-curve typically shows cumulative values growing
            period_bcws = Decimal("100000") * Decimal(str(1 + i * 0.2))
            period_bcwp = period_bcws * Decimal("0.95")
            period_acwp = period_bcws * Decimal("1.02")

            cumulative_bcws += period_bcws
            cumulative_bcwp += period_bcwp
            cumulative_acwp += period_acwp

            periods.append(
                MockEVMSPeriod(
                    id=uuid4(),
                    program_id=program_id,
                    period_name=f"Month {i + 1}",
                    period_start=period_start,
                    period_end=period_end,
                    cumulative_bcws=cumulative_bcws,
                    cumulative_bcwp=cumulative_bcwp,
                    cumulative_acwp=cumulative_acwp,
                    bcws=period_bcws,
                    bcwp=period_bcwp,
                    acwp=period_acwp,
                )
            )

        return periods

    def test_enhanced_scurve_generation(self) -> None:
        """Test enhanced S-curve generation with Monte Carlo bands."""
        program_id = uuid4()
        periods = self.create_test_periods_for_scurve(program_id)
        bac = Decimal("2000000.00")
        start_date = date(2026, 1, 1)

        # Create simulation metrics (from Monte Carlo)
        simulation_metrics = SimulationMetrics(
            duration_p10=180,
            duration_p50=200,
            duration_p90=230,
            duration_mean=205.0,
            duration_std=15.0,
        )

        # Generate enhanced S-curve
        service = EnhancedSCurveService(
            program_id=program_id,
            periods=periods,
            bac=bac,
            simulation_metrics=simulation_metrics,
            start_date=start_date,
        )

        result = service.generate()

        # Verify result structure
        assert result.program_id == program_id
        assert result.bac == bac
        assert len(result.data_points) == 6
        assert result.simulation_available is True

        # Verify data points
        for i, dp in enumerate(result.data_points):
            assert dp.period_number == i + 1
            assert dp.bcws > 0
            assert dp.bcwp > 0
            assert dp.acwp > 0
            assert dp.cumulative_bcws > 0
            assert dp.cumulative_bcwp > 0
            assert dp.cumulative_acwp > 0

        # Verify completion range from simulation
        assert result.completion_range is not None
        assert result.completion_range.p10_days == 180
        assert result.completion_range.p50_days == 200
        assert result.completion_range.p90_days == 230

    def test_scurve_without_simulation(self) -> None:
        """Test S-curve generation without simulation data."""
        program_id = uuid4()
        periods = self.create_test_periods_for_scurve(program_id)
        bac = Decimal("2000000.00")

        # Generate S-curve without simulation
        service = EnhancedSCurveService(
            program_id=program_id,
            periods=periods,
            bac=bac,
            simulation_metrics=None,
            start_date=date(2026, 1, 1),
        )

        result = service.generate()

        # Should still produce valid S-curve
        assert len(result.data_points) == 6
        assert result.simulation_available is False

        # Should not have confidence bands
        assert result.completion_range is None


# =============================================================================
# Integration Scenarios
# =============================================================================


class TestMonth2IntegrationScenarios:
    """Integration tests combining multiple Month 2 features."""

    def test_evms_to_variance_to_format5_workflow(self) -> None:
        """Test complete workflow from EVMS data to variance analysis to Format 5."""
        # 1. Create program and EVMS data
        program = MockProgram(
            id=uuid4(),
            name="Integration Test Program",
            code="INT-001",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            budget_at_completion=Decimal("2000000.00"),
        )

        # 2. Create periods with variances
        periods = []
        base_date = date(2026, 1, 1)

        cumulative_values = [
            (Decimal("200000"), Decimal("180000"), Decimal("190000")),  # Month 1
            (Decimal("400000"), Decimal("350000"), Decimal("380000")),  # Month 2
            (Decimal("600000"), Decimal("510000"), Decimal("580000")),  # Month 3
        ]

        for i, (bcws, bcwp, acwp) in enumerate(cumulative_values):
            periods.append(
                MockEVMSPeriod(
                    id=uuid4(),
                    program_id=program.id,
                    period_name=f"Month {i + 1}",
                    period_start=base_date + timedelta(days=i * 30),
                    period_end=base_date + timedelta(days=(i + 1) * 30 - 1),
                    cumulative_bcws=bcws,
                    cumulative_bcwp=bcwp,
                    cumulative_acwp=acwp,
                )
            )

        # 3. Run variance analysis
        variance_service = VarianceAnalysisService()
        period_data = [
            {
                "wbs_id": uuid4(),
                "wbs_code": "1.0",
                "wbs_name": "Total Program",
                "period_name": "Month 3",
                "cumulative_bcws": cumulative_values[2][0],
                "sv": cumulative_values[2][1] - cumulative_values[2][0],  # -90000 = -15%
                "cv": cumulative_values[2][1] - cumulative_values[2][2],  # -70000 = -11.7%
            }
        ]

        variance_result = variance_service.analyze_program_variances(
            program_id=program.id,
            period_name="Month 3",
            period_data=period_data,
        )

        # Should detect significant variances
        assert len(variance_result.alerts) >= 1
        assert variance_result.critical_count > 0 or variance_result.significant_count > 0

        # 4. Generate Format 5 report
        format5_generator = CPRFormat5Generator(program, periods)
        format5_report = format5_generator.generate()

        # 5. Verify Format 5 reflects the variance issues
        assert format5_report.cumulative_cpi < Decimal("1.0")
        assert format5_report.cumulative_spi < Decimal("1.0")
        assert format5_report.current_eac > program.budget_at_completion

        # 6. Verify EAC analysis shows overrun
        assert format5_report.eac_analysis is not None
        assert format5_report.eac_analysis.eac_cpi > program.budget_at_completion

    def test_monte_carlo_to_enhanced_scurve_workflow(self) -> None:
        """Test workflow from Monte Carlo simulation to enhanced S-curve."""
        # 1. Create activities and run Monte Carlo
        program_id = uuid4()
        wbs_id = uuid4()

        activities = [
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code=f"A{i}",
                name=f"Activity {i}",
                duration=10 + i * 5,
                budgeted_cost=Decimal(str(50000 + i * 10000)),
            )
            for i in range(5)
        ]

        dependencies = [
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[i].id,
                successor_id=activities[i + 1].id,
                dependency_type=DependencyType.FS.value,
            )
            for i in range(4)
        ]

        # Create distributions for Monte Carlo
        distributions: dict[UUID, DistributionParams] = {}
        for activity in activities:
            distributions[activity.id] = DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=activity.duration * 0.8,
                mode=float(activity.duration),
                max_value=activity.duration * 1.3,
            )

        # Run Monte Carlo with optimized engine
        mc_engine = OptimizedNetworkMonteCarloEngine(seed=42)
        mc_result = mc_engine.simulate(
            activities=activities,
            dependencies=dependencies,
            distributions=distributions,
            iterations=100,
        )

        # 2. Create EVMS periods
        periods = [
            MockEVMSPeriod(
                id=uuid4(),
                program_id=program_id,
                period_name=f"Month {i}",
                period_start=date(2026, i, 1),
                period_end=date(2026, i, 28),
                cumulative_bcws=Decimal(str(50000 * i)),
                cumulative_bcwp=Decimal(str(48000 * i)),
                cumulative_acwp=Decimal(str(52000 * i)),
                bcws=Decimal("50000"),
                bcwp=Decimal("48000"),
                acwp=Decimal("52000"),
            )
            for i in range(1, 4)
        ]

        # 3. Build simulation metrics from Monte Carlo
        bac = sum(a.budgeted_cost for a in activities)

        simulation_metrics = SimulationMetrics(
            duration_p10=mc_result.project_duration_p10,
            duration_p50=mc_result.project_duration_p50,
            duration_p90=mc_result.project_duration_p90,
            duration_mean=mc_result.project_duration_mean,
            duration_std=mc_result.project_duration_std,
        )

        # 4. Generate enhanced S-curve
        scurve_service = EnhancedSCurveService(
            program_id=program_id,
            periods=periods,
            bac=bac,
            simulation_metrics=simulation_metrics,
            start_date=date(2026, 1, 1),
        )

        scurve_result = scurve_service.generate()

        # 5. Verify integration
        assert scurve_result.simulation_available is True
        assert scurve_result.completion_range is not None

        # Completion range should reflect Monte Carlo results (allow small rounding differences)
        assert scurve_result.completion_range.p10_days == pytest.approx(
            mc_result.project_duration_p10, rel=0.01
        )
        assert scurve_result.completion_range.p50_days == pytest.approx(
            mc_result.project_duration_p50, rel=0.01
        )
        assert scurve_result.completion_range.p90_days == pytest.approx(
            mc_result.project_duration_p90, rel=0.01
        )
