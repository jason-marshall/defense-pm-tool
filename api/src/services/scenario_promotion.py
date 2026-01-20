"""Scenario promotion service for creating baselines from scenarios.

This service handles the promotion workflow:
1. Validate scenario is eligible for promotion
2. Create new baseline with scenario changes applied
3. Mark scenario as promoted
4. Log promotion for audit trail
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from uuid import UUID

    from src.models.baseline import Baseline
    from src.models.scenario import Scenario, ScenarioChange
    from src.repositories.activity import ActivityRepository
    from src.repositories.baseline import BaselineRepository
    from src.repositories.scenario import ScenarioRepository
    from src.repositories.wbs import WBSElementRepository

logger = structlog.get_logger(__name__)


class PromotionError(Exception):
    """Base exception for promotion operations."""

    def __init__(self, message: str, code: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class ScenarioNotFoundError(PromotionError):
    """Scenario not found."""

    pass


class ScenarioNotEligibleError(PromotionError):
    """Scenario not eligible for promotion."""

    pass


class BaselineCreationError(PromotionError):
    """Failed to create baseline."""

    pass


@dataclass
class PromotionResult:
    """Result of scenario promotion."""

    success: bool
    scenario_id: UUID
    baseline_id: UUID | None = None
    baseline_name: str | None = None
    baseline_version: int | None = None
    changes_count: int = 0
    error_message: str | None = None
    duration_ms: int = 0


class ScenarioPromotionService:
    """
    Service for promoting scenarios to baselines.

    Promotion workflow:
    1. Validate scenario exists and is eligible (not already promoted)
    2. Get all scenario changes
    3. Apply changes to create modified schedule/cost snapshots
    4. Create new baseline with snapshots
    5. Mark scenario as promoted with baseline reference

    Attributes:
        scenario_repo: Repository for scenarios
        baseline_repo: Repository for baselines
        activity_repo: Repository for activities
        wbs_repo: Repository for WBS elements
    """

    def __init__(
        self,
        scenario_repo: ScenarioRepository,
        baseline_repo: BaselineRepository,
        activity_repo: ActivityRepository,
        wbs_repo: WBSElementRepository,
    ) -> None:
        """Initialize promotion service with repositories."""
        self.scenario_repo = scenario_repo
        self.baseline_repo = baseline_repo
        self.activity_repo = activity_repo
        self.wbs_repo = wbs_repo

    async def promote_scenario(
        self,
        scenario_id: UUID,
        baseline_name: str,
        baseline_description: str | None = None,
        created_by_id: UUID | None = None,
    ) -> PromotionResult:
        """
        Promote a scenario to a new baseline.

        Args:
            scenario_id: Scenario to promote
            baseline_name: Name for the new baseline
            baseline_description: Optional description
            created_by_id: User performing promotion

        Returns:
            PromotionResult with baseline details

        Raises:
            ScenarioNotFoundError: If scenario doesn't exist
            ScenarioNotEligibleError: If scenario already promoted
            BaselineCreationError: If baseline creation fails
        """
        start_time = time.time()

        try:
            # 1. Get and validate scenario
            scenario = await self._get_and_validate_scenario(scenario_id)

            # 2. Get scenario changes
            changes = await self.scenario_repo.get_changes(scenario_id)

            # 3. Get current program data
            activities = await self.activity_repo.get_by_program(scenario.program_id)
            wbs_elements = await self.wbs_repo.get_by_program(scenario.program_id)

            # 4. Build snapshots with changes applied
            schedule_snapshot = self._build_schedule_snapshot(activities, changes)
            wbs_snapshot = self._build_wbs_snapshot(wbs_elements, changes)
            cost_snapshot = self._build_cost_snapshot(wbs_elements, changes)

            # 5. Get next baseline version
            existing_baselines = await self.baseline_repo.get_by_program(scenario.program_id)
            next_version = len(existing_baselines) + 1

            # 6. Create new baseline
            baseline = await self._create_baseline(
                program_id=scenario.program_id,
                name=baseline_name,
                description=baseline_description,
                version=next_version,
                schedule_snapshot=schedule_snapshot,
                wbs_snapshot=wbs_snapshot,
                cost_snapshot=cost_snapshot,
                created_by_id=created_by_id or scenario.created_by_id,
            )

            # 7. Mark scenario as promoted
            await self.scenario_repo.mark_promoted(
                scenario_id=scenario_id,
                baseline_id=baseline.id,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "scenario_promoted",
                scenario_id=str(scenario_id),
                baseline_id=str(baseline.id),
                baseline_name=baseline_name,
                baseline_version=next_version,
                changes_count=len(changes),
                duration_ms=duration_ms,
            )

            return PromotionResult(
                success=True,
                scenario_id=scenario_id,
                baseline_id=baseline.id,
                baseline_name=baseline_name,
                baseline_version=next_version,
                changes_count=len(changes),
                duration_ms=duration_ms,
            )

        except (ScenarioNotFoundError, ScenarioNotEligibleError):
            raise
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "scenario_promotion_failed",
                scenario_id=str(scenario_id),
                error=str(e),
            )
            raise BaselineCreationError(
                f"Failed to create baseline: {e}",
                "BASELINE_CREATION_FAILED",
                {"scenario_id": str(scenario_id)},
            ) from e

    async def _get_and_validate_scenario(self, scenario_id: UUID) -> Scenario:
        """Get scenario and validate it's eligible for promotion."""
        scenario = await self.scenario_repo.get(scenario_id)

        if not scenario:
            raise ScenarioNotFoundError(
                f"Scenario {scenario_id} not found",
                "SCENARIO_NOT_FOUND",
            )

        if scenario.status == "promoted":
            raise ScenarioNotEligibleError(
                f"Scenario {scenario_id} already promoted",
                "ALREADY_PROMOTED",
                {"promoted_at": str(scenario.promoted_at) if scenario.promoted_at else None},
            )

        if scenario.status == "archived":
            raise ScenarioNotEligibleError(
                f"Scenario {scenario_id} is archived",
                "SCENARIO_ARCHIVED",
            )

        return scenario

    async def _create_baseline(
        self,
        program_id: UUID,
        name: str,
        description: str | None,
        version: int,
        schedule_snapshot: dict[str, Any],
        wbs_snapshot: dict[str, Any],
        cost_snapshot: dict[str, Any],
        created_by_id: UUID,
    ) -> Baseline:
        """Create a new baseline with the provided snapshots."""
        from src.models.baseline import Baseline  # noqa: PLC0415

        # Calculate summary metrics from snapshots
        activity_count = len(schedule_snapshot.get("activities", []))
        wbs_count = len(wbs_snapshot.get("elements", []))
        total_bac = Decimal(cost_snapshot.get("total_bac", "0"))

        baseline = Baseline(
            program_id=program_id,
            name=name,
            version=version,
            description=description,
            schedule_snapshot=schedule_snapshot,
            cost_snapshot=cost_snapshot,
            wbs_snapshot=wbs_snapshot,
            total_bac=total_bac,
            activity_count=activity_count,
            wbs_count=wbs_count,
            created_by_id=created_by_id,
        )

        self.baseline_repo.session.add(baseline)
        await self.baseline_repo.session.flush()
        return baseline

    def _build_schedule_snapshot(
        self,
        activities: list[Any],
        changes: list[ScenarioChange],
    ) -> dict[str, Any]:
        """Build schedule snapshot with changes applied."""
        # Apply changes
        modified_activities = []
        for activity in activities:
            activity_data = {
                "id": str(activity.id),
                "code": activity.code,
                "name": activity.name,
                "duration": activity.duration,
                "early_start": activity.early_start.isoformat() if activity.early_start else None,
                "early_finish": activity.early_finish.isoformat()
                if activity.early_finish
                else None,
                "late_start": activity.late_start.isoformat() if activity.late_start else None,
                "late_finish": activity.late_finish.isoformat() if activity.late_finish else None,
                "total_float": activity.total_float,
                "is_critical": activity.is_critical,
                "budgeted_cost": str(activity.budgeted_cost) if activity.budgeted_cost else "0",
                "percent_complete": str(activity.percent_complete)
                if activity.percent_complete
                else "0",
            }

            # Apply any changes for this activity
            for change in changes:
                if (
                    change.entity_type == "activity"
                    and str(change.entity_id) == str(activity.id)
                    and change.field_name
                    and change.change_type == "update"
                ):
                    # Handle the new_value which might be JSON or a simple value
                    new_val = change.new_value
                    if isinstance(new_val, dict) and "value" in new_val:
                        activity_data[change.field_name] = new_val["value"]
                    else:
                        activity_data[change.field_name] = new_val

            modified_activities.append(activity_data)

        return {
            "activities": modified_activities,
            "snapshot_at": datetime.now(UTC).isoformat(),
        }

    def _build_wbs_snapshot(
        self,
        wbs_elements: list[Any],
        changes: list[ScenarioChange],
    ) -> dict[str, Any]:
        """Build WBS snapshot with changes applied."""
        modified_wbs = []
        for wbs in wbs_elements:
            wbs_data = {
                "id": str(wbs.id),
                "code": wbs.wbs_code,
                "name": wbs.name,
                "level": wbs.level,
                "path": str(wbs.path) if wbs.path else None,
            }

            # Apply any changes for this WBS
            for change in changes:
                if (
                    change.entity_type == "wbs"
                    and str(change.entity_id) == str(wbs.id)
                    and change.field_name
                    and change.change_type == "update"
                ):
                    new_val = change.new_value
                    if isinstance(new_val, dict) and "value" in new_val:
                        wbs_data[change.field_name] = new_val["value"]
                    else:
                        wbs_data[change.field_name] = new_val

            modified_wbs.append(wbs_data)

        return {
            "elements": modified_wbs,
            "snapshot_at": datetime.now(UTC).isoformat(),
        }

    def _build_cost_snapshot(
        self,
        wbs_elements: list[Any],
        changes: list[ScenarioChange],
    ) -> dict[str, Any]:
        """Build cost snapshot with changes applied."""
        cost_by_wbs = {}
        for wbs in wbs_elements:
            budgeted_cost = getattr(wbs, "budget_at_completion", None) or Decimal("0")

            # Check for cost changes
            for change in changes:
                if (
                    change.entity_type == "wbs"
                    and str(change.entity_id) == str(wbs.id)
                    and change.field_name in ("budgeted_cost", "budget_at_completion")
                    and change.change_type == "update"
                ):
                    new_val = change.new_value
                    if isinstance(new_val, dict) and "value" in new_val:
                        budgeted_cost = Decimal(str(new_val["value"]))
                    else:
                        budgeted_cost = Decimal(str(new_val))

            cost_by_wbs[str(wbs.id)] = str(budgeted_cost)

        total_bac = sum(Decimal(v) for v in cost_by_wbs.values())

        return {
            "by_wbs": cost_by_wbs,
            "total_bac": str(total_bac),
            "snapshot_at": datetime.now(UTC).isoformat(),
        }
