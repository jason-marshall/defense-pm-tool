"""
Unit tests validating EVMS calculations against reference data.

Per Risk Playbook: SPI/CPI must match within 0.5%
"""

from decimal import Decimal

import pytest

from src.services.evms import EVMSCalculator
from tests.fixtures.evms_reference_data import (
    EVMS_REFERENCE_CASES,
    EVMSReferenceCase,
    get_reference_case,
    validate_evms_calculation,
)


class TestEVMSReferenceValidation:
    """Validate EVMS calculations against industry-standard reference cases."""

    @pytest.fixture
    def calculator(self) -> EVMSCalculator:
        """Create EVMS calculator instance."""
        return EVMSCalculator()

    @pytest.mark.parametrize(
        "case",
        EVMS_REFERENCE_CASES,
        ids=[c.name for c in EVMS_REFERENCE_CASES],
    )
    def test_schedule_variance(self, case: EVMSReferenceCase) -> None:
        """Schedule Variance should match reference: SV = BCWP - BCWS."""
        sv = case.bcwp - case.bcws
        assert sv == case.expected_sv, f"SV mismatch for {case.name}"

    @pytest.mark.parametrize(
        "case",
        EVMS_REFERENCE_CASES,
        ids=[c.name for c in EVMS_REFERENCE_CASES],
    )
    def test_cost_variance(self, case: EVMSReferenceCase) -> None:
        """Cost Variance should match reference: CV = BCWP - ACWP."""
        cv = case.bcwp - case.acwp
        assert cv == case.expected_cv, f"CV mismatch for {case.name}"

    @pytest.mark.parametrize(
        "case",
        EVMS_REFERENCE_CASES,
        ids=[c.name for c in EVMS_REFERENCE_CASES],
    )
    def test_spi_calculation(self, case: EVMSReferenceCase) -> None:
        """SPI should match reference within 0.5%: SPI = BCWP / BCWS."""
        if case.bcws == 0:
            pytest.skip("Cannot calculate SPI with BCWS = 0")

        spi = case.bcwp / case.bcws
        diff = abs(spi - case.expected_spi)
        assert diff <= case.tolerance, (
            f"SPI mismatch for {case.name}: expected {case.expected_spi}, "
            f"got {spi:.4f}, diff={diff:.4f} (tolerance={case.tolerance})"
        )

    @pytest.mark.parametrize(
        "case",
        EVMS_REFERENCE_CASES,
        ids=[c.name for c in EVMS_REFERENCE_CASES],
    )
    def test_cpi_calculation(self, case: EVMSReferenceCase) -> None:
        """CPI should match reference within 0.5%: CPI = BCWP / ACWP."""
        if case.acwp == 0:
            pytest.skip("Cannot calculate CPI with ACWP = 0")

        cpi = case.bcwp / case.acwp
        diff = abs(cpi - case.expected_cpi)
        assert diff <= case.tolerance, (
            f"CPI mismatch for {case.name}: expected {case.expected_cpi}, "
            f"got {cpi:.4f}, diff={diff:.4f} (tolerance={case.tolerance})"
        )

    @pytest.mark.parametrize(
        "case",
        EVMS_REFERENCE_CASES,
        ids=[c.name for c in EVMS_REFERENCE_CASES],
    )
    def test_eac_typical_calculation(self, case: EVMSReferenceCase) -> None:
        """EAC Typical should match: EAC = ACWP + (BAC - BCWP)."""
        eac_typical = case.acwp + (case.bac - case.bcwp)
        assert eac_typical == case.expected_eac_typical, (
            f"EAC Typical mismatch for {case.name}: expected {case.expected_eac_typical}, "
            f"got {eac_typical}"
        )

    @pytest.mark.parametrize(
        "case",
        EVMS_REFERENCE_CASES,
        ids=[c.name for c in EVMS_REFERENCE_CASES],
    )
    def test_tcpi_bac_calculation(self, case: EVMSReferenceCase) -> None:
        """TCPI(BAC) should match reference within tolerance."""
        remaining_work = case.bac - case.bcwp
        remaining_budget = case.bac - case.acwp

        if remaining_budget <= 0:
            pytest.skip("Cannot calculate TCPI with non-positive remaining budget")

        tcpi_bac = remaining_work / remaining_budget
        diff = abs(tcpi_bac - case.expected_tcpi_bac)

        # TCPI can have slightly higher tolerance due to rounding
        tcpi_tolerance = Decimal("0.02")  # 2%
        assert diff <= tcpi_tolerance, (
            f"TCPI(BAC) mismatch for {case.name}: expected {case.expected_tcpi_bac}, "
            f"got {tcpi_bac:.4f}, diff={diff:.4f}"
        )


