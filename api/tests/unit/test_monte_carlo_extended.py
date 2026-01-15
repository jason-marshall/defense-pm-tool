"""Extended unit tests for Monte Carlo service."""

from uuid import uuid4

import numpy as np
import pytest

from src.services.monte_carlo import (
    DistributionParams,
    DistributionType,
    MonteCarloEngine,
    SimulationInput,
    SimulationOutput,
    parse_distribution_params,
)


class TestDistributionParams:
    """Tests for DistributionParams dataclass."""

    def test_triangular_params_valid(self):
        """Should validate triangular parameters."""
        params = DistributionParams(
            distribution=DistributionType.TRIANGULAR,
            min_value=5.0,
            mode=10.0,
            max_value=15.0,
        )
        params.validate()  # Should not raise

    def test_triangular_params_invalid_order(self):
        """Should reject invalid triangular parameter order."""
        params = DistributionParams(
            distribution=DistributionType.TRIANGULAR,
            min_value=15.0,  # Greater than mode
            mode=10.0,
            max_value=20.0,
        )
        with pytest.raises(ValueError, match="min <= mode <= max"):
            params.validate()

    def test_triangular_params_missing(self):
        """Should reject missing triangular parameters."""
        params = DistributionParams(
            distribution=DistributionType.TRIANGULAR,
            min_value=5.0,
            # mode is missing
            max_value=15.0,
        )
        with pytest.raises(ValueError, match="requires min_value, mode, and max_value"):
            params.validate()

    def test_pert_params_valid(self):
        """Should validate PERT parameters."""
        params = DistributionParams(
            distribution=DistributionType.PERT,
            min_value=5.0,
            mode=10.0,
            max_value=25.0,
        )
        params.validate()  # Should not raise

    def test_pert_params_missing(self):
        """Should reject missing PERT parameters."""
        params = DistributionParams(
            distribution=DistributionType.PERT,
            min_value=5.0,
            max_value=25.0,
            # mode is missing
        )
        with pytest.raises(ValueError, match="requires min_value, mode, and max_value"):
            params.validate()

    def test_normal_params_valid(self):
        """Should validate normal parameters."""
        params = DistributionParams(
            distribution=DistributionType.NORMAL,
            mean=100.0,
            std=10.0,
        )
        params.validate()  # Should not raise

    def test_normal_params_negative_std(self):
        """Should reject negative standard deviation."""
        params = DistributionParams(
            distribution=DistributionType.NORMAL,
            mean=100.0,
            std=-5.0,
        )
        with pytest.raises(ValueError, match="non-negative"):
            params.validate()

    def test_normal_params_missing(self):
        """Should reject missing normal parameters."""
        params = DistributionParams(
            distribution=DistributionType.NORMAL,
            mean=100.0,
            # std is missing
        )
        with pytest.raises(ValueError, match="requires mean and std"):
            params.validate()

    def test_uniform_params_valid(self):
        """Should validate uniform parameters."""
        params = DistributionParams(
            distribution=DistributionType.UNIFORM,
            min_value=0.0,
            max_value=100.0,
        )
        params.validate()  # Should not raise

    def test_uniform_params_invalid_order(self):
        """Should reject invalid uniform parameter order."""
        params = DistributionParams(
            distribution=DistributionType.UNIFORM,
            min_value=100.0,
            max_value=0.0,  # Less than min
        )
        with pytest.raises(ValueError, match="min_value must be <= max_value"):
            params.validate()

    def test_uniform_params_missing(self):
        """Should reject missing uniform parameters."""
        params = DistributionParams(
            distribution=DistributionType.UNIFORM,
            min_value=0.0,
            # max_value is missing
        )
        with pytest.raises(ValueError, match="requires min_value and max_value"):
            params.validate()


class TestMonteCarloEngineInit:
    """Tests for MonteCarloEngine initialization."""

    def test_engine_init_default(self):
        """Should initialize with no seed."""
        engine = MonteCarloEngine()
        assert engine.seed is None

    def test_engine_init_with_seed(self):
        """Should initialize with seed."""
        engine = MonteCarloEngine(seed=42)
        assert engine.seed == 42


