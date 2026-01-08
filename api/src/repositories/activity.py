"""Repository for Activity model."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.activity import Activity
from src.repositories.base import BaseRepository


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
                selectinload(Activity.predecessor_dependencies),
                selectinload(Activity.successor_dependencies),
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
                selectinload(Activity.predecessor_dependencies),
                selectinload(Activity.successor_dependencies),
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