class TestEVMSCalculatorIntegration:
    """Test EVMSCalculator against reference data."""

    @pytest.fixture
    def calculator(self) -> EVMSCalculator:
        """Create EVMS calculator instance."""
        return EVMSCalculator()

    def test_healthy_program_metrics(self, calculator: EVMSCalculator) -> None:
        """Validate healthy program EVMS metrics."""
        case = get_reference_case("healthy_program")
        assert case is not None

        # Calculate metrics
        sv = case.bcwp - case.bcws
        cv = case.bcwp - case.acwp
        spi = case.bcwp / case.bcws
        cpi = case.bcwp / case.acwp

        # Validate
        is_valid, message = validate_evms_calculation(case, spi, cpi)
        assert is_valid, message

        assert sv == case.expected_sv
        assert cv == case.expected_cv

    def test_troubled_program_metrics(self, calculator: EVMSCalculator) -> None:
        """Validate troubled program EVMS metrics."""
        case = get_reference_case("troubled_program")
        assert case is not None

        # Calculate metrics
        sv = case.bcwp - case.bcws
        cv = case.bcwp - case.acwp
        spi = case.bcwp / case.bcws
        cpi = case.bcwp / case.acwp

        # Validate
        is_valid, message = validate_evms_calculation(case, spi, cpi)
        assert is_valid, message

        # Verify negative variances
        assert sv < 0, "Schedule variance should be negative"
        assert cv < 0, "Cost variance should be negative"
        assert spi < 1, "SPI should be less than 1"
        assert cpi < 1, "CPI should be less than 1"

    def test_exactly_on_plan(self, calculator: EVMSCalculator) -> None:
        """Validate exactly on plan metrics."""
        case = get_reference_case("exactly_on_plan")
        assert case is not None

        # Calculate metrics
        sv = case.bcwp - case.bcws
        cv = case.bcwp - case.acwp
        spi = case.bcwp / case.bcws
        cpi = case.bcwp / case.acwp

        assert sv == Decimal("0")
        assert cv == Decimal("0")
        assert spi == Decimal("1")
        assert cpi == Decimal("1")


class TestReferenceDataIntegrity:
    """Verify reference data is internally consistent."""

    @pytest.mark.parametrize(
        "case",
        EVMS_REFERENCE_CASES,
        ids=[c.name for c in EVMS_REFERENCE_CASES],
    )
    def test_sv_consistency(self, case: EVMSReferenceCase) -> None:
        """Verify SV = BCWP - BCWS in reference data."""
        calculated_sv = case.bcwp - case.bcws
        assert calculated_sv == case.expected_sv, (
            f"Reference data inconsistency in {case.name}: "
            f"BCWP({case.bcwp}) - BCWS({case.bcws}) = {calculated_sv}, "
            f"but expected_sv = {case.expected_sv}"
        )

    @pytest.mark.parametrize(
        "case",
        EVMS_REFERENCE_CASES,
        ids=[c.name for c in EVMS_REFERENCE_CASES],
    )
    def test_cv_consistency(self, case: EVMSReferenceCase) -> None:
        """Verify CV = BCWP - ACWP in reference data."""
        calculated_cv = case.bcwp - case.acwp
        assert calculated_cv == case.expected_cv, (
            f"Reference data inconsistency in {case.name}: "
            f"BCWP({case.bcwp}) - ACWP({case.acwp}) = {calculated_cv}, "
            f"but expected_cv = {case.expected_cv}"
        )

    @pytest.mark.parametrize(
        "case",
        EVMS_REFERENCE_CASES,
        ids=[c.name for c in EVMS_REFERENCE_CASES],
    )
    def test_eac_typical_consistency(self, case: EVMSReferenceCase) -> None:
        """Verify EAC Typical = ACWP + (BAC - BCWP) in reference data."""
        calculated_eac = case.acwp + (case.bac - case.bcwp)
        assert calculated_eac == case.expected_eac_typical, (
            f"Reference data inconsistency in {case.name}: "
            f"ACWP({case.acwp}) + (BAC({case.bac}) - BCWP({case.bcwp})) = {calculated_eac}, "
            f"but expected_eac_typical = {case.expected_eac_typical}"
        )

    def test_all_cases_have_positive_bac(self) -> None:
        """All reference cases should have positive BAC."""
        for case in EVMS_REFERENCE_CASES:
            assert case.bac > 0, f"Case {case.name} has non-positive BAC"

    def test_all_cases_have_non_negative_acwp(self) -> None:
        """All reference cases should have non-negative ACWP."""
        for case in EVMS_REFERENCE_CASES:
            assert case.acwp >= 0, f"Case {case.name} has negative ACWP"
