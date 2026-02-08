"""Optimized Monte Carlo simulation with vectorized CPM.

This module provides a high-performance Monte Carlo simulation engine
that uses vectorized operations to achieve <5s for 1000 iterations.

Key optimizations:
1. Pre-compute network topology once (adjacency matrix, topological order)
2. Vectorize forward pass across all iterations using NumPy
3. Avoid Python loops where possible
4. Use NumPy broadcasting for parallel computation

The optimization avoids creating a new CPMEngine for each iteration,
instead performing the forward pass using matrix operations.
"""

import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

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
class OptimizedNetworkSimulationOutput:
    """Output from optimized network Monte Carlo simulation.

    Attributes:
        project_duration_samples: Raw samples of project duration
        project_duration_p10-p90: Duration percentiles
        project_duration_mean/std: Duration statistics
        activity_criticality: % of iterations each activity was critical
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


class OptimizedNetworkMonteCarloEngine:
    """
    Optimized Monte Carlo simulation with vectorized operations.

    Key optimizations over standard NetworkMonteCarloEngine:
    1. Pre-compute network topology once (O(1) per iteration instead of O(n))
    2. Vectorized forward pass across iterations (NumPy broadcasting)
    3. Avoid creating CPMEngine objects per iteration
    4. Use adjacency matrix instead of graph library

    Performance target: <5s for 1000 iterations with 100 activities.

    Example usage:
        engine = OptimizedNetworkMonteCarloEngine(seed=42)
        output = engine.simulate(
            activities=activities,
            dependencies=dependencies,
            distributions=distributions,
            iterations=1000,
        )
        print(f"P80 Duration: {output.project_duration_p80}")
        print(f"Elapsed: {output.elapsed_seconds:.3f}s")
    """

    def __init__(self, seed: int | None = None) -> None:
        """Initialize optimized network Monte Carlo engine.

        Args:
            seed: Optional random seed for reproducibility
        """
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.base_engine = MonteCarloEngine(seed)

    def simulate(
        self,
        activities: Sequence[ActivityProtocol],
        dependencies: Sequence[DependencyProtocol],
        distributions: dict[UUID, DistributionParams],
        iterations: int = 1000,
    ) -> OptimizedNetworkSimulationOutput:
        """
        Run optimized Monte Carlo simulation.

        Uses vectorized CPM forward pass for better performance.

        Args:
            activities: List of activities with id and duration
            dependencies: List of dependencies between activities
            distributions: Map of activity ID to distribution params
            iterations: Number of simulation iterations

        Returns:
            OptimizedNetworkSimulationOutput with distributions and metrics
        """
        start_time = time.perf_counter()

        n_activities = len(activities)
        activity_ids = [a.id for a in activities]
        activity_index = {aid: i for i, aid in enumerate(activity_ids)}

        # Pre-generate all random samples (vectorized)
        # Shape: (iterations, n_activities)
        duration_samples = self._generate_all_samples(activities, distributions, iterations)

        # Build adjacency structures for network
        # predecessor_matrix[i, j] = True if j is predecessor of i
        # lag_matrix[i, j] = lag from j to i
        predecessor_matrix = np.zeros((n_activities, n_activities), dtype=bool)
        lag_matrix = np.zeros((n_activities, n_activities), dtype=np.float64)

        for dep in dependencies:
            # Currently only support FS (Finish-to-Start) for vectorized version
            if dep.dependency_type == "FS":
                pred_idx = activity_index.get(dep.predecessor_id)
                succ_idx = activity_index.get(dep.successor_id)
                if pred_idx is not None and succ_idx is not None:
                    predecessor_matrix[succ_idx, pred_idx] = True
                    lag_matrix[succ_idx, pred_idx] = dep.lag

        # Compute topological order once
        topo_order = self._topological_sort(predecessor_matrix)

        # Vectorized forward pass - compute all iterations at once
        # early_finish[iter, activity] = early finish for that activity
        early_finish = self._vectorized_forward_pass(
            duration_samples, predecessor_matrix, lag_matrix, topo_order, iterations
        )

        # Project duration = max early finish per iteration
        project_durations = np.max(early_finish, axis=1)

        # Calculate criticality using vectorized approach
        # An activity is critical if it's on the longest path
        activity_criticality = self._calculate_criticality_vectorized(
            early_finish,
            duration_samples,
            predecessor_matrix,
            project_durations,
            activity_ids,
            iterations,
        )

        # Calculate activity finish distributions
        activity_finish_distributions = self._calculate_finish_distributions(
            early_finish, activity_ids
        )

        # Calculate sensitivity (correlation with project duration)
        sensitivity = self._calculate_sensitivity(duration_samples, project_durations, activity_ids)

        # Calculate histogram
        hist_counts, hist_bins = np.histogram(project_durations, bins="auto")

        elapsed = time.perf_counter() - start_time

        return OptimizedNetworkSimulationOutput(
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
        activities: Sequence[ActivityProtocol],
        distributions: dict[UUID, DistributionParams],
        iterations: int,
    ) -> NDArray[np.float64]:
        """Pre-generate all duration samples (vectorized).

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
                params.validate()
                samples[:, j] = self._sample_distribution(params, iterations)
            else:
                samples[:, j] = activity.duration or 0

        return samples

    def _topological_sort(self, predecessor_matrix: NDArray[np.bool_]) -> list[int]:
        """Compute topological order using Kahn's algorithm.

        Args:
            predecessor_matrix: Boolean matrix where [i,j]=True means j precedes i

        Returns:
            List of activity indices in topological order
        """
        in_degree = predecessor_matrix.sum(axis=1).astype(int)
        queue = list(np.where(in_degree == 0)[0])
        order = []

        while queue:
            node = queue.pop(0)
            order.append(node)

            # Find successors (rows where this node is a predecessor)
            successors = np.where(predecessor_matrix[:, node])[0]

            for succ in successors:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        return order

    def _vectorized_forward_pass(
        self,
        duration_samples: NDArray[np.float64],
        predecessor_matrix: NDArray[np.bool_],
        lag_matrix: NDArray[np.float64],
        topo_order: list[int],
        iterations: int,
    ) -> NDArray[np.float64]:
        """Perform vectorized forward pass for all iterations.

        This is the key optimization - instead of running CPM for each
        iteration, we compute the forward pass for all iterations at once
        using NumPy broadcasting.

        Args:
            duration_samples: Shape (iterations, n_activities)
            predecessor_matrix: Shape (n_activities, n_activities)
            lag_matrix: Shape (n_activities, n_activities)
            topo_order: Activities in topological order
            iterations: Number of iterations

        Returns:
            Early finish times, shape (iterations, n_activities)
        """
        n_activities = duration_samples.shape[1]
        early_finish = np.zeros((iterations, n_activities))

        for act_idx in topo_order:
            # Get all predecessors of this activity
            pred_indices = np.where(predecessor_matrix[act_idx])[0]

            if len(pred_indices) == 0:
                # No predecessors - starts at 0
                early_start = np.zeros(iterations)
            else:
                # For FS dependencies: ES = max(EF of predecessors + lag)
                # Shape: (iterations, n_predecessors)
                pred_ef = early_finish[:, pred_indices]
                pred_lags = lag_matrix[act_idx, pred_indices]

                # Add lags and take max across predecessors
                early_start = np.max(pred_ef + pred_lags, axis=1)

            # Early finish = early start + duration
            early_finish[:, act_idx] = early_start + duration_samples[:, act_idx]

        return early_finish

    def _calculate_criticality_vectorized(
        self,
        early_finish: NDArray[np.float64],
        duration_samples: NDArray[np.float64],
        predecessor_matrix: NDArray[np.bool_],
        project_durations: NDArray[np.float64],
        activity_ids: list[UUID],
        iterations: int,
    ) -> dict[UUID, float]:
        """Calculate activity criticality using vectorized operations.

        An activity is critical if it's on the longest path from start to end.
        We use a simplified approach: activities whose early finish equals
        project duration are on the critical path to the end.

        Args:
            early_finish: Shape (iterations, n_activities)
            duration_samples: Shape (iterations, n_activities)
            predecessor_matrix: Shape (n_activities, n_activities)
            project_durations: Shape (iterations,)
            activity_ids: List of activity UUIDs
            iterations: Number of iterations

        Returns:
            Dict mapping activity ID to criticality percentage
        """
        n_activities = len(activity_ids)
        critical_counts = np.zeros(n_activities)

        # Calculate early start for each activity
        early_start = early_finish - duration_samples

        # For each iteration, find activities on critical path
        for iter_idx in range(iterations):
            proj_dur = project_durations[iter_idx]
            ef_iter = early_finish[iter_idx]
            es_iter = early_start[iter_idx]

            # Find activities that finish at project end (end of critical path)
            final_activities = np.where(np.abs(ef_iter - proj_dur) < 0.001)[0]

            # Trace back through critical path
            visited = set()
            stack = list(final_activities)

            while stack:
                act_idx = stack.pop()
                if act_idx in visited:
                    continue
                visited.add(act_idx)
                critical_counts[act_idx] += 1

                # Find critical predecessors
                # A predecessor is critical if its EF + lag = this activity's ES
                pred_indices = np.where(predecessor_matrix[act_idx])[0]
                my_es = es_iter[act_idx]

                for pred_idx in pred_indices:
                    pred_ef = ef_iter[pred_idx]
                    # Check if predecessor is on critical path to this activity
                    if abs(pred_ef - my_es) < 0.001:
                        stack.append(pred_idx)

        # Convert to percentages
        return {
            activity_ids[j]: float(critical_counts[j] / iterations * 100)
            for j in range(n_activities)
        }

    def _calculate_finish_distributions(
        self,
        early_finish: NDArray[np.float64],
        activity_ids: list[UUID],
    ) -> dict[UUID, dict[str, float]]:
        """Calculate finish date distributions for each activity.

        Args:
            early_finish: Shape (iterations, n_activities)
            activity_ids: List of activity UUIDs

        Returns:
            Dict mapping activity ID to distribution statistics
        """
        distributions: dict[UUID, dict[str, float]] = {}

        for j, act_id in enumerate(activity_ids):
            finishes = early_finish[:, j]
            distributions[act_id] = {
                "p10": float(np.percentile(finishes, 10)),
                "p50": float(np.percentile(finishes, 50)),
                "p90": float(np.percentile(finishes, 90)),
                "mean": float(np.mean(finishes)),
                "std": float(np.std(finishes)),
                "min": float(np.min(finishes)),
                "max": float(np.max(finishes)),
            }

        return distributions

    def _calculate_sensitivity(
        self,
        duration_samples: NDArray[np.float64],
        project_durations: NDArray[np.float64],
        activity_ids: list[UUID],
    ) -> dict[UUID, float]:
        """Calculate sensitivity (correlation with project duration).

        Args:
            duration_samples: Shape (iterations, n_activities)
            project_durations: Shape (iterations,)
            activity_ids: List of activity UUIDs

        Returns:
            Dict mapping activity ID to correlation coefficient
        """
        sensitivity: dict[UUID, float] = {}

        for j, act_id in enumerate(activity_ids):
            act_durations = duration_samples[:, j]
            if np.std(act_durations) > 0:
                corr_matrix = np.corrcoef(act_durations, project_durations)
                corr = corr_matrix[0, 1]
                sensitivity[act_id] = float(corr) if not np.isnan(corr) else 0.0
            else:
                sensitivity[act_id] = 0.0

        return sensitivity

    def _sample_distribution(
        self,
        params: DistributionParams,
        n: int,
    ) -> NDArray[np.float64]:
        """Generate n samples from the specified distribution.

        Note: params.validate() must be called before this method to ensure
        required parameters are not None.

        Args:
            params: Distribution parameters
            n: Number of samples

        Returns:
            Array of n samples
        """
        if params.distribution == DistributionType.TRIANGULAR:
            if params.min_value is None or params.mode is None or params.max_value is None:
                raise ValueError("TRIANGULAR requires min_value, mode, and max_value")
            if params.min_value == params.max_value:
                return np.full(n, params.min_value)
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
        """Sample from PERT distribution.

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
