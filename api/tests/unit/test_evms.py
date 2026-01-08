"""Unit tests for EVMS calculator."""

from decimal import Decimal

import pytest

from src.services.evms import EVMethod, EVMSCalculator


class TestEarnedValueCalculation:
    """Tests for earned value (BCWP) calculation."""

    def test_percent_complete_method(self):
        """Percent complete method should multiply budget by %."""
        # Arrange
        budgeted_cost = Decimal("10000.00")
        percent_complete = Decimal("50")

        # Act
        ev = EVMSCalculator.calculate_earned_value(
            budgeted_cost,
            percent_complete,
            EVMethod.PERCENT_COMPLETE,
        )

        # Assert
        assert ev == Decimal("5000.00")

    def test_zero_hundred_method_incomplete(self):
        """0/100 method should return 0 when not complete."""
        # Arrange
        budgeted_cost = Decimal("10000.00")
        percent_complete = Decimal("99")

        # Act
        ev = EVMSCalculator.calculate_earned_value(
            budgeted_cost,
            percent_complete,
            EVMethod.ZERO_HUNDRED,
        )

        # Assert
        assert ev == Decimal("0")

    def test_zero_hundred_method_complete(self):
        """0/100 method should return full budget when complete."""
        # Arrange
        budgeted_cost = Decimal("10000.00")
        percent_complete = Decimal("100")

        # Act
        ev = EVMSCalculator.calculate_earned_value(
            budgeted_cost,
            percent_complete,
            EVMethod.ZERO_HUNDRED,
        )

        # Assert
        assert ev == Decimal("10000.00")

    def test_fifty_fifty_method_started(self):
        """50/50 method should return 50% when started."""
        # Arrange
        budgeted_cost = Decimal("10000.00")
        percent_complete = Decimal("10")

        # Act
        ev = EVMSCalculator.calculate_earned_value(
            budgeted_cost,
            percent_complete,
            EVMethod.FIFTY_FIFTY,
        )

        # Assert
        assert ev == Decimal("5000.00")

    def test_fifty_fifty_method_complete(self):
        """50/50 method should return full budget when complete."""
        # Arrange
        budgeted_cost = Decimal("10000.00")
        percent_complete = Decimal("100")

        # Act
        ev = EVMSCalculator.calculate_earned_value(
            budgeted_cost,
            percent_complete,
            EVMethod.FIFTY_FIFTY,
        )

        # Assert
        assert ev == Decimal("10000.00")


class TestVarianceCalculation:
    """Tests for variance calculations."""

    def test_positive_cost_variance(self):
        """Under budget should give positive CV."""
        # Arrange
        bcwp = Decimal("10000.00")
        acwp = Decimal("8000.00")

        # Act
        cv = EVMSCalculator.calculate_cost_variance(bcwp, acwp)

        # Assert
        assert cv == Decimal("2000.00")

    def test_negative_cost_variance(self):
        """Over budget should give negative CV."""
        # Arrange
        bcwp = Decimal("10000.00")
        acwp = Decimal("12000.00")

        # Act
        cv = EVMSCalculator.calculate_cost_variance(bcwp, acwp)

        # Assert
        assert cv == Decimal("-2000.00")

    def test_positive_schedule_variance(self):
        """Ahead of schedule should give positive SV."""
        # Arrange
        bcwp = Decimal("10000.00")
        bcws = Decimal("8000.00")

        # Act
        sv = EVMSCalculator.calculate_schedule_variance(bcwp, bcws)

        # Assert
        assert sv == Decimal("2000.00")

    def test_negative_schedule_variance(self):
        """Behind schedule should give negative SV."""
        # Arrange
        bcwp = Decimal("8000.00")
        bcws = Decimal("10000.00")

        # Act
        sv = EVMSCalculator.calculate_schedule_variance(bcwp, bcws)

        # Assert
        assert sv == Decimal("-2000.00")


