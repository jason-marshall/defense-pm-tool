"""Earned Value Management System (EVMS) calculations.

Enhanced EVMS Calculator with advanced EAC methods per GL 27:
- CPI Method: Assumes historical cost efficiency continues
- Typical: Assumes remaining work at budgeted rate
- Mathematical: Uses CPI for remaining work
- Comprehensive: Factors in both CPI and SPI
- Independent: Uses bottom-up estimate from PM
- Composite: Weighted average based on program phase
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum


class EVMethod(str, Enum):
    """Earned Value measurement methods."""

    ZERO_HUNDRED = "0/100"  # 0% at start, 100% at completion
    FIFTY_FIFTY = "50/50"  # 50% at start, 50% at completion
    PERCENT_COMPLETE = "percent_complete"  # Based on actual % complete
    MILESTONE = "milestone"  # Based on milestone achievement


class EACMethod(str, Enum):
    """EAC calculation methods per GL 27."""

    CPI = "cpi"  # BAC / CPI
    TYPICAL = "typical"  # ACWP + (BAC - BCWP)
    MATHEMATICAL = "mathematical"  # ACWP + (BAC - BCWP) / CPI
    COMPREHENSIVE = "comprehensive"  # ACWP + (BAC - BCWP) / (CPI * SPI)
    INDEPENDENT = "independent"  # ACWP + Manager ETC
    COMPOSITE = "composite"  # Weighted average of methods


@dataclass
class EACResult:
    """Result of EAC calculation."""

    method: EACMethod
    eac: Decimal
    etc: Decimal
    vac: Decimal
    description: str


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

    @classmethod
    def calculate_eac_advanced(
        cls,
        bcws: Decimal,
        bcwp: Decimal,
        acwp: Decimal,
        bac: Decimal,
        method: EACMethod = EACMethod.CPI,
        manager_etc: Decimal | None = None,
    ) -> EACResult:
        """
        Calculate EAC using the specified advanced method.

        Args:
            bcws: Budgeted Cost of Work Scheduled
            bcwp: Budgeted Cost of Work Performed
            acwp: Actual Cost of Work Performed
            bac: Budget at Completion
            method: EAC calculation method
            manager_etc: Manager's bottom-up ETC estimate (for independent method)

        Returns:
            EACResult with EAC, ETC, VAC, and description

        Raises:
            ZeroDivisionError: If required indices are zero
            ValueError: If required parameters are missing
        """
        # Pre-calculate indices
        cpi = cls.calculate_cpi(bcwp, acwp)
        spi = cls.calculate_spi(bcwp, bcws)

        match method:
            case EACMethod.CPI:
                return cls._eac_cpi_method(acwp, bac, cpi)

            case EACMethod.TYPICAL:
                return cls._eac_typical_method(acwp, bcwp, bac)

            case EACMethod.MATHEMATICAL:
                return cls._eac_mathematical_method(acwp, bcwp, bac, cpi)

            case EACMethod.COMPREHENSIVE:
                return cls._eac_comprehensive_method(acwp, bcwp, bac, cpi, spi)

            case EACMethod.INDEPENDENT:
                return cls._eac_independent_method(acwp, bac, manager_etc)

            case EACMethod.COMPOSITE:
                return cls._eac_composite_method(bcws, bcwp, acwp, bac, cpi, spi)

            case _:
                raise ValueError(f"Unknown EAC method: {method}")

    @classmethod
    def _eac_cpi_method(cls, acwp: Decimal, bac: Decimal, cpi: Decimal | None) -> EACResult:
        """
        CPI Method: EAC = BAC / CPI

        Assumes historical cost efficiency will continue for remaining work.
        Best when: Variances are typical and expected to continue.
        """
        if cpi is None or cpi == 0:
            raise ZeroDivisionError("CPI is zero or undefined")

        eac = cls._round(bac / cpi)
        etc = cls._round(eac - acwp)
        vac = cls._round(bac - eac)

        return EACResult(
            method=EACMethod.CPI,
            eac=eac,
            etc=etc,
            vac=vac,
            description="Assumes historical cost efficiency continues",
        )

    @classmethod
    def _eac_typical_method(cls, acwp: Decimal, bcwp: Decimal, bac: Decimal) -> EACResult:
        """
        Typical Method: EAC = ACWP + (BAC - BCWP)

        Assumes remaining work will be performed at budgeted rate.
        Best when: Current variances are atypical and won't continue.
        """
        remaining_work = bac - bcwp
        eac = cls._round(acwp + remaining_work)
        etc = cls._round(remaining_work)
        vac = cls._round(bac - eac)

        return EACResult(
            method=EACMethod.TYPICAL,
            eac=eac,
            etc=etc,
            vac=vac,
            description="Assumes remaining work at budgeted rate",
        )

    @classmethod
    def _eac_mathematical_method(
        cls, acwp: Decimal, bcwp: Decimal, bac: Decimal, cpi: Decimal | None
    ) -> EACResult:
        """
        Mathematical Method: EAC = ACWP + (BAC - BCWP) / CPI

        Uses CPI to estimate remaining work cost.
        Best when: Cost efficiency issues expected to continue.
        """
        if cpi is None or cpi == 0:
            raise ZeroDivisionError("CPI is zero or undefined")

        remaining_work = bac - bcwp
        etc = cls._round(remaining_work / cpi)
        eac = cls._round(acwp + etc)
        vac = cls._round(bac - eac)

        return EACResult(
            method=EACMethod.MATHEMATICAL,
            eac=eac,
            etc=etc,
            vac=vac,
            description="Remaining work adjusted by CPI",
        )

    @classmethod
    def _eac_comprehensive_method(
        cls,
        acwp: Decimal,
        bcwp: Decimal,
        bac: Decimal,
        cpi: Decimal | None,
        spi: Decimal | None,
    ) -> EACResult:
        """
        Comprehensive Method: EAC = ACWP + (BAC - BCWP) / (CPI x SPI).

        Factors in both cost and schedule performance.
        Best when: Both cost and schedule issues are ongoing.
        """
        if cpi is None or cpi == 0:
            raise ZeroDivisionError("CPI is zero or undefined")
        if spi is None or spi == 0:
            raise ZeroDivisionError("SPI is zero or undefined")

        efficiency_factor = cpi * spi
        remaining_work = bac - bcwp
        etc = cls._round(remaining_work / efficiency_factor)
        eac = cls._round(acwp + etc)
        vac = cls._round(bac - eac)

        return EACResult(
            method=EACMethod.COMPREHENSIVE,
            eac=eac,
            etc=etc,
            vac=vac,
            description="Remaining work adjusted by CPI x SPI",
        )

    @classmethod
    def _eac_independent_method(
        cls, acwp: Decimal, bac: Decimal, manager_etc: Decimal | None
    ) -> EACResult:
        """
        Independent ETC Method: EAC = ACWP + Manager ETC

        Uses bottom-up estimate from program manager.
        Best when: Significant re-planning has occurred.
        """
        if manager_etc is None:
            raise ValueError("Manager ETC not provided")

        etc = manager_etc
        eac = cls._round(acwp + etc)
        vac = cls._round(bac - eac)

        return EACResult(
            method=EACMethod.INDEPENDENT,
            eac=eac,
            etc=etc,
            vac=vac,
            description="Based on manager's bottom-up estimate",
        )

    @classmethod
    def _eac_composite_method(
        cls,
        _bcws: Decimal,
        bcwp: Decimal,
        acwp: Decimal,
        bac: Decimal,
        cpi: Decimal | None,
        _spi: Decimal | None,
    ) -> EACResult:
        """
        Composite Method: Weighted average of methods.

        Weights based on program completion percentage:
        - Early (<25%): Higher weight on typical/mathematical
        - Middle (25-75%): Balanced
        - Late (>75%): Higher weight on CPI-based methods
        """
        # Calculate percent complete
        percent_complete = Decimal("0") if bac == 0 else bcwp / bac
        pct = float(percent_complete)

        # Calculate component EACs
        try:
            if cpi is None or cpi == 0:
                # Fall back to typical if CPI unavailable
                return cls._eac_typical_method(acwp, bcwp, bac)

            eac_cpi = cls._round(bac / cpi)
            eac_typical = cls._round(acwp + (bac - bcwp))
            eac_math = cls._round(acwp + (bac - bcwp) / cpi)
        except (ZeroDivisionError, TypeError):
            return cls._eac_typical_method(acwp, bcwp, bac)

        # Apply weights based on completion
        if pct < 0.25:
            # Early: more weight on typical
            weights = {"cpi": Decimal("0.2"), "typical": Decimal("0.5"), "math": Decimal("0.3")}
        elif pct < 0.75:
            # Middle: balanced
            weights = {"cpi": Decimal("0.35"), "typical": Decimal("0.3"), "math": Decimal("0.35")}
        else:
            # Late: more weight on CPI
            weights = {"cpi": Decimal("0.5"), "typical": Decimal("0.2"), "math": Decimal("0.3")}

        eac = cls._round(
            weights["cpi"] * eac_cpi + weights["typical"] * eac_typical + weights["math"] * eac_math
        )
        etc = cls._round(eac - acwp)
        vac = cls._round(bac - eac)

        return EACResult(
            method=EACMethod.COMPOSITE,
            eac=eac,
            etc=etc,
            vac=vac,
            description=f"Weighted average ({int(pct * 100)}% complete)",
        )

    @classmethod
    def calculate_all_eac_methods(
        cls,
        bcws: Decimal,
        bcwp: Decimal,
        acwp: Decimal,
        bac: Decimal,
        manager_etc: Decimal | None = None,
    ) -> list[EACResult]:
        """
        Calculate EAC using all applicable methods.

        Returns list of EACResult for each method that can be calculated.
        Skips methods that would raise errors (e.g., zero CPI).
        """
        results = []

        for method in EACMethod:
            try:
                if method == EACMethod.INDEPENDENT and manager_etc is None:
                    continue

                result = cls.calculate_eac_advanced(
                    bcws=bcws,
                    bcwp=bcwp,
                    acwp=acwp,
                    bac=bac,
                    method=method,
                    manager_etc=manager_etc,
                )
                results.append(result)
            except (ZeroDivisionError, TypeError, ValueError):
                continue

        return results
