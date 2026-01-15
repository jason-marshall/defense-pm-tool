"""Unit tests for Monte Carlo simulation engine."""

from uuid import uuid4

import numpy as np
import pytest

from src.services.monte_carlo import (
    DistributionParams,
    DistributionType,
    MonteCarloEngine,
    SimulationInput,
    parse_distribution_params,
)


class TestDistributionParams:
    """Tests for DistributionParams validation."""

    def test_triangular_valid(self):
        """Should validate correct triangular params."""
        params = DistributionParams(
            distribution=DistributionType.TRIANGULAR,
            min_value=5.0,
            mode=10.0,
            max_value=15.0,
        )
        params.validate()  # Should not raise

    def test_triangular_invalid_order(self):
        """Should reject triangular with mode outside range."""
        params = DistributionParams(
            distribution=DistributionType.TRIANGULAR,
            min_value=5.0,
            mode=20.0,  # Greater than max
            max_value=15.0,
        )
        with pytest.raises(ValueError, match="min <= mode <= max"):
            params.validate()

    def test_triangular_missing_params(self):
        """Should reject triangular with missing params."""
        params = DistributionParams(
            distribution=DistributionType.TRIANGULAR,
            min_value=5.0,
            # mode missing
            max_value=15.0,
        )
        with pytest.raises(ValueError, match="requires min_value, mode, and max_value"):
            params.validate()

    def test_normal_valid(self):
        """Should validate correct normal params."""
        params = DistributionParams(
            distribution=DistributionType.NORMAL,
            mean=10.0,
            std=2.0,
        )
        params.validate()  # Should not raise

    def test_normal_negative_std(self):
        """Should reject negative standard deviation."""
        params = DistributionParams(
            distribution=DistributionType.NORMAL,
            mean=10.0,
            std=-2.0,
        )
        with pytest.raises(ValueError, match="non-negative"):
            params.validate()

    def test_uniform_valid(self):
        """Should validate correct uniform params."""
        params = DistributionParams(
            distribution=DistributionType.UNIFORM,
            min_value=5.0,
            max_value=15.0,
        )
        params.validate()  # Should not raise

    def test_pert_valid(self):
        """Should validate correct PERT params."""
        params = DistributionParams(
            distribution=DistributionType.PERT,
            min_value=5.0,
            mode=10.0,
            max_value=20.0,
        )
        params.validate()  # Should not raise


