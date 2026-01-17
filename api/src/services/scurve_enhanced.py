"""Enhanced S-curve service with Monte Carlo confidence bands.

This module generates S-curve visualizations that combine:
- Historical EVMS period data (BCWS, BCWP, ACWP)
- Monte Carlo simulation results for forecast confidence bands
- EAC range estimates based on simulation uncertainty

The confidence bands show P10/P50/P90 ranges for:
- Estimate at Completion (EAC)
- Project completion date/duration
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass
class SCurveDataPoint:
    """S-curve data point with optional confidence bands.

    Attributes:
        period_number: Sequential period number (1, 2, 3, ...)
        period_date: End date of the period
        period_name: Human-readable period name
        bcws: Period BCWS (Planned Value)
        bcwp: Period BCWP (Earned Value)
        acwp: Period ACWP (Actual Cost)
        cumulative_bcws: Cumulative BCWS through this period
        cumulative_bcwp: Cumulative BCWP through this period
        cumulative_acwp: Cumulative ACWP through this period
        is_forecast: Whether this is a forecast point
        forecast_bcwp_p10: P10 forecast for BCWP (optimistic)
        forecast_bcwp_p50: P50 forecast for BCWP (most likely)
        forecast_bcwp_p90: P90 forecast for BCWP (pessimistic)
    """

    period_number: int
    period_date: date
    period_name: str

    # Period values
    bcws: Decimal
    bcwp: Decimal
    acwp: Decimal

    # Cumulative values
    cumulative_bcws: Decimal
    cumulative_bcwp: Decimal
    cumulative_acwp: Decimal

    # Forecast fields (for future periods)
    is_forecast: bool = False
    forecast_bcwp_p10: Decimal | None = None
    forecast_bcwp_p50: Decimal | None = None
    forecast_bcwp_p90: Decimal | None = None


@dataclass
class EACRange:
    """EAC estimate range from Monte Carlo simulation.

    Attributes:
        p10: 10th percentile (optimistic)
        p50: 50th percentile (median/most likely)
        p90: 90th percentile (pessimistic)
        method: EAC calculation method used
    """

    p10: Decimal
    p50: Decimal
    p90: Decimal
    method: str = "simulation"


@dataclass
class CompletionDateRange:
    """Project completion date/duration range.

    Attributes:
        p10_days: 10th percentile duration (optimistic)
        p50_days: 50th percentile duration (most likely)
        p90_days: 90th percentile duration (pessimistic)
        p10_date: Estimated P10 completion date
        p50_date: Estimated P50 completion date
        p90_date: Estimated P90 completion date
    """

    p10_days: float
    p50_days: float
    p90_days: float
    p10_date: date | None = None
    p50_date: date | None = None
    p90_date: date | None = None


@dataclass
class EnhancedSCurveResponse:
    """Enhanced S-curve response with forecasts and confidence bands.

    Attributes:
        program_id: Program ID
        data_points: List of S-curve data points
        bac: Budget at Completion
        current_period: Current/latest period number
        percent_complete: Overall percent complete
        eac_range: EAC estimate range
        completion_range: Completion date/duration range
        simulation_available: Whether simulation data is available
    """

    program_id: UUID
    data_points: list[SCurveDataPoint]
    bac: Decimal
    current_period: int
    percent_complete: Decimal
    eac_range: EACRange | None = None
    completion_range: CompletionDateRange | None = None
    simulation_available: bool = False


@dataclass
class SimulationMetrics:
    """Simplified simulation metrics for S-curve calculations.

    Attributes:
        duration_p10: P10 project duration
        duration_p50: P50 project duration
        duration_p90: P90 project duration
        duration_mean: Mean project duration
        duration_std: Standard deviation of duration
    """

    duration_p10: float
    duration_p50: float
    duration_p90: float
    duration_mean: float
    duration_std: float


class EnhancedSCurveService:
    """
    Generate S-curve with Monte Carlo-derived confidence bands.

    Combines historical EVMS data with simulation forecasts to show
    completion confidence ranges. This enables risk-informed decision
    making by visualizing the range of possible outcomes.

    Example usage:
        service = EnhancedSCurveService(
            program_id=program_id,
            periods=evms_periods,
            bac=Decimal("1000000"),
            simulation_metrics=simulation_metrics,
        )
        response = service.generate()
    """

    def __init__(
        self,
        program_id: UUID,
        periods: list[Any],  # EVMSPeriod objects
        bac: Decimal,
        simulation_metrics: SimulationMetrics | None = None,
        start_date: date | None = None,
    ) -> None:
        """
        Initialize enhanced S-curve service.

        Args:
            program_id: Program ID
            periods: List of EVMS period objects with cumulative values
            bac: Budget at Completion
            simulation_metrics: Optional Monte Carlo simulation metrics
            start_date: Program start date for date calculations
        """
        self.program_id = program_id
        self.periods = sorted(periods, key=lambda p: p.period_end) if periods else []
        self.bac = bac or Decimal("0")
        self.simulation = simulation_metrics
        self.start_date = start_date

    def generate(self) -> EnhancedSCurveResponse:
        """
        Generate enhanced S-curve with confidence bands.

        Returns:
            EnhancedSCurveResponse with data points and forecasts
        """
        # Convert periods to data points
        data_points = self._build_data_points()

        # Determine current state
        current_period = len(data_points) if data_points else 0
        percent_complete = self._calculate_percent_complete()

        # Calculate EAC range if simulation available
        eac_range = self._calculate_eac_range() if self.simulation else None

        # Calculate completion range if simulation available
        completion_range = self._calculate_completion_range() if self.simulation else None

        return EnhancedSCurveResponse(
            program_id=self.program_id,
            data_points=data_points,
            bac=self.bac,
            current_period=current_period,
            percent_complete=percent_complete,
            eac_range=eac_range,
            completion_range=completion_range,
            simulation_available=self.simulation is not None,
        )

    def _build_data_points(self) -> list[SCurveDataPoint]:
        """Build S-curve data points from EVMS periods."""
        data_points: list[SCurveDataPoint] = []

        for i, period in enumerate(self.periods, start=1):
            # Get period values (handle both attribute and dict access)
            bcws = getattr(period, "bcws", Decimal("0")) or Decimal("0")
            bcwp = getattr(period, "bcwp", Decimal("0")) or Decimal("0")
            acwp = getattr(period, "acwp", Decimal("0")) or Decimal("0")

            cumulative_bcws = getattr(period, "cumulative_bcws", Decimal("0")) or Decimal("0")
            cumulative_bcwp = getattr(period, "cumulative_bcwp", Decimal("0")) or Decimal("0")
            cumulative_acwp = getattr(period, "cumulative_acwp", Decimal("0")) or Decimal("0")

            period_date = getattr(period, "period_end", date.today())
            period_name = getattr(period, "period_name", f"Period {i}")

            data_points.append(
                SCurveDataPoint(
                    period_number=i,
                    period_date=period_date,
                    period_name=period_name,
                    bcws=bcws,
                    bcwp=bcwp,
                    acwp=acwp,
                    cumulative_bcws=cumulative_bcws,
                    cumulative_bcwp=cumulative_bcwp,
                    cumulative_acwp=cumulative_acwp,
                    is_forecast=False,
                )
            )

        return data_points

    def _calculate_percent_complete(self) -> Decimal:
        """Calculate overall percent complete."""
        if not self.periods or self.bac == 0:
            return Decimal("0")

        latest = self.periods[-1]
        cumulative_bcwp = getattr(latest, "cumulative_bcwp", Decimal("0")) or Decimal("0")

        return (cumulative_bcwp / self.bac * 100).quantize(Decimal("0.01"))

    def _calculate_eac_range(self) -> EACRange | None:
        """Calculate EAC range from simulation uncertainty."""
        if not self.simulation or not self.periods:
            return None

        # Get current values
        latest = self.periods[-1]
        acwp = float(getattr(latest, "cumulative_acwp", 0) or 0)
        bcwp = float(getattr(latest, "cumulative_bcwp", 0) or 0)
        bac = float(self.bac)

        if bac == 0:
            return None

        # Calculate current CPI
        cpi = bcwp / acwp if acwp > 0 else 1.0

        # If no work done, return BAC
        if bcwp == 0:
            return EACRange(
                p10=self.bac,
                p50=self.bac,
                p90=self.bac,
                method="no_progress",
            )

        # Calculate remaining work percentage
        remaining_pct = (bac - bcwp) / bac

        # Apply duration uncertainty to cost estimate
        # Higher duration uncertainty = higher cost uncertainty
        if self.simulation.duration_mean > 0:
            uncertainty_factor = self.simulation.duration_std / self.simulation.duration_mean
        else:
            uncertainty_factor = 0.1  # Default 10% uncertainty

        # Base EAC using CPI method
        base_eac = acwp + (bac - bcwp) / cpi

        # Apply uncertainty based on remaining work
        # More remaining work = more uncertainty impact
        uncertainty_impact = uncertainty_factor * remaining_pct

        eac_p10 = base_eac * (1 - uncertainty_impact)
        eac_p50 = base_eac
        eac_p90 = base_eac * (1 + uncertainty_impact)

        return EACRange(
            p10=Decimal(str(round(eac_p10, 2))),
            p50=Decimal(str(round(eac_p50, 2))),
            p90=Decimal(str(round(eac_p90, 2))),
            method="simulation_adjusted",
        )

    def _calculate_completion_range(self) -> CompletionDateRange | None:
        """Calculate completion date range from simulation."""
        if not self.simulation:
            return None

        # Get duration percentiles from simulation
        p10_days = self.simulation.duration_p10
        p50_days = self.simulation.duration_p50
        p90_days = self.simulation.duration_p90

        # Calculate dates if start date available
        p10_date = None
        p50_date = None
        p90_date = None

        if self.start_date:
            p10_date = self.start_date + timedelta(days=int(p10_days))
            p50_date = self.start_date + timedelta(days=int(p50_days))
            p90_date = self.start_date + timedelta(days=int(p90_days))

        return CompletionDateRange(
            p10_days=round(p10_days, 1),
            p50_days=round(p50_days, 1),
            p90_days=round(p90_days, 1),
            p10_date=p10_date,
            p50_date=p50_date,
            p90_date=p90_date,
        )


def build_simulation_metrics_from_result(result: Any) -> SimulationMetrics | None:
    """
    Build SimulationMetrics from a SimulationResult object.

    Args:
        result: SimulationResult with duration_results JSON field

    Returns:
        SimulationMetrics or None if result invalid
    """
    if not result:
        return None

    duration_results = getattr(result, "duration_results", None)
    if not duration_results:
        return None

    try:
        return SimulationMetrics(
            duration_p10=float(duration_results.get("p10", 0)),
            duration_p50=float(duration_results.get("p50", 0)),
            duration_p90=float(duration_results.get("p90", 0)),
            duration_mean=float(duration_results.get("mean", 0)),
            duration_std=float(duration_results.get("std", 1)),
        )
    except (TypeError, ValueError):
        return None
