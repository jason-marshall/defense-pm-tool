"""Repository for JiraIntegration model."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.jira_integration import JiraIntegration
from src.repositories.base import BaseRepository


class JiraIntegrationRepository(BaseRepository[JiraIntegration]):
    """Repository for Jira integration CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with JiraIntegration model."""
        super().__init__(JiraIntegration, session)

    async def get_by_program(
        self,
        program_id: UUID,
        include_deleted: bool = False,
    ) -> JiraIntegration | None:
        """Get Jira integration for a program.

        Args:
            program_id: Program UUID
            include_deleted: Whether to include soft-deleted records

        Returns:
            JiraIntegration or None if not found
        """
        query = select(JiraIntegration).where(JiraIntegration.program_id == program_id)
        query = self._apply_soft_delete_filter(query, include_deleted)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_integrations(self) -> list[JiraIntegration]:
        """Get all active (sync_enabled=True) integrations.

        Returns:
            List of active JiraIntegration instances
        """
        query = (
            select(JiraIntegration)
            .where(
                JiraIntegration.sync_enabled.is_(True),
                JiraIntegration.deleted_at.is_(None),
            )
            .order_by(JiraIntegration.created_at)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: str,
        include_deleted: bool = False,
    ) -> list[JiraIntegration]:
        """Get integrations by sync status.

        Args:
            status: Sync status value (active, paused, error, disconnected)
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of matching JiraIntegration instances
        """
        query = select(JiraIntegration).where(JiraIntegration.sync_status == status)
        query = self._apply_soft_delete_filter(query, include_deleted)

        result = await self.session.execute(query)
        return list(result.scalars().all())
