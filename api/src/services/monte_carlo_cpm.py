"""Monte Carlo simulation integrated with CPM network.

This module provides network-aware Monte Carlo simulation that respects
the actual dependency topology when calculating schedule risk.

For each iteration, durations are sampled from distributions and the
CPM network is simulated to determine the actual critical path and
project duration. This captures critical path shifts that occur when
activity durations vary.

Key outputs:
- Project duration distribution (P10, P50, P80, P90)
- Activity criticality (% of iterations on critical path)
- Activity finish date distributions
- Sensitivity analysis (correlation with project duration)
"""

import time
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

from src.services.cpm import CPMEngine
from src.services.monte_carlo import (
    DistributionParams,
    DistributionType,
    MonteCarloEngine,
)


class ActivityProtocol(Protocol):
    """Protocol for activity-like objects."""

    id: UUID
    duration: int


class DependencyProtocol(Protocol):
    """Protocol for dependency-like objects."""

    predecessor_id: UUID
    successor_id: UUID
    dependency_type: str
    lag: int


@dataclass
class NetworkSimulationInput:
    """Input for network-aware Monte Carlo simulation.

    Attributes:
        activities: List of activities with id and duration
        dependencies: List of dependencies between activities
        duration_distributions: Map of activity ID to distribution params
        iterations: Number of simulation iterations
        seed: Optional random seed for reproducibility
    """

    activities: list[ActivityProtocol]
    dependencies: list[DependencyProtocol]
    duration_distributions: dict[UUID, DistributionParams]
    iterations: int = 1000
    seed: int | None = None


@dataclass
class NetworkSimulationOutput:
    """Output from network-aware Monte Carlo simulation.

    Attributes:
        project_duration_samples: Raw samples of project duration
        project_duration_p10-p90: Duration percentiles
        project_duration_mean/std: Duration statistics
        activity_criticality: % of iterations each activity was critical
        activity_finish_distributions: Finish date stats per activity
        sensitivity: Correlation of each activity with project duration
        iterations: Number of iterations completed
        elapsed_seconds: Computation time
    """

    # Project duration distribution
    project_duration_samples: NDArray[np.float64]
    project_duration_p10: float
    project_duration_p50: float
    project_duration_p80: float
    project_duration_p90: float
    project_duration_mean: float
    project_duration_std: float
    project_duration_min: float
    project_duration_max: float

    # Activity criticality (% of iterations on critical path)
    activity_criticality: dict[UUID, float] = field(default_factory=dict)

    # Finish date distribution by activity
    activity_finish_distributions: dict[UUID, dict[str, float]] = field(default_factory=dict)

    # Sensitivity (correlation with project duration)
    sensitivity: dict[UUID, float] = field(default_factory=dict)

    # Histogram data
    duration_histogram_bins: NDArray[np.float64] | None = None
    duration_histogram_counts: NDArray[np.int64] | None = None

    # Metadata
    iterations: int = 0
    elapsed_seconds: float = 0.0
    seed: int | None = None


@dataclass
class SimulatedActivity:
    """Activity with simulated duration for CPM calculation."""

    id: UUID
    duration: int

    def __init__(self, id: UUID, duration: float | int) -> None:
        """Initialize simulated activity."""
        self.id = id
        # Convert float to int, ensuring non-negative
        self.duration = max(0, round(duration)) if isinstance(duration, float) else max(0, duration)


