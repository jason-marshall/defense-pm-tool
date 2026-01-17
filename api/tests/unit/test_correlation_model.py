"""Tests for activity correlation modeling."""

from uuid import uuid4

import numpy as np
import pytest

from src.services.correlation_model import (
    CorrelatedSampler,
    CorrelationEntry,
    CorrelationMatrix,
    _get_parent_wbs,
)


class TestCorrelationEntry:
    """Tests for CorrelationEntry dataclass."""

    def test_valid_correlation(self):
        """Should accept valid correlations."""
        entry = CorrelationEntry(uuid4(), uuid4(), 0.5)
        assert entry.correlation == 0.5

    def test_correlation_bounds_positive(self):
        """Should accept correlation of 1.0."""
        entry = CorrelationEntry(uuid4(), uuid4(), 1.0)
        assert entry.correlation == 1.0

    def test_correlation_bounds_negative(self):
        """Should accept correlation of -1.0."""
        entry = CorrelationEntry(uuid4(), uuid4(), -1.0)
        assert entry.correlation == -1.0

    def test_correlation_bounds_zero(self):
        """Should accept correlation of 0.0."""
        entry = CorrelationEntry(uuid4(), uuid4(), 0.0)
        assert entry.correlation == 0.0

    def test_invalid_correlation_too_high(self):
        """Should reject correlation > 1.0."""
        with pytest.raises(ValueError, match="Correlation must be between"):
            CorrelationEntry(uuid4(), uuid4(), 1.5)

    def test_invalid_correlation_too_low(self):
        """Should reject correlation < -1.0."""
        with pytest.raises(ValueError, match="Correlation must be between"):
            CorrelationEntry(uuid4(), uuid4(), -1.5)


class TestCorrelationMatrixIdentity:
    """Tests for identity correlation matrix."""

    def test_identity_matrix(self):
        """Should create identity matrix."""
        ids = [uuid4(), uuid4(), uuid4()]
        matrix = CorrelationMatrix.identity(ids)

        assert matrix.matrix.shape == (3, 3)
        np.testing.assert_array_equal(matrix.matrix, np.eye(3))

    def test_identity_single_activity(self):
        """Should handle single activity."""
        ids = [uuid4()]
        matrix = CorrelationMatrix.identity(ids)

        assert matrix.matrix.shape == (1, 1)
        assert matrix.matrix[0, 0] == 1.0


class TestCorrelationMatrixFromEntries:
    """Tests for building matrix from correlation entries."""

    def test_from_entries_basic(self):
        """Should build matrix from correlation entries."""
        a_id, b_id, c_id = uuid4(), uuid4(), uuid4()

        entries = [
            CorrelationEntry(a_id, b_id, 0.5),
            CorrelationEntry(b_id, c_id, 0.3),
        ]

        matrix = CorrelationMatrix.from_entries(
            activity_ids=[a_id, b_id, c_id],
            entries=entries,
        )

        assert matrix.matrix.shape == (3, 3)
        assert matrix.matrix[0, 1] == 0.5  # a-b correlation
        assert matrix.matrix[1, 0] == 0.5  # Symmetric
        assert matrix.matrix[1, 2] == 0.3  # b-c correlation
        assert matrix.matrix[2, 1] == 0.3  # Symmetric
        assert matrix.matrix[0, 0] == 1.0  # Self-correlation
        assert matrix.matrix[1, 1] == 1.0
        assert matrix.matrix[2, 2] == 1.0
        assert matrix.matrix[0, 2] == 0.0  # No correlation specified

    def test_from_entries_with_default_correlation(self):
        """Should apply default correlation to unspecified pairs."""
        a_id, b_id, c_id = uuid4(), uuid4(), uuid4()

        entries = [CorrelationEntry(a_id, b_id, 0.5)]

        matrix = CorrelationMatrix.from_entries(
            activity_ids=[a_id, b_id, c_id],
            entries=entries,
            default_correlation=0.1,
        )

        assert matrix.matrix[0, 1] == 0.5  # Explicit
        assert matrix.matrix[0, 2] == 0.1  # Default
        assert matrix.matrix[1, 2] == 0.1  # Default
        assert matrix.matrix[0, 0] == 1.0  # Diagonal always 1

    def test_from_entries_empty(self):
        """Should handle empty entries."""
        ids = [uuid4(), uuid4()]
        matrix = CorrelationMatrix.from_entries(
            activity_ids=ids,
            entries=[],
        )

        np.testing.assert_array_equal(matrix.matrix, np.eye(2))

    def test_from_entries_unknown_activity(self):
        """Should ignore entries with unknown activities."""
        a_id, b_id = uuid4(), uuid4()
        unknown_id = uuid4()

        entries = [
            CorrelationEntry(a_id, unknown_id, 0.5),  # unknown_id not in list
        ]

        matrix = CorrelationMatrix.from_entries(
            activity_ids=[a_id, b_id],
            entries=entries,
        )

        # Should be identity since entry was ignored
        np.testing.assert_array_equal(matrix.matrix, np.eye(2))

    def test_from_entries_negative_correlation(self):
        """Should handle negative correlations."""
        a_id, b_id = uuid4(), uuid4()

        entries = [CorrelationEntry(a_id, b_id, -0.5)]

        matrix = CorrelationMatrix.from_entries(
            activity_ids=[a_id, b_id],
            entries=entries,
        )

        assert matrix.matrix[0, 1] == -0.5
        assert matrix.matrix[1, 0] == -0.5


