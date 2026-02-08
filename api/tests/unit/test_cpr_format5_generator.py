"""Unit tests for CPR Format 5 (EVMS) report generator."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from src.schemas.cpr_format5 import (
    CPRFormat5Report,
    EACAnalysis,
    Format5ExportConfig,
    ManagementReserveRow,
    VarianceExplanation,
)
from src.services.cpr_format5_generator import CPRFormat5Generator


def _make_program(
    name: str = "Test Program",
    code: str = "TP-001",
    contract_number: str | None = "C-99999",
    budget_at_completion: Decimal = Decimal("100000.00"),
    management_reserve: Decimal = Decimal("5000.00"),
) -> MagicMock:
    """Create a mock Program model."""
    program = MagicMock()
    program.id = "00000000-0000-0000-0000-000000000001"
    program.name = name
    program.code = code
    program.contract_number = contract_number
    program.budget_at_completion = budget_at_completion
    program.management_reserve = management_reserve
    return program


def _make_period(
    period_name: str = "Jan 2026",
    period_start: date = date(2026, 1, 1),
    period_end: date = date(2026, 1, 31),
    cumulative_bcws: Decimal = Decimal("10000.00"),
    cumulative_bcwp: Decimal = Decimal("9000.00"),
    cumulative_acwp: Decimal = Decimal("9500.00"),
    spi: Decimal | None = Decimal("0.90"),
    cpi: Decimal | None = Decimal("0.95"),
) -> MagicMock:
    """Create a mock EVMSPeriod model."""
    period = MagicMock()
    period.period_name = period_name
    period.period_start = period_start
    period.period_end = period_end
    period.cumulative_bcws = cumulative_bcws
    period.cumulative_bcwp = cumulative_bcwp
    period.cumulative_acwp = cumulative_acwp
    period.spi = spi
    period.cpi = cpi
    return period


def _make_variance_explanation(
    variance_type: str = "cost",
    variance_amount: Decimal = Decimal("-5000.00"),
    variance_percent: Decimal = Decimal("-15.00"),
    explanation: str = "Material costs exceeded estimate",
    corrective_action: str | None = "Renegotiate supplier contract",
    expected_resolution: date | None = date(2026, 6, 30),
    wbs_code: str = "1.1.1",
    wbs_name: str = "Design Phase",
) -> MagicMock:
    """Create a mock VarianceExplanation model."""
    ve = MagicMock()
    ve.variance_type = variance_type
    ve.variance_amount = variance_amount
    ve.variance_percent = variance_percent
    ve.explanation = explanation
    ve.corrective_action = corrective_action
    ve.expected_resolution = expected_resolution

    wbs_mock = MagicMock()
    wbs_mock.wbs_code = wbs_code
    wbs_mock.name = wbs_name
    ve.wbs = wbs_mock

    return ve


def _make_mr_log(
    beginning_mr: Decimal = Decimal("5000.00"),
    changes_in: Decimal = Decimal("0.00"),
    changes_out: Decimal = Decimal("1000.00"),
    ending_mr: Decimal = Decimal("4000.00"),
    reason: str | None = "Released to WBS 1.2",
    period_name: str = "Jan 2026",
) -> MagicMock:
    """Create a mock ManagementReserveLog model."""
    log = MagicMock()
    log.beginning_mr = beginning_mr
    log.changes_in = changes_in
    log.changes_out = changes_out
    log.ending_mr = ending_mr
    log.reason = reason

    period_mock = MagicMock()
    period_mock.period_name = period_name
    log.period = period_mock

    return log


class TestCPRFormat5Generate:
    """Tests for CPRFormat5Generator.generate()."""

    def test_generate_returns_report(self):
        """Should return a CPRFormat5Report instance."""
        # Arrange
        program = _make_program()
        periods = [_make_period()]
        generator = CPRFormat5Generator(program, periods)

        # Act
        report = generator.generate()

        # Assert
        assert isinstance(report, CPRFormat5Report)

    def test_generate_with_empty_periods(self):
        """Should handle empty periods gracefully with defaults."""
        # Arrange
        program = _make_program()
        generator = CPRFormat5Generator(program, periods=[])

        # Act
        report = generator.generate()

        # Assert
        assert report.reporting_period == ""
        assert report.percent_complete == Decimal("0.00")
        assert report.percent_spent == Decimal("0.00")
        assert report.current_eac == Decimal("100000.00")  # falls back to BAC
        assert report.period_rows == []
        assert report.eac_analysis is None

    def test_format5_report_has_program_info(self):
        """Should carry program name, code, and contract number."""
        # Arrange
        program = _make_program(
            name="Delta Force",
            code="DF-200",
            contract_number="CONTRACT-789",
        )
        generator = CPRFormat5Generator(program, [_make_period()])

        # Act
        report = generator.generate()

        # Assert
        assert report.program_name == "Delta Force"
        assert report.program_code == "DF-200"
        assert report.contract_number == "CONTRACT-789"

    def test_cumulative_bcws_calculated(self):
        """Should report cumulative BCWS from latest period data."""
        # Arrange
        period = _make_period(cumulative_bcws=Decimal("50000"))
        generator = CPRFormat5Generator(_make_program(), [period])

        # Act
        report = generator.generate()

        # Assert
        # The CPI method uses cumulative_bcws from the latest period
        assert report.cumulative_spi is not None

    def test_cumulative_bcwp_calculated(self):
        """Should use cumulative BCWP from the latest period."""
        # Arrange
        period = _make_period(
            cumulative_bcwp=Decimal("40000"),
            cumulative_acwp=Decimal("50000"),
        )
        program = _make_program(budget_at_completion=Decimal("100000"))
        generator = CPRFormat5Generator(program, [period])

        # Act
        report = generator.generate()

        # Assert
        # percent_complete = cumulative_bcwp / bac * 100 = 40000/100000*100 = 40
        assert report.percent_complete == Decimal("40.00")


class TestBuildPeriodRows:
    """Tests for CPRFormat5Generator._build_period_rows()."""

    def test_period_rows_include_variance_data(self):
        """Should compute period SV, CV, and cumulative variances."""
        # Arrange
        period = _make_period(
            cumulative_bcws=Decimal("10000"),
            cumulative_bcwp=Decimal("8000"),
            cumulative_acwp=Decimal("9000"),
        )
        generator = CPRFormat5Generator(_make_program(), [period])

        # Act
        rows = generator._build_period_rows()

        # Assert
        assert len(rows) == 1
        row = rows[0]
        # Cumulative SV = 8000 - 10000 = -2000
        assert row.cumulative_sv == Decimal("-2000")
        # Cumulative CV = 8000 - 9000 = -1000
        assert row.cumulative_cv == Decimal("-1000")

    def test_period_rows_count_limited_by_config(self):
        """Should respect periods_to_include from config."""
        # Arrange
        periods = [
            _make_period(
                period_name=f"Month {i}",
                period_start=date(2026, max(1, i), 1),
                period_end=date(2026, max(1, i), 28),
                cumulative_bcws=Decimal(str(i * 1000)),
                cumulative_bcwp=Decimal(str(i * 900)),
                cumulative_acwp=Decimal(str(i * 950)),
            )
            for i in range(1, 7)
        ]
        config = Format5ExportConfig(periods_to_include=3)
        generator = CPRFormat5Generator(_make_program(), periods, config=config)

        # Act
        rows = generator._build_period_rows()

        # Assert
        assert len(rows) == 3  # only last 3 periods


class TestBuildEACAnalysis:
    """Tests for CPRFormat5Generator._build_eac_analysis()."""

    def test_eac_analysis_with_healthy_program(self):
        """Should use CPI method for healthy program (CPI >= 0.95)."""
        # Arrange
        period = _make_period(
            cumulative_bcws=Decimal("50000"),
            cumulative_bcwp=Decimal("50000"),
            cumulative_acwp=Decimal("50000"),
        )
        program = _make_program(budget_at_completion=Decimal("100000"))
        generator = CPRFormat5Generator(program, [period])

        # Act
        analysis = generator._build_eac_analysis(period, Decimal("100000"))

        # Assert
        assert isinstance(analysis, EACAnalysis)
        # CPI = 1.0, so EAC_CPI = BAC/CPI = 100000
        assert analysis.eac_cpi == Decimal("100000.00")
        assert "standard practice" in analysis.selection_rationale

    def test_eac_analysis_with_overbudget_program(self):
        """Should reflect cost overrun in EAC analysis."""
        # Arrange
        period = _make_period(
            cumulative_bcws=Decimal("50000"),
            cumulative_bcwp=Decimal("40000"),
            cumulative_acwp=Decimal("60000"),
        )
        bac = Decimal("100000")
        program = _make_program(budget_at_completion=bac)
        generator = CPRFormat5Generator(program, [period])

        # Act
        analysis = generator._build_eac_analysis(period, bac)

        # Assert
        # CPI = 40000/60000 = 0.6667 -> EAC = BAC / CPI > BAC
        assert analysis.eac_cpi > bac
        # Typical: ACWP + (BAC - BCWP) = 60000 + 60000 = 120000
        assert analysis.eac_typical == Decimal("120000.00")

    def test_eac_methods_calculated(self):
        """Should calculate all 6 EAC methods (management may be None)."""
        # Arrange
        period = _make_period(
            cumulative_bcws=Decimal("50000"),
            cumulative_bcwp=Decimal("45000"),
            cumulative_acwp=Decimal("48000"),
        )
        bac = Decimal("100000")
        generator = CPRFormat5Generator(
            _make_program(budget_at_completion=bac),
            [period],
            manager_etc=Decimal("55000"),
        )

        # Act
        analysis = generator._build_eac_analysis(period, bac)

        # Assert
        assert analysis.eac_cpi is not None
        assert analysis.eac_spi is not None
        assert analysis.eac_composite is not None
        assert analysis.eac_typical is not None
        assert analysis.eac_atypical is not None
        # Management EAC available because manager_etc was provided
        assert analysis.eac_management == (Decimal("48000") + Decimal("55000")).quantize(
            Decimal("0.01")
        )

    def test_eac_analysis_range_and_average(self):
        """Should compute range (low, high) and average across EAC methods."""
        # Arrange
        period = _make_period(
            cumulative_bcws=Decimal("50000"),
            cumulative_bcwp=Decimal("45000"),
            cumulative_acwp=Decimal("50000"),
        )
        bac = Decimal("100000")
        generator = CPRFormat5Generator(
            _make_program(budget_at_completion=bac),
            [period],
        )

        # Act
        analysis = generator._build_eac_analysis(period, bac)

        # Assert
        assert analysis.eac_range_low is not None
        assert analysis.eac_range_high is not None
        assert analysis.eac_average is not None
        assert analysis.eac_range_low <= analysis.eac_range_high


class TestBuildVarianceExplanations:
    """Tests for CPRFormat5Generator._build_variance_explanations()."""

    def test_variance_explanations_mapped_correctly(self):
        """Should map model fields to schema correctly."""
        # Arrange
        ve = _make_variance_explanation(
            variance_type="cost",
            variance_amount=Decimal("-5000"),
            variance_percent=Decimal("-15.00"),
            explanation="Over budget on materials",
            wbs_code="1.1",
            wbs_name="Engineering",
        )
        generator = CPRFormat5Generator(
            _make_program(),
            [_make_period()],
            variance_explanations=[ve],
        )

        # Act
        explanations = generator._build_variance_explanations()

        # Assert
        assert len(explanations) == 1
        exp = explanations[0]
        assert isinstance(exp, VarianceExplanation)
        assert exp.wbs_code == "1.1"
        assert exp.wbs_name == "Engineering"
        assert exp.variance_type == "cost"
        assert exp.explanation == "Over budget on materials"

    def test_generate_with_no_variance_explanations(self):
        """Should produce empty variance explanations list when none provided."""
        # Arrange
        generator = CPRFormat5Generator(_make_program(), [_make_period()])

        # Act
        report = generator.generate()

        # Assert
        assert report.variance_explanations == []

    def test_variance_explanations_filtered_by_threshold(self):
        """Should exclude variances below the configured threshold."""
        # Arrange
        ve_above = _make_variance_explanation(variance_percent=Decimal("-15.00"))
        ve_below = _make_variance_explanation(variance_percent=Decimal("-5.00"))
        config = Format5ExportConfig(variance_threshold_percent=Decimal("10"))
        generator = CPRFormat5Generator(
            _make_program(),
            [_make_period()],
            config=config,
            variance_explanations=[ve_above, ve_below],
        )

        # Act
        explanations = generator._build_variance_explanations()

        # Assert
        assert len(explanations) == 1
        assert explanations[0].variance_percent == Decimal("-15.00")

    def test_variance_explanations_disabled_by_config(self):
        """Should return empty list when include_explanations is False."""
        # Arrange
        ve = _make_variance_explanation()
        config = Format5ExportConfig(include_explanations=False)
        generator = CPRFormat5Generator(
            _make_program(),
            [_make_period()],
            config=config,
            variance_explanations=[ve],
        )

        # Act
        explanations = generator._build_variance_explanations()

        # Assert
        assert explanations == []


class TestBuildMRRows:
    """Tests for CPRFormat5Generator._build_mr_rows()."""

    def test_mr_rows_include_all_logs(self):
        """Should produce one row per MR log entry."""
        # Arrange
        log1 = _make_mr_log(period_name="Jan 2026")
        log2 = _make_mr_log(
            beginning_mr=Decimal("4000"),
            changes_in=Decimal("500"),
            changes_out=Decimal("0"),
            ending_mr=Decimal("4500"),
            period_name="Feb 2026",
        )
        generator = CPRFormat5Generator(
            _make_program(),
            [_make_period()],
            mr_logs=[log1, log2],
        )

        # Act
        rows = generator._build_mr_rows()

        # Assert
        assert len(rows) == 2
        assert isinstance(rows[0], ManagementReserveRow)
        assert rows[0].beginning_mr == Decimal("5000.00")
        assert rows[1].ending_mr == Decimal("4500")

    def test_generate_with_no_mr_logs(self):
        """Should produce empty MR rows when no logs provided."""
        # Arrange
        generator = CPRFormat5Generator(_make_program(), [_make_period()])

        # Act
        report = generator.generate()

        # Assert
        assert report.mr_rows == []
        assert report.current_mr == Decimal("0")

    def test_mr_rows_disabled_by_config(self):
        """Should return empty list when include_mr is False."""
        # Arrange
        config = Format5ExportConfig(include_mr=False)
        generator = CPRFormat5Generator(
            _make_program(),
            [_make_period()],
            config=config,
            mr_logs=[_make_mr_log()],
        )

        # Act
        rows = generator._build_mr_rows()

        # Assert
        assert rows == []
