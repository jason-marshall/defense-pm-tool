"""Tests for tornado chart data generation."""

from uuid import uuid4

import pytest

from src.services.tornado_chart import (
    TornadoBar,
    TornadoChartData,
    TornadoChartService,
    build_tornado_from_simulation_result,
)


class TestTornadoBar:
    """Tests for TornadoBar dataclass."""

    def test_basic_creation(self):
        """Should create a tornado bar with all fields."""
        bar = TornadoBar(
            activity_id=uuid4(),
            activity_name="Design Phase",
            correlation=0.75,
            low_impact=90.0,
            high_impact=110.0,
            base_value=100.0,
            rank=1,
        )

        assert bar.activity_name == "Design Phase"
        assert bar.correlation == 0.75
        assert bar.rank == 1

    def test_impact_range(self):
        """Should calculate impact range correctly."""
        bar = TornadoBar(
            activity_id=uuid4(),
            activity_name="Test",
            correlation=0.5,
            low_impact=95.0,
            high_impact=105.0,
            base_value=100.0,
            rank=1,
        )

        assert bar.impact_range == 10.0

    def test_is_positive_correlation(self):
        """Should identify positive correlation."""
        pos_bar = TornadoBar(
            activity_id=uuid4(),
            activity_name="Positive",
            correlation=0.5,
            low_impact=95.0,
            high_impact=105.0,
            base_value=100.0,
            rank=1,
        )

        neg_bar = TornadoBar(
            activity_id=uuid4(),
            activity_name="Negative",
            correlation=-0.3,
            low_impact=105.0,
            high_impact=95.0,
            base_value=100.0,
            rank=2,
        )

        assert pos_bar.is_positive_correlation is True
        assert neg_bar.is_positive_correlation is False

    def test_absolute_correlation(self):
        """Should return absolute correlation value."""
        bar = TornadoBar(
            activity_id=uuid4(),
            activity_name="Test",
            correlation=-0.6,
            low_impact=105.0,
            high_impact=95.0,
            base_value=100.0,
            rank=1,
        )

        assert bar.absolute_correlation == 0.6

    def test_impact_direction(self):
        """Should return correct impact direction."""
        pos_bar = TornadoBar(
            activity_id=uuid4(),
            activity_name="Positive",
            correlation=0.5,
            low_impact=95.0,
            high_impact=105.0,
            base_value=100.0,
            rank=1,
        )

        neg_bar = TornadoBar(
            activity_id=uuid4(),
            activity_name="Negative",
            correlation=-0.3,
            low_impact=105.0,
            high_impact=95.0,
            base_value=100.0,
            rank=2,
        )

        assert pos_bar.impact_direction == "direct"
        assert neg_bar.impact_direction == "inverse"


