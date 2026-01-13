"""Additional EVMS tests for edge cases and coverage boost."""

import pytest
from decimal import Decimal

from src.services.evms import EVMSCalculator, EVMethod


class TestEVMSEdgeCases:
    """Edge case tests for EVMS calculations."""

    def test_zero_bcws_returns_none_spi(self):
        """SPI should be None when BCWS is zero."""
        spi = EVMSCalculator.calculate_spi(
            bcwp=Decimal("100"),
            bcws=Decimal("0"),
        )
        assert spi is None

    def test_zero_acwp_returns_none_cpi(self):
        """CPI should be None when ACWP is zero."""
        cpi = EVMSCalculator.calculate_cpi(
            bcwp=Decimal("100"),
            acwp=Decimal("0"),
        )
        assert cpi is None

    def test_negative_schedule_variance(self):
        """Test negative SV (behind schedule)."""
        sv = EVMSCalculator.calculate_schedule_variance(
            bcwp=Decimal("800"),
            bcws=Decimal("1000"),
        )
        assert sv == Decimal("-200")

    def test_negative_cost_variance(self):
        """Test negative CV (over budget)."""
        cv = EVMSCalculator.calculate_cost_variance(
            bcwp=Decimal("800"),
            acwp=Decimal("1200"),
        )
        assert cv == Decimal("-400")

    def test_spi_behind_schedule(self):
        """SPI < 1 means behind schedule."""
        spi = EVMSCalculator.calculate_spi(
            bcwp=Decimal("800"),
            bcws=Decimal("1000"),
        )
        assert spi == Decimal("0.80")
        assert spi < Decimal("1")

    def test_cpi_over_budget(self):
        """CPI < 1 means over budget."""
        cpi = EVMSCalculator.calculate_cpi(
            bcwp=Decimal("800"),
            acwp=Decimal("1000"),
        )
        assert cpi == Decimal("0.80")
        assert cpi < Decimal("1")

    def test_spi_ahead_schedule(self):
        """SPI > 1 means ahead of schedule."""
        spi = EVMSCalculator.calculate_spi(
            bcwp=Decimal("1200"),
            bcws=Decimal("1000"),
        )
        assert spi == Decimal("1.20")
        assert spi > Decimal("1")

    def test_cpi_under_budget(self):
        """CPI > 1 means under budget."""
        cpi = EVMSCalculator.calculate_cpi(
            bcwp=Decimal("1000"),
            acwp=Decimal("800"),
        )
        assert cpi == Decimal("1.25")
        assert cpi > Decimal("1")


class TestEVMSTCPI:
    """Tests for To-Complete Performance Index."""

    def test_tcpi_for_bac_target(self):
        """TCPI for completing at BAC."""
        tcpi = EVMSCalculator.calculate_tcpi(
            bac=Decimal("1000"),
            bcwp=Decimal("400"),
            acwp=Decimal("500"),
            target="bac",
        )
        # TCPI = (BAC - BCWP) / (BAC - ACWP) = (1000-400)/(1000-500) = 1.2
        assert tcpi == Decimal("1.20")

    def test_tcpi_when_remaining_budget_zero(self):
        """TCPI should be None when remaining budget is zero."""
        tcpi = EVMSCalculator.calculate_tcpi(
            bac=Decimal("1000"),
            bcwp=Decimal("500"),
            acwp=Decimal("1000"),  # Already spent BAC
            target="bac",
        )
        assert tcpi is None

    def test_tcpi_achievable(self):
        """TCPI close to 1 is achievable."""
        tcpi = EVMSCalculator.calculate_tcpi(
            bac=Decimal("1000"),
            bcwp=Decimal("500"),
            acwp=Decimal("500"),
            target="bac",
        )
        # TCPI = (1000-500)/(1000-500) = 1.0
        assert tcpi == Decimal("1.00")

    def test_tcpi_difficult(self):
        """TCPI > 1.2 is difficult to achieve."""
        tcpi = EVMSCalculator.calculate_tcpi(
            bac=Decimal("1000"),
            bcwp=Decimal("300"),
            acwp=Decimal("600"),
            target="bac",
        )
        # TCPI = (1000-300)/(1000-600) = 700/400 = 1.75
        assert tcpi == Decimal("1.75")
        assert tcpi > Decimal("1.2")

    def test_tcpi_for_eac_target(self):
        """TCPI for completing at EAC."""
        tcpi = EVMSCalculator.calculate_tcpi(
            bac=Decimal("1000"),
            bcwp=Decimal("400"),
            acwp=Decimal("500"),
            target="eac",
            eac=Decimal("1200"),
        )
        # TCPI = (BAC - BCWP) / (EAC - ACWP) = (1000-400)/(1200-500) = 600/700
        assert tcpi == Decimal("0.86")

    def test_tcpi_eac_target_without_eac_returns_none(self):
        """TCPI with EAC target but no EAC value returns None."""
        tcpi = EVMSCalculator.calculate_tcpi(
            bac=Decimal("1000"),
            bcwp=Decimal("400"),
            acwp=Decimal("500"),
            target="eac",
            eac=None,
        )
        assert tcpi is None


