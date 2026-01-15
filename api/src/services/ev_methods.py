"""Earned Value (EV) Method Calculator for EVMS compliance.

This module implements multiple EV calculation methods per DI-MGMT-81466
and EIA-748 standards.

Methods implemented:
- 0/100: Discrete tasks (0% until complete, then 100%)
- 50/50: Medium tasks (50% at start, 100% at finish)
- Percent Complete: Based on reported progress
- Milestone Weight: Based on completed milestone weights
- LOE: Level of Effort (BCWP = BCWS)
- Apportioned: Based on related activity (deferred)
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.models.enums import EVMethod


@dataclass
class Milestone:
    """Represents a milestone for milestone-weighted EV calculation."""

    name: str
    weight: Decimal
    is_complete: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Milestone":
        """Create Milestone from dictionary."""
        return cls(
            name=data.get("name", ""),
            weight=Decimal(str(data.get("weight", 0))),
            is_complete=data.get("is_complete", False),
        )


@dataclass
class EVCalculationInput:
    """Input parameters for EV calculation."""

    bac: Decimal  # Budget at Completion
    bcws: Decimal  # Budgeted Cost of Work Scheduled (planned value)
    percent_complete: Decimal  # Reported percent complete (0-100)
    is_started: bool  # Whether activity has started
    is_completed: bool  # Whether activity is 100% complete
    milestones: list[Milestone] | None = None  # For milestone-weight method
    base_bcwp: Decimal | None = None  # For apportioned method
    apportionment_factor: Decimal | None = None  # For apportioned method


@dataclass
class EVCalculationResult:
    """Result of EV calculation."""

    bcwp: Decimal  # Earned Value (Budgeted Cost of Work Performed)
    method_used: EVMethod
    earned_percent: Decimal  # Percent earned (0-100)
    notes: str | None = None


class EVMethodCalculator:
    """
    Calculator for Earned Value using various methods.

    Per EVMS guidelines:
    - 0/100: Best for tasks < 1 month
    - 50/50: Best for 1-2 month tasks
    - Percent Complete: General use
    - Milestone Weight: 3+ month tasks with milestones
    - LOE: Support/overhead activities

    Example:
        >>> calc = EVMethodCalculator()
        >>> result = calc.calculate(
        ...     EVMethod.FIFTY_FIFTY,
        ...     EVCalculationInput(
        ...         bac=Decimal("10000"),
        ...         bcws=Decimal("5000"),
        ...         percent_complete=Decimal("50"),
        ...         is_started=True,
        ...         is_completed=False,
        ...     )
        ... )
        >>> result.bcwp
        Decimal('5000.00')
    """

    def calculate(
        self,
        method: EVMethod,
        input_data: EVCalculationInput,
    ) -> EVCalculationResult:
        """
        Calculate earned value using the specified method.

        Args:
            method: EV calculation method to use
            input_data: Input parameters for calculation

        Returns:
            EVCalculationResult with BCWP and metadata

        Raises:
            ValueError: If method requires data not provided
        """
        match method:
            case EVMethod.ZERO_HUNDRED:
                return self._calculate_zero_hundred(input_data)
            case EVMethod.FIFTY_FIFTY:
                return self._calculate_fifty_fifty(input_data)
            case EVMethod.PERCENT_COMPLETE:
                return self._calculate_percent_complete(input_data)
            case EVMethod.MILESTONE_WEIGHT:
                return self._calculate_milestone_weight(input_data)
            case EVMethod.LOE:
                return self._calculate_loe(input_data)
            case EVMethod.APPORTIONED:
                return self._calculate_apportioned(input_data)
            case _:
                raise ValueError(f"Unknown EV method: {method}")

    def _calculate_zero_hundred(
        self,
        input_data: EVCalculationInput,
    ) -> EVCalculationResult:
        """
        Calculate EV using 0/100 method.

        BCWP = 0 until complete, then BAC.
        Best for short discrete tasks.
        """
        if input_data.is_completed:
            bcwp = input_data.bac
            earned_percent = Decimal("100.00")
        else:
            bcwp = Decimal("0.00")
            earned_percent = Decimal("0.00")

        return EVCalculationResult(
            bcwp=bcwp.quantize(Decimal("0.01")),
            method_used=EVMethod.ZERO_HUNDRED,
            earned_percent=earned_percent,
            notes="0/100 discrete method",
        )

    def _calculate_fifty_fifty(
        self,
        input_data: EVCalculationInput,
    ) -> EVCalculationResult:
        """
        Calculate EV using 50/50 method.

        BCWP = 50% of BAC when started, 100% when complete.
        Best for 1-2 month tasks.
        """
        if input_data.is_completed:
            bcwp = input_data.bac
            earned_percent = Decimal("100.00")
        elif input_data.is_started:
            bcwp = input_data.bac * Decimal("0.50")
            earned_percent = Decimal("50.00")
        else:
            bcwp = Decimal("0.00")
            earned_percent = Decimal("0.00")

        return EVCalculationResult(
            bcwp=bcwp.quantize(Decimal("0.01")),
            method_used=EVMethod.FIFTY_FIFTY,
            earned_percent=earned_percent,
            notes="50/50 method",
        )

    def _calculate_percent_complete(
        self,
        input_data: EVCalculationInput,
    ) -> EVCalculationResult:
        """
        Calculate EV using percent complete method.

        BCWP = BAC * (percent_complete / 100)
        Default method for general use.
        """
        earned_percent = input_data.percent_complete
        bcwp = input_data.bac * earned_percent / Decimal("100.00")

        return EVCalculationResult(
            bcwp=bcwp.quantize(Decimal("0.01")),
            method_used=EVMethod.PERCENT_COMPLETE,
            earned_percent=earned_percent,
            notes=f"Based on {earned_percent}% complete",
        )

    def _calculate_milestone_weight(
        self,
        input_data: EVCalculationInput,
    ) -> EVCalculationResult:
        """
        Calculate EV using milestone weight method.

        BCWP = BAC * sum(completed milestone weights)
        Best for long tasks with defined milestones.
        """
        if not input_data.milestones:
            raise ValueError("Milestone-weight method requires milestone definitions")

        # Sum weights of completed milestones
        total_weight = sum(m.weight for m in input_data.milestones if m.is_complete)

        # Calculate BCWP
        bcwp = input_data.bac * total_weight
        earned_percent = total_weight * Decimal("100.00")

        # Build note about completed milestones
        completed = [m.name for m in input_data.milestones if m.is_complete]
        note = f"Completed: {', '.join(completed)}" if completed else "No milestones complete"

        return EVCalculationResult(
            bcwp=bcwp.quantize(Decimal("0.01")),
            method_used=EVMethod.MILESTONE_WEIGHT,
            earned_percent=earned_percent.quantize(Decimal("0.01")),
            notes=note,
        )

    def _calculate_loe(
        self,
        input_data: EVCalculationInput,
    ) -> EVCalculationResult:
        """
        Calculate EV using Level of Effort (LOE) method.

        BCWP = BCWS (earned value always equals planned value)
        Best for support/overhead activities.
        """
        bcwp = input_data.bcws

        # Calculate earned percent based on BCWS/BAC
        if input_data.bac > 0:
            earned_percent = (input_data.bcws / input_data.bac) * Decimal("100.00")
        else:
            earned_percent = Decimal("0.00")

        return EVCalculationResult(
            bcwp=bcwp.quantize(Decimal("0.01")),
            method_used=EVMethod.LOE,
            earned_percent=earned_percent.quantize(Decimal("0.01")),
            notes="LOE: BCWP = BCWS",
        )

    def _calculate_apportioned(
        self,
        input_data: EVCalculationInput,
    ) -> EVCalculationResult:
        """
        Calculate EV using apportioned effort method.

        BCWP = factor * base_activity_BCWP
        For activities tied to another activity's progress.
        """
        if input_data.base_bcwp is None:
            raise ValueError("Apportioned method requires base_bcwp")
        if input_data.apportionment_factor is None:
            raise ValueError("Apportioned method requires apportionment_factor")

        bcwp = input_data.base_bcwp * input_data.apportionment_factor

        # Calculate earned percent
        if input_data.bac > 0:
            earned_percent = (bcwp / input_data.bac) * Decimal("100.00")
        else:
            earned_percent = Decimal("0.00")

        return EVCalculationResult(
            bcwp=bcwp.quantize(Decimal("0.01")),
            method_used=EVMethod.APPORTIONED,
            earned_percent=earned_percent.quantize(Decimal("0.01")),
            notes=f"Apportioned at {input_data.apportionment_factor}* base BCWP",
        )


def validate_milestone_weights(milestones: list[dict[str, Any]]) -> bool:
    """
    Validate that milestone weights sum to 1.0 (100%).

    Args:
        milestones: List of milestone dicts with 'weight' key

    Returns:
        True if weights sum to 1.0 (within tolerance)

    Example:
        >>> validate_milestone_weights([
        ...     {"name": "Design", "weight": 0.25},
        ...     {"name": "Build", "weight": 0.50},
        ...     {"name": "Test", "weight": 0.25},
        ... ])
        True
    """
    total = sum(Decimal(str(m.get("weight", 0))) for m in milestones)
    return abs(total - Decimal("1.0")) < Decimal("0.001")


def get_ev_method_info() -> list[dict[str, str]]:
    """
    Get information about all available EV methods.

    Returns:
        List of dicts with method info for API response.

    Example:
        >>> methods = get_ev_method_info()
        >>> methods[0]["value"]
        '0/100'
    """
    return [
        {
            "value": method.value,
            "display_name": method.display_name,
            "description": method.description,
            "recommended_duration": method.recommended_duration,
        }
        for method in EVMethod
    ]