class TestTornadoChartData:
    """Tests for TornadoChartData dataclass."""

    def test_basic_creation(self):
        """Should create chart data with default values."""
        chart = TornadoChartData(
            base_project_duration=100.0,
            bars=[],
            top_drivers_count=0,
        )

        assert chart.base_project_duration == 100.0
        assert len(chart.bars) == 0

    def test_min_max_duration_empty(self):
        """Should return base duration for empty chart."""
        chart = TornadoChartData(
            base_project_duration=100.0,
            bars=[],
            top_drivers_count=0,
        )

        assert chart.min_duration == 100.0
        assert chart.max_duration == 100.0
        assert chart.chart_range == 0.0

    def test_min_max_duration_with_bars(self):
        """Should calculate min/max from bars."""
        bars = [
            TornadoBar(
                activity_id=uuid4(),
                activity_name="A",
                correlation=0.5,
                low_impact=85.0,
                high_impact=115.0,
                base_value=100.0,
                rank=1,
            ),
            TornadoBar(
                activity_id=uuid4(),
                activity_name="B",
                correlation=0.3,
                low_impact=90.0,
                high_impact=110.0,
                base_value=100.0,
                rank=2,
            ),
        ]

        chart = TornadoChartData(
            base_project_duration=100.0,
            bars=bars,
            top_drivers_count=2,
        )

        assert chart.min_duration == 85.0
        assert chart.max_duration == 115.0
        assert chart.chart_range == 30.0

    def test_get_bar_by_activity(self):
        """Should find bar by activity ID."""
        act_id = uuid4()
        bars = [
            TornadoBar(
                activity_id=act_id,
                activity_name="Target",
                correlation=0.5,
                low_impact=95.0,
                high_impact=105.0,
                base_value=100.0,
                rank=1,
            ),
            TornadoBar(
                activity_id=uuid4(),
                activity_name="Other",
                correlation=0.3,
                low_impact=97.0,
                high_impact=103.0,
                base_value=100.0,
                rank=2,
            ),
        ]

        chart = TornadoChartData(
            base_project_duration=100.0,
            bars=bars,
            top_drivers_count=2,
        )

        found = chart.get_bar_by_activity(act_id)
        assert found is not None
        assert found.activity_name == "Target"

        not_found = chart.get_bar_by_activity(uuid4())
        assert not_found is None

    def test_get_top_n(self):
        """Should return top N bars."""
        bars = [
            TornadoBar(
                activity_id=uuid4(),
                activity_name="A",
                correlation=0.8,
                low_impact=92.0,
                high_impact=108.0,
                base_value=100.0,
                rank=1,
            ),
            TornadoBar(
                activity_id=uuid4(),
                activity_name="B",
                correlation=0.6,
                low_impact=94.0,
                high_impact=106.0,
                base_value=100.0,
                rank=2,
            ),
            TornadoBar(
                activity_id=uuid4(),
                activity_name="C",
                correlation=0.4,
                low_impact=96.0,
                high_impact=104.0,
                base_value=100.0,
                rank=3,
            ),
        ]

        chart = TornadoChartData(
            base_project_duration=100.0,
            bars=bars,
            top_drivers_count=3,
        )

        top_2 = chart.get_top_n(2)
        assert len(top_2) == 2
        assert top_2[0].activity_name == "A"
        assert top_2[1].activity_name == "B"


