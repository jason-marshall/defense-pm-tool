"""Resource service for business logic and loading calculations.

Provides resource management functionality including:
- Resource loading calculations for date ranges
- Overallocation detection
- Program resource summary with caching
- Default calendar generation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from src.models.enums import ResourceType
from src.repositories.resource import (
    ResourceAssignmentRepository,
    ResourceCalendarRepository,
    ResourceRepository,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.models.resource import ResourceAssignment, ResourceCalendar
    from src.services.cache_service import CacheService


# Cache TTL for resource summary (5 minutes)
RESOURCE_SUMMARY_TTL = timedelta(minutes=5)


@dataclass
class ResourceLoadingDay:
    """Resource loading data for a single day.

    Attributes:
        date: The calendar date
        available_hours: Hours available based on calendar
        assigned_hours: Hours assigned from all active assignments
        utilization: Percentage of available hours that are assigned
        is_overallocated: True if assigned > available
    """

    date: date
    available_hours: Decimal
    assigned_hours: Decimal
    utilization: Decimal = field(init=False)
    is_overallocated: bool = field(init=False)

    def __post_init__(self) -> None:
        """Calculate utilization and overallocation status."""
        if self.available_hours > Decimal("0"):
            self.utilization = (
                (self.assigned_hours / self.available_hours) * Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            # If no available hours, any assignment means overallocation
            self.utilization = (
                Decimal("100") if self.assigned_hours > Decimal("0") else Decimal("0")
            )

        self.is_overallocated = self.assigned_hours > self.available_hours


@dataclass
class ResourceSummaryStats:
    """Summary statistics for program resources.

    Attributes:
        total_resources: Total count of resources
        labor_count: Count of LABOR type resources
        equipment_count: Count of EQUIPMENT type resources
        material_count: Count of MATERIAL type resources
        active_count: Count of active resources
        inactive_count: Count of inactive resources
    """

    total_resources: int
    labor_count: int
    equipment_count: int
    material_count: int
    active_count: int
    inactive_count: int

    def model_dump(self) -> dict[str, int]:
        """Convert to dictionary for caching."""
        return {
            "total_resources": self.total_resources,
            "labor_count": self.labor_count,
            "equipment_count": self.equipment_count,
            "material_count": self.material_count,
            "active_count": self.active_count,
            "inactive_count": self.inactive_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> ResourceSummaryStats:
        """Create from dictionary (for cache retrieval)."""
        return cls(
            total_resources=data["total_resources"],
            labor_count=data["labor_count"],
            equipment_count=data["equipment_count"],
            material_count=data["material_count"],
            active_count=data["active_count"],
            inactive_count=data["inactive_count"],
        )


class ResourceService:
    """Service for resource business logic and calculations.

    Provides methods for:
    - Calculating resource loading over date ranges
    - Detecting overallocation
    - Getting program resource summaries with caching
    - Generating default calendars

    Example usage:
        service = ResourceService(session)
        loading = await service.get_resource_loading(
            resource_id,
            date(2024, 1, 1),
            date(2024, 1, 31)
        )
        for day in loading.values():
            if day.is_overallocated:
                print(f"Overallocated on {day.date}")
    """

    def __init__(
        self,
        session: AsyncSession,
        cache: CacheService | None = None,
    ) -> None:
        """Initialize ResourceService.

        Args:
            session: Database session for queries
            cache: Optional cache service for summary caching
        """
        self.session = session
        self.cache = cache
        self._resource_repo = ResourceRepository(session)
        self._assignment_repo = ResourceAssignmentRepository(session)
        self._calendar_repo = ResourceCalendarRepository(session)

    def _assignment_active_on_date(
        self,
        assignment: ResourceAssignment,
        check_date: date,
    ) -> bool:
        """Check if an assignment is active on a specific date.

        An assignment is active if:
        - It has no start_date or start_date <= check_date
        - It has no finish_date or finish_date >= check_date

        Args:
            assignment: The resource assignment to check
            check_date: The date to check against

        Returns:
            True if assignment is active on the date
        """
        # Check start constraint (no start_date or start_date <= check_date)
        start_ok = not assignment.start_date or assignment.start_date <= check_date
        # Check finish constraint (no finish_date or finish_date >= check_date)
        finish_ok = not assignment.finish_date or assignment.finish_date >= check_date
        return start_ok and finish_ok

    async def get_resource_loading(
        self,
        resource_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[date, ResourceLoadingDay]:
        """Calculate resource loading for each day in a date range.

        Combines calendar availability with assignment allocations to
        calculate daily utilization and identify overallocations.

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

        # Get all assignments that might overlap this range
        assignments = await self._assignment_repo.get_by_resource(
            resource_id, start_date=start_date, end_date=end_date
        )

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
            for assignment in assignments:
                if self._assignment_active_on_date(assignment, current_date):
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
        loading = await self.get_resource_loading(resource_id, start_date, end_date)

        return [day.date for day in loading.values() if day.is_overallocated]

    async def get_program_resource_summary(
        self,
        program_id: UUID,
    ) -> ResourceSummaryStats:
        """Get summary statistics for program resources.

        Uses caching when available (5-minute TTL).

        Args:
            program_id: The program to get summary for

        Returns:
            ResourceSummaryStats with counts by type and status
        """
        cache_key = f"resource_summary:{program_id}"

        # Try cache first
        if self.cache and self.cache.is_available:
            cached = await self.cache.get(cache_key, "resource_summary")
            if cached:
                return ResourceSummaryStats.from_dict(cached)

        # Calculate from database
        total = await self._resource_repo.count_by_program(program_id)
        labor = await self._resource_repo.count_by_program(
            program_id, resource_type=ResourceType.LABOR
        )
        equipment = await self._resource_repo.count_by_program(
            program_id, resource_type=ResourceType.EQUIPMENT
        )
        material = await self._resource_repo.count_by_program(
            program_id, resource_type=ResourceType.MATERIAL
        )
        active = await self._resource_repo.count_by_program(program_id, is_active=True)
        inactive = await self._resource_repo.count_by_program(program_id, is_active=False)

        summary = ResourceSummaryStats(
            total_resources=total,
            labor_count=labor,
            equipment_count=equipment,
            material_count=material,
            active_count=active,
            inactive_count=inactive,
        )

        # Cache the result
        if self.cache and self.cache.is_available:
            await self.cache.set(
                cache_key,
                summary.model_dump(),
                RESOURCE_SUMMARY_TTL,
                "resource_summary",
            )

        return summary

    async def generate_default_calendar(
        self,
        resource_id: UUID,
        start_date: date,
        end_date: date,
        hours_per_day: Decimal = Decimal("8.0"),
        include_weekends: bool = False,
    ) -> list[ResourceCalendar]:
        """Generate default calendar entries for a resource.

        Creates calendar entries for each day in the range based on
        weekday/weekend logic.

        Args:
            resource_id: The resource to create calendar for
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            hours_per_day: Default hours for working days
            include_weekends: If True, weekends are working days

        Returns:
            List of created ResourceCalendar entries
        """
        entries_data: list[dict[str, object]] = []
        current_date = start_date

        while current_date <= end_date:
            is_weekend = current_date.weekday() >= 5  # Saturday = 5, Sunday = 6

            if include_weekends or not is_weekend:
                # Working day
                entries_data.append(
                    {
                        "resource_id": resource_id,
                        "calendar_date": current_date,
                        "available_hours": hours_per_day,
                        "is_working_day": True,
                    }
                )
            else:
                # Weekend (non-working)
                entries_data.append(
                    {
                        "resource_id": resource_id,
                        "calendar_date": current_date,
                        "available_hours": Decimal("0"),
                        "is_working_day": False,
                    }
                )

            current_date += timedelta(days=1)

        # Delete existing entries in range first
        await self._calendar_repo.delete_range(resource_id, start_date, end_date)

        # Create new entries
        entries = await self._calendar_repo.bulk_create_entries(entries_data)

        return entries
