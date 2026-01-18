"""Repository for JiraSyncLog model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.jira_sync_log import JiraSyncLog
from src.repositories.base import BaseRepository


class JiraSyncLogRepository(BaseRepository[JiraSyncLog]):
    """Repository for Jira sync log operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with JiraSyncLog model."""
        super().__init__(JiraSyncLog, session)

    async def get_by_integration(
        self,
        integration_id: UUID,
        limit: int = 100,
    ) -> list[JiraSyncLog]:
        """Get sync logs for an integration.

        Args:
            integration_id: Jira integration UUID
            limit: Maximum number of records to return

        Returns:
            List of JiraSyncLog instances ordered by created_at desc
        """
        query = (
            select(JiraSyncLog)
            .where(JiraSyncLog.integration_id == integration_id)
            .order_by(JiraSyncLog.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_mapping(
        self,
        mapping_id: UUID,
        limit: int = 50,
    ) -> list[JiraSyncLog]:
        """Get sync logs for a specific mapping.

        Args:
            mapping_id: Jira mapping UUID
            limit: Maximum number of records to return

        Returns:
            List of JiraSyncLog instances
        """
        query = (
            select(JiraSyncLog)
            .where(JiraSyncLog.mapping_id == mapping_id)
            .order_by(JiraSyncLog.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest(
        self,
        integration_id: UUID,
    ) -> JiraSyncLog | None:
        """Get the most recent sync log for an integration.

        Args:
            integration_id: Jira integration UUID

        Returns:
            Most recent JiraSyncLog or None
        """
        query = (
            select(JiraSyncLog)
            .where(JiraSyncLog.integration_id == integration_id)
            .order_by(JiraSyncLog.created_at.desc())
            .limit(1)
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_status(
        self,
        integration_id: UUID,
        status: str,
        limit: int = 50,
    ) -> list[JiraSyncLog]:
        """Get sync logs by status.

        Args:
            integration_id: Jira integration UUID
            status: Sync status (success, failed, partial)
            limit: Maximum number of records to return

        Returns:
            List of JiraSyncLog instances
        """
        query = (
            select(JiraSyncLog)
            .where(
                JiraSyncLog.integration_id == integration_id,
                JiraSyncLog.status == status,
            )
            .order_by(JiraSyncLog.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_date_range(
        self,
        integration_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[JiraSyncLog]:
        """Get sync logs within a date range.

        Args:
            integration_id: Jira integration UUID
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of JiraSyncLog instances
        """
        query = (
            select(JiraSyncLog)
            .where(
                JiraSyncLog.integration_id == integration_id,
                JiraSyncLog.created_at >= start_date,
                JiraSyncLog.created_at <= end_date,
            )
            .order_by(JiraSyncLog.created_at.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_stats(
        self,
        integration_id: UUID,
    ) -> dict[str, int]:
        """Get sync statistics for an integration.

        Args:
            integration_id: Jira integration UUID

        Returns:
            Dict with total_syncs, total_items, success_count, failed_count
        """
        # Count by status
        status_query = (
            select(JiraSyncLog.status, func.count(JiraSyncLog.id))
            .where(JiraSyncLog.integration_id == integration_id)
            .group_by(JiraSyncLog.status)
        )
        status_result = await self.session.execute(status_query)
        status_counts: dict[str, int] = {row[0]: row[1] for row in status_result.all()}

        # Total items synced
        items_query = select(func.sum(JiraSyncLog.items_synced)).where(
            JiraSyncLog.integration_id == integration_id
        )
        items_result = await self.session.execute(items_query)
        total_items = items_result.scalar_one() or 0

        return {
            "total_syncs": sum(status_counts.values()),
            "total_items": total_items,
            "success_count": status_counts.get("success", 0),
            "failed_count": status_counts.get("failed", 0),
            "partial_count": status_counts.get("partial", 0),
        }

    async def cleanup_old_logs(
        self,
        integration_id: UUID,
        keep_count: int = 1000,
    ) -> int:
        """Delete old sync logs, keeping the most recent ones.

        Args:
            integration_id: Jira integration UUID
            keep_count: Number of recent logs to keep

        Returns:
            Number of deleted logs
        """
        # Get IDs of logs to keep
        keep_query = (
            select(JiraSyncLog.id)
            .where(JiraSyncLog.integration_id == integration_id)
            .order_by(JiraSyncLog.created_at.desc())
            .limit(keep_count)
        )
        keep_result = await self.session.execute(keep_query)
        keep_ids = set(keep_result.scalars().all())

        # Get all logs for integration
        all_query = select(JiraSyncLog).where(JiraSyncLog.integration_id == integration_id)
        all_result = await self.session.execute(all_query)
        all_logs = list(all_result.scalars().all())

        # Delete logs not in keep set
        deleted_count = 0
        for log in all_logs:
            if log.id not in keep_ids:
                await self.session.delete(log)
                deleted_count += 1

        if deleted_count > 0:
            await self.session.flush()

        return deleted_count
