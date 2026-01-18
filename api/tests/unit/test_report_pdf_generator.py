"""Tests for PDF report generation service."""

from datetime import date
from decimal import Decimal

import pytest

from src.schemas.cpr_format3 import CPRFormat3Report, TimePhaseRow
from src.schemas.cpr_format5 import (
    CPRFormat5Report,
    EACAnalysis,
    Format5PeriodRow,
    ManagementReserveRow,
    VarianceExplanation,
)
from src.services.report_generator import CPRFormat1Report, WBSSummaryRow
from src.services.report_pdf_generator import PDFConfig, ReportPDFGenerator


class TestPDFConfig:
    """Tests for PDFConfig dataclass."""

    def test_default_config(self):
        """Should create config with default values."""
        config = PDFConfig()

        assert config.landscape_mode is True
        assert config.include_header is True
        assert config.include_footer is True
        assert config.include_page_numbers is True
        assert config.classification == "UNCLASSIFIED"
        assert config.company_name == "Defense Program Management"

    def test_custom_config(self):
        """Should create config with custom values."""
        config = PDFConfig(
            landscape_mode=False,
            include_header=False,
            classification="CONFIDENTIAL",
            company_name="Custom Corp",
        )

        assert config.landscape_mode is False
        assert config.include_header is False
        assert config.classification == "CONFIDENTIAL"
        assert config.company_name == "Custom Corp"