class TestEVMSEAC:
    """Tests for Estimate at Completion."""

    def test_eac_with_cpi_method(self):
        """EAC = BAC / CPI using CPI method."""
        eac = EVMSCalculator.calculate_eac(
            bac=Decimal("10000"),
            acwp=Decimal("5000"),
            bcwp=Decimal("4000"),  # CPI = 4000/5000 = 0.80
            method="cpi",
        )
        # EAC = 10000 / 0.80 = 12500
        assert eac == Decimal("12500.00")

    def test_eac_under_budget(self):
        """EAC less than BAC when CPI > 1."""
        eac = EVMSCalculator.calculate_eac(
            bac=Decimal("10000"),
            acwp=Decimal("4000"),
            bcwp=Decimal("5000"),  # CPI = 5000/4000 = 1.25
            method="cpi",
        )
        # EAC = 10000 / 1.25 = 8000
        assert eac == Decimal("8000.00")
        assert eac < Decimal("10000")

    def test_eac_typical_method(self):
        """EAC = ACWP + (BAC - BCWP) using typical method."""
        eac = EVMSCalculator.calculate_eac(
            bac=Decimal("10000"),
            acwp=Decimal("5000"),
            bcwp=Decimal("4000"),
            method="typical",
        )
        # EAC = 5000 + (10000 - 4000) = 5000 + 6000 = 11000
        assert eac == Decimal("11000.00")

    def test_eac_zero_cpi_returns_none(self):
        """EAC returns None when CPI would be zero."""
        eac = EVMSCalculator.calculate_eac(
            bac=Decimal("10000"),
            acwp=Decimal("0"),
            bcwp=Decimal("0"),
            method="cpi",
        )
        assert eac is None

    def test_etc_calculation(self):
        """ETC = EAC - ACWP."""
        etc = EVMSCalculator.calculate_etc(
            eac=Decimal("12500"),
            acwp=Decimal("5000"),
        )
        assert etc == Decimal("7500")

    def test_vac_calculation(self):
        """VAC = BAC - EAC."""
        vac = EVMSCalculator.calculate_vac(
            bac=Decimal("10000"),
            eac=Decimal("12500"),
        )
        assert vac == Decimal("-2500")  # Will exceed budget by 2500


