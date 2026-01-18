"""Comprehensive tests for CPR Format 5 (EVMS) report generator.

Tests all 6 EAC methods, variance explanations, and MR tracking
per DFARS requirements and EVMS GL 27.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.schemas.cpr_format5 import (
    CPRFormat5Report,
    Format5ExportConfig,
)
from src.services.cpr_format5_generator import CPRFormat5Generator, generate_format5_report


# Mock classes for testing
@dataclass
class MockProgram:
    """Mock Program for testing."""

    id: UUID
    code: str
    name: str
    contract_number: str | None
    budget_at_completion: Decimal


@dataclass
class MockEVMSPeriod:
    """Mock EVMS Period for testing."""

    id: UUID
    program_id: UUID
    period_name: str
    period_start: date
    period_end: date
    cumulative_bcws: Decimal
    cumulative_bcwp: Decimal
    cumulative_acwp: Decimal

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
class MockWBS:
    """Mock WBS Element for testing."""

    id: UUID
    wbs_code: str
    name: str


@dataclass
class MockVarianceExplanation:
    """Mock VarianceExplanation model for testing."""

    id: UUID
    program_id: UUID
    wbs: MockWBS | None
    period: MockEVMSPeriod | None
    variance_type: str
    variance_amount: Decimal
    variance_percent: Decimal
    explanation: str
    corrective_action: str | None
    expected_resolution: date | None


@dataclass
class MockManagementReserveLog:
    """Mock ManagementReserveLog model for testing."""

    id: UUID
    program_id: UUID
    period: MockEVMSPeriod | None
    beginning_mr: Decimal
    changes_in: Decimal
    changes_out: Decimal
    ending_mr: Decimal
    reason: str | None


class TestEACAnalysisCalculations:
    """Tests for all 6 EAC calculation methods."""

    @pytest.fixture
    def program(self) -> MockProgram:
        """Create test program with BAC of $1,000,000."""
        return MockProgram(
            id=uuid4(),
            code="TEST-001",
            name="Test Program",
            contract_number="N00024-26-C-0001",
            budget_at_completion=Decimal("1000000.00"),
        )

    @pytest.fixture
    def healthy_periods(self, program: MockProgram) -> list[MockEVMSPeriod]:
        """Create periods for a healthy project (CPI=1.0, SPI=1.0)."""
        return [
            MockEVMSPeriod(
                id=uuid4(),
                program_id=program.id,
                period_name="January 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                cumulative_bcws=Decimal("100000.00"),
                cumulative_bcwp=Decimal("100000.00"),
                cumulative_acwp=Decimal("100000.00"),
            )
        ]

    @pytest.fixture
    def troubled_periods(self, program: MockProgram) -> list[MockEVMSPeriod]:
        """Create periods for a troubled project (CPI=0.85, SPI=0.80)."""
        return [
            MockEVMSPeriod(
                id=uuid4(),
                program_id=program.id,
                period_name="January 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                cumulative_bcws=Decimal("500000.00"),
                cumulative_bcwp=Decimal("400000.00"),  # SPI = 0.80
                cumulative_acwp=Decimal("470588.24"),  # CPI = 0.85
            )
        ]

    def test_eac_analysis_all_methods_present(
        self, program: MockProgram, healthy_periods: list[MockEVMSPeriod]
    ) -> None:
        """Should calculate all 6 EAC methods."""
        generator = CPRFormat5Generator(
            program=program,
            periods=healthy_periods,
        )
        report = generator.generate()

        assert report.eac_analysis is not None
        eac = report.eac_analysis

        # All 6 methods should be present
        assert eac.eac_cpi is not None
        assert eac.eac_spi is not None
        assert eac.eac_composite is not None
        assert eac.eac_typical is not None
        assert eac.eac_atypical is not None
        # Management EAC is None without manager_etc
        assert eac.eac_management is None

        # Comparison metrics
        assert eac.eac_range_low is not None
        assert eac.eac_range_high is not None
        assert eac.eac_average is not None

        # Selection
        assert eac.eac_selected is not None
        assert eac.selection_rationale is not None

    def test_eac_cpi_method_calculation(
        self, program: MockProgram, troubled_periods: list[MockEVMSPeriod]
    ) -> None:
        """EAC CPI should equal BAC / CPI."""
        generator = CPRFormat5Generator(
            program=program,
            periods=troubled_periods,
        )
        report = generator.generate()

        # CPI = 400000 / 470588.24 = 0.85
        # EAC CPI = 1000000 / 0.85 = 1176470.59
        assert report.eac_analysis is not None
        eac_cpi = report.eac_analysis.eac_cpi
        assert eac_cpi > Decimal("1170000")
        assert eac_cpi < Decimal("1180000")

    def test_eac_spi_method_calculation(
        self, program: MockProgram, troubled_periods: list[MockEVMSPeriod]
    ) -> None:
        """EAC SPI should equal BAC / SPI."""
        generator = CPRFormat5Generator(
            program=program,
            periods=troubled_periods,
        )
        report = generator.generate()

        # SPI = 400000 / 500000 = 0.80
        # EAC SPI = 1000000 / 0.80 = 1250000
        assert report.eac_analysis is not None
        eac_spi = report.eac_analysis.eac_spi
        assert eac_spi == Decimal("1250000.00")

    def test_eac_composite_method_calculation(
        self, program: MockProgram, troubled_periods: list[MockEVMSPeriod]
    ) -> None:
        """EAC Composite should equal ACWP + (BAC - BCWP) / (CPI * SPI)."""
        generator = CPRFormat5Generator(
            program=program,
            periods=troubled_periods,
        )
        report = generator.generate()

        # CPI = 0.85, SPI = 0.80, CPI*SPI = 0.68
        # Remaining = 1000000 - 400000 = 600000
        # EAC = 470588.24 + (600000 / 0.68) = 470588.24 + 882352.94 = 1352941.18
        assert report.eac_analysis is not None
        eac_composite = report.eac_analysis.eac_composite
        assert eac_composite > Decimal("1350000")
        assert eac_composite < Decimal("1360000")

    def test_eac_typical_method_calculation(
        self, program: MockProgram, troubled_periods: list[MockEVMSPeriod]
    ) -> None:
        """EAC Typical should equal ACWP + (BAC - BCWP)."""
        generator = CPRFormat5Generator(
            program=program,
            periods=troubled_periods,
        )
        report = generator.generate()

        # EAC Typical = 470588.24 + (1000000 - 400000) = 1070588.24
        assert report.eac_analysis is not None
        eac_typical = report.eac_analysis.eac_typical
        expected = Decimal("470588.24") + Decimal("600000.00")
        assert eac_typical == expected.quantize(Decimal("0.01"))

    def test_eac_atypical_method_calculation(
        self, program: MockProgram, troubled_periods: list[MockEVMSPeriod]
    ) -> None:
        """EAC Atypical should equal ACWP + (BAC - BCWP) / CPI."""
        generator = CPRFormat5Generator(
            program=program,
            periods=troubled_periods,
        )
        report = generator.generate()

        # CPI = 0.85
        # EAC Atypical = 470588.24 + (600000 / 0.85) = 470588.24 + 705882.35 = 1176470.59
        assert report.eac_analysis is not None
        eac_atypical = report.eac_analysis.eac_atypical
        assert eac_atypical > Decimal("1170000")
        assert eac_atypical < Decimal("1180000")

    def test_eac_management_with_manager_etc(
        self, program: MockProgram, troubled_periods: list[MockEVMSPeriod]
    ) -> None:
        """EAC Management should equal ACWP + Manager ETC when provided."""
        manager_etc = Decimal("700000.00")
        generator = CPRFormat5Generator(
            program=program,
            periods=troubled_periods,
            manager_etc=manager_etc,
        )
        report = generator.generate()

        # EAC Management = 470588.24 + 700000 = 1170588.24
        assert report.eac_analysis is not None
        assert report.eac_analysis.eac_management is not None
        expected = Decimal("470588.24") + manager_etc
        assert report.eac_analysis.eac_management == expected.quantize(Decimal("0.01"))

    def test_eac_selection_uses_composite_for_troubled_project(
        self, program: MockProgram, troubled_periods: list[MockEVMSPeriod]
    ) -> None:
        """Should select composite method when CPI < 0.90 and SPI < 0.90."""
        generator = CPRFormat5Generator(
            program=program,
            periods=troubled_periods,
        )
        report = generator.generate()

        assert report.eac_analysis is not None
        assert report.eac_analysis.eac_selected == report.eac_analysis.eac_composite
        assert "Composite method" in report.eac_analysis.selection_rationale

    def test_eac_selection_uses_cpi_for_healthy_project(
        self, program: MockProgram, healthy_periods: list[MockEVMSPeriod]
    ) -> None:
        """Should select CPI method for healthy projects."""
        generator = CPRFormat5Generator(
            program=program,
            periods=healthy_periods,
        )
        report = generator.generate()

        assert report.eac_analysis is not None
        assert report.eac_analysis.eac_selected == report.eac_analysis.eac_cpi
        assert "CPI method" in report.eac_analysis.selection_rationale

    def test_eac_range_calculation(
        self, program: MockProgram, troubled_periods: list[MockEVMSPeriod]
    ) -> None:
        """Should calculate min, max, and average EAC correctly."""
        generator = CPRFormat5Generator(
            program=program,
            periods=troubled_periods,
        )
        report = generator.generate()

        assert report.eac_analysis is not None
        eac = report.eac_analysis

        # Range low should be minimum of all methods
        all_eacs = [eac.eac_cpi, eac.eac_composite, eac.eac_typical, eac.eac_atypical]
        if eac.eac_spi:
            all_eacs.append(eac.eac_spi)

        assert eac.eac_range_low == min(all_eacs)
        assert eac.eac_range_high == max(all_eacs)

        # Average should be sum / count
        expected_avg = sum(all_eacs) / len(all_eacs)
        assert eac.eac_average == expected_avg.quantize(Decimal("0.01"))


class TestVarianceExplanations:
    """Tests for variance explanation handling."""

    @pytest.fixture
    def program(self) -> MockProgram:
        """Create test program."""
        return MockProgram(
            id=uuid4(),
            code="VAR-001",
            name="Variance Test Program",
            contract_number="N00024-26-C-0002",
            budget_at_completion=Decimal("1000000.00"),
        )

    @pytest.fixture
    def periods(self, program: MockProgram) -> list[MockEVMSPeriod]:
        """Create test periods."""
        return [
            MockEVMSPeriod(
                id=uuid4(),
                program_id=program.id,
                period_name="January 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                cumulative_bcws=Decimal("100000.00"),
                cumulative_bcwp=Decimal("85000.00"),
                cumulative_acwp=Decimal("100000.00"),
            )
        ]

    @pytest.fixture
    def variance_explanations(self, program: MockProgram) -> list[MockVarianceExplanation]:
        """Create test variance explanations."""
        wbs = MockWBS(id=uuid4(), wbs_code="1.1", name="Engineering")
        return [
            MockVarianceExplanation(
                id=uuid4(),
                program_id=program.id,
                wbs=wbs,
                period=None,
                variance_type="schedule",
                variance_amount=Decimal("-15000.00"),
                variance_percent=Decimal("-15.00"),
                explanation="Requirements changes delayed engineering start",
                corrective_action="Fast-track remaining work packages",
                expected_resolution=date(2026, 3, 31),
            ),
            MockVarianceExplanation(
                id=uuid4(),
                program_id=program.id,
                wbs=wbs,
                period=None,
                variance_type="cost",
                variance_amount=Decimal("-12000.00"),
                variance_percent=Decimal("-12.00"),
                explanation="Labor rate increases above estimate",
                corrective_action="Renegotiate subcontract terms",
                expected_resolution=date(2026, 2, 28),
            ),
            # Small variance below threshold
            MockVarianceExplanation(
                id=uuid4(),
                program_id=program.id,
                wbs=None,
                period=None,
                variance_type="schedule",
                variance_amount=Decimal("-5000.00"),
                variance_percent=Decimal("-5.00"),  # Below 10% threshold
                explanation="Minor delay in material delivery",
                corrective_action=None,
                expected_resolution=None,
            ),
        ]

    def test_variance_explanations_included_when_enabled(
        self,
        program: MockProgram,
        periods: list[MockEVMSPeriod],
        variance_explanations: list[MockVarianceExplanation],
    ) -> None:
        """Should include variance explanations when enabled."""
        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
            variance_explanations=variance_explanations,
            config=Format5ExportConfig(include_explanations=True),
        )
        report = generator.generate()

        # Should have 2 explanations (above 10% threshold)
        assert len(report.variance_explanations) == 2

    def test_variance_explanations_excluded_when_disabled(
        self,
        program: MockProgram,
        periods: list[MockEVMSPeriod],
        variance_explanations: list[MockVarianceExplanation],
    ) -> None:
        """Should exclude variance explanations when disabled."""
        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
            variance_explanations=variance_explanations,
            config=Format5ExportConfig(include_explanations=False),
        )
        report = generator.generate()

        assert len(report.variance_explanations) == 0

    def test_variance_threshold_filtering(
        self,
        program: MockProgram,
        periods: list[MockEVMSPeriod],
        variance_explanations: list[MockVarianceExplanation],
    ) -> None:
        """Should filter variances below threshold."""
        # Lower threshold to 5%
        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
            variance_explanations=variance_explanations,
            config=Format5ExportConfig(variance_threshold_percent=Decimal("5")),
        )
        report = generator.generate()

        # All 3 should be included (all >= 5%)
        assert len(report.variance_explanations) == 3

    def test_variance_explanations_sorted_by_percent(
        self,
        program: MockProgram,
        periods: list[MockEVMSPeriod],
        variance_explanations: list[MockVarianceExplanation],
    ) -> None:
        """Should sort variance explanations by absolute percent descending."""
        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
            variance_explanations=variance_explanations,
        )
        report = generator.generate()

        percents = [abs(ve.variance_percent) for ve in report.variance_explanations]
        assert percents == sorted(percents, reverse=True)

    def test_variance_explanation_fields(
        self,
        program: MockProgram,
        periods: list[MockEVMSPeriod],
        variance_explanations: list[MockVarianceExplanation],
    ) -> None:
        """Should include all variance explanation fields."""
        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
            variance_explanations=variance_explanations,
        )
        report = generator.generate()

        ve = report.variance_explanations[0]  # -15% variance
        assert ve.wbs_code == "1.1"
        assert ve.wbs_name == "Engineering"
        assert ve.variance_type == "schedule"
        assert ve.variance_amount == Decimal("-15000.00")
        assert ve.variance_percent == Decimal("-15.00")
        assert "Requirements changes" in ve.explanation
        assert "Fast-track" in ve.corrective_action
        assert ve.expected_resolution_date == date(2026, 3, 31)


class TestManagementReserveTracking:
    """Tests for Management Reserve (MR) tracking."""

    @pytest.fixture
    def program(self) -> MockProgram:
        """Create test program."""
        return MockProgram(
            id=uuid4(),
            code="MR-001",
            name="MR Test Program",
            contract_number="N00024-26-C-0003",
            budget_at_completion=Decimal("1000000.00"),
        )

    @pytest.fixture
    def periods(self, program: MockProgram) -> list[MockEVMSPeriod]:
        """Create test periods."""
        period1 = MockEVMSPeriod(
            id=uuid4(),
            program_id=program.id,
            period_name="January 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            cumulative_bcws=Decimal("100000.00"),
            cumulative_bcwp=Decimal("100000.00"),
            cumulative_acwp=Decimal("100000.00"),
        )
        period2 = MockEVMSPeriod(
            id=uuid4(),
            program_id=program.id,
            period_name="February 2026",
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28),
            cumulative_bcws=Decimal("200000.00"),
            cumulative_bcwp=Decimal("200000.00"),
            cumulative_acwp=Decimal("200000.00"),
        )
        return [period1, period2]

    @pytest.fixture
    def mr_logs(
        self, program: MockProgram, periods: list[MockEVMSPeriod]
    ) -> list[MockManagementReserveLog]:
        """Create test MR log entries."""
        return [
            MockManagementReserveLog(
                id=uuid4(),
                program_id=program.id,
                period=periods[0],
                beginning_mr=Decimal("100000.00"),
                changes_in=Decimal("0.00"),
                changes_out=Decimal("20000.00"),
                ending_mr=Decimal("80000.00"),
                reason="Released to Engineering WP for scope growth",
            ),
            MockManagementReserveLog(
                id=uuid4(),
                program_id=program.id,
                period=periods[1],
                beginning_mr=Decimal("80000.00"),
                changes_in=Decimal("10000.00"),
                changes_out=Decimal("15000.00"),
                ending_mr=Decimal("75000.00"),
                reason="Contract modification added MR, released to testing",
            ),
        ]

    def test_mr_rows_included_when_enabled(
        self,
        program: MockProgram,
        periods: list[MockEVMSPeriod],
        mr_logs: list[MockManagementReserveLog],
    ) -> None:
        """Should include MR rows when enabled."""
        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
            mr_logs=mr_logs,
            config=Format5ExportConfig(include_mr=True),
        )
        report = generator.generate()

        assert len(report.mr_rows) == 2

    def test_mr_rows_excluded_when_disabled(
        self,
        program: MockProgram,
        periods: list[MockEVMSPeriod],
        mr_logs: list[MockManagementReserveLog],
    ) -> None:
        """Should exclude MR rows when disabled."""
        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
            mr_logs=mr_logs,
            config=Format5ExportConfig(include_mr=False),
        )
        report = generator.generate()

        assert len(report.mr_rows) == 0

    def test_current_mr_from_latest_log(
        self,
        program: MockProgram,
        periods: list[MockEVMSPeriod],
        mr_logs: list[MockManagementReserveLog],
    ) -> None:
        """Should set current_mr from latest log entry."""
        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
            mr_logs=mr_logs,
        )
        report = generator.generate()

        # Latest ending_mr is 75000
        assert report.current_mr == Decimal("75000.00")

    def test_mr_row_fields(
        self,
        program: MockProgram,
        periods: list[MockEVMSPeriod],
        mr_logs: list[MockManagementReserveLog],
    ) -> None:
        """Should include all MR row fields."""
        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
            mr_logs=mr_logs,
        )
        report = generator.generate()

        mr1 = report.mr_rows[0]
        assert mr1.period_name == "January 2026"
        assert mr1.beginning_mr == Decimal("100000.00")
        assert mr1.changes_in == Decimal("0.00")
        assert mr1.changes_out == Decimal("20000.00")
        assert mr1.ending_mr == Decimal("80000.00")
        assert "Engineering" in mr1.reason


class TestPeriodRowCalculations:
    """Tests for period row calculations."""

    @pytest.fixture
    def program(self) -> MockProgram:
        """Create test program."""
        return MockProgram(
            id=uuid4(),
            code="PERIOD-001",
            name="Period Test Program",
            contract_number=None,
            budget_at_completion=Decimal("500000.00"),
        )

    @pytest.fixture
    def three_periods(self, program: MockProgram) -> list[MockEVMSPeriod]:
        """Create three months of period data."""
        return [
            MockEVMSPeriod(
                id=uuid4(),
                program_id=program.id,
                period_name="January 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                cumulative_bcws=Decimal("50000.00"),
                cumulative_bcwp=Decimal("48000.00"),
                cumulative_acwp=Decimal("52000.00"),
            ),
            MockEVMSPeriod(
                id=uuid4(),
                program_id=program.id,
                period_name="February 2026",
                period_start=date(2026, 2, 1),
                period_end=date(2026, 2, 28),
                cumulative_bcws=Decimal("100000.00"),
                cumulative_bcwp=Decimal("95000.00"),
                cumulative_acwp=Decimal("110000.00"),
            ),
            MockEVMSPeriod(
                id=uuid4(),
                program_id=program.id,
                period_name="March 2026",
                period_start=date(2026, 3, 1),
                period_end=date(2026, 3, 31),
                cumulative_bcws=Decimal("150000.00"),
                cumulative_bcwp=Decimal("140000.00"),
                cumulative_acwp=Decimal("165000.00"),
            ),
        ]

    def test_period_values_calculated_correctly(
        self, program: MockProgram, three_periods: list[MockEVMSPeriod]
    ) -> None:
        """Should calculate period-only values from cumulative."""
        generator = CPRFormat5Generator(
            program=program,
            periods=three_periods,
        )
        report = generator.generate()

        # Check February (second period)
        feb = report.period_rows[1]

        # Period BCWS = 100000 - 50000 = 50000
        assert feb.bcws == Decimal("50000.00")

        # Period BCWP = 95000 - 48000 = 47000
        assert feb.bcwp == Decimal("47000.00")

        # Period ACWP = 110000 - 52000 = 58000
        assert feb.acwp == Decimal("58000.00")

    def test_variance_calculations(
        self, program: MockProgram, three_periods: list[MockEVMSPeriod]
    ) -> None:
        """Should calculate variances correctly."""
        generator = CPRFormat5Generator(
            program=program,
            periods=three_periods,
        )
        report = generator.generate()

        # Check March (final period)
        march = report.period_rows[2]

        # Cumulative SV = 140000 - 150000 = -10000
        assert march.cumulative_sv == Decimal("-10000.00")

        # Cumulative CV = 140000 - 165000 = -25000
        assert march.cumulative_cv == Decimal("-25000.00")

        # SV% = -10000 / 150000 * 100 = -6.67%
        assert march.sv_percent == Decimal("-6.67")

        # CV% = -25000 / 150000 * 100 = -16.67%
        assert march.cv_percent == Decimal("-16.67")

    def test_periods_to_include_limit(
        self, program: MockProgram, three_periods: list[MockEVMSPeriod]
    ) -> None:
        """Should respect periods_to_include configuration."""
        generator = CPRFormat5Generator(
            program=program,
            periods=three_periods,
            config=Format5ExportConfig(periods_to_include=2),
        )
        report = generator.generate()

        # Should only include last 2 periods
        assert len(report.period_rows) == 2
        assert report.period_rows[0].period_name == "February 2026"
        assert report.period_rows[1].period_name == "March 2026"


class TestReportSummaryMetrics:
    """Tests for report summary metrics."""

    @pytest.fixture
    def program(self) -> MockProgram:
        """Create test program."""
        return MockProgram(
            id=uuid4(),
            code="SUMMARY-001",
            name="Summary Test Program",
            contract_number="N00024-26-C-0004",
            budget_at_completion=Decimal("1000000.00"),
        )

    @pytest.fixture
    def periods(self, program: MockProgram) -> list[MockEVMSPeriod]:
        """Create periods at 40% complete."""
        return [
            MockEVMSPeriod(
                id=uuid4(),
                program_id=program.id,
                period_name="March 2026",
                period_start=date(2026, 3, 1),
                period_end=date(2026, 3, 31),
                cumulative_bcws=Decimal("450000.00"),
                cumulative_bcwp=Decimal("400000.00"),  # 40% complete
                cumulative_acwp=Decimal("450000.00"),
            )
        ]

    def test_summary_metrics(self, program: MockProgram, periods: list[MockEVMSPeriod]) -> None:
        """Should calculate summary metrics correctly."""
        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
        )
        report = generator.generate()

        # BAC
        assert report.bac == Decimal("1000000.00")

        # Percent complete = 400000 / 1000000 * 100 = 40%
        assert report.percent_complete == Decimal("40.00")

        # Percent spent = 450000 / 1000000 * 100 = 45%
        assert report.percent_spent == Decimal("45.00")

        # CPI = 400000 / 450000 = 0.89
        assert report.cumulative_cpi == Decimal("0.89")

        # SPI = 400000 / 450000 = 0.89
        assert report.cumulative_spi == Decimal("0.89")

    def test_report_metadata(self, program: MockProgram, periods: list[MockEVMSPeriod]) -> None:
        """Should include report metadata."""
        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
        )
        report = generator.generate()

        assert report.program_name == "Summary Test Program"
        assert report.program_code == "SUMMARY-001"
        assert report.contract_number == "N00024-26-C-0004"
        assert report.reporting_period == "March 2026"
        assert report.report_date == date.today()
        assert report.generated_at == date.today()


class TestConvenienceFunction:
    """Tests for generate_format5_report convenience function."""

    def test_generate_format5_report(self) -> None:
        """Should generate report using convenience function."""
        program = MockProgram(
            id=uuid4(),
            code="CONV-001",
            name="Convenience Test",
            contract_number=None,
            budget_at_completion=Decimal("100000.00"),
        )
        periods = [
            MockEVMSPeriod(
                id=uuid4(),
                program_id=program.id,
                period_name="January 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                cumulative_bcws=Decimal("10000.00"),
                cumulative_bcwp=Decimal("10000.00"),
                cumulative_acwp=Decimal("10000.00"),
            )
        ]

        report = generate_format5_report(
            program=program,
            periods=periods,
        )

        assert isinstance(report, CPRFormat5Report)
        assert report.program_code == "CONV-001"
        assert len(report.period_rows) == 1


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_periods(self) -> None:
        """Should handle empty periods gracefully."""
        program = MockProgram(
            id=uuid4(),
            code="EMPTY-001",
            name="Empty Periods Test",
            contract_number=None,
            budget_at_completion=Decimal("100000.00"),
        )

        generator = CPRFormat5Generator(
            program=program,
            periods=[],
        )
        report = generator.generate()

        assert len(report.period_rows) == 0
        assert report.reporting_period == ""
        assert report.eac_analysis is None
        assert report.current_eac == Decimal("100000.00")

    def test_zero_bac(self) -> None:
        """Should handle zero BAC gracefully."""
        program = MockProgram(
            id=uuid4(),
            code="ZERO-001",
            name="Zero BAC Test",
            contract_number=None,
            budget_at_completion=Decimal("0.00"),
        )
        periods = [
            MockEVMSPeriod(
                id=uuid4(),
                program_id=program.id,
                period_name="January 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                cumulative_bcws=Decimal("0.00"),
                cumulative_bcwp=Decimal("0.00"),
                cumulative_acwp=Decimal("0.00"),
            )
        ]

        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
        )
        report = generator.generate()

        assert report.percent_complete == Decimal("0")
        assert report.percent_spent == Decimal("0")

    def test_variance_explanation_without_wbs(self) -> None:
        """Should handle variance explanation without WBS."""
        program = MockProgram(
            id=uuid4(),
            code="NO-WBS-001",
            name="No WBS Test",
            contract_number=None,
            budget_at_completion=Decimal("100000.00"),
        )
        periods = [
            MockEVMSPeriod(
                id=uuid4(),
                program_id=program.id,
                period_name="January 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                cumulative_bcws=Decimal("10000.00"),
                cumulative_bcwp=Decimal("8000.00"),
                cumulative_acwp=Decimal("10000.00"),
            )
        ]
        explanations = [
            MockVarianceExplanation(
                id=uuid4(),
                program_id=program.id,
                wbs=None,  # No WBS
                period=None,
                variance_type="cost",
                variance_amount=Decimal("-2000.00"),
                variance_percent=Decimal("-20.00"),
                explanation="Overall cost overrun",
                corrective_action=None,
                expected_resolution=None,
            )
        ]

        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
            variance_explanations=explanations,
        )
        report = generator.generate()

        assert len(report.variance_explanations) == 1
        ve = report.variance_explanations[0]
        assert ve.wbs_code == ""
        assert ve.wbs_name == ""
