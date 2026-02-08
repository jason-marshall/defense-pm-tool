"""Unit tests for Variance Analysis service."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from src.services.variance_analysis import (
    TrendDirection,
    VarianceAlert,
    VarianceAnalysisResult,
    VarianceAnalysisService,
    VarianceSeverity,
    VarianceThresholds,
    VarianceTrend,
    VarianceType,
)


class TestVarianceType:
    """Tests for VarianceType enum."""

    def test_schedule_variance_type(self):
        """Should have schedule type."""
        assert VarianceType.SCHEDULE.value == "schedule"

    def test_cost_variance_type(self):
        """Should have cost type."""
        assert VarianceType.COST.value == "cost"


class TestVarianceSeverity:
    """Tests for VarianceSeverity enum."""

    def test_severity_levels(self):
        """Should have all severity levels."""
        assert VarianceSeverity.MINOR.value == "minor"
        assert VarianceSeverity.MODERATE.value == "moderate"
        assert VarianceSeverity.SIGNIFICANT.value == "significant"
        assert VarianceSeverity.CRITICAL.value == "critical"


class TestTrendDirection:
    """Tests for TrendDirection enum."""

    def test_trend_directions(self):
        """Should have all trend directions."""
        assert TrendDirection.IMPROVING.value == "improving"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.WORSENING.value == "worsening"


class TestVarianceThresholds:
    """Tests for VarianceThresholds dataclass."""

    def test_default_thresholds(self):
        """Should have correct default values."""
        thresholds = VarianceThresholds()

        assert thresholds.minor_threshold == Decimal("5")
        assert thresholds.moderate_threshold == Decimal("10")
        assert thresholds.significant_threshold == Decimal("15")
        assert thresholds.explanation_required_threshold == Decimal("10")

    def test_custom_thresholds(self):
        """Should accept custom values."""
        thresholds = VarianceThresholds(
            minor_threshold=Decimal("3"),
            moderate_threshold=Decimal("7"),
            significant_threshold=Decimal("12"),
            explanation_required_threshold=Decimal("7"),
        )

        assert thresholds.minor_threshold == Decimal("3")
        assert thresholds.explanation_required_threshold == Decimal("7")


class TestVarianceAlert:
    """Tests for VarianceAlert dataclass."""

    def test_create_alert(self):
        """Should create alert with all fields."""
        wbs_id = uuid4()
        alert = VarianceAlert(
            wbs_id=wbs_id,
            wbs_code="1.2.3",
            wbs_name="Software Development",
            variance_type=VarianceType.COST,
            variance_amount=Decimal("-50000"),
            variance_percent=Decimal("-12.50"),
            severity=VarianceSeverity.SIGNIFICANT,
            period_name="January 2026",
            trend=TrendDirection.WORSENING,
            explanation_required=True,
        )

        assert alert.wbs_id == wbs_id
        assert alert.variance_type == VarianceType.COST
        assert alert.severity == VarianceSeverity.SIGNIFICANT
        assert alert.explanation_required is True

    def test_alert_optional_fields(self):
        """Should handle optional fields."""
        alert = VarianceAlert(
            wbs_id=uuid4(),
            wbs_code="1.2.3",
            wbs_name="Test",
            variance_type=VarianceType.SCHEDULE,
            variance_amount=Decimal("-10000"),
            variance_percent=Decimal("-5.00"),
            severity=VarianceSeverity.MINOR,
            period_name="Test Period",
            trend=TrendDirection.STABLE,
            explanation_required=False,
            existing_explanation="Already explained",
            corrective_action="Action taken",
            expected_resolution=date(2026, 3, 31),
        )

        assert alert.existing_explanation == "Already explained"
        assert alert.corrective_action == "Action taken"
        assert alert.expected_resolution == date(2026, 3, 31)


class TestVarianceTrend:
    """Tests for VarianceTrend dataclass."""

    def test_create_trend(self):
        """Should create trend with all fields."""
        wbs_id = uuid4()
        trend = VarianceTrend(
            wbs_id=wbs_id,
            wbs_code="1.2.3",
            variance_type=VarianceType.COST,
            periods=["Jan 2026", "Feb 2026", "Mar 2026"],
            values=[Decimal("-10000"), Decimal("-15000"), Decimal("-20000")],
            percentages=[Decimal("-5"), Decimal("-7"), Decimal("-9")],
            trend_direction=TrendDirection.WORSENING,
            periods_in_breach=2,
        )

        assert trend.wbs_id == wbs_id
        assert len(trend.periods) == 3
        assert trend.trend_direction == TrendDirection.WORSENING
        assert trend.periods_in_breach == 2


class TestVarianceAnalysisResult:
    """Tests for VarianceAnalysisResult dataclass."""

    def test_create_result(self):
        """Should create result with all fields."""
        program_id = uuid4()
        result = VarianceAnalysisResult(
            program_id=program_id,
            analysis_date=date(2026, 1, 31),
            period_name="January 2026",
            total_wbs_analyzed=50,
            critical_count=2,
            significant_count=5,
            moderate_count=8,
            minor_count=10,
            schedule_variance_count=12,
            cost_variance_count=13,
            explanations_required=7,
            explanations_provided=5,
        )

        assert result.program_id == program_id
        assert result.total_wbs_analyzed == 50
        assert result.critical_count == 2
        assert result.explanations_required == 7

    def test_result_default_lists(self):
        """Should initialize empty lists by default."""
        result = VarianceAnalysisResult(
            program_id=uuid4(),
            analysis_date=date.today(),
            period_name="Test",
            total_wbs_analyzed=0,
        )

        assert result.alerts == []
        assert result.trends == []
        assert result.critical_count == 0


class TestVarianceAnalysisServiceClassifySeverity:
    """Tests for severity classification."""

    def test_classify_minor_variance(self):
        """Should classify variance < 5% as minor."""
        service = VarianceAnalysisService()

        assert service.classify_severity(Decimal("0")) == VarianceSeverity.MINOR
        assert service.classify_severity(Decimal("3")) == VarianceSeverity.MINOR
        assert service.classify_severity(Decimal("-4.9")) == VarianceSeverity.MINOR

    def test_classify_moderate_variance(self):
        """Should classify 5-10% variance as moderate."""
        service = VarianceAnalysisService()

        assert service.classify_severity(Decimal("5")) == VarianceSeverity.MODERATE
        assert service.classify_severity(Decimal("7.5")) == VarianceSeverity.MODERATE
        assert service.classify_severity(Decimal("-9.9")) == VarianceSeverity.MODERATE

    def test_classify_significant_variance(self):
        """Should classify 10-15% variance as significant."""
        service = VarianceAnalysisService()

        assert service.classify_severity(Decimal("10")) == VarianceSeverity.SIGNIFICANT
        assert service.classify_severity(Decimal("12")) == VarianceSeverity.SIGNIFICANT
        assert service.classify_severity(Decimal("-14.9")) == VarianceSeverity.SIGNIFICANT

    def test_classify_critical_variance(self):
        """Should classify > 15% variance as critical."""
        service = VarianceAnalysisService()

        assert service.classify_severity(Decimal("15")) == VarianceSeverity.CRITICAL
        assert service.classify_severity(Decimal("20")) == VarianceSeverity.CRITICAL
        assert service.classify_severity(Decimal("-25")) == VarianceSeverity.CRITICAL

    def test_classify_with_custom_thresholds(self):
        """Should use custom thresholds."""
        thresholds = VarianceThresholds(
            minor_threshold=Decimal("3"),
            moderate_threshold=Decimal("6"),
            significant_threshold=Decimal("10"),
        )
        service = VarianceAnalysisService(thresholds=thresholds)

        assert service.classify_severity(Decimal("2")) == VarianceSeverity.MINOR
        assert service.classify_severity(Decimal("5")) == VarianceSeverity.MODERATE
        assert service.classify_severity(Decimal("8")) == VarianceSeverity.SIGNIFICANT
        assert service.classify_severity(Decimal("12")) == VarianceSeverity.CRITICAL


class TestVarianceAnalysisServiceRequiresExplanation:
    """Tests for explanation requirement check."""

    def test_requires_explanation_above_threshold(self):
        """Should require explanation above 10% threshold."""
        service = VarianceAnalysisService()

        assert service.requires_explanation(Decimal("10")) is True
        assert service.requires_explanation(Decimal("15")) is True
        assert service.requires_explanation(Decimal("-12")) is True

    def test_no_explanation_below_threshold(self):
        """Should not require explanation below 10% threshold."""
        service = VarianceAnalysisService()

        assert service.requires_explanation(Decimal("5")) is False
        assert service.requires_explanation(Decimal("9.9")) is False
        assert service.requires_explanation(Decimal("-8")) is False


class TestVarianceAnalysisServiceDetectVariances:
    """Tests for variance detection."""

    def create_period_data(
        self,
        wbs_code: str,
        bcws: Decimal,
        sv: Decimal,
        cv: Decimal,
    ) -> dict:
        """Create test period data."""
        return {
            "wbs_id": uuid4(),
            "wbs_code": wbs_code,
            "wbs_name": f"WBS {wbs_code}",
            "period_name": "January 2026",
            "cumulative_bcws": bcws,
            "sv": sv,
            "cv": cv,
        }

    def test_detect_no_variances(self):
        """Should return empty list when no significant variances."""
        service = VarianceAnalysisService()
        period_data = [
            self.create_period_data("1.1", Decimal("100000"), Decimal("5000"), Decimal("3000")),
            self.create_period_data("1.2", Decimal("50000"), Decimal("-2000"), Decimal("-1000")),
        ]

        alerts = service.detect_significant_variances(period_data)

        assert len(alerts) == 0

    def test_detect_schedule_variance(self):
        """Should detect significant schedule variance."""
        service = VarianceAnalysisService()
        period_data = [
            self.create_period_data(
                "1.1",
                Decimal("100000"),
                Decimal("-15000"),  # -15% SV
                Decimal("0"),
            ),
        ]

        alerts = service.detect_significant_variances(period_data)

        assert len(alerts) == 1
        assert alerts[0].variance_type == VarianceType.SCHEDULE
        assert alerts[0].variance_percent == Decimal("-15.00")
        assert alerts[0].explanation_required is True

    def test_detect_cost_variance(self):
        """Should detect significant cost variance."""
        service = VarianceAnalysisService()
        period_data = [
            self.create_period_data(
                "1.1",
                Decimal("100000"),
                Decimal("0"),
                Decimal("-12000"),  # -12% CV
            ),
        ]

        alerts = service.detect_significant_variances(period_data)

        assert len(alerts) == 1
        assert alerts[0].variance_type == VarianceType.COST
        assert alerts[0].variance_percent == Decimal("-12.00")

    def test_detect_both_variances(self):
        """Should detect both schedule and cost variances."""
        service = VarianceAnalysisService()
        period_data = [
            self.create_period_data(
                "1.1",
                Decimal("100000"),
                Decimal("-11000"),  # -11% SV
                Decimal("-12000"),  # -12% CV
            ),
        ]

        alerts = service.detect_significant_variances(period_data)

        assert len(alerts) == 2
        variance_types = {a.variance_type for a in alerts}
        assert VarianceType.SCHEDULE in variance_types
        assert VarianceType.COST in variance_types

    def test_detect_multiple_wbs_variances(self):
        """Should detect variances across multiple WBS elements."""
        service = VarianceAnalysisService()
        period_data = [
            self.create_period_data("1.1", Decimal("100000"), Decimal("-15000"), Decimal("0")),
            self.create_period_data("1.2", Decimal("50000"), Decimal("0"), Decimal("-10000")),
            self.create_period_data("1.3", Decimal("75000"), Decimal("-5000"), Decimal("-3000")),
        ]

        alerts = service.detect_significant_variances(period_data)

        # 1.1: -15% SV (significant)
        # 1.2: -20% CV (critical)
        # 1.3: -6.7% SV, -4% CV (no alerts)
        assert len(alerts) == 2
        codes = {a.wbs_code for a in alerts}
        assert "1.1" in codes
        assert "1.2" in codes

    def test_alerts_sorted_by_severity(self):
        """Should sort alerts by severity (critical first)."""
        service = VarianceAnalysisService()
        period_data = [
            self.create_period_data(
                "1.1", Decimal("100000"), Decimal("-11000"), Decimal("0")
            ),  # 11%
            self.create_period_data(
                "1.2", Decimal("100000"), Decimal("-25000"), Decimal("0")
            ),  # 25%
            self.create_period_data(
                "1.3", Decimal("100000"), Decimal("-18000"), Decimal("0")
            ),  # 18%
        ]

        alerts = service.detect_significant_variances(period_data)

        assert alerts[0].severity == VarianceSeverity.CRITICAL  # 25%
        assert alerts[1].severity == VarianceSeverity.CRITICAL  # 18%
        assert alerts[2].severity == VarianceSeverity.SIGNIFICANT  # 11%

    def test_skip_zero_bcws(self):
        """Should skip WBS with zero BCWS."""
        service = VarianceAnalysisService()
        period_data = [
            {
                "wbs_id": uuid4(),
                "wbs_code": "1.1",
                "wbs_name": "Test",
                "period_name": "Test",
                "cumulative_bcws": Decimal("0"),
                "sv": Decimal("-10000"),
                "cv": Decimal("-10000"),
            },
        ]

        alerts = service.detect_significant_variances(period_data)

        assert len(alerts) == 0

    def test_custom_threshold(self):
        """Should use custom threshold when provided."""
        service = VarianceAnalysisService()
        period_data = [
            self.create_period_data("1.1", Decimal("100000"), Decimal("-8000"), Decimal("0")),  # 8%
        ]

        # Default 10% threshold - no alert
        alerts_default = service.detect_significant_variances(period_data)
        assert len(alerts_default) == 0

        # Custom 5% threshold - should alert
        alerts_custom = service.detect_significant_variances(
            period_data, threshold_percent=Decimal("5")
        )
        assert len(alerts_custom) == 1

    def test_detect_with_historical_data_worsening(self):
        """Should calculate worsening trend from historical data."""
        service = VarianceAnalysisService()
        wbs_id = uuid4()
        period_data = [
            {
                "wbs_id": wbs_id,
                "wbs_code": "1.1",
                "wbs_name": "WBS 1.1",
                "period_name": "March 2026",
                "cumulative_bcws": Decimal("100000"),
                "sv": Decimal("-15000"),
                "cv": Decimal("0"),
            },
        ]

        historical_data = {
            wbs_id: [
                {
                    "period_name": "Jan",
                    "cumulative_bcws": Decimal("100000"),
                    "sv": Decimal("-5000"),
                    "cv": Decimal("0"),
                },
                {
                    "period_name": "Feb",
                    "cumulative_bcws": Decimal("100000"),
                    "sv": Decimal("-10000"),
                    "cv": Decimal("0"),
                },
                {
                    "period_name": "Mar",
                    "cumulative_bcws": Decimal("100000"),
                    "sv": Decimal("-15000"),
                    "cv": Decimal("0"),
                },
            ],
        }

        alerts = service.detect_significant_variances(period_data, historical_data=historical_data)

        assert len(alerts) == 1
        assert alerts[0].trend == TrendDirection.WORSENING

    def test_detect_with_historical_data_improving(self):
        """Should calculate improving trend from historical data."""
        service = VarianceAnalysisService()
        wbs_id = uuid4()
        period_data = [
            {
                "wbs_id": wbs_id,
                "wbs_code": "1.1",
                "wbs_name": "WBS 1.1",
                "period_name": "March 2026",
                "cumulative_bcws": Decimal("100000"),
                "sv": Decimal("-11000"),
                "cv": Decimal("0"),
            },
        ]

        historical_data = {
            wbs_id: [
                {
                    "period_name": "Jan",
                    "cumulative_bcws": Decimal("100000"),
                    "sv": Decimal("-20000"),
                    "cv": Decimal("0"),
                },
                {
                    "period_name": "Feb",
                    "cumulative_bcws": Decimal("100000"),
                    "sv": Decimal("-15000"),
                    "cv": Decimal("0"),
                },
                {
                    "period_name": "Mar",
                    "cumulative_bcws": Decimal("100000"),
                    "sv": Decimal("-11000"),
                    "cv": Decimal("0"),
                },
            ],
        }

        alerts = service.detect_significant_variances(period_data, historical_data=historical_data)

        assert len(alerts) == 1
        assert alerts[0].trend == TrendDirection.IMPROVING

    def test_detect_without_historical_data_defaults_stable(self):
        """Should default to STABLE when no historical data provided."""
        service = VarianceAnalysisService()
        period_data = [
            self.create_period_data(
                "1.1",
                Decimal("100000"),
                Decimal("-15000"),
                Decimal("0"),
            ),
        ]

        alerts = service.detect_significant_variances(period_data)

        assert len(alerts) == 1
        assert alerts[0].trend == TrendDirection.STABLE

    def test_detect_with_historical_data_cost_trend(self):
        """Should calculate cost variance trend from historical data."""
        service = VarianceAnalysisService()
        wbs_id = uuid4()
        period_data = [
            {
                "wbs_id": wbs_id,
                "wbs_code": "1.1",
                "wbs_name": "WBS 1.1",
                "period_name": "March 2026",
                "cumulative_bcws": Decimal("100000"),
                "sv": Decimal("0"),
                "cv": Decimal("-15000"),
            },
        ]

        historical_data = {
            wbs_id: [
                {
                    "period_name": "Jan",
                    "cumulative_bcws": Decimal("100000"),
                    "sv": Decimal("0"),
                    "cv": Decimal("-5000"),
                },
                {
                    "period_name": "Feb",
                    "cumulative_bcws": Decimal("100000"),
                    "sv": Decimal("0"),
                    "cv": Decimal("-10000"),
                },
                {
                    "period_name": "Mar",
                    "cumulative_bcws": Decimal("100000"),
                    "sv": Decimal("0"),
                    "cv": Decimal("-15000"),
                },
            ],
        }

        alerts = service.detect_significant_variances(period_data, historical_data=historical_data)

        assert len(alerts) == 1
        assert alerts[0].variance_type == VarianceType.COST
        assert alerts[0].trend == TrendDirection.WORSENING

    def test_detect_with_partial_historical_data(self):
        """Should handle WBS with no historical data gracefully."""
        service = VarianceAnalysisService()
        wbs_id = uuid4()
        other_wbs_id = uuid4()
        period_data = [
            {
                "wbs_id": wbs_id,
                "wbs_code": "1.1",
                "wbs_name": "WBS 1.1",
                "period_name": "March 2026",
                "cumulative_bcws": Decimal("100000"),
                "sv": Decimal("-15000"),
                "cv": Decimal("0"),
            },
        ]

        # Historical data exists but for a different WBS
        historical_data = {
            other_wbs_id: [
                {
                    "period_name": "Jan",
                    "cumulative_bcws": Decimal("100000"),
                    "sv": Decimal("-5000"),
                    "cv": Decimal("0"),
                },
            ],
        }

        alerts = service.detect_significant_variances(period_data, historical_data=historical_data)

        assert len(alerts) == 1
        # No history for this WBS, defaults to STABLE
        assert alerts[0].trend == TrendDirection.STABLE


class TestVarianceAnalysisServiceCalculateTrend:
    """Tests for trend calculation."""

    def test_calculate_stable_trend(self):
        """Should identify stable trend."""
        service = VarianceAnalysisService()

        history = [Decimal("-5"), Decimal("-5.2"), Decimal("-5.1"), Decimal("-5")]
        trend = service.calculate_trend(history)

        assert trend == TrendDirection.STABLE

    def test_calculate_improving_trend(self):
        """Should identify improving trend (variance getting more positive)."""
        service = VarianceAnalysisService()

        # Getting less negative = improving
        history = [Decimal("-10"), Decimal("-8"), Decimal("-5"), Decimal("-2")]
        trend = service.calculate_trend(history)

        assert trend == TrendDirection.IMPROVING

    def test_calculate_worsening_trend(self):
        """Should identify worsening trend (variance getting more negative)."""
        service = VarianceAnalysisService()

        # Getting more negative = worsening
        history = [Decimal("-2"), Decimal("-5"), Decimal("-8"), Decimal("-12")]
        trend = service.calculate_trend(history)

        assert trend == TrendDirection.WORSENING

    def test_single_value_stable(self):
        """Should return stable for single value."""
        service = VarianceAnalysisService()

        history = [Decimal("-5")]
        trend = service.calculate_trend(history)

        assert trend == TrendDirection.STABLE

    def test_empty_history_stable(self):
        """Should return stable for empty history."""
        service = VarianceAnalysisService()

        trend = service.calculate_trend([])

        assert trend == TrendDirection.STABLE

    def test_windowed_trend(self):
        """Should use window parameter for trend calculation."""
        service = VarianceAnalysisService()

        # Old values improving, recent values worsening
        history = [
            Decimal("-15"),  # Old
            Decimal("-10"),  # Old
            Decimal("-5"),  # In window
            Decimal("-8"),  # In window
            Decimal("-12"),  # In window
        ]

        # With window=3, should see worsening trend
        trend = service.calculate_trend(history, window=3)

        assert trend == TrendDirection.WORSENING


class TestVarianceAnalysisServiceBuildTrend:
    """Tests for building variance trends."""

    def test_build_trend(self):
        """Should build trend from period history."""
        service = VarianceAnalysisService()
        wbs_id = uuid4()

        period_history = [
            {
                "period_name": "Jan",
                "cumulative_bcws": Decimal("100000"),
                "sv": Decimal("-5000"),
                "cv": Decimal("0"),
            },
            {
                "period_name": "Feb",
                "cumulative_bcws": Decimal("200000"),
                "sv": Decimal("-15000"),
                "cv": Decimal("0"),
            },
            {
                "period_name": "Mar",
                "cumulative_bcws": Decimal("300000"),
                "sv": Decimal("-30000"),
                "cv": Decimal("0"),
            },
        ]

        trend = service.build_variance_trend(
            wbs_id=wbs_id,
            wbs_code="1.2.3",
            variance_type=VarianceType.SCHEDULE,
            period_history=period_history,
        )

        assert trend.wbs_id == wbs_id
        assert len(trend.periods) == 3
        assert len(trend.values) == 3
        assert len(trend.percentages) == 3
        assert trend.percentages[0] == Decimal("-5.00")
        assert trend.percentages[2] == Decimal("-10.00")

    def test_build_trend_with_breach_count(self):
        """Should count consecutive periods in breach."""
        service = VarianceAnalysisService()
        wbs_id = uuid4()

        period_history = [
            {
                "period_name": "Jan",
                "cumulative_bcws": Decimal("100000"),
                "sv": Decimal("-5000"),
                "cv": Decimal("0"),
            },  # 5%
            {
                "period_name": "Feb",
                "cumulative_bcws": Decimal("100000"),
                "sv": Decimal("-12000"),
                "cv": Decimal("0"),
            },  # 12%
            {
                "period_name": "Mar",
                "cumulative_bcws": Decimal("100000"),
                "sv": Decimal("-15000"),
                "cv": Decimal("0"),
            },  # 15%
            {
                "period_name": "Apr",
                "cumulative_bcws": Decimal("100000"),
                "sv": Decimal("-18000"),
                "cv": Decimal("0"),
            },  # 18%
        ]

        trend = service.build_variance_trend(
            wbs_id=wbs_id,
            wbs_code="1.2.3",
            variance_type=VarianceType.SCHEDULE,
            period_history=period_history,
        )

        # 3 consecutive periods in breach (Feb, Mar, Apr)
        assert trend.periods_in_breach == 3


class TestVarianceAnalysisServiceAnalyzeProgram:
    """Tests for complete program analysis."""

    def test_analyze_program(self):
        """Should perform complete program analysis."""
        service = VarianceAnalysisService()
        program_id = uuid4()

        period_data = [
            {
                "wbs_id": uuid4(),
                "wbs_code": "1.1",
                "wbs_name": "WBS 1.1",
                "period_name": "January 2026",
                "cumulative_bcws": Decimal("100000"),
                "sv": Decimal("-15000"),
                "cv": Decimal("-12000"),
            },
            {
                "wbs_id": uuid4(),
                "wbs_code": "1.2",
                "wbs_name": "WBS 1.2",
                "period_name": "January 2026",
                "cumulative_bcws": Decimal("50000"),
                "sv": Decimal("-2000"),
                "cv": Decimal("-1000"),
            },
        ]

        result = service.analyze_program_variances(
            program_id=program_id,
            period_name="January 2026",
            period_data=period_data,
        )

        assert result.program_id == program_id
        assert result.period_name == "January 2026"
        assert result.total_wbs_analyzed == 2
        assert len(result.alerts) == 2  # SV and CV for 1.1
        assert result.schedule_variance_count == 1
        assert result.cost_variance_count == 1

    def test_analyze_program_with_history(self):
        """Should update trends when history provided."""
        service = VarianceAnalysisService()
        program_id = uuid4()
        wbs_id = uuid4()

        period_data = [
            {
                "wbs_id": wbs_id,
                "wbs_code": "1.1",
                "wbs_name": "WBS 1.1",
                "period_name": "March 2026",
                "cumulative_bcws": Decimal("100000"),
                "sv": Decimal("-15000"),
                "cv": Decimal("0"),
            },
        ]

        historical_data = {
            wbs_id: [
                {
                    "period_name": "Jan",
                    "cumulative_bcws": Decimal("100000"),
                    "sv": Decimal("-5000"),
                    "cv": Decimal("0"),
                },
                {
                    "period_name": "Feb",
                    "cumulative_bcws": Decimal("100000"),
                    "sv": Decimal("-10000"),
                    "cv": Decimal("0"),
                },
                {
                    "period_name": "Mar",
                    "cumulative_bcws": Decimal("100000"),
                    "sv": Decimal("-15000"),
                    "cv": Decimal("0"),
                },
            ],
        }

        result = service.analyze_program_variances(
            program_id=program_id,
            period_name="March 2026",
            period_data=period_data,
            historical_data=historical_data,
        )

        assert len(result.trends) > 0
        # Alert should have trend updated
        assert result.alerts[0].trend == TrendDirection.WORSENING


class TestVarianceAnalysisServiceSummaryText:
    """Tests for summary text generation."""

    def test_get_variance_summary_text(self):
        """Should generate readable summary text."""
        service = VarianceAnalysisService()

        result = VarianceAnalysisResult(
            program_id=uuid4(),
            analysis_date=date(2026, 1, 31),
            period_name="January 2026",
            total_wbs_analyzed=50,
            critical_count=2,
            significant_count=5,
            moderate_count=8,
            minor_count=10,
            schedule_variance_count=12,
            cost_variance_count=13,
            explanations_required=7,
            explanations_provided=5,
        )

        summary = service.get_variance_summary_text(result)

        assert "January 2026" in summary
        assert "Total WBS Elements Analyzed: 50" in summary
        assert "Critical:    2" in summary
        assert "Schedule Variances: 12" in summary
        assert "Explanations Required: 7" in summary
        assert "Explanations Needed:   2" in summary  # 7 - 5 = 2
