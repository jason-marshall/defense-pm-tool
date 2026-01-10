"""Repository for Dependency model."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.dependency import Dependency
from src.repositories.base import BaseRepository


class DependencyRepository(BaseRepository[Dependency]):
    """Repository for Dependency CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with Dependency model."""
        super().__init__(Dependency, session)

    async def get_by_activities(
        self,
        predecessor_id: UUID,
        successor_id: UUID,
    ) -> Dependency | None:
        """Get a dependency by predecessor and successor IDs."""
        result = await self.session.execute(
            select(Dependency).where(
                Dependency.predecessor_id == predecessor_id,
                Dependency.successor_id == successor_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_activity(self, activity_id: UUID) -> list[Dependency]:
        """Get all dependencies where activity is predecessor or successor."""
        result = await self.session.execute(
            select(Dependency).where(
                or_(
                    Dependency.predecessor_id == activity_id,
                    Dependency.successor_id == activity_id,
                )
            )
        )
        return list(result.scalars().all())

    async def get_predecessors(self, activity_id: UUID) -> list[Dependency]:
        """Get all dependencies where activity is the successor."""
        result = await self.session.execute(
            select(Dependency).where(Dependency.successor_id == activity_id)
        )
        return list(result.scalars().all())

    async def get_successors(self, activity_id: UUID) -> list[Dependency]:
        """Get all dependencies where activity is the predecessor."""
        result = await self.session.execute(
            select(Dependency).where(Dependency.predecessor_id == activity_id)
        )
        return list(result.scalars().all())

    async def dependency_exists(
        self,
        predecessor_id: UUID,
        successor_id: UUID,
    ) -> bool:
        """Check if a dependency already exists between two activities."""
        result = await self.session.execute(
            select(Dependency).where(
                Dependency.predecessor_id == predecessor_id,
                Dependency.successor_id == successor_id,
            )
        )
        return result.scalar_one_or_none() is not None
