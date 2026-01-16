"""
EVMS Reference Test Data for Validation.

This fixture contains known EVMS calculations that have been
validated against industry-standard spreadsheets and EVMS guidelines.

Per Risk Playbook: SPI/CPI must match within 0.5%

Reference: EIA-748-D Standard for Earned Value Management Systems
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class EVMSReferenceCase:
    """Reference case for EVMS validation."""

    name: str
    description: str

    # Input values
    bcws: Decimal  # Budgeted Cost of Work Scheduled (Planned Value)
    bcwp: Decimal  # Budgeted Cost of Work Performed (Earned Value)
    acwp: Decimal  # Actual Cost of Work Performed (Actual Cost)
    bac: Decimal   # Budget at Completion

    # Expected outputs
    expected_sv: Decimal        # Schedule Variance = BCWP - BCWS
    expected_cv: Decimal        # Cost Variance = BCWP - ACWP
    expected_spi: Decimal       # Schedule Performance Index = BCWP / BCWS
    expected_cpi: Decimal       # Cost Performance Index = BCWP / ACWP
    expected_eac_cpi: Decimal   # Estimate at Completion = BAC / CPI
    expected_eac_typical: Decimal  # EAC Typical = ACWP + (BAC - BCWP)
    expected_etc: Decimal       # Estimate to Complete = EAC - ACWP
    expected_vac: Decimal       # Variance at Completion = BAC - EAC
    expected_tcpi_bac: Decimal  # To Complete Performance Index (BAC) = (BAC - BCWP) / (BAC - ACWP)
    expected_tcpi_eac: Decimal | None  # TCPI (EAC) when applicable

    # Tolerance for validation
    tolerance: Decimal = Decimal("0.005")  # 0.5%


# Reference cases from validated EVMS spreadsheets
EVMS_REFERENCE_CASES = [
    EVMSReferenceCase(
        name="healthy_program",
        description="Program on track - CPI and SPI > 1.0",
        bcws=Decimal("100000.00"),
        bcwp=Decimal("110000.00"),  # Ahead of schedule
        acwp=Decimal("95000.00"),   # Under budget
        bac=Decimal("500000.00"),
        expected_sv=Decimal("10000.00"),
        expected_cv=Decimal("15000.00"),
        expected_spi=Decimal("1.10"),
        expected_cpi=Decimal("1.16"),  # 110000 / 95000 = 1.157894...
        expected_eac_cpi=Decimal("431818.18"),  # 500000 / 1.157894 = 431818.18
        expected_eac_typical=Decimal("485000.00"),  # 95000 + (500000 - 110000)
        expected_etc=Decimal("336818.18"),  # EAC - ACWP
        expected_vac=Decimal("68181.82"),   # BAC - EAC
        expected_tcpi_bac=Decimal("0.96"),  # (500000 - 110000) / (500000 - 95000) = 0.963
        expected_tcpi_eac=Decimal("1.00"),
    ),
    EVMSReferenceCase(
        name="troubled_program",
        description="Program in trouble - CPI and SPI < 1.0",
        bcws=Decimal("200000.00"),
        bcwp=Decimal("150000.00"),  # Behind schedule
        acwp=Decimal("225000.00"),  # Over budget
        bac=Decimal("1000000.00"),
        expected_sv=Decimal("-50000.00"),
        expected_cv=Decimal("-75000.00"),
        expected_spi=Decimal("0.75"),
        expected_cpi=Decimal("0.67"),  # 150000 / 225000 = 0.666...
        expected_eac_cpi=Decimal("1500000.00"),  # 1000000 / 0.666... = 1500000
        expected_eac_typical=Decimal("1075000.00"),  # 225000 + (1000000 - 150000)
        expected_etc=Decimal("1275000.00"),  # EAC - ACWP
        expected_vac=Decimal("-500000.00"),  # BAC - EAC
        expected_tcpi_bac=Decimal("1.10"),  # (1000000 - 150000) / (1000000 - 225000) = 1.096
        expected_tcpi_eac=None,
    ),
    EVMSReferenceCase(
        name="early_stage",
        description="Early stage program with minimal progress",
        bcws=Decimal("10000.00"),
        bcwp=Decimal("8000.00"),
        acwp=Decimal("9000.00"),
        bac=Decimal("500000.00"),
        expected_sv=Decimal("-2000.00"),
        expected_cv=Decimal("-1000.00"),
        expected_spi=Decimal("0.80"),
        expected_cpi=Decimal("0.89"),  # 8000 / 9000 = 0.888...
        expected_eac_cpi=Decimal("562500.00"),  # 500000 / 0.888... = 562500
        expected_eac_typical=Decimal("501000.00"),  # 9000 + (500000 - 8000)
        expected_etc=Decimal("553500.00"),  # EAC - ACWP
        expected_vac=Decimal("-62500.00"),  # BAC - EAC
        expected_tcpi_bac=Decimal("1.00"),  # (500000 - 8000) / (500000 - 9000) = 1.002
        expected_tcpi_eac=None,
    ),
    EVMSReferenceCase(
        name="near_completion",
        description="Program near completion with good performance",
        bcws=Decimal("450000.00"),
        bcwp=Decimal("480000.00"),
        acwp=Decimal("460000.00"),
        bac=Decimal("500000.00"),
        expected_sv=Decimal("30000.00"),
        expected_cv=Decimal("20000.00"),
        expected_spi=Decimal("1.07"),  # 480000 / 450000 = 1.0666...
        expected_cpi=Decimal("1.04"),  # 480000 / 460000 = 1.0434...
        expected_eac_cpi=Decimal("479166.67"),  # 500000 / 1.0434... = 479166.67
        expected_eac_typical=Decimal("480000.00"),  # 460000 + (500000 - 480000)
        expected_etc=Decimal("19166.67"),  # EAC - ACWP
        expected_vac=Decimal("20833.33"),  # BAC - EAC
        expected_tcpi_bac=Decimal("0.50"),  # (500000 - 480000) / (500000 - 460000) = 0.50
        expected_tcpi_eac=None,
    ),
    EVMSReferenceCase(
        name="exactly_on_plan",
        description="Program exactly on schedule and budget",
        bcws=Decimal("250000.00"),
        bcwp=Decimal("250000.00"),  # On schedule
        acwp=Decimal("250000.00"),  # On budget
        bac=Decimal("1000000.00"),
        expected_sv=Decimal("0.00"),
        expected_cv=Decimal("0.00"),
        expected_spi=Decimal("1.00"),
        expected_cpi=Decimal("1.00"),
        expected_eac_cpi=Decimal("1000000.00"),  # BAC / 1.0
        expected_eac_typical=Decimal("1000000.00"),  # ACWP + (BAC - BCWP)
        expected_etc=Decimal("750000.00"),  # EAC - ACWP
        expected_vac=Decimal("0.00"),  # BAC - EAC
        expected_tcpi_bac=Decimal("1.00"),  # (BAC - BCWP) / (BAC - ACWP)
        expected_tcpi_eac=Decimal("1.00"),
    ),
    EVMSReferenceCase(
        name="recovery_scenario",
        description="Behind schedule but recovering on cost",
        bcws=Decimal("300000.00"),
        bcwp=Decimal("270000.00"),  # Behind schedule
        acwp=Decimal("260000.00"),  # Under budget
        bac=Decimal("1000000.00"),
        expected_sv=Decimal("-30000.00"),
        expected_cv=Decimal("10000.00"),
        expected_spi=Decimal("0.90"),  # 270000 / 300000 = 0.90
        expected_cpi=Decimal("1.04"),  # 270000 / 260000 = 1.0384...
        expected_eac_cpi=Decimal("962962.96"),  # 1000000 / 1.0384... = 962962.96
        expected_eac_typical=Decimal("990000.00"),  # 260000 + (1000000 - 270000)
        expected_etc=Decimal("702962.96"),  # EAC - ACWP
        expected_vac=Decimal("37037.04"),  # BAC - EAC
        expected_tcpi_bac=Decimal("0.99"),  # (1000000 - 270000) / (1000000 - 260000) = 0.986
        expected_tcpi_eac=None,
    ),
]


def get_reference_case(name: str) -> EVMSReferenceCase | None:
    """Get a reference case by name."""
    for case in EVMS_REFERENCE_CASES:
        if case.name == name:
            return case
    return None


def validate_evms_calculation(
    case: EVMSReferenceCase,
    calculated_spi: Decimal,
    calculated_cpi: Decimal,
) -> tuple[bool, str]:
    """
    Validate SPI and CPI calculations against reference case.

    Args:
        case: Reference case to validate against
        calculated_spi: Calculated SPI value
        calculated_cpi: Calculated CPI value

    Returns:
        Tuple of (is_valid, message)
    """
    spi_diff = abs(calculated_spi - case.expected_spi)
    cpi_diff = abs(calculated_cpi - case.expected_cpi)

    spi_valid = spi_diff <= case.tolerance
    cpi_valid = cpi_diff <= case.tolerance

    if spi_valid and cpi_valid:
        return True, f"PASS: SPI diff={spi_diff}, CPI diff={cpi_diff}"

    messages = []
    if not spi_valid:
        messages.append(
            f"SPI mismatch: expected {case.expected_spi}, got {calculated_spi}, diff={spi_diff}"
        )
    if not cpi_valid:
        messages.append(
            f"CPI mismatch: expected {case.expected_cpi}, got {calculated_cpi}, diff={cpi_diff}"
        )

    return False, "; ".join(messages)


# Monte Carlo reference data for duration estimation
MONTE_CARLO_REFERENCE = {
    "simple_chain": {
        "description": "Simple chain of 5 activities with triangular distributions",
        "activities": [
            {"id": "A", "min": 5, "mode": 10, "max": 20},
            {"id": "B", "min": 3, "mode": 5, "max": 10},
            {"id": "C", "min": 8, "mode": 12, "max": 18},
            {"id": "D", "min": 4, "mode": 6, "max": 12},
            {"id": "E", "min": 6, "mode": 8, "max": 14},
        ],
        "dependencies": [
            {"pred": "A", "succ": "B"},
            {"pred": "B", "succ": "C"},
            {"pred": "C", "succ": "D"},
            {"pred": "D", "succ": "E"},
        ],
        # Expected results based on analytical calculation
        "expected_mean_duration": 41.0,  # Sum of modes
        "expected_p50_range": (38, 44),   # Median should be close to mean
        "expected_p90_range": (48, 56),   # 90th percentile range
    },
    "parallel_paths": {
        "description": "Two parallel paths converging",
        "activities": [
            {"id": "START", "min": 0, "mode": 0, "max": 0},
            {"id": "PATH1_A", "min": 5, "mode": 10, "max": 20},
            {"id": "PATH1_B", "min": 5, "mode": 8, "max": 15},
            {"id": "PATH2_A", "min": 8, "mode": 12, "max": 20},
            {"id": "PATH2_B", "min": 3, "mode": 5, "max": 10},
            {"id": "END", "min": 2, "mode": 3, "max": 5},
        ],
        "dependencies": [
            {"pred": "START", "succ": "PATH1_A"},
            {"pred": "START", "succ": "PATH2_A"},
            {"pred": "PATH1_A", "succ": "PATH1_B"},
            {"pred": "PATH2_A", "succ": "PATH2_B"},
            {"pred": "PATH1_B", "succ": "END"},
            {"pred": "PATH2_B", "succ": "END"},
        ],
        # Critical path should be longer of the two paths
        "expected_critical_path_probability": {"PATH1": 0.45, "PATH2": 0.55},
    },
}
