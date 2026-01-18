"""Repository for JiraMapping model."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.jira_mapping import JiraMapping
from src.models.wbs import WBSElement
from src.repositories.base import BaseRepository


class JiraMappingRepository(BaseRepository[JiraMapping]):
    """Repository for Jira mapping CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with JiraMapping model."""
        super().__init__(JiraMapping, session)

    async def get_by_wbs(
        self,
        integration_id: UUID,
        wbs_id: UUID,
        include_deleted: bool = False,
    ) -> JiraMapping | None:
        """Get mapping for a WBS element.

        Args:
            integration_id: Jira integration UUID
            wbs_id: WBS element UUID
            include_deleted: Whether to include soft-deleted records

        Returns:
            JiraMapping or None if not found
        """
        query = select(JiraMapping).where(
            JiraMapping.integration_id == integration_id,
            JiraMapping.wbs_id == wbs_id,
        )
        query = self._apply_soft_delete_filter(query, include_deleted)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_activity(
        self,
        integration_id: UUID,
        activity_id: UUID,
        include_deleted: bool = False,
    ) -> JiraMapping | None:
        """Get mapping for an activity.

        Args:
            integration_id: Jira integration UUID
            activity_id: Activity UUID
            include_deleted: Whether to include soft-deleted records

        Returns:
            JiraMapping or None if not found
        """
        query = select(JiraMapping).where(
            JiraMapping.integration_id == integration_id,
            JiraMapping.activity_id == activity_id,
        )
        query = self._apply_soft_delete_filter(query, include_deleted)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_integration(
        self,
        integration_id: UUID,
        entity_type: str | None = None,
        include_deleted: bool = False,
    ) -> list[JiraMapping]:
        """Get all mappings for an integration.

        Args:
            integration_id: Jira integration UUID
            entity_type: Optional entity type filter ('wbs' or 'activity')
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of JiraMapping instances
        """
        query = select(JiraMapping).where(JiraMapping.integration_id == integration_id)

        if entity_type:
            query = query.where(JiraMapping.entity_type == entity_type)

        query = self._apply_soft_delete_filter(query, include_deleted)
        query = query.order_by(JiraMapping.created_at)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_jira_key(
        self,
        integration_id: UUID,
        jira_issue_key: str,
        include_deleted: bool = False,
    ) -> JiraMapping | None:
        """Get mapping by Jira issue key.

        Args:
            integration_id: Jira integration UUID
            jira_issue_key: Jira issue key (e.g., 'PROJ-123')
            include_deleted: Whether to include soft-deleted records

        Returns:
            JiraMapping or None if not found
        """
        query = select(JiraMapping).where(
            JiraMapping.integration_id == integration_id,
            JiraMapping.jira_issue_key == jira_issue_key,
        )
        query = self._apply_soft_delete_filter(query, include_deleted)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_unmapped_wbs(
        self,
        integration_id: UUID,
        program_id: UUID,
    ) -> list[UUID]:
        """Get WBS element IDs that are not yet mapped.

        Args:
            integration_id: Jira integration UUID
            program_id: Program UUID

        Returns:
            List of unmapped WBS element UUIDs
        """
        # Get all WBS IDs for the program
        wbs_query = select(WBSElement.id).where(
            WBSElement.program_id == program_id,
            WBSElement.deleted_at.is_(None),
        )

        # Get mapped WBS IDs
        mapped_query = select(JiraMapping.wbs_id).where(
            JiraMapping.integration_id == integration_id,
            JiraMapping.wbs_id.isnot(None),
            JiraMapping.deleted_at.is_(None),
        )

        # Find unmapped
        all_wbs = await self.session.execute(wbs_query)
        all_wbs_ids = set(all_wbs.scalars().all())

        mapped = await self.session.execute(mapped_query)
        mapped_ids = set(mapped.scalars().all())

        return list(all_wbs_ids - mapped_ids)

    async def count_by_entity_type(
        self,
        integration_id: UUID,
    ) -> dict[str, int]:
        """Count mappings by entity type.

        Args:
            integration_id: Jira integration UUID

        Returns:
            Dict with counts by entity type
        """
        query = (
            select(JiraMapping.entity_type, func.count(JiraMapping.id))
            .where(
                JiraMapping.integration_id == integration_id,
                JiraMapping.deleted_at.is_(None),
            )
            .group_by(JiraMapping.entity_type)
        )

        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.all()}