class TestCorrelationMatrixFromWBS:
    """Tests for WBS-based correlation generation."""

    def test_from_wbs_hierarchy_same_wbs(self):
        """Should correlate activities in same WBS."""
        a_id, b_id, c_id = uuid4(), uuid4(), uuid4()

        activity_wbs = {
            a_id: "1.1.1",
            b_id: "1.1.1",  # Same as a
            c_id: "1.2.1",  # Different
        }

        matrix = CorrelationMatrix.from_wbs_hierarchy(
            activity_ids=[a_id, b_id, c_id],
            activity_wbs=activity_wbs,
            same_wbs_correlation=0.3,
            sibling_wbs_correlation=0.15,
        )

        # a and b are same WBS
        assert matrix.matrix[0, 1] == 0.3
        assert matrix.matrix[1, 0] == 0.3

        # a and c are NOT siblings (different parent)
        assert matrix.matrix[0, 2] == 0.0

    def test_from_wbs_hierarchy_siblings(self):
        """Should correlate sibling WBS elements."""
        a_id, b_id, c_id, d_id = uuid4(), uuid4(), uuid4(), uuid4()

        activity_wbs = {
            a_id: "1.1.1",
            b_id: "1.1.2",  # Sibling of a
            c_id: "1.1.3",  # Sibling of a and b
            d_id: "1.2.1",  # Different branch
        }

        matrix = CorrelationMatrix.from_wbs_hierarchy(
            activity_ids=[a_id, b_id, c_id, d_id],
            activity_wbs=activity_wbs,
            same_wbs_correlation=0.3,
            sibling_wbs_correlation=0.15,
        )

        # a, b, c are siblings (parent is 1.1)
        assert matrix.matrix[0, 1] == 0.15
        assert matrix.matrix[0, 2] == 0.15
        assert matrix.matrix[1, 2] == 0.15

        # d is not related
        assert matrix.matrix[0, 3] == 0.0
        assert matrix.matrix[1, 3] == 0.0

    def test_from_wbs_hierarchy_missing_wbs(self):
        """Should handle activities without WBS."""
        a_id, b_id = uuid4(), uuid4()

        activity_wbs = {
            a_id: "1.1.1",
            # b_id not in map
        }

        matrix = CorrelationMatrix.from_wbs_hierarchy(
            activity_ids=[a_id, b_id],
            activity_wbs=activity_wbs,
        )

        # No correlation for activities without WBS
        assert matrix.matrix[0, 1] == 0.0


