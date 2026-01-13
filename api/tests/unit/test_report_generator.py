"""Unit tests for Report Generator service."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.models.evms_period import PeriodStatus
from src.services.report_generator import ReportGenerator, WBSSummaryRow


@dataclass
class MockProgram:
    """Mock Program for testing."""

    id: UUID
    name: str
    code: str
    contract_number: str | None
    budget_at_completion: Decimal


class MockEVMSPeriod:
    """Mock EVMSPeriod for testing with computed properties."""

    def __init__(
        self,
        id: UUID,
        program_id: UUID,
        period_start: date,
        period_end: date,
        period_name: str,
        status: PeriodStatus,
        cumulative_bcws: Decimal,
        cumulative_bcwp: Decimal,
        cumulative_acwp: Decimal,
        notes: str | None = None,
        period_data: list[Any] | None = None,
    ):
        self.id = id
        self.program_id = program_id
        self.period_start = period_start
        self.period_end = period_end
        self.period_name = period_name
        self.status = status
        self.cumulative_bcws = cumulative_bcws
        self.cumulative_bcwp = cumulative_bcwp
        self.cumulative_acwp = cumulative_acwp
        self.notes = notes
        self.period_data = period_data or []

    @property
    def cost_variance(self) -> Decimal:
        """Calculate Cost Variance (CV = BCWP - ACWP)."""
        return self.cumulative_bcwp - self.cumulative_acwp

    @property
    def schedule_variance(self) -> Decimal:
        """Calculate Schedule Variance (SV = BCWP - BCWS)."""
        return self.cumulative_bcwp - self.cumulative_bcws

    @property
    def cpi(self) -> Decimal | None:
        """Calculate Cost Performance Index (CPI = BCWP / ACWP)."""
        if self.cumulative_acwp == 0:
            return None
        return (self.cumulative_bcwp / self.cumulative_acwp).quantize(Decimal("0.01"))

    @property
    def spi(self) -> Decimal | None:
        """Calculate Schedule Performance Index (SPI = BCWP / BCWS)."""
        if self.cumulative_bcws == 0:
            return None
        return (self.cumulative_bcwp / self.cumulative_bcws).quantize(Decimal("0.01"))


@dataclass
class MockWBSElement:
    """Mock WBSElement for testing."""

    id: UUID
    program_id: UUID
    wbs_code: str
    name: str
    path: str
    level: int
    is_control_account: bool
    budget_at_completion: Decimal


@dataclass
class MockEVMSPeriodData:
    """Mock EVMSPeriodData for testing."""

    id: UUID
    period_id: UUID
    wbs_id: UUID
    bcws: Decimal
    bcwp: Decimal
    acwp: Decimal
    cumulative_bcws: Decimal
    cumulative_bcwp: Decimal
    cumulative_acwp: Decimal
    cv: Decimal
    sv: Decimal
    cpi: Decimal | None
    spi: Decimal | None


class TestReportGenerator:
    """Tests for ReportGenerator class."""

    @pytest.fixture
    def sample_program(self) -> MockProgram:
        """Create a sample program."""
        return MockProgram(
            id=uuid4(),
            name="Test Defense Program",
            code="TDP-001",
            contract_number="W912DQ-24-C-0001",
            budget_at_completion=Decimal("1000000.00"),
        )

    @pytest.fixture
    def sample_period(self, sample_program: MockProgram) -> MockEVMSPeriod:
        """Create a sample period."""
        return MockEVMSPeriod(
            id=uuid4(),
            program_id=sample_program.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            period_name="January 2024",
            status=PeriodStatus.APPROVED,
            cumulative_bcws=Decimal("150000.00"),
            cumulative_bcwp=Decimal("140000.00"),
            cumulative_acwp=Decimal("145000.00"),
            notes=None,
            period_data=[],
        )

    @pytest.fixture
    def sample_wbs_elements(self, sample_program: MockProgram) -> list[MockWBSElement]:
        """Create sample WBS elements."""
        wbs1 = MockWBSElement(
            id=uuid4(),
            program_id=sample_program.id,
            wbs_code="1.0",
            name="Program Management",
            path="1",
            level=1,
            is_control_account=True,
            budget_at_completion=Decimal("300000.00"),
        )

        wbs2 = MockWBSElement(
            id=uuid4(),
            program_id=sample_program.id,
            wbs_code="1.1",
            name="Design",
            path="1.1",
            level=2,
            is_control_account=True,
            budget_at_completion=Decimal("200000.00"),
        )

        return [wbs1, wbs2]

    @pytest.fixture
    def sample_period_data(
        self, sample_period: MockEVMSPeriod, sample_wbs_elements: list[MockWBSElement]
    ) -> list[MockEVMSPeriodData]:
        """Create sample period data."""
        data1 = MockEVMSPeriodData(
            id=uuid4(),
            period_id=sample_period.id,
            wbs_id=sample_wbs_elements[0].id,
            bcws=Decimal("50000.00"),
            bcwp=Decimal("50000.00"),
            acwp=Decimal("48000.00"),
            cumulative_bcws=Decimal("50000.00"),
            cumulative_bcwp=Decimal("50000.00"),
            cumulative_acwp=Decimal("48000.00"),
            cv=Decimal("2000.00"),
            sv=Decimal("0.00"),
            cpi=Decimal("1.04"),
            spi=Decimal("1.00"),
        )

        data2 = MockEVMSPeriodData(
            id=uuid4(),
            period_id=sample_period.id,
            wbs_id=sample_wbs_elements[1].id,
            bcws=Decimal("100000.00"),
            bcwp=Decimal("90000.00"),
            acwp=Decimal("97000.00"),
            cumulative_bcws=Decimal("100000.00"),
            cumulative_bcwp=Decimal("90000.00"),
            cumulative_acwp=Decimal("97000.00"),
            cv=Decimal("-7000.00"),
            sv=Decimal("-10000.00"),
            cpi=Decimal("0.93"),
            spi=Decimal("0.90"),
        )

        return [data1, data2]

    def test_generate_cpr_format1_basic(
        self,
        sample_program: MockProgram,
        sample_period: MockEVMSPeriod,
        sample_wbs_elements: list[MockWBSElement],
        sample_period_data: list[MockEVMSPeriodData],
    ):
        """Test basic CPR Format 1 report generation."""
        generator = ReportGenerator(
            program=sample_program,
            period=sample_period,
            period_data=sample_period_data,
            wbs_elements=sample_wbs_elements,
        )

        report = generator.generate_cpr_format1()

        assert report.program_name == "Test Defense Program"
        assert report.program_code == "TDP-001"
        assert report.contract_number == "W912DQ-24-C-0001"
        assert report.reporting_period == "January 2024"
        assert len(report.wbs_rows) == 2

    def test_generate_cpr_format1_totals(
        self,
        sample_program: MockProgram,
        sample_period: MockEVMSPeriod,
        sample_wbs_elements: list[MockWBSElement],
        sample_period_data: list[MockEVMSPeriodData],
    ):
        """Test CPR Format 1 totals calculation."""
        generator = ReportGenerator(
            program=sample_program,
            period=sample_period,
            period_data=sample_period_data,
            wbs_elements=sample_wbs_elements,
        )

        report = generator.generate_cpr_format1()

        assert report.total_bac == Decimal("1000000.00")
        assert report.total_bcws == Decimal("150000.00")
        assert report.total_bcwp == Decimal("140000.00")
        assert report.total_acwp == Decimal("145000.00")

    def test_generate_cpr_format1_empty_data(
        self,
        sample_program: MockProgram,
        sample_period: MockEVMSPeriod,
        sample_wbs_elements: list[MockWBSElement],
    ):
        """Test CPR Format 1 with empty period data."""
        generator = ReportGenerator(
            program=sample_program,
            period=sample_period,
            period_data=[],
            wbs_elements=sample_wbs_elements,
        )

        report = generator.generate_cpr_format1()

        assert len(report.wbs_rows) == 2
        # WBS rows should have zero values
        for row in report.wbs_rows:
            assert row.bcws == Decimal("0")
            assert row.bcwp == Decimal("0")
            assert row.acwp == Decimal("0")

    def test_to_dict(
        self,
        sample_program: MockProgram,
        sample_period: MockEVMSPeriod,
        sample_wbs_elements: list[MockWBSElement],
        sample_period_data: list[MockEVMSPeriodData],
    ):
        """Test conversion to dictionary."""
        generator = ReportGenerator(
            program=sample_program,
            period=sample_period,
            period_data=sample_period_data,
            wbs_elements=sample_wbs_elements,
        )

        report = generator.generate_cpr_format1()
        report_dict = generator.to_dict(report)

        assert report_dict["program_name"] == "Test Defense Program"
        assert "totals" in report_dict
        assert "wbs_rows" in report_dict
        assert len(report_dict["wbs_rows"]) == 2
        assert report_dict["totals"]["bac"] == "1000000.00"

    def test_to_html(
        self,
        sample_program: MockProgram,
        sample_period: MockEVMSPeriod,
        sample_wbs_elements: list[MockWBSElement],
        sample_period_data: list[MockEVMSPeriodData],
    ):
        """Test HTML generation."""
        generator = ReportGenerator(
            program=sample_program,
            period=sample_period,
            period_data=sample_period_data,
            wbs_elements=sample_wbs_elements,
        )

        report = generator.generate_cpr_format1()
        html = generator.to_html(report)

        assert "<!DOCTYPE html>" in html
        assert "Contract Performance Report" in html
        assert "Test Defense Program" in html
        assert "WBS Summary" in html
        assert "Program Management" in html

    def test_variance_notes_generation(
        self,
        sample_program: MockProgram,
        sample_period: MockEVMSPeriod,
        sample_wbs_elements: list[MockWBSElement],
    ):
        """Test variance notes generation for items exceeding threshold."""
        # Create data with large variances
        data = MockEVMSPeriodData(
            id=uuid4(),
            period_id=sample_period.id,
            wbs_id=sample_wbs_elements[0].id,
            bcws=Decimal("100000.00"),
            bcwp=Decimal("80000.00"),  # -20% schedule variance
            acwp=Decimal("120000.00"),  # -33% cost variance
            cumulative_bcws=Decimal("100000.00"),
            cumulative_bcwp=Decimal("80000.00"),
            cumulative_acwp=Decimal("120000.00"),
            cv=Decimal("-40000.00"),
            sv=Decimal("-20000.00"),
            cpi=Decimal("0.67"),
            spi=Decimal("0.80"),
        )

        generator = ReportGenerator(
            program=sample_program,
            period=sample_period,
            period_data=[data],
            wbs_elements=sample_wbs_elements,
        )

        report = generator.generate_cpr_format1()

        # Should have variance notes for the large variances
        assert len(report.variance_notes) >= 1

    def test_percent_metrics_calculation(
        self,
        sample_program: MockProgram,
        sample_period: MockEVMSPeriod,
        sample_wbs_elements: list[MockWBSElement],
        sample_period_data: list[MockEVMSPeriodData],
    ):
        """Test percent complete and percent spent calculation."""
        generator = ReportGenerator(
            program=sample_program,
            period=sample_period,
            period_data=sample_period_data,
            wbs_elements=sample_wbs_elements,
        )

        report = generator.generate_cpr_format1()

        # percent_complete = (BCWP / BAC) * 100 = (140000 / 1000000) * 100 = 14%
        assert report.percent_complete == Decimal("14.00")
        # percent_spent = (ACWP / BAC) * 100 = (145000 / 1000000) * 100 = 14.5%
        assert report.percent_spent == Decimal("14.50")

    def test_zero_bac_handling(
        self,
        sample_period: MockEVMSPeriod,
        sample_wbs_elements: list[MockWBSElement],
    ):
        """Test handling when BAC is zero."""
        program = MockProgram(
            id=uuid4(),
            name="Zero BAC Program",
            code="ZBP-001",
            contract_number=None,
            budget_at_completion=Decimal("0.00"),
        )

        generator = ReportGenerator(
            program=program,
            period=sample_period,
            period_data=[],
            wbs_elements=sample_wbs_elements,
        )

        report = generator.generate_cpr_format1()

        assert report.percent_complete == Decimal("0")
        assert report.percent_spent == Decimal("0")


class TestWBSSummaryRow:
    """Tests for WBSSummaryRow dataclass."""

    def test_create_row(self):
        """Test creating a WBS summary row."""
        row = WBSSummaryRow(
            wbs_code="1.0",
            wbs_name="Test Element",
            level=1,
            is_control_account=True,
            bac=Decimal("100000.00"),
            bcws=Decimal("50000.00"),
            bcwp=Decimal("48000.00"),
            acwp=Decimal("45000.00"),
            cv=Decimal("3000.00"),
            sv=Decimal("-2000.00"),
            cpi=Decimal("1.07"),
            spi=Decimal("0.96"),
            eac=Decimal("93458.00"),
            etc=Decimal("48458.00"),
            vac=Decimal("6542.00"),
        )

        assert row.wbs_code == "1.0"
        assert row.is_control_account is True
        assert row.cv == Decimal("3000.00")

    def test_row_with_none_values(self):
        """Test row with None values for optional fields."""
        row = WBSSummaryRow(
            wbs_code="1.0",
            wbs_name="Test Element",
            level=1,
            is_control_account=False,
            bac=Decimal("100000.00"),
            bcws=Decimal("0.00"),
            bcwp=Decimal("0.00"),
            acwp=Decimal("0.00"),
            cv=Decimal("0.00"),
            sv=Decimal("0.00"),
            cpi=None,
            spi=None,
            eac=None,
            etc=None,
            vac=None,
        )

        assert row.cpi is None
        assert row.spi is None
        assert row.eac is None