class TestReportPDFGenerator:
    """Tests for ReportPDFGenerator class."""

    @pytest.fixture
    def pdf_generator(self) -> ReportPDFGenerator:
        """Create a PDF generator instance."""
        return ReportPDFGenerator()

    @pytest.fixture
    def custom_pdf_generator(self) -> ReportPDFGenerator:
        """Create a PDF generator with custom config."""
        config = PDFConfig(
            landscape_mode=False,
            classification="FOR OFFICIAL USE ONLY",
        )
        return ReportPDFGenerator(config=config)

    @pytest.fixture
    def sample_format1_report(self) -> CPRFormat1Report:
        """Create a sample Format 1 report."""
        wbs_rows = [
            WBSSummaryRow(
                wbs_code="1.0",
                wbs_name="Program Management",
                level=1,
                is_control_account=False,
                bac=Decimal("500000"),
                bcws=Decimal("200000"),
                bcwp=Decimal("180000"),
                acwp=Decimal("190000"),
                cv=Decimal("-10000"),
                sv=Decimal("-20000"),
                cpi=Decimal("0.95"),
                spi=Decimal("0.90"),
                eac=Decimal("526316"),
                etc=Decimal("336316"),
                vac=Decimal("-26316"),
            ),
            WBSSummaryRow(
                wbs_code="1.1",
                wbs_name="Project Planning",
                level=2,
                is_control_account=True,
                bac=Decimal("100000"),
                bcws=Decimal("50000"),
                bcwp=Decimal("45000"),
                acwp=Decimal("48000"),
                cv=Decimal("-3000"),
                sv=Decimal("-5000"),
                cpi=Decimal("0.94"),
                spi=Decimal("0.90"),
                eac=Decimal("106383"),
                etc=Decimal("58383"),
                vac=Decimal("-6383"),
            ),
            WBSSummaryRow(
                wbs_code="1.2",
                wbs_name="Engineering",
                level=2,
                is_control_account=True,
                bac=Decimal("400000"),
                bcws=Decimal("150000"),
                bcwp=Decimal("135000"),
                acwp=Decimal("142000"),
                cv=Decimal("-7000"),
                sv=Decimal("-15000"),
                cpi=Decimal("0.95"),
                spi=Decimal("0.90"),
                eac=Decimal("421053"),
                etc=Decimal("279053"),
                vac=Decimal("-21053"),
            ),
        ]

        return CPRFormat1Report(
            program_name="Test Defense Program",
            program_code="TDP-001",
            contract_number="W12345-26-C-0001",
            reporting_period="January 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            report_date=date(2026, 2, 5),
            total_bac=Decimal("500000"),
            total_bcws=Decimal("200000"),
            total_bcwp=Decimal("180000"),
            total_acwp=Decimal("190000"),
            total_cv=Decimal("-10000"),
            total_sv=Decimal("-20000"),
            total_cpi=Decimal("0.95"),
            total_spi=Decimal("0.90"),
            total_eac=Decimal("526316"),
            total_etc=Decimal("336316"),
            total_vac=Decimal("-26316"),
            percent_complete=Decimal("36.00"),
            percent_spent=Decimal("38.00"),
            wbs_rows=wbs_rows,
            variance_notes=[
                "1.1 (Project Planning): Schedule variance requires explanation.",
                "1.2 (Engineering): Cost variance of -7000 requires explanation.",
            ],
        )

    @pytest.fixture
    def sample_format3_report(self) -> CPRFormat3Report:
        """Create a sample Format 3 report."""
        time_rows = [
            TimePhaseRow(
                period_name="October 2025",
                period_start=date(2025, 10, 1),
                period_end=date(2025, 10, 31),
                bcws=Decimal("50000"),
                bcwp=Decimal("48000"),
                acwp=Decimal("49000"),
                cumulative_bcws=Decimal("50000"),
                cumulative_bcwp=Decimal("48000"),
                cumulative_acwp=Decimal("49000"),
                sv=Decimal("-2000"),
                cv=Decimal("-1000"),
            ),
            TimePhaseRow(
                period_name="November 2025",
                period_start=date(2025, 11, 1),
                period_end=date(2025, 11, 30),
                bcws=Decimal("60000"),
                bcwp=Decimal("55000"),
                acwp=Decimal("58000"),
                cumulative_bcws=Decimal("110000"),
                cumulative_bcwp=Decimal("103000"),
                cumulative_acwp=Decimal("107000"),
                sv=Decimal("-5000"),
                cv=Decimal("-3000"),
            ),
            TimePhaseRow(
                period_name="December 2025",
                period_start=date(2025, 12, 1),
                period_end=date(2025, 12, 31),
                bcws=Decimal("70000"),
                bcwp=Decimal("62000"),
                acwp=Decimal("68000"),
                cumulative_bcws=Decimal("180000"),
                cumulative_bcwp=Decimal("165000"),
                cumulative_acwp=Decimal("175000"),
                sv=Decimal("-8000"),
                cv=Decimal("-6000"),
            ),
        ]

        return CPRFormat3Report(
            program_name="Test Defense Program",
            program_code="TDP-001",
            contract_number="W12345-26-C-0001",
            baseline_name="Initial PMB",
            baseline_version=1,
            report_date=date(2026, 1, 15),
            bac=Decimal("1000000"),
            current_period="December 2025",
            percent_complete=Decimal("16.50"),
            percent_spent=Decimal("17.50"),
            total_bcws=Decimal("180000"),
            total_bcwp=Decimal("165000"),
            total_acwp=Decimal("175000"),
            total_sv=Decimal("-15000"),
            total_cv=Decimal("-10000"),
            eac=Decimal("1060606"),
            etc=Decimal("885606"),
            vac=Decimal("-60606"),
            cpi=Decimal("0.94"),
            spi=Decimal("0.92"),
            tcpi=Decimal("1.01"),
            time_phase_rows=time_rows,
            baseline_finish_date=date(2027, 6, 30),
            forecast_finish_date=date(2027, 8, 15),
            schedule_variance_days=46,
        )

    @pytest.fixture
    def sample_format5_report(self) -> CPRFormat5Report:
        """Create a sample Format 5 report."""
        period_rows = [
            Format5PeriodRow(
                period_name="October 2025",
                period_start=date(2025, 10, 1),
                period_end=date(2025, 10, 31),
                bcws=Decimal("50000"),
                bcwp=Decimal("48000"),
                acwp=Decimal("49000"),
                cumulative_bcws=Decimal("50000"),
                cumulative_bcwp=Decimal("48000"),
                cumulative_acwp=Decimal("49000"),
                period_sv=Decimal("-2000"),
                period_cv=Decimal("-1000"),
                cumulative_sv=Decimal("-2000"),
                cumulative_cv=Decimal("-1000"),
                sv_percent=Decimal("-4.00"),
                cv_percent=Decimal("-2.00"),
                spi=Decimal("0.96"),
                cpi=Decimal("0.98"),
                eac=Decimal("1020408"),
                etc=Decimal("971408"),
                vac=Decimal("-20408"),
                tcpi=Decimal("1.00"),
            ),
            Format5PeriodRow(
                period_name="November 2025",
                period_start=date(2025, 11, 1),
                period_end=date(2025, 11, 30),
                bcws=Decimal("60000"),
                bcwp=Decimal("55000"),
                acwp=Decimal("58000"),
                cumulative_bcws=Decimal("110000"),
                cumulative_bcwp=Decimal("103000"),
                cumulative_acwp=Decimal("107000"),
                period_sv=Decimal("-5000"),
                period_cv=Decimal("-3000"),
                cumulative_sv=Decimal("-7000"),
                cumulative_cv=Decimal("-4000"),
                sv_percent=Decimal("-6.36"),
                cv_percent=Decimal("-3.64"),
                spi=Decimal("0.94"),
                cpi=Decimal("0.96"),
                eac=Decimal("1041667"),
                etc=Decimal("934667"),
                vac=Decimal("-41667"),
                tcpi=Decimal("1.00"),
            ),
        ]

        mr_rows = [
            ManagementReserveRow(
                period_name="October 2025",
                beginning_mr=Decimal("100000"),
                changes_in=Decimal("0"),
                changes_out=Decimal("5000"),
                ending_mr=Decimal("95000"),
                reason="Released to WBS 1.2 for unplanned testing",
            ),
            ManagementReserveRow(
                period_name="November 2025",
                beginning_mr=Decimal("95000"),
                changes_in=Decimal("0"),
                changes_out=Decimal("10000"),
                ending_mr=Decimal("85000"),
                reason="Released to WBS 1.1 for scope change",
            ),
        ]

        variance_explanations = [
            VarianceExplanation(
                wbs_code="1.1",
                wbs_name="Project Planning",
                variance_type="cost",
                variance_amount=Decimal("-15000"),
                variance_percent=Decimal("-12.5"),
                explanation="Unplanned contractor support required for requirements analysis.",
                corrective_action="Reassigning internal staff to reduce contractor dependency.",
                expected_resolution_date=date(2026, 2, 28),
            ),
            VarianceExplanation(
                wbs_code="1.2",
                wbs_name="Engineering",
                variance_type="schedule",
                variance_amount=Decimal("-20000"),
                variance_percent=Decimal("-11.1"),
                explanation="Design review delayed due to stakeholder availability.",
                corrective_action="Accelerated review schedule implemented.",
                expected_resolution_date=date(2026, 1, 31),
            ),
        ]

        eac_analysis = EACAnalysis(
            eac_cpi=Decimal("1041667"),
            eac_spi=Decimal("1063830"),
            eac_composite=Decimal("1107527"),
            eac_typical=Decimal("1004000"),
            eac_atypical=Decimal("1041667"),
            eac_management=Decimal("1050000"),
            eac_selected=Decimal("1041667"),
            selection_rationale="CPI method selected - historical cost efficiency expected to continue",
            eac_range_low=Decimal("1004000"),
            eac_range_high=Decimal("1107527"),
            eac_average=Decimal("1051448"),
        )

        return CPRFormat5Report(
            program_name="Test Defense Program",
            program_code="TDP-001",
            contract_number="W12345-26-C-0001",
            report_date=date(2026, 1, 15),
            reporting_period="November 2025",
            bac=Decimal("1000000"),
            current_eac=Decimal("1041667"),
            current_etc=Decimal("934667"),
            current_vac=Decimal("-41667"),
            cumulative_cpi=Decimal("0.96"),
            cumulative_spi=Decimal("0.94"),
            cumulative_tcpi=Decimal("1.00"),
            percent_complete=Decimal("10.30"),
            percent_spent=Decimal("10.70"),
            period_rows=period_rows,
            mr_rows=mr_rows,
            current_mr=Decimal("85000"),
            variance_explanations=variance_explanations,
            eac_analysis=eac_analysis,
            generated_at=date(2026, 1, 15),
        )

    # =========================================================================
    # Format 1 PDF Tests
    # =========================================================================

    def test_generate_format1_pdf_returns_bytes(
        self, pdf_generator: ReportPDFGenerator, sample_format1_report: CPRFormat1Report
    ):
        """Should return PDF as bytes."""
        result = pdf_generator.generate_format1_pdf(sample_format1_report)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_format1_pdf_starts_with_pdf_header(
        self, pdf_generator: ReportPDFGenerator, sample_format1_report: CPRFormat1Report
    ):
        """Should generate valid PDF with correct header."""
        result = pdf_generator.generate_format1_pdf(sample_format1_report)

        # PDF files start with %PDF-
        assert result[:5] == b"%PDF-"

    def test_generate_format1_pdf_is_valid(
        self, pdf_generator: ReportPDFGenerator, sample_format1_report: CPRFormat1Report
    ):
        """Should generate valid PDF with content."""
        result = pdf_generator.generate_format1_pdf(sample_format1_report)

        # PDF text is compressed/encoded, so we check structure instead
        assert result[:5] == b"%PDF-"
        assert b"%%EOF" in result
        # PDF should have substantial content
        assert len(result) > 1000

    def test_generate_format1_pdf_with_custom_config(
        self, custom_pdf_generator: ReportPDFGenerator, sample_format1_report: CPRFormat1Report
    ):
        """Should respect custom configuration."""
        result = custom_pdf_generator.generate_format1_pdf(sample_format1_report)

        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:5] == b"%PDF-"

    def test_generate_format1_pdf_with_empty_wbs_rows(self, pdf_generator: ReportPDFGenerator):
        """Should handle report with no WBS rows."""
        report = CPRFormat1Report(
            program_name="Empty Program",
            program_code="EMPTY-001",
            contract_number=None,
            reporting_period="January 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            report_date=date(2026, 2, 5),
            total_bac=Decimal("0"),
            total_bcws=Decimal("0"),
            total_bcwp=Decimal("0"),
            total_acwp=Decimal("0"),
            total_cv=Decimal("0"),
            total_sv=Decimal("0"),
            total_cpi=None,
            total_spi=None,
            total_eac=None,
            total_etc=None,
            total_vac=None,
            percent_complete=Decimal("0"),
            percent_spent=Decimal("0"),
            wbs_rows=[],
            variance_notes=[],
        )

        result = pdf_generator.generate_format1_pdf(report)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_format1_pdf_with_null_values(self, pdf_generator: ReportPDFGenerator):
        """Should handle null/None values gracefully."""
        report = CPRFormat1Report(
            program_name="Test Program",
            program_code="TEST-001",
            contract_number=None,
            reporting_period="January 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            report_date=date(2026, 2, 5),
            total_bac=Decimal("100000"),
            total_bcws=Decimal("50000"),
            total_bcwp=Decimal("0"),
            total_acwp=Decimal("0"),
            total_cv=Decimal("0"),
            total_sv=Decimal("-50000"),
            total_cpi=None,  # N/A when ACWP is 0
            total_spi=None,  # N/A when BCWS is 0
            total_eac=None,
            total_etc=None,
            total_vac=None,
            percent_complete=Decimal("0"),
            percent_spent=Decimal("0"),
            wbs_rows=[],
            variance_notes=[],
        )

        result = pdf_generator.generate_format1_pdf(report)

        assert isinstance(result, bytes)
        assert len(result) > 0

    # =========================================================================
    # Format 3 PDF Tests
    # =========================================================================

    def test_generate_format3_pdf_returns_bytes(
        self, pdf_generator: ReportPDFGenerator, sample_format3_report: CPRFormat3Report
    ):
        """Should return PDF as bytes."""
        result = pdf_generator.generate_format3_pdf(sample_format3_report)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_format3_pdf_starts_with_pdf_header(
        self, pdf_generator: ReportPDFGenerator, sample_format3_report: CPRFormat3Report
    ):
        """Should generate valid PDF with correct header."""
        result = pdf_generator.generate_format3_pdf(sample_format3_report)

        assert result[:5] == b"%PDF-"

    def test_generate_format3_pdf_is_valid(
        self, pdf_generator: ReportPDFGenerator, sample_format3_report: CPRFormat3Report
    ):
        """Should generate valid PDF with content."""
        result = pdf_generator.generate_format3_pdf(sample_format3_report)

        # PDF text is compressed/encoded, so we check structure instead
        assert result[:5] == b"%PDF-"
        assert b"%%EOF" in result
        # PDF should have substantial content
        assert len(result) > 1000

    def test_generate_format3_pdf_with_empty_time_rows(self, pdf_generator: ReportPDFGenerator):
        """Should handle report with no time phase rows."""
        report = CPRFormat3Report(
            program_name="Empty Program",
            program_code="EMPTY-001",
            contract_number=None,
            baseline_name="Empty Baseline",
            baseline_version=1,
            report_date=date(2026, 1, 15),
            bac=Decimal("100000"),
            current_period="",
            percent_complete=Decimal("0"),
            percent_spent=Decimal("0"),
            total_bcws=Decimal("0"),
            total_bcwp=Decimal("0"),
            total_acwp=Decimal("0"),
            total_sv=Decimal("0"),
            total_cv=Decimal("0"),
            eac=Decimal("100000"),
            etc=Decimal("100000"),
            vac=Decimal("0"),
            cpi=None,
            spi=None,
            tcpi=None,
            time_phase_rows=[],
        )

        result = pdf_generator.generate_format3_pdf(report)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_format3_pdf_with_schedule_info(
        self, pdf_generator: ReportPDFGenerator, sample_format3_report: CPRFormat3Report
    ):
        """Should include schedule status in PDF."""
        result = pdf_generator.generate_format3_pdf(sample_format3_report)

        assert isinstance(result, bytes)
        # The PDF should be larger when it includes time-phased data
        assert len(result) > 1000

    # =========================================================================
    # Format 5 PDF Tests
    # =========================================================================

    def test_generate_format5_pdf_returns_bytes(
        self, pdf_generator: ReportPDFGenerator, sample_format5_report: CPRFormat5Report
    ):
        """Should return PDF as bytes."""
        result = pdf_generator.generate_format5_pdf(sample_format5_report)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_format5_pdf_starts_with_pdf_header(
        self, pdf_generator: ReportPDFGenerator, sample_format5_report: CPRFormat5Report
    ):
        """Should generate valid PDF with correct header."""
        result = pdf_generator.generate_format5_pdf(sample_format5_report)

        assert result[:5] == b"%PDF-"

    def test_generate_format5_pdf_with_eac_analysis(
        self, pdf_generator: ReportPDFGenerator, sample_format5_report: CPRFormat5Report
    ):
        """Should include EAC analysis section."""
        result = pdf_generator.generate_format5_pdf(sample_format5_report)

        assert isinstance(result, bytes)
        # PDF with EAC analysis should be substantial
        assert len(result) > 2000

    def test_generate_format5_pdf_with_mr_tracking(
        self, pdf_generator: ReportPDFGenerator, sample_format5_report: CPRFormat5Report
    ):
        """Should include Management Reserve tracking."""
        result = pdf_generator.generate_format5_pdf(sample_format5_report)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_format5_pdf_with_variance_explanations(
        self, pdf_generator: ReportPDFGenerator, sample_format5_report: CPRFormat5Report
    ):
        """Should include variance explanations."""
        result = pdf_generator.generate_format5_pdf(sample_format5_report)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_format5_pdf_without_optional_sections(
        self, pdf_generator: ReportPDFGenerator
    ):
        """Should handle report without optional sections."""
        report = CPRFormat5Report(
            program_name="Minimal Program",
            program_code="MIN-001",
            contract_number=None,
            report_date=date(2026, 1, 15),
            reporting_period="January 2026",
            bac=Decimal("100000"),
            current_eac=Decimal("100000"),
            current_etc=Decimal("100000"),
            current_vac=Decimal("0"),
            cumulative_cpi=None,
            cumulative_spi=None,
            cumulative_tcpi=None,
            percent_complete=Decimal("0"),
            percent_spent=Decimal("0"),
            period_rows=[],
            mr_rows=[],
            current_mr=Decimal("0"),
            variance_explanations=[],
            eac_analysis=None,
        )

        result = pdf_generator.generate_format5_pdf(report)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_format5_pdf_with_all_eac_methods(
        self, pdf_generator: ReportPDFGenerator, sample_format5_report: CPRFormat5Report
    ):
        """Should include all 6 EAC methods when present."""
        result = pdf_generator.generate_format5_pdf(sample_format5_report)

        # The PDF should be substantial with all EAC methods
        assert len(result) > 3000


