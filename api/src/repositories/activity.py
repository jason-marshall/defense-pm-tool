"""Repository for Activity model."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.activity import Activity
from src.repositories.base import BaseRepository
from src.services.cache_service import get_cache_service
from src.services.dashboard_cache import dashboard_cache


class ActivityRepository(BaseRepository[Activity]):
    """Repository for Activity CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with Activity model."""
        super().__init__(Activity, session)

    async def get_by_program(
        self,
        program_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Activity]:
        """Get all activities for a program."""
        result = await self.session.execute(
            select(Activity)
            .where(Activity.program_id == program_id)
            .offset(skip)
            .limit(limit)
            .order_by(Activity.code)
        )
        return list(result.scalars().all())

    async def get_with_dependencies(self, id: UUID) -> Activity | None:
        """Get an activity with its dependencies loaded."""
        result = await self.session.execute(
            select(Activity)
            .where(Activity.id == id)
            .options(
                selectinload(Activity.predecessor_links),
                selectinload(Activity.successor_links),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_with_dependencies(
        self,
        program_id: UUID,
    ) -> list[Activity]:
        """Get all activities for a program with dependencies loaded."""
        result = await self.session.execute(
            select(Activity)
            .where(Activity.program_id == program_id)
            .options(
                selectinload(Activity.predecessor_links),
                selectinload(Activity.successor_links),
            )
        )
        return list(result.scalars().all())

    async def get_by_code(
        self,
        program_id: UUID,
        code: str,
    ) -> Activity | None:
        """Get an activity by its code within a program."""
        result = await self.session.execute(
            select(Activity).where(
                Activity.program_id == program_id,
                Activity.code == code,
            )
        )
        return result.scalar_one_or_none()

    async def get_critical_path(self, program_id: UUID) -> list[Activity]:
        """Get activities on the critical path (zero total float)."""
        result = await self.session.execute(
            select(Activity)
            .where(
                Activity.program_id == program_id,
                Activity.total_float == 0,
            )
            .order_by(Activity.early_start)
        )
        return list(result.scalars().all())

    async def create(self, data: dict[str, Any]) -> Activity:
        """Create activity and invalidate related caches.

        Invalidates CPM and dashboard caches for the program.
        """
        activity = await super().create(data)

        # Invalidate caches
        await self._invalidate_caches(activity.program_id)

        return activity

    async def update(
        self,
        db_obj: Activity,
        data: dict[str, Any],
    ) -> Activity:
        """Update activity and invalidate related caches.

        Invalidates CPM and dashboard caches for the program.
        """
        activity = await super().update(db_obj, data)

        # Invalidate caches
        await self._invalidate_caches(activity.program_id)

        return activity

    async def delete(
        self,
        id: UUID,
        soft: bool = True,
    ) -> bool:
        """Delete activity and invalidate related caches.

        Invalidates CPM and dashboard caches for the program.
        """
        # Get program_id before deletion
        activity = await self.get_by_id(id, include_deleted=not soft)
        program_id = activity.program_id if activity else None

        result = await super().delete(id, soft)

        # Invalidate caches if deletion was successful
        if result and program_id:
            await self._invalidate_caches(program_id)

        return result

    async def _invalidate_caches(self, program_id: UUID) -> None:
        """Invalidate all caches related to activities for a program.

        Args:
            program_id: Program UUID
        """
        cache = get_cache_service()

        # Invalidate CPM cache (schedule calculations depend on activities)
        await cache.invalidate_cpm(program_id)

        # Invalidate dashboard caches (activities, schedule, S-curve)
        await dashboard_cache.invalidate_on_activity_update(program_id)