class TestEVMethods:
    """Tests for different EV calculation methods."""

    def test_ev_0_100_not_started(self):
        """0/100 method: 0% if not complete."""
        ev = EVMSCalculator.calculate_earned_value(
            budgeted_cost=Decimal("1000"),
            percent_complete=Decimal("50"),
            method=EVMethod.ZERO_HUNDRED,
        )
        assert ev == Decimal("0")

    def test_ev_0_100_complete(self):
        """0/100 method: 100% if complete."""
        ev = EVMSCalculator.calculate_earned_value(
            budgeted_cost=Decimal("1000"),
            percent_complete=Decimal("100"),
            method=EVMethod.ZERO_HUNDRED,
        )
        assert ev == Decimal("1000")

    def test_ev_50_50_started(self):
        """50/50 method: 50% when started."""
        ev = EVMSCalculator.calculate_earned_value(
            budgeted_cost=Decimal("1000"),
            percent_complete=Decimal("10"),
            method=EVMethod.FIFTY_FIFTY,
        )
        assert ev == Decimal("500")

    def test_ev_50_50_complete(self):
        """50/50 method: 100% when complete."""
        ev = EVMSCalculator.calculate_earned_value(
            budgeted_cost=Decimal("1000"),
            percent_complete=Decimal("100"),
            method=EVMethod.FIFTY_FIFTY,
        )
        assert ev == Decimal("1000")

    def test_ev_50_50_not_started(self):
        """50/50 method: 0% when not started."""
        ev = EVMSCalculator.calculate_earned_value(
            budgeted_cost=Decimal("1000"),
            percent_complete=Decimal("0"),
            method=EVMethod.FIFTY_FIFTY,
        )
        assert ev == Decimal("0")

    def test_ev_percent_complete(self):
        """Percent complete method."""
        ev = EVMSCalculator.calculate_earned_value(
            budgeted_cost=Decimal("1000"),
            percent_complete=Decimal("75"),
            method=EVMethod.PERCENT_COMPLETE,
        )
        assert ev == Decimal("750")

    def test_ev_milestone_not_achieved(self):
        """Milestone method: 0 when not achieved."""
        ev = EVMSCalculator.calculate_earned_value(
            budgeted_cost=Decimal("1000"),
            percent_complete=Decimal("50"),
            method=EVMethod.MILESTONE,
            milestone_achieved=False,
        )
        assert ev == Decimal("0")

    def test_ev_milestone_achieved(self):
        """Milestone method: 100% when achieved."""
        ev = EVMSCalculator.calculate_earned_value(
            budgeted_cost=Decimal("1000"),
            percent_complete=Decimal("50"),
            method=EVMethod.MILESTONE,
            milestone_achieved=True,
        )
        assert ev == Decimal("1000")


class TestEVMSAllMetrics:
    """Tests for complete metrics calculation."""

    def test_all_metrics_healthy_project(self):
        """Calculate all metrics for on-track project."""
        metrics = EVMSCalculator.calculate_all_metrics(
            bcws=Decimal("1000"),
            bcwp=Decimal("1000"),
            acwp=Decimal("1000"),
            bac=Decimal("5000"),
        )
        assert metrics.schedule_variance == Decimal("0")
        assert metrics.cost_variance == Decimal("0")
        assert metrics.schedule_performance_index == Decimal("1.00")
        assert metrics.cost_performance_index == Decimal("1.00")

    def test_all_metrics_troubled_project(self):
        """Calculate all metrics for troubled project."""
        metrics = EVMSCalculator.calculate_all_metrics(
            bcws=Decimal("1000"),
            bcwp=Decimal("800"),   # Behind schedule
            acwp=Decimal("1200"),  # Over budget
            bac=Decimal("5000"),
        )
        assert metrics.schedule_variance == Decimal("-200")
        assert metrics.cost_variance == Decimal("-400")
        assert metrics.schedule_performance_index < Decimal("1")
        assert metrics.cost_performance_index < Decimal("1")

    def test_all_metrics_ahead_under(self):
        """Calculate all metrics for ahead/under budget project."""
        metrics = EVMSCalculator.calculate_all_metrics(
            bcws=Decimal("1000"),
            bcwp=Decimal("1200"),  # Ahead of schedule
            acwp=Decimal("900"),   # Under budget
            bac=Decimal("5000"),
        )
        assert metrics.schedule_variance == Decimal("200")
        assert metrics.cost_variance == Decimal("300")
        assert metrics.schedule_performance_index > Decimal("1")
        assert metrics.cost_performance_index > Decimal("1")

    def test_all_metrics_includes_estimates(self):
        """All metrics should include EAC, ETC, VAC, TCPI."""
        metrics = EVMSCalculator.calculate_all_metrics(
            bcws=Decimal("1000"),
            bcwp=Decimal("800"),
            acwp=Decimal("1000"),
            bac=Decimal("5000"),
        )
        assert metrics.budget_at_completion == Decimal("5000")
        assert metrics.estimate_at_completion is not None
        assert metrics.estimate_to_complete is not None
        assert metrics.variance_at_completion is not None
        assert metrics.to_complete_performance_index is not None
