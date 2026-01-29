"""Resource loading service with activity date integration.

Provides enhanced resource loading calculations that integrate with
activity planned dates from CPM scheduling.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from src.repositories.resource import (
    ResourceAssignmentRepository,
    ResourceCalendarRepository,
    ResourceRepository,
)
from src.services.resource import ResourceLoadingDay

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.models.enums import ResourceType
    from src.models.resource import Resource, ResourceAssignment, ResourceCalendar
    from src.services.cache_service import CacheService


class ResourceLoadingService:
    """Service for enhanced resource loading calculations.

    Integrates with activity planned dates from CPM scheduling to provide
    accurate resource loading over time. Supports:
    - Assignment date overrides
    - Fallback to activity planned dates
    - Fallback to activity early dates (CPM calculated)
    - Calendar-aware availability

    Example usage:
        service = ResourceLoadingService(session)
        loading = await service.calculate_daily_loading(
            resource_id,
            date(2024, 1, 1),
            date(2024, 1, 31)
        )
        for day_date, day_data in loading.items():
            if day_data.is_overallocated:
                print(f"Overallocated on {day_date}: {day_data.utilization}%")
    """

    def __init__(
        self,
        session: AsyncSession,
        cache: CacheService | None = None,
    ) -> None:
        """Initialize ResourceLoadingService.

        Args:
            session: Database session for queries
            cache: Optional cache service for caching results
        """
        self.session = session
        self.cache = cache
        self._resource_repo = ResourceRepository(session)
        self._assignment_repo = ResourceAssignmentRepository(session)
        self._calendar_repo = ResourceCalendarRepository(session)

    def get_assignment_date_range(
        self,
        assignment: ResourceAssignment,
    ) -> tuple[date | None, date | None]:
        """Get effective date range for an assignment.

        Returns the effective start and end dates for the assignment using
        the following priority:
        1. Assignment explicit dates (if set)
        2. Activity planned_start/planned_finish (from baseline)
        3. Activity early_start/early_finish (from CPM)

        Args:
            assignment: The resource assignment to get dates for

        Returns:
            Tuple of (start_date, end_date). Either or both may be None
            if no dates are available at any level.
        """
        # Priority 1: Use explicit assignment dates if set
        start_date = assignment.start_date
        finish_date = assignment.finish_date

        # Priority 2 & 3: Fall back to activity dates if assignment dates not set
        activity = assignment.activity
        if activity:
            if start_date is None:
                # Try planned_start first, then early_start
                start_date = activity.planned_start or activity.early_start

            if finish_date is None:
                # Try planned_finish first, then early_finish
                finish_date = activity.planned_finish or activity.early_finish

        return start_date, finish_date

    def _is_assignment_active_on_date(
        self,
        assignment: ResourceAssignment,
        check_date: date,
    ) -> bool:
        """Check if an assignment is active on a specific date.

        Uses get_assignment_date_range to determine the effective date range.

        Args:
            assignment: The resource assignment to check
            check_date: The date to check against

        Returns:
            True if assignment is active on the date
        """
        start_date, finish_date = self.get_assignment_date_range(assignment)

        # If no start date, assume active from the beginning
        if start_date is not None and start_date > check_date:
            return False

        # If no finish date, assume active indefinitely
        return not (finish_date is not None and finish_date < check_date)

    def get_loading_for_assignment(
        self,
        assignment: ResourceAssignment,
        resource: Resource,
        start_date: date,
        end_date: date,
    ) -> dict[date, Decimal]:
        """Calculate hours per day for a single assignment.

        Returns a dictionary mapping dates to assigned hours based on
        the assignment's units and the resource's capacity.

        Args:
            assignment: The resource assignment
            resource: The resource being assigned
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            Dictionary mapping dates to assigned hours
        """
        loading: dict[date, Decimal] = {}
        current_date = start_date

        while current_date <= end_date:
            if self._is_assignment_active_on_date(assignment, current_date):
                # Units represent allocation (1.0 = 100% = full capacity)
                hours = assignment.units * resource.capacity_per_day
                loading[current_date] = hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                loading[current_date] = Decimal("0")

            current_date += timedelta(days=1)

        return loading

    async def calculate_daily_loading(
        self,
        resource_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[date, ResourceLoadingDay]:
        """Calculate resource loading for each day in a date range.

        Combines calendar availability with assignment allocations to
        calculate daily utilization and identify overallocations.
        Uses activity dates for assignments without explicit dates.

        Args:
            resource_id: The resource to calculate loading for
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            Dictionary mapping dates to ResourceLoadingDay objects
        """
        # Get resource to check capacity
        resource = await self._resource_repo.get_by_id(resource_id)
        if not resource:
            return {}

        default_capacity = resource.capacity_per_day

        # Get calendar entries for the range
        calendar_entries = await self._calendar_repo.get_for_date_range(
            resource_id, start_date, end_date
        )

        # Build calendar lookup
        calendar_by_date: dict[date, ResourceCalendar] = {
            entry.calendar_date: entry for entry in calendar_entries
        }

        # Get all assignments with activities eagerly loaded
        assignments = await self._assignment_repo.get_assignments_with_activities(resource_id)

        # Filter to only assignments that might overlap this range
        relevant_assignments = []
        for assignment in assignments:
            assign_start, assign_finish = self.get_assignment_date_range(assignment)
            # Check if assignment overlaps with our date range
            if assign_finish is not None and assign_finish < start_date:
                continue
            if assign_start is not None and assign_start > end_date:
                continue
            relevant_assignments.append(assignment)

        # Calculate loading for each day
        loading: dict[date, ResourceLoadingDay] = {}
        current_date = start_date

        while current_date <= end_date:
            # Get available hours from calendar or default
            if current_date in calendar_by_date:
                calendar_entry = calendar_by_date[current_date]
                available_hours = (
                    calendar_entry.available_hours
                    if calendar_entry.is_working_day
                    else Decimal("0")
                )
            # No calendar entry - use default capacity for weekdays
            elif current_date.weekday() < 5:  # Monday = 0, Friday = 4
                available_hours = default_capacity
            else:
                available_hours = Decimal("0")

            # Calculate assigned hours from active assignments
            assigned_hours = Decimal("0")
            for assignment in relevant_assignments:
                if self._is_assignment_active_on_date(assignment, current_date):
                    # Units represent allocation (1.0 = 100% = full capacity)
                    assigned_hours += assignment.units * default_capacity

            loading[current_date] = ResourceLoadingDay(
                date=current_date,
                available_hours=available_hours,
                assigned_hours=assigned_hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            )

            current_date += timedelta(days=1)

        return loading

    async def get_overallocated_dates(
        self,
        resource_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[date]:
        """Get list of dates where resource is overallocated.

        Args:
            resource_id: The resource to check
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of dates where assigned hours exceed available hours
        """
        loading = await self.calculate_daily_loading(resource_id, start_date, end_date)
        return [day.date for day in loading.values() if day.is_overallocated]

    async def aggregate_program_loading(
        self,
        program_id: UUID,
        start_date: date,
        end_date: date,
        *,
        resource_type: ResourceType | None = None,
        active_only: bool = True,
    ) -> dict[UUID, dict[date, ResourceLoadingDay]]:
        """Get loading for all resources in a program.

        Args:
            program_id: The program to get loading for
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            resource_type: Optional filter by resource type
            active_only: If True, only include active resources

        Returns:
            Dictionary mapping resource IDs to their daily loading
        """
        # Get all resources for the program
        resources, _ = await self._resource_repo.get_by_program(
            program_id,
            resource_type=resource_type,
            is_active=active_only if active_only else None,
            skip=0,
            limit=10000,  # Get all resources
        )

        # Calculate loading for each resource
        result: dict[UUID, dict[date, ResourceLoadingDay]] = {}
        for resource in resources:
            loading = await self.calculate_daily_loading(resource.id, start_date, end_date)
            result[resource.id] = loading

        return result

    async def get_program_overallocation_summary(
        self,
        program_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[UUID, list[date]]:
        """Get overallocated dates for all resources in a program.

        Args:
            program_id: The program to check
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            Dictionary mapping resource IDs to their overallocated dates
        """
        loading = await self.aggregate_program_loading(program_id, start_date, end_date)

        result: dict[UUID, list[date]] = {}
        for resource_id, daily_loading in loading.items():
            overallocated = [day.date for day in daily_loading.values() if day.is_overallocated]
            if overallocated:
                result[resource_id] = overallocated

        return result
