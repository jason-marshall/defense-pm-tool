"""Repository for Dependency model."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity
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

    async def get_by_program(self, program_id: UUID) -> list[Dependency]:
        """
        Get all dependencies for activities in a program.

        Args:
            program_id: ID of the program

        Returns:
            List of dependencies where predecessor activity belongs to the program
        """
        # Get all activity IDs for the program
        activity_result = await self.session.execute(
            select(Activity.id).where(Activity.program_id == program_id)
        )
        activity_ids = [row[0] for row in activity_result.all()]

        if not activity_ids:
            return []

        # Get dependencies where predecessor is in the program
        result = await self.session.execute(
            select(Dependency).where(Dependency.predecessor_id.in_(activity_ids))
        )
        return list(result.scalars().all())
