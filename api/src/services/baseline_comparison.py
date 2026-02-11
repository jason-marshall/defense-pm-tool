"""Baseline Comparison Service for EVMS variance analysis.

This module compares baseline snapshots to current program state,
identifying schedule, cost, and scope variances per EIA-748 guidelines.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity
from src.models.baseline import Baseline
from src.models.wbs import WBSElement


@dataclass
class ActivityVariance:
    """Variance details for a single activity."""

    activity_id: str
    activity_code: str
    activity_name: str
    change_type: str  # "added", "removed", "modified", "unchanged"

    # Schedule variances
    duration_baseline: int | None = None
    duration_current: int | None = None
    duration_variance: int | None = None

    start_baseline: date | None = None
    start_current: date | None = None
    start_variance_days: int | None = None

    finish_baseline: date | None = None
    finish_current: date | None = None
    finish_variance_days: int | None = None

    # Cost variances
    bac_baseline: Decimal | None = None
    bac_current: Decimal | None = None
    bac_variance: Decimal | None = None

    # Critical path change
    was_critical: bool | None = None
    is_critical: bool | None = None


@dataclass
class WBSVariance:
    """Variance details for a WBS element."""

    wbs_id: str
    wbs_code: str
    wbs_name: str
    change_type: str  # "added", "removed", "modified", "unchanged"

    bac_baseline: Decimal | None = None
    bac_current: Decimal | None = None
    bac_variance: Decimal | None = None


@dataclass
class ComparisonResult:
    """Complete baseline comparison result."""

    baseline_id: UUID
    baseline_name: str
    baseline_version: int
    comparison_date: datetime

    # Summary metrics
    total_bac_baseline: Decimal = Decimal("0.00")
    total_bac_current: Decimal = Decimal("0.00")
    bac_variance: Decimal = Decimal("0.00")
    bac_variance_percent: Decimal = Decimal("0.00")

    project_finish_baseline: date | None = None
    project_finish_current: date | None = None
    schedule_variance_days: int = 0

    # Activity counts
    activities_baseline: int = 0
    activities_current: int = 0
    activities_added: int = 0
    activities_removed: int = 0
    activities_modified: int = 0
    activities_unchanged: int = 0

    # Critical path changes
    critical_path_baseline: list[str] = field(default_factory=list)
    critical_path_current: list[str] = field(default_factory=list)
    critical_path_changed: bool = False

    # WBS counts
    wbs_baseline: int = 0
    wbs_current: int = 0
    wbs_added: int = 0
    wbs_removed: int = 0
    wbs_modified: int = 0

    # Detailed variances
    activity_variances: list[ActivityVariance] = field(default_factory=list)
    wbs_variances: list[WBSVariance] = field(default_factory=list)

    # Lists of changed items (codes only for summary)
    added_activity_codes: list[str] = field(default_factory=list)
    removed_activity_codes: list[str] = field(default_factory=list)
    modified_activity_codes: list[str] = field(default_factory=list)


class BaselineComparisonService:
    """
    Service for comparing baseline snapshots to current program state.

    Provides variance analysis per EVMS guidelines:
    - Schedule variance (dates, durations)
    - Cost variance (BAC changes)
    - Scope variance (activities added/removed)
    - Critical path changes

    Example:
        >>> service = BaselineComparisonService(db_session)
        >>> result = await service.compare_to_current(baseline_id)
        >>> print(f"BAC variance: ${result.bac_variance}")
    """

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    async def compare_to_current(
        self,
        baseline: Baseline,
        include_details: bool = True,
    ) -> ComparisonResult:
        """
        Compare a baseline to the current program state.

        Args:
            baseline: The baseline to compare
            include_details: Whether to include detailed activity/WBS variances

        Returns:
            ComparisonResult with all variance data
        """
        result = ComparisonResult(
            baseline_id=baseline.id,
            baseline_name=baseline.name,
            baseline_version=baseline.version,
            comparison_date=datetime.now(UTC),
        )

        # Get current activities
        current_activities = await self._get_current_activities(baseline.program_id)

        # Get current WBS elements
        current_wbs = await self._get_current_wbs(baseline.program_id)

        # Compare schedule
        if baseline.schedule_snapshot:
            await self._compare_schedule(baseline, current_activities, result, include_details)

        # Compare cost/WBS
        if baseline.cost_snapshot or baseline.wbs_snapshot:
            await self._compare_cost_wbs(baseline, current_wbs, result, include_details)

        # Calculate summary metrics
        self._calculate_summaries(result)

        return result

    async def _get_current_activities(self, program_id: UUID) -> dict[str, Activity]:
        """Get current activities indexed by code."""
        query = (
            select(Activity)
            .where(Activity.program_id == program_id)
            .where(Activity.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        activities = result.scalars().all()
        return {a.code: a for a in activities}

    async def _get_current_wbs(self, program_id: UUID) -> dict[str, WBSElement]:
        """Get current WBS elements indexed by code."""
        query = (
            select(WBSElement)
            .where(WBSElement.program_id == program_id)
            .where(WBSElement.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        elements = result.scalars().all()
        return {e.wbs_code: e for e in elements}

    async def _compare_schedule(
        self,
        baseline: Baseline,
        current_activities: dict[str, Activity],
        result: ComparisonResult,
        include_details: bool,
    ) -> None:
        """Compare schedule snapshot to current state."""
        snapshot = baseline.schedule_snapshot
        if not snapshot:
            return

        baseline_activities = {a["code"]: a for a in snapshot.get("activities", [])}

        result.activities_baseline = len(baseline_activities)
        result.activities_current = len(current_activities)

        # Extract critical path from baseline
        critical_ids_baseline = set(snapshot.get("critical_path_ids", []))

        # Build code-to-id mapping for baseline
        baseline_id_to_code = {a["id"]: a["code"] for a in snapshot.get("activities", [])}
        result.critical_path_baseline = [
            baseline_id_to_code.get(id, id) for id in critical_ids_baseline
        ]

        # Current critical path
        result.critical_path_current = [
            a.code for a in current_activities.values() if a.is_critical
        ]

        # Check if critical path changed
        result.critical_path_changed = set(result.critical_path_baseline) != set(
            result.critical_path_current
        )

        # Project finish dates
        if snapshot.get("project_finish"):
            result.project_finish_baseline = date.fromisoformat(snapshot["project_finish"])

        # Find current project finish
        if current_activities:
            finishes = [a.early_finish for a in current_activities.values() if a.early_finish]
            if finishes:
                result.project_finish_current = max(finishes)

        # Calculate schedule variance
        if result.project_finish_baseline and result.project_finish_current:
            result.schedule_variance_days = (
                result.project_finish_current - result.project_finish_baseline
            ).days

        # Find added, removed, modified activities
        baseline_codes = set(baseline_activities.keys())
        current_codes = set(current_activities.keys())

        added_codes = current_codes - baseline_codes
        removed_codes = baseline_codes - current_codes
        common_codes = baseline_codes & current_codes

        result.activities_added = len(added_codes)
        result.activities_removed = len(removed_codes)
        result.added_activity_codes = sorted(added_codes)
        result.removed_activity_codes = sorted(removed_codes)

        # Check modified activities
        modified_codes = []
        unchanged_codes = []

        for code in common_codes:
            baseline_act = baseline_activities[code]
            current_act = current_activities[code]

            if self._activity_modified(baseline_act, current_act):
                modified_codes.append(code)
            else:
                unchanged_codes.append(code)

        result.activities_modified = len(modified_codes)
        result.activities_unchanged = len(unchanged_codes)
        result.modified_activity_codes = sorted(modified_codes)

        # Build detailed variances if requested
        if include_details:
            # Added activities
            for code in added_codes:
                act = current_activities[code]
                result.activity_variances.append(
                    ActivityVariance(
                        activity_id=str(act.id),
                        activity_code=code,
                        activity_name=act.name,
                        change_type="added",
                        duration_current=act.duration,
                        start_current=act.early_start,
                        finish_current=act.early_finish,
                        bac_current=act.budgeted_cost,
                        is_critical=act.is_critical,
                    )
                )

            # Removed activities
            for code in removed_codes:
                act = baseline_activities[code]
                result.activity_variances.append(
                    ActivityVariance(
                        activity_id=act["id"],
                        activity_code=code,
                        activity_name=act["name"],
                        change_type="removed",
                        duration_baseline=act["duration"],
                        start_baseline=date.fromisoformat(act["early_start"])
                        if act.get("early_start")
                        else None,
                        finish_baseline=date.fromisoformat(act["early_finish"])
                        if act.get("early_finish")
                        else None,
                        bac_baseline=Decimal(act["budgeted_cost"]),
                        was_critical=act["is_critical"],
                    )
                )

            # Modified activities
            for code in modified_codes:
                baseline_act = baseline_activities[code]
                current_act = current_activities[code]
                variance = self._build_activity_variance(baseline_act, current_act, "modified")
                result.activity_variances.append(variance)

    def _activity_modified(
        self,
        baseline: dict[str, Any],
        current: Activity,
    ) -> bool:
        """Check if an activity has been modified."""
        # Check duration
        if baseline["duration"] != current.duration:
            return True

        # Check BAC
        if Decimal(baseline["budgeted_cost"]) != current.budgeted_cost:
            return True

        # Check dates (if both exist)
        baseline_start = baseline.get("early_start")
        if baseline_start and current.early_start:
            if date.fromisoformat(baseline_start) != current.early_start:
                return True

        baseline_finish = baseline.get("early_finish")
        if baseline_finish and current.early_finish:
            if date.fromisoformat(baseline_finish) != current.early_finish:
                return True

        # Check critical path status
        if baseline["is_critical"] != current.is_critical:
            return True

        return False

    def _build_activity_variance(
        self,
        baseline: dict[str, Any],
        current: Activity,
        change_type: str,
    ) -> ActivityVariance:
        """Build detailed variance for an activity."""
        variance = ActivityVariance(
            activity_id=str(current.id),
            activity_code=current.code,
            activity_name=current.name,
            change_type=change_type,
        )

        # Duration
        variance.duration_baseline = baseline["duration"]
        variance.duration_current = current.duration
        variance.duration_variance = current.duration - baseline["duration"]

        # Start date
        if baseline.get("early_start"):
            variance.start_baseline = date.fromisoformat(baseline["early_start"])
        if current.early_start:
            variance.start_current = current.early_start
        if variance.start_baseline and variance.start_current:
            variance.start_variance_days = (variance.start_current - variance.start_baseline).days

        # Finish date
        if baseline.get("early_finish"):
            variance.finish_baseline = date.fromisoformat(baseline["early_finish"])
        if current.early_finish:
            variance.finish_current = current.early_finish
        if variance.finish_baseline and variance.finish_current:
            variance.finish_variance_days = (
                variance.finish_current - variance.finish_baseline
            ).days

        # BAC
        variance.bac_baseline = Decimal(baseline["budgeted_cost"])
        variance.bac_current = current.budgeted_cost
        variance.bac_variance = current.budgeted_cost - variance.bac_baseline

        # Critical path
        variance.was_critical = baseline["is_critical"]
        variance.is_critical = current.is_critical

        return variance

    async def _compare_cost_wbs(
        self,
        baseline: Baseline,
        current_wbs: dict[str, WBSElement],
        result: ComparisonResult,
        include_details: bool,
    ) -> None:
        """Compare cost/WBS snapshot to current state."""
        # Use cost_snapshot if available, otherwise wbs_snapshot
        snapshot = baseline.cost_snapshot or baseline.wbs_snapshot
        if not snapshot:
            return

        baseline_wbs = {w["wbs_code"]: w for w in snapshot.get("wbs_elements", [])}

        result.wbs_baseline = len(baseline_wbs)
        result.wbs_current = len(current_wbs)
        result.total_bac_baseline = baseline.total_bac

        # Calculate current total BAC
        result.total_bac_current = sum(
            ((w.budget_at_completion or Decimal("0")) for w in current_wbs.values()),
            Decimal("0"),
        )

        # Find added, removed, modified WBS
        baseline_codes = set(baseline_wbs.keys())
        current_codes = set(current_wbs.keys())

        added_codes = current_codes - baseline_codes
        removed_codes = baseline_codes - current_codes
        common_codes = baseline_codes & current_codes

        result.wbs_added = len(added_codes)
        result.wbs_removed = len(removed_codes)

        # Check modified WBS
        modified_count = 0
        for code in common_codes:
            baseline_elem = baseline_wbs[code]
            current_elem = current_wbs[code]

            if Decimal(baseline_elem["budgeted_cost"]) != current_elem.budget_at_completion:
                modified_count += 1

                if include_details:
                    result.wbs_variances.append(
                        WBSVariance(
                            wbs_id=str(current_elem.id),
                            wbs_code=code,
                            wbs_name=current_elem.name,
                            change_type="modified",
                            bac_baseline=Decimal(baseline_elem["budgeted_cost"]),
                            bac_current=current_elem.budget_at_completion,
                            bac_variance=current_elem.budget_at_completion
                            - Decimal(baseline_elem["budgeted_cost"]),
                        )
                    )

        result.wbs_modified = modified_count

        if include_details:
            # Added WBS
            for code in added_codes:
                elem = current_wbs[code]
                result.wbs_variances.append(
                    WBSVariance(
                        wbs_id=str(elem.id),
                        wbs_code=code,
                        wbs_name=elem.name,
                        change_type="added",
                        bac_current=elem.budget_at_completion,
                    )
                )

            # Removed WBS
            for code in removed_codes:
                elem = baseline_wbs[code]
                result.wbs_variances.append(
                    WBSVariance(
                        wbs_id=elem["id"],
                        wbs_code=code,
                        wbs_name=elem["name"],
                        change_type="removed",
                        bac_baseline=Decimal(elem["budgeted_cost"]),
                    )
                )

    def _calculate_summaries(self, result: ComparisonResult) -> None:
        """Calculate summary metrics."""
        # BAC variance
        result.bac_variance = result.total_bac_current - result.total_bac_baseline

        if result.total_bac_baseline > 0:
            result.bac_variance_percent = (
                result.bac_variance / result.total_bac_baseline * 100
            ).quantize(Decimal("0.01"))


def comparison_result_to_dict(result: ComparisonResult) -> dict[str, Any]:
    """Convert ComparisonResult to dictionary for API response."""
    return {
        "baseline_id": str(result.baseline_id),
        "baseline_name": result.baseline_name,
        "baseline_version": result.baseline_version,
        "comparison_date": result.comparison_date.isoformat(),
        # Summary
        "total_bac_baseline": str(result.total_bac_baseline),
        "total_bac_current": str(result.total_bac_current),
        "bac_variance": str(result.bac_variance),
        "bac_variance_percent": str(result.bac_variance_percent),
        "project_finish_baseline": result.project_finish_baseline.isoformat()
        if result.project_finish_baseline
        else None,
        "project_finish_current": result.project_finish_current.isoformat()
        if result.project_finish_current
        else None,
        "schedule_variance_days": result.schedule_variance_days,
        # Activity counts
        "activities_baseline": result.activities_baseline,
        "activities_current": result.activities_current,
        "activities_added": result.activities_added,
        "activities_removed": result.activities_removed,
        "activities_modified": result.activities_modified,
        "activities_unchanged": result.activities_unchanged,
        # Critical path
        "critical_path_baseline": result.critical_path_baseline,
        "critical_path_current": result.critical_path_current,
        "critical_path_changed": result.critical_path_changed,
        # WBS counts
        "wbs_baseline": result.wbs_baseline,
        "wbs_current": result.wbs_current,
        "wbs_added": result.wbs_added,
        "wbs_removed": result.wbs_removed,
        "wbs_modified": result.wbs_modified,
        # Activity code lists
        "added_activity_codes": result.added_activity_codes,
        "removed_activity_codes": result.removed_activity_codes,
        "modified_activity_codes": result.modified_activity_codes,
        # Detailed variances
        "activity_variances": [
            {
                "activity_id": v.activity_id,
                "activity_code": v.activity_code,
                "activity_name": v.activity_name,
                "change_type": v.change_type,
                "duration_baseline": v.duration_baseline,
                "duration_current": v.duration_current,
                "duration_variance": v.duration_variance,
                "start_baseline": v.start_baseline.isoformat() if v.start_baseline else None,
                "start_current": v.start_current.isoformat() if v.start_current else None,
                "start_variance_days": v.start_variance_days,
                "finish_baseline": v.finish_baseline.isoformat() if v.finish_baseline else None,
                "finish_current": v.finish_current.isoformat() if v.finish_current else None,
                "finish_variance_days": v.finish_variance_days,
                "bac_baseline": str(v.bac_baseline) if v.bac_baseline else None,
                "bac_current": str(v.bac_current) if v.bac_current else None,
                "bac_variance": str(v.bac_variance) if v.bac_variance else None,
                "was_critical": v.was_critical,
                "is_critical": v.is_critical,
            }
            for v in result.activity_variances
        ],
        "wbs_variances": [
            {
                "wbs_id": v.wbs_id,
                "wbs_code": v.wbs_code,
                "wbs_name": v.wbs_name,
                "change_type": v.change_type,
                "bac_baseline": str(v.bac_baseline) if v.bac_baseline else None,
                "bac_current": str(v.bac_current) if v.bac_current else None,
                "bac_variance": str(v.bac_variance) if v.bac_variance else None,
            }
            for v in result.wbs_variances
        ],
    }
