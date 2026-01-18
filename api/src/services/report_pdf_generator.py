"""PDF export service for CPR reports.

Generates PDF versions of CPR Format 1, 3, and 5 reports using reportlab.
Designed for DoD compliance reporting with professional formatting.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from io import BytesIO
from typing import Any, cast

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.schemas.cpr_format3 import CPRFormat3Report
from src.schemas.cpr_format5 import CPRFormat5Report
from src.services.report_generator import CPRFormat1Report

# Default colors for PDF styling
_DEFAULT_PRIMARY_COLOR = "#1a365d"
_DEFAULT_ACCENT_COLOR = "#2b6cb0"
_DEFAULT_POSITIVE_COLOR = "#276749"
_DEFAULT_NEGATIVE_COLOR = "#c53030"


@dataclass
class PDFConfig:
    """Configuration for PDF generation."""

    # Page settings
    page_size: tuple[float, float] = LETTER
    landscape_mode: bool = True
    margin_top: float = 0.5 * inch
    margin_bottom: float = 0.5 * inch
    margin_left: float = 0.5 * inch
    margin_right: float = 0.5 * inch

    # Header/footer
    include_header: bool = True
    include_footer: bool = True
    include_page_numbers: bool = True

    # Branding
    company_name: str = "Defense Program Management"
    classification: str = "UNCLASSIFIED"

    # Style options (use hex strings, converted to colors at runtime)
    primary_color_hex: str = field(default=_DEFAULT_PRIMARY_COLOR)
    accent_color_hex: str = field(default=_DEFAULT_ACCENT_COLOR)
    positive_color_hex: str = field(default=_DEFAULT_POSITIVE_COLOR)
    negative_color_hex: str = field(default=_DEFAULT_NEGATIVE_COLOR)

    @property
    def primary_color(self) -> colors.Color:
        """Get primary color."""
        return colors.HexColor(self.primary_color_hex)

    @property
    def accent_color(self) -> colors.Color:
        """Get accent color."""
        return colors.HexColor(self.accent_color_hex)

    @property
    def positive_color(self) -> colors.Color:
        """Get positive color."""
        return colors.HexColor(self.positive_color_hex)

    @property
    def negative_color(self) -> colors.Color:
        """Get negative color."""
        return colors.HexColor(self.negative_color_hex)


class ReportPDFGenerator:
    """Generates PDF versions of CPR reports.

    Supports:
    - CPR Format 1 (WBS Summary)
    - CPR Format 3 (Baseline)
    - CPR Format 5 (EVMS)

    Example usage:
        pdf_gen = ReportPDFGenerator(config=PDFConfig())
        pdf_bytes = pdf_gen.generate_format1_pdf(report)
    """

    def __init__(self, config: PDFConfig | None = None) -> None:
        """Initialize PDF generator with configuration.

        Args:
            config: Optional PDF configuration. Uses defaults if not provided.
        """
        self.config = config or PDFConfig()
        self._init_styles()

    def _init_styles(self) -> None:
        """Initialize paragraph and table styles."""
        self.styles = getSampleStyleSheet()

        # Title style
        self.styles.add(
            ParagraphStyle(
                "ReportTitle",
                parent=self.styles["Heading1"],
                fontSize=16,
                textColor=self.config.primary_color,
                spaceAfter=6,
                alignment=TA_CENTER,
            )
        )

        # Subtitle style
        self.styles.add(
            ParagraphStyle(
                "ReportSubtitle",
                parent=self.styles["Heading2"],
                fontSize=12,
                textColor=self.config.accent_color,
                spaceAfter=12,
                alignment=TA_CENTER,
            )
        )

        # Section header style
        self.styles.add(
            ParagraphStyle(
                "SectionHeader",
                parent=self.styles["Heading3"],
                fontSize=11,
                textColor=self.config.primary_color,
                spaceBefore=12,
                spaceAfter=6,
            )
        )

        # Normal text style
        self.styles.add(
            ParagraphStyle(
                "ReportBody",
                parent=self.styles["Normal"],
                fontSize=9,
                spaceAfter=6,
            )
        )

        # Right-aligned number style
        self.styles.add(
            ParagraphStyle(
                "RightAlign",
                parent=self.styles["Normal"],
                fontSize=9,
                alignment=TA_RIGHT,
            )
        )

        # Classification banner
        self.styles.add(
            ParagraphStyle(
                "Classification",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.green,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

    def _get_page_size(self) -> tuple[float, float]:
        """Get page size based on configuration."""
        if self.config.landscape_mode:
            return cast("tuple[float, float]", landscape(self.config.page_size))
        return self.config.page_size

    def _format_currency(self, value: Decimal | None) -> str:
        """Format a decimal value as currency."""
        if value is None:
            return "N/A"
        return f"${value:,.0f}"

    def _format_percent(self, value: Decimal | None) -> str:
        """Format a decimal value as percentage."""
        if value is None:
            return "N/A"
        return f"{value:.1f}%"

    def _format_index(self, value: Decimal | None) -> str:
        """Format a performance index value."""
        if value is None:
            return "N/A"
        return f"{value:.2f}"

    def _format_date(self, value: date | None) -> str:
        """Format a date value."""
        if value is None:
            return "N/A"
        return value.strftime("%b %d, %Y")

    def _create_header_footer(self, canvas: Any, doc: Any) -> None:
        """Add header and footer to pages."""
        canvas.saveState()
        page_width, page_height = self._get_page_size()

        # Classification banner at top
        if self.config.include_header:
            canvas.setFont("Helvetica-Bold", 10)
            canvas.setFillColor(colors.green)
            canvas.drawCentredString(
                page_width / 2, page_height - 0.3 * inch, self.config.classification
            )

        # Footer with page number
        if self.config.include_footer:
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.gray)

            # Left side: company name
            canvas.drawString(self.config.margin_left, 0.35 * inch, self.config.company_name)

            # Right side: page number
            if self.config.include_page_numbers:
                canvas.drawRightString(
                    page_width - self.config.margin_right,
                    0.35 * inch,
                    f"Page {doc.page}",
                )

            # Center: classification again
            canvas.setFillColor(colors.green)
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawCentredString(page_width / 2, 0.35 * inch, self.config.classification)

        canvas.restoreState()

    def _create_summary_table(self, data: list[tuple[str, str]], title: str) -> list[Any]:
        """Create a summary metrics table.

        Args:
            data: List of (label, value) tuples
            title: Section title

        Returns:
            List of flowables for the summary section
        """
        elements = []
        elements.append(Paragraph(title, self.styles["SectionHeader"]))

        # Create table data
        table_data = [[label, value] for label, value in data]

        table = Table(
            table_data,
            colWidths=[2 * inch, 1.5 * inch],
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 12))

        return elements

    def generate_format1_pdf(self, report: CPRFormat1Report) -> bytes:
        """Generate PDF for CPR Format 1 (WBS Summary) report.

        Args:
            report: CPRFormat1Report dataclass

        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        page_size = self._get_page_size()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            topMargin=self.config.margin_top + 0.3 * inch,  # Extra for classification
            bottomMargin=self.config.margin_bottom + 0.3 * inch,
            leftMargin=self.config.margin_left,
            rightMargin=self.config.margin_right,
        )

        elements = []

        # Title
        elements.append(
            Paragraph("Contract Performance Report - Format 1", self.styles["ReportTitle"])
        )
        elements.append(
            Paragraph(
                f"{report.program_name} ({report.program_code})", self.styles["ReportSubtitle"]
            )
        )
        elements.append(Spacer(1, 6))

        # Header info
        header_data = [
            ("Contract Number:", report.contract_number or "N/A"),
            ("Reporting Period:", report.reporting_period),
            (
                "Period:",
                f"{self._format_date(report.period_start)} - {self._format_date(report.period_end)}",
            ),
            ("Report Date:", self._format_date(report.report_date)),
        ]
        elements.extend(self._create_summary_table(header_data, "Report Information"))

        # Summary metrics
        summary_data = [
            ("Budget at Completion (BAC):", self._format_currency(report.total_bac)),
            ("BCWS (Planned Value):", self._format_currency(report.total_bcws)),
            ("BCWP (Earned Value):", self._format_currency(report.total_bcwp)),
            ("ACWP (Actual Cost):", self._format_currency(report.total_acwp)),
            ("Cost Variance (CV):", self._format_currency(report.total_cv)),
            ("Schedule Variance (SV):", self._format_currency(report.total_sv)),
            ("CPI:", self._format_index(report.total_cpi)),
            ("SPI:", self._format_index(report.total_spi)),
            ("EAC:", self._format_currency(report.total_eac)),
            ("VAC:", self._format_currency(report.total_vac)),
            ("% Complete:", self._format_percent(report.percent_complete)),
            ("% Spent:", self._format_percent(report.percent_spent)),
        ]
        elements.extend(self._create_summary_table(summary_data, "Performance Summary"))

        # WBS table
        elements.append(Paragraph("WBS Summary", self.styles["SectionHeader"]))

        # Table headers
        wbs_headers = [
            "WBS Code",
            "Description",
            "BAC",
            "BCWS",
            "BCWP",
            "ACWP",
            "CV",
            "SV",
            "CPI",
            "SPI",
            "EAC",
            "VAC",
        ]

        # Build table data
        wbs_data = [wbs_headers]
        for row in report.wbs_rows:
            indent = "  " * (row.level - 1)
            ca_marker = " *" if row.is_control_account else ""
            wbs_data.append(
                [
                    row.wbs_code,
                    f"{indent}{row.wbs_name}{ca_marker}",
                    self._format_currency(row.bac),
                    self._format_currency(row.bcws),
                    self._format_currency(row.bcwp),
                    self._format_currency(row.acwp),
                    self._format_currency(row.cv),
                    self._format_currency(row.sv),
                    self._format_index(row.cpi),
                    self._format_index(row.spi),
                    self._format_currency(row.eac),
                    self._format_currency(row.vac),
                ]
            )

        # Add totals row
        wbs_data.append(
            [
                "TOTAL",
                "",
                self._format_currency(report.total_bac),
                self._format_currency(report.total_bcws),
                self._format_currency(report.total_bcwp),
                self._format_currency(report.total_acwp),
                self._format_currency(report.total_cv),
                self._format_currency(report.total_sv),
                self._format_index(report.total_cpi),
                self._format_index(report.total_spi),
                self._format_currency(report.total_eac),
                self._format_currency(report.total_vac),
            ]
        )

        # Calculate column widths based on page size
        available_width = page_size[0] - self.config.margin_left - self.config.margin_right
        col_widths = [
            0.08 * available_width,  # WBS Code
            0.18 * available_width,  # Description
            0.08 * available_width,  # BAC
            0.08 * available_width,  # BCWS
            0.08 * available_width,  # BCWP
            0.08 * available_width,  # ACWP
            0.08 * available_width,  # CV
            0.08 * available_width,  # SV
            0.05 * available_width,  # CPI
            0.05 * available_width,  # SPI
            0.08 * available_width,  # EAC
            0.08 * available_width,  # VAC
        ]

        wbs_table = Table(wbs_data, colWidths=col_widths)

        # Style table
        table_style = [
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), self.config.primary_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            # Body
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),  # Numbers right-aligned
            ("ALIGN", (0, 1), (1, -1), "LEFT"),  # Text left-aligned
            # Borders
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            # Padding
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            # Totals row
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f4ff")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            # Alternating row colors
        ]

        # Add alternating row colors
        for i in range(1, len(wbs_data) - 1):
            if i % 2 == 0:
                table_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f9f9f9")))

        # Highlight control accounts
        for i, row in enumerate(report.wbs_rows, start=1):
            if row.is_control_account:
                table_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fff3e0")))

        wbs_table.setStyle(TableStyle(table_style))
        elements.append(wbs_table)

        elements.append(Spacer(1, 6))
        elements.append(Paragraph("* Indicates Control Account", self.styles["ReportBody"]))

        # Variance notes if any
        if report.variance_notes:
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("Variance Analysis Required", self.styles["SectionHeader"]))
            for note in report.variance_notes:
                elements.append(Paragraph(f"• {note}", self.styles["ReportBody"]))

        # Build document
        doc.build(
            elements,
            onFirstPage=self._create_header_footer,
            onLaterPages=self._create_header_footer,
        )

        return buffer.getvalue()

    def generate_format3_pdf(self, report: CPRFormat3Report) -> bytes:
        """Generate PDF for CPR Format 3 (Baseline) report.

        Args:
            report: CPRFormat3Report dataclass

        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        page_size = self._get_page_size()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            topMargin=self.config.margin_top + 0.3 * inch,
            bottomMargin=self.config.margin_bottom + 0.3 * inch,
            leftMargin=self.config.margin_left,
            rightMargin=self.config.margin_right,
        )

        elements = []

        # Title
        elements.append(
            Paragraph("Contract Performance Report - Format 3", self.styles["ReportTitle"])
        )
        elements.append(
            Paragraph(
                f"{report.program_name} ({report.program_code})", self.styles["ReportSubtitle"]
            )
        )
        elements.append(Spacer(1, 6))

        # Header info
        header_data = [
            ("Contract Number:", report.contract_number or "N/A"),
            ("Baseline:", f"{report.baseline_name} (v{report.baseline_version})"),
            ("Report Date:", self._format_date(report.report_date)),
            ("Current Period:", report.current_period),
        ]
        elements.extend(self._create_summary_table(header_data, "Report Information"))

        # Summary metrics
        summary_data = [
            ("Budget at Completion (BAC):", self._format_currency(report.bac)),
            ("Cumulative BCWS:", self._format_currency(report.total_bcws)),
            ("Cumulative BCWP:", self._format_currency(report.total_bcwp)),
            ("Cumulative ACWP:", self._format_currency(report.total_acwp)),
            ("Schedule Variance:", self._format_currency(report.total_sv)),
            ("Cost Variance:", self._format_currency(report.total_cv)),
            ("SPI:", self._format_index(report.spi)),
            ("CPI:", self._format_index(report.cpi)),
            ("EAC:", self._format_currency(report.eac)),
            ("ETC:", self._format_currency(report.etc)),
            ("VAC:", self._format_currency(report.vac)),
            ("TCPI:", self._format_index(report.tcpi)),
            ("% Complete:", self._format_percent(report.percent_complete)),
            ("% Spent:", self._format_percent(report.percent_spent)),
        ]
        elements.extend(self._create_summary_table(summary_data, "Performance Summary"))

        # Schedule status
        schedule_data = [
            ("Baseline Finish:", self._format_date(report.baseline_finish_date)),
            ("Forecast Finish:", self._format_date(report.forecast_finish_date)),
            ("Schedule Variance:", f"{report.schedule_variance_days} days"),
            ("Status:", "Behind Schedule" if report.is_behind_schedule else "On Schedule"),
        ]
        elements.extend(self._create_summary_table(schedule_data, "Schedule Status"))

        # Time-phased data table
        if report.time_phase_rows:
            elements.append(Paragraph("Time-Phased Performance", self.styles["SectionHeader"]))

            time_headers = [
                "Period",
                "BCWS",
                "BCWP",
                "ACWP",
                "SV",
                "CV",
                "Cum BCWS",
                "Cum BCWP",
                "Cum ACWP",
                "SPI",
                "CPI",
            ]

            time_data = [time_headers]
            for row in report.time_phase_rows:
                time_data.append(
                    [
                        row.period_name,
                        self._format_currency(row.bcws),
                        self._format_currency(row.bcwp),
                        self._format_currency(row.acwp),
                        self._format_currency(row.sv),
                        self._format_currency(row.cv),
                        self._format_currency(row.cumulative_bcws),
                        self._format_currency(row.cumulative_bcwp),
                        self._format_currency(row.cumulative_acwp),
                        self._format_index(row.cumulative_spi),
                        self._format_index(row.cumulative_cpi),
                    ]
                )

            available_width = page_size[0] - self.config.margin_left - self.config.margin_right
            col_widths = [available_width / len(time_headers)] * len(time_headers)

            time_table = Table(time_data, colWidths=col_widths)

            table_style = [
                ("BACKGROUND", (0, 0), (-1, 0), self.config.primary_color),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 1), (0, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]

            # Add alternating row colors
            for i in range(1, len(time_data)):
                if i % 2 == 0:
                    table_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f9f9f9")))

            time_table.setStyle(TableStyle(table_style))
            elements.append(time_table)

        # Build document
        doc.build(
            elements,
            onFirstPage=self._create_header_footer,
            onLaterPages=self._create_header_footer,
        )

        return buffer.getvalue()

    def _build_format5_eac_section(self, report: CPRFormat5Report, elements: list[Any]) -> None:
        """Build EAC analysis section for Format 5 PDF."""
        if not report.eac_analysis:
            return

        eac = report.eac_analysis
        elements.append(Paragraph("EAC Analysis (Per GL 27)", self.styles["SectionHeader"]))

        eac_data = [
            ["Method", "EAC Value", "Description"],
            ["CPI Method", self._format_currency(eac.eac_cpi), "BAC / CPI"],
            [
                "SPI Method",
                self._format_currency(eac.eac_spi) if eac.eac_spi else "N/A",
                "BAC / SPI",
            ],
            [
                "Composite",
                self._format_currency(eac.eac_composite),
                "ACWP + (BAC - BCWP) / (CPI x SPI)",
            ],
            ["Typical", self._format_currency(eac.eac_typical), "ACWP + (BAC - BCWP)"],
            ["Atypical", self._format_currency(eac.eac_atypical), "ACWP + (BAC - BCWP) / CPI"],
            [
                "Management",
                self._format_currency(eac.eac_management) if eac.eac_management else "N/A",
                "Bottom-up estimate",
            ],
        ]

        eac_table = Table(eac_data, colWidths=[1.5 * inch, 1.5 * inch, 4 * inch])
        eac_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), self.config.primary_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        elements.append(eac_table)

        elements.append(Spacer(1, 6))
        elements.append(
            Paragraph(
                f"<b>Selected EAC:</b> {self._format_currency(eac.eac_selected)}",
                self.styles["ReportBody"],
            )
        )
        if eac.selection_rationale:
            elements.append(
                Paragraph(f"<b>Rationale:</b> {eac.selection_rationale}", self.styles["ReportBody"])
            )
        if eac.eac_range_low and eac.eac_range_high:
            elements.append(
                Paragraph(
                    f"<b>EAC Range:</b> {self._format_currency(eac.eac_range_low)} - {self._format_currency(eac.eac_range_high)}",
                    self.styles["ReportBody"],
                )
            )
        elements.append(Spacer(1, 12))

    def _build_format5_period_table(
        self, report: CPRFormat5Report, elements: list[Any], page_size: tuple[float, float]
    ) -> None:
        """Build period data table for Format 5 PDF."""
        if not report.period_rows:
            return

        elements.append(Paragraph("Period Performance Data", self.styles["SectionHeader"]))

        period_headers = [
            "Period",
            "BCWS",
            "BCWP",
            "ACWP",
            "SV",
            "CV",
            "SV%",
            "CV%",
            "SPI",
            "CPI",
            "EAC",
        ]
        period_data = [period_headers]

        for row in report.period_rows:
            period_data.append(
                [
                    row.period_name,
                    self._format_currency(row.bcws),
                    self._format_currency(row.bcwp),
                    self._format_currency(row.acwp),
                    self._format_currency(row.period_sv),
                    self._format_currency(row.period_cv),
                    self._format_percent(row.sv_percent),
                    self._format_percent(row.cv_percent),
                    self._format_index(row.spi),
                    self._format_index(row.cpi),
                    self._format_currency(row.eac),
                ]
            )

        available_width = page_size[0] - self.config.margin_left - self.config.margin_right
        col_widths = [available_width / len(period_headers)] * len(period_headers)

        period_table = Table(period_data, colWidths=col_widths)
        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), self.config.primary_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]

        for i in range(1, len(period_data)):
            if i % 2 == 0:
                table_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f9f9f9")))

        period_table.setStyle(TableStyle(table_style))
        elements.append(period_table)

    def _build_format5_mr_section(
        self, report: CPRFormat5Report, elements: list[Any], page_size: tuple[float, float]
    ) -> None:
        """Build Management Reserve section for Format 5 PDF."""
        if not report.mr_rows:
            return

        elements.append(PageBreak())
        elements.append(Paragraph("Management Reserve Tracking", self.styles["SectionHeader"]))

        mr_headers = ["Period", "Beginning MR", "Changes In", "Changes Out", "Ending MR", "Reason"]
        mr_data = [mr_headers]

        for row in report.mr_rows:
            mr_data.append(
                [
                    row.period_name,
                    self._format_currency(row.beginning_mr),
                    self._format_currency(row.changes_in),
                    self._format_currency(row.changes_out),
                    self._format_currency(row.ending_mr),
                    row.reason or "",
                ]
            )

        available_width = page_size[0] - self.config.margin_left - self.config.margin_right
        mr_col_widths = [0.12, 0.14, 0.14, 0.14, 0.14, 0.32]
        mr_col_widths = [w * available_width for w in mr_col_widths]

        mr_table = Table(mr_data, colWidths=mr_col_widths)
        mr_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), self.config.primary_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("ALIGN", (1, 1), (4, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        elements.append(mr_table)

    def _build_format5_variance_section(
        self, report: CPRFormat5Report, elements: list[Any]
    ) -> None:
        """Build variance explanations section for Format 5 PDF."""
        if not report.variance_explanations:
            return

        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Variance Explanations", self.styles["SectionHeader"]))

        for exp in report.variance_explanations:
            var_type = "Schedule" if exp.variance_type == "schedule" else "Cost"
            header = f"{exp.wbs_code} - {exp.wbs_name} ({var_type} Variance)"
            elements.append(Paragraph(f"<b>{header}</b>", self.styles["ReportBody"]))
            elements.append(
                Paragraph(
                    f"Variance: {self._format_currency(exp.variance_amount)} ({self._format_percent(exp.variance_percent)})",
                    self.styles["ReportBody"],
                )
            )
            elements.append(Paragraph(f"Explanation: {exp.explanation}", self.styles["ReportBody"]))
            if exp.corrective_action:
                elements.append(
                    Paragraph(
                        f"Corrective Action: {exp.corrective_action}", self.styles["ReportBody"]
                    )
                )
            if exp.expected_resolution_date:
                elements.append(
                    Paragraph(
                        f"Expected Resolution: {self._format_date(exp.expected_resolution_date)}",
                        self.styles["ReportBody"],
                    )
                )
            elements.append(Spacer(1, 6))

    def generate_format5_pdf(self, report: CPRFormat5Report) -> bytes:
        """Generate PDF for CPR Format 5 (EVMS) report.

        Args:
            report: CPRFormat5Report dataclass

        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        page_size = self._get_page_size()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            topMargin=self.config.margin_top + 0.3 * inch,
            bottomMargin=self.config.margin_bottom + 0.3 * inch,
            leftMargin=self.config.margin_left,
            rightMargin=self.config.margin_right,
        )

        elements: list[Any] = []

        # Title
        elements.append(
            Paragraph("Contract Performance Report - Format 5", self.styles["ReportTitle"])
        )
        elements.append(
            Paragraph("Earned Value Management System Report", self.styles["ReportSubtitle"])
        )
        elements.append(
            Paragraph(
                f"{report.program_name} ({report.program_code})", self.styles["ReportSubtitle"]
            )
        )
        elements.append(Spacer(1, 6))

        # Header info
        header_data = [
            ("Contract Number:", report.contract_number or "N/A"),
            ("Report Date:", self._format_date(report.report_date)),
            ("Reporting Period:", report.reporting_period),
        ]
        elements.extend(self._create_summary_table(header_data, "Report Information"))

        # Summary metrics
        summary_data = [
            ("Budget at Completion (BAC):", self._format_currency(report.bac)),
            ("EAC:", self._format_currency(report.current_eac)),
            ("ETC:", self._format_currency(report.current_etc)),
            ("VAC:", self._format_currency(report.current_vac)),
            ("CPI:", self._format_index(report.cumulative_cpi)),
            ("SPI:", self._format_index(report.cumulative_spi)),
            ("TCPI:", self._format_index(report.cumulative_tcpi)),
            ("% Complete:", self._format_percent(report.percent_complete)),
            ("% Spent:", self._format_percent(report.percent_spent)),
            ("Management Reserve:", self._format_currency(report.current_mr)),
        ]
        elements.extend(self._create_summary_table(summary_data, "Performance Summary"))

        # Build sections via helper methods
        self._build_format5_eac_section(report, elements)
        self._build_format5_period_table(report, elements, page_size)
        self._build_format5_mr_section(report, elements, page_size)
        self._build_format5_variance_section(report, elements)

        # Build document
        doc.build(
            elements,
            onFirstPage=self._create_header_footer,
            onLaterPages=self._create_header_footer,
        )

        return buffer.getvalue()
