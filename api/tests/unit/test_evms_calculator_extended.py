"""Extended unit tests for EVMS Calculator service."""

from decimal import Decimal

from src.services.evms import EVMSCalculator


class TestEVMSCalculatorCostVariance:
    """Tests for cost variance calculations."""

    def test_calculate_cost_variance_positive(self):
        """Test positive cost variance (under budget)."""
        cv = EVMSCalculator.calculate_cost_variance(
            bcwp=Decimal("100000.00"),
            acwp=Decimal("90000.00"),
        )
        assert cv == Decimal("10000.00")

    def test_calculate_cost_variance_negative(self):
        """Test negative cost variance (over budget)."""
        cv = EVMSCalculator.calculate_cost_variance(
            bcwp=Decimal("100000.00"),
            acwp=Decimal("110000.00"),
        )
        assert cv == Decimal("-10000.00")

    def test_calculate_cost_variance_zero(self):
        """Test zero cost variance (on budget)."""
        cv = EVMSCalculator.calculate_cost_variance(
            bcwp=Decimal("100000.00"),
            acwp=Decimal("100000.00"),
        )
        assert cv == Decimal("0.00")


class TestEVMSCalculatorScheduleVariance:
    """Tests for schedule variance calculations."""

    def test_calculate_schedule_variance_positive(self):
        """Test positive schedule variance (ahead of schedule)."""
        sv = EVMSCalculator.calculate_schedule_variance(
            bcwp=Decimal("110000.00"),
            bcws=Decimal("100000.00"),
        )
        assert sv == Decimal("10000.00")

    def test_calculate_schedule_variance_negative(self):
        """Test negative schedule variance (behind schedule)."""
        sv = EVMSCalculator.calculate_schedule_variance(
            bcwp=Decimal("90000.00"),
            bcws=Decimal("100000.00"),
        )
        assert sv == Decimal("-10000.00")

    def test_calculate_schedule_variance_zero(self):
        """Test zero schedule variance (on schedule)."""
        sv = EVMSCalculator.calculate_schedule_variance(
            bcwp=Decimal("100000.00"),
            bcws=Decimal("100000.00"),
        )
        assert sv == Decimal("0.00")


class TestEVMSCalculatorCPI:
    """Tests for CPI calculations."""

    def test_calculate_cpi_good_performance(self):
        """Test CPI > 1 (good cost performance)."""
        cpi = EVMSCalculator.calculate_cpi(
            bcwp=Decimal("100000.00"),
            acwp=Decimal("90000.00"),
        )
        assert cpi == Decimal("1.11")

    def test_calculate_cpi_poor_performance(self):
        """Test CPI < 1 (poor cost performance)."""
        cpi = EVMSCalculator.calculate_cpi(
            bcwp=Decimal("90000.00"),
            acwp=Decimal("100000.00"),
        )
        assert cpi == Decimal("0.90")

    def test_calculate_cpi_exact(self):
        """Test CPI = 1 (on budget)."""
        cpi = EVMSCalculator.calculate_cpi(
            bcwp=Decimal("100000.00"),
            acwp=Decimal("100000.00"),
        )
        assert cpi == Decimal("1.00")

    def test_calculate_cpi_zero_acwp(self):
        """Test CPI returns None when ACWP is zero."""
        cpi = EVMSCalculator.calculate_cpi(
            bcwp=Decimal("100000.00"),
            acwp=Decimal("0.00"),
        )
        assert cpi is None


class TestEVMSCalculatorSPI:
    """Tests for SPI calculations."""

    def test_calculate_spi_good_performance(self):
        """Test SPI > 1 (ahead of schedule)."""
        spi = EVMSCalculator.calculate_spi(
            bcwp=Decimal("110000.00"),
            bcws=Decimal("100000.00"),
        )
        assert spi == Decimal("1.10")

    def test_calculate_spi_poor_performance(self):
        """Test SPI < 1 (behind schedule)."""
        spi = EVMSCalculator.calculate_spi(
            bcwp=Decimal("85000.00"),
            bcws=Decimal("100000.00"),
        )
        assert spi == Decimal("0.85")

    def test_calculate_spi_exact(self):
        """Test SPI = 1 (on schedule)."""
        spi = EVMSCalculator.calculate_spi(
            bcwp=Decimal("100000.00"),
            bcws=Decimal("100000.00"),
        )
        assert spi == Decimal("1.00")

    def test_calculate_spi_zero_bcws(self):
        """Test SPI returns None when BCWS is zero."""
        spi = EVMSCalculator.calculate_spi(
            bcwp=Decimal("100000.00"),
            bcws=Decimal("0.00"),
        )
        assert spi is None