class TestCorrelationMatrixFromResources:
    """Tests for resource-based correlation generation."""

    def test_from_resource_sharing(self):
        """Should correlate activities sharing resources."""
        a_id, b_id, c_id = uuid4(), uuid4(), uuid4()

        activity_resources = {
            a_id: {"engineer_1", "equipment_a"},
            b_id: {"engineer_1"},  # Shares engineer_1 with a
            c_id: {"engineer_2"},  # No shared resources
        }

        matrix = CorrelationMatrix.from_resource_sharing(
            activity_ids=[a_id, b_id, c_id],
            activity_resources=activity_resources,
            shared_resource_correlation=0.4,
        )

        # a and b share 1 of 2 unique resources (engineer_1)
        # correlation = 0.4 * (1/2) = 0.2
        assert abs(matrix.matrix[0, 1] - 0.2) < 0.01

        # a and c share nothing
        assert matrix.matrix[0, 2] == 0.0

    def test_from_resource_sharing_multiple(self):
        """Should scale correlation by shared resource count."""
        a_id, b_id = uuid4(), uuid4()

        activity_resources = {
            a_id: {"r1", "r2", "r3"},
            b_id: {"r1", "r2"},  # Shares 2 of 3 unique resources
        }

        matrix = CorrelationMatrix.from_resource_sharing(
            activity_ids=[a_id, b_id],
            activity_resources=activity_resources,
            shared_resource_correlation=0.6,
        )

        # 2 shared / 3 unique = 2/3
        expected = 0.6 * (2 / 3)
        assert abs(matrix.matrix[0, 1] - expected) < 0.01


class TestCorrelationMatrixValidation:
    """Tests for matrix validation methods."""

    def test_is_positive_definite_identity(self):
        """Identity matrix should be positive definite."""
        matrix = CorrelationMatrix.identity([uuid4(), uuid4()])
        assert matrix.is_positive_definite()

    def test_is_positive_definite_valid(self):
        """Valid correlation matrix should be positive definite."""
        ids = [uuid4(), uuid4()]
        entries = [CorrelationEntry(ids[0], ids[1], 0.5)]
        matrix = CorrelationMatrix.from_entries(ids, entries)
        assert matrix.is_positive_definite()

    def test_make_positive_definite(self):
        """Should make matrix positive definite."""
        ids = [uuid4(), uuid4()]
        # Create a problematic matrix (slightly invalid)
        matrix_array = np.array([[1.0, 0.99], [0.99, 1.0]])
        matrix = CorrelationMatrix(activity_ids=ids, matrix=matrix_array)

        adjusted = matrix.make_positive_definite()
        assert adjusted.is_positive_definite()

    def test_get_correlation(self):
        """Should retrieve correlation between activities."""
        a_id, b_id = uuid4(), uuid4()
        entries = [CorrelationEntry(a_id, b_id, 0.7)]
        matrix = CorrelationMatrix.from_entries([a_id, b_id], entries)

        assert matrix.get_correlation(a_id, b_id) == 0.7
        assert matrix.get_correlation(b_id, a_id) == 0.7
        assert matrix.get_correlation(a_id, a_id) == 1.0

    def test_get_correlation_unknown_activity(self):
        """Should raise KeyError for unknown activity."""
        a_id = uuid4()
        matrix = CorrelationMatrix.identity([a_id])

        with pytest.raises(KeyError):
            matrix.get_correlation(a_id, uuid4())


class TestCorrelatedSampler:
    """Tests for correlated sample generation."""

    def test_generates_correct_shape(self):
        """Should generate samples of correct shape."""
        ids = [uuid4(), uuid4(), uuid4()]
        matrix = CorrelationMatrix.identity(ids)
        sampler = CorrelatedSampler(matrix, seed=42)

        samples = sampler.generate_correlated_samples(100)

        assert samples.shape == (100, 3)

    def test_generates_correlated_samples(self):
        """Should produce samples with expected correlations."""
        a_id, b_id = uuid4(), uuid4()

        entries = [CorrelationEntry(a_id, b_id, 0.7)]

        matrix = CorrelationMatrix.from_entries(
            activity_ids=[a_id, b_id],
            entries=entries,
        )

        sampler = CorrelatedSampler(matrix, seed=42)
        samples = sampler.generate_correlated_samples(10000)

        # Check that empirical correlation is close to specified
        empirical_corr = np.corrcoef(samples[:, 0], samples[:, 1])[0, 1]
        assert abs(empirical_corr - 0.7) < 0.05

    def test_generates_uncorrelated_samples(self):
        """Should produce uncorrelated samples when correlation is 0."""
        ids = [uuid4(), uuid4()]
        matrix = CorrelationMatrix.identity(ids)

        sampler = CorrelatedSampler(matrix, seed=42)
        samples = sampler.generate_correlated_samples(10000)

        empirical_corr = np.corrcoef(samples[:, 0], samples[:, 1])[0, 1]
        assert abs(empirical_corr) < 0.05

    def test_generates_negative_correlation(self):
        """Should produce negatively correlated samples."""
        a_id, b_id = uuid4(), uuid4()

        entries = [CorrelationEntry(a_id, b_id, -0.6)]

        matrix = CorrelationMatrix.from_entries(
            activity_ids=[a_id, b_id],
            entries=entries,
        )

        sampler = CorrelatedSampler(matrix, seed=42)
        samples = sampler.generate_correlated_samples(10000)

        empirical_corr = np.corrcoef(samples[:, 0], samples[:, 1])[0, 1]
        assert abs(empirical_corr - (-0.6)) < 0.05

    def test_reproducible_with_seed(self):
        """Should produce same samples with same seed."""
        ids = [uuid4(), uuid4()]
        entries = [CorrelationEntry(ids[0], ids[1], 0.5)]
        matrix = CorrelationMatrix.from_entries(ids, entries)

        sampler1 = CorrelatedSampler(matrix, seed=42)
        samples1 = sampler1.generate_correlated_samples(100)

        sampler2 = CorrelatedSampler(matrix, seed=42)
        samples2 = sampler2.generate_correlated_samples(100)

        np.testing.assert_array_equal(samples1, samples2)


