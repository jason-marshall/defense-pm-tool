"""Activity correlation modeling for Monte Carlo simulation.

This module provides correlation modeling between activity durations
for more realistic Monte Carlo simulations. Activities often have
correlated durations due to shared resources, similar tasks, or
common risk factors.

Key concepts:
- CorrelationEntry: Explicit correlation between two activities
- CorrelationMatrix: Full correlation matrix with construction methods
- CorrelatedSampler: Generate correlated samples using Cholesky decomposition

Per architecture: Probabilistic Analysis Module correlation modeling.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from scipy import stats


@dataclass
class CorrelationEntry:
    """Correlation between two activities.

    Attributes:
        activity_1_id: First activity UUID
        activity_2_id: Second activity UUID
        correlation: Correlation coefficient (-1.0 to 1.0)
    """

    activity_1_id: UUID
    activity_2_id: UUID
    correlation: float  # -1.0 to 1.0

    def __post_init__(self) -> None:
        """Validate correlation bounds."""
        if not -1.0 <= self.correlation <= 1.0:
            raise ValueError(f"Correlation must be between -1 and 1, got {self.correlation}")


@dataclass
class CorrelationMatrix:
    """Correlation matrix for activities.

    Represents pairwise correlations between all activities in a network.
    The matrix is symmetric with 1.0 on the diagonal (self-correlation).

    Attributes:
        activity_ids: List of activity UUIDs in matrix order
        matrix: NumPy array of shape (n_activities, n_activities)
    """

    activity_ids: list[UUID]
    matrix: NDArray[np.float64]  # Shape: (n_activities, n_activities)

    def __post_init__(self) -> None:
        """Validate matrix properties."""
        n = len(self.activity_ids)
        if self.matrix.shape != (n, n):
            raise ValueError(f"Matrix shape {self.matrix.shape} doesn't match {n} activities")

    @classmethod
    def identity(cls, activity_ids: Sequence[UUID]) -> "CorrelationMatrix":
        """Create identity correlation matrix (no correlations).

        Args:
            activity_ids: List of activity UUIDs

        Returns:
            CorrelationMatrix with identity matrix (no cross-correlations)
        """
        n = len(activity_ids)
        return cls(activity_ids=list(activity_ids), matrix=np.eye(n))

    @classmethod
    def from_entries(
        cls,
        activity_ids: Sequence[UUID],
        entries: Sequence[CorrelationEntry],
        default_correlation: float = 0.0,
    ) -> "CorrelationMatrix":
        """Build correlation matrix from explicit correlation entries.

        Args:
            activity_ids: List of activity UUIDs
            entries: List of CorrelationEntry objects
            default_correlation: Default off-diagonal correlation (0.0 = independent)

        Returns:
            CorrelationMatrix with specified correlations
        """
        n = len(activity_ids)
        id_to_idx = {aid: i for i, aid in enumerate(activity_ids)}

        # Initialize with identity plus default correlation
        if default_correlation == 0.0:
            matrix = np.eye(n)
        else:
            matrix = np.full((n, n), default_correlation)
            np.fill_diagonal(matrix, 1.0)

        for entry in entries:
            i = id_to_idx.get(entry.activity_1_id)
            j = id_to_idx.get(entry.activity_2_id)
            if i is not None and j is not None and i != j:
                matrix[i, j] = entry.correlation
                matrix[j, i] = entry.correlation  # Symmetric

        return cls(activity_ids=list(activity_ids), matrix=matrix)

    @classmethod
    def from_wbs_hierarchy(
        cls,
        activity_ids: Sequence[UUID],
        activity_wbs: dict[UUID, str],  # activity_id -> wbs_path
        same_wbs_correlation: float = 0.3,
        sibling_wbs_correlation: float = 0.15,
    ) -> "CorrelationMatrix":
        """Generate correlation matrix based on WBS hierarchy.

        Activities under the same WBS element are positively correlated
        because they often share resources, risks, or dependencies.

        Args:
            activity_ids: List of activity UUIDs
            activity_wbs: Mapping of activity ID to WBS path (e.g., "1.2.3")
            same_wbs_correlation: Correlation for activities in same WBS
            sibling_wbs_correlation: Correlation for sibling WBS elements

        Returns:
            CorrelationMatrix based on WBS structure
        """
        n = len(activity_ids)
        activity_ids_list = list(activity_ids)
        matrix = np.eye(n)

        for i, aid_i in enumerate(activity_ids_list):
            wbs_i = activity_wbs.get(aid_i, "")
            for j, aid_j in enumerate(activity_ids_list):
                if i >= j:
                    continue

                wbs_j = activity_wbs.get(aid_j, "")

                # Check if same WBS
                if wbs_i and wbs_j:
                    if wbs_i == wbs_j:
                        matrix[i, j] = same_wbs_correlation
                        matrix[j, i] = same_wbs_correlation
                    elif _get_parent_wbs(wbs_i) == _get_parent_wbs(wbs_j):
                        # Siblings under same parent
                        matrix[i, j] = sibling_wbs_correlation
                        matrix[j, i] = sibling_wbs_correlation

        return cls(activity_ids=activity_ids_list, matrix=matrix)

    @classmethod
    def from_resource_sharing(
        cls,
        activity_ids: Sequence[UUID],
        activity_resources: dict[UUID, set[str]],  # activity_id -> set of resource names
        shared_resource_correlation: float = 0.4,
    ) -> "CorrelationMatrix":
        """Generate correlation matrix based on shared resources.

        Activities sharing resources tend to have correlated durations
        because delays in one affect availability for others.

        Args:
            activity_ids: List of activity UUIDs
            activity_resources: Mapping of activity ID to set of resource names
            shared_resource_correlation: Correlation for activities sharing resources

        Returns:
            CorrelationMatrix based on resource sharing
        """
        n = len(activity_ids)
        activity_ids_list = list(activity_ids)
        matrix = np.eye(n)

        for i, aid_i in enumerate(activity_ids_list):
            resources_i = activity_resources.get(aid_i, set())
            for j, aid_j in enumerate(activity_ids_list):
                if i >= j:
                    continue

                resources_j = activity_resources.get(aid_j, set())

                # Check for shared resources
                if resources_i and resources_j and resources_i & resources_j:
                    # Scale correlation by number of shared resources
                    shared_count = len(resources_i & resources_j)
                    total_count = len(resources_i | resources_j)
                    correlation = shared_resource_correlation * (shared_count / total_count)
                    matrix[i, j] = correlation
                    matrix[j, i] = correlation

        return cls(activity_ids=activity_ids_list, matrix=matrix)

    def is_positive_definite(self) -> bool:
        """Check if the correlation matrix is positive definite.

        Required for Cholesky decomposition.

        Returns:
            True if matrix is positive definite
        """
        try:
            np.linalg.cholesky(self.matrix)
            return True
        except np.linalg.LinAlgError:
            return False

    def make_positive_definite(self, epsilon: float = 1e-6) -> "CorrelationMatrix":
        """Adjust matrix to ensure positive definiteness.

        Uses eigenvalue adjustment to make matrix positive definite
        while preserving as much of the original structure as possible.

        Args:
            epsilon: Minimum eigenvalue to ensure

        Returns:
            New CorrelationMatrix that is positive definite
        """
        # Eigenvalue decomposition
        eigenvalues, eigenvectors = np.linalg.eigh(self.matrix)

        # Adjust negative eigenvalues
        eigenvalues = np.maximum(eigenvalues, epsilon)

        # Reconstruct matrix
        adjusted = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T

        # Normalize to ensure diagonal is 1.0
        d = np.sqrt(np.diag(adjusted))
        adjusted = adjusted / np.outer(d, d)

        return CorrelationMatrix(activity_ids=self.activity_ids.copy(), matrix=adjusted)

    def get_correlation(self, activity_1_id: UUID, activity_2_id: UUID) -> float:
        """Get correlation between two activities.

        Args:
            activity_1_id: First activity UUID
            activity_2_id: Second activity UUID

        Returns:
            Correlation coefficient

        Raises:
            KeyError: If activity not in matrix
        """
        id_to_idx = {aid: i for i, aid in enumerate(self.activity_ids)}
        i = id_to_idx.get(activity_1_id)
        j = id_to_idx.get(activity_2_id)

        if i is None:
            raise KeyError(f"Activity {activity_1_id} not in correlation matrix")
        if j is None:
            raise KeyError(f"Activity {activity_2_id} not in correlation matrix")

        return float(self.matrix[i, j])


class CorrelatedSampler:
    """Generate correlated random samples using Cholesky decomposition.

    Given a correlation matrix and marginal distributions, produces
    samples that respect both the correlations and distribution shapes.

    The process:
    1. Generate independent standard normal samples
    2. Apply Cholesky transformation to induce correlations
    3. Transform to uniform via normal CDF
    4. Transform to target distributions via inverse CDF

    Example:
        matrix = CorrelationMatrix.from_entries(activity_ids, entries)
        sampler = CorrelatedSampler(matrix, seed=42)
        normals = sampler.generate_correlated_samples(1000)
        samples = sampler.transform_to_distributions(normals, distributions)
    """

    def __init__(
        self,
        correlation_matrix: CorrelationMatrix,
        seed: int | None = None,
    ) -> None:
        """Initialize correlated sampler.

        Args:
            correlation_matrix: Correlation matrix for activities
            seed: Optional random seed for reproducibility
        """
        self.correlation = correlation_matrix
        self.rng = np.random.default_rng(seed)

        # Ensure positive definiteness and compute Cholesky decomposition
        matrix = correlation_matrix.matrix.copy()

        # Add small diagonal for numerical stability
        matrix = matrix + np.eye(len(correlation_matrix.activity_ids)) * 1e-10

        try:
            self.cholesky = np.linalg.cholesky(matrix)
        except np.linalg.LinAlgError:
            # Matrix not positive definite, adjust it
            adjusted = correlation_matrix.make_positive_definite()
            self.cholesky = np.linalg.cholesky(adjusted.matrix)

    def generate_correlated_samples(
        self,
        n_samples: int,
    ) -> NDArray[np.float64]:
        """Generate correlated standard normal samples.

        Args:
            n_samples: Number of samples to generate

        Returns:
            Array of shape (n_samples, n_activities) with
            correlations matching the correlation matrix
        """
        n_activities = len(self.correlation.activity_ids)

        # Generate independent standard normal samples
        independent = self.rng.standard_normal((n_samples, n_activities))

        # Apply Cholesky transformation to induce correlations
        # correlated = independent @ cholesky.T
        correlated = independent @ self.cholesky.T

        return correlated

    def transform_to_distributions(
        self,
        correlated_normals: NDArray[np.float64],
        distributions: dict[UUID, tuple[str, dict]],
    ) -> NDArray[np.float64]:
        """Transform correlated normal samples to target distributions.

        Uses inverse CDF (probability integral transform) to convert
        correlated normal samples to any target distribution while
        preserving the correlation structure.

        Args:
            correlated_normals: Correlated normal samples from generate_correlated_samples
            distributions: Map of activity_id to (dist_type, params)
                - dist_type: "triangular", "normal", "uniform", "pert"
                - params: Distribution parameters dict

        Returns:
            Samples transformed to target distributions
        """
        samples = np.zeros_like(correlated_normals)

        for j, activity_id in enumerate(self.correlation.activity_ids):
            dist_info = distributions.get(activity_id, ("triangular", {}))
            dist_type, params = dist_info

            # Convert normal to uniform via normal CDF
            uniform = stats.norm.cdf(correlated_normals[:, j])

            # Convert uniform to target distribution via inverse CDF
            if dist_type == "triangular":
                min_val = params.get("min_value", 0)
                mode = params.get("mode", 5)
                max_val = params.get("max_value", 10)

                # Handle edge case where min == max
                if max_val <= min_val:
                    samples[:, j] = min_val
                else:
                    c = (mode - min_val) / (max_val - min_val)
                    samples[:, j] = stats.triang.ppf(
                        uniform, c, loc=min_val, scale=max_val - min_val
                    )

            elif dist_type == "normal":
                mean = params.get("mean", 10)
                std = params.get("std", 2)
                samples[:, j] = stats.norm.ppf(uniform, loc=mean, scale=std)

            elif dist_type == "uniform":
                min_val = params.get("min_value", 0)
                max_val = params.get("max_value", 10)

                if max_val <= min_val:
                    samples[:, j] = min_val
                else:
                    samples[:, j] = stats.uniform.ppf(uniform, loc=min_val, scale=max_val - min_val)

            elif dist_type == "pert":
                # PERT uses beta distribution
                min_val = params.get("min_value", 0)
                mode = params.get("mode", 5)
                max_val = params.get("max_value", 10)
                lambda_param = params.get("lambda", 4.0)

                if max_val <= min_val:
                    samples[:, j] = min_val
                else:
                    range_val = max_val - min_val
                    alpha = 1 + lambda_param * (mode - min_val) / range_val
                    beta_param = 1 + lambda_param * (max_val - mode) / range_val

                    # Ensure positive shape parameters
                    alpha = max(alpha, 0.01)
                    beta_param = max(beta_param, 0.01)

                    samples[:, j] = stats.beta.ppf(uniform, alpha, beta_param)
                    samples[:, j] = min_val + samples[:, j] * range_val

            else:
                # Default to uniform [5, 15]
                samples[:, j] = uniform * 10 + 5

        return samples

    def generate_samples(
        self,
        n_samples: int,
        distributions: dict[UUID, tuple[str, dict]],
    ) -> NDArray[np.float64]:
        """Generate correlated samples directly in target distributions.

        Convenience method combining generate_correlated_samples and
        transform_to_distributions.

        Args:
            n_samples: Number of samples to generate
            distributions: Map of activity_id to (dist_type, params)

        Returns:
            Samples in target distributions with specified correlations
        """
        normals = self.generate_correlated_samples(n_samples)
        return self.transform_to_distributions(normals, distributions)


def _get_parent_wbs(wbs_path: str) -> str:
    """Get parent WBS path.

    Args:
        wbs_path: WBS path like "1.2.3"

    Returns:
        Parent path like "1.2" or empty string if no parent
    """
    if "." not in wbs_path:
        return ""
    return wbs_path.rsplit(".", 1)[0]
