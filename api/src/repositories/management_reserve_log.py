"""Repository for ManagementReserveLog model."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.management_reserve_log import ManagementReserveLog
from src.repositories.base import BaseRepository


class ManagementReserveLogRepository(BaseRepository[ManagementReserveLog]):
    """
    Repository for Management Reserve log CRUD operations.

    Provides methods for tracking MR changes per DFARS requirements.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__(ManagementReserveLog, session)

    async def get_by_program(
        self,
        program_id: UUID,
        include_deleted: bool = False,
    ) -> list[ManagementReserveLog]:
        """
        Get all MR log entries for a program.

        Args:
            program_id: Program ID
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of MR log entries ordered by creation date
        """
        query = select(ManagementReserveLog).where(ManagementReserveLog.program_id == program_id)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = query.order_by(ManagementReserveLog.created_at.asc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_period(
        self,
        period_id: UUID,
        include_deleted: bool = False,
    ) -> list[ManagementReserveLog]:
        """
        Get MR log entries for a specific period.

        Args:
            period_id: EVMS Period ID
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of MR log entries for the period
        """
        query = select(ManagementReserveLog).where(ManagementReserveLog.period_id == period_id)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = query.order_by(ManagementReserveLog.created_at.asc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_for_program(
        self,
        program_id: UUID,
        include_deleted: bool = False,
    ) -> ManagementReserveLog | None:
        """
        Get the most recent MR log entry for a program.

        Args:
            program_id: Program ID
            include_deleted: Whether to include soft-deleted records

        Returns:
            Most recent MR log entry or None
        """
        query = select(ManagementReserveLog).where(ManagementReserveLog.program_id == program_id)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = query.order_by(ManagementReserveLog.created_at.desc())
        query = query.limit(1)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_history(
        self,
        program_id: UUID,
        limit: int = 12,
        include_deleted: bool = False,
    ) -> list[ManagementReserveLog]:
        """
        Get MR history for a program (most recent entries).

        Args:
            program_id: Program ID
            limit: Maximum number of entries to return
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of recent MR log entries
        """
        query = select(ManagementReserveLog).where(ManagementReserveLog.program_id == program_id)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = query.order_by(ManagementReserveLog.created_at.desc())
        query = query.limit(limit)

        result = await self.session.execute(query)
        # Return in chronological order
        return list(reversed(result.scalars().all()))