class TestCorrelatedSamplerTransform:
    """Tests for distribution transformation."""

    def test_transform_to_triangular(self):
        """Should transform to triangular distribution."""
        a_id = uuid4()

        matrix = CorrelationMatrix.from_entries(
            activity_ids=[a_id],
            entries=[],
        )

        sampler = CorrelatedSampler(matrix, seed=42)
        normals = sampler.generate_correlated_samples(10000)

        distributions = {
            a_id: ("triangular", {"min_value": 5, "mode": 10, "max_value": 20}),
        }

        samples = sampler.transform_to_distributions(normals, distributions)

        assert samples.min() >= 5
        assert samples.max() <= 20
        # Mode should be around 10 - check median is reasonable
        assert 8 < np.median(samples) < 12

    def test_transform_to_normal(self):
        """Should transform to normal distribution."""
        a_id = uuid4()

        matrix = CorrelationMatrix.identity([a_id])
        sampler = CorrelatedSampler(matrix, seed=42)
        normals = sampler.generate_correlated_samples(10000)

        distributions = {
            a_id: ("normal", {"mean": 100, "std": 10}),
        }

        samples = sampler.transform_to_distributions(normals, distributions)

        assert abs(np.mean(samples) - 100) < 1
        assert abs(np.std(samples) - 10) < 1

    def test_transform_to_uniform(self):
        """Should transform to uniform distribution."""
        a_id = uuid4()

        matrix = CorrelationMatrix.identity([a_id])
        sampler = CorrelatedSampler(matrix, seed=42)
        normals = sampler.generate_correlated_samples(10000)

        distributions = {
            a_id: ("uniform", {"min_value": 0, "max_value": 100}),
        }

        samples = sampler.transform_to_distributions(normals, distributions)

        assert samples.min() >= 0
        assert samples.max() <= 100
        assert abs(np.mean(samples) - 50) < 2  # Mean of uniform

    def test_transform_to_pert(self):
        """Should transform to PERT distribution."""
        a_id = uuid4()

        matrix = CorrelationMatrix.identity([a_id])
        sampler = CorrelatedSampler(matrix, seed=42)
        normals = sampler.generate_correlated_samples(10000)

        distributions = {
            a_id: ("pert", {"min_value": 5, "mode": 10, "max_value": 20}),
        }

        samples = sampler.transform_to_distributions(normals, distributions)

        assert samples.min() >= 5
        assert samples.max() <= 20
        # PERT mean = (min + 4*mode + max) / 6 = (5 + 40 + 20) / 6 = 10.83
        assert abs(np.mean(samples) - 10.83) < 0.5

    def test_transform_preserves_correlation(self):
        """Transformation should preserve correlation structure."""
        a_id, b_id = uuid4(), uuid4()

        entries = [CorrelationEntry(a_id, b_id, 0.6)]
        matrix = CorrelationMatrix.from_entries([a_id, b_id], entries)

        sampler = CorrelatedSampler(matrix, seed=42)
        normals = sampler.generate_correlated_samples(10000)

        distributions = {
            a_id: ("triangular", {"min_value": 5, "mode": 10, "max_value": 20}),
            b_id: ("normal", {"mean": 50, "std": 5}),
        }

        samples = sampler.transform_to_distributions(normals, distributions)

        # Correlation should be approximately preserved
        # (may not be exactly 0.6 due to non-linear transformation)
        empirical_corr = np.corrcoef(samples[:, 0], samples[:, 1])[0, 1]
        assert empirical_corr > 0.4  # Should still be positive and significant

    def test_transform_handles_edge_case_min_equals_max(self):
        """Should handle case where min equals max."""
        a_id = uuid4()

        matrix = CorrelationMatrix.identity([a_id])
        sampler = CorrelatedSampler(matrix, seed=42)
        normals = sampler.generate_correlated_samples(100)

        distributions = {
            a_id: ("triangular", {"min_value": 10, "mode": 10, "max_value": 10}),
        }

        samples = sampler.transform_to_distributions(normals, distributions)

        # All samples should be the constant value
        np.testing.assert_array_equal(samples, 10)

    def test_generate_samples_convenience(self):
        """Test the convenience method that combines steps."""
        a_id, b_id = uuid4(), uuid4()

        entries = [CorrelationEntry(a_id, b_id, 0.5)]
        matrix = CorrelationMatrix.from_entries([a_id, b_id], entries)

        sampler = CorrelatedSampler(matrix, seed=42)

        distributions = {
            a_id: ("triangular", {"min_value": 5, "mode": 10, "max_value": 20}),
            b_id: ("uniform", {"min_value": 0, "max_value": 50}),
        }

        samples = sampler.generate_samples(1000, distributions)

        assert samples.shape == (1000, 2)
        assert samples[:, 0].min() >= 5
        assert samples[:, 0].max() <= 20
        assert samples[:, 1].min() >= 0
        assert samples[:, 1].max() <= 50


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_parent_wbs_basic(self):
        """Should get parent WBS path."""
        assert _get_parent_wbs("1.2.3") == "1.2"
        assert _get_parent_wbs("1.2") == "1"
        assert _get_parent_wbs("1") == ""

    def test_get_parent_wbs_empty(self):
        """Should handle empty string."""
        assert _get_parent_wbs("") == ""

    def test_get_parent_wbs_long_path(self):
        """Should handle long paths."""
        assert _get_parent_wbs("1.2.3.4.5.6") == "1.2.3.4.5"