class TestMonteCarloEngineSimulate:
    """Tests for MonteCarloEngine.simulate method."""

    def test_simulate_triangular(self):
        """Should simulate with triangular distribution."""
        engine = MonteCarloEngine(seed=42)
        activity_id = uuid4()

        input_data = SimulationInput(
            activity_durations={
                activity_id: DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0,
                    mode=10.0,
                    max_value=20.0,
                )
            },
            iterations=1000,
        )

        output = engine.simulate(input_data)

        assert output.iterations == 1000
        assert len(output.duration_samples) == 1000
        assert all(5 <= s <= 20 for s in output.duration_samples)
        assert output.duration_p50 > 0

    def test_simulate_normal(self):
        """Should simulate with normal distribution."""
        engine = MonteCarloEngine(seed=42)
        activity_id = uuid4()

        input_data = SimulationInput(
            activity_durations={
                activity_id: DistributionParams(
                    distribution=DistributionType.NORMAL,
                    mean=100.0,
                    std=10.0,
                )
            },
            iterations=1000,
        )

        output = engine.simulate(input_data)

        # Mean should be around 100
        assert 90 <= output.duration_mean <= 110

    def test_simulate_uniform(self):
        """Should simulate with uniform distribution."""
        engine = MonteCarloEngine(seed=42)
        activity_id = uuid4()

        input_data = SimulationInput(
            activity_durations={
                activity_id: DistributionParams(
                    distribution=DistributionType.UNIFORM,
                    min_value=0.0,
                    max_value=100.0,
                )
            },
            iterations=1000,
        )

        output = engine.simulate(input_data)

        assert all(0 <= s <= 100 for s in output.duration_samples)
        # Uniform mean should be around 50
        assert 40 <= output.duration_mean <= 60

    def test_simulate_pert(self):
        """Should simulate with PERT distribution."""
        engine = MonteCarloEngine(seed=42)
        activity_id = uuid4()

        input_data = SimulationInput(
            activity_durations={
                activity_id: DistributionParams(
                    distribution=DistributionType.PERT,
                    min_value=5.0,
                    mode=10.0,
                    max_value=25.0,
                )
            },
            iterations=1000,
        )

        output = engine.simulate(input_data)

        assert all(5 <= s <= 25 for s in output.duration_samples)

    def test_simulate_multiple_activities(self):
        """Should simulate multiple activities."""
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
            },
            iterations=1000,
        )

        output = engine.simulate(input_data)

        # Total should be sum of two activities
        # Minimum sum: 5 + 3 = 8
        # Maximum sum: 15 + 8 = 23
        assert output.duration_min >= 8
        assert output.duration_max <= 23

    def test_simulate_with_cost(self):
        """Should simulate with cost distributions."""
        engine = MonteCarloEngine(seed=42)
        activity_id = uuid4()

        input_data = SimulationInput(
            activity_durations={
                activity_id: DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0,
                    mode=10.0,
                    max_value=15.0,
                )
            },
            activity_costs={
                activity_id: DistributionParams(
                    distribution=DistributionType.NORMAL,
                    mean=1000.0,
                    std=100.0,
                )
            },
            iterations=1000,
        )

        output = engine.simulate(input_data)

        assert output.cost_samples is not None
        assert len(output.cost_samples) == 1000
        assert output.cost_p50 is not None
        assert 900 <= output.cost_mean <= 1100

    def test_simulate_with_activity_stats(self):
        """Should calculate per-activity statistics."""
        engine = MonteCarloEngine(seed=42)
        activity_id = uuid4()

        input_data = SimulationInput(
            activity_durations={
                activity_id: DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0,
                    mode=10.0,
                    max_value=15.0,
                )
            },
            iterations=1000,
            include_activity_stats=True,
        )

        output = engine.simulate(input_data)

        assert output.activity_stats is not None
        assert str(activity_id) in output.activity_stats
        stats = output.activity_stats[str(activity_id)]
        assert "mean" in stats
        assert "std" in stats
        assert "p50" in stats
        assert "p90" in stats

    def test_simulate_with_input_seed(self):
        """Should use seed from input."""
        engine = MonteCarloEngine()  # No seed
        activity_id = uuid4()

        input_data = SimulationInput(
            activity_durations={
                activity_id: DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=5.0,
                    mode=10.0,
                    max_value=15.0,
                )
            },
            iterations=100,
            seed=42,
        )

        output1 = engine.simulate(input_data)
        output2 = engine.simulate(input_data)

        np.testing.assert_array_equal(output1.duration_samples, output2.duration_samples)


