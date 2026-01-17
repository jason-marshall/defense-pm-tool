"""Tests for CPR Format 3 (Baseline) report generation."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from src.schemas.cpr_format3 import CPRFormat3Report, TimePhaseRow
from src.services.cpr_format3_generator import CPRFormat3Generator

# Mock classes for testing


@dataclass
class MockProgram:
    """Mock program for testing."""

    name: str = "Test Program"
    code: str = "TP-001"
    contract_number: str | None = "FA8802-24-C-0001"
    budget_at_completion: Decimal | None = Decimal("1000000.00")


@dataclass
class MockBaseline:
    """Mock baseline for testing."""

    name: str = "Initial Baseline"
    version: int = 1
    total_bac: Decimal = Decimal("1000000.00")
    scheduled_finish: date | None = date(2026, 12, 31)
    created_at: datetime = datetime(2026, 1, 1, 0, 0, 0)


@dataclass
class MockEVMSPeriod:
    """Mock EVMS period for testing."""

    period_name: str
    period_start: date
    period_end: date
    bcws: Decimal | None
    bcwp: Decimal | None
    acwp: Decimal | None


class TestTimePhaseRow:
    """Tests for TimePhaseRow dataclass."""

    def test_basic_creation(self):
        """Should create a time phase row with all fields."""
        row = TimePhaseRow(
            period_name="Jan 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            bcws=Decimal("100000"),
            bcwp=Decimal("95000"),
            acwp=Decimal("98000"),
            cumulative_bcws=Decimal("100000"),
            cumulative_bcwp=Decimal("95000"),
            cumulative_acwp=Decimal("98000"),
            sv=Decimal("-5000"),
            cv=Decimal("-3000"),
        )

        assert row.period_name == "Jan 2026"
        assert row.bcws == Decimal("100000")
        assert row.sv == Decimal("-5000")

    def test_period_spi(self):
        """Should calculate period SPI correctly."""
        row = TimePhaseRow(
            period_name="Jan 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            bcws=Decimal("100000"),
            bcwp=Decimal("95000"),
            acwp=Decimal("98000"),
            cumulative_bcws=Decimal("100000"),
            cumulative_bcwp=Decimal("95000"),
            cumulative_acwp=Decimal("98000"),
            sv=Decimal("-5000"),
            cv=Decimal("-3000"),
        )

        assert row.spi == Decimal("0.950")

    def test_period_cpi(self):
        """Should calculate period CPI correctly."""
        row = TimePhaseRow(
            period_name="Jan 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            bcws=Decimal("100000"),
            bcwp=Decimal("95000"),
            acwp=Decimal("98000"),
            cumulative_bcws=Decimal("100000"),
            cumulative_bcwp=Decimal("95000"),
            cumulative_acwp=Decimal("98000"),
            sv=Decimal("-5000"),
            cv=Decimal("-3000"),
        )

        assert row.cpi == Decimal("0.969")

    def test_cumulative_indices(self):
        """Should calculate cumulative SPI and CPI."""
        row = TimePhaseRow(
            period_name="Feb 2026",
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28),
            bcws=Decimal("50000"),
            bcwp=Decimal("48000"),
            acwp=Decimal("52000"),
            cumulative_bcws=Decimal("150000"),
            cumulative_bcwp=Decimal("143000"),
            cumulative_acwp=Decimal("150000"),
            sv=Decimal("-2000"),
            cv=Decimal("-4000"),
        )

        # Cumulative SPI = 143000 / 150000 = 0.953
        assert row.cumulative_spi == Decimal("0.953")
        # Cumulative CPI = 143000 / 150000 = 0.953
        assert row.cumulative_cpi == Decimal("0.953")

    def test_spi_with_zero_bcws(self):
        """Should return None for SPI when BCWS is zero."""
        row = TimePhaseRow(
            period_name="Period X",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            bcws=Decimal("0"),
            bcwp=Decimal("0"),
            acwp=Decimal("0"),
            cumulative_bcws=Decimal("0"),
            cumulative_bcwp=Decimal("0"),
            cumulative_acwp=Decimal("0"),
            sv=Decimal("0"),
            cv=Decimal("0"),
        )

        assert row.spi is None
        assert row.cumulative_spi is None


class TestCPRFormat3Report:
    """Tests for CPRFormat3Report dataclass."""

    def test_is_behind_schedule(self):
        """Should detect behind schedule status."""
        report = CPRFormat3Report(
            program_name="Test",
            program_code="T001",
            contract_number=None,
            baseline_name="Baseline",
            baseline_version=1,
            report_date=date.today(),
            bac=Decimal("1000000"),
            current_period="Jan 2026",
            percent_complete=Decimal("50.00"),
            percent_spent=Decimal("55.00"),
            total_bcws=Decimal("500000"),
            total_bcwp=Decimal("450000"),
            total_acwp=Decimal("550000"),
            total_sv=Decimal("-50000"),  # Behind
            total_cv=Decimal("-100000"),
            eac=Decimal("1100000"),
            etc=Decimal("550000"),
            vac=Decimal("-100000"),
            cpi=Decimal("0.818"),
            spi=Decimal("0.900"),
            tcpi=Decimal("1.222"),
        )

        assert report.is_behind_schedule is True

    def test_is_over_budget(self):
        """Should detect over budget status."""
        report = CPRFormat3Report(
            program_name="Test",
            program_code="T001",
            contract_number=None,
            baseline_name="Baseline",
            baseline_version=1,
            report_date=date.today(),
            bac=Decimal("1000000"),
            current_period="Jan 2026",
            percent_complete=Decimal("50.00"),
            percent_spent=Decimal("55.00"),
            total_bcws=Decimal("500000"),
            total_bcwp=Decimal("500000"),
            total_acwp=Decimal("550000"),
            total_sv=Decimal("0"),
            total_cv=Decimal("-50000"),  # Over budget
            eac=Decimal("1100000"),
            etc=Decimal("550000"),
            vac=Decimal("-100000"),
            cpi=Decimal("0.909"),
            spi=Decimal("1.000"),
            tcpi=Decimal("1.111"),
        )

        assert report.is_over_budget is True
        assert report.is_behind_schedule is False

    def test_status_color_green(self):
        """Should return green when both indices >= 0.9."""
        report = CPRFormat3Report(
            program_name="Test",
            program_code="T001",
            contract_number=None,
            baseline_name="Baseline",
            baseline_version=1,
            report_date=date.today(),
            bac=Decimal("1000000"),
            current_period="Jan 2026",
            percent_complete=Decimal("50.00"),
            percent_spent=Decimal("48.00"),
            total_bcws=Decimal("500000"),
            total_bcwp=Decimal("510000"),
            total_acwp=Decimal("480000"),
            total_sv=Decimal("10000"),
            total_cv=Decimal("30000"),
            eac=Decimal("950000"),
            etc=Decimal("470000"),
            vac=Decimal("50000"),
            cpi=Decimal("1.063"),
            spi=Decimal("1.020"),
            tcpi=Decimal("0.942"),
        )

        assert report.status_color == "green"

    def test_status_color_yellow(self):
        """Should return yellow when one index < 0.9."""
        report = CPRFormat3Report(
            program_name="Test",
            program_code="T001",
            contract_number=None,
            baseline_name="Baseline",
            baseline_version=1,
            report_date=date.today(),
            bac=Decimal("1000000"),
            current_period="Jan 2026",
            percent_complete=Decimal("50.00"),
            percent_spent=Decimal("55.00"),
            total_bcws=Decimal("500000"),
            total_bcwp=Decimal("500000"),
            total_acwp=Decimal("550000"),
            total_sv=Decimal("0"),
            total_cv=Decimal("-50000"),
            eac=Decimal("1100000"),
            etc=Decimal("550000"),
            vac=Decimal("-100000"),
            cpi=Decimal("0.850"),  # < 0.9
            spi=Decimal("1.000"),  # >= 0.9
            tcpi=Decimal("1.111"),
        )

        assert report.status_color == "yellow"

    def test_status_color_red(self):
        """Should return red when both indices < 0.9."""
        report = CPRFormat3Report(
            program_name="Test",
            program_code="T001",
            contract_number=None,
            baseline_name="Baseline",
            baseline_version=1,
            report_date=date.today(),
            bac=Decimal("1000000"),
            current_period="Jan 2026",
            percent_complete=Decimal("40.00"),
            percent_spent=Decimal("55.00"),
            total_bcws=Decimal("500000"),
            total_bcwp=Decimal("400000"),
            total_acwp=Decimal("550000"),
            total_sv=Decimal("-100000"),
            total_cv=Decimal("-150000"),
            eac=Decimal("1300000"),
            etc=Decimal("750000"),
            vac=Decimal("-300000"),
            cpi=Decimal("0.727"),  # < 0.9
            spi=Decimal("0.800"),  # < 0.9
            tcpi=Decimal("1.333"),
        )

        assert report.status_color == "red"

    def test_get_period_by_name(self):
        """Should retrieve period by name."""
        rows = [
            TimePhaseRow(
                period_name="Jan 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                bcws=Decimal("100000"),
                bcwp=Decimal("95000"),
                acwp=Decimal("98000"),
                cumulative_bcws=Decimal("100000"),
                cumulative_bcwp=Decimal("95000"),
                cumulative_acwp=Decimal("98000"),
                sv=Decimal("-5000"),
                cv=Decimal("-3000"),
            ),
            TimePhaseRow(
                period_name="Feb 2026",
                period_start=date(2026, 2, 1),
                period_end=date(2026, 2, 28),
                bcws=Decimal("100000"),
                bcwp=Decimal("100000"),
                acwp=Decimal("102000"),
                cumulative_bcws=Decimal("200000"),
                cumulative_bcwp=Decimal("195000"),
                cumulative_acwp=Decimal("200000"),
                sv=Decimal("0"),
                cv=Decimal("-2000"),
            ),
        ]

        report = CPRFormat3Report(
            program_name="Test",
            program_code="T001",
            contract_number=None,
            baseline_name="Baseline",
            baseline_version=1,
            report_date=date.today(),
            bac=Decimal("1000000"),
            current_period="Feb 2026",
            percent_complete=Decimal("19.50"),
            percent_spent=Decimal("20.00"),
            total_bcws=Decimal("200000"),
            total_bcwp=Decimal("195000"),
            total_acwp=Decimal("200000"),
            total_sv=Decimal("-5000"),
            total_cv=Decimal("-5000"),
            eac=Decimal("1025641"),
            etc=Decimal("825641"),
            vac=Decimal("-25641"),
            cpi=Decimal("0.975"),
            spi=Decimal("0.975"),
            tcpi=Decimal("1.006"),
            time_phase_rows=rows,
        )

        feb = report.get_period_by_name("Feb 2026")
        assert feb is not None
        assert feb.bcws == Decimal("100000")

        missing = report.get_period_by_name("Mar 2026")
        assert missing is None


class TestCPRFormat3Generator:
    """Tests for CPR Format 3 generator."""

    def test_generate_empty_periods(self):
        """Should handle empty periods list."""
        program = MockProgram()
        baseline = MockBaseline()

        generator = CPRFormat3Generator(program, baseline, [])
        report = generator.generate()

        assert report.program_name == "Test Program"
        assert report.total_bcws == Decimal("0")
        assert report.total_bcwp == Decimal("0")
        assert report.total_acwp == Decimal("0")
        assert len(report.time_phase_rows) == 0

    def test_generate_single_period(self):
        """Should generate report with single period."""
        program = MockProgram()
        baseline = MockBaseline()
        periods = [
            MockEVMSPeriod(
                period_name="Jan 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                bcws=Decimal("100000"),
                bcwp=Decimal("95000"),
                acwp=Decimal("98000"),
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        report = generator.generate()

        assert len(report.time_phase_rows) == 1
        assert report.total_bcws == Decimal("100000")
        assert report.total_bcwp == Decimal("95000")
        assert report.total_acwp == Decimal("98000")
        assert report.total_sv == Decimal("-5000")
        assert report.total_cv == Decimal("-3000")

    def test_generate_multiple_periods(self):
        """Should generate report with cumulative calculations."""
        program = MockProgram()
        baseline = MockBaseline()
        periods = [
            MockEVMSPeriod(
                period_name="Jan 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                bcws=Decimal("100000"),
                bcwp=Decimal("95000"),
                acwp=Decimal("98000"),
            ),
            MockEVMSPeriod(
                period_name="Feb 2026",
                period_start=date(2026, 2, 1),
                period_end=date(2026, 2, 28),
                bcws=Decimal("100000"),
                bcwp=Decimal("105000"),
                acwp=Decimal("102000"),
            ),
            MockEVMSPeriod(
                period_name="Mar 2026",
                period_start=date(2026, 3, 1),
                period_end=date(2026, 3, 31),
                bcws=Decimal("100000"),
                bcwp=Decimal("100000"),
                acwp=Decimal("100000"),
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        report = generator.generate()

        assert len(report.time_phase_rows) == 3

        # Check cumulative values for last row
        last_row = report.time_phase_rows[-1]
        assert last_row.cumulative_bcws == Decimal("300000")
        assert last_row.cumulative_bcwp == Decimal("300000")
        assert last_row.cumulative_acwp == Decimal("300000")

        # Total values should match cumulative of last row
        assert report.total_bcws == Decimal("300000")
        assert report.total_bcwp == Decimal("300000")
        assert report.total_acwp == Decimal("300000")

    def test_generate_percent_complete(self):
        """Should calculate percent complete correctly."""
        program = MockProgram(budget_at_completion=Decimal("1000000"))
        baseline = MockBaseline(total_bac=Decimal("1000000"))
        periods = [
            MockEVMSPeriod(
                period_name="Jan 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                bcws=Decimal("200000"),
                bcwp=Decimal("250000"),  # 25% complete
                acwp=Decimal("240000"),
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        report = generator.generate()

        assert report.percent_complete == Decimal("25.00")
        assert report.percent_spent == Decimal("24.00")

    def test_generate_performance_indices(self):
        """Should calculate CPI and SPI correctly."""
        program = MockProgram()
        baseline = MockBaseline()
        periods = [
            MockEVMSPeriod(
                period_name="Jan 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                bcws=Decimal("100000"),
                bcwp=Decimal("90000"),  # SPI = 0.9
                acwp=Decimal("100000"),  # CPI = 0.9
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        report = generator.generate()

        assert report.spi == Decimal("0.900")
        assert report.cpi == Decimal("0.900")

    def test_generate_eac_etc_vac(self):
        """Should calculate EAC, ETC, and VAC."""
        program = MockProgram(budget_at_completion=Decimal("1000000"))
        baseline = MockBaseline(total_bac=Decimal("1000000"))
        periods = [
            MockEVMSPeriod(
                period_name="Jan 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                bcws=Decimal("100000"),
                bcwp=Decimal("100000"),
                acwp=Decimal("110000"),  # CPI = 0.909
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        report = generator.generate()

        # EAC = BAC / CPI = 1000000 / 0.909 ≈ 1100110
        assert report.eac > Decimal("1000000")
        # ETC = EAC - ACWP
        assert report.etc == report.eac - Decimal("110000")
        # VAC = BAC - EAC
        assert report.vac == Decimal("1000000") - report.eac

    def test_generate_forecast_finish(self):
        """Should calculate forecast finish date from SPI."""
        program = MockProgram()
        baseline = MockBaseline(
            scheduled_finish=date(2026, 12, 31),
            created_at=datetime(2026, 1, 1, 0, 0, 0),
        )
        periods = [
            MockEVMSPeriod(
                period_name="Jun 2026",
                period_start=date(2026, 6, 1),
                period_end=date(2026, 6, 30),
                bcws=Decimal("500000"),
                bcwp=Decimal("450000"),  # SPI = 0.9
                acwp=Decimal("500000"),
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        report = generator.generate()

        # Original duration: 365 days
        # Adjusted duration: 365 / 0.9 ≈ 406 days
        assert report.baseline_finish_date == date(2026, 12, 31)
        assert report.forecast_finish_date is not None
        assert report.forecast_finish_date > report.baseline_finish_date
        assert report.schedule_variance_days > 0

    def test_generate_ahead_of_schedule(self):
        """Should handle ahead of schedule (SPI > 1)."""
        program = MockProgram()
        baseline = MockBaseline(
            scheduled_finish=date(2026, 12, 31),
            created_at=datetime(2026, 1, 1, 0, 0, 0),
        )
        periods = [
            MockEVMSPeriod(
                period_name="Jun 2026",
                period_start=date(2026, 6, 1),
                period_end=date(2026, 6, 30),
                bcws=Decimal("500000"),
                bcwp=Decimal("550000"),  # SPI = 1.1
                acwp=Decimal("500000"),
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        report = generator.generate()

        # Should forecast earlier finish
        assert report.forecast_finish_date is not None
        assert report.forecast_finish_date < report.baseline_finish_date
        assert report.schedule_variance_days < 0  # Negative means ahead

    def test_generate_handles_none_values(self):
        """Should handle None EVMS values."""
        program = MockProgram()
        baseline = MockBaseline()
        periods = [
            MockEVMSPeriod(
                period_name="Jan 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                bcws=None,
                bcwp=None,
                acwp=None,
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        report = generator.generate()

        assert report.total_bcws == Decimal("0")
        assert report.total_bcwp == Decimal("0")
        assert report.total_acwp == Decimal("0")

    def test_generate_sorts_periods(self):
        """Should sort periods by date."""
        program = MockProgram()
        baseline = MockBaseline()
        # Provide periods out of order
        periods = [
            MockEVMSPeriod(
                period_name="Mar 2026",
                period_start=date(2026, 3, 1),
                period_end=date(2026, 3, 31),
                bcws=Decimal("100000"),
                bcwp=Decimal("100000"),
                acwp=Decimal("100000"),
            ),
            MockEVMSPeriod(
                period_name="Jan 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                bcws=Decimal("100000"),
                bcwp=Decimal("100000"),
                acwp=Decimal("100000"),
            ),
            MockEVMSPeriod(
                period_name="Feb 2026",
                period_start=date(2026, 2, 1),
                period_end=date(2026, 2, 28),
                bcws=Decimal("100000"),
                bcwp=Decimal("100000"),
                acwp=Decimal("100000"),
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        report = generator.generate()

        # Should be sorted
        assert report.time_phase_rows[0].period_name == "Jan 2026"
        assert report.time_phase_rows[1].period_name == "Feb 2026"
        assert report.time_phase_rows[2].period_name == "Mar 2026"

    def test_to_dict(self):
        """Should convert report to dictionary format."""
        program = MockProgram()
        baseline = MockBaseline()
        periods = [
            MockEVMSPeriod(
                period_name="Jan 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                bcws=Decimal("100000"),
                bcwp=Decimal("95000"),
                acwp=Decimal("98000"),
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        result = generator.to_dict()

        assert result["program_name"] == "Test Program"
        assert result["program_code"] == "TP-001"
        assert result["baseline_name"] == "Initial Baseline"
        assert result["baseline_version"] == 1
        assert "summary" in result
        assert "cumulative" in result
        assert "schedule" in result
        assert "time_phase_data" in result
        assert len(result["time_phase_data"]) == 1

    def test_to_dict_summary_fields(self):
        """Should include all summary fields in dict."""
        program = MockProgram()
        baseline = MockBaseline()
        periods = [
            MockEVMSPeriod(
                period_name="Jan 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                bcws=Decimal("100000"),
                bcwp=Decimal("95000"),
                acwp=Decimal("98000"),
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        result = generator.to_dict()

        summary = result["summary"]
        assert "bac" in summary
        assert "eac" in summary
        assert "etc" in summary
        assert "vac" in summary
        assert "percent_complete" in summary
        assert "percent_spent" in summary
        assert "cpi" in summary
        assert "spi" in summary
        assert "tcpi" in summary
        assert "status_color" in summary


class TestCPRFormat3GeneratorEdgeCases:
    """Edge case tests for CPR Format 3 generator."""

    def test_zero_bac(self):
        """Should handle zero BAC gracefully."""
        program = MockProgram(budget_at_completion=Decimal("0"))
        baseline = MockBaseline(total_bac=Decimal("0"))
        periods = [
            MockEVMSPeriod(
                period_name="Jan 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                bcws=Decimal("100000"),
                bcwp=Decimal("95000"),
                acwp=Decimal("98000"),
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        report = generator.generate()

        assert report.percent_complete == Decimal("0")
        assert report.percent_spent == Decimal("0")

    def test_no_scheduled_finish(self):
        """Should handle missing scheduled finish date."""
        program = MockProgram()
        baseline = MockBaseline(scheduled_finish=None)
        periods = [
            MockEVMSPeriod(
                period_name="Jan 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                bcws=Decimal("100000"),
                bcwp=Decimal("95000"),
                acwp=Decimal("98000"),
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        report = generator.generate()

        assert report.baseline_finish_date is None
        assert report.forecast_finish_date is None
        assert report.schedule_variance_days == 0

    def test_very_low_spi(self):
        """Should handle very low SPI (project severely behind)."""
        program = MockProgram()
        baseline = MockBaseline(
            scheduled_finish=date(2026, 12, 31),
            created_at=datetime(2026, 1, 1, 0, 0, 0),
        )
        periods = [
            MockEVMSPeriod(
                period_name="Jun 2026",
                period_start=date(2026, 6, 1),
                period_end=date(2026, 6, 30),
                bcws=Decimal("500000"),
                bcwp=Decimal("100000"),  # SPI = 0.2 (severely behind)
                acwp=Decimal("500000"),
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        report = generator.generate()

        # Should forecast much later finish
        assert report.forecast_finish_date is not None
        assert report.forecast_finish_date > date(2027, 1, 1)  # Well into next year

    def test_negative_variances(self):
        """Should calculate negative variances correctly."""
        program = MockProgram()
        baseline = MockBaseline()
        periods = [
            MockEVMSPeriod(
                period_name="Jan 2026",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                bcws=Decimal("100000"),
                bcwp=Decimal("80000"),  # Behind schedule
                acwp=Decimal("120000"),  # Over budget
            ),
        ]

        generator = CPRFormat3Generator(program, baseline, periods)
        report = generator.generate()

        assert report.total_sv == Decimal("-20000")  # Negative = behind
        assert report.total_cv == Decimal("-40000")  # Negative = over budget
        assert report.is_behind_schedule is True
        assert report.is_over_budget is True