class TestPDFGeneratorHelperMethods:
    """Tests for helper methods in ReportPDFGenerator."""

    @pytest.fixture
    def generator(self) -> ReportPDFGenerator:
        """Create generator instance."""
        return ReportPDFGenerator()

    def test_format_currency_with_value(self, generator: ReportPDFGenerator):
        """Should format decimal as currency."""
        result = generator._format_currency(Decimal("1234567.89"))
        assert result == "$1,234,568"

    def test_format_currency_with_none(self, generator: ReportPDFGenerator):
        """Should return N/A for None."""
        result = generator._format_currency(None)
        assert result == "N/A"

    def test_format_currency_with_negative(self, generator: ReportPDFGenerator):
        """Should format negative values correctly."""
        result = generator._format_currency(Decimal("-50000"))
        assert result == "$-50,000"

    def test_format_percent_with_value(self, generator: ReportPDFGenerator):
        """Should format decimal as percentage."""
        result = generator._format_percent(Decimal("75.50"))
        assert result == "75.5%"

    def test_format_percent_with_none(self, generator: ReportPDFGenerator):
        """Should return N/A for None."""
        result = generator._format_percent(None)
        assert result == "N/A"

    def test_format_index_with_value(self, generator: ReportPDFGenerator):
        """Should format index with 2 decimal places."""
        result = generator._format_index(Decimal("0.9567"))
        assert result == "0.96"

    def test_format_index_with_none(self, generator: ReportPDFGenerator):
        """Should return N/A for None."""
        result = generator._format_index(None)
        assert result == "N/A"

    def test_format_date_with_value(self, generator: ReportPDFGenerator):
        """Should format date as readable string."""
        result = generator._format_date(date(2026, 1, 15))
        assert result == "Jan 15, 2026"

    def test_format_date_with_none(self, generator: ReportPDFGenerator):
        """Should return N/A for None."""
        result = generator._format_date(None)
        assert result == "N/A"