class TestMonteCarloEnginePertEdgeCases:
    """Tests for PERT distribution edge cases."""

    def test_pert_zero_range(self):
        """Should handle zero range (min=max)."""
        engine = MonteCarloEngine(seed=42)
        activity_id = uuid4()

        input_data = SimulationInput(
            activity_durations={
                activity_id: DistributionParams(
                    distribution=DistributionType.PERT,
                    min_value=10.0,
                    mode=10.0,
                    max_value=10.0,
                )
            },
            iterations=100,
        )

        output = engine.simulate(input_data)

        # All samples should be 10
        assert all(s == 10.0 for s in output.duration_samples)

    def test_pert_mode_at_min(self):
        """Should handle mode at minimum."""
        engine = MonteCarloEngine(seed=42)
        activity_id = uuid4()

        input_data = SimulationInput(
            activity_durations={
                activity_id: DistributionParams(
                    distribution=DistributionType.PERT,
                    min_value=5.0,
                    mode=5.0,
                    max_value=15.0,
                )
            },
            iterations=1000,
        )

        output = engine.simulate(input_data)

        assert all(5 <= s <= 15 for s in output.duration_samples)

    def test_pert_mode_at_max(self):
        """Should handle mode at maximum."""
        engine = MonteCarloEngine(seed=42)
        activity_id = uuid4()

        input_data = SimulationInput(
            activity_durations={
                activity_id: DistributionParams(
                    distribution=DistributionType.PERT,
                    min_value=5.0,
                    mode=15.0,
                    max_value=15.0,
                )
            },
            iterations=1000,
        )

        output = engine.simulate(input_data)

        assert all(5 <= s <= 15 for s in output.duration_samples)


class TestSimulationOutput:
    """Tests for SimulationOutput dataclass."""

    def test_to_dict_basic(self):
        """Should convert to dict with duration results."""
        output = SimulationOutput(
            duration_samples=np.array([1.0, 2.0, 3.0]),
            duration_p10=1.0,
            duration_p50=2.0,
            duration_p80=2.5,
            duration_p90=3.0,
            duration_mean=2.0,
            duration_std=0.8,
            duration_min=1.0,
            duration_max=3.0,
            iterations=3,
            elapsed_seconds=0.01,
        )

        result = output.to_dict()

        assert "duration_results" in result
        assert result["duration_results"]["p50"] == 2.0
        assert result["iterations"] == 3

    def test_to_dict_with_cost(self):
        """Should include cost results in dict."""
        output = SimulationOutput(
            duration_samples=np.array([1.0, 2.0]),
            duration_p10=1.0,
            duration_p50=1.5,
            duration_p80=1.8,
            duration_p90=2.0,
            duration_mean=1.5,
            duration_std=0.5,
            duration_min=1.0,
            duration_max=2.0,
            cost_samples=np.array([100.0, 200.0]),
            cost_p10=100.0,
            cost_p50=150.0,
            cost_p80=180.0,
            cost_p90=200.0,
            cost_mean=150.0,
            cost_std=50.0,
            cost_min=100.0,
            cost_max=200.0,
            iterations=2,
            elapsed_seconds=0.01,
        )

        result = output.to_dict()

        assert "cost_results" in result
        assert result["cost_results"]["p50"] == 150.0

    def test_to_dict_with_histograms(self):
        """Should include histogram data in dict."""
        output = SimulationOutput(
            duration_samples=np.array([1.0, 2.0]),
            duration_p10=1.0,
            duration_p50=1.5,
            duration_p80=1.8,
            duration_p90=2.0,
            duration_mean=1.5,
            duration_std=0.5,
            duration_min=1.0,
            duration_max=2.0,
            duration_histogram_bins=np.array([0.0, 1.0, 2.0, 3.0]),
            duration_histogram_counts=np.array([0, 1, 1]),
            iterations=2,
            elapsed_seconds=0.01,
        )

        result = output.to_dict()

        assert "duration_histogram" in result
        assert result["duration_histogram"]["bins"] == [0.0, 1.0, 2.0, 3.0]
        assert result["duration_histogram"]["counts"] == [0, 1, 1]

    def test_to_dict_with_activity_stats(self):
        """Should include activity stats in dict."""
        output = SimulationOutput(
            duration_samples=np.array([1.0, 2.0]),
            duration_p10=1.0,
            duration_p50=1.5,
            duration_p80=1.8,
            duration_p90=2.0,
            duration_mean=1.5,
            duration_std=0.5,
            duration_min=1.0,
            duration_max=2.0,
            activity_stats={"activity1": {"mean": 1.5, "std": 0.5}},
            iterations=2,
            elapsed_seconds=0.01,
        )

        result = output.to_dict()

        assert "activity_stats" in result
        assert result["activity_stats"]["activity1"]["mean"] == 1.5

    def test_to_dict_with_seed(self):
        """Should include seed in dict."""
        output = SimulationOutput(
            duration_samples=np.array([1.0]),
            duration_p10=1.0,
            duration_p50=1.0,
            duration_p80=1.0,
            duration_p90=1.0,
            duration_mean=1.0,
            duration_std=0.0,
            duration_min=1.0,
            duration_max=1.0,
            iterations=1,
            elapsed_seconds=0.01,
            seed=42,
        )

        result = output.to_dict()

        assert result["seed"] == 42


