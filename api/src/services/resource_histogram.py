"""Resource histogram service for visualization data.

Provides histogram data showing resource loading over time for capacity planning.
Supports single-resource and program-wide histograms with daily/weekly granularity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from src.repositories.program import ProgramRepository
from src.repositories.resource import ResourceRepository
from src.services.resource_loading import ResourceLoadingService

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.models.enums import ResourceType
    from src.services.cache_service import CacheService


@dataclass
class HistogramDataPoint:
    """A single data point in the resource histogram.

    Attributes:
        date: The date for this data point
        available_hours: Hours available on this day
        assigned_hours: Hours assigned on this day
        utilization_percent: Utilization as percentage (0-100+)
        is_overallocated: True if assigned > available
    """

    date: date
    available_hours: Decimal
    assigned_hours: Decimal
    utilization_percent: Decimal
    is_overallocated: bool


@dataclass
class ResourceHistogram:
    """Complete histogram data for a single resource.

    Attributes:
        resource_id: UUID of the resource
        resource_code: Resource code for display
        resource_name: Resource name for display
        resource_type: Type of resource (labor, equipment, etc.)
        start_date: Start of histogram period
        end_date: End of histogram period
        data_points: List of data points in the histogram
        peak_utilization: Maximum utilization percentage
        peak_date: Date of peak utilization
        average_utilization: Average utilization over period
        overallocated_days: Number of days with over-allocation
        total_available_hours: Sum of available hours in period
        total_assigned_hours: Sum of assigned hours in period
    """

    resource_id: UUID
    resource_code: str
    resource_name: str
    resource_type: ResourceType
    start_date: date
    end_date: date
    data_points: list[HistogramDataPoint] = field(default_factory=list)
    peak_utilization: Decimal = Decimal("0")
    peak_date: date | None = None
    average_utilization: Decimal = Decimal("0")
    overallocated_days: int = 0
    total_available_hours: Decimal = Decimal("0")
    total_assigned_hours: Decimal = Decimal("0")


@dataclass
class ProgramHistogramSummary:
    """Summary statistics for program-wide histogram.

    Attributes:
        program_id: UUID of the program
        start_date: Start of analysis period
        end_date: End of analysis period
        resource_count: Number of resources in histogram
        total_overallocated_days: Sum of overallocated days across all resources
        resources_with_overallocation: Count of resources with any over-allocation
    """

    program_id: UUID
    start_date: date
    end_date: date
    resource_count: int
    total_overallocated_days: int
    resources_with_overallocation: int


class ResourceHistogramService:
    """Service for generating resource histogram data.

    Provides histogram visualization data for capacity planning and
    resource management. Supports both single-resource detailed views
    and program-wide summary views.

    Example usage:
        service = ResourceHistogramService(session)
        histogram = await service.get_resource_histogram(
            resource_id,
            date(2024, 1, 1),
            date(2024, 3, 31),
            granularity="weekly"
        )
        for point in histogram.data_points:
            print(f"{point.date}: {point.utilization_percent}%")
    """

    def __init__(
        self,
        session: AsyncSession,
        cache: CacheService | None = None,
    ) -> None:
        """Initialize ResourceHistogramService.

        Args:
            session: Database session for queries
            cache: Optional cache service
        """
        self.session = session
        self.cache = cache
        self._resource_repo = ResourceRepository(session)
        self._program_repo = ProgramRepository(session)
        self._loading_service = ResourceLoadingService(session, cache)

    async def get_resource_histogram(
        self,
        resource_id: UUID,
        start_date: date,
        end_date: date,
        granularity: str = "daily",
    ) -> ResourceHistogram | None:
        """Generate histogram data for a single resource.

        Args:
            resource_id: UUID of the resource
            start_date: Start of histogram period
            end_date: End of histogram period
            granularity: "daily" or "weekly"

        Returns:
            ResourceHistogram with data points, or None if resource not found
        """
        resource = await self._resource_repo.get_by_id(resource_id)
        if not resource:
            return None

        # Get daily loading data
        loading = await self._loading_service.calculate_daily_loading(
            resource_id, start_date, end_date
        )

        # Convert to data points
        data_points: list[HistogramDataPoint] = []
        current = start_date
        while current <= end_date:
            if current in loading:
                day_loading = loading[current]
                available = day_loading.available_hours
                assigned = day_loading.assigned_hours
                utilization = (
                    (assigned / available * Decimal("100")) if available > 0 else Decimal("0")
                )
                is_over = day_loading.is_overallocated
            else:
                # No loading data - use resource capacity
                available = resource.capacity_per_day
                assigned = Decimal("0")
                utilization = Decimal("0")
                is_over = False

            data_points.append(
                HistogramDataPoint(
                    date=current,
                    available_hours=available,
                    assigned_hours=assigned,
                    utilization_percent=utilization,
                    is_overallocated=is_over,
                )
            )
            current += timedelta(days=1)

        # Aggregate if weekly
        if granularity == "weekly":
            data_points = self._aggregate_to_weekly(data_points)

        # Calculate statistics
        stats = self._calculate_statistics(data_points)

        return ResourceHistogram(
            resource_id=resource.id,
            resource_code=resource.code,
            resource_name=resource.name,
            resource_type=resource.resource_type,
            start_date=start_date,
            end_date=end_date,
            data_points=data_points,
            peak_utilization=stats["peak_utilization"],
            peak_date=stats["peak_date"],
            average_utilization=stats["average_utilization"],
            overallocated_days=stats["overallocated_days"],
            total_available_hours=stats["total_available_hours"],
            total_assigned_hours=stats["total_assigned_hours"],
        )

    async def get_program_histogram(
        self,
        program_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        resource_ids: list[UUID] | None = None,
    ) -> tuple[ProgramHistogramSummary, list[ResourceHistogram]]:
        """Generate histogram data for all resources in a program.

        Args:
            program_id: UUID of the program
            start_date: Start of period (defaults to program start)
            end_date: End of period (defaults to program end)
            resource_ids: Optional filter for specific resources

        Returns:
            Tuple of (ProgramHistogramSummary, list of ResourceHistogram)
        """
        program = await self._program_repo.get_by_id(program_id)

        if not program:
            return (
                ProgramHistogramSummary(
                    program_id=program_id,
                    start_date=start_date or date.today(),
                    end_date=end_date or date.today(),
                    resource_count=0,
                    total_overallocated_days=0,
                    resources_with_overallocation=0,
                ),
                [],
            )

        # Use program dates if not specified
        analysis_start = start_date or program.start_date
        analysis_end = end_date or program.end_date

        # Get resources
        resources, _ = await self._resource_repo.get_by_program(
            program_id, is_active=True, skip=0, limit=10000
        )

        # Filter if specific resources requested
        if resource_ids:
            resource_id_set = set(resource_ids)
            resources = [r for r in resources if r.id in resource_id_set]

        # Generate histograms for each resource
        histograms: list[ResourceHistogram] = []
        total_overallocated_days = 0
        resources_with_overallocation = 0

        for resource in resources:
            histogram = await self.get_resource_histogram(
                resource.id, analysis_start, analysis_end, granularity="daily"
            )
            if histogram:
                histograms.append(histogram)
                total_overallocated_days += histogram.overallocated_days
                if histogram.overallocated_days > 0:
                    resources_with_overallocation += 1

        summary = ProgramHistogramSummary(
            program_id=program_id,
            start_date=analysis_start,
            end_date=analysis_end,
            resource_count=len(histograms),
            total_overallocated_days=total_overallocated_days,
            resources_with_overallocation=resources_with_overallocation,
        )

        return summary, histograms

    def _aggregate_to_weekly(
        self,
        daily_data: list[HistogramDataPoint],
    ) -> list[HistogramDataPoint]:
        """Aggregate daily data points to weekly.

        Sums hours and calculates average utilization for each week.
        Week starts on Monday.

        Args:
            daily_data: List of daily data points

        Returns:
            List of weekly aggregated data points
        """
        if not daily_data:
            return []

        weekly_data: list[HistogramDataPoint] = []
        week_points: list[HistogramDataPoint] = []
        current_week_start: date | None = None

        for point in daily_data:
            # Get Monday of this week
            week_start = point.date - timedelta(days=point.date.weekday())

            if current_week_start is None:
                current_week_start = week_start

            if week_start != current_week_start:
                # Aggregate previous week
                if week_points:
                    weekly_data.append(self._aggregate_week(week_points))
                week_points = []
                current_week_start = week_start

            week_points.append(point)

        # Don't forget the last week
        if week_points:
            weekly_data.append(self._aggregate_week(week_points))

        return weekly_data

    def _aggregate_week(
        self,
        points: list[HistogramDataPoint],
    ) -> HistogramDataPoint:
        """Aggregate a list of daily points into one weekly point.

        Args:
            points: Daily data points for one week

        Returns:
            Single aggregated data point for the week
        """
        total_available = sum((p.available_hours for p in points), Decimal("0"))
        total_assigned = sum((p.assigned_hours for p in points), Decimal("0"))
        is_over = any(p.is_overallocated for p in points)

        utilization = (
            (total_assigned / total_available * Decimal("100"))
            if total_available > 0
            else Decimal("0")
        )

        # Use Monday of the week as the date
        week_start = points[0].date - timedelta(days=points[0].date.weekday())

        return HistogramDataPoint(
            date=week_start,
            available_hours=total_available,
            assigned_hours=total_assigned,
            utilization_percent=utilization,
            is_overallocated=is_over,
        )

    def _calculate_statistics(
        self,
        data_points: list[HistogramDataPoint],
    ) -> dict:  # type: ignore[type-arg]
        """Calculate summary statistics for histogram data.

        Args:
            data_points: List of data points

        Returns:
            Dictionary with peak_utilization, peak_date, average_utilization,
            overallocated_days, total_available_hours, total_assigned_hours
        """
        if not data_points:
            return {
                "peak_utilization": Decimal("0"),
                "peak_date": None,
                "average_utilization": Decimal("0"),
                "overallocated_days": 0,
                "total_available_hours": Decimal("0"),
                "total_assigned_hours": Decimal("0"),
            }

        peak_utilization = Decimal("0")
        peak_date: date | None = None
        total_utilization = Decimal("0")
        overallocated_days = 0
        total_available = Decimal("0")
        total_assigned = Decimal("0")

        for point in data_points:
            if point.utilization_percent > peak_utilization:
                peak_utilization = point.utilization_percent
                peak_date = point.date

            total_utilization += point.utilization_percent
            total_available += point.available_hours
            total_assigned += point.assigned_hours

            if point.is_overallocated:
                overallocated_days += 1

        average_utilization = total_utilization / len(data_points)

        return {
            "peak_utilization": peak_utilization,
            "peak_date": peak_date,
            "average_utilization": average_utilization,
            "overallocated_days": overallocated_days,
            "total_available_hours": total_available,
            "total_assigned_hours": total_assigned,
        }
