"""Earned Value Management System (EVMS) calculations."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum


class EVMethod(str, Enum):
    """Earned Value measurement methods."""

    ZERO_HUNDRED = "0/100"  # 0% at start, 100% at completion
    FIFTY_FIFTY = "50/50"  # 50% at start, 50% at completion
    PERCENT_COMPLETE = "percent_complete"  # Based on actual % complete
    MILESTONE = "milestone"  # Based on milestone achievement


@dataclass
class EVMSMetrics:
    """Container for EVMS metrics."""

    # Core values
    bcws: Decimal  # Budgeted Cost of Work Scheduled (Planned Value)
    bcwp: Decimal  # Budgeted Cost of Work Performed (Earned Value)
    acwp: Decimal  # Actual Cost of Work Performed

    # Variances
    cost_variance: Decimal | None = None  # CV = BCWP - ACWP
    schedule_variance: Decimal | None = None  # SV = BCWP - BCWS

    # Performance indices
    cost_performance_index: Decimal | None = None  # CPI = BCWP / ACWP
    schedule_performance_index: Decimal | None = None  # SPI = BCWP / BCWS

    # Estimates
    budget_at_completion: Decimal | None = None  # BAC
    estimate_at_completion: Decimal | None = None  # EAC
    estimate_to_complete: Decimal | None = None  # ETC
    variance_at_completion: Decimal | None = None  # VAC = BAC - EAC
    to_complete_performance_index: Decimal | None = None  # TCPI


class EVMSCalculator:
    """
    Calculator for Earned Value Management System metrics.

    All calculations use Decimal for financial accuracy and handle
    division by zero gracefully by returning None.
    """

    PRECISION = Decimal("0.01")

    @classmethod
    def _round(cls, value: Decimal) -> Decimal:
        """Round a decimal value to 2 decimal places."""
        return value.quantize(cls.PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_earned_value(
        cls,
        budgeted_cost: Decimal,
        percent_complete: Decimal,
        method: EVMethod = EVMethod.PERCENT_COMPLETE,
        milestone_achieved: bool = False,
    ) -> Decimal:
        """
        Calculate earned value (BCWP) for an activity.

        Args:
            budgeted_cost: The budgeted cost for the activity
            percent_complete: Completion percentage (0-100)
            method: EV measurement method
            milestone_achieved: Whether milestone is achieved (for milestone method)

        Returns:
            Earned value (BCWP) for the activity
        """
        match method:
            case EVMethod.ZERO_HUNDRED:
                return budgeted_cost if percent_complete == 100 else Decimal("0")

            case EVMethod.FIFTY_FIFTY:
                if percent_complete == 100:
                    return budgeted_cost
                elif percent_complete > 0:
                    return cls._round(budgeted_cost * Decimal("0.5"))
                return Decimal("0")

            case EVMethod.MILESTONE:
                return budgeted_cost if milestone_achieved else Decimal("0")

            case EVMethod.PERCENT_COMPLETE | _:
                return cls._round(budgeted_cost * percent_complete / 100)

    @classmethod
    def calculate_cost_variance(cls, bcwp: Decimal, acwp: Decimal) -> Decimal:
        """
        Calculate Cost Variance (CV = BCWP - ACWP).

        Positive CV indicates under budget.
        Negative CV indicates over budget.
        """
        return cls._round(bcwp - acwp)

    @classmethod
    def calculate_schedule_variance(cls, bcwp: Decimal, bcws: Decimal) -> Decimal:
        """
        Calculate Schedule Variance (SV = BCWP - BCWS).

        Positive SV indicates ahead of schedule.
        Negative SV indicates behind schedule.
        """
        return cls._round(bcwp - bcws)

    @classmethod
    def calculate_cpi(cls, bcwp: Decimal, acwp: Decimal) -> Decimal | None:
        """
        Calculate Cost Performance Index (CPI = BCWP / ACWP).

        CPI > 1.0 indicates under budget.
        CPI < 1.0 indicates over budget.

        Returns None if ACWP is zero.
        """
        if acwp == 0:
            return None
        return cls._round(bcwp / acwp)

    @classmethod
    def calculate_spi(cls, bcwp: Decimal, bcws: Decimal) -> Decimal | None:
        """
        Calculate Schedule Performance Index (SPI = BCWP / BCWS).

        SPI > 1.0 indicates ahead of schedule.
        SPI < 1.0 indicates behind schedule.

        Returns None if BCWS is zero.
        """
        if bcws == 0:
            return None
        return cls._round(bcwp / bcws)

    @classmethod
    def calculate_eac(
        cls,
        bac: Decimal,
        acwp: Decimal,
        bcwp: Decimal,
        method: str = "cpi",
    ) -> Decimal | None:
        """
        Calculate Estimate at Completion (EAC).

        Methods:
        - "cpi": EAC = BAC / CPI (assumes current cost performance continues)
        - "typical": EAC = ACWP + (BAC - BCWP) (assumes original estimates)
        - "atypical": EAC = ACWP + new_etc (requires new estimate)

        Returns None if calculation is not possible.
        """
        match method:
            case "cpi":
                cpi = cls.calculate_cpi(bcwp, acwp)
                if cpi is None or cpi == 0:
                    return None
                return cls._round(bac / cpi)

            case "typical":
                return cls._round(acwp + (bac - bcwp))

            case _:
                return None

    @classmethod
    def calculate_etc(cls, eac: Decimal, acwp: Decimal) -> Decimal:
        """
        Calculate Estimate to Complete (ETC = EAC - ACWP).

        The remaining cost to complete the project.
        """
        return cls._round(eac - acwp)

    @classmethod
    def calculate_vac(cls, bac: Decimal, eac: Decimal) -> Decimal:
        """
        Calculate Variance at Completion (VAC = BAC - EAC).

        Positive VAC indicates expected under budget.
        Negative VAC indicates expected over budget.
        """
        return cls._round(bac - eac)

    @classmethod
    def calculate_tcpi(
        cls,
        bac: Decimal,
        bcwp: Decimal,
        acwp: Decimal,
        target: str = "bac",
        eac: Decimal | None = None,
    ) -> Decimal | None:
        """
        Calculate To-Complete Performance Index.

        TCPI = (BAC - BCWP) / (BAC - ACWP) for BAC target
        TCPI = (BAC - BCWP) / (EAC - ACWP) for EAC target

        TCPI > 1.0 indicates harder performance required.
        TCPI < 1.0 indicates easier performance acceptable.

        Returns None if denominator is zero.
        """
        remaining_work = bac - bcwp

        match target:
            case "bac":
                remaining_budget = bac - acwp
            case "eac":
                if eac is None:
                    return None
                remaining_budget = eac - acwp
            case _:
                return None

        if remaining_budget == 0:
            return None

        return cls._round(remaining_work / remaining_budget)

    @classmethod
    def calculate_all_metrics(
        cls,
        bcws: Decimal,
        bcwp: Decimal,
        acwp: Decimal,
        bac: Decimal,
    ) -> EVMSMetrics:
        """
        Calculate all EVMS metrics for a given set of values.

        Args:
            bcws: Budgeted Cost of Work Scheduled (Planned Value)
            bcwp: Budgeted Cost of Work Performed (Earned Value)
            acwp: Actual Cost of Work Performed
            bac: Budget at Completion

        Returns:
            EVMSMetrics dataclass with all calculated values
        """
        cv = cls.calculate_cost_variance(bcwp, acwp)
        sv = cls.calculate_schedule_variance(bcwp, bcws)
        cpi = cls.calculate_cpi(bcwp, acwp)
        spi = cls.calculate_spi(bcwp, bcws)
        eac = cls.calculate_eac(bac, acwp, bcwp, "cpi")

        etc = cls.calculate_etc(eac, acwp) if eac else None
        vac = cls.calculate_vac(bac, eac) if eac else None
        tcpi = cls.calculate_tcpi(bac, bcwp, acwp, "bac")

        return EVMSMetrics(
            bcws=bcws,
            bcwp=bcwp,
            acwp=acwp,
            cost_variance=cv,
            schedule_variance=sv,
            cost_performance_index=cpi,
            schedule_performance_index=spi,
            budget_at_completion=bac,
            estimate_at_completion=eac,
            estimate_to_complete=etc,
            variance_at_completion=vac,
            to_complete_performance_index=tcpi,
        )
