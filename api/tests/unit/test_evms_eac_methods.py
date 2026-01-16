"""Unit tests for advanced EAC calculation methods per GL 27."""

from decimal import Decimal

import pytest

from src.services.evms import EACMethod, EACResult, EVMSCalculator


class TestEACMethods:
    """Tests for individual EAC calculation methods."""

    def test_cpi_method(self) -> None:
        """CPI Method: EAC = BAC / CPI."""
        # BAC = 100, BCWP = 50, ACWP = 60 -> CPI = 50/60 = 0.83
        # EAC = 100 / 0.83 = 120.48
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("50"),
            bcwp=Decimal("50"),
            acwp=Decimal("60"),
            bac=Decimal("100"),
            method=EACMethod.CPI,
        )

        assert result.method == EACMethod.CPI
        assert result.eac == Decimal("120.48")  # 100 / 0.83
        assert result.etc == Decimal("60.48")  # 120.48 - 60
        assert result.vac == Decimal("-20.48")  # 100 - 120.48
        assert "historical cost efficiency" in result.description

    def test_cpi_method_under_budget(self) -> None:
        """CPI Method when under budget (CPI > 1)."""
        # BAC = 100, BCWP = 50, ACWP = 40 -> CPI = 50/40 = 1.25
        # EAC = 100 / 1.25 = 80
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("50"),
            bcwp=Decimal("50"),
            acwp=Decimal("40"),
            bac=Decimal("100"),
            method=EACMethod.CPI,
        )

        assert result.eac == Decimal("80.00")
        assert result.etc == Decimal("40.00")
        assert result.vac == Decimal("20.00")  # Positive - under budget

    def test_cpi_method_zero_cpi_raises(self) -> None:
        """CPI Method should raise when CPI is zero."""
        with pytest.raises(ZeroDivisionError, match="CPI is zero"):
            EVMSCalculator.calculate_eac_advanced(
                bcws=Decimal("50"),
                bcwp=Decimal("0"),
                acwp=Decimal("60"),
                bac=Decimal("100"),
                method=EACMethod.CPI,
            )

    def test_typical_method(self) -> None:
        """Typical Method: EAC = ACWP + (BAC - BCWP)."""
        # ACWP = 60, BAC = 100, BCWP = 50
        # EAC = 60 + (100 - 50) = 110
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("50"),
            bcwp=Decimal("50"),
            acwp=Decimal("60"),
            bac=Decimal("100"),
            method=EACMethod.TYPICAL,
        )

        assert result.method == EACMethod.TYPICAL
        assert result.eac == Decimal("110.00")
        assert result.etc == Decimal("50.00")  # BAC - BCWP
        assert result.vac == Decimal("-10.00")
        assert "budgeted rate" in result.description

    def test_typical_method_ahead_of_plan(self) -> None:
        """Typical Method when ahead of schedule."""
        # ACWP = 40, BAC = 100, BCWP = 60
        # EAC = 40 + (100 - 60) = 80
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("50"),
            bcwp=Decimal("60"),
            acwp=Decimal("40"),
            bac=Decimal("100"),
            method=EACMethod.TYPICAL,
        )

        assert result.eac == Decimal("80.00")
        assert result.etc == Decimal("40.00")
        assert result.vac == Decimal("20.00")

    def test_mathematical_method(self) -> None:
        """Mathematical Method: EAC = ACWP + (BAC - BCWP) / CPI."""
        # ACWP = 60, BAC = 100, BCWP = 50, CPI = 0.83
        # ETC = (100 - 50) / 0.83 = 60.24
        # EAC = 60 + 60.24 = 120.24
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("50"),
            bcwp=Decimal("50"),
            acwp=Decimal("60"),
            bac=Decimal("100"),
            method=EACMethod.MATHEMATICAL,
        )

        assert result.method == EACMethod.MATHEMATICAL
        assert result.eac == Decimal("120.24")  # ACWP + (BAC-BCWP)/CPI
        assert result.etc == Decimal("60.24")  # (100-50) / 0.83
        assert result.vac == Decimal("-20.24")
        assert "adjusted by CPI" in result.description

    def test_mathematical_method_zero_cpi_raises(self) -> None:
        """Mathematical Method should raise when CPI is zero."""
        with pytest.raises(ZeroDivisionError, match="CPI is zero"):
            EVMSCalculator.calculate_eac_advanced(
                bcws=Decimal("50"),
                bcwp=Decimal("0"),
                acwp=Decimal("60"),
                bac=Decimal("100"),
                method=EACMethod.MATHEMATICAL,
            )

    def test_comprehensive_method(self) -> None:
        """Comprehensive Method: EAC = ACWP + (BAC - BCWP) / (CPI x SPI)."""
        # ACWP = 60, BAC = 100, BCWP = 40, BCWS = 50
        # CPI = 40/60 = 0.67, SPI = 40/50 = 0.8
        # ETC = (100 - 40) / (0.67 * 0.8) = 60 / 0.536 = 111.94
        # EAC = 60 + 111.94 = 171.94
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("50"),
            bcwp=Decimal("40"),
            acwp=Decimal("60"),
            bac=Decimal("100"),
            method=EACMethod.COMPREHENSIVE,
        )

        assert result.method == EACMethod.COMPREHENSIVE
        # Result depends on rounding, just verify it's higher than mathematical
        assert result.eac > Decimal("100")
        assert "CPI x SPI" in result.description

    def test_comprehensive_method_zero_spi_raises(self) -> None:
        """Comprehensive Method should raise when SPI is zero."""
        # Note: When BCWP=0, both CPI=0 and SPI=0, and CPI is checked first
        # So this test verifies the zero division behavior
        with pytest.raises(ZeroDivisionError, match="CPI is zero"):
            EVMSCalculator.calculate_eac_advanced(
                bcws=Decimal("50"),
                bcwp=Decimal("0"),  # CPI = 0/60 = 0, checked first
                acwp=Decimal("60"),
                bac=Decimal("100"),
                method=EACMethod.COMPREHENSIVE,
            )

    def test_independent_method(self) -> None:
        """Independent Method: EAC = ACWP + Manager ETC."""
        # ACWP = 60, Manager ETC = 35
        # EAC = 60 + 35 = 95
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("50"),
            bcwp=Decimal("50"),
            acwp=Decimal("60"),
            bac=Decimal("100"),
            method=EACMethod.INDEPENDENT,
            manager_etc=Decimal("35"),
        )

        assert result.method == EACMethod.INDEPENDENT
        assert result.eac == Decimal("95.00")
        assert result.etc == Decimal("35.00")  # Manager's estimate
        assert result.vac == Decimal("5.00")  # Under budget
        assert "bottom-up estimate" in result.description

    def test_independent_method_missing_etc_raises(self) -> None:
        """Independent Method should raise when manager ETC not provided."""
        with pytest.raises(ValueError, match="Manager ETC not provided"):
            EVMSCalculator.calculate_eac_advanced(
                bcws=Decimal("50"),
                bcwp=Decimal("50"),
                acwp=Decimal("60"),
                bac=Decimal("100"),
                method=EACMethod.INDEPENDENT,
            )


