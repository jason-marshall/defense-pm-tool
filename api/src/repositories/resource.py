"""Repository layer for Resource, ResourceAssignment, and ResourceCalendar."""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.models.enums import ResourceType
from src.models.resource import Resource, ResourceAssignment, ResourceCalendar
from src.repositories.base import BaseRepository


class ResourceRepository(BaseRepository[Resource]):
    """
    Repository for Resource model operations.

    Provides program-scoped resource queries, code lookups, and
    eager loading of assignments.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with Resource model."""
        super().__init__(Resource, session)

    async def get_by_program(
        self,
        program_id: UUID,
        *,
        resource_type: ResourceType | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Resource], int]:
        """
        Get resources for a program with optional filters.

        Args:
            program_id: Program UUID
            resource_type: Filter by resource type
            is_active: Filter by active status
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of resources, total count)
        """
        # Build base query
        query = select(Resource).where(Resource.program_id == program_id)
        query = self._apply_soft_delete_filter(query)

        # Apply optional filters
        if resource_type is not None:
            query = query.where(Resource.resource_type == resource_type)
        if is_active is not None:
            query = query.where(Resource.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Apply pagination and ordering
        query = query.order_by(Resource.code).offset(skip).limit(limit)

        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def count_by_program(
        self,
        program_id: UUID,
        *,
        resource_type: ResourceType | None = None,
        is_active: bool | None = None,
    ) -> int:
        """
        Count resources for a program with optional filters.

        Args:
            program_id: Program UUID
            resource_type: Filter by resource type
            is_active: Filter by active status

        Returns:
            Number of matching resources
        """
        query = select(func.count()).select_from(Resource).where(Resource.program_id == program_id)
        query = self._apply_soft_delete_filter(query)

        if resource_type is not None:
            query = query.where(Resource.resource_type == resource_type)
        if is_active is not None:
            query = query.where(Resource.is_active == is_active)

        result = await self.session.execute(query)
        count: int = result.scalar_one()
        return count

    async def get_by_code(
        self,
        program_id: UUID,
        code: str,
    ) -> Resource | None:
        """
        Get a resource by its code within a program.

        Args:
            program_id: Program UUID
            code: Resource code (case-insensitive)

        Returns:
            Resource if found, None otherwise
        """
        query = (
            select(Resource)
            .where(Resource.program_id == program_id)
            .where(func.upper(Resource.code) == code.upper())
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def code_exists(
        self,
        program_id: UUID,
        code: str,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        """
        Check if a resource code exists within a program.

        Args:
            program_id: Program UUID
            code: Resource code to check
            exclude_id: Optional resource ID to exclude from check

        Returns:
            True if code exists, False otherwise
        """
        query = (
            select(func.count())
            .select_from(Resource)
            .where(Resource.program_id == program_id)
            .where(func.upper(Resource.code) == code.upper())
        )
        query = self._apply_soft_delete_filter(query)

        if exclude_id is not None:
            query = query.where(Resource.id != exclude_id)

        result = await self.session.execute(query)
        count: int = result.scalar_one()
        return count > 0

    async def get_with_assignments(
        self,
        resource_id: UUID,
    ) -> Resource | None:
        """
        Get a resource with its assignments eagerly loaded.

        Args:
            resource_id: Resource UUID

        Returns:
            Resource with assignments if found, None otherwise
        """
        query = (
            select(Resource)
            .where(Resource.id == resource_id)
            .options(joinedload(Resource.assignments))
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()


class ResourceAssignmentRepository(BaseRepository[ResourceAssignment]):
    """
    Repository for ResourceAssignment model operations.

    Provides activity and resource scoped queries with eager loading.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with ResourceAssignment model."""
        super().__init__(ResourceAssignment, session)

    async def get_by_activity(
        self,
        activity_id: UUID,
    ) -> list[ResourceAssignment]:
        """
        Get all assignments for an activity with resource eagerly loaded.

        Args:
            activity_id: Activity UUID

        Returns:
            List of assignments with resources
        """
        query = (
            select(ResourceAssignment)
            .where(ResourceAssignment.activity_id == activity_id)
            .options(joinedload(ResourceAssignment.resource))
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def get_by_resource(
        self,
        resource_id: UUID,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[ResourceAssignment]:
        """
        Get all assignments for a resource with optional date filtering.

        Args:
            resource_id: Resource UUID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of assignments with resource eagerly loaded
        """
        query = (
            select(ResourceAssignment)
            .where(ResourceAssignment.resource_id == resource_id)
            .options(joinedload(ResourceAssignment.resource))
        )
        query = self._apply_soft_delete_filter(query)

        # Filter by date range if provided
        if start_date is not None:
            query = query.where(
                (ResourceAssignment.finish_date.is_(None))
                | (ResourceAssignment.finish_date >= start_date)
            )
        if end_date is not None:
            query = query.where(
                (ResourceAssignment.start_date.is_(None))
                | (ResourceAssignment.start_date <= end_date)
            )

        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def assignment_exists(
        self,
        activity_id: UUID,
        resource_id: UUID,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        """
        Check if an assignment exists for an activity-resource pair.

        Args:
            activity_id: Activity UUID
            resource_id: Resource UUID
            exclude_id: Optional assignment ID to exclude

        Returns:
            True if assignment exists, False otherwise
        """
        query = (
            select(func.count())
            .select_from(ResourceAssignment)
            .where(ResourceAssignment.activity_id == activity_id)
            .where(ResourceAssignment.resource_id == resource_id)
        )
        query = self._apply_soft_delete_filter(query)

        if exclude_id is not None:
            query = query.where(ResourceAssignment.id != exclude_id)

        result = await self.session.execute(query)
        count: int = result.scalar_one()
        return count > 0

    async def get_total_units_for_resource(
        self,
        resource_id: UUID,
        on_date: date,
    ) -> Decimal:
        """
        Get total allocation units for a resource on a specific date.

        Args:
            resource_id: Resource UUID
            on_date: Date to check allocation

        Returns:
            Total units allocated on the date
        """
        query = (
            select(func.coalesce(func.sum(ResourceAssignment.units), Decimal("0")))
            .where(ResourceAssignment.resource_id == resource_id)
            .where(
                (ResourceAssignment.start_date.is_(None))
                | (ResourceAssignment.start_date <= on_date)
            )
            .where(
                (ResourceAssignment.finish_date.is_(None))
                | (ResourceAssignment.finish_date >= on_date)
            )
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        total: Decimal = result.scalar_one()
        return total


class ResourceCalendarRepository(BaseRepository[ResourceCalendar]):
    """
    Repository for ResourceCalendar model operations.

    Provides date range queries, bulk operations, and aggregations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with ResourceCalendar model."""
        super().__init__(ResourceCalendar, session)

    async def get_for_date_range(
        self,
        resource_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[ResourceCalendar]:
        """
        Get calendar entries for a resource within a date range.

        Args:
            resource_id: Resource UUID
            start_date: Range start date (inclusive)
            end_date: Range end date (inclusive)

        Returns:
            List of calendar entries ordered by date
        """
        query = (
            select(ResourceCalendar)
            .where(ResourceCalendar.resource_id == resource_id)
            .where(ResourceCalendar.calendar_date >= start_date)
            .where(ResourceCalendar.calendar_date <= end_date)
            .order_by(ResourceCalendar.calendar_date)
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_date(
        self,
        resource_id: UUID,
        calendar_date: date,
    ) -> ResourceCalendar | None:
        """
        Get a calendar entry for a specific date.

        Args:
            resource_id: Resource UUID
            calendar_date: The date to look up

        Returns:
            Calendar entry if found, None otherwise
        """
        query = (
            select(ResourceCalendar)
            .where(ResourceCalendar.resource_id == resource_id)
            .where(ResourceCalendar.calendar_date == calendar_date)
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def bulk_create_entries(
        self,
        entries: list[dict[str, Any]],
    ) -> list[ResourceCalendar]:
        """
        Create multiple calendar entries efficiently.

        Args:
            entries: List of entry dictionaries

        Returns:
            List of created calendar entries
        """
        return await self.bulk_create(entries)

    async def get_working_days_count(
        self,
        resource_id: UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """
        Count working days for a resource within a date range.

        Args:
            resource_id: Resource UUID
            start_date: Range start date (inclusive)
            end_date: Range end date (inclusive)

        Returns:
            Number of working days
        """
        query = (
            select(func.count())
            .select_from(ResourceCalendar)
            .where(ResourceCalendar.resource_id == resource_id)
            .where(ResourceCalendar.calendar_date >= start_date)
            .where(ResourceCalendar.calendar_date <= end_date)
            .where(ResourceCalendar.is_working_day.is_(True))
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        count: int = result.scalar_one()
        return count

    async def get_total_hours(
        self,
        resource_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        """
        Get total available hours for a resource within a date range.

        Args:
            resource_id: Resource UUID
            start_date: Range start date (inclusive)
            end_date: Range end date (inclusive)

        Returns:
            Total available hours
        """
        query = (
            select(func.coalesce(func.sum(ResourceCalendar.available_hours), Decimal("0")))
            .where(ResourceCalendar.resource_id == resource_id)
            .where(ResourceCalendar.calendar_date >= start_date)
            .where(ResourceCalendar.calendar_date <= end_date)
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        total: Decimal = result.scalar_one()
        return total

    async def delete_range(
        self,
        resource_id: UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """
        Delete calendar entries for a resource within a date range.

        Args:
            resource_id: Resource UUID
            start_date: Range start date (inclusive)
            end_date: Range end date (inclusive)

        Returns:
            Number of entries deleted
        """
        # Use hard delete for calendar entries (no soft delete needed)
        stmt = (
            delete(ResourceCalendar)
            .where(ResourceCalendar.resource_id == resource_id)
            .where(ResourceCalendar.calendar_date >= start_date)
            .where(ResourceCalendar.calendar_date <= end_date)
        )

        cursor_result = await self.session.execute(stmt)
        await self.session.flush()
        deleted: int = cursor_result.rowcount  # type: ignore[attr-defined]
        return deleted
