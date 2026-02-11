"""Repository for Scenario model."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.scenario import Scenario, ScenarioChange
from src.repositories.base import BaseRepository


class ScenarioRepository(BaseRepository[Scenario]):
    """Repository for Scenario CRUD operations."""

    model = Scenario

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with Scenario model."""
        super().__init__(Scenario, session)

    async def get_with_changes(self, scenario_id: UUID) -> Scenario | None:
        """Get scenario with its changes eagerly loaded."""
        query = (
            select(self.model)
            .options(selectinload(self.model.changes))
            .where(self.model.id == scenario_id)
            .where(self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_program(
        self,
        program_id: UUID,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False,
        include_deleted: bool = False,
    ) -> list[Scenario]:
        """Get all scenarios for a program."""
        query = select(self.model).where(self.model.program_id == program_id)

        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))

        if active_only:
            query = query.where(self.model.is_active.is_(True))

        query = query.order_by(self.model.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_program(
        self,
        program_id: UUID,
        active_only: bool = False,
        include_deleted: bool = False,
    ) -> int:
        """Count scenarios for a program."""
        query = (
            select(func.count()).select_from(self.model).where(self.model.program_id == program_id)
        )

        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))

        if active_only:
            query = query.where(self.model.is_active.is_(True))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def add_change(
        self,
        scenario_id: UUID,
        entity_type: str,
        entity_id: UUID,
        change_type: str,
        entity_code: str | None = None,
        field_name: str | None = None,
        old_value: Any | None = None,
        new_value: Any | None = None,
    ) -> ScenarioChange:
        """
        Add a change to a scenario.

        This also invalidates any cached results.
        """
        # Get scenario to invalidate cache
        scenario = await self.get(scenario_id)
        if scenario:
            scenario.invalidate_cache()

        change = ScenarioChange(
            scenario_id=scenario_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_code=entity_code,
            change_type=change_type,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
        )

        self.session.add(change)
        await self.session.flush()
        return change

    async def get_changes(
        self,
        scenario_id: UUID,
        entity_type: str | None = None,
    ) -> list[ScenarioChange]:
        """Get changes for a scenario, optionally filtered by entity type."""
        query = (
            select(ScenarioChange)
            .where(ScenarioChange.scenario_id == scenario_id)
            .where(ScenarioChange.deleted_at.is_(None))
        )

        if entity_type:
            query = query.where(ScenarioChange.entity_type == entity_type)

        query = query.order_by(ScenarioChange.created_at)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_changes_for_entity(
        self,
        scenario_id: UUID,
        entity_id: UUID,
    ) -> list[ScenarioChange]:
        """Get all changes for a specific entity in a scenario."""
        query = (
            select(ScenarioChange)
            .where(ScenarioChange.scenario_id == scenario_id)
            .where(ScenarioChange.entity_id == entity_id)
            .where(ScenarioChange.deleted_at.is_(None))
            .order_by(ScenarioChange.created_at)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def remove_change(self, change_id: UUID) -> bool:
        """Remove a change from a scenario."""
        query = select(ScenarioChange).where(ScenarioChange.id == change_id)
        result = await self.session.execute(query)
        change = result.scalar_one_or_none()

        if change:
            # Invalidate scenario cache
            scenario = await self.get(change.scenario_id)
            if scenario:
                scenario.invalidate_cache()

            await self.session.delete(change)
            return True

        return False

    async def update_cache(
        self,
        scenario_id: UUID,
        results: dict[str, Any],
    ) -> Scenario | None:
        """Update cached CPM results for a scenario."""
        scenario = await self.get(scenario_id)
        if scenario:
            scenario.results_cache = results
            await self.session.flush()
        return scenario

    async def mark_promoted(
        self,
        scenario_id: UUID,
        baseline_id: UUID,
    ) -> Scenario | None:
        """Mark scenario as promoted and link to baseline."""
        scenario = await self.get(scenario_id)
        if scenario:
            scenario.status = "promoted"
            scenario.promoted_at = datetime.now(UTC)
            scenario.promoted_baseline_id = baseline_id
            scenario.is_active = False
            await self.session.flush()
        return scenario

    async def archive(self, scenario_id: UUID) -> Scenario | None:
        """Archive a scenario (keep but mark inactive)."""
        scenario = await self.get(scenario_id)
        if scenario:
            scenario.status = "archived"
            scenario.is_active = False
            await self.session.flush()
        return scenario

    async def branch_from_scenario(
        self,
        parent_scenario_id: UUID,
        name: str,
        description: str | None,
        created_by_id: UUID,
    ) -> Scenario | None:
        """
        Create a new scenario branched from an existing one.

        The new scenario inherits all changes from the parent.
        """
        parent = await self.get_with_changes(parent_scenario_id)
        if not parent:
            return None

        # Create new scenario
        new_scenario = Scenario(
            program_id=parent.program_id,
            baseline_id=parent.baseline_id,
            parent_scenario_id=parent_scenario_id,
            name=name,
            description=description,
            status="draft",
            is_active=True,
            created_by_id=created_by_id,
        )

        self.session.add(new_scenario)
        await self.session.flush()

        # Copy changes from parent
        for change in parent.changes:
            new_change = ScenarioChange(
                scenario_id=new_scenario.id,
                entity_type=change.entity_type,
                entity_id=change.entity_id,
                entity_code=change.entity_code,
                change_type=change.change_type,
                field_name=change.field_name,
                old_value=change.old_value,
                new_value=change.new_value,
            )
            self.session.add(new_change)

        await self.session.flush()
        return new_scenario

    async def get_change_summary(self, scenario_id: UUID) -> dict[str, int]:
        """Get summary counts of changes by type and entity."""
        changes = await self.get_changes(scenario_id)

        summary = {
            "activities_created": 0,
            "activities_updated": 0,
            "activities_deleted": 0,
            "dependencies_created": 0,
            "dependencies_updated": 0,
            "dependencies_deleted": 0,
            "wbs_created": 0,
            "wbs_updated": 0,
            "wbs_deleted": 0,
            "total_changes": len(changes),
        }

        # Pluralization map for entity types
        plural_map = {
            "activity": "activities",
            "dependency": "dependencies",
            "wbs": "wbs",
        }

        for change in changes:
            entity_plural = plural_map.get(change.entity_type, f"{change.entity_type}s")
            key = f"{entity_plural}_{change.change_type}d"
            if key in summary:
                summary[key] += 1

        return summary