class TestMonteCarloEngine:
    """Tests for MonteCarloEngine."""

    def test_basic_simulation(self):
        """Should complete basic simulation."""
        engine = MonteCarloEngine(seed=42)

        input_data = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0,
                    mode=10.0,
                    max_value=15.0,
                ),
            },
            iterations=100,
        )

        output = engine.simulate(input_data)

        assert output.iterations == 100
        assert output.duration_mean > 0
        assert output.duration_p50 > 0
        assert output.duration_p90 >= output.duration_p50
        assert output.elapsed_seconds > 0

    def test_reproducibility_with_seed(self):
        """Should produce identical results with same seed."""
        engine1 = MonteCarloEngine(seed=42)
        engine2 = MonteCarloEngine(seed=42)

        activity_id = uuid4()
        input_data = SimulationInput(
            activity_durations={
                activity_id: DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0,
                    mode=10.0,
                    max_value=15.0,
                ),
            },
            iterations=100,
        )

        output1 = engine1.simulate(input_data)
        output2 = engine2.simulate(input_data)

        assert output1.duration_mean == output2.duration_mean
        assert output1.duration_p50 == output2.duration_p50
        np.testing.assert_array_equal(output1.duration_samples, output2.duration_samples)

    def test_multiple_activities(self):
        """Should handle multiple activities."""
        engine = MonteCarloEngine(seed=42)

        input_data = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0,
                    mode=10.0,
                    max_value=15.0,
                ),
                uuid4(): DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=3.0,
                    mode=5.0,
                    max_value=8.0,
                ),
                uuid4(): DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=2.0,
                    mode=4.0,
                    max_value=7.0,
                ),
            },
            iterations=1000,
        )

        output = engine.simulate(input_data)

        # Sum of three activities: min ~10, mode ~19, max ~30
        assert output.duration_p50 > 15
        assert output.duration_p50 < 25
        assert output.iterations == 1000

    def test_cost_distributions(self):
        """Should handle cost distributions."""
        engine = MonteCarloEngine(seed=42)

        activity_id = uuid4()
        input_data = SimulationInput(
            activity_durations={
                activity_id: DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0,
                    mode=10.0,
                    max_value=15.0,
                ),
            },
            activity_costs={
                activity_id: DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=1000.0,
                    mode=2000.0,
                    max_value=3500.0,
                ),
            },
            iterations=100,
        )

        output = engine.simulate(input_data)

        assert output.cost_p50 is not None
        assert output.cost_mean is not None
        assert output.cost_p50 > 1000
        assert output.cost_p50 < 3500

    def test_activity_stats(self):
        """Should calculate per-activity statistics when requested."""
        engine = MonteCarloEngine(seed=42)

        activity_id = uuid4()
        input_data = SimulationInput(
            activity_durations={
                activity_id: DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0,
                    mode=10.0,
                    max_value=15.0,
                ),
            },
            iterations=100,
            include_activity_stats=True,
        )

        output = engine.simulate(input_data)

        assert output.activity_stats is not None
        assert str(activity_id) in output.activity_stats

        stats = output.activity_stats[str(activity_id)]
        assert "mean" in stats
        assert "std" in stats
        assert "p10" in stats
        assert "p50" in stats
        assert "p90" in stats

    def test_histogram_generation(self):
        """Should generate histogram data."""
        engine = MonteCarloEngine(seed=42)

        input_data = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0,
                    mode=10.0,
                    max_value=15.0,
                ),
            },
            iterations=100,
        )

        output = engine.simulate(input_data)

        assert output.duration_histogram_bins is not None
        assert output.duration_histogram_counts is not None
        assert len(output.duration_histogram_bins) > 0
        assert sum(output.duration_histogram_counts) == 100

    def test_to_dict(self):
        """Should convert output to dictionary."""
        engine = MonteCarloEngine(seed=42)

        input_data = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0,
                    mode=10.0,
                    max_value=15.0,
                ),
            },
            iterations=100,
        )

        output = engine.simulate(input_data)
        result = output.to_dict()

        assert "duration_results" in result
        assert "iterations" in result
        assert "elapsed_seconds" in result
        assert result["duration_results"]["p50"] > 0


class TestTriangularDistribution:
    """Tests for triangular distribution sampling."""

    def test_triangular_bounds(self):
        """Samples should be within min/max bounds."""
        engine = MonteCarloEngine(seed=42)

        input_data = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0,
                    mode=10.0,
                    max_value=15.0,
                ),
            },
            iterations=1000,
        )

        output = engine.simulate(input_data)

        assert output.duration_min >= 5.0
        assert output.duration_max <= 15.0

    def test_triangular_mode_tendency(self):
        """Mean should be close to (min + mode + max) / 3."""
        engine = MonteCarloEngine(seed=42)

        input_data = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=6.0,
                    mode=10.0,
                    max_value=14.0,
                ),
            },
            iterations=10000,
        )

        output = engine.simulate(input_data)

        # Triangular mean = (min + mode + max) / 3 = 10
        expected_mean = (6.0 + 10.0 + 14.0) / 3
        assert abs(output.duration_mean - expected_mean) < 0.5


class TestPERTDistribution:
    """Tests for PERT distribution sampling."""

    def test_pert_bounds(self):
        """PERT samples should be within bounds."""
        engine = MonteCarloEngine(seed=42)

        input_data = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution=DistributionType.PERT,
                    min_value=5.0,
                    mode=10.0,
                    max_value=20.0,
                ),
            },
            iterations=1000,
        )

        output = engine.simulate(input_data)

        assert output.duration_min >= 5.0
        assert output.duration_max <= 20.0

    def test_pert_weighted_mean(self):
        """PERT mean should be (min + 4*mode + max) / 6."""
        engine = MonteCarloEngine(seed=42)

        input_data = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution=DistributionType.PERT,
                    min_value=5.0,
                    mode=10.0,
                    max_value=20.0,
                ),
            },
            iterations=10000,
        )

        output = engine.simulate(input_data)

        # PERT mean = (min + 4*mode + max) / 6 = (5 + 40 + 20) / 6 = 10.83
        expected_mean = (5.0 + 4 * 10.0 + 20.0) / 6
        assert abs(output.duration_mean - expected_mean) < 0.5