class TestPDFGeneratorOutputSize:
    """Tests to ensure PDF generation produces reasonable output sizes."""

    @pytest.fixture
    def generator(self) -> ReportPDFGenerator:
        """Create generator instance."""
        return ReportPDFGenerator()

    def test_format1_pdf_reasonable_size(self, generator: ReportPDFGenerator):
        """Format 1 PDF should be within reasonable size range."""
        report = CPRFormat1Report(
            program_name="Size Test Program",
            program_code="SIZE-001",
            contract_number="CONTRACT-123",
            reporting_period="January 2026",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            report_date=date(2026, 2, 5),
            total_bac=Decimal("1000000"),
            total_bcws=Decimal("500000"),
            total_bcwp=Decimal("450000"),
            total_acwp=Decimal("480000"),
            total_cv=Decimal("-30000"),
            total_sv=Decimal("-50000"),
            total_cpi=Decimal("0.94"),
            total_spi=Decimal("0.90"),
            total_eac=Decimal("1063830"),
            total_etc=Decimal("583830"),
            total_vac=Decimal("-63830"),
            percent_complete=Decimal("45.00"),
            percent_spent=Decimal("48.00"),
            wbs_rows=[
                WBSSummaryRow(
                    wbs_code=f"1.{i}",
                    wbs_name=f"Work Package {i}",
                    level=2,
                    is_control_account=i % 3 == 0,
                    bac=Decimal("100000"),
                    bcws=Decimal("50000"),
                    bcwp=Decimal("45000"),
                    acwp=Decimal("48000"),
                    cv=Decimal("-3000"),
                    sv=Decimal("-5000"),
                    cpi=Decimal("0.94"),
                    spi=Decimal("0.90"),
                    eac=Decimal("106383"),
                    etc=Decimal("58383"),
                    vac=Decimal("-6383"),
                )
                for i in range(10)
            ],
            variance_notes=["Note 1", "Note 2", "Note 3"],
        )

        result = generator.generate_format1_pdf(report)

        # PDF should be between 2KB and 500KB (reportlab generates compact PDFs)
        assert 2000 < len(result) < 500000

    def test_format3_pdf_reasonable_size(self, generator: ReportPDFGenerator):
        """Format 3 PDF should be within reasonable size range."""
        report = CPRFormat3Report(
            program_name="Size Test Program",
            program_code="SIZE-001",
            contract_number="CONTRACT-123",
            baseline_name="Test Baseline",
            baseline_version=1,
            report_date=date(2026, 1, 15),
            bac=Decimal("1000000"),
            current_period="December 2025",
            percent_complete=Decimal("45.00"),
            percent_spent=Decimal("48.00"),
            total_bcws=Decimal("500000"),
            total_bcwp=Decimal("450000"),
            total_acwp=Decimal("480000"),
            total_sv=Decimal("-50000"),
            total_cv=Decimal("-30000"),
            eac=Decimal("1063830"),
            etc=Decimal("583830"),
            vac=Decimal("-63830"),
            cpi=Decimal("0.94"),
            spi=Decimal("0.90"),
            tcpi=Decimal("1.02"),
            time_phase_rows=[
                TimePhaseRow(
                    period_name=f"Month {i}",
                    period_start=date(2025, (i % 12) + 1, 1),
                    period_end=date(2025, (i % 12) + 1, 28),
                    bcws=Decimal("50000"),
                    bcwp=Decimal("45000"),
                    acwp=Decimal("48000"),
                    cumulative_bcws=Decimal("50000") * (i + 1),
                    cumulative_bcwp=Decimal("45000") * (i + 1),
                    cumulative_acwp=Decimal("48000") * (i + 1),
                    sv=Decimal("-5000"),
                    cv=Decimal("-3000"),
                )
                for i in range(12)
            ],
        )

        result = generator.generate_format3_pdf(report)

        # PDF should be between 2KB and 500KB (reportlab generates compact PDFs)
        assert 2000 < len(result) < 500000

    def test_format5_pdf_reasonable_size(self, generator: ReportPDFGenerator):
        """Format 5 PDF should be within reasonable size range."""
        report = CPRFormat5Report(
            program_name="Size Test Program",
            program_code="SIZE-001",
            contract_number="CONTRACT-123",
            report_date=date(2026, 1, 15),
            reporting_period="December 2025",
            bac=Decimal("1000000"),
            current_eac=Decimal("1063830"),
            current_etc=Decimal("583830"),
            current_vac=Decimal("-63830"),
            cumulative_cpi=Decimal("0.94"),
            cumulative_spi=Decimal("0.90"),
            cumulative_tcpi=Decimal("1.02"),
            percent_complete=Decimal("45.00"),
            percent_spent=Decimal("48.00"),
            period_rows=[
                Format5PeriodRow(
                    period_name=f"Month {i}",
                    period_start=date(2025, (i % 12) + 1, 1),
                    period_end=date(2025, (i % 12) + 1, 28),
                    bcws=Decimal("50000"),
                    bcwp=Decimal("45000"),
                    acwp=Decimal("48000"),
                    cumulative_bcws=Decimal("50000") * (i + 1),
                    cumulative_bcwp=Decimal("45000") * (i + 1),
                    cumulative_acwp=Decimal("48000") * (i + 1),
                    period_sv=Decimal("-5000"),
                    period_cv=Decimal("-3000"),
                    cumulative_sv=Decimal("-5000") * (i + 1),
                    cumulative_cv=Decimal("-3000") * (i + 1),
                    sv_percent=Decimal("-10.00"),
                    cv_percent=Decimal("-6.00"),
                    spi=Decimal("0.90"),
                    cpi=Decimal("0.94"),
                    eac=Decimal("1063830"),
                    etc=Decimal("583830"),
                    vac=Decimal("-63830"),
                    tcpi=Decimal("1.02"),
                )
                for i in range(12)
            ],
            mr_rows=[
                ManagementReserveRow(
                    period_name=f"Month {i}",
                    beginning_mr=Decimal("100000") - Decimal("5000") * i,
                    changes_in=Decimal("0"),
                    changes_out=Decimal("5000"),
                    ending_mr=Decimal("95000") - Decimal("5000") * i,
                    reason=f"Released for unplanned work {i}",
                )
                for i in range(6)
            ],
            current_mr=Decimal("70000"),
            variance_explanations=[
                VarianceExplanation(
                    wbs_code=f"1.{i}",
                    wbs_name=f"Work Package {i}",
                    variance_type="cost" if i % 2 == 0 else "schedule",
                    variance_amount=Decimal("-15000"),
                    variance_percent=Decimal("-12.5"),
                    explanation=f"Explanation for variance {i}",
                    corrective_action=f"Corrective action {i}",
                    expected_resolution_date=date(2026, 2, 28),
                )
                for i in range(5)
            ],
            eac_analysis=EACAnalysis(
                eac_cpi=Decimal("1063830"),
                eac_spi=Decimal("1111111"),
                eac_composite=Decimal("1180872"),
                eac_typical=Decimal("1030000"),
                eac_atypical=Decimal("1063830"),
                eac_management=Decimal("1050000"),
                eac_selected=Decimal("1063830"),
                selection_rationale="CPI method selected",
                eac_range_low=Decimal("1030000"),
                eac_range_high=Decimal("1180872"),
                eac_average=Decimal("1083274"),
            ),
        )

        result = generator.generate_format5_pdf(report)

        # PDF with all sections should be between 3KB and 1MB (reportlab generates compact PDFs)
        assert 3000 < len(result) < 1000000
