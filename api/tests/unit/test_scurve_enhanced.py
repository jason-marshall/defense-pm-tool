"""Unit tests for Enhanced S-Curve service."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from src.services.scurve_enhanced import (
    CompletionDateRange,
    EACRange,
    EnhancedSCurveResponse,
    EnhancedSCurveService,
    SCurveDataPoint,
    SimulationMetrics,
    build_simulation_metrics_from_result,
)


class TestSCurveDataPoint:
    """Tests for SCurveDataPoint dataclass."""

    def test_create_data_point(self):
        """Should create data point with all fields."""
        dp = SCurveDataPoint(
            period_number=1,
            period_date=date(2026, 1, 31),
            period_name="January 2026",
            bcws=Decimal("50000"),
            bcwp=Decimal("45000"),
            acwp=Decimal("48000"),
            cumulative_bcws=Decimal("50000"),
            cumulative_bcwp=Decimal("45000"),
            cumulative_acwp=Decimal("48000"),
        )

        assert dp.period_number == 1
        assert dp.period_date == date(2026, 1, 31)
        assert dp.bcws == Decimal("50000")
        assert dp.is_forecast is False

    def test_create_forecast_data_point(self):
        """Should create forecast data point with confidence bands."""
        dp = SCurveDataPoint(
            period_number=5,
            period_date=date(2026, 5, 31),
            period_name="May 2026",
            bcws=Decimal("100000"),
            bcwp=Decimal("0"),
            acwp=Decimal("0"),
            cumulative_bcws=Decimal("250000"),
            cumulative_bcwp=Decimal("200000"),
            cumulative_acwp=Decimal("210000"),
            is_forecast=True,
            forecast_bcwp_p10=Decimal("220000"),
            forecast_bcwp_p50=Decimal("240000"),
            forecast_bcwp_p90=Decimal("260000"),
        )

        assert dp.is_forecast is True
        assert dp.forecast_bcwp_p10 == Decimal("220000")
        assert dp.forecast_bcwp_p50 == Decimal("240000")
        assert dp.forecast_bcwp_p90 == Decimal("260000")


class TestEACRange:
    """Tests for EACRange dataclass."""

    def test_create_eac_range(self):
        """Should create EAC range with percentiles."""
        eac_range = EACRange(
            p10=Decimal("950000"),
            p50=Decimal("1000000"),
            p90=Decimal("1100000"),
            method="simulation_adjusted",
        )

        assert eac_range.p10 == Decimal("950000")
        assert eac_range.p50 == Decimal("1000000")
        assert eac_range.p90 == Decimal("1100000")
        assert eac_range.method == "simulation_adjusted"

    def test_default_method(self):
        """Should default to 'simulation' method."""
        eac_range = EACRange(
            p10=Decimal("100"),
            p50=Decimal("110"),
            p90=Decimal("120"),
        )

        assert eac_range.method == "simulation"


class TestCompletionDateRange:
    """Tests for CompletionDateRange dataclass."""

    def test_create_completion_range_days_only(self):
        """Should create completion range with days only."""
        completion = CompletionDateRange(
            p10_days=85.0,
            p50_days=95.0,
            p90_days=110.0,
        )

        assert completion.p10_days == 85.0
        assert completion.p50_days == 95.0
        assert completion.p90_days == 110.0
        assert completion.p10_date is None
        assert completion.p50_date is None
        assert completion.p90_date is None

    def test_create_completion_range_with_dates(self):
        """Should create completion range with dates."""
        completion = CompletionDateRange(
            p10_days=85.0,
            p50_days=95.0,
            p90_days=110.0,
            p10_date=date(2026, 4, 15),
            p50_date=date(2026, 4, 25),
            p90_date=date(2026, 5, 10),
        )

        assert completion.p10_date == date(2026, 4, 15)
        assert completion.p50_date == date(2026, 4, 25)
        assert completion.p90_date == date(2026, 5, 10)


class TestSimulationMetrics:
    """Tests for SimulationMetrics dataclass."""

    def test_create_simulation_metrics(self):
        """Should create simulation metrics."""
        metrics = SimulationMetrics(
            duration_p10=85.0,
            duration_p50=95.0,
            duration_p90=110.0,
            duration_mean=96.5,
            duration_std=12.3,
        )

        assert metrics.duration_p10 == 85.0
        assert metrics.duration_p50 == 95.0
        assert metrics.duration_p90 == 110.0
        assert metrics.duration_mean == 96.5
        assert metrics.duration_std == 12.3


class TestEnhancedSCurveResponse:
    """Tests for EnhancedSCurveResponse dataclass."""

    def test_create_response_minimal(self):
        """Should create response with minimal fields."""
        response = EnhancedSCurveResponse(
            program_id=uuid4(),
            data_points=[],
            bac=Decimal("1000000"),
            current_period=0,
            percent_complete=Decimal("0"),
        )

        assert response.bac == Decimal("1000000")
        assert response.current_period == 0
        assert response.eac_range is None
        assert response.completion_range is None
        assert response.simulation_available is False

    def test_create_response_with_simulation(self):
        """Should create response with simulation data."""
        response = EnhancedSCurveResponse(
            program_id=uuid4(),
            data_points=[],
            bac=Decimal("1000000"),
            current_period=5,
            percent_complete=Decimal("48.50"),
            eac_range=EACRange(
                p10=Decimal("950000"),
                p50=Decimal("1000000"),
                p90=Decimal("1100000"),
            ),
            completion_range=CompletionDateRange(
                p10_days=85.0,
                p50_days=95.0,
                p90_days=110.0,
            ),
            simulation_available=True,
        )

        assert response.simulation_available is True
        assert response.eac_range is not None
        assert response.completion_range is not None


class MockPeriod:
    """Mock EVMS period for testing."""

    def __init__(
        self,
        period_end: date,
        period_name: str,
        bcws: Decimal = Decimal("0"),
        bcwp: Decimal = Decimal("0"),
        acwp: Decimal = Decimal("0"),
        cumulative_bcws: Decimal = Decimal("0"),
        cumulative_bcwp: Decimal = Decimal("0"),
        cumulative_acwp: Decimal = Decimal("0"),
    ):
        self.period_end = period_end
        self.period_name = period_name
        self.bcws = bcws
        self.bcwp = bcwp
        self.acwp = acwp
        self.cumulative_bcws = cumulative_bcws
        self.cumulative_bcwp = cumulative_bcwp
        self.cumulative_acwp = cumulative_acwp


class TestEnhancedSCurveService:
    """Tests for EnhancedSCurveService."""

    def test_generate_empty_periods(self):
        """Should handle empty periods list."""
        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=[],
            bac=Decimal("1000000"),
        )

        result = service.generate()

        assert len(result.data_points) == 0
        assert result.current_period == 0
        assert result.percent_complete == Decimal("0")
        assert result.simulation_available is False

    def test_generate_with_periods(self):
        """Should generate S-curve data from periods."""
        periods = [
            MockPeriod(
                period_end=date(2026, 1, 31),
                period_name="January 2026",
                bcws=Decimal("50000"),
                bcwp=Decimal("45000"),
                acwp=Decimal("48000"),
                cumulative_bcws=Decimal("50000"),
                cumulative_bcwp=Decimal("45000"),
                cumulative_acwp=Decimal("48000"),
            ),
            MockPeriod(
                period_end=date(2026, 2, 28),
                period_name="February 2026",
                bcws=Decimal("50000"),
                bcwp=Decimal("55000"),
                acwp=Decimal("52000"),
                cumulative_bcws=Decimal("100000"),
                cumulative_bcwp=Decimal("100000"),
                cumulative_acwp=Decimal("100000"),
            ),
        ]

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=periods,
            bac=Decimal("500000"),
        )

        result = service.generate()

        assert len(result.data_points) == 2
        assert result.current_period == 2
        assert result.percent_complete == Decimal("20.00")

    def test_generate_with_simulation_metrics(self):
        """Should include simulation data when available."""
        periods = [
            MockPeriod(
                period_end=date(2026, 1, 31),
                period_name="January 2026",
                cumulative_bcws=Decimal("100000"),
                cumulative_bcwp=Decimal("80000"),
                cumulative_acwp=Decimal("90000"),
            ),
        ]

        simulation = SimulationMetrics(
            duration_p10=85.0,
            duration_p50=95.0,
            duration_p90=110.0,
            duration_mean=96.5,
            duration_std=12.3,
        )

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=periods,
            bac=Decimal("500000"),
            simulation_metrics=simulation,
        )

        result = service.generate()

        assert result.simulation_available is True
        assert result.eac_range is not None
        assert result.completion_range is not None

    def test_generate_with_start_date(self):
        """Should calculate completion dates when start date provided."""
        periods = [
            MockPeriod(
                period_end=date(2026, 1, 31),
                period_name="January 2026",
                cumulative_bcws=Decimal("100000"),
                cumulative_bcwp=Decimal("80000"),
                cumulative_acwp=Decimal("90000"),
            ),
        ]

        simulation = SimulationMetrics(
            duration_p10=85.0,
            duration_p50=95.0,
            duration_p90=110.0,
            duration_mean=96.5,
            duration_std=12.3,
        )

        start_date = date(2026, 1, 1)

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=periods,
            bac=Decimal("500000"),
            simulation_metrics=simulation,
            start_date=start_date,
        )

        result = service.generate()

        assert result.completion_range is not None
        assert result.completion_range.p10_date == start_date + timedelta(days=85)
        assert result.completion_range.p50_date == start_date + timedelta(days=95)
        assert result.completion_range.p90_date == start_date + timedelta(days=110)

    def test_calculate_percent_complete_zero_bac(self):
        """Should return 0% when BAC is zero."""
        periods = [
            MockPeriod(
                period_end=date(2026, 1, 31),
                period_name="January 2026",
                cumulative_bcwp=Decimal("50000"),
            ),
        ]

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=periods,
            bac=Decimal("0"),
        )

        result = service.generate()

        assert result.percent_complete == Decimal("0")

    def test_eac_range_no_progress(self):
        """Should return BAC when no progress made."""
        periods = [
            MockPeriod(
                period_end=date(2026, 1, 31),
                period_name="January 2026",
                cumulative_bcws=Decimal("100000"),
                cumulative_bcwp=Decimal("0"),
                cumulative_acwp=Decimal("0"),
            ),
        ]

        simulation = SimulationMetrics(
            duration_p10=85.0,
            duration_p50=95.0,
            duration_p90=110.0,
            duration_mean=96.5,
            duration_std=12.3,
        )

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=periods,
            bac=Decimal("500000"),
            simulation_metrics=simulation,
        )

        result = service.generate()

        assert result.eac_range is not None
        assert result.eac_range.p10 == Decimal("500000")
        assert result.eac_range.p50 == Decimal("500000")
        assert result.eac_range.p90 == Decimal("500000")
        assert result.eac_range.method == "no_progress"

    def test_eac_range_zero_bac(self):
        """Should return None for EAC range when BAC is zero."""
        periods = [
            MockPeriod(
                period_end=date(2026, 1, 31),
                period_name="January 2026",
                cumulative_bcwp=Decimal("50000"),
                cumulative_acwp=Decimal("50000"),
            ),
        ]

        simulation = SimulationMetrics(
            duration_p10=85.0,
            duration_p50=95.0,
            duration_p90=110.0,
            duration_mean=96.5,
            duration_std=12.3,
        )

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=periods,
            bac=Decimal("0"),
            simulation_metrics=simulation,
        )

        result = service.generate()

        assert result.eac_range is None

    def test_eac_range_with_over_budget(self):
        """Should calculate EAC range when over budget (CPI < 1)."""
        periods = [
            MockPeriod(
                period_end=date(2026, 1, 31),
                period_name="January 2026",
                cumulative_bcws=Decimal("100000"),
                cumulative_bcwp=Decimal("80000"),
                cumulative_acwp=Decimal("100000"),  # CPI = 0.8
            ),
        ]

        simulation = SimulationMetrics(
            duration_p10=85.0,
            duration_p50=95.0,
            duration_p90=110.0,
            duration_mean=100.0,
            duration_std=10.0,  # 10% uncertainty
        )

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=periods,
            bac=Decimal("500000"),
            simulation_metrics=simulation,
        )

        result = service.generate()

        assert result.eac_range is not None
        # CPI = 0.8, so EAC base = 100000 + (500000-80000)/0.8 = 625000
        # With 10% uncertainty and 84% remaining work
        assert result.eac_range.p50 > Decimal("500000")  # Over budget

    def test_eac_range_zero_duration_mean(self):
        """Should use default uncertainty when duration mean is zero."""
        periods = [
            MockPeriod(
                period_end=date(2026, 1, 31),
                period_name="January 2026",
                cumulative_bcws=Decimal("100000"),
                cumulative_bcwp=Decimal("50000"),
                cumulative_acwp=Decimal("50000"),
            ),
        ]

        simulation = SimulationMetrics(
            duration_p10=0.0,
            duration_p50=0.0,
            duration_p90=0.0,
            duration_mean=0.0,  # Zero mean
            duration_std=0.0,
        )

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=periods,
            bac=Decimal("500000"),
            simulation_metrics=simulation,
        )

        result = service.generate()

        # Should still calculate EAC range with default 10% uncertainty
        assert result.eac_range is not None

    def test_completion_range_without_simulation(self):
        """Should return None for completion range without simulation."""
        periods = [
            MockPeriod(
                period_end=date(2026, 1, 31),
                period_name="January 2026",
            ),
        ]

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=periods,
            bac=Decimal("500000"),
            simulation_metrics=None,
        )

        result = service.generate()

        assert result.completion_range is None

    def test_data_points_sorted_by_date(self):
        """Should sort periods by end date."""
        # Create periods out of order
        periods = [
            MockPeriod(
                period_end=date(2026, 3, 31),
                period_name="March 2026",
            ),
            MockPeriod(
                period_end=date(2026, 1, 31),
                period_name="January 2026",
            ),
            MockPeriod(
                period_end=date(2026, 2, 28),
                period_name="February 2026",
            ),
        ]

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=periods,
            bac=Decimal("500000"),
        )

        result = service.generate()

        # Should be sorted by date
        assert result.data_points[0].period_date == date(2026, 1, 31)
        assert result.data_points[1].period_date == date(2026, 2, 28)
        assert result.data_points[2].period_date == date(2026, 3, 31)


class TestBuildSimulationMetricsFromResult:
    """Tests for build_simulation_metrics_from_result helper."""

    def test_build_from_valid_result(self):
        """Should build metrics from valid result."""

        class MockResult:
            def __init__(self):
                self.duration_results = {
                    "p10": 85.0,
                    "p50": 95.0,
                    "p90": 110.0,
                    "mean": 96.5,
                    "std": 12.3,
                }

        result = build_simulation_metrics_from_result(MockResult())

        assert result is not None
        assert result.duration_p10 == 85.0
        assert result.duration_p50 == 95.0
        assert result.duration_p90 == 110.0
        assert result.duration_mean == 96.5
        assert result.duration_std == 12.3

    def test_build_from_none_result(self):
        """Should return None for None result."""
        result = build_simulation_metrics_from_result(None)
        assert result is None

    def test_build_from_result_without_duration_results(self):
        """Should return None when duration_results missing."""

        class MockResult:
            duration_results = None

        result = build_simulation_metrics_from_result(MockResult())
        assert result is None

    def test_build_from_result_with_missing_keys(self):
        """Should handle missing keys with defaults."""

        class MockResult:
            def __init__(self):
                self.duration_results = {
                    "p10": 85.0,
                    "p50": 95.0,
                    # Missing p90, mean, std
                }

        result = build_simulation_metrics_from_result(MockResult())

        assert result is not None
        assert result.duration_p10 == 85.0
        assert result.duration_p50 == 95.0
        assert result.duration_p90 == 0.0  # Default
        assert result.duration_mean == 0.0  # Default
        assert result.duration_std == 1.0  # Default

    def test_build_from_result_with_invalid_values(self):
        """Should return None for invalid values."""

        class MockResult:
            def __init__(self):
                self.duration_results = {
                    "p10": "not_a_number",
                    "p50": 95.0,
                }

        result = build_simulation_metrics_from_result(MockResult())
        assert result is None

    def test_build_handles_no_attribute(self):
        """Should return None when result has no duration_results attr."""

        class MockResult:
            pass

        result = build_simulation_metrics_from_result(MockResult())
        assert result is None


class TestEnhancedSCurveServiceEdgeCases:
    """Additional edge case tests for EnhancedSCurveService."""

    def test_eac_range_with_simulation_but_no_periods(self):
        """Should return None for EAC range when simulation exists but no periods."""
        simulation = SimulationMetrics(
            duration_p10=85.0,
            duration_p50=95.0,
            duration_p90=110.0,
            duration_mean=96.5,
            duration_std=12.3,
        )

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=[],  # No periods
            bac=Decimal("500000"),
            simulation_metrics=simulation,
        )

        result = service.generate()

        # EAC range should be None because no periods
        assert result.eac_range is None

    def test_completion_range_explicit_none_simulation(self):
        """Should return None for completion range when simulation is explicitly None."""
        periods = [
            MockPeriod(
                period_end=date(2026, 1, 31),
                period_name="January 2026",
                cumulative_bcws=Decimal("100000"),
                cumulative_bcwp=Decimal("80000"),
                cumulative_acwp=Decimal("90000"),
            ),
        ]

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=periods,
            bac=Decimal("500000"),
            simulation_metrics=None,  # Explicitly None
        )

        # Call the private method directly to ensure coverage
        completion_range = service._calculate_completion_range()

        assert completion_range is None

    def test_periods_with_none_values(self):
        """Should handle periods with None values gracefully."""

        class PeriodWithNones:
            period_end = date(2026, 1, 31)
            period_name = "January 2026"
            bcws = None
            bcwp = None
            acwp = None
            cumulative_bcws = None
            cumulative_bcwp = None
            cumulative_acwp = None

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=[PeriodWithNones()],
            bac=Decimal("500000"),
        )

        result = service.generate()

        assert len(result.data_points) == 1
        assert result.data_points[0].bcws == Decimal("0")
        assert result.data_points[0].bcwp == Decimal("0")
        assert result.data_points[0].acwp == Decimal("0")

    def test_eac_range_calculation_with_zero_acwp(self):
        """Should handle zero ACWP (CPI defaults to 1.0)."""
        periods = [
            MockPeriod(
                period_end=date(2026, 1, 31),
                period_name="January 2026",
                cumulative_bcws=Decimal("100000"),
                cumulative_bcwp=Decimal("50000"),
                cumulative_acwp=Decimal("0"),  # Zero ACWP
            ),
        ]

        simulation = SimulationMetrics(
            duration_p10=85.0,
            duration_p50=95.0,
            duration_p90=110.0,
            duration_mean=96.5,
            duration_std=12.3,
        )

        service = EnhancedSCurveService(
            program_id=uuid4(),
            periods=periods,
            bac=Decimal("500000"),
            simulation_metrics=simulation,
        )

        result = service.generate()

        # Should still calculate EAC range with CPI=1.0 (default)
        assert result.eac_range is not None