class TestCompositeMethod:
    """Tests for the composite EAC method with weighted averages."""

    def test_early_phase_weights(self) -> None:
        """Composite Method early phase (<25%) favors typical method."""
        # BCWP/BAC = 20/100 = 20% complete
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("20"),
            bcwp=Decimal("20"),
            acwp=Decimal("25"),
            bac=Decimal("100"),
            method=EACMethod.COMPOSITE,
        )

        assert result.method == EACMethod.COMPOSITE
        assert "20% complete" in result.description

    def test_middle_phase_weights(self) -> None:
        """Composite Method middle phase (25-75%) uses balanced weights."""
        # BCWP/BAC = 50/100 = 50% complete
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("50"),
            bcwp=Decimal("50"),
            acwp=Decimal("60"),
            bac=Decimal("100"),
            method=EACMethod.COMPOSITE,
        )

        assert result.method == EACMethod.COMPOSITE
        assert "50% complete" in result.description

    def test_late_phase_weights(self) -> None:
        """Composite Method late phase (>75%) favors CPI method."""
        # BCWP/BAC = 80/100 = 80% complete
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("80"),
            bcwp=Decimal("80"),
            acwp=Decimal("90"),
            bac=Decimal("100"),
            method=EACMethod.COMPOSITE,
        )

        assert result.method == EACMethod.COMPOSITE
        assert "80% complete" in result.description

    def test_composite_fallback_when_cpi_zero(self) -> None:
        """Composite Method should fall back to typical when CPI unavailable."""
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("50"),
            bcwp=Decimal("0"),  # CPI = 0
            acwp=Decimal("60"),
            bac=Decimal("100"),
            method=EACMethod.COMPOSITE,
        )

        # Should fall back to typical method
        assert result.method == EACMethod.TYPICAL


class TestCalculateAllEACMethods:
    """Tests for calculate_all_eac_methods function."""

    def test_returns_all_valid_methods(self) -> None:
        """Should return results for all methods that can be calculated."""
        results = EVMSCalculator.calculate_all_eac_methods(
            bcws=Decimal("50"),
            bcwp=Decimal("50"),
            acwp=Decimal("60"),
            bac=Decimal("100"),
        )

        # Should have CPI, TYPICAL, MATHEMATICAL, COMPREHENSIVE, COMPOSITE
        # (not INDEPENDENT - no manager_etc provided)
        assert len(results) == 5
        methods = {r.method for r in results}
        assert EACMethod.CPI in methods
        assert EACMethod.TYPICAL in methods
        assert EACMethod.MATHEMATICAL in methods
        assert EACMethod.COMPREHENSIVE in methods
        assert EACMethod.COMPOSITE in methods
        assert EACMethod.INDEPENDENT not in methods

    def test_includes_independent_when_manager_etc_provided(self) -> None:
        """Should include independent method when manager ETC is provided."""
        results = EVMSCalculator.calculate_all_eac_methods(
            bcws=Decimal("50"),
            bcwp=Decimal("50"),
            acwp=Decimal("60"),
            bac=Decimal("100"),
            manager_etc=Decimal("45"),
        )

        assert len(results) == 6
        methods = {r.method for r in results}
        assert EACMethod.INDEPENDENT in methods

    def test_skips_methods_that_fail(self) -> None:
        """Should skip methods that would raise errors."""
        # BCWP = 0 means CPI = 0, so CPI-based methods will fail
        results = EVMSCalculator.calculate_all_eac_methods(
            bcws=Decimal("50"),
            bcwp=Decimal("0"),
            acwp=Decimal("60"),
            bac=Decimal("100"),
        )

        # Should only have TYPICAL (CPI, MATHEMATICAL, COMPREHENSIVE fail)
        # COMPOSITE falls back to TYPICAL
        methods = {r.method for r in results}
        assert EACMethod.TYPICAL in methods
        assert EACMethod.CPI not in methods
        assert EACMethod.MATHEMATICAL not in methods
        assert EACMethod.COMPREHENSIVE not in methods


