"""CPR Format 5 (EVMS) report schemas.

CPR Format 5 provides detailed Earned Value Management data
per DFARS requirements for variance analysis and forecasting.

Key elements per DFARS:
- Monthly/quarterly BCWS, BCWP, ACWP
- Variance percentages and trends
- Management Reserve (MR) changes
- Estimate at Completion (EAC) analysis
- Narrative variance explanations
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class Format5PeriodRow:
    """Single period row for CPR Format 5.

    Contains period-level and cumulative EVMS metrics
    for variance analysis and trend tracking.
    """

    period_name: str
    period_start: date
    period_end: date

    # Period values (current period only)
    bcws: Decimal
    bcwp: Decimal
    acwp: Decimal

    # Cumulative values (start through this period)
    cumulative_bcws: Decimal
    cumulative_bcwp: Decimal
    cumulative_acwp: Decimal

    # Variances (period and cumulative)
    period_sv: Decimal  # Period Schedule Variance
    period_cv: Decimal  # Period Cost Variance
    cumulative_sv: Decimal  # Cumulative Schedule Variance
    cumulative_cv: Decimal  # Cumulative Cost Variance

    # Variance percentages (cumulative)
    sv_percent: Decimal
    cv_percent: Decimal

    # Performance indices
    spi: Decimal | None
    cpi: Decimal | None

    # Forecasts
    eac: Decimal  # Estimate at Completion
    etc: Decimal  # Estimate to Complete
    vac: Decimal  # Variance at Completion
    tcpi: Decimal | None  # To-Complete Performance Index


@dataclass
class ManagementReserveRow:
    """Management Reserve (MR) changes for Format 5.

    Tracks changes to management reserve with explanations
    per DFARS reporting requirements.
    """

    period_name: str
    beginning_mr: Decimal
    changes_in: Decimal  # MR added
    changes_out: Decimal  # MR released to work packages
    ending_mr: Decimal
    reason: str | None = None


@dataclass
class VarianceExplanation:
    """Variance explanation for significant variances.

    Per DFARS, variances exceeding threshold require
    written explanation and corrective action plans.
    """

    wbs_code: str
    wbs_name: str
    variance_type: str  # "schedule" or "cost"
    variance_amount: Decimal
    variance_percent: Decimal
    explanation: str
    corrective_action: str | None = None
    expected_resolution_date: date | None = None


@dataclass
class EACAnalysis:
    """EAC analysis comparing different estimation methods.

    Per EVMS GL 27, multiple EAC methods should be compared
    to validate the management estimate.
    """

    eac_cpi: Decimal  # BAC / CPI
    eac_spi_cpi: Decimal  # Comprehensive: ACWP + (BAC - BCWP) / (CPI x SPI)
    eac_management: Decimal  # Management bottom-up estimate
    eac_selected: Decimal  # Selected EAC for reporting
    selection_rationale: str | None = None


@dataclass
class CPRFormat5Report:
    """Complete CPR Format 5 (EVMS) report.

    Contains all elements required for DFARS-compliant
    CPR Format 5 reporting including:
    - Summary performance metrics
    - Period-by-period EVMS data
    - Management Reserve tracking
    - Variance explanations
    - EAC analysis
    """

    # Header info
    program_name: str
    program_code: str
    contract_number: str | None
    report_date: date
    reporting_period: str

    # Summary metrics (at time of report)
    bac: Decimal
    current_eac: Decimal
    current_etc: Decimal
    current_vac: Decimal

    # Performance indices (cumulative)
    cumulative_cpi: Decimal | None
    cumulative_spi: Decimal | None
    cumulative_tcpi: Decimal | None

    # Percent metrics
    percent_complete: Decimal
    percent_spent: Decimal

    # Period data (typically 12-18 months of history)
    period_rows: list[Format5PeriodRow] = field(default_factory=list)

    # Management Reserve tracking
    mr_rows: list[ManagementReserveRow] = field(default_factory=list)
    current_mr: Decimal = Decimal("0")

    # Variance explanations (for variances > threshold)
    variance_explanations: list[VarianceExplanation] = field(default_factory=list)

    # EAC Analysis
    eac_analysis: EACAnalysis | None = None

    # Report metadata
    generated_at: date | None = None
    generated_by: str | None = None


@dataclass
class Format5ExportConfig:
    """Configuration for CPR Format 5 export."""

    include_mr: bool = True
    include_explanations: bool = True
    variance_threshold_percent: Decimal = Decimal("10")  # Require explanation above this
    periods_to_include: int = 12  # Number of periods to include
    include_eac_analysis: bool = True