class TestParseDistributionParams:
    """Tests for parse_distribution_params function."""

    def test_parse_triangular(self):
        """Should parse triangular distribution params."""
        data = {
            "distribution": "triangular",
            "min": 5,
            "mode": 10,
            "max": 20,
        }

        params = parse_distribution_params(data)

        assert params.distribution == DistributionType.TRIANGULAR
        assert params.min_value == 5
        assert params.mode == 10
        assert params.max_value == 20

    def test_parse_normal(self):
        """Should parse normal distribution params."""
        data = {
            "distribution": "normal",
            "mean": 100,
            "std": 10,
        }

        params = parse_distribution_params(data)

        assert params.distribution == DistributionType.NORMAL
        assert params.mean == 100
        assert params.std == 10

    def test_parse_uniform(self):
        """Should parse uniform distribution params."""
        data = {
            "distribution": "uniform",
            "min": 10,
            "max": 100,
        }

        params = parse_distribution_params(data)

        assert params.distribution == DistributionType.UNIFORM
        assert params.min_value == 10
        assert params.max_value == 100

    def test_parse_pert(self):
        """Should parse PERT distribution params."""
        data = {
            "distribution": "pert",
            "min": 5,
            "mode": 10,
            "max": 25,
        }

        params = parse_distribution_params(data)

        assert params.distribution == DistributionType.PERT
        assert params.min_value == 5
        assert params.mode == 10
        assert params.max_value == 25

    def test_parse_with_min_value_key(self):
        """Should parse with min_value/max_value keys."""
        data = {
            "distribution": "uniform",
            "min_value": 0,
            "max_value": 100,
        }

        params = parse_distribution_params(data)

        assert params.min_value == 0
        assert params.max_value == 100

    def test_parse_uniform_with_zero_min(self):
        """Should correctly parse min=0 (regression test for falsy 0 bug)."""
        data = {
            "distribution": "uniform",
            "min": 0,  # 0 is a valid value and should not be treated as falsy
            "max": 100,
        }

        params = parse_distribution_params(data)

        # This test catches the bug where `data.get("min") or data.get("min_value")`
        # would incorrectly skip 0 because 0 is falsy in Python
        assert params.min_value == 0
        assert params.max_value == 100

    def test_parse_triangular_with_zero_min(self):
        """Should correctly parse triangular with min=0."""
        data = {
            "distribution": "triangular",
            "min": 0,
            "mode": 5,
            "max": 10,
        }

        params = parse_distribution_params(data)

        assert params.min_value == 0
        assert params.mode == 5
        assert params.max_value == 10

    def test_parse_default_distribution(self):
        """Should default to triangular if not specified."""
        data = {
            "min": 5,
            "mode": 10,
            "max": 15,
        }

        params = parse_distribution_params(data)

        assert params.distribution == DistributionType.TRIANGULAR


class TestDistributionType:
    """Tests for DistributionType enum."""

    def test_triangular_value(self):
        """Test triangular distribution type value."""
        assert DistributionType.TRIANGULAR == "triangular"

    def test_pert_value(self):
        """Test PERT distribution type value."""
        assert DistributionType.PERT == "pert"

    def test_normal_value(self):
        """Test normal distribution type value."""
        assert DistributionType.NORMAL == "normal"

    def test_uniform_value(self):
        """Test uniform distribution type value."""
        assert DistributionType.UNIFORM == "uniform"