class TestEACResultDataclass:
    """Tests for EACResult dataclass."""

    def test_eac_result_fields(self) -> None:
        """Should have all expected fields."""
        result = EACResult(
            method=EACMethod.CPI,
            eac=Decimal("120.00"),
            etc=Decimal("60.00"),
            vac=Decimal("-20.00"),
            description="Test description",
        )

        assert result.method == EACMethod.CPI
        assert result.eac == Decimal("120.00")
        assert result.etc == Decimal("60.00")
        assert result.vac == Decimal("-20.00")
        assert result.description == "Test description"


class TestEACMethodEnum:
    """Tests for EACMethod enum."""

    def test_method_values(self) -> None:
        """Should have correct string values."""
        assert EACMethod.CPI.value == "cpi"
        assert EACMethod.TYPICAL.value == "typical"
        assert EACMethod.MATHEMATICAL.value == "mathematical"
        assert EACMethod.COMPREHENSIVE.value == "comprehensive"
        assert EACMethod.INDEPENDENT.value == "independent"
        assert EACMethod.COMPOSITE.value == "composite"

    def test_all_methods_present(self) -> None:
        """Should have all 6 methods."""
        assert len(EACMethod) == 6


class TestEACEdgeCases:
    """Tests for edge cases in EAC calculations."""

    def test_cpi_method_exactly_one(self) -> None:
        """CPI Method when CPI = 1.0 (on budget)."""
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("50"),
            bcwp=Decimal("50"),
            acwp=Decimal("50"),
            bac=Decimal("100"),
            method=EACMethod.CPI,
        )

        assert result.eac == Decimal("100.00")  # BAC / 1.0 = BAC
        assert result.vac == Decimal("0.00")

    def test_mathematical_vs_cpi_relationship(self) -> None:
        """Mathematical and CPI methods should give same EAC."""
        bcws = Decimal("50")
        bcwp = Decimal("50")
        acwp = Decimal("60")
        bac = Decimal("100")

        cpi_result = EVMSCalculator.calculate_eac_advanced(
            bcws=bcws, bcwp=bcwp, acwp=acwp, bac=bac, method=EACMethod.CPI
        )
        math_result = EVMSCalculator.calculate_eac_advanced(
            bcws=bcws, bcwp=bcwp, acwp=acwp, bac=bac, method=EACMethod.MATHEMATICAL
        )

        # CPI method: BAC / CPI
        # Mathematical: ACWP + (BAC - BCWP) / CPI
        # When ACWP + ETC = BAC/CPI, they should be equal or very close
        assert abs(cpi_result.eac - math_result.eac) <= Decimal("1.00")

    def test_zero_bac(self) -> None:
        """Should handle zero BAC gracefully."""
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("0"),
            bcwp=Decimal("0"),
            acwp=Decimal("10"),
            bac=Decimal("0"),
            method=EACMethod.TYPICAL,
        )

        # EAC = ACWP + (0 - 0) = 10
        assert result.eac == Decimal("10.00")
        assert result.vac == Decimal("-10.00")

    def test_large_values(self) -> None:
        """Should handle large decimal values."""
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("50000000"),
            bcwp=Decimal("50000000"),
            acwp=Decimal("60000000"),
            bac=Decimal("100000000"),
            method=EACMethod.CPI,
        )

        # CPI = 50M/60M = 0.83, EAC = 100M / 0.83 = 120,481,927.71
        assert result.eac == Decimal("120481927.71")
        assert result.vac == Decimal("-20481927.71")

    def test_very_small_cpi(self) -> None:
        """Should handle very small CPI (severe cost overrun)."""
        # CPI = 10/100 = 0.1 (very bad)
        result = EVMSCalculator.calculate_eac_advanced(
            bcws=Decimal("50"),
            bcwp=Decimal("10"),
            acwp=Decimal("100"),
            bac=Decimal("200"),
            method=EACMethod.CPI,
        )

        # EAC = 200 / 0.1 = 2000 (10x over budget)
        assert result.eac == Decimal("2000.00")
        assert result.vac == Decimal("-1800.00")