class TestCorrelationMatrixValidationError:
    """Tests for validation error handling."""

    def test_invalid_matrix_shape(self):
        """Should reject matrix with wrong shape."""
        ids = [uuid4(), uuid4()]

        with pytest.raises(ValueError, match="Matrix shape"):
            CorrelationMatrix(
                activity_ids=ids,
                matrix=np.eye(3),  # Wrong shape
            )


class TestMultipleCorrelations:
    """Tests for complex correlation scenarios."""

    def test_three_way_correlation(self):
        """Should handle correlations between three activities."""
        a_id, b_id, c_id = uuid4(), uuid4(), uuid4()

        entries = [
            CorrelationEntry(a_id, b_id, 0.5),
            CorrelationEntry(b_id, c_id, 0.4),
            CorrelationEntry(a_id, c_id, 0.3),
        ]

        matrix = CorrelationMatrix.from_entries([a_id, b_id, c_id], entries)
        sampler = CorrelatedSampler(matrix, seed=42)
        samples = sampler.generate_correlated_samples(10000)

        # Check all correlations are approximately correct
        corr_ab = np.corrcoef(samples[:, 0], samples[:, 1])[0, 1]
        corr_bc = np.corrcoef(samples[:, 1], samples[:, 2])[0, 1]
        corr_ac = np.corrcoef(samples[:, 0], samples[:, 2])[0, 1]

        assert abs(corr_ab - 0.5) < 0.1
        assert abs(corr_bc - 0.4) < 0.1
        assert abs(corr_ac - 0.3) < 0.1

    def test_large_correlation_matrix(self):
        """Should handle larger correlation matrices."""
        n = 20
        ids = [uuid4() for _ in range(n)]

        # Create some random correlations
        entries = []
        for i in range(n - 1):
            entries.append(CorrelationEntry(ids[i], ids[i + 1], 0.3))

        matrix = CorrelationMatrix.from_entries(ids, entries)
        assert matrix.is_positive_definite()

        sampler = CorrelatedSampler(matrix, seed=42)
        samples = sampler.generate_correlated_samples(1000)

        assert samples.shape == (1000, n)
