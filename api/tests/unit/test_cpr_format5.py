"""Unit tests for CPR Format 5 (EVMS) report generation."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from src.schemas.cpr_format5 import (
    CPRFormat5Report,
    EACAnalysis,
    Format5ExportConfig,
    Format5PeriodRow,
    ManagementReserveRow,
    VarianceExplanation,
)
from src.services.cpr_format5_generator import CPRFormat5Generator, generate_format5_report


class TestFormat5PeriodRow:
    """Tests for Format5PeriodRow dataclass."""

    def test_create_period_row(self):
        """Should create period row with all fields."""
        row = Format5PeriodRow(
            period_name="January 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            bcws=Decimal("100000"),
            bcwp=Decimal("95000"),
            acwp=Decimal("98000"),
            cumulative_bcws=Decimal("500000"),
            cumulative_bcwp=Decimal("480000"),
            cumulative_acwp=Decimal("490000"),
            period_sv=Decimal("-5000"),
            period_cv=Decimal("-3000"),
            cumulative_sv=Decimal("-20000"),
            cumulative_cv=Decimal("-10000"),
            sv_percent=Decimal("-4.00"),
            cv_percent=Decimal("-2.00"),
            spi=Decimal("0.96"),
            cpi=Decimal("0.98"),
            eac=Decimal("1020408"),
            etc=Decimal("530408"),
            vac=Decimal("-20408"),
            tcpi=Decimal("1.04"),
        )

        assert row.period_name == "January 2026"
        assert row.bcws == Decimal("100000")
        assert row.sv_percent == Decimal("-4.00")
        assert row.cpi == Decimal("0.98")

    def test_period_row_with_none_indices(self):
        """Should handle None for indices at start of program."""
        row = Format5PeriodRow(
            period_name="Start",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            bcws=Decimal("0"),
            bcwp=Decimal("0"),
            acwp=Decimal("0"),
            cumulative_bcws=Decimal("0"),
            cumulative_bcwp=Decimal("0"),
            cumulative_acwp=Decimal("0"),
            period_sv=Decimal("0"),
            period_cv=Decimal("0"),
            cumulative_sv=Decimal("0"),
            cumulative_cv=Decimal("0"),
            sv_percent=Decimal("0"),
            cv_percent=Decimal("0"),
            spi=None,
            cpi=None,
            eac=Decimal("1000000"),
            etc=Decimal("1000000"),
            vac=Decimal("0"),
            tcpi=None,
        )

        assert row.spi is None
        assert row.cpi is None
        assert row.tcpi is None


class TestManagementReserveRow:
    """Tests for ManagementReserveRow dataclass."""

    def test_create_mr_row(self):
        """Should create MR row with all fields."""
        row = ManagementReserveRow(
            period_name="January 2026",
            beginning_mr=Decimal("100000"),
            changes_in=Decimal("10000"),
            changes_out=Decimal("25000"),
            ending_mr=Decimal("85000"),
            reason="Released MR for scope growth in WBS 1.2.3",
        )

        assert row.beginning_mr == Decimal("100000")
        assert row.ending_mr == Decimal("85000")
        assert row.changes_out == Decimal("25000")

    def test_mr_row_optional_reason(self):
        """Should handle optional reason field."""
        row = ManagementReserveRow(
            period_name="January 2026",
            beginning_mr=Decimal("100000"),
            changes_in=Decimal("0"),
            changes_out=Decimal("0"),
            ending_mr=Decimal("100000"),
        )

        assert row.reason is None


class TestVarianceExplanation:
    """Tests for VarianceExplanation dataclass."""

    def test_create_variance_explanation(self):
        """Should create variance explanation with all fields."""
        explanation = VarianceExplanation(
            wbs_code="1.2.3",
            wbs_name="Software Development",
            variance_type="cost",
            variance_amount=Decimal("-50000"),
            variance_percent=Decimal("-15.00"),
            explanation="Labor costs exceeded estimates due to additional complexity",
            corrective_action="Added experienced staff to accelerate work",
            expected_resolution_date=date(2026, 3, 31),
        )

        assert explanation.wbs_code == "1.2.3"
        assert explanation.variance_type == "cost"
        assert explanation.variance_percent == Decimal("-15.00")

    def test_variance_explanation_optional_fields(self):
        """Should handle optional corrective action fields."""
        explanation = VarianceExplanation(
            wbs_code="1.2.3",
            wbs_name="Software Development",
            variance_type="schedule",
            variance_amount=Decimal("-10000"),
            variance_percent=Decimal("-5.00"),
            explanation="Minor delay due to resource availability",
        )

        assert explanation.corrective_action is None
        assert explanation.expected_resolution_date is None


class TestEACAnalysis:
    """Tests for EACAnalysis dataclass."""

    def test_create_eac_analysis(self):
        """Should create EAC analysis with all methods."""
        analysis = EACAnalysis(
            eac_cpi=Decimal("1050000"),
            eac_spi_cpi=Decimal("1080000"),
            eac_management=Decimal("1060000"),
            eac_selected=Decimal("1060000"),
            selection_rationale="Management estimate validated by bottom-up analysis",
        )

        assert analysis.eac_cpi == Decimal("1050000")
        assert analysis.eac_spi_cpi == Decimal("1080000")
        assert analysis.eac_selected == Decimal("1060000")


class TestFormat5ExportConfig:
    """Tests for Format5ExportConfig dataclass."""

    def test_default_config(self):
        """Should have correct default values."""
        config = Format5ExportConfig()

        assert config.include_mr is True
        assert config.include_explanations is True
        assert config.variance_threshold_percent == Decimal("10")
        assert config.periods_to_include == 12
        assert config.include_eac_analysis is True

    def test_custom_config(self):
        """Should accept custom values."""
        config = Format5ExportConfig(
            include_mr=False,
            variance_threshold_percent=Decimal("5"),
            periods_to_include=18,
        )

        assert config.include_mr is False
        assert config.variance_threshold_percent == Decimal("5")
        assert config.periods_to_include == 18


class TestCPRFormat5Report:
    """Tests for CPRFormat5Report dataclass."""

    def test_create_report(self):
        """Should create report with all fields."""
        report = CPRFormat5Report(
            program_name="Test Program",
            program_code="TEST-001",
            contract_number="W12345-26-C-0001",
            report_date=date(2026, 1, 31),
            reporting_period="January 2026",
            bac=Decimal("1000000"),
            current_eac=Decimal("1020000"),
            current_etc=Decimal("530000"),
            current_vac=Decimal("-20000"),
            cumulative_cpi=Decimal("0.98"),
            cumulative_spi=Decimal("0.96"),
            cumulative_tcpi=Decimal("1.04"),
            percent_complete=Decimal("48.00"),
            percent_spent=Decimal("49.00"),
        )

        assert report.program_name == "Test Program"
        assert report.bac == Decimal("1000000")
        assert report.current_vac == Decimal("-20000")

    def test_report_default_lists(self):
        """Should initialize empty lists by default."""
        report = CPRFormat5Report(
            program_name="Test",
            program_code="TEST",
            contract_number=None,
            report_date=date.today(),
            reporting_period="",
            bac=Decimal("0"),
            current_eac=Decimal("0"),
            current_etc=Decimal("0"),
            current_vac=Decimal("0"),
            cumulative_cpi=None,
            cumulative_spi=None,
            cumulative_tcpi=None,
            percent_complete=Decimal("0"),
            percent_spent=Decimal("0"),
        )

        assert report.period_rows == []
        assert report.mr_rows == []
        assert report.variance_explanations == []
        assert report.current_mr == Decimal("0")


def create_mock_program(
    bac: Decimal = Decimal("1000000"),
    code: str = "TEST-001",
    name: str = "Test Program",
) -> MagicMock:
    """Create a mock program for testing."""
    program = MagicMock()
    program.id = uuid4()
    program.code = code
    program.name = name
    program.contract_number = "W12345-26-C-0001"
    program.budget_at_completion = bac
    return program


def create_mock_period(
    period_name: str,
    period_start: date,
    period_end: date,
    cumulative_bcws: Decimal,
    cumulative_bcwp: Decimal,
    cumulative_acwp: Decimal,
) -> MagicMock:
    """Create a mock EVMS period for testing."""
    period = MagicMock()
    period.id = uuid4()
    period.period_name = period_name
    period.period_start = period_start
    period.period_end = period_end
    period.cumulative_bcws = cumulative_bcws
    period.cumulative_bcwp = cumulative_bcwp
    period.cumulative_acwp = cumulative_acwp

    # Calculate derived properties
    if cumulative_acwp > 0:
        period.cpi = (cumulative_bcwp / cumulative_acwp).quantize(Decimal("0.01"))
    else:
        period.cpi = None

    if cumulative_bcws > 0:
        period.spi = (cumulative_bcwp / cumulative_bcws).quantize(Decimal("0.01"))
    else:
        period.spi = None

    return period


class TestCPRFormat5Generator:
    """Tests for CPRFormat5Generator service."""

    def test_generate_empty_periods(self):
        """Should handle empty periods list."""
        program = create_mock_program()
        generator = CPRFormat5Generator(program, [])

        report = generator.generate()

        assert report.program_name == "Test Program"
        assert report.bac == Decimal("1000000")
        assert report.period_rows == []
        assert report.reporting_period == ""

    def test_generate_single_period(self):
        """Should generate report with single period."""
        program = create_mock_program()
        periods = [
            create_mock_period(
                "January 2026",
                date(2026, 1, 1),
                date(2026, 1, 31),
                Decimal("100000"),
                Decimal("95000"),
                Decimal("98000"),
            )
        ]

        generator = CPRFormat5Generator(program, periods)
        report = generator.generate()

        assert report.reporting_period == "January 2026"
        assert len(report.period_rows) == 1
        assert report.period_rows[0].period_name == "January 2026"
        assert report.period_rows[0].cumulative_bcws == Decimal("100000")

    def test_generate_multiple_periods(self):
        """Should generate report with multiple periods."""
        program = create_mock_program()
        periods = [
            create_mock_period(
                "January 2026",
                date(2026, 1, 1),
                date(2026, 1, 31),
                Decimal("100000"),
                Decimal("95000"),
                Decimal("98000"),
            ),
            create_mock_period(
                "February 2026",
                date(2026, 2, 1),
                date(2026, 2, 28),
                Decimal("200000"),
                Decimal("190000"),
                Decimal("195000"),
            ),
            create_mock_period(
                "March 2026",
                date(2026, 3, 1),
                date(2026, 3, 31),
                Decimal("300000"),
                Decimal("285000"),
                Decimal("292000"),
            ),
        ]

        generator = CPRFormat5Generator(program, periods)
        report = generator.generate()

        assert len(report.period_rows) == 3
        assert report.reporting_period == "March 2026"

        # Verify period values are calculated correctly
        # First period
        assert report.period_rows[0].bcws == Decimal("100000")
        assert report.period_rows[0].bcwp == Decimal("95000")
        assert report.period_rows[0].acwp == Decimal("98000")

        # Second period (incremental values)
        assert report.period_rows[1].bcws == Decimal("100000")  # 200000 - 100000
        assert report.period_rows[1].bcwp == Decimal("95000")  # 190000 - 95000
        assert report.period_rows[1].acwp == Decimal("97000")  # 195000 - 98000

    def test_generate_periods_sorted(self):
        """Should sort periods by date."""
        program = create_mock_program()
        # Provide periods out of order
        periods = [
            create_mock_period(
                "March 2026",
                date(2026, 3, 1),
                date(2026, 3, 31),
                Decimal("300000"),
                Decimal("285000"),
                Decimal("292000"),
            ),
            create_mock_period(
                "January 2026",
                date(2026, 1, 1),
                date(2026, 1, 31),
                Decimal("100000"),
                Decimal("95000"),
                Decimal("98000"),
            ),
        ]

        generator = CPRFormat5Generator(program, periods)
        report = generator.generate()

        # Should be sorted chronologically
        assert report.period_rows[0].period_name == "January 2026"
        assert report.period_rows[1].period_name == "March 2026"

    def test_generate_limits_periods(self):
        """Should limit periods based on config."""
        program = create_mock_program()

        # Create 15 periods
        periods = []
        for i in range(15):
            month = (i % 12) + 1
            year = 2025 + (i // 12)
            periods.append(
                create_mock_period(
                    f"Period {i + 1}",
                    date(year, month, 1),
                    date(year, month, 28),
                    Decimal(str((i + 1) * 50000)),
                    Decimal(str((i + 1) * 48000)),
                    Decimal(str((i + 1) * 49000)),
                )
            )

        config = Format5ExportConfig(periods_to_include=6)
        generator = CPRFormat5Generator(program, periods, config)
        report = generator.generate()

        # Should only include last 6 periods
        assert len(report.period_rows) == 6
        assert report.period_rows[0].period_name == "Period 10"
        assert report.period_rows[5].period_name == "Period 15"

    def test_generate_calculates_variances(self):
        """Should calculate period and cumulative variances."""
        program = create_mock_program()
        periods = [
            create_mock_period(
                "January 2026",
                date(2026, 1, 1),
                date(2026, 1, 31),
                Decimal("100000"),  # BCWS
                Decimal("90000"),  # BCWP
                Decimal("95000"),  # ACWP
            ),
        ]

        generator = CPRFormat5Generator(program, periods)
        report = generator.generate()

        row = report.period_rows[0]

        # Period variances
        assert row.period_sv == Decimal("-10000")  # BCWP - BCWS = 90000 - 100000
        assert row.period_cv == Decimal("-5000")  # BCWP - ACWP = 90000 - 95000

        # Cumulative variances (same as period for first period)
        assert row.cumulative_sv == Decimal("-10000")
        assert row.cumulative_cv == Decimal("-5000")

    def test_generate_calculates_variance_percentages(self):
        """Should calculate variance percentages."""
        program = create_mock_program()
        periods = [
            create_mock_period(
                "January 2026",
                date(2026, 1, 1),
                date(2026, 1, 31),
                Decimal("100000"),  # BCWS
                Decimal("90000"),  # BCWP
                Decimal("95000"),  # ACWP
            ),
        ]

        generator = CPRFormat5Generator(program, periods)
        report = generator.generate()

        row = report.period_rows[0]

        # SV% = SV / BCWS * 100 = -10000 / 100000 * 100 = -10%
        assert row.sv_percent == Decimal("-10.00")

        # CV% = CV / BCWS * 100 = -5000 / 100000 * 100 = -5%
        assert row.cv_percent == Decimal("-5.00")

    def test_generate_summary_metrics(self):
        """Should calculate summary metrics correctly."""
        program = create_mock_program(bac=Decimal("1000000"))
        periods = [
            create_mock_period(
                "January 2026",
                date(2026, 1, 1),
                date(2026, 1, 31),
                Decimal("500000"),  # BCWS - 50% planned
                Decimal("480000"),  # BCWP - 48% complete
                Decimal("490000"),  # ACWP
            ),
        ]

        generator = CPRFormat5Generator(program, periods)
        report = generator.generate()

        assert report.bac == Decimal("1000000")
        assert report.cumulative_cpi == Decimal("0.98")  # 480000 / 490000
        assert report.cumulative_spi == Decimal("0.96")  # 480000 / 500000
        assert report.percent_complete == Decimal("48.00")  # 480000 / 1000000 * 100
        assert report.percent_spent == Decimal("49.00")  # 490000 / 1000000 * 100

    def test_generate_eac_analysis(self):
        """Should build EAC analysis with different methods."""
        program = create_mock_program(bac=Decimal("1000000"))
        periods = [
            create_mock_period(
                "January 2026",
                date(2026, 1, 1),
                date(2026, 1, 31),
                Decimal("500000"),
                Decimal("480000"),
                Decimal("490000"),
            ),
        ]

        generator = CPRFormat5Generator(program, periods)
        report = generator.generate()

        assert report.eac_analysis is not None
        assert report.eac_analysis.eac_cpi > Decimal("1000000")  # Over budget
        assert report.eac_analysis.eac_spi_cpi > report.eac_analysis.eac_cpi  # Worse
        assert report.eac_analysis.selection_rationale is not None

    def test_generate_with_zero_bac(self):
        """Should handle zero BAC gracefully."""
        program = create_mock_program(bac=Decimal("0"))
        periods = [
            create_mock_period(
                "January 2026",
                date(2026, 1, 1),
                date(2026, 1, 31),
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
            ),
        ]

        generator = CPRFormat5Generator(program, periods)
        report = generator.generate()

        assert report.bac == Decimal("0")
        assert report.percent_complete == Decimal("0")
        assert report.percent_spent == Decimal("0")


class TestGenerateFormat5ReportFunction:
    """Tests for the convenience function."""

    def test_generate_format5_report(self):
        """Should generate report using convenience function."""
        program = create_mock_program()
        periods = [
            create_mock_period(
                "January 2026",
                date(2026, 1, 1),
                date(2026, 1, 31),
                Decimal("100000"),
                Decimal("95000"),
                Decimal("98000"),
            ),
        ]

        report = generate_format5_report(program, periods)

        assert isinstance(report, CPRFormat5Report)
        assert report.program_name == "Test Program"
        assert len(report.period_rows) == 1

    def test_generate_format5_report_with_config(self):
        """Should accept custom config."""
        program = create_mock_program()
        periods = []
        for i in range(10):
            periods.append(
                create_mock_period(
                    f"Period {i + 1}",
                    date(2026, 1, i + 1),
                    date(2026, 1, i + 2),
                    Decimal(str((i + 1) * 10000)),
                    Decimal(str((i + 1) * 9500)),
                    Decimal(str((i + 1) * 9800)),
                )
            )

        config = Format5ExportConfig(periods_to_include=5)
        report = generate_format5_report(program, periods, config)

        assert len(report.period_rows) == 5


class TestFormat5PerformanceIndices:
    """Tests for performance index calculations."""

    def test_over_budget_scenario(self):
        """Should correctly identify over budget condition."""
        program = create_mock_program(bac=Decimal("1000000"))
        periods = [
            create_mock_period(
                "January 2026",
                date(2026, 1, 1),
                date(2026, 1, 31),
                Decimal("500000"),  # BCWS
                Decimal("450000"),  # BCWP (behind schedule)
                Decimal("520000"),  # ACWP (over budget)
            ),
        ]

        generator = CPRFormat5Generator(program, periods)
        report = generator.generate()

        # CPI < 1.0 means over budget
        assert report.cumulative_cpi < Decimal("1.0")

        # SPI < 1.0 means behind schedule
        assert report.cumulative_spi < Decimal("1.0")

        # EAC > BAC means projected overrun
        assert report.current_eac > report.bac

        # VAC < 0 means projected unfavorable variance
        assert report.current_vac < Decimal("0")

    def test_under_budget_scenario(self):
        """Should correctly identify under budget condition."""
        program = create_mock_program(bac=Decimal("1000000"))
        periods = [
            create_mock_period(
                "January 2026",
                date(2026, 1, 1),
                date(2026, 1, 31),
                Decimal("500000"),  # BCWS
                Decimal("520000"),  # BCWP (ahead of schedule)
                Decimal("480000"),  # ACWP (under budget)
            ),
        ]

        generator = CPRFormat5Generator(program, periods)
        report = generator.generate()

        # CPI > 1.0 means under budget
        assert report.cumulative_cpi > Decimal("1.0")

        # SPI > 1.0 means ahead of schedule
        assert report.cumulative_spi > Decimal("1.0")

        # EAC < BAC means projected underrun
        assert report.current_eac < report.bac

        # VAC > 0 means projected favorable variance
        assert report.current_vac > Decimal("0")