class TestNormalDistribution:
    """Tests for normal distribution sampling."""

    def test_normal_mean_std(self):
        """Normal distribution should match mean and std."""
        engine = MonteCarloEngine(seed=42)

        input_data = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution=DistributionType.NORMAL,
                    mean=100.0,
                    std=10.0,
                ),
            },
            iterations=10000,
        )

        output = engine.simulate(input_data)

        assert abs(output.duration_mean - 100.0) < 1.0
        assert abs(output.duration_std - 10.0) < 1.0


class TestUniformDistribution:
    """Tests for uniform distribution sampling."""

    def test_uniform_bounds(self):
        """Uniform samples should be within bounds."""
        engine = MonteCarloEngine(seed=42)

        input_data = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution=DistributionType.UNIFORM,
                    min_value=5.0,
                    max_value=15.0,
                ),
            },
            iterations=1000,
        )

        output = engine.simulate(input_data)

        assert output.duration_min >= 5.0
        assert output.duration_max <= 15.0

    def test_uniform_mean(self):
        """Uniform mean should be (min + max) / 2."""
        engine = MonteCarloEngine(seed=42)

        input_data = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution=DistributionType.UNIFORM,
                    min_value=0.0,
                    max_value=20.0,
                ),
            },
            iterations=10000,
        )

        output = engine.simulate(input_data)

        expected_mean = (0.0 + 20.0) / 2
        assert abs(output.duration_mean - expected_mean) < 0.5


class TestPerformance:
    """Performance tests for Monte Carlo engine."""

    def test_1000_iterations_under_5_seconds(self):
        """Should complete 1000 iterations in under 5 seconds."""
        engine = MonteCarloEngine(seed=42)

        # Create 50 activities with distributions
        activity_distributions = {
            uuid4(): DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=float(i),
                mode=float(i + 5),
                max_value=float(i + 10),
            )
            for i in range(50)
        }

        input_data = SimulationInput(
            activity_durations=activity_distributions,
            iterations=1000,
        )

        output = engine.simulate(input_data)

        assert output.elapsed_seconds < 5.0
        assert output.iterations == 1000

    def test_large_simulation(self):
        """Should handle larger simulations efficiently."""
        engine = MonteCarloEngine(seed=42)

        # Create 100 activities with distributions
        activity_distributions = {
            uuid4(): DistributionParams(
                distribution=DistributionType.PERT,
                min_value=float(i),
                mode=float(i + 3),
                max_value=float(i + 8),
            )
            for i in range(100)
        }

        input_data = SimulationInput(
            activity_durations=activity_distributions,
            iterations=5000,
        )

        output = engine.simulate(input_data)

        # Should complete in reasonable time
        assert output.elapsed_seconds < 10.0
        assert output.iterations == 5000


class TestParseDistributionParams:
    """Tests for parse_distribution_params helper."""

    def test_parse_triangular(self):
        """Should parse triangular distribution."""
        data = {
            "distribution": "triangular",
            "min": 5,
            "mode": 10,
            "max": 15,
        }
        params = parse_distribution_params(data)

        assert params.distribution == DistributionType.TRIANGULAR
        assert params.min_value == 5
        assert params.mode == 10
        assert params.max_value == 15

    def test_parse_normal(self):
        """Should parse normal distribution."""
        data = {
            "distribution": "normal",
            "mean": 100,
            "std": 10,
        }
        params = parse_distribution_params(data)

        assert params.distribution == DistributionType.NORMAL
        assert params.mean == 100
        assert params.std == 10

    def test_parse_with_alias(self):
        """Should handle min_value/max_value aliases."""
        data = {
            "distribution": "uniform",
            "min_value": 5,
            "max_value": 15,
        }
        params = parse_distribution_params(data)

        assert params.min_value == 5
        assert params.max_value == 15
