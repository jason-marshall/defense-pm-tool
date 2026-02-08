"""Unit tests for CPR Format 3 (Baseline) report generator."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from src.schemas.cpr_format3 import CPRFormat3Report
from src.services.cpr_format3_generator import CPRFormat3Generator


def _make_program(
    name: str = "Test Program",
    code: str = "TP-001",
    contract_number: str | None = "C-12345",
    budget_at_completion: Decimal | None = Decimal("100000.00"),
) -> MagicMock:
    """Create a mock program matching ProgramProtocol."""
    program = MagicMock()
    program.name = name
    program.code = code
    program.contract_number = contract_number
    program.budget_at_completion = budget_at_completion
    return program


def _make_baseline(
    name: str = "Baseline 1",
    version: int = 1,
    total_bac: Decimal = Decimal("100000.00"),
    scheduled_finish: date | None = date(2026, 12, 31),
    created_at: datetime | None = datetime(2026, 1, 1, tzinfo=UTC),
) -> MagicMock:
    """Create a mock baseline matching BaselineProtocol."""
    baseline = MagicMock()
    baseline.name = name
    baseline.version = version
    baseline.total_bac = total_bac
    baseline.scheduled_finish = scheduled_finish
    baseline.created_at = created_at
    return baseline


def _make_period(
    period_name: str = "Jan 2026",
    period_start: date = date(2026, 1, 1),
    period_end: date = date(2026, 1, 31),
    bcws: Decimal | None = Decimal("10000.00"),
    bcwp: Decimal | None = Decimal("9000.00"),
    acwp: Decimal | None = Decimal("9500.00"),
) -> MagicMock:
    """Create a mock EVMS period matching EVMSPeriodProtocol."""
    period = MagicMock()
    period.period_name = period_name
    period.period_start = period_start
    period.period_end = period_end
    period.bcws = bcws
    period.bcwp = bcwp
    period.acwp = acwp
    return period


class TestCPRFormat3Generate:
    """Tests for CPRFormat3Generator.generate()."""

    def test_generate_returns_report_object(self):
        """Should return a CPRFormat3Report instance."""
        # Arrange
        program = _make_program()
        baseline = _make_baseline()
        periods = [_make_period()]

        generator = CPRFormat3Generator(program, baseline, periods)

        # Act
        report = generator.generate()

        # Assert
        assert isinstance(report, CPRFormat3Report)

    def test_generate_with_no_periods_returns_zero_values(self):
        """Should return report with zero cumulative values when no periods given."""
        # Arrange
        program = _make_program()
        baseline = _make_baseline()
        generator = CPRFormat3Generator(program, baseline, periods=[])

        # Act
        report = generator.generate()

        # Assert
        assert report.total_bcws == Decimal("0")
        assert report.total_bcwp == Decimal("0")
        assert report.total_acwp == Decimal("0")
        assert report.total_sv == Decimal("0")
        assert report.total_cv == Decimal("0")
        assert report.time_phase_rows == []
        assert report.current_period == ""

    def test_generate_with_single_period(self):
        """Should correctly calculate values for a single period."""
        # Arrange
        program = _make_program()
        baseline = _make_baseline()
        period = _make_period(
            bcws=Decimal("10000"),
            bcwp=Decimal("8000"),
            acwp=Decimal("9000"),
        )
        generator = CPRFormat3Generator(program, baseline, [period])

        # Act
        report = generator.generate()

        # Assert
        assert report.total_bcws == Decimal("10000")
        assert report.total_bcwp == Decimal("8000")
        assert report.total_acwp == Decimal("9000")
        assert report.total_sv == Decimal("-2000")  # 8000 - 10000
        assert report.total_cv == Decimal("-1000")  # 8000 - 9000
        assert report.current_period == "Jan 2026"
        assert len(report.time_phase_rows) == 1

    def test_generate_with_multiple_periods_cumulative_values(self):
        """Should accumulate values across multiple periods."""
        # Arrange
        program = _make_program()
        baseline = _make_baseline()
        period1 = _make_period(
            period_name="Jan 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            bcws=Decimal("10000"),
            bcwp=Decimal("9000"),
            acwp=Decimal("9500"),
        )
        period2 = _make_period(
            period_name="Feb 2026",
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28),
            bcws=Decimal("12000"),
            bcwp=Decimal("11000"),
            acwp=Decimal("11500"),
        )
        generator = CPRFormat3Generator(program, baseline, [period1, period2])

        # Act
        report = generator.generate()

        # Assert
        assert report.total_bcws == Decimal("22000")  # 10000 + 12000
        assert report.total_bcwp == Decimal("20000")  # 9000 + 11000
        assert report.total_acwp == Decimal("21000")  # 9500 + 11500
        assert report.current_period == "Feb 2026"

    def test_generate_with_zero_bac(self):
        """Should handle zero BAC gracefully."""
        # Arrange
        program = _make_program(budget_at_completion=Decimal("0"))
        baseline = _make_baseline(total_bac=Decimal("0"))
        period = _make_period(
            bcws=Decimal("0"),
            bcwp=Decimal("0"),
            acwp=Decimal("0"),
        )
        generator = CPRFormat3Generator(program, baseline, [period])

        # Act
        report = generator.generate()

        # Assert
        assert report.bac == Decimal("0")
        assert report.percent_complete == Decimal("0")
        assert report.percent_spent == Decimal("0")

    def test_generate_calculates_cpi_correctly(self):
        """Should calculate CPI as BCWP/ACWP."""
        # Arrange
        program = _make_program()
        baseline = _make_baseline()
        period = _make_period(
            bcws=Decimal("10000"),
            bcwp=Decimal("8000"),
            acwp=Decimal("10000"),
        )
        generator = CPRFormat3Generator(program, baseline, [period])

        # Act
        report = generator.generate()

        # Assert
        # CPI = 8000/10000 = 0.80
        assert report.cpi == Decimal("0.80")

    def test_generate_calculates_spi_correctly(self):
        """Should calculate SPI as BCWP/BCWS."""
        # Arrange
        program = _make_program()
        baseline = _make_baseline()
        period = _make_period(
            bcws=Decimal("10000"),
            bcwp=Decimal("9000"),
            acwp=Decimal("9000"),
        )
        generator = CPRFormat3Generator(program, baseline, [period])

        # Act
        report = generator.generate()

        # Assert
        # SPI = 9000/10000 = 0.90
        assert report.spi == Decimal("0.90")

    def test_generate_program_name_and_code(self):
        """Should include program name and code in report."""
        # Arrange
        program = _make_program(name="Alpha Program", code="AP-100")
        baseline = _make_baseline()
        generator = CPRFormat3Generator(program, baseline, periods=[])

        # Act
        report = generator.generate()

        # Assert
        assert report.program_name == "Alpha Program"
        assert report.program_code == "AP-100"


class TestBuildTimePhaseRows:
    """Tests for CPRFormat3Generator._build_time_phase_rows()."""

    def test_time_phase_rows_count_matches_periods(self):
        """Should produce one row per period."""
        # Arrange
        periods = [
            _make_period(
                period_name=f"Period {i}",
                period_start=date(2026, i, 1),
                period_end=date(2026, i, 28),
            )
            for i in range(1, 4)
        ]
        generator = CPRFormat3Generator(_make_program(), _make_baseline(), periods)

        # Act
        rows = generator._build_time_phase_rows()

        # Assert
        assert len(rows) == 3

    def test_time_phase_rows_contain_cv_sv(self):
        """Should compute SV and CV for each row."""
        # Arrange
        period = _make_period(
            bcws=Decimal("5000"),
            bcwp=Decimal("4000"),
            acwp=Decimal("4500"),
        )
        generator = CPRFormat3Generator(_make_program(), _make_baseline(), [period])

        # Act
        rows = generator._build_time_phase_rows()

        # Assert
        row = rows[0]
        assert row.sv == Decimal("-1000")  # 4000 - 5000
        assert row.cv == Decimal("-500")  # 4000 - 4500

    def test_time_phase_rows_cumulative_values(self):
        """Should accumulate BCWS, BCWP, ACWP across rows."""
        # Arrange
        p1 = _make_period(
            period_name="P1",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            bcws=Decimal("1000"),
            bcwp=Decimal("900"),
            acwp=Decimal("950"),
        )
        p2 = _make_period(
            period_name="P2",
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28),
            bcws=Decimal("2000"),
            bcwp=Decimal("1800"),
            acwp=Decimal("1900"),
        )
        generator = CPRFormat3Generator(_make_program(), _make_baseline(), [p1, p2])

        # Act
        rows = generator._build_time_phase_rows()

        # Assert
        assert rows[1].cumulative_bcws == Decimal("3000")  # 1000 + 2000
        assert rows[1].cumulative_bcwp == Decimal("2700")  # 900 + 1800
        assert rows[1].cumulative_acwp == Decimal("2850")  # 950 + 1900


class TestForecastFinish:
    """Tests for CPRFormat3Generator._calculate_forecast_finish()."""

    def test_forecast_finish_with_spi_one_returns_end_date(self):
        """When SPI = 1.0, forecast finish should equal baseline finish."""
        # Arrange
        baseline = _make_baseline(
            scheduled_finish=date(2026, 12, 31),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        generator = CPRFormat3Generator(_make_program(), baseline, periods=[])

        # Act
        result = generator._calculate_forecast_finish(Decimal("1.00"))

        # Assert
        assert result == date(2026, 12, 31)

    def test_forecast_finish_with_spi_less_than_one(self):
        """When SPI < 1.0, forecast finish should be later than baseline."""
        # Arrange
        baseline = _make_baseline(
            scheduled_finish=date(2026, 12, 31),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        generator = CPRFormat3Generator(_make_program(), baseline, periods=[])

        # Act
        result = generator._calculate_forecast_finish(Decimal("0.50"))

        # Assert
        assert result is not None
        assert result > date(2026, 12, 31)

    def test_forecast_finish_with_zero_spi_returns_none(self):
        """When SPI = 0, should return None (cannot forecast)."""
        # Arrange
        baseline = _make_baseline()
        generator = CPRFormat3Generator(_make_program(), baseline, periods=[])

        # Act
        result = generator._calculate_forecast_finish(Decimal("0"))

        # Assert
        assert result is None

    def test_forecast_finish_with_none_spi_returns_none(self):
        """When SPI is None, should return None."""
        # Arrange
        baseline = _make_baseline()
        generator = CPRFormat3Generator(_make_program(), baseline, periods=[])

        # Act
        result = generator._calculate_forecast_finish(None)

        # Assert
        assert result is None

    def test_forecast_finish_no_baseline_finish_returns_none(self):
        """When baseline has no scheduled finish, should return None."""
        # Arrange
        baseline = _make_baseline(scheduled_finish=None)
        generator = CPRFormat3Generator(_make_program(), baseline, periods=[])

        # Act
        result = generator._calculate_forecast_finish(Decimal("1.00"))

        # Assert
        assert result is None


class TestToDict:
    """Tests for CPRFormat3Generator.to_dict()."""

    def test_to_dict_contains_all_keys(self):
        """Should contain all expected top-level keys."""
        # Arrange
        program = _make_program()
        baseline = _make_baseline()
        period = _make_period()
        generator = CPRFormat3Generator(program, baseline, [period])

        # Act
        result = generator.to_dict()

        # Assert
        expected_keys = {
            "program_name",
            "program_code",
            "contract_number",
            "baseline_name",
            "baseline_version",
            "report_date",
            "summary",
            "cumulative",
            "schedule",
            "time_phase_data",
        }
        assert set(result.keys()) == expected_keys

    def test_to_dict_summary_section(self):
        """Should contain summary section with performance metrics."""
        # Arrange
        generator = CPRFormat3Generator(
            _make_program(),
            _make_baseline(),
            [_make_period()],
        )

        # Act
        result = generator.to_dict()

        # Assert
        summary = result["summary"]
        assert "bac" in summary
        assert "cpi" in summary
        assert "spi" in summary
        assert "percent_complete" in summary
        assert "status_color" in summary

    def test_to_dict_time_phase_data_count(self):
        """Should have one entry per period in time_phase_data."""
        # Arrange
        periods = [
            _make_period(
                period_name=f"P{i}",
                period_start=date(2026, i, 1),
                period_end=date(2026, i, 28),
            )
            for i in range(1, 4)
        ]
        generator = CPRFormat3Generator(_make_program(), _make_baseline(), periods)

        # Act
        result = generator.to_dict()

        # Assert
        assert len(result["time_phase_data"]) == 3
