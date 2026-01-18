"""Tornado chart data generation for sensitivity analysis.

Tornado charts visualize which activities have the greatest impact on
project duration based on Monte Carlo simulation sensitivity analysis.

The chart shows horizontal bars for each activity, with:
- Bar width representing the impact range (low to high estimate)
- Bars sorted by absolute correlation (highest impact first)
- Base project duration shown as vertical reference line

Per architecture: Probabilistic Analysis Module sensitivity visualization.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class TornadoBar:
    """Single bar in tornado chart.

    Represents one activity's impact on project duration.

    Attributes:
        activity_id: Unique identifier for the activity
        activity_name: Human-readable activity name
        correlation: Correlation coefficient with project duration (-1 to 1)
        low_impact: Project duration when activity is at low estimate
        high_impact: Project duration when activity is at high estimate
        base_value: Expected (mean) project duration
        rank: Position in the tornado chart (1 = most impactful)
        impact_range: Absolute difference between high and low impact
    """

    activity_id: UUID
    activity_name: str
    correlation: float
    low_impact: float
    high_impact: float
    base_value: float
    rank: int

    @property
    def impact_range(self) -> float:
        """Calculate the total impact range."""
        return abs(self.high_impact - self.low_impact)

    @property
    def is_positive_correlation(self) -> bool:
        """Check if activity has positive correlation."""
        return self.correlation >= 0

    @property
    def absolute_correlation(self) -> float:
        """Get absolute value of correlation."""
        return abs(self.correlation)

    @property
    def impact_direction(self) -> str:
        """Get impact direction description.

        Returns:
            'direct' if positive correlation, 'inverse' if negative
        """
        return "direct" if self.correlation >= 0 else "inverse"


@dataclass
class TornadoChartData:
    """Complete tornado chart data.

    Contains all data needed to render a tornado chart visualization.

    Attributes:
        base_project_duration: Mean/expected project duration (vertical line)
        bars: List of tornado bars sorted by impact
        top_drivers_count: Number of bars included
        min_duration: Minimum value across all bars (for chart scaling)
        max_duration: Maximum value across all bars (for chart scaling)
    """

    base_project_duration: float
    bars: list[TornadoBar] = field(default_factory=list)
    top_drivers_count: int = 0

    @property
    def min_duration(self) -> float:
        """Get minimum duration value for chart scaling."""
        if not self.bars:
            return self.base_project_duration
        return min(min(bar.low_impact, bar.high_impact) for bar in self.bars)

    @property
    def max_duration(self) -> float:
        """Get maximum duration value for chart scaling."""
        if not self.bars:
            return self.base_project_duration
        return max(max(bar.low_impact, bar.high_impact) for bar in self.bars)

    @property
    def chart_range(self) -> float:
        """Get total range for chart scaling."""
        return self.max_duration - self.min_duration

    def get_bar_by_activity(self, activity_id: UUID) -> TornadoBar | None:
        """Find a bar by activity ID."""
        for bar in self.bars:
            if bar.activity_id == activity_id:
                return bar
        return None

    def get_top_n(self, n: int) -> list[TornadoBar]:
        """Get top N most impactful activities."""
        return self.bars[:n]


class TornadoChartService:
    """Generate tornado chart data from simulation results.

    Uses sensitivity analysis results (correlations) to create a visual
    representation of which activities most influence project duration.

    Example usage:
        service = TornadoChartService(
            sensitivity=sensitivity_dict,
            activity_names=name_dict,
            base_duration=100.5,
            activity_ranges=range_dict,
        )
        chart_data = service.generate(top_n=10)
    """

    def __init__(
        self,
        sensitivity: Mapping[UUID, float],
        activity_names: Mapping[UUID, str],
        base_duration: float,
        activity_ranges: Mapping[UUID, tuple[float, float]],  # (min, max)
    ) -> None:
        """Initialize tornado chart service.

        Args:
            sensitivity: Map of activity ID to correlation with project duration
            activity_names: Map of activity ID to human-readable name
            base_duration: Mean/expected project duration
            activity_ranges: Map of activity ID to (min_estimate, max_estimate)
        """
        self.sensitivity = dict(sensitivity)
        self.activity_names = dict(activity_names)
        self.base_duration = base_duration
        self.activity_ranges = dict(activity_ranges)

    def generate(self, top_n: int = 10) -> TornadoChartData:
        """Generate tornado chart data for top N drivers.

        Sorts activities by absolute correlation and calculates
        impact ranges for visualization.

        Args:
            top_n: Number of top drivers to include (default 10)

        Returns:
            TornadoChartData with sorted bars
        """
        # Sort by absolute correlation (highest first)
        sorted_activities = sorted(
            self.sensitivity.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:top_n]

        bars: list[TornadoBar] = []
        for rank, (activity_id, correlation) in enumerate(sorted_activities, 1):
            # Get activity name (fallback to truncated UUID)
            name = self.activity_names.get(activity_id, str(activity_id)[:8])

            # Get activity duration range
            min_val, max_val = self.activity_ranges.get(activity_id, (0, 0))
            activity_range = max_val - min_val

            # Calculate impact on project duration
            # The correlation tells us how activity duration affects project duration
            # Higher positive correlation = longer activity -> longer project
            low_impact, high_impact = self._calculate_impact(
                correlation=correlation,
                activity_range=activity_range,
            )

            bars.append(
                TornadoBar(
                    activity_id=activity_id,
                    activity_name=name,
                    correlation=round(correlation, 4),
                    low_impact=round(low_impact, 2),
                    high_impact=round(high_impact, 2),
                    base_value=round(self.base_duration, 2),
                    rank=rank,
                )
            )

        return TornadoChartData(
            base_project_duration=round(self.base_duration, 2),
            bars=bars,
            top_drivers_count=len(bars),
        )

    def _calculate_impact(
        self,
        correlation: float,
        activity_range: float,
    ) -> tuple[float, float]:
        """Calculate low and high impact values for an activity.

        The impact is calculated by scaling the activity range by the
        correlation coefficient to estimate how much the activity
        affects the project duration.

        Args:
            correlation: Correlation with project duration
            activity_range: Difference between max and min estimate

        Returns:
            Tuple of (low_impact, high_impact) project durations
        """
        # Scale impact by absolute correlation
        # This approximates how much changing this activity affects the project
        impact_magnitude = activity_range * abs(correlation)

        if correlation >= 0:
            # Positive correlation: longer activity -> longer project
            # Low estimate reduces project duration
            # High estimate increases project duration
            low_impact = self.base_duration - impact_magnitude / 2
            high_impact = self.base_duration + impact_magnitude / 2
        else:
            # Negative correlation: longer activity -> shorter project
            # (rare but possible in certain network configurations)
            # Low estimate increases project duration
            # High estimate decreases project duration
            low_impact = self.base_duration + impact_magnitude / 2
            high_impact = self.base_duration - impact_magnitude / 2

        return low_impact, high_impact

    def get_critical_drivers(
        self,
        threshold: float = 0.3,
    ) -> list[tuple[UUID, float]]:
        """Get activities with correlation above threshold.

        Args:
            threshold: Minimum absolute correlation to include

        Returns:
            List of (activity_id, correlation) tuples
        """
        return [
            (act_id, corr) for act_id, corr in self.sensitivity.items() if abs(corr) >= threshold
        ]

    def calculate_cumulative_impact(
        self,
        activity_ids: Sequence[UUID],
    ) -> float:
        """Calculate combined impact of multiple activities.

        Uses sum of squared correlations as a measure of combined influence.

        Args:
            activity_ids: List of activity IDs to include

        Returns:
            Combined impact score (0 to 1)
        """
        total_r_squared = sum(self.sensitivity.get(act_id, 0) ** 2 for act_id in activity_ids)
        # Normalize to 0-1 range
        return min(total_r_squared, 1.0)


def build_tornado_from_simulation_result(
    result: Mapping[str, float | dict[str, Any]],
    activity_names: Mapping[UUID, str],
    activity_distributions: Mapping[str, dict[str, Any]],
) -> TornadoChartData:
    """Build tornado chart from a simulation result.

    Convenience function to extract tornado chart data from
    a Monte Carlo simulation result.

    Args:
        result: Simulation result with sensitivity and duration data
        activity_names: Map of activity ID to name
        activity_distributions: Distribution parameters by activity ID string

    Returns:
        TornadoChartData ready for visualization
    """
    # Extract sensitivity data
    sensitivity_raw = result.get("sensitivity", {})
    if isinstance(sensitivity_raw, dict):
        sensitivity: dict[UUID, float] = {UUID(k): float(v) for k, v in sensitivity_raw.items()}
    else:
        sensitivity = {}

    # Extract base duration
    mean_val = result.get("mean", 0)
    base_duration = float(mean_val) if isinstance(mean_val, (int, float, str)) else 0.0

    # Extract activity ranges from distributions
    activity_ranges: dict[UUID, tuple[float, float]] = {}
    for act_id_str, params in activity_distributions.items():
        try:
            act_id = UUID(act_id_str)
            min_val = float(params.get("min_value", params.get("min", 0)))
            max_val = float(params.get("max_value", params.get("max", min_val + 10)))
            activity_ranges[act_id] = (min_val, max_val)
        except (ValueError, TypeError):
            continue

    service = TornadoChartService(
        sensitivity=sensitivity,
        activity_names=activity_names,
        base_duration=base_duration,
        activity_ranges=activity_ranges,
    )

    return service.generate()