class TestTornadoChartService:
    """Tests for TornadoChartService."""

    def test_generate_basic(self):
        """Should generate tornado chart with sorted bars."""
        a_id, b_id, c_id = uuid4(), uuid4(), uuid4()

        sensitivity = {
            a_id: 0.3,
            b_id: 0.7,  # Highest
            c_id: 0.5,
        }

        activity_names = {
            a_id: "Activity A",
            b_id: "Activity B",
            c_id: "Activity C",
        }

        activity_ranges = {
            a_id: (5, 15),
            b_id: (10, 30),
            c_id: (8, 20),
        }

        service = TornadoChartService(
            sensitivity=sensitivity,
            activity_names=activity_names,
            base_duration=100.0,
            activity_ranges=activity_ranges,
        )

        chart = service.generate(top_n=10)

        assert chart.base_project_duration == 100.0
        assert len(chart.bars) == 3

        # Should be sorted by absolute correlation
        assert chart.bars[0].activity_name == "Activity B"  # 0.7
        assert chart.bars[1].activity_name == "Activity C"  # 0.5
        assert chart.bars[2].activity_name == "Activity A"  # 0.3

    def test_generate_respects_top_n(self):
        """Should limit to top N activities."""
        activities = {uuid4(): 0.1 * i for i in range(1, 11)}
        names = {act_id: f"Activity {i}" for i, act_id in enumerate(activities.keys())}
        ranges = dict.fromkeys(activities.keys(), (5, 15))

        service = TornadoChartService(
            sensitivity=activities,
            activity_names=names,
            base_duration=100.0,
            activity_ranges=ranges,
        )

        chart = service.generate(top_n=5)

        assert len(chart.bars) == 5
        assert chart.top_drivers_count == 5

    def test_generate_positive_correlation(self):
        """Should calculate impact correctly for positive correlation."""
        act_id = uuid4()

        service = TornadoChartService(
            sensitivity={act_id: 0.5},
            activity_names={act_id: "Test"},
            base_duration=100.0,
            activity_ranges={act_id: (10, 30)},  # Range of 20
        )

        chart = service.generate()
        bar = chart.bars[0]

        # Impact = 20 * 0.5 = 10
        # Low = 100 - 5 = 95
        # High = 100 + 5 = 105
        assert bar.low_impact == 95.0
        assert bar.high_impact == 105.0

    def test_generate_negative_correlation(self):
        """Should calculate impact correctly for negative correlation."""
        act_id = uuid4()

        service = TornadoChartService(
            sensitivity={act_id: -0.5},
            activity_names={act_id: "Test"},
            base_duration=100.0,
            activity_ranges={act_id: (10, 30)},  # Range of 20
        )

        chart = service.generate()
        bar = chart.bars[0]

        # Impact = 20 * 0.5 = 10
        # Negative correlation reverses direction
        # Low = 100 + 5 = 105
        # High = 100 - 5 = 95
        assert bar.low_impact == 105.0
        assert bar.high_impact == 95.0

    def test_generate_with_missing_names(self):
        """Should use truncated UUID when name missing."""
        act_id = uuid4()

        service = TornadoChartService(
            sensitivity={act_id: 0.5},
            activity_names={},  # No names provided
            base_duration=100.0,
            activity_ranges={act_id: (10, 20)},
        )

        chart = service.generate()

        # Should use first 8 chars of UUID
        assert len(chart.bars[0].activity_name) == 8

    def test_generate_with_missing_ranges(self):
        """Should handle missing activity ranges."""
        act_id = uuid4()

        service = TornadoChartService(
            sensitivity={act_id: 0.5},
            activity_names={act_id: "Test"},
            base_duration=100.0,
            activity_ranges={},  # No ranges provided
        )

        chart = service.generate()

        # Range of 0 means no impact variation
        assert chart.bars[0].low_impact == 100.0
        assert chart.bars[0].high_impact == 100.0

    def test_generate_ranks_correctly(self):
        """Should assign correct ranks to bars."""
        a_id, b_id, c_id = uuid4(), uuid4(), uuid4()

        service = TornadoChartService(
            sensitivity={a_id: 0.2, b_id: 0.8, c_id: 0.5},
            activity_names={a_id: "A", b_id: "B", c_id: "C"},
            base_duration=100.0,
            activity_ranges={a_id: (5, 15), b_id: (5, 15), c_id: (5, 15)},
        )

        chart = service.generate()

        assert chart.bars[0].rank == 1
        assert chart.bars[0].activity_name == "B"
        assert chart.bars[1].rank == 2
        assert chart.bars[1].activity_name == "C"
        assert chart.bars[2].rank == 3
        assert chart.bars[2].activity_name == "A"

    def test_get_critical_drivers(self):
        """Should return activities above threshold."""
        a_id, b_id, c_id = uuid4(), uuid4(), uuid4()

        service = TornadoChartService(
            sensitivity={a_id: 0.2, b_id: 0.8, c_id: -0.4},
            activity_names={a_id: "A", b_id: "B", c_id: "C"},
            base_duration=100.0,
            activity_ranges={},
        )

        critical = service.get_critical_drivers(threshold=0.3)

        # B (0.8) and C (-0.4) are above 0.3 threshold
        assert len(critical) == 2
        act_ids = [c[0] for c in critical]
        assert b_id in act_ids
        assert c_id in act_ids
        assert a_id not in act_ids

    def test_calculate_cumulative_impact(self):
        """Should calculate combined impact of activities."""
        a_id, b_id = uuid4(), uuid4()

        service = TornadoChartService(
            sensitivity={a_id: 0.6, b_id: 0.8},  # r² = 0.36 + 0.64 = 1.0
            activity_names={a_id: "A", b_id: "B"},
            base_duration=100.0,
            activity_ranges={},
        )

        impact = service.calculate_cumulative_impact([a_id, b_id])

        # 0.6² + 0.8² = 0.36 + 0.64 = 1.0
        assert abs(impact - 1.0) < 0.01


