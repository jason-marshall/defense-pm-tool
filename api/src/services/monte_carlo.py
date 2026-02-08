"""Monte Carlo simulation engine using NumPy.

This module provides a high-performance Monte Carlo simulation engine
for schedule and cost risk analysis. Uses NumPy vectorization for
efficient computation, targeting <5 seconds for 1000 iterations.

Supported probability distributions:
- Triangular: min, mode, max (classic three-point estimate)
- PERT: min, mode, max (beta distribution with better central tendency)
- Normal: mean, std (Gaussian distribution)
- Uniform: min, max (equal probability across range)
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import UUID

import numpy as np
from numpy.typing import NDArray


class DistributionType(str, Enum):
    """Supported probability distributions."""

    TRIANGULAR = "triangular"
    PERT = "pert"
    NORMAL = "normal"
    UNIFORM = "uniform"


@dataclass
class DistributionParams:
    """Parameters for probability distribution.

    For triangular/PERT: min_value, mode, max_value
    For normal: mean, std
    For uniform: min_value, max_value

    Attributes:
        distribution: Distribution type (triangular, pert, normal, uniform)
        min_value: Minimum value (for triangular, pert, uniform)
        max_value: Maximum value (for triangular, pert, uniform)
        mode: Most likely value (for triangular, pert)
        mean: Mean value (for normal)
        std: Standard deviation (for normal)
    """

    distribution: DistributionType
    min_value: float | None = None
    max_value: float | None = None
    mode: float | None = None
    mean: float | None = None
    std: float | None = None

    def validate(self) -> None:
        """Validate distribution parameters."""
        if self.distribution in (DistributionType.TRIANGULAR, DistributionType.PERT):
            if self.min_value is None or self.mode is None or self.max_value is None:
                raise ValueError(f"{self.distribution} requires min_value, mode, and max_value")
            if not (self.min_value <= self.mode <= self.max_value):
                raise ValueError(f"Invalid {self.distribution} params: min <= mode <= max required")
        elif self.distribution == DistributionType.NORMAL:
            if self.mean is None or self.std is None:
                raise ValueError("Normal distribution requires mean and std")
            if self.std < 0:
                raise ValueError("Standard deviation must be non-negative")
        elif self.distribution == DistributionType.UNIFORM:
            if self.min_value is None or self.max_value is None:
                raise ValueError("Uniform distribution requires min_value and max_value")
            if self.min_value > self.max_value:
                raise ValueError("min_value must be <= max_value for uniform")


@dataclass
class SimulationInput:
    """Input for Monte Carlo simulation.

    Attributes:
        activity_durations: Map of activity ID to duration distribution params
        activity_costs: Optional map of activity ID to cost distribution params
        iterations: Number of simulation iterations
        seed: Optional random seed for reproducibility
        include_activity_stats: Whether to compute per-activity statistics
    """

    activity_durations: dict[UUID, DistributionParams]
    activity_costs: dict[UUID, DistributionParams] | None = None
    iterations: int = 1000
    seed: int | None = None
    include_activity_stats: bool = False


@dataclass
class SimulationOutput:
    """Output from Monte Carlo simulation.

    Contains percentile values (P10, P50, P80, P90), mean, std,
    and optional histogram data for visualization.

    Attributes:
        duration_samples: Raw duration samples (iterations,)
        duration_p10-p90: Duration percentiles
        duration_mean/std/min/max: Duration statistics
        cost_*: Cost metrics (if cost distributions provided)
        activity_stats: Per-activity statistics (if requested)
        histogram_bins/counts: Histogram data for visualization
        iterations: Number of iterations completed
        elapsed_seconds: Computation time
    """

    # Duration results
    duration_samples: NDArray[np.float64]
    duration_p10: float
    duration_p50: float
    duration_p80: float
    duration_p90: float
    duration_mean: float
    duration_std: float
    duration_min: float
    duration_max: float

    # Cost results (optional)
    cost_samples: NDArray[np.float64] | None = None
    cost_p10: float | None = None
    cost_p50: float | None = None
    cost_p80: float | None = None
    cost_p90: float | None = None
    cost_mean: float | None = None
    cost_std: float | None = None
    cost_min: float | None = None
    cost_max: float | None = None

    # Per-activity statistics (optional)
    activity_stats: dict[str, dict[str, float]] | None = None

    # Histogram data
    duration_histogram_bins: NDArray[np.float64] | None = None
    duration_histogram_counts: NDArray[np.int64] | None = None
    cost_histogram_bins: NDArray[np.float64] | None = None
    cost_histogram_counts: NDArray[np.int64] | None = None

    # Metadata
    iterations: int = 0
    elapsed_seconds: float = 0.0
    seed: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "duration_results": {
                "p10": self.duration_p10,
                "p50": self.duration_p50,
                "p80": self.duration_p80,
                "p90": self.duration_p90,
                "mean": self.duration_mean,
                "std": self.duration_std,
                "min": self.duration_min,
                "max": self.duration_max,
            },
            "iterations": self.iterations,
            "elapsed_seconds": self.elapsed_seconds,
        }

        if self.cost_p50 is not None:
            result["cost_results"] = {
                "p10": self.cost_p10,
                "p50": self.cost_p50,
                "p80": self.cost_p80,
                "p90": self.cost_p90,
                "mean": self.cost_mean,
                "std": self.cost_std,
                "min": self.cost_min,
                "max": self.cost_max,
            }

        if self.duration_histogram_bins is not None:
            result["duration_histogram"] = {
                "bins": self.duration_histogram_bins.tolist(),
                "counts": self.duration_histogram_counts.tolist()
                if self.duration_histogram_counts is not None
                else [],
            }

        if self.cost_histogram_bins is not None:
            result["cost_histogram"] = {
                "bins": self.cost_histogram_bins.tolist(),
                "counts": self.cost_histogram_counts.tolist()
                if self.cost_histogram_counts is not None
                else [],
            }

        if self.activity_stats is not None:
            result["activity_stats"] = self.activity_stats

        if self.seed is not None:
            result["seed"] = self.seed

        return result


class MonteCarloEngine:
    """
    Vectorized Monte Carlo simulation engine.

    Uses NumPy for high-performance simulation:
    - Generates all random samples at once (vectorized)
    - Performs batch calculations
    - Target: 1000 iterations in <5 seconds

    Supported distributions:
    - Triangular: min, mode, max
    - PERT: min, mode, max (beta distribution with better behavior)
    - Normal: mean, std
    - Uniform: min, max

    Example usage:
        engine = MonteCarloEngine(seed=42)
        output = engine.simulate(SimulationInput(
            activity_durations={
                uuid1: DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0, mode=10.0, max_value=20.0
                ),
            },
            iterations=1000
        ))
        print(f"P80 Duration: {output.duration_p80}")
    """

    def __init__(self, seed: int | None = None):
        """Initialize Monte Carlo engine.

        Args:
            seed: Optional random seed for reproducibility
        """
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def simulate(self, input_data: SimulationInput) -> SimulationOutput:
        """
        Run Monte Carlo simulation.

        Generates random samples for all activities, sums them to get
        total project duration/cost, and computes statistics.

        Note: This is a simplified simulation that sums durations.
        For a more accurate simulation with dependencies, the CPM
        network would need to be simulated for each iteration.

        Args:
            input_data: Simulation parameters and distributions

        Returns:
            SimulationOutput with percentiles, statistics, and histograms
        """
        start_time = time.perf_counter()

        # Validate inputs
        for params in input_data.activity_durations.values():
            params.validate()

        if input_data.activity_costs:
            for params in input_data.activity_costs.values():
                params.validate()

        iterations = input_data.iterations

        # Use provided seed or engine's default
        used_seed: int | None
        if input_data.seed is not None:
            self.rng = np.random.default_rng(input_data.seed)
            used_seed = input_data.seed
        else:
            used_seed = self.seed

        # Generate duration samples for all activities
        duration_matrix = self._generate_samples(
            input_data.activity_durations,
            iterations,
        )

        # Sum durations across activities for each iteration
        # Note: This assumes serial execution. For parallel paths,
        # we would need to simulate the CPM network per iteration.
        total_durations = np.sum(duration_matrix, axis=1)

        # Generate cost samples if provided
        total_costs: NDArray[np.float64] | None = None
        if input_data.activity_costs:
            cost_matrix = self._generate_samples(
                input_data.activity_costs,
                iterations,
            )
            total_costs = np.sum(cost_matrix, axis=1)

        # Calculate per-activity statistics if requested
        activity_stats: dict[str, dict[str, float]] | None = None
        if input_data.include_activity_stats:
            activity_stats = self._calculate_activity_stats(
                input_data.activity_durations,
                duration_matrix,
            )

        elapsed = time.perf_counter() - start_time

        # Build output with statistics and histograms
        return self._build_output(
            total_durations=total_durations,
            total_costs=total_costs,
            activity_stats=activity_stats,
            iterations=iterations,
            elapsed=elapsed,
            seed=used_seed,
        )

    def _generate_samples(
        self,
        distributions: dict[UUID, DistributionParams],
        iterations: int,
    ) -> NDArray[np.float64]:
        """
        Generate random samples for all activities.

        Returns matrix of shape (iterations, num_activities).
        """
        num_activities = len(distributions)
        samples = np.zeros((iterations, num_activities))

        for i, (_activity_id, params) in enumerate(distributions.items()):
            samples[:, i] = self._sample_distribution(params, iterations)

        return samples

    def _sample_distribution(
        self,
        params: DistributionParams,
        n: int,
    ) -> NDArray[np.float64]:
        """Generate n samples from the specified distribution.

        Note: params.validate() must be called before this method to ensure
        required parameters are not None.
        """

        if params.distribution == DistributionType.TRIANGULAR:
            if params.min_value is None or params.mode is None or params.max_value is None:
                raise ValueError("TRIANGULAR requires min_value, mode, and max_value")
            return self.rng.triangular(
                left=params.min_value,
                mode=params.mode,
                right=params.max_value,
                size=n,
            )

        elif params.distribution == DistributionType.NORMAL:
            if params.mean is None or params.std is None:
                raise ValueError("NORMAL requires mean and std")
            return self.rng.normal(
                loc=params.mean,
                scale=params.std,
                size=n,
            )

        elif params.distribution == DistributionType.UNIFORM:
            if params.min_value is None or params.max_value is None:
                raise ValueError("UNIFORM requires min_value and max_value")
            return self.rng.uniform(
                low=params.min_value,
                high=params.max_value,
                size=n,
            )

        elif params.distribution == DistributionType.PERT:
            if params.min_value is None or params.mode is None or params.max_value is None:
                raise ValueError("PERT requires min_value, mode, and max_value")
            return self._sample_pert(
                params.min_value,
                params.mode,
                params.max_value,
                n,
            )

        else:
            raise ValueError(f"Unknown distribution: {params.distribution}")

    def _sample_pert(
        self,
        min_val: float,
        mode: float,
        max_val: float,
        n: int,
        lambda_param: float = 4.0,
    ) -> NDArray[np.float64]:
        """
        Sample from PERT (Program Evaluation and Review Technique) distribution.

        PERT is a modified beta distribution that provides smoother results
        than triangular. It's commonly used in project management.

        The lambda parameter controls the weight given to the mode:
        - lambda=4 is standard PERT
        - Higher lambda gives more weight to the mode

        Formula:
        - mean = (min + lambda*mode + max) / (lambda + 2)
        - alpha = ((mean - min) / (max - min)) * ((mean - min)*(max - mean)/(variance) - 1)
        - beta = alpha * (max - mean) / (mean - min)

        Args:
            min_val: Minimum value
            mode: Most likely value
            max_val: Maximum value
            n: Number of samples
            lambda_param: Weight for mode (default 4.0)

        Returns:
            Array of n samples from PERT distribution
        """
        range_val = max_val - min_val

        if range_val == 0:
            return np.full(n, min_val)

        # Calculate mean using PERT formula
        mean = (min_val + lambda_param * mode + max_val) / (lambda_param + 2)

        # Handle edge case where mode equals min or max
        if mode == min_val:
            alpha = 1.0
            beta = (max_val - mean) / (mean - min_val + 1e-10) if mean > min_val else 1.0
        elif mode == max_val:
            beta = 1.0
            alpha = (mean - min_val) / (max_val - mean + 1e-10) if mean < max_val else 1.0
        else:
            # Standard PERT shape parameters
            alpha = 1 + lambda_param * (mode - min_val) / range_val
            beta = 1 + lambda_param * (max_val - mode) / range_val

        # Ensure alpha and beta are positive
        alpha = max(alpha, 0.01)
        beta = max(beta, 0.01)

        # Sample from beta distribution and scale to range
        beta_samples = self.rng.beta(alpha, beta, size=n)
        return min_val + beta_samples * range_val

    def _calculate_activity_stats(
        self,
        distributions: dict[UUID, DistributionParams],
        samples: NDArray[np.float64],
    ) -> dict[str, dict[str, float]]:
        """Calculate per-activity statistics."""
        stats: dict[str, dict[str, float]] = {}

        for i, activity_id in enumerate(distributions.keys()):
            activity_samples = samples[:, i]
            stats[str(activity_id)] = {
                "mean": float(np.mean(activity_samples)),
                "std": float(np.std(activity_samples)),
                "min": float(np.min(activity_samples)),
                "max": float(np.max(activity_samples)),
                "p10": float(np.percentile(activity_samples, 10)),
                "p50": float(np.percentile(activity_samples, 50)),
                "p90": float(np.percentile(activity_samples, 90)),
            }

        return stats

    def _build_output(
        self,
        total_durations: NDArray[np.float64],
        total_costs: NDArray[np.float64] | None,
        activity_stats: dict[str, dict[str, float]] | None,
        iterations: int,
        elapsed: float,
        seed: int | None,
    ) -> SimulationOutput:
        """Build SimulationOutput with statistics and histograms."""

        # Calculate duration histogram
        dur_counts, dur_bins = np.histogram(total_durations, bins="auto")

        # Build base output
        output = SimulationOutput(
            duration_samples=total_durations,
            duration_p10=float(np.percentile(total_durations, 10)),
            duration_p50=float(np.percentile(total_durations, 50)),
            duration_p80=float(np.percentile(total_durations, 80)),
            duration_p90=float(np.percentile(total_durations, 90)),
            duration_mean=float(np.mean(total_durations)),
            duration_std=float(np.std(total_durations)),
            duration_min=float(np.min(total_durations)),
            duration_max=float(np.max(total_durations)),
            duration_histogram_bins=dur_bins,
            duration_histogram_counts=dur_counts,
            activity_stats=activity_stats,
            iterations=iterations,
            elapsed_seconds=elapsed,
            seed=seed,
        )

        # Add cost statistics if provided
        if total_costs is not None:
            cost_counts, cost_bins = np.histogram(total_costs, bins="auto")

            output.cost_samples = total_costs
            output.cost_p10 = float(np.percentile(total_costs, 10))
            output.cost_p50 = float(np.percentile(total_costs, 50))
            output.cost_p80 = float(np.percentile(total_costs, 80))
            output.cost_p90 = float(np.percentile(total_costs, 90))
            output.cost_mean = float(np.mean(total_costs))
            output.cost_std = float(np.std(total_costs))
            output.cost_min = float(np.min(total_costs))
            output.cost_max = float(np.max(total_costs))
            output.cost_histogram_bins = cost_bins
            output.cost_histogram_counts = cost_counts

        return output


def parse_distribution_params(data: dict[str, Any]) -> DistributionParams:
    """
    Parse distribution parameters from dictionary.

    Expected format:
    {
        "distribution": "triangular",
        "min": 5,
        "mode": 10,
        "max": 20
    }

    Args:
        data: Dictionary with distribution parameters

    Returns:
        DistributionParams instance
    """
    dist_type = DistributionType(data.get("distribution", "triangular"))

    # Use explicit None checks to handle 0 values correctly (0 is a valid value)
    min_val = data.get("min")
    min_value = min_val if min_val is not None else data.get("min_value")

    max_val = data.get("max")
    max_value = max_val if max_val is not None else data.get("max_value")

    return DistributionParams(
        distribution=dist_type,
        min_value=min_value,
        max_value=max_value,
        mode=data.get("mode"),
        mean=data.get("mean"),
        std=data.get("std"),
    )
