"""Over-allocation detection service for resource conflict identification.

Identifies resource over-allocations where assigned hours exceed available
hours, supporting resource leveling decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from src.repositories.activity import ActivityRepository
from src.repositories.program import ProgramRepository
from src.repositories.resource import ResourceAssignmentRepository, ResourceRepository
from src.services.resource_loading import ResourceLoadingService

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.services.cache_service import CacheService
    from src.services.resource import ResourceLoadingDay


@dataclass
class OverallocationPeriod:
    """Represents a continuous period of resource over-allocation.

    Attributes:
        resource_id: UUID of the over-allocated resource
        resource_code: Resource code for display
        resource_name: Resource name for display
        start_date: First day of over-allocation period
        end_date: Last day of over-allocation period (inclusive)
        peak_assigned: Maximum assigned hours during period
        peak_available: Available hours on peak day
        peak_excess: Maximum excess (assigned - available)
        affected_activities: Activity IDs contributing to over-allocation
    """

    resource_id: UUID
    resource_code: str
    resource_name: str
    start_date: date
    end_date: date
    peak_assigned: Decimal
    peak_available: Decimal
    peak_excess: Decimal
    affected_activities: list[UUID] = field(default_factory=list)

    @property
    def duration_days(self) -> int:
        """Number of days in the over-allocation period."""
        return (self.end_date - self.start_date).days + 1

    @property
    def severity(self) -> str:
        """Classify severity based on peak excess.

        Returns:
            'low' if excess <= 2 hours
            'medium' if excess <= 4 hours
            'high' if excess > 4 hours
        """
        if self.peak_excess <= Decimal("2.0"):
            return "low"
        if self.peak_excess <= Decimal("4.0"):
            return "medium"
        return "high"


@dataclass
class ProgramOverallocationReport:
    """Summary report of all over-allocations in a program.

    Attributes:
        program_id: UUID of the analyzed program
        analysis_start: Start date of analysis period
        analysis_end: End date of analysis period
        total_overallocations: Total number of over-allocation periods
        resources_affected: Number of resources with over-allocations
        periods: List of all over-allocation periods
        critical_path_affected: Whether any critical path activities are affected
    """

    program_id: UUID
    analysis_start: date
    analysis_end: date
    total_overallocations: int
    resources_affected: int
    periods: list[OverallocationPeriod]
    critical_path_affected: bool

    @property
    def has_high_severity(self) -> bool:
        """Check if any period has high severity."""
        return any(p.severity == "high" for p in self.periods)

    @property
    def total_affected_days(self) -> int:
        """Total days with over-allocation across all resources."""
        return sum(p.duration_days for p in self.periods)


class OverallocationService:
    """Service for detecting and analyzing resource over-allocations.

    Uses ResourceLoadingService to calculate daily loading and identifies
    periods where assigned hours exceed available hours.

    Example usage:
        service = OverallocationService(session)
        report = await service.detect_program_overallocations(
            program_id,
            date(2024, 1, 1),
            date(2024, 3, 31)
        )
        if report.critical_path_affected:
            print("Critical path resources are over-allocated!")
        for period in report.periods:
            print(f"{period.resource_name}: {period.severity} severity")
    """

    def __init__(
        self,
        session: AsyncSession,
        cache: CacheService | None = None,
    ) -> None:
        """Initialize OverallocationService.

        Args:
            session: Database session for queries
            cache: Optional cache service for caching results
        """
        self.session = session
        self.cache = cache
        self._loading_service = ResourceLoadingService(session, cache)
        self._resource_repo = ResourceRepository(session)
        self._assignment_repo = ResourceAssignmentRepository(session)
        self._activity_repo = ActivityRepository(session)

    async def detect_resource_overallocations(
        self,
        resource_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[OverallocationPeriod]:
        """Find all over-allocated periods for a single resource.

        Analyzes daily loading and identifies continuous periods where
        assigned hours exceed available hours.

        Args:
            resource_id: The resource to analyze
            start_date: Start of analysis period (inclusive)
            end_date: End of analysis period (inclusive)

        Returns:
            List of OverallocationPeriod objects, merged for adjacent days
        """
        # Get resource info
        resource = await self._resource_repo.get_by_id(resource_id)
        if not resource:
            return []

        # Calculate daily loading
        loading = await self._loading_service.calculate_daily_loading(
            resource_id, start_date, end_date
        )

        if not loading:
            return []

        # Find over-allocated days
        overallocated_days: list[tuple[date, Decimal, Decimal]] = []
        for day_date, day_loading in sorted(loading.items()):
            if day_loading.is_overallocated:
                overallocated_days.append(
                    (day_date, day_loading.assigned_hours, day_loading.available_hours)
                )

        if not overallocated_days:
            return []

        # Group consecutive days into periods
        periods: list[OverallocationPeriod] = []
        current_start = overallocated_days[0][0]
        current_end = overallocated_days[0][0]
        peak_assigned = overallocated_days[0][1]
        peak_available = overallocated_days[0][2]
        peak_excess = peak_assigned - peak_available

        for i in range(1, len(overallocated_days)):
            day_date, assigned, available = overallocated_days[i]
            excess = assigned - available

            # Check if consecutive day
            if day_date == current_end + timedelta(days=1):
                current_end = day_date
                if excess > peak_excess:
                    peak_assigned = assigned
                    peak_available = available
                    peak_excess = excess
            else:
                # Save current period and start new one
                affected = await self.get_affected_activities(
                    resource_id, current_start, current_end
                )
                periods.append(
                    OverallocationPeriod(
                        resource_id=resource_id,
                        resource_code=resource.code,
                        resource_name=resource.name,
                        start_date=current_start,
                        end_date=current_end,
                        peak_assigned=peak_assigned,
                        peak_available=peak_available,
                        peak_excess=peak_excess,
                        affected_activities=affected,
                    )
                )
                current_start = day_date
                current_end = day_date
                peak_assigned = assigned
                peak_available = available
                peak_excess = excess

        # Don't forget the last period
        affected = await self.get_affected_activities(resource_id, current_start, current_end)
        periods.append(
            OverallocationPeriod(
                resource_id=resource_id,
                resource_code=resource.code,
                resource_name=resource.name,
                start_date=current_start,
                end_date=current_end,
                peak_assigned=peak_assigned,
                peak_available=peak_available,
                peak_excess=peak_excess,
                affected_activities=affected,
            )
        )

        return periods

    async def detect_program_overallocations(
        self,
        program_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ProgramOverallocationReport:
        """Analyze entire program for over-allocations.

        Examines all active resources in the program and identifies
        over-allocation periods for each.

        Args:
            program_id: The program to analyze
            start_date: Start of analysis period (defaults to program start)
            end_date: End of analysis period (defaults to program end)

        Returns:
            ProgramOverallocationReport with all over-allocation details
        """
        program_repo = ProgramRepository(self.session)
        program = await program_repo.get_by_id(program_id)

        if not program:
            # Return empty report for missing program
            return ProgramOverallocationReport(
                program_id=program_id,
                analysis_start=start_date or date.today(),
                analysis_end=end_date or date.today(),
                total_overallocations=0,
                resources_affected=0,
                periods=[],
                critical_path_affected=False,
            )

        # Use program dates if not specified
        analysis_start = start_date or program.start_date
        analysis_end = end_date or program.end_date

        # Get all active resources for program
        resources, _ = await self._resource_repo.get_by_program(
            program_id, is_active=True, skip=0, limit=10000
        )

        all_periods: list[OverallocationPeriod] = []
        resources_with_overallocations: set[UUID] = set()

        for resource in resources:
            periods = await self.detect_resource_overallocations(
                resource.id, analysis_start, analysis_end
            )
            if periods:
                all_periods.extend(periods)
                resources_with_overallocations.add(resource.id)

        # Check if critical path is affected
        critical_path_affected = await self.check_critical_path_impact(program_id, all_periods)

        return ProgramOverallocationReport(
            program_id=program_id,
            analysis_start=analysis_start,
            analysis_end=analysis_end,
            total_overallocations=len(all_periods),
            resources_affected=len(resources_with_overallocations),
            periods=all_periods,
            critical_path_affected=critical_path_affected,
        )

    async def get_affected_activities(
        self,
        resource_id: UUID,
        start_date: date,
        end_date: date | None = None,
    ) -> list[UUID]:
        """Return activity IDs contributing to over-allocation on given date(s).

        Args:
            resource_id: The resource to check
            start_date: Start date (or single date if end_date is None)
            end_date: End date (inclusive), defaults to start_date

        Returns:
            List of activity UUIDs with assignments active during the period
        """
        if end_date is None:
            end_date = start_date

        # Get assignments with activities loaded
        assignments = await self._assignment_repo.get_assignments_with_activities(resource_id)

        affected_activity_ids: set[UUID] = set()
        for assignment in assignments:
            # Get effective date range for assignment
            assign_start, assign_finish = self._loading_service.get_assignment_date_range(
                assignment
            )

            # Check if assignment overlaps with our date range
            if assign_finish is not None and assign_finish < start_date:
                continue
            if assign_start is not None and assign_start > end_date:
                continue

            # Assignment is active during at least part of the period
            affected_activity_ids.add(assignment.activity_id)

        return list(affected_activity_ids)

    async def check_critical_path_impact(
        self,
        _program_id: UUID,
        overallocations: list[OverallocationPeriod],
    ) -> bool:
        """Check if any over-allocation affects critical path activities.

        Args:
            _program_id: The program to check (reserved for future use)
            overallocations: List of over-allocation periods

        Returns:
            True if any affected activity is on the critical path
        """
        if not overallocations:
            return False

        # Collect all affected activity IDs
        affected_ids: set[UUID] = set()
        for period in overallocations:
            affected_ids.update(period.affected_activities)

        if not affected_ids:
            return False

        # Check if any are critical
        for activity_id in affected_ids:
            activity = await self._activity_repo.get_by_id(activity_id)
            if activity and activity.is_critical:
                return True

        return False

    def _merge_adjacent_periods(
        self,
        periods: list[OverallocationPeriod],
    ) -> list[OverallocationPeriod]:
        """Combine consecutive over-allocated days into single periods.

        This is called internally during detection, but exposed for
        re-merging if needed.

        Args:
            periods: List of potentially fragmented periods

        Returns:
            List with adjacent periods merged
        """
        if not periods:
            return []

        # Sort by resource and start date
        sorted_periods = sorted(periods, key=lambda p: (p.resource_id, p.start_date))

        merged: list[OverallocationPeriod] = []
        current = sorted_periods[0]

        for period in sorted_periods[1:]:
            # Check if same resource and adjacent
            if (
                period.resource_id == current.resource_id
                and period.start_date <= current.end_date + timedelta(days=1)
            ):
                # Merge periods
                current = OverallocationPeriod(
                    resource_id=current.resource_id,
                    resource_code=current.resource_code,
                    resource_name=current.resource_name,
                    start_date=current.start_date,
                    end_date=max(current.end_date, period.end_date),
                    peak_assigned=max(current.peak_assigned, period.peak_assigned),
                    peak_available=min(current.peak_available, period.peak_available),
                    peak_excess=max(current.peak_excess, period.peak_excess),
                    affected_activities=list(
                        set(current.affected_activities + period.affected_activities)
                    ),
                )
            else:
                merged.append(current)
                current = period

        merged.append(current)
        return merged

    def _calculate_peak_excess(
        self,
        loading: dict[date, ResourceLoadingDay],
    ) -> tuple[date | None, Decimal]:
        """Find date with maximum over-allocation.

        Args:
            loading: Dictionary mapping dates to ResourceLoadingDay objects

        Returns:
            Tuple of (peak_date, peak_excess). Returns (None, 0) if no over-allocation.
        """
        peak_date: date | None = None
        peak_excess = Decimal("0")

        for day_date, day_loading in loading.items():
            if day_loading.is_overallocated:
                excess = day_loading.assigned_hours - day_loading.available_hours
                if excess > peak_excess:
                    peak_date = day_date
                    peak_excess = excess

        return peak_date, peak_excess