class TestTornadoChartEdgeCases:
    """Edge case tests for tornado chart."""

    def test_empty_sensitivity(self):
        """Should handle empty sensitivity data."""
        service = TornadoChartService(
            sensitivity={},
            activity_names={},
            base_duration=100.0,
            activity_ranges={},
        )

        chart = service.generate()

        assert len(chart.bars) == 0
        assert chart.top_drivers_count == 0

    def test_zero_correlation(self):
        """Should include activities with zero correlation."""
        act_id = uuid4()

        service = TornadoChartService(
            sensitivity={act_id: 0.0},
            activity_names={act_id: "Zero"},
            base_duration=100.0,
            activity_ranges={act_id: (5, 15)},
        )

        chart = service.generate()

        assert len(chart.bars) == 1
        assert chart.bars[0].correlation == 0.0
        assert chart.bars[0].impact_range == 0.0

    def test_very_high_correlation(self):
        """Should handle correlation near 1.0."""
        act_id = uuid4()

        service = TornadoChartService(
            sensitivity={act_id: 0.95},
            activity_names={act_id: "Critical"},
            base_duration=100.0,
            activity_ranges={act_id: (10, 30)},
        )

        chart = service.generate()

        # Impact = 20 * 0.95 = 19
        assert chart.bars[0].impact_range == pytest.approx(19.0, abs=0.1)

    def test_negative_base_duration(self):
        """Should handle negative base duration (edge case)."""
        act_id = uuid4()

        service = TornadoChartService(
            sensitivity={act_id: 0.5},
            activity_names={act_id: "Test"},
            base_duration=-10.0,  # Unusual but test handling
            activity_ranges={act_id: (5, 15)},
        )

        chart = service.generate()

        assert chart.base_project_duration == -10.0

    def test_large_number_of_activities(self):
        """Should handle many activities efficiently."""
        n = 100
        sensitivity = {uuid4(): 0.01 * (i % 100) for i in range(n)}
        names = {act_id: f"Act{i}" for i, act_id in enumerate(sensitivity.keys())}
        ranges = dict.fromkeys(sensitivity.keys(), (5, 15))

        service = TornadoChartService(
            sensitivity=sensitivity,
            activity_names=names,
            base_duration=100.0,
            activity_ranges=ranges,
        )

        chart = service.generate(top_n=20)

        assert len(chart.bars) == 20
        # Bars should be sorted by descending correlation
        for i in range(len(chart.bars) - 1):
            assert chart.bars[i].absolute_correlation >= chart.bars[i + 1].absolute_correlation


class TestBuildTornadoFromSimulationResult:
    """Tests for convenience function."""

    def test_build_from_result(self):
        """Should build chart from simulation result format."""
        act_id = uuid4()

        result = {
            "mean": 100.0,
            "sensitivity": {str(act_id): 0.7},
        }

        activity_names = {act_id: "Test Activity"}

        activity_distributions = {
            str(act_id): {"min_value": 5, "max_value": 15},
        }

        chart = build_tornado_from_simulation_result(
            result=result,
            activity_names=activity_names,
            activity_distributions=activity_distributions,
        )

        assert chart.base_project_duration == 100.0
        assert len(chart.bars) == 1
        assert chart.bars[0].activity_name == "Test Activity"
        assert chart.bars[0].correlation == 0.7

    def test_build_with_missing_sensitivity(self):
        """Should handle missing sensitivity data."""
        result = {
            "mean": 100.0,
            # No sensitivity key
        }

        chart = build_tornado_from_simulation_result(
            result=result,
            activity_names={},
            activity_distributions={},
        )

        assert len(chart.bars) == 0

    def test_build_with_alternative_key_names(self):
        """Should handle alternative key names in distributions."""
        act_id = uuid4()

        result = {
            "mean": 100.0,
            "sensitivity": {str(act_id): 0.5},
        }

        activity_distributions = {
            str(act_id): {"min": 10, "max": 20},  # Alternative keys
        }

        chart = build_tornado_from_simulation_result(
            result=result,
            activity_names={act_id: "Test"},
            activity_distributions=activity_distributions,
        )

        # Should use 'min' and 'max' as fallback
        assert chart.bars[0].impact_range > 0
