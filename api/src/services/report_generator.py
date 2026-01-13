"""Report generation service for CPR Format 1 and other EVMS reports."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from src.models.evms_period import EVMSPeriod, EVMSPeriodData
from src.models.program import Program
from src.models.wbs import WBSElement
from src.services.evms import EVMSCalculator

if TYPE_CHECKING:
    from uuid import UUID


@dataclass
class WBSSummaryRow:
    """A single row in the WBS summary section of CPR Format 1."""

    wbs_code: str
    wbs_name: str
    level: int
    is_control_account: bool
    bac: Decimal
    bcws: Decimal
    bcwp: Decimal
    acwp: Decimal
    cv: Decimal
    sv: Decimal
    cpi: Decimal | None
    spi: Decimal | None
    eac: Decimal | None
    etc: Decimal | None
    vac: Decimal | None


@dataclass
class CPRFormat1Report:
    """Contract Performance Report Format 1 - WBS Summary."""

    # Header Information
    program_name: str
    program_code: str
    contract_number: str | None
    reporting_period: str
    period_start: date
    period_end: date
    report_date: date

    # Summary Totals
    total_bac: Decimal
    total_bcws: Decimal
    total_bcwp: Decimal
    total_acwp: Decimal
    total_cv: Decimal
    total_sv: Decimal
    total_cpi: Decimal | None
    total_spi: Decimal | None
    total_eac: Decimal | None
    total_etc: Decimal | None
    total_vac: Decimal | None

    # Percent Metrics
    percent_complete: Decimal
    percent_spent: Decimal

    # WBS Detail Rows
    wbs_rows: list[WBSSummaryRow]

    # Variance Analysis Notes (optional)
    variance_notes: list[str]


class ReportGenerator:
    """Generates EVMS reports in standard formats."""

    def __init__(
        self,
        program: Program,
        period: EVMSPeriod,
        period_data: list[EVMSPeriodData],
        wbs_elements: list[WBSElement],
    ) -> None:
        """Initialize with program, period, and WBS data."""
        self.program = program
        self.period = period
        self.period_data = period_data
        self.wbs_elements = wbs_elements

        # Build WBS lookup
        self.wbs_by_id: dict[UUID, WBSElement] = {wbs.id: wbs for wbs in wbs_elements}

        # Build period data lookup by WBS
        self.data_by_wbs: dict[UUID, EVMSPeriodData] = {data.wbs_id: data for data in period_data}

    def _build_wbs_row(self, wbs: WBSElement) -> WBSSummaryRow:
        """Build a single WBS summary row."""
        data = self.data_by_wbs.get(wbs.id)

        if data:
            bcws, bcwp, acwp = data.cumulative_bcws, data.cumulative_bcwp, data.cumulative_acwp
            cv, sv, cpi, spi = data.cv, data.sv, data.cpi, data.spi
        else:
            bcws = bcwp = acwp = cv = sv = Decimal("0")
            cpi = spi = None

        bac = wbs.budget_at_completion or Decimal("0")
        eac, etc, vac = self._calculate_projections(bac, acwp, bcwp)

        return WBSSummaryRow(
            wbs_code=wbs.wbs_code,
            wbs_name=wbs.name,
            level=wbs.level,
            is_control_account=wbs.is_control_account,
            bac=bac,
            bcws=bcws,
            bcwp=bcwp,
            acwp=acwp,
            cv=cv,
            sv=sv,
            cpi=cpi,
            spi=spi,
            eac=eac,
            etc=etc,
            vac=vac,
        )

    def _calculate_projections(
        self, bac: Decimal, acwp: Decimal, bcwp: Decimal
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
        """Calculate EAC, ETC, VAC projections."""
        if acwp <= 0 or bcwp <= 0:
            return None, None, None
        eac = EVMSCalculator.calculate_eac(bac, acwp, bcwp)
        if not eac:
            return None, None, None
        etc = EVMSCalculator.calculate_etc(eac, acwp)
        vac = EVMSCalculator.calculate_vac(bac, eac)
        return eac, etc, vac

    def _calculate_percent_metrics(
        self, total_bac: Decimal, total_bcwp: Decimal, total_acwp: Decimal
    ) -> tuple[Decimal, Decimal]:
        """Calculate percent complete and percent spent."""
        if total_bac <= 0:
            return Decimal("0"), Decimal("0")
        percent_complete = (total_bcwp / total_bac * 100).quantize(Decimal("0.01"))
        percent_spent = (total_acwp / total_bac * 100).quantize(Decimal("0.01"))
        return percent_complete, percent_spent

    def generate_cpr_format1(self) -> CPRFormat1Report:
        """Generate CPR Format 1 (WBS Summary) report."""
        wbs_rows = [
            self._build_wbs_row(wbs) for wbs in sorted(self.wbs_elements, key=lambda w: w.path)
        ]

        # Calculate totals from period data
        total_bac = self.program.budget_at_completion or Decimal("0")
        total_bcws, total_bcwp = self.period.cumulative_bcws, self.period.cumulative_bcwp
        total_acwp = self.period.cumulative_acwp
        total_cv = self.period.cost_variance or Decimal("0")
        total_sv = self.period.schedule_variance or Decimal("0")
        total_cpi, total_spi = self.period.cpi, self.period.spi

        total_eac, total_etc, total_vac = self._calculate_projections(
            total_bac, total_acwp, total_bcwp
        )
        percent_complete, percent_spent = self._calculate_percent_metrics(
            total_bac, total_bcwp, total_acwp
        )
        variance_notes = self._generate_variance_notes(wbs_rows)

        return CPRFormat1Report(
            program_name=self.program.name,
            program_code=self.program.code,
            contract_number=self.program.contract_number,
            reporting_period=self.period.period_name,
            period_start=self.period.period_start,
            period_end=self.period.period_end,
            report_date=date.today(),
            total_bac=total_bac,
            total_bcws=total_bcws,
            total_bcwp=total_bcwp,
            total_acwp=total_acwp,
            total_cv=total_cv,
            total_sv=total_sv,
            total_cpi=total_cpi,
            total_spi=total_spi,
            total_eac=total_eac,
            total_etc=total_etc,
            total_vac=total_vac,
            percent_complete=percent_complete,
            percent_spent=percent_spent,
            wbs_rows=wbs_rows,
            variance_notes=variance_notes,
        )

    def _generate_variance_notes(
        self, rows: list[WBSSummaryRow], threshold_percent: Decimal = Decimal("10")
    ) -> list[str]:
        """Generate variance explanation notes for items exceeding threshold."""
        notes: list[str] = []

        for row in rows:
            if row.bac <= 0:
                continue

            # Check cost variance
            cv_percent = abs(row.cv / row.bac * 100) if row.bac > 0 else Decimal("0")
            if cv_percent > threshold_percent:
                direction = "under" if row.cv > 0 else "over"
                notes.append(
                    f"{row.wbs_code} ({row.wbs_name}): Cost variance of "
                    f"${row.cv:,.0f} ({cv_percent:.1f}% {direction} budget) "
                    "requires explanation."
                )

            # Check schedule variance
            sv_percent = abs(row.sv / row.bac * 100) if row.bac > 0 else Decimal("0")
            if sv_percent > threshold_percent:
                direction = "ahead" if row.sv > 0 else "behind"
                notes.append(
                    f"{row.wbs_code} ({row.wbs_name}): Schedule variance of "
                    f"${row.sv:,.0f} ({sv_percent:.1f}% {direction} schedule) "
                    "requires explanation."
                )

        return notes

    def to_dict(self, report: CPRFormat1Report) -> dict[str, Any]:
        """Convert CPR Format 1 report to dictionary for JSON serialization."""

        def decimal_to_str(val: Decimal | None) -> str | None:
            if val is None:
                return None
            return str(val)

        return {
            "program_name": report.program_name,
            "program_code": report.program_code,
            "contract_number": report.contract_number,
            "reporting_period": report.reporting_period,
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "report_date": report.report_date.isoformat(),
            "totals": {
                "bac": decimal_to_str(report.total_bac),
                "bcws": decimal_to_str(report.total_bcws),
                "bcwp": decimal_to_str(report.total_bcwp),
                "acwp": decimal_to_str(report.total_acwp),
                "cv": decimal_to_str(report.total_cv),
                "sv": decimal_to_str(report.total_sv),
                "cpi": decimal_to_str(report.total_cpi),
                "spi": decimal_to_str(report.total_spi),
                "eac": decimal_to_str(report.total_eac),
                "etc": decimal_to_str(report.total_etc),
                "vac": decimal_to_str(report.total_vac),
                "percent_complete": decimal_to_str(report.percent_complete),
                "percent_spent": decimal_to_str(report.percent_spent),
            },
            "wbs_rows": [
                {
                    "wbs_code": row.wbs_code,
                    "wbs_name": row.wbs_name,
                    "level": row.level,
                    "is_control_account": row.is_control_account,
                    "bac": decimal_to_str(row.bac),
                    "bcws": decimal_to_str(row.bcws),
                    "bcwp": decimal_to_str(row.bcwp),
                    "acwp": decimal_to_str(row.acwp),
                    "cv": decimal_to_str(row.cv),
                    "sv": decimal_to_str(row.sv),
                    "cpi": decimal_to_str(row.cpi),
                    "spi": decimal_to_str(row.spi),
                    "eac": decimal_to_str(row.eac),
                    "etc": decimal_to_str(row.etc),
                    "vac": decimal_to_str(row.vac),
                }
                for row in report.wbs_rows
            ],
            "variance_notes": report.variance_notes,
        }

    def to_html(self, report: CPRFormat1Report) -> str:
        """Generate HTML representation of CPR Format 1 report."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>CPR Format 1 - {report.program_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        h2 {{ color: #666; }}
        .header-info {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px; }}
        .header-info div {{ background: #f5f5f5; padding: 10px; border-radius: 4px; }}
        .header-info label {{ font-weight: bold; color: #666; font-size: 12px; }}
        .header-info span {{ display: block; font-size: 14px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: right; }}
        th {{ background: #4a90d9; color: white; }}
        td:first-child, td:nth-child(2) {{ text-align: left; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        tr.total {{ background: #e8f4ff; font-weight: bold; }}
        tr.control-account {{ background: #fff3e0; }}
        .positive {{ color: #2e7d32; }}
        .negative {{ color: #c62828; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
        .summary-card {{ background: #f5f5f5; padding: 15px; border-radius: 8px; text-align: center; }}
        .summary-card.positive {{ border-left: 4px solid #4caf50; }}
        .summary-card.negative {{ border-left: 4px solid #f44336; }}
        .summary-card label {{ font-size: 11px; color: #666; text-transform: uppercase; }}
        .summary-card .value {{ font-size: 24px; font-weight: bold; margin-top: 5px; }}
        .variance-notes {{ background: #fff8e1; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        .variance-notes h3 {{ margin-top: 0; color: #f57c00; }}
        .variance-notes ul {{ margin: 0; padding-left: 20px; }}
        @media print {{
            body {{ margin: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <h1>Contract Performance Report - Format 1</h1>
    <h2>WBS Summary</h2>

    <div class="header-info">
        <div><label>Program</label><span>{report.program_name} ({report.program_code})</span></div>
        <div><label>Contract</label><span>{report.contract_number or "N/A"}</span></div>
        <div><label>Report Date</label><span>{report.report_date.strftime("%B %d, %Y")}</span></div>
        <div><label>Reporting Period</label><span>{report.reporting_period}</span></div>
        <div><label>Period Start</label><span>{report.period_start.strftime("%B %d, %Y")}</span></div>
        <div><label>Period End</label><span>{report.period_end.strftime("%B %d, %Y")}</span></div>
    </div>

    <div class="summary-grid">
        <div class="summary-card">
            <label>Budget at Completion</label>
            <div class="value">${report.total_bac:,.0f}</div>
        </div>
        <div class="summary-card {"positive" if report.total_cv >= 0 else "negative"}">
            <label>Cost Variance</label>
            <div class="value {"positive" if report.total_cv >= 0 else "negative"}">${report.total_cv:,.0f}</div>
        </div>
        <div class="summary-card {"positive" if report.total_sv >= 0 else "negative"}">
            <label>Schedule Variance</label>
            <div class="value {"positive" if report.total_sv >= 0 else "negative"}">${report.total_sv:,.0f}</div>
        </div>
        <div class="summary-card">
            <label>% Complete</label>
            <div class="value">{report.percent_complete:.1f}%</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>WBS Code</th>
                <th>Description</th>
                <th>BAC</th>
                <th>BCWS</th>
                <th>BCWP</th>
                <th>ACWP</th>
                <th>CV</th>
                <th>SV</th>
                <th>CPI</th>
                <th>SPI</th>
                <th>EAC</th>
                <th>VAC</th>
            </tr>
        </thead>
        <tbody>
"""
        # Add WBS rows
        for row in report.wbs_rows:
            ca_class = ' class="control-account"' if row.is_control_account else ""
            cv_class = "positive" if row.cv >= 0 else "negative"
            sv_class = "positive" if row.sv >= 0 else "negative"

            indent = "&nbsp;" * (row.level * 4)

            cpi_str = f"{row.cpi:.2f}" if row.cpi else "N/A"
            spi_str = f"{row.spi:.2f}" if row.spi else "N/A"
            eac_str = f"${row.eac:,.0f}" if row.eac else "N/A"
            vac_str = f"${row.vac:,.0f}" if row.vac else "N/A"

            html += f"""
            <tr{ca_class}>
                <td>{row.wbs_code}</td>
                <td>{indent}{row.wbs_name}{"*" if row.is_control_account else ""}</td>
                <td>${row.bac:,.0f}</td>
                <td>${row.bcws:,.0f}</td>
                <td>${row.bcwp:,.0f}</td>
                <td>${row.acwp:,.0f}</td>
                <td class="{cv_class}">${row.cv:,.0f}</td>
                <td class="{sv_class}">${row.sv:,.0f}</td>
                <td>{cpi_str}</td>
                <td>{spi_str}</td>
                <td>{eac_str}</td>
                <td class="{cv_class}">{vac_str}</td>
            </tr>
"""

        # Add totals row
        total_cv_class = "positive" if report.total_cv >= 0 else "negative"
        total_sv_class = "positive" if report.total_sv >= 0 else "negative"
        total_cpi_str = f"{report.total_cpi:.2f}" if report.total_cpi else "N/A"
        total_spi_str = f"{report.total_spi:.2f}" if report.total_spi else "N/A"
        total_eac_str = f"${report.total_eac:,.0f}" if report.total_eac else "N/A"
        total_vac_str = f"${report.total_vac:,.0f}" if report.total_vac else "N/A"

        html += f"""
            <tr class="total">
                <td colspan="2"><strong>TOTAL</strong></td>
                <td>${report.total_bac:,.0f}</td>
                <td>${report.total_bcws:,.0f}</td>
                <td>${report.total_bcwp:,.0f}</td>
                <td>${report.total_acwp:,.0f}</td>
                <td class="{total_cv_class}">${report.total_cv:,.0f}</td>
                <td class="{total_sv_class}">${report.total_sv:,.0f}</td>
                <td>{total_cpi_str}</td>
                <td>{total_spi_str}</td>
                <td>{total_eac_str}</td>
                <td class="{total_cv_class}">{total_vac_str}</td>
            </tr>
        </tbody>
    </table>

    <p><em>* Indicates Control Account</em></p>
"""

        # Add variance notes if any
        if report.variance_notes:
            html += """
    <div class="variance-notes">
        <h3>Variance Analysis Required</h3>
        <ul>
"""
            for note in report.variance_notes:
                html += f"            <li>{note}</li>\n"
            html += """
        </ul>
    </div>
"""

        html += """
</body>
</html>
"""
        return html
