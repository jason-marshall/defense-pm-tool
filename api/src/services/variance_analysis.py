"""Variance Analysis service for EVMS compliance.

Detects significant variances and generates analysis reports
per DFARS requirements. When CV or SV exceeds thresholds
(typically 10%), explanations are required.

Key features:
1. Detect significant variances automatically
2. Track variance trends over time
3. Classify variance severity
4. Support corrective action tracking
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class VarianceType(str, Enum):
    """Type of variance being analyzed."""

    SCHEDULE = "schedule"
    COST = "cost"


class VarianceSeverity(str, Enum):
    """Severity classification for variances.

    Severity levels per typical EVMS thresholds:
    - MINOR: < 5% variance, typically informational
    - MODERATE: 5-10% variance, monitoring required
    - SIGNIFICANT: 10-15% variance, explanation required per DFARS
    - CRITICAL: > 15% variance, immediate attention and corrective action
    """

    MINOR = "minor"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"
    CRITICAL = "critical"


class TrendDirection(str, Enum):
    """Direction of variance trend."""

    IMPROVING = "improving"
    STABLE = "stable"
    WORSENING = "worsening"


@dataclass
class VarianceAlert:
    """Alert for variance requiring attention or explanation.

    Generated when variance exceeds configured thresholds.
    Contains all information needed for variance analysis report.
    """

    wbs_id: UUID
    wbs_code: str
    wbs_name: str
    variance_type: VarianceType
    variance_amount: Decimal
    variance_percent: Decimal
    severity: VarianceSeverity
    period_name: str
    trend: TrendDirection
    explanation_required: bool
    existing_explanation: str | None = None
    corrective_action: str | None = None
    expected_resolution: date | None = None


@dataclass
class VarianceTrend:
    """Trend data for a variance over time.

    Tracks variance progression across multiple periods
    to identify patterns and predict future performance.
    """

    wbs_id: UUID
    wbs_code: str
    variance_type: VarianceType
    periods: list[str] = field(default_factory=list)
    values: list[Decimal] = field(default_factory=list)
    percentages: list[Decimal] = field(default_factory=list)
    trend_direction: TrendDirection = TrendDirection.STABLE
    periods_in_breach: int = 0  # Consecutive periods above threshold


@dataclass
class VarianceThresholds:
    """Configurable thresholds for variance classification.

    Default values align with typical EVMS reporting requirements.
    """

    minor_threshold: Decimal = Decimal("5")
    moderate_threshold: Decimal = Decimal("10")
    significant_threshold: Decimal = Decimal("15")
    explanation_required_threshold: Decimal = Decimal("10")


@dataclass
class VarianceAnalysisResult:
    """Complete variance analysis result for a program.

    Contains all alerts, trends, and summary statistics
    for variance reporting.
    """

    program_id: UUID
    analysis_date: date
    period_name: str
    total_wbs_analyzed: int
    alerts: list[VarianceAlert] = field(default_factory=list)
    trends: list[VarianceTrend] = field(default_factory=list)

    # Summary counts by severity
    critical_count: int = 0
    significant_count: int = 0
    moderate_count: int = 0
    minor_count: int = 0

    # Summary counts by type
    schedule_variance_count: int = 0
    cost_variance_count: int = 0

    # Explanation status
    explanations_required: int = 0
    explanations_provided: int = 0


class VarianceAnalysisService:
    """Analyze variances and generate alerts for EVMS compliance.

    This service:
    1. Detects WBS elements with significant variances
    2. Classifies variance severity
    3. Tracks variance trends over time
    4. Identifies items requiring explanation

    Foundation for Week 9 full implementation with:
    - Automated narrative generation
    - Integration with corrective action tracking
    - Historical trend analysis

    Example usage:
        service = VarianceAnalysisService()
        alerts = service.detect_significant_variances(period_data)
        for alert in alerts:
            if alert.explanation_required:
                # Generate or request explanation
                pass
    """

    def __init__(
        self,
        thresholds: VarianceThresholds | None = None,
    ) -> None:
        """Initialize variance analysis service.

        Args:
            thresholds: Optional custom thresholds. Uses defaults if not provided.
        """
        self.thresholds = thresholds or VarianceThresholds()

    def classify_severity(self, variance_percent: Decimal) -> VarianceSeverity:
        """Classify variance severity based on percentage.

        Args:
            variance_percent: Variance as percentage (can be negative)

        Returns:
            VarianceSeverity classification
        """
        abs_percent = abs(variance_percent)

        if abs_percent < self.thresholds.minor_threshold:
            return VarianceSeverity.MINOR
        elif abs_percent < self.thresholds.moderate_threshold:
            return VarianceSeverity.MODERATE
        elif abs_percent < self.thresholds.significant_threshold:
            return VarianceSeverity.SIGNIFICANT
        else:
            return VarianceSeverity.CRITICAL

    def requires_explanation(self, variance_percent: Decimal) -> bool:
        """Check if variance requires written explanation.

        Args:
            variance_percent: Variance as percentage

        Returns:
            True if explanation is required per thresholds
        """
        return abs(variance_percent) >= self.thresholds.explanation_required_threshold

    def detect_significant_variances(
        self,
        period_data: list[dict[str, Any]],
        threshold_percent: Decimal | None = None,
        historical_data: dict[UUID, list[dict[str, Any]]] | None = None,
    ) -> list[VarianceAlert]:
        """Detect WBS elements with significant variances.

        Analyzes period data to identify schedule and cost variances
        that exceed the configured threshold.

        Args:
            period_data: List of WBS period data dicts containing:
                - wbs_id: UUID of WBS element
                - wbs_code: WBS code string
                - wbs_name: WBS name string
                - period_name: Name of the period
                - cumulative_bcws: Cumulative planned value
                - sv: Schedule variance amount
                - cv: Cost variance amount
            threshold_percent: Override threshold (uses config default if None)
            historical_data: Optional dict mapping WBS ID to historical periods
                for trend calculation. When provided, alerts will have computed
                trend directions instead of defaulting to STABLE.

        Returns:
            List of VarianceAlert sorted by severity (critical first)
        """
        threshold = threshold_percent or self.thresholds.explanation_required_threshold
        alerts: list[VarianceAlert] = []

        for data in period_data:
            wbs_id: UUID = data.get("wbs_id")  # type: ignore[assignment]
            wbs_code: str = data.get("wbs_code", "")
            wbs_name: str = data.get("wbs_name", "")
            period_name = data.get("period_name", "")

            # Get cumulative BCWS for percentage calculation
            bcws = data.get("cumulative_bcws", Decimal("0"))
            if bcws <= 0:
                continue  # Skip if no planned value

            sv = data.get("sv", Decimal("0"))
            cv = data.get("cv", Decimal("0"))

            # Calculate variance percentages
            sv_percent = (sv / bcws * 100).quantize(Decimal("0.01"))
            cv_percent = (cv / bcws * 100).quantize(Decimal("0.01"))

            # Calculate trends from history if available
            sv_trend = TrendDirection.STABLE
            cv_trend = TrendDirection.STABLE
            if historical_data and wbs_id in historical_data:
                history = historical_data[wbs_id]
                sv_trend_data = self.build_variance_trend(
                    wbs_id, wbs_code, VarianceType.SCHEDULE, history
                )
                cv_trend_data = self.build_variance_trend(
                    wbs_id, wbs_code, VarianceType.COST, history
                )
                sv_trend = sv_trend_data.trend_direction
                cv_trend = cv_trend_data.trend_direction

            # Check schedule variance
            if abs(sv_percent) >= threshold:
                severity = self.classify_severity(sv_percent)
                alerts.append(
                    VarianceAlert(
                        wbs_id=wbs_id,
                        wbs_code=wbs_code,
                        wbs_name=wbs_name,
                        variance_type=VarianceType.SCHEDULE,
                        variance_amount=sv,
                        variance_percent=sv_percent,
                        severity=severity,
                        period_name=period_name,
                        trend=sv_trend,
                        explanation_required=self.requires_explanation(sv_percent),
                    )
                )

            # Check cost variance
            if abs(cv_percent) >= threshold:
                severity = self.classify_severity(cv_percent)
                alerts.append(
                    VarianceAlert(
                        wbs_id=wbs_id,
                        wbs_code=wbs_code,
                        wbs_name=wbs_name,
                        variance_type=VarianceType.COST,
                        variance_amount=cv,
                        variance_percent=cv_percent,
                        severity=severity,
                        period_name=period_name,
                        trend=cv_trend,
                        explanation_required=self.requires_explanation(cv_percent),
                    )
                )

        # Sort by severity (critical first), then by absolute variance
        severity_order = {
            VarianceSeverity.CRITICAL: 0,
            VarianceSeverity.SIGNIFICANT: 1,
            VarianceSeverity.MODERATE: 2,
            VarianceSeverity.MINOR: 3,
        }
        alerts.sort(key=lambda a: (severity_order[a.severity], -abs(a.variance_percent)))

        logger.info(
            "variance_analysis_complete",
            items_analyzed=len(period_data),
            alerts_generated=len(alerts),
            critical=sum(1 for a in alerts if a.severity == VarianceSeverity.CRITICAL),
            significant=sum(1 for a in alerts if a.severity == VarianceSeverity.SIGNIFICANT),
        )

        return alerts

    def calculate_trend(
        self,
        variance_history: list[Decimal],
        window: int = 3,
    ) -> TrendDirection:
        """Calculate variance trend direction from history.

        Analyzes recent variance values to determine if performance
        is improving, stable, or worsening.

        Args:
            variance_history: List of variance values (oldest to newest)
            window: Number of recent periods to consider

        Returns:
            TrendDirection indicating variance trend
        """
        if len(variance_history) < 2:
            return TrendDirection.STABLE

        # Use the most recent periods up to window size
        recent = variance_history[-window:] if len(variance_history) >= window else variance_history

        # Calculate period-over-period changes
        changes = [recent[i] - recent[i - 1] for i in range(1, len(recent))]

        if not changes:
            return TrendDirection.STABLE

        avg_change = sum(changes) / len(changes)

        # Positive variance (EV > PV or EV > AC) is good
        # Improving means variance getting more positive (less negative)
        # Use 0.5% as threshold for meaningful change
        threshold = Decimal("0.5")

        if avg_change > threshold:
            return TrendDirection.IMPROVING
        elif avg_change < -threshold:
            return TrendDirection.WORSENING
        else:
            return TrendDirection.STABLE

    def build_variance_trend(
        self,
        wbs_id: UUID,
        wbs_code: str,
        variance_type: VarianceType,
        period_history: list[dict[str, Any]],
        threshold_percent: Decimal | None = None,
    ) -> VarianceTrend:
        """Build variance trend for a specific WBS element.

        Args:
            wbs_id: UUID of the WBS element
            wbs_code: WBS code string
            variance_type: Type of variance to track
            period_history: List of period data dicts sorted by date
            threshold_percent: Threshold for counting breach periods

        Returns:
            VarianceTrend with historical data and direction
        """
        threshold = threshold_percent or self.thresholds.explanation_required_threshold

        periods: list[str] = []
        values: list[Decimal] = []
        percentages: list[Decimal] = []
        consecutive_breach = 0
        current_breach_count = 0

        for period_data in period_history:
            period_name = period_data.get("period_name", "")
            bcws = period_data.get("cumulative_bcws", Decimal("0"))

            if variance_type == VarianceType.SCHEDULE:
                variance = period_data.get("sv", Decimal("0"))
            else:
                variance = period_data.get("cv", Decimal("0"))

            if bcws > 0:
                variance_pct = (variance / bcws * 100).quantize(Decimal("0.01"))
            else:
                variance_pct = Decimal("0")

            periods.append(period_name)
            values.append(variance)
            percentages.append(variance_pct)

            # Track consecutive periods in breach
            if abs(variance_pct) >= threshold:
                current_breach_count += 1
                consecutive_breach = max(consecutive_breach, current_breach_count)
            else:
                current_breach_count = 0

        # Calculate trend direction
        trend_direction = self.calculate_trend(percentages)

        return VarianceTrend(
            wbs_id=wbs_id,
            wbs_code=wbs_code,
            variance_type=variance_type,
            periods=periods,
            values=values,
            percentages=percentages,
            trend_direction=trend_direction,
            periods_in_breach=consecutive_breach,
        )

    def analyze_program_variances(
        self,
        program_id: UUID,
        period_name: str,
        period_data: list[dict[str, Any]],
        historical_data: dict[UUID, list[dict[str, Any]]] | None = None,
    ) -> VarianceAnalysisResult:
        """Perform complete variance analysis for a program.

        Combines alert detection, trend analysis, and summary statistics
        into a comprehensive analysis result.

        Args:
            program_id: UUID of the program being analyzed
            period_name: Name of the current reporting period
            period_data: Current period WBS data
            historical_data: Optional dict mapping WBS ID to historical periods

        Returns:
            VarianceAnalysisResult with complete analysis
        """
        # Detect significant variances
        alerts = self.detect_significant_variances(period_data)

        # Build trends if historical data provided
        trends: list[VarianceTrend] = []
        if historical_data:
            # Get unique WBS IDs with alerts
            alert_wbs_ids = {a.wbs_id for a in alerts}

            for wbs_id in alert_wbs_ids:
                if wbs_id in historical_data:
                    history = historical_data[wbs_id]
                    wbs_code = next((a.wbs_code for a in alerts if a.wbs_id == wbs_id), "")

                    # Build trend for both variance types
                    for vtype in [VarianceType.SCHEDULE, VarianceType.COST]:
                        trend = self.build_variance_trend(wbs_id, wbs_code, vtype, history)
                        if trend.values:  # Only add if we have data
                            trends.append(trend)

                            # Update alert with trend direction
                            for alert in alerts:
                                if alert.wbs_id == wbs_id and alert.variance_type == vtype:
                                    alert.trend = trend.trend_direction

        # Calculate summary statistics
        result = VarianceAnalysisResult(
            program_id=program_id,
            analysis_date=date.today(),
            period_name=period_name,
            total_wbs_analyzed=len(period_data),
            alerts=alerts,
            trends=trends,
            critical_count=sum(1 for a in alerts if a.severity == VarianceSeverity.CRITICAL),
            significant_count=sum(1 for a in alerts if a.severity == VarianceSeverity.SIGNIFICANT),
            moderate_count=sum(1 for a in alerts if a.severity == VarianceSeverity.MODERATE),
            minor_count=sum(1 for a in alerts if a.severity == VarianceSeverity.MINOR),
            schedule_variance_count=sum(
                1 for a in alerts if a.variance_type == VarianceType.SCHEDULE
            ),
            cost_variance_count=sum(1 for a in alerts if a.variance_type == VarianceType.COST),
            explanations_required=sum(1 for a in alerts if a.explanation_required),
            explanations_provided=sum(1 for a in alerts if a.existing_explanation is not None),
        )

        logger.info(
            "program_variance_analysis_complete",
            program_id=str(program_id),
            period=period_name,
            total_alerts=len(alerts),
            critical=result.critical_count,
            explanations_required=result.explanations_required,
        )

        return result

    def get_variance_summary_text(self, result: VarianceAnalysisResult) -> str:
        """Generate human-readable summary of variance analysis.

        Args:
            result: Complete variance analysis result

        Returns:
            Formatted summary text for reporting
        """
        lines = [
            f"Variance Analysis Summary - {result.period_name}",
            f"Analysis Date: {result.analysis_date}",
            "",
            f"Total WBS Elements Analyzed: {result.total_wbs_analyzed}",
            f"Total Variance Alerts: {len(result.alerts)}",
            "",
            "Alerts by Severity:",
            f"  Critical:    {result.critical_count}",
            f"  Significant: {result.significant_count}",
            f"  Moderate:    {result.moderate_count}",
            f"  Minor:       {result.minor_count}",
            "",
            "Alerts by Type:",
            f"  Schedule Variances: {result.schedule_variance_count}",
            f"  Cost Variances:     {result.cost_variance_count}",
            "",
            f"Explanations Required: {result.explanations_required}",
            f"Explanations Provided: {result.explanations_provided}",
        ]

        if result.explanations_required > result.explanations_provided:
            gap = result.explanations_required - result.explanations_provided
            lines.append(f"Explanations Needed:   {gap}")

        return "\n".join(lines)