class TestPerformanceIndices:
    """Tests for performance index calculations."""

    def test_cpi_under_budget(self):
        """Under budget should give CPI > 1."""
        # Arrange
        bcwp = Decimal("10000.00")
        acwp = Decimal("8000.00")

        # Act
        cpi = EVMSCalculator.calculate_cpi(bcwp, acwp)

        # Assert
        assert cpi == Decimal("1.25")

    def test_cpi_over_budget(self):
        """Over budget should give CPI < 1."""
        # Arrange
        bcwp = Decimal("8000.00")
        acwp = Decimal("10000.00")

        # Act
        cpi = EVMSCalculator.calculate_cpi(bcwp, acwp)

        # Assert
        assert cpi == Decimal("0.80")

    def test_cpi_zero_acwp(self):
        """CPI should return None when ACWP is zero."""
        # Arrange
        bcwp = Decimal("10000.00")
        acwp = Decimal("0")

        # Act
        cpi = EVMSCalculator.calculate_cpi(bcwp, acwp)

        # Assert
        assert cpi is None

    def test_spi_ahead_schedule(self):
        """Ahead of schedule should give SPI > 1."""
        # Arrange
        bcwp = Decimal("10000.00")
        bcws = Decimal("8000.00")

        # Act
        spi = EVMSCalculator.calculate_spi(bcwp, bcws)

        # Assert
        assert spi == Decimal("1.25")

    def test_spi_behind_schedule(self):
        """Behind schedule should give SPI < 1."""
        # Arrange
        bcwp = Decimal("8000.00")
        bcws = Decimal("10000.00")

        # Act
        spi = EVMSCalculator.calculate_spi(bcwp, bcws)

        # Assert
        assert spi == Decimal("0.80")

    def test_spi_zero_bcws(self):
        """SPI should return None when BCWS is zero."""
        # Arrange
        bcwp = Decimal("10000.00")
        bcws = Decimal("0")

        # Act
        spi = EVMSCalculator.calculate_spi(bcwp, bcws)

        # Assert
        assert spi is None


class TestEstimates:
    """Tests for EAC, ETC, VAC calculations."""

    def test_eac_cpi_method(self):
        """EAC using CPI method should be BAC / CPI."""
        # Arrange
        bac = Decimal("100000.00")
        acwp = Decimal("40000.00")
        bcwp = Decimal("50000.00")  # CPI = 1.25

        # Act
        eac = EVMSCalculator.calculate_eac(bac, acwp, bcwp, "cpi")

        # Assert - EAC = 100000 / 1.25 = 80000
        assert eac == Decimal("80000.00")

    def test_eac_typical_method(self):
        """EAC using typical method should be ACWP + (BAC - BCWP)."""
        # Arrange
        bac = Decimal("100000.00")
        acwp = Decimal("40000.00")
        bcwp = Decimal("50000.00")

        # Act
        eac = EVMSCalculator.calculate_eac(bac, acwp, bcwp, "typical")

        # Assert - EAC = 40000 + (100000 - 50000) = 90000
        assert eac == Decimal("90000.00")

    def test_etc_calculation(self):
        """ETC should be EAC - ACWP."""
        # Arrange
        eac = Decimal("90000.00")
        acwp = Decimal("40000.00")

        # Act
        etc = EVMSCalculator.calculate_etc(eac, acwp)

        # Assert
        assert etc == Decimal("50000.00")

    def test_vac_calculation(self):
        """VAC should be BAC - EAC."""
        # Arrange
        bac = Decimal("100000.00")
        eac = Decimal("90000.00")

        # Act
        vac = EVMSCalculator.calculate_vac(bac, eac)

        # Assert - Positive VAC indicates expected under budget
        assert vac == Decimal("10000.00")


class TestTCPI:
    """Tests for To-Complete Performance Index calculation."""

    def test_tcpi_bac_target(self):
        """TCPI for BAC target."""
        # Arrange
        bac = Decimal("100000.00")
        bcwp = Decimal("50000.00")
        acwp = Decimal("40000.00")

        # Act
        tcpi = EVMSCalculator.calculate_tcpi(bac, bcwp, acwp, "bac")

        # Assert - TCPI = (100000-50000) / (100000-40000) = 50000/60000 = 0.83
        assert tcpi == Decimal("0.83")

    def test_tcpi_eac_target(self):
        """TCPI for EAC target."""
        # Arrange
        bac = Decimal("100000.00")
        bcwp = Decimal("50000.00")
        acwp = Decimal("40000.00")
        eac = Decimal("90000.00")

        # Act
        tcpi = EVMSCalculator.calculate_tcpi(bac, bcwp, acwp, "eac", eac)

        # Assert - TCPI = (100000-50000) / (90000-40000) = 50000/50000 = 1.0
        assert tcpi == Decimal("1.00")


class TestCalculateAllMetrics:
    """Tests for calculating all EVMS metrics at once."""

    def test_calculate_all_metrics(self):
        """Should calculate all EVMS metrics correctly."""
        # Arrange
        bcws = Decimal("50000.00")
        bcwp = Decimal("45000.00")
        acwp = Decimal("40000.00")
        bac = Decimal("100000.00")

        # Act
        metrics = EVMSCalculator.calculate_all_metrics(bcws, bcwp, acwp, bac)

        # Assert
        assert metrics.bcws == bcws
        assert metrics.bcwp == bcwp
        assert metrics.acwp == acwp
        assert metrics.cost_variance == Decimal("5000.00")  # 45000 - 40000
        assert metrics.schedule_variance == Decimal("-5000.00")  # 45000 - 50000
        assert metrics.cost_performance_index == Decimal("1.13")  # 45000 / 40000
        assert metrics.schedule_performance_index == Decimal("0.90")  # 45000 / 50000
        assert metrics.budget_at_completion == bac