class TestEVMSCalculatorEAC:
    """Tests for EAC calculations."""

    def test_calculate_eac_over_budget(self):
        """Test EAC when project is over budget."""
        eac = EVMSCalculator.calculate_eac(
            bac=Decimal("1000000.00"),
            acwp=Decimal("500000.00"),
            bcwp=Decimal("450000.00"),
        )
        assert eac is not None
        assert eac > Decimal("1000000.00")

    def test_calculate_eac_under_budget(self):
        """Test EAC when project is under budget."""
        eac = EVMSCalculator.calculate_eac(
            bac=Decimal("1000000.00"),
            acwp=Decimal("400000.00"),
            bcwp=Decimal("500000.00"),
        )
        assert eac is not None
        assert eac < Decimal("1000000.00")

    def test_calculate_eac_zero_bcwp(self):
        """Test EAC returns None when BCWP is zero."""
        eac = EVMSCalculator.calculate_eac(
            bac=Decimal("1000000.00"),
            acwp=Decimal("50000.00"),
            bcwp=Decimal("0.00"),
        )
        assert eac is None


class TestEVMSCalculatorETC:
    """Tests for ETC calculations."""

    def test_calculate_etc_typical(self):
        """Test ETC calculation."""
        etc = EVMSCalculator.calculate_etc(
            eac=Decimal("1100000.00"),
            acwp=Decimal("500000.00"),
        )
        assert etc == Decimal("600000.00")

    def test_calculate_etc_project_complete(self):
        """Test ETC when project is complete."""
        etc = EVMSCalculator.calculate_etc(
            eac=Decimal("1000000.00"),
            acwp=Decimal("1000000.00"),
        )
        assert etc == Decimal("0.00")


class TestEVMSCalculatorVAC:
    """Tests for VAC calculations."""

    def test_calculate_vac_positive(self):
        """Test positive VAC (under budget projection)."""
        vac = EVMSCalculator.calculate_vac(
            bac=Decimal("1000000.00"),
            eac=Decimal("900000.00"),
        )
        assert vac == Decimal("100000.00")

    def test_calculate_vac_negative(self):
        """Test negative VAC (over budget projection)."""
        vac = EVMSCalculator.calculate_vac(
            bac=Decimal("1000000.00"),
            eac=Decimal("1100000.00"),
        )
        assert vac == Decimal("-100000.00")

    def test_calculate_vac_zero(self):
        """Test zero VAC (on budget projection)."""
        vac = EVMSCalculator.calculate_vac(
            bac=Decimal("1000000.00"),
            eac=Decimal("1000000.00"),
        )
        assert vac == Decimal("0.00")


class TestEVMSCalculatorTCPI:
    """Tests for TCPI calculations."""

    def test_calculate_tcpi_achievable(self):
        """Test TCPI when BAC is achievable."""
        tcpi = EVMSCalculator.calculate_tcpi(
            bac=Decimal("1000000.00"),
            bcwp=Decimal("500000.00"),
            acwp=Decimal("450000.00"),
        )
        assert tcpi is not None
        assert tcpi < Decimal("1.00")

    def test_calculate_tcpi_difficult(self):
        """Test TCPI when BAC is difficult."""
        tcpi = EVMSCalculator.calculate_tcpi(
            bac=Decimal("1000000.00"),
            bcwp=Decimal("400000.00"),
            acwp=Decimal("600000.00"),
        )
        assert tcpi is not None
        assert tcpi > Decimal("1.00")

    def test_calculate_tcpi_no_budget_remaining(self):
        """Test TCPI when no budget remaining."""
        tcpi = EVMSCalculator.calculate_tcpi(
            bac=Decimal("1000000.00"),
            bcwp=Decimal("500000.00"),
            acwp=Decimal("1000000.00"),
        )
        assert tcpi is None


class TestEVMSCalculatorSmallValues:
    """Test EVMS calculations with small values."""

    def test_small_bcwp_bcws(self):
        """Test with very small values."""
        spi = EVMSCalculator.calculate_spi(
            bcwp=Decimal("0.01"),
            bcws=Decimal("0.01"),
        )
        assert spi == Decimal("1.00")

    def test_small_cost_values(self):
        """Test CV with small values."""
        cv = EVMSCalculator.calculate_cost_variance(
            bcwp=Decimal("100.50"),
            acwp=Decimal("99.25"),
        )
        assert cv == Decimal("1.25")


class TestEVMSCalculatorLargeValues:
    """Test EVMS calculations with large values."""

    def test_large_budget_values(self):
        """Test with large budget values."""
        cv = EVMSCalculator.calculate_cost_variance(
            bcwp=Decimal("999999999.99"),
            acwp=Decimal("888888888.88"),
        )
        assert cv == Decimal("111111111.11")

    def test_large_eac_calculation(self):
        """Test EAC with large values."""
        eac = EVMSCalculator.calculate_eac(
            bac=Decimal("10000000000.00"),
            acwp=Decimal("5000000000.00"),
            bcwp=Decimal("4500000000.00"),
        )
        assert eac is not None