class NetworkMonteCarloEngine:
    """
    Monte Carlo simulation through CPM network.

    For each iteration:
    1. Sample durations from distributions
    2. Run CPM forward pass with sampled durations
    3. Record project finish and critical path
    4. Aggregate statistics across iterations

    Uses vectorized NumPy operations where possible for performance.

    Example usage:
        engine = NetworkMonteCarloEngine(seed=42)
        output = engine.simulate(NetworkSimulationInput(
            activities=activities,
            dependencies=dependencies,
            duration_distributions={
                act.id: DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0, mode=10.0, max_value=20.0
                )
                for act in activities
            },
            iterations=1000
        ))
        print(f"P80 Duration: {output.project_duration_p80}")
        print(f"Activity A criticality: {output.activity_criticality[a_id]}%")
    """

    def __init__(self, seed: int | None = None) -> None:
        """Initialize network Monte Carlo engine.

        Args:
            seed: Optional random seed for reproducibility
        """
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.base_engine = MonteCarloEngine(seed)

    def simulate(self, input_data: NetworkSimulationInput) -> NetworkSimulationOutput:
        """
        Run Monte Carlo simulation through the network.

        For each iteration, samples activity durations and runs CPM
        to determine actual project duration and critical path.

        Args:
            input_data: Network simulation parameters

        Returns:
            NetworkSimulationOutput with distributions and criticality
        """
        start_time = time.perf_counter()

        iterations = input_data.iterations
        activities = input_data.activities
        dependencies = input_data.dependencies
        distributions = input_data.duration_distributions

        # Build activity index for fast lookup
        activity_ids = [a.id for a in activities]
        n_activities = len(activities)

        # Pre-generate all random samples (vectorized)
        duration_samples = self._generate_all_samples(activities, distributions, iterations)

        # Storage for results
        project_durations = np.zeros(iterations)
        activity_finishes = np.zeros((iterations, n_activities))
        critical_counts = np.zeros(n_activities)

        # Run simulations
        for i in range(iterations):
            # Get durations for this iteration
            iter_durations = duration_samples[i, :]

            # Create simulated activities with sampled durations
            sim_activities = [
                SimulatedActivity(id=activities[j].id, duration=iter_durations[j])
                for j in range(n_activities)
            ]

            # Run CPM
            try:
                engine = CPMEngine(sim_activities, dependencies)  # type: ignore
                results = engine.calculate()

                # Record project duration
                max_ef = max(r.early_finish for r in results.values())
                project_durations[i] = max_ef

                # Record activity finishes and criticality
                for j, activity in enumerate(activities):
                    result = results.get(activity.id)
                    if result:
                        activity_finishes[i, j] = result.early_finish
                        if result.is_critical:
                            critical_counts[j] += 1

            except Exception:
                # If CPM fails, use sum of durations as fallback
                project_durations[i] = np.sum(iter_durations)
                activity_finishes[i, :] = iter_durations

        elapsed = time.perf_counter() - start_time

        # Calculate activity criticality percentages
        activity_criticality = {
            activity_ids[j]: float(critical_counts[j] / iterations * 100)
            for j in range(n_activities)
        }

        # Calculate activity finish distributions
        activity_finish_distributions: dict[UUID, dict[str, float]] = {}
        for j, activity in enumerate(activities):
            finishes = activity_finishes[:, j]
            activity_finish_distributions[activity.id] = {
                "p10": float(np.percentile(finishes, 10)),
                "p50": float(np.percentile(finishes, 50)),
                "p90": float(np.percentile(finishes, 90)),
                "mean": float(np.mean(finishes)),
                "std": float(np.std(finishes)),
                "min": float(np.min(finishes)),
                "max": float(np.max(finishes)),
            }

        # Calculate sensitivity (correlation with project duration)
        sensitivity: dict[UUID, float] = {}
        for j, activity in enumerate(activities):
            # Correlation between activity duration and project duration
            if np.std(duration_samples[:, j]) > 0:
                corr = np.corrcoef(duration_samples[:, j], project_durations)[0, 1]
                sensitivity[activity.id] = float(corr) if not np.isnan(corr) else 0.0
            else:
                sensitivity[activity.id] = 0.0

        # Calculate histogram
        hist_counts, hist_bins = np.histogram(project_durations, bins="auto")

        return NetworkSimulationOutput(
            project_duration_samples=project_durations,
            project_duration_p10=float(np.percentile(project_durations, 10)),
            project_duration_p50=float(np.percentile(project_durations, 50)),
            project_duration_p80=float(np.percentile(project_durations, 80)),
            project_duration_p90=float(np.percentile(project_durations, 90)),
            project_duration_mean=float(np.mean(project_durations)),
            project_duration_std=float(np.std(project_durations)),
            project_duration_min=float(np.min(project_durations)),
            project_duration_max=float(np.max(project_durations)),
            activity_criticality=activity_criticality,
            activity_finish_distributions=activity_finish_distributions,
            sensitivity=sensitivity,
            duration_histogram_bins=hist_bins,
            duration_histogram_counts=hist_counts,
            iterations=iterations,
            elapsed_seconds=elapsed,
            seed=self.seed,
        )

    def _generate_all_samples(
        self,
        activities: list[ActivityProtocol],
        distributions: dict[UUID, DistributionParams],
        iterations: int,
    ) -> NDArray[np.float64]:
        """
        Pre-generate all duration samples.

        Uses vectorized sampling for performance.

        Args:
            activities: List of activities
            distributions: Map of activity ID to distribution params
            iterations: Number of iterations

        Returns:
            Matrix of shape (iterations, n_activities)
        """
        n_activities = len(activities)
        samples = np.zeros((iterations, n_activities))

        for j, activity in enumerate(activities):
            params = distributions.get(activity.id)

            if params:
                # Validate and sample
                params.validate()
                samples[:, j] = self._sample_distribution(params, iterations)
            else:
                # Use base duration if no distribution specified
                samples[:, j] = activity.duration or 0

        return samples

    def _sample_distribution(
        self,
        params: DistributionParams,
        n: int,
    ) -> NDArray[np.float64]:
        """Generate n samples from the specified distribution."""
        if params.distribution == DistributionType.TRIANGULAR:
            # Handle edge case where min == max (constant value)
            if params.min_value == params.max_value:
                return np.full(n, params.min_value)
            return self.rng.triangular(
                left=params.min_value,
                mode=params.mode,
                right=params.max_value,
                size=n,
            )

        elif params.distribution == DistributionType.NORMAL:
            return self.rng.normal(
                loc=params.mean,
                scale=params.std,
                size=n,
            )

        elif params.distribution == DistributionType.UNIFORM:
            return self.rng.uniform(
                low=params.min_value,
                high=params.max_value,
                size=n,
            )

        elif params.distribution == DistributionType.PERT:
            return self._sample_pert(
                params.min_value,  # type: ignore
                params.mode,  # type: ignore
                params.max_value,  # type: ignore
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
        Sample from PERT distribution.

        PERT is a modified beta distribution commonly used in project management.

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

        # Standard PERT shape parameters
        alpha = 1 + lambda_param * (mode - min_val) / range_val
        beta = 1 + lambda_param * (max_val - mode) / range_val

        # Ensure alpha and beta are positive
        alpha = max(alpha, 0.01)
        beta = max(beta, 0.01)

        # Sample from beta distribution and scale to range
        beta_samples = self.rng.beta(alpha, beta, size=n)
        return min_val + beta_samples * range_val
