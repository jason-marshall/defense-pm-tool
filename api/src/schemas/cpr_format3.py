"""CPR Format 3 (Baseline) report schemas.

CPR Format 3 shows time-phased Performance Measurement Baseline (PMB)
with actual performance overlay per DFARS requirements.

Key elements:
- Time-phased BCWS (planned values by period)
- Time-phased BCWP (earned values by period)
- Time-phased ACWP (actual costs by period)
- Cumulative curves for trend analysis
- BAC by period for baseline tracking
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class TimePhaseRow:
    """Single time period row for CPR Format 3.

    Represents one reporting period with current and cumulative values
    for all key EVMS metrics.

    Attributes:
        period_name: Human-readable period identifier (e.g., "Jan 2026")
        period_start: Start date of the period
        period_end: End date of the period
        bcws: Budgeted Cost of Work Scheduled for this period
        bcwp: Budgeted Cost of Work Performed for this period
        acwp: Actual Cost of Work Performed for this period
        cumulative_bcws: Running total of BCWS through this period
        cumulative_bcwp: Running total of BCWP through this period
        cumulative_acwp: Running total of ACWP through this period
        sv: Schedule Variance for this period (BCWP - BCWS)
        cv: Cost Variance for this period (BCWP - ACWP)
        eac: Estimate at Completion as of this period
    """

    period_name: str
    period_start: date
    period_end: date

    # Current period values
    bcws: Decimal
    bcwp: Decimal
    acwp: Decimal

    # Cumulative values
    cumulative_bcws: Decimal
    cumulative_bcwp: Decimal
    cumulative_acwp: Decimal

    # Variances
    sv: Decimal  # BCWP - BCWS
    cv: Decimal  # BCWP - ACWP

    # EAC/ETC for this period
    eac: Decimal | None = None

    @property
    def spi(self) -> Decimal | None:
        """Calculate period SPI (BCWP/BCWS)."""
        if self.bcws and self.bcws > 0:
            return (self.bcwp / self.bcws).quantize(Decimal("0.001"))
        return None

    @property
    def cpi(self) -> Decimal | None:
        """Calculate period CPI (BCWP/ACWP)."""
        if self.acwp and self.acwp > 0:
            return (self.bcwp / self.acwp).quantize(Decimal("0.001"))
        return None

    @property
    def cumulative_spi(self) -> Decimal | None:
        """Calculate cumulative SPI."""
        if self.cumulative_bcws and self.cumulative_bcws > 0:
            return (self.cumulative_bcwp / self.cumulative_bcws).quantize(Decimal("0.001"))
        return None

    @property
    def cumulative_cpi(self) -> Decimal | None:
        """Calculate cumulative CPI."""
        if self.cumulative_acwp and self.cumulative_acwp > 0:
            return (self.cumulative_bcwp / self.cumulative_acwp).quantize(Decimal("0.001"))
        return None


@dataclass
class CPRFormat3Report:
    """Complete CPR Format 3 (Baseline) report.

    This report shows time-phased PMB with actual performance,
    enabling trend analysis and forecasting per DFARS requirements.

    Attributes:
        program_name: Name of the program
        program_code: Program code identifier
        contract_number: Contract number (if applicable)
        baseline_name: Name of the baseline being reported against
        baseline_version: Version number of the baseline
        report_date: Date the report was generated
        bac: Budget at Completion
        current_period: Name of the current/latest period
        percent_complete: Overall % complete (BCWP/BAC)
        percent_spent: Overall % spent (ACWP/BAC)
        total_bcws: Cumulative BCWS to date
        total_bcwp: Cumulative BCWP to date
        total_acwp: Cumulative ACWP to date
        total_sv: Cumulative Schedule Variance
        total_cv: Cumulative Cost Variance
        eac: Estimate at Completion
        etc: Estimate to Complete
        vac: Variance at Completion
        cpi: Cost Performance Index
        spi: Schedule Performance Index
        tcpi: To-Complete Performance Index
        time_phase_rows: List of time-phased data rows
        baseline_finish_date: Original scheduled completion date
        forecast_finish_date: Current forecast completion date
        schedule_variance_days: Days ahead/behind schedule
    """

    # Header info
    program_name: str
    program_code: str
    contract_number: str | None
    baseline_name: str
    baseline_version: int
    report_date: date

    # Summary metrics
    bac: Decimal
    current_period: str
    percent_complete: Decimal
    percent_spent: Decimal

    # Cumulative metrics
    total_bcws: Decimal
    total_bcwp: Decimal
    total_acwp: Decimal
    total_sv: Decimal
    total_cv: Decimal
    eac: Decimal
    etc: Decimal
    vac: Decimal

    # Performance indices
    cpi: Decimal | None
    spi: Decimal | None
    tcpi: Decimal | None

    # Time-phased data
    time_phase_rows: list[TimePhaseRow] = field(default_factory=list)

    # Baseline vs actual summary
    baseline_finish_date: date | None = None
    forecast_finish_date: date | None = None
    schedule_variance_days: int = 0

    @property
    def is_behind_schedule(self) -> bool:
        """Check if project is behind schedule."""
        return self.total_sv < 0

    @property
    def is_over_budget(self) -> bool:
        """Check if project is over budget."""
        return self.total_cv < 0

    @property
    def status_color(self) -> str:
        """Get status color based on performance.

        Returns:
            'green' if on track, 'yellow' if minor issues, 'red' if significant issues
        """
        if self.cpi is None or self.spi is None:
            return "gray"

        # Both indices below 0.9 is red
        if self.cpi < Decimal("0.9") and self.spi < Decimal("0.9"):
            return "red"

        # Either index below 0.9 is yellow
        if self.cpi < Decimal("0.9") or self.spi < Decimal("0.9"):
            return "yellow"

        # Both indices at or above 0.9 is green
        return "green"

    def get_period_by_name(self, period_name: str) -> TimePhaseRow | None:
        """Get a specific period by name."""
        for row in self.time_phase_rows:
            if row.period_name == period_name:
                return row
        return None

    def get_periods_in_range(self, start: date, end: date) -> list[TimePhaseRow]:
        """Get periods within a date range."""
        return [
            row
            for row in self.time_phase_rows
            if row.period_start >= start and row.period_end <= end
        ]
