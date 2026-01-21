"""Service for applying scenario changes to program data.

This service applies scenario delta changes to actual program entities:
- Activity changes (duration, cost, dates)
- WBS changes (budgeted_cost, name)
- Dependency changes (create, delete, modify)

WARNING: This operation modifies actual program data and should be
used with caution. Consider promoting to baseline instead for
non-destructive change tracking.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from uuid import UUID

    from src.models.scenario import ScenarioChange
    from src.repositories.activity import ActivityRepository
    from src.repositories.dependency import DependencyRepository
    from src.repositories.scenario import ScenarioRepository
    from src.repositories.wbs import WBSElementRepository

logger = structlog.get_logger(__name__)


class ApplyChangesError(Exception):
    """Base exception for apply operations."""

    def __init__(self, message: str, code: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class ScenarioNotFoundError(ApplyChangesError):
    """Scenario not found."""

    pass


class ChangeApplicationError(ApplyChangesError):
    """Failed to apply a specific change."""

    pass


@dataclass
class ApplyResult:
    """Result of applying scenario changes."""

    success: bool
    scenario_id: UUID
    changes_applied: int = 0
    changes_failed: int = 0
    activities_modified: int = 0
    wbs_modified: int = 0
    dependencies_modified: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


class ScenarioApplyService:
    """
    Service for applying scenario changes to program data.

    Processes each change type:
    - activity: Update activity fields
    - wbs: Update WBS fields
    - dependency: Create/update/delete dependencies

    Changes are applied in order - partial failures are tracked.
    On success, the scenario is archived.
    """

    def __init__(
        self,
        scenario_repo: ScenarioRepository,
        activity_repo: ActivityRepository,
        wbs_repo: WBSElementRepository,
        dependency_repo: DependencyRepository,
    ) -> None:
        """Initialize apply service."""
        self.scenario_repo = scenario_repo
        self.activity_repo = activity_repo
        self.wbs_repo = wbs_repo
        self.dependency_repo = dependency_repo

    async def apply_changes(
        self,
        scenario_id: UUID,
        confirm: bool = False,
    ) -> ApplyResult:
        """
        Apply all scenario changes to program data.

        Args:
            scenario_id: Scenario with changes to apply
            confirm: Must be True to actually apply (safety check)

        Returns:
            ApplyResult with summary of changes

        Raises:
            ScenarioNotFoundError: If scenario doesn't exist
            ApplyChangesError: If confirm is False or scenario is promoted
        """
        start_time = time.time()
        result = ApplyResult(success=True, scenario_id=scenario_id)

        if not confirm:
            raise ApplyChangesError(
                "Must confirm to apply changes (set confirm=True)",
                "CONFIRM_REQUIRED",
            )

        # Validate scenario
        await self._validate_scenario(scenario_id)

        # Get all changes
        changes = await self.scenario_repo.get_changes(scenario_id)

        if not changes:
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result

        # Apply all changes
        await self._apply_all_changes(changes, result)

        result.duration_ms = int((time.time() - start_time) * 1000)

        if result.success:
            # Mark scenario as archived after successful application
            await self.scenario_repo.archive(scenario_id)

            logger.info(
                "scenario_changes_applied",
                scenario_id=str(scenario_id),
                changes_applied=result.changes_applied,
                activities_modified=result.activities_modified,
                wbs_modified=result.wbs_modified,
                dependencies_modified=result.dependencies_modified,
                duration_ms=result.duration_ms,
            )
        else:
            logger.error(
                "scenario_apply_partial_failure",
                scenario_id=str(scenario_id),
                changes_applied=result.changes_applied,
                changes_failed=result.changes_failed,
                errors=result.errors,
            )

        return result

    async def _validate_scenario(self, scenario_id: UUID) -> None:
        """Validate scenario exists and is eligible for applying changes."""
        scenario = await self.scenario_repo.get(scenario_id)
        if not scenario:
            raise ScenarioNotFoundError(
                f"Scenario {scenario_id} not found",
                "SCENARIO_NOT_FOUND",
            )

        if scenario.status == "promoted":
            raise ApplyChangesError(
                "Cannot apply changes from promoted scenario",
                "ALREADY_PROMOTED",
            )

        if scenario.status == "archived":
            raise ApplyChangesError(
                "Cannot apply changes from archived scenario",
                "SCENARIO_ARCHIVED",
            )

    async def _apply_all_changes(
        self,
        changes: list[ScenarioChange],
        result: ApplyResult,
    ) -> None:
        """Apply all changes grouped by entity type."""
        # Group changes by entity type
        change_handlers = {
            "activity": (self._apply_activity_change, "activities_modified"),
            "wbs": (self._apply_wbs_change, "wbs_modified"),
            "dependency": (self._apply_dependency_change, "dependencies_modified"),
        }

        for change in changes:
            handler_info = change_handlers.get(change.entity_type)
            if not handler_info:
                continue

            handler, count_attr = handler_info
            try:
                await handler(change)
                result.changes_applied += 1
                setattr(result, count_attr, getattr(result, count_attr) + 1)
            except Exception as e:
                result.changes_failed += 1
                result.errors.append(f"{change.entity_type.title()} {change.entity_id}: {e}")
                result.success = False

    async def _apply_activity_change(self, change: ScenarioChange) -> None:
        """Apply a single activity change."""
        if change.change_type == "delete":
            await self.activity_repo.delete(change.entity_id)
            return

        activity = await self.activity_repo.get_by_id(change.entity_id)
        if not activity:
            raise ChangeApplicationError(
                f"Activity {change.entity_id} not found",
                "ACTIVITY_NOT_FOUND",
            )

        if change.change_type == "update" and change.field_name:
            # Extract value from wrapped format if needed
            new_value = change.new_value
            if isinstance(new_value, dict) and "value" in new_value:
                new_value = new_value["value"]

            update_data = {change.field_name: new_value}
            await self.activity_repo.update(activity, update_data)

    async def _apply_wbs_change(self, change: ScenarioChange) -> None:
        """Apply a single WBS change."""
        if change.change_type == "delete":
            await self.wbs_repo.delete(change.entity_id)
            return

        wbs = await self.wbs_repo.get_by_id(change.entity_id)
        if not wbs:
            raise ChangeApplicationError(
                f"WBS {change.entity_id} not found",
                "WBS_NOT_FOUND",
            )

        if change.change_type == "update" and change.field_name:
            # Extract value from wrapped format if needed
            new_value = change.new_value
            if isinstance(new_value, dict) and "value" in new_value:
                new_value = new_value["value"]

            update_data = {change.field_name: new_value}
            await self.wbs_repo.update(wbs, update_data)

    async def _apply_dependency_change(self, change: ScenarioChange) -> None:
        """Apply a single dependency change."""
        if change.change_type == "delete":
            await self.dependency_repo.delete(change.entity_id)
            return

        if change.change_type == "create":
            # new_value should contain dependency data
            if isinstance(change.new_value, dict):
                await self.dependency_repo.create(**change.new_value)
            return

        # Update existing dependency
        dependency = await self.dependency_repo.get_by_id(change.entity_id)
        if not dependency:
            raise ChangeApplicationError(
                f"Dependency {change.entity_id} not found",
                "DEPENDENCY_NOT_FOUND",
            )

        if change.change_type == "update" and change.field_name:
            # Extract value from wrapped format if needed
            new_value = change.new_value
            if isinstance(new_value, dict) and "value" in new_value:
                new_value = new_value["value"]

            update_data = {change.field_name: new_value}
            await self.dependency_repo.update(dependency, update_data)
