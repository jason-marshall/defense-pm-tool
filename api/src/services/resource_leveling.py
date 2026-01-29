"""Serial resource leveling algorithm for resolving over-allocations.

Processes activities one at a time in priority order, delaying activities
when resources are overallocated to achieve feasible resource schedules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from src.repositories.activity import ActivityRepository
from src.repositories.dependency import DependencyRepository
from src.repositories.program import ProgramRepository
from src.repositories.resource import ResourceAssignmentRepository, ResourceRepository
from src.services.resource_loading import ResourceLoadingService

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.models.activity import Activity
    from src.services.cache_service import CacheService


@dataclass
class LevelingOptions:
    """Options for controlling resource leveling behavior.

    Attributes:
        preserve_critical_path: If True, never delay critical path activities
        max_iterations: Maximum leveling iterations before stopping
        target_resources: Specific resources to level (None = all resources)
        level_within_float: If True, only delay activities within their total float
    """

    preserve_critical_path: bool = True
    max_iterations: int = 100
    target_resources: list[UUID] | None = None
    level_within_float: bool = True


@dataclass
class ActivityShift:
    """Records a single activity delay during leveling.

    Attributes:
        activity_id: UUID of the shifted activity
        activity_code: Activity code for display
        original_start: Original early start date
        original_finish: Original early finish date
        new_start: New start date after leveling
        new_finish: New finish date after leveling
        delay_days: Number of days delayed
        reason: Explanation for the delay
    """

    activity_id: UUID
    activity_code: str
    original_start: date
    original_finish: date
    new_start: date
    new_finish: date
    delay_days: int
    reason: str


@dataclass
class LevelingResult:
    """Results from a resource leveling operation.

    Attributes:
        program_id: UUID of the leveled program
        success: True if all over-allocations resolved
        iterations_used: Number of leveling iterations performed
        activities_shifted: Count of activities that were delayed
        shifts: List of all activity shifts made
        remaining_overallocations: Count of unresolved over-allocations
        new_project_finish: Project finish date after leveling
        original_project_finish: Project finish date before leveling
        schedule_extension_days: Days added to project duration
        warnings: List of warning messages
    """

    program_id: UUID
    success: bool
    iterations_used: int
    activities_shifted: int
    shifts: list[ActivityShift]
    remaining_overallocations: int
    new_project_finish: date
    original_project_finish: date
    schedule_extension_days: int
    warnings: list[str] = field(default_factory=list)


class ResourceLevelingService:
    """Service for serial resource leveling.

    Implements a priority-based serial leveling algorithm that processes
    activities one at a time, delaying those that cause over-allocations.

    Algorithm:
    1. Sort activities by leveling priority (early_start, total_float, id)
    2. For each activity, check if it causes over-allocation
    3. If overallocated, find next available slot for the resource
    4. Delay activity if allowed (respects critical path and float constraints)
    5. Recalculate successor dates
    6. Repeat until no more changes or max iterations reached

    Example usage:
        service = ResourceLevelingService(session)
        options = LevelingOptions(preserve_critical_path=True)
        result = await service.level_program(program_id, options)

        if result.success:
            print(f"Leveled in {result.iterations_used} iterations")
            for shift in result.shifts:
                print(f"{shift.activity_code}: delayed {shift.delay_days} days")
    """

    def __init__(
        self,
        session: AsyncSession,
        cache: CacheService | None = None,
    ) -> None:
        """Initialize ResourceLevelingService.

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

    async def level_program(  # noqa: PLR0912, PLR0915
        self,
        program_id: UUID,
        options: LevelingOptions | None = None,
    ) -> LevelingResult:
        """Main entry point for resource leveling.

        Applies serial leveling algorithm to resolve resource over-allocations
        in the program.

        Args:
            program_id: Program to level
            options: Leveling options (uses defaults if None)

        Returns:
            LevelingResult with details of all changes made
        """
        if options is None:
            options = LevelingOptions()

        # Get program info
        program = await self._program_repo.get_by_id(program_id)
        if not program:
            return LevelingResult(
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

        # Get original project finish
        original_finish = await self._get_project_finish(program_id)

        # Get all activities sorted by leveling priority
        activities = await self._get_sorted_activities(program_id)
        if not activities:
            return LevelingResult(
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

        # Get target resources
        target_resource_ids = await self._get_target_resources(program_id, options)

        # Build activity lookup for fast access
        activity_lookup: dict[UUID, Activity] = {a.id: a for a in activities}

        # Track shifts and working copies of dates
        shifts: list[ActivityShift] = []
        working_dates: dict[UUID, tuple[date, date]] = {}
        for activity in activities:
            start = activity.early_start or activity.planned_start or program.start_date
            finish = activity.early_finish or activity.planned_finish or program.end_date
            working_dates[activity.id] = (start, finish)

        warnings: list[str] = []
        iteration = 0

        while iteration < options.max_iterations:
            iteration += 1
            made_change = False

            # Process each activity in priority order
            for activity in activities:
                current_start, current_finish = working_dates[activity.id]

                # Get assignments for this activity
                assignments = await self._assignment_repo.get_by_activity(activity.id)

                for assignment in assignments:
                    # Skip if not a target resource
                    if (
                        target_resource_ids is not None
                        and assignment.resource_id not in target_resource_ids
                    ):
                        continue

                    # Check for over-allocation
                    if await self._is_overallocated_on_dates(
                        assignment.resource_id,
                        current_start,
                        current_finish,
                        working_dates,
                        activity_lookup,
                    ):
                        # Find next available slot
                        new_start = await self._find_next_available_slot(
                            activity,
                            assignment.resource_id,
                            current_start,
                            working_dates,
                            activity_lookup,
                        )

                        delay_days = (new_start - current_start).days
                        if delay_days <= 0:
                            continue

                        # Check if we can delay
                        if not self._can_delay_activity(
                            activity, delay_days, options, working_dates
                        ):
                            if options.preserve_critical_path and activity.is_critical:
                                warnings.append(f"Cannot delay critical activity {activity.code}")
                            continue

                        # Apply the delay
                        new_finish = new_start + (current_finish - current_start)

                        # Get resource info for reason
                        resource = await self._resource_repo.get_by_id(assignment.resource_id)
                        reason = (
                            f"Resource {resource.code} overallocated"
                            if resource
                            else "Resource overallocated"
                        )

                        shift = ActivityShift(
                            activity_id=activity.id,
                            activity_code=activity.code,
                            original_start=current_start,
                            original_finish=current_finish,
                            new_start=new_start,
                            new_finish=new_finish,
                            delay_days=delay_days,
                            reason=reason,
                        )
                        shifts.append(shift)

                        # Update working dates
                        working_dates[activity.id] = (new_start, new_finish)

                        # Recalculate successor dates
                        await self._recalculate_successors(
                            activity.id, working_dates, activity_lookup
                        )

                        made_change = True
                        break

                if made_change:
                    break

            if not made_change:
                break

        # Count remaining over-allocations
        remaining = await self._count_remaining_overallocations(
            program_id, target_resource_ids, working_dates, activity_lookup
        )

        # Calculate new project finish
        new_finish = original_finish
        for _act_start, act_finish in working_dates.values():
            new_finish = max(new_finish, act_finish)

        extension_days = (new_finish - original_finish).days
        extension_days = max(extension_days, 0)

        return LevelingResult(
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
        )

    def _get_leveling_priority(
        self,
        activity: Activity,
        working_dates: dict[UUID, tuple[date, date]],
    ) -> tuple[date, int, UUID]:
        """Get sorting key for leveling priority.

        Activities are processed in order of:
        1. Early start date (earliest first)
        2. Total float (least float first - more constrained)
        3. Activity ID (for deterministic ordering)

        Args:
            activity: Activity to get priority for
            working_dates: Current working dates

        Returns:
            Tuple for sorting (early_start, total_float, id)
        """
        start, _ = working_dates.get(activity.id, (activity.early_start or date.max, date.max))
        total_float = activity.total_float if activity.total_float is not None else 9999
        return (start, total_float, activity.id)

    async def _get_sorted_activities(self, program_id: UUID) -> list[Activity]:
        """Get all activities sorted by leveling priority.

        Args:
            program_id: Program to get activities for

        Returns:
            List of activities sorted by (early_start, total_float, id)
        """
        activities = await self._activity_repo.get_by_program(program_id, skip=0, limit=100000)

        # Create working dates for sorting
        working_dates: dict[UUID, tuple[date, date]] = {}
        for activity in activities:
            start = activity.early_start or activity.planned_start or date.max
            finish = activity.early_finish or activity.planned_finish or date.max
            working_dates[activity.id] = (start, finish)

        return sorted(
            activities,
            key=lambda a: self._get_leveling_priority(a, working_dates),
        )

    async def _get_target_resources(
        self,
        _program_id: UUID,
        options: LevelingOptions,
    ) -> set[UUID] | None:
        """Get set of resource IDs to level.

        Args:
            program_id: Program to get resources for
            options: Leveling options with target_resources

        Returns:
            Set of resource IDs, or None if leveling all resources
        """
        if options.target_resources is not None:
            return set(options.target_resources)
        return None  # Level all resources

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

    async def _is_overallocated_on_dates(
        self,
        resource_id: UUID,
        start_date: date,
        end_date: date,
        working_dates: dict[UUID, tuple[date, date]],
        _activity_lookup: dict[UUID, Activity],
    ) -> bool:
        """Check if resource is overallocated during date range.

        Uses working dates to calculate current loading state.

        Args:
            resource_id: Resource to check
            start_date: Start of range
            end_date: End of range
            working_dates: Current activity dates
            activity_lookup: Activity lookup by ID

        Returns:
            True if resource is overallocated on any day in range
        """
        resource = await self._resource_repo.get_by_id(resource_id)
        if not resource:
            return False

        capacity = resource.capacity_per_day

        # Get all assignments for this resource
        assignments = await self._assignment_repo.get_assignments_with_activities(resource_id)

        # Check each day in range
        current = start_date
        while current <= end_date:
            # Skip weekends (simple check)
            if current.weekday() >= 5:
                current += timedelta(days=1)
                continue

            total_assigned = Decimal("0")

            for assignment in assignments:
                # Get effective dates from working_dates
                if assignment.activity_id in working_dates:
                    act_start, act_finish = working_dates[assignment.activity_id]
                else:
                    maybe_start, maybe_finish = self._loading_service.get_assignment_date_range(
                        assignment
                    )
                    if maybe_start is None or maybe_finish is None:
                        continue
                    act_start, act_finish = maybe_start, maybe_finish

                # Check if assignment is active on this day
                if act_start <= current <= act_finish:
                    total_assigned += assignment.units * capacity

            if total_assigned > capacity:
                return True

            current += timedelta(days=1)

        return False

    async def _find_next_available_slot(  # noqa: PLR0912
        self,
        activity: Activity,
        resource_id: UUID,
        earliest_start: date,
        working_dates: dict[UUID, tuple[date, date]],
        _activity_lookup: dict[UUID, Activity],
    ) -> date:
        """Find next date when resource has capacity for activity.

        Searches forward from earliest_start until finding a slot where
        the resource can accommodate the activity without over-allocation.

        Args:
            activity: Activity to schedule
            resource_id: Resource to check
            earliest_start: Earliest possible start date
            working_dates: Current activity dates
            activity_lookup: Activity lookup by ID

        Returns:
            Date when activity can start without over-allocating resource
        """
        resource = await self._resource_repo.get_by_id(resource_id)
        if not resource:
            return earliest_start

        capacity = resource.capacity_per_day

        # Get assignment for this activity/resource
        assignments = await self._assignment_repo.get_by_activity(activity.id)
        activity_assignment = None
        for a in assignments:
            if a.resource_id == resource_id:
                activity_assignment = a
                break

        if not activity_assignment:
            return earliest_start

        activity_units = activity_assignment.units
        _, current_finish = working_dates.get(activity.id, (earliest_start, earliest_start))
        activity_duration = (current_finish - earliest_start).days

        # Get all other assignments for this resource
        all_assignments = await self._assignment_repo.get_assignments_with_activities(resource_id)

        candidate_start = earliest_start
        max_search_days = 365  # Limit search to 1 year

        for _ in range(max_search_days):
            # Skip weekends
            while candidate_start.weekday() >= 5:
                candidate_start += timedelta(days=1)

            candidate_finish = candidate_start + timedelta(days=activity_duration)

            # Check if this slot works
            slot_works = True
            current = candidate_start
            while current <= candidate_finish:
                if current.weekday() >= 5:
                    current += timedelta(days=1)
                    continue

                # Calculate total load on this day (excluding current activity)
                total_load = Decimal("0")
                for assignment in all_assignments:
                    if assignment.activity_id == activity.id:
                        continue

                    if assignment.activity_id in working_dates:
                        act_start, act_finish = working_dates[assignment.activity_id]
                    else:
                        maybe_start, maybe_finish = self._loading_service.get_assignment_date_range(
                            assignment
                        )
                        if maybe_start is None or maybe_finish is None:
                            continue
                        act_start, act_finish = maybe_start, maybe_finish

                    if act_start <= current <= act_finish:
                        total_load += assignment.units * capacity

                # Check if adding this activity would exceed capacity
                if total_load + (activity_units * capacity) > capacity:
                    slot_works = False
                    break

                current += timedelta(days=1)

            if slot_works:
                return candidate_start

            candidate_start += timedelta(days=1)

        # If no slot found within search limit, return far future date
        return earliest_start + timedelta(days=max_search_days)

    def _can_delay_activity(
        self,
        activity: Activity,
        delay_days: int,
        options: LevelingOptions,
        _working_dates: dict[UUID, tuple[date, date]],
    ) -> bool:
        """Check if activity can be delayed by specified amount.

        Considers:
        - Critical path preservation option
        - Float constraints if level_within_float is True

        Args:
            activity: Activity to potentially delay
            delay_days: Proposed delay in days
            options: Leveling options
            working_dates: Current activity dates

        Returns:
            True if delay is allowed
        """
        if delay_days <= 0:
            return False

        # Check critical path constraint
        if options.preserve_critical_path and activity.is_critical:
            return False

        # Check float constraint
        if options.level_within_float:
            total_float = activity.total_float or 0
            if delay_days > total_float:
                return False

        return True

    async def _recalculate_successors(
        self,
        activity_id: UUID,
        working_dates: dict[UUID, tuple[date, date]],
        activity_lookup: dict[UUID, Activity],
    ) -> None:
        """Update dates for all successor activities after a delay.

        Propagates date changes through the dependency network.

        Args:
            activity_id: Activity that was delayed
            working_dates: Working dates to update
            activity_lookup: Activity lookup by ID
        """
        # Get dependencies where this activity is predecessor
        dependencies = await self._dependency_repo.get_successors(activity_id)

        for dep in dependencies:
            successor_id = dep.successor_id
            if successor_id not in activity_lookup:
                continue

            predecessor_start, predecessor_finish = working_dates[activity_id]
            current_start, current_finish = working_dates[successor_id]
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
                working_dates[successor_id] = (new_earliest, new_finish)

                # Recursively update successors
                await self._recalculate_successors(successor_id, working_dates, activity_lookup)

    async def _count_remaining_overallocations(
        self,
        program_id: UUID,
        target_resource_ids: set[UUID] | None,
        working_dates: dict[UUID, tuple[date, date]],
        activity_lookup: dict[UUID, Activity],
    ) -> int:
        """Count remaining over-allocation periods after leveling.

        Args:
            program_id: Program to check
            target_resource_ids: Resources to check (None = all)
            working_dates: Current activity dates
            activity_lookup: Activity lookup by ID

        Returns:
            Number of remaining over-allocation periods
        """
        # Get all resources for program
        resources, _ = await self._resource_repo.get_by_program(
            program_id, is_active=True, skip=0, limit=10000
        )

        count = 0
        for resource in resources:
            if target_resource_ids is not None and resource.id not in target_resource_ids:
                continue

            # Get date range from working dates
            min_date = date.max
            max_date = date.min
            for act_start, act_finish in working_dates.values():
                min_date = min(min_date, act_start)
                max_date = max(max_date, act_finish)

            if min_date >= max_date:
                continue

            # Check for over-allocations
            if await self._is_overallocated_on_dates(
                resource.id, min_date, max_date, working_dates, activity_lookup
            ):
                count += 1

        return count

    async def apply_leveling_result(
        self,
        result: LevelingResult,
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
