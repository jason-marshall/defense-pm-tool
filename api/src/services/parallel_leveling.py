"""Parallel resource leveling algorithm for multi-resource optimization.

Unlike serial leveling which processes activities one at a time,
parallel leveling considers all resources and activities simultaneously
to find a globally better (often optimal) solution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from heapq import heappop, heappush
from typing import TYPE_CHECKING, Any

from src.repositories.activity import ActivityRepository
from src.repositories.dependency import DependencyRepository
from src.repositories.program import ProgramRepository
from src.repositories.resource import ResourceAssignmentRepository, ResourceRepository
from src.services.resource_leveling import ActivityShift, LevelingOptions, LevelingResult
from src.services.resource_loading import ResourceLoadingService

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.models.activity import Activity
    from src.services.cache_service import CacheService


@dataclass
class ResourceConflict:
    """Represents a resource conflict on a specific date.

    Attributes:
        resource_id: UUID of the overallocated resource
        conflict_date: Date when overallocation occurs
        overallocation_hours: Hours over capacity
        activities: Activity IDs contributing to overallocation
    """

    resource_id: UUID
    conflict_date: date
    overallocation_hours: Decimal
    activities: list[UUID]

    def __lt__(self, other: ResourceConflict) -> bool:
        """Order by date, then by severity (more severe = higher priority)."""
        if self.conflict_date != other.conflict_date:
            return self.conflict_date < other.conflict_date
        return self.overallocation_hours > other.overallocation_hours


@dataclass
class ActivityPriority:
    """Priority score for an activity during leveling.

    Used to determine which activity should be delayed when
    multiple activities compete for the same resource.

    Attributes:
        activity_id: UUID of the activity
        early_start: Original early start date
        total_float: Available total float in days
        is_critical: Whether activity is on critical path
        resource_count: Number of resources assigned to activity
    """

    activity_id: UUID
    early_start: date
    total_float: int
    is_critical: bool
    resource_count: int

    @property
    def score(self) -> tuple[int, date, int, int]:
        """Priority tuple for sorting (lower = higher priority, should NOT be delayed).

        Priority order (most protected first):
        1. Critical path activities (should not delay)
        2. Earlier start dates (earlier = more constrained)
        3. Less float (less flexibility)
        4. More resources (harder to reschedule)
        """
        return (
            0 if self.is_critical else 1,  # Critical path first (protected)
            self.early_start,  # Earlier start first
            self.total_float,  # Less float first
            -self.resource_count,  # More resources = harder to move
        )

    def __lt__(self, other: ActivityPriority) -> bool:
        """Compare priorities for heap operations."""
        return self.score < other.score


@dataclass
class ParallelLevelingResult(LevelingResult):
    """Extended result with parallel-specific metrics.

    Attributes:
        conflicts_resolved: Total conflicts resolved during leveling
        resources_processed: Number of unique resources processed
        comparison_with_serial: Comparison metrics vs serial algorithm
    """

    conflicts_resolved: int = 0
    resources_processed: int = 0
    comparison_with_serial: dict[str, Any] = field(default_factory=dict)


class ParallelLevelingService:
    """Parallel resource leveling service.

    Unlike serial leveling which processes activities one at a time,
    parallel leveling considers all resources and activities simultaneously
    to find a globally better (often optimal) solution.

    Algorithm:
    1. Build conflict matrix: all (resource, date, activities) tuples
    2. Create priority queue of conflicts ordered by date
    3. For each conflict, determine which activity to delay
    4. Update all affected resources and propagate to successors
    5. Repeat until no conflicts or max iterations

    Key Improvements over Serial:
    - Considers multi-resource activities holistically
    - Better handling of shared resources across activities
    - Finds solutions serial method might miss

    Example usage:
        service = ParallelLevelingService(session)
        options = LevelingOptions(preserve_critical_path=True)
        result = await service.level_program(program_id, options)

        if result.success:
            print(f"Resolved {result.conflicts_resolved} conflicts")
            print(f"Processed {result.resources_processed} resources")
    """

    def __init__(
        self,
        session: AsyncSession,
        cache: CacheService | None = None,
    ) -> None:
        """Initialize ParallelLevelingService.

        Args:
            session: Database session for queries
            cache: Optional cache service
        """
        self.session = session
        self.cache = cache
        self._activity_repo = ActivityRepository(session)
        self._resource_repo = ResourceRepository(session)
        self._assignment_repo = ResourceAssignmentRepository(session)
        self._dependency_repo = DependencyRepository(session)
        self._program_repo = ProgramRepository(session)
        self._loading_service = ResourceLoadingService(session, cache)

    async def level_program(
        self,
        program_id: UUID,
        options: LevelingOptions | None = None,
    ) -> ParallelLevelingResult:
        """Execute parallel resource leveling.

        Args:
            program_id: Program to level
            options: Leveling options

        Returns:
            ParallelLevelingResult with all changes and metrics
        """
        if options is None:
            options = LevelingOptions()

        warnings: list[str] = []
        shifts: list[ActivityShift] = []

        # Get program and validate
        program = await self._program_repo.get_by_id(program_id)
        if not program:
            return ParallelLevelingResult(
                program_id=program_id,
                success=False,
                iterations_used=0,
                activities_shifted=0,
                shifts=[],
                remaining_overallocations=0,
                new_project_finish=date.today(),
                original_project_finish=date.today(),
                schedule_extension_days=0,
                warnings=["Program not found"],
            )

        # Get original finish date
        original_finish = await self._get_project_finish(program_id)

        # Get all activities with their priorities
        activities = await self._get_activities_with_schedule(program_id)
        if not activities:
            return ParallelLevelingResult(
                program_id=program_id,
                success=True,
                iterations_used=0,
                activities_shifted=0,
                shifts=[],
                remaining_overallocations=0,
                new_project_finish=original_finish,
                original_project_finish=original_finish,
                schedule_extension_days=0,
            )

        # Initialize working dates from activities
        activity_dates: dict[UUID, tuple[date, date]] = {}
        for activity in activities:
            start = activity.early_start or activity.planned_start or program.start_date
            finish = activity.early_finish or activity.planned_finish or program.end_date
            activity_dates[activity.id] = (start, finish)

        # Calculate activity priorities
        priority_map = await self._calculate_priorities(activities)

        # Build initial conflict matrix
        conflicts = await self._build_conflict_matrix(program_id, activity_dates, options)

        initial_conflict_count = len(conflicts)
        unique_resources: set[UUID] = set()

        if not conflicts:
            return ParallelLevelingResult(
                program_id=program_id,
                success=True,
                iterations_used=0,
                activities_shifted=0,
                shifts=[],
                remaining_overallocations=0,
                new_project_finish=original_finish,
                original_project_finish=original_finish,
                schedule_extension_days=0,
            )

        # Main leveling loop
        iteration = 0
        activity_lookup = {a.id: a for a in activities}

        while conflicts and iteration < options.max_iterations:
            iteration += 1

            # Get highest priority conflict (earliest date, most severe)
            conflict = heappop(conflicts)
            unique_resources.add(conflict.resource_id)

            # Find best activity to delay (lowest priority = most flexible)
            activity_to_delay = self._select_activity_to_delay(
                conflict,
                priority_map,
                activity_dates,
                options,
            )

            if activity_to_delay is None:
                resource = await self._resource_repo.get_by_id(conflict.resource_id)
                resource_name = resource.code if resource else str(conflict.resource_id)
                warnings.append(
                    f"Could not resolve conflict on {conflict.conflict_date} "
                    f"for resource {resource_name}"
                )
                continue

            # Calculate delay needed
            delay_days = await self._calculate_minimum_delay(
                activity_to_delay,
                conflict.resource_id,
                conflict.conflict_date,
                activity_dates,
            )

            if delay_days <= 0:
                continue

            # Apply delay
            old_start, old_finish = activity_dates[activity_to_delay]
            new_start = old_start + timedelta(days=delay_days)
            new_finish = old_finish + timedelta(days=delay_days)
            activity_dates[activity_to_delay] = (new_start, new_finish)

            # Record shift
            activity = activity_lookup[activity_to_delay]
            resource = await self._resource_repo.get_by_id(conflict.resource_id)
            resource_name = resource.code if resource else "Unknown"

            shifts.append(
                ActivityShift(
                    activity_id=activity_to_delay,
                    activity_code=activity.code,
                    original_start=old_start,
                    original_finish=old_finish,
                    new_start=new_start,
                    new_finish=new_finish,
                    delay_days=delay_days,
                    reason=f"Resource {resource_name} conflict on {conflict.conflict_date}",
                )
            )

            # Propagate to successors
            await self._propagate_to_successors(
                activity_to_delay,
                activity_dates,
                activity_lookup,
            )

            # Rebuild conflict matrix with new dates
            conflicts = await self._build_conflict_matrix(program_id, activity_dates, options)

        # Calculate final metrics
        new_finish = max(dates[1] for dates in activity_dates.values())
        remaining = len(conflicts)
        extension_days = max(0, (new_finish - original_finish).days)

        return ParallelLevelingResult(
            program_id=program_id,
            success=remaining == 0,
            iterations_used=iteration,
            activities_shifted=len({s.activity_id for s in shifts}),
            shifts=shifts,
            remaining_overallocations=remaining,
            new_project_finish=new_finish,
            original_project_finish=original_finish,
            schedule_extension_days=extension_days,
            warnings=warnings,
            conflicts_resolved=initial_conflict_count - remaining,
            resources_processed=len(unique_resources),
        )

    async def _get_project_finish(self, program_id: UUID) -> date:
        """Get the current project finish date.

        Args:
            program_id: Program to check

        Returns:
            Latest activity finish date in the program
        """
        activities = await self._activity_repo.get_by_program(program_id, skip=0, limit=100000)

        if not activities:
            program = await self._program_repo.get_by_id(program_id)
            return program.end_date if program else date.today()

        max_finish = date.min
        for activity in activities:
            finish = activity.early_finish or activity.planned_finish
            if finish and finish > max_finish:
                max_finish = finish

        return max_finish if max_finish > date.min else date.today()

    async def _get_activities_with_schedule(
        self,
        program_id: UUID,
    ) -> list[Activity]:
        """Get all activities with their schedule dates.

        Args:
            program_id: Program to get activities for

        Returns:
            List of activities with schedule information
        """
        return await self._activity_repo.get_by_program(program_id, skip=0, limit=100000)

    async def _calculate_priorities(
        self,
        activities: list[Activity],
    ) -> dict[UUID, ActivityPriority]:
        """Calculate priority scores for all activities.

        Args:
            activities: List of activities to prioritize

        Returns:
            Dictionary mapping activity IDs to their priorities
        """
        priorities: dict[UUID, ActivityPriority] = {}

        for activity in activities:
            # Get resource count for this activity
            assignments = await self._assignment_repo.get_by_activity(activity.id)
            resource_count = len(assignments)

            early_start = activity.early_start or activity.planned_start or date.max
            total_float = activity.total_float if activity.total_float is not None else 9999

            priorities[activity.id] = ActivityPriority(
                activity_id=activity.id,
                early_start=early_start,
                total_float=total_float,
                is_critical=activity.is_critical or False,
                resource_count=resource_count,
            )

        return priorities

    async def _build_conflict_matrix(
        self,
        program_id: UUID,
        activity_dates: dict[UUID, tuple[date, date]],
        options: LevelingOptions,
    ) -> list[ResourceConflict]:
        """Build matrix of all resource conflicts.

        Scans all resources for overallocation periods and identifies
        which activities are competing for each overallocated slot.

        Args:
            program_id: Program to analyze
            activity_dates: Current working dates for activities
            options: Leveling options

        Returns:
            Heap-ordered list of ResourceConflict objects
        """
        conflicts: list[ResourceConflict] = []

        # Get all resources
        resources, _ = await self._resource_repo.get_by_program(
            program_id, is_active=True, skip=0, limit=10000
        )
        target_ids = set(options.target_resources) if options.target_resources else None

        # Find date range from activity dates
        if not activity_dates:
            return conflicts

        min_date = min(d[0] for d in activity_dates.values())
        max_date = max(d[1] for d in activity_dates.values())

        for resource in resources:
            if target_ids is not None and resource.id not in target_ids:
                continue

            # Get all assignments for this resource
            assignments = await self._assignment_repo.get_assignments_with_activities(resource.id)

            if not assignments:
                continue

            capacity = resource.capacity_per_day

            # Check each day in the range
            current = min_date
            while current <= max_date:
                # Skip weekends
                if current.weekday() >= 5:
                    current += timedelta(days=1)
                    continue

                # Calculate total load and identify activities on this day
                total_load = Decimal("0")
                activities_on_day: list[UUID] = []

                for assignment in assignments:
                    activity_id = assignment.activity_id
                    if activity_id not in activity_dates:
                        continue

                    act_start, act_finish = activity_dates[activity_id]

                    # Check if assignment is active on this day
                    if act_start <= current <= act_finish:
                        total_load += assignment.units * capacity
                        activities_on_day.append(activity_id)

                # Check for overallocation with multiple activities
                if total_load > capacity and len(activities_on_day) > 1:
                    heappush(
                        conflicts,
                        ResourceConflict(
                            resource_id=resource.id,
                            conflict_date=current,
                            overallocation_hours=total_load - capacity,
                            activities=activities_on_day,
                        ),
                    )

                current += timedelta(days=1)

        return conflicts

    def _select_activity_to_delay(
        self,
        conflict: ResourceConflict,
        priority_map: dict[UUID, ActivityPriority],
        activity_dates: dict[UUID, tuple[date, date]],
        options: LevelingOptions,
    ) -> UUID | None:
        """Select the best activity to delay based on priorities.

        Chooses the activity with the lowest priority (most flexible)
        that can actually be delayed according to options.

        Args:
            conflict: The conflict to resolve
            priority_map: Activity priority scores
            activity_dates: Current working dates
            options: Leveling options

        Returns:
            Activity ID to delay, or None if no candidate found
        """
        candidates: list[tuple[tuple[int, date, int, int], UUID]] = []

        for activity_id in conflict.activities:
            priority = priority_map.get(activity_id)
            if priority is None:
                continue

            # Skip critical path if option set
            if options.preserve_critical_path and priority.is_critical:
                continue

            # Check float constraint
            if options.level_within_float:
                current_start = activity_dates[activity_id][0]
                original_start = priority.early_start
                used_float = (current_start - original_start).days
                if used_float >= priority.total_float:
                    continue

            candidates.append((priority.score, activity_id))

        if not candidates:
            return None

        # Return activity with highest score (lowest priority = most flexible)
        candidates.sort(reverse=True)
        return candidates[0][1]

    async def _calculate_minimum_delay(  # noqa: PLR0912
        self,
        activity_id: UUID,
        resource_id: UUID,
        conflict_date: date,
        activity_dates: dict[UUID, tuple[date, date]],
    ) -> int:
        """Calculate minimum delay to resolve conflict.

        Finds the next available slot for the resource and determines
        how many days the activity needs to be delayed.

        Args:
            activity_id: Activity to delay
            resource_id: Conflicting resource
            conflict_date: Date of conflict
            activity_dates: Current working dates

        Returns:
            Number of days to delay (minimum 1)
        """
        current_start, current_finish = activity_dates[activity_id]
        duration = (current_finish - current_start).days

        # Get resource and its assignments
        resource = await self._resource_repo.get_by_id(resource_id)
        if not resource:
            return 1

        capacity = resource.capacity_per_day
        assignments = await self._assignment_repo.get_assignments_with_activities(resource_id)

        # Get the assignment for this activity
        activity_assignment = None
        for a in assignments:
            if a.activity_id == activity_id:
                activity_assignment = a
                break

        if not activity_assignment:
            return 1

        activity_units = activity_assignment.units

        # Search forward from conflict date for available slot
        candidate_start = conflict_date + timedelta(days=1)
        max_search_days = 365

        for _ in range(max_search_days):
            # Skip weekends
            while candidate_start.weekday() >= 5:
                candidate_start += timedelta(days=1)

            candidate_finish = candidate_start + timedelta(days=duration)

            # Check if this slot works for the entire duration
            slot_works = True
            check_date = candidate_start

            while check_date <= candidate_finish:
                if check_date.weekday() >= 5:
                    check_date += timedelta(days=1)
                    continue

                # Calculate load on this day (excluding current activity)
                total_load = Decimal("0")
                for assignment in assignments:
                    if assignment.activity_id == activity_id:
                        continue

                    if assignment.activity_id not in activity_dates:
                        continue

                    act_start, act_finish = activity_dates[assignment.activity_id]
                    if act_start <= check_date <= act_finish:
                        total_load += assignment.units * capacity

                # Check if adding this activity would exceed capacity
                if total_load + (activity_units * capacity) > capacity:
                    slot_works = False
                    break

                check_date += timedelta(days=1)

            if slot_works:
                return (candidate_start - current_start).days

            candidate_start += timedelta(days=1)

        # If no slot found, return a reasonable delay
        return max_search_days

    async def _propagate_to_successors(
        self,
        activity_id: UUID,
        activity_dates: dict[UUID, tuple[date, date]],
        activity_lookup: dict[UUID, Activity],
    ) -> None:
        """Propagate delay to successor activities.

        Updates successor dates based on dependency relationships.
        Recursively propagates changes through the network.

        Args:
            activity_id: Activity that was delayed
            activity_dates: Working dates to update
            activity_lookup: Activity lookup by ID
        """
        # Get dependencies where this activity is predecessor
        dependencies = await self._dependency_repo.get_successors(activity_id)

        for dep in dependencies:
            successor_id = dep.successor_id
            if successor_id not in activity_lookup:
                continue
            if successor_id not in activity_dates:
                continue

            predecessor_start, predecessor_finish = activity_dates[activity_id]
            current_start, current_finish = activity_dates[successor_id]
            duration = (current_finish - current_start).days

            # Calculate new earliest start based on dependency type
            lag = dep.lag or 0
            dep_type = dep.dependency_type.value if dep.dependency_type else "FS"

            if dep_type == "FS":  # Finish-to-Start
                new_earliest = predecessor_finish + timedelta(days=1 + lag)
            elif dep_type == "SS":  # Start-to-Start
                new_earliest = predecessor_start + timedelta(days=lag)
            elif dep_type == "FF":  # Finish-to-Finish
                new_earliest = predecessor_finish + timedelta(days=lag) - timedelta(days=duration)
            elif dep_type == "SF":  # Start-to-Finish
                new_earliest = predecessor_start + timedelta(days=lag) - timedelta(days=duration)
            else:
                new_earliest = predecessor_finish + timedelta(days=1 + lag)

            # Only update if new date is later
            if new_earliest > current_start:
                new_finish = new_earliest + timedelta(days=duration)
                activity_dates[successor_id] = (new_earliest, new_finish)

                # Recursively update successors
                await self._propagate_to_successors(successor_id, activity_dates, activity_lookup)

    async def apply_leveling_result(
        self,
        result: ParallelLevelingResult,
    ) -> bool:
        """Apply leveling result to database by updating activity dates.

        Args:
            result: Leveling result to apply

        Returns:
            True if changes were applied successfully
        """
        if not result.shifts:
            return True

        # Group shifts by activity (take latest shift for each)
        final_shifts: dict[UUID, ActivityShift] = {}
        for shift in result.shifts:
            final_shifts[shift.activity_id] = shift

        # Update each activity
        for activity_id, shift in final_shifts.items():
            activity = await self._activity_repo.get_by_id(activity_id)
            if activity:
                # Update planned dates
                activity.planned_start = shift.new_start
                activity.planned_finish = shift.new_finish
                await self.session.flush()

        return True
