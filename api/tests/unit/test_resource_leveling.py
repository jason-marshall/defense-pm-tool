"""Unit tests for ResourceLevelingService.

Tests the serial resource leveling algorithm including:
- Simple over-allocation resolution
- Critical path preservation
- Float constraints
- Multiple resource handling
- Successor recalculation
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.services.resource_leveling import (
    ActivityShift,
    LevelingOptions,
    LevelingResult,
    ResourceLevelingService,
)


class TestLevelingOptions:
    """Tests for LevelingOptions dataclass."""

    def test_default_options(self) -> None:
        """Should have sensible defaults."""
        options = LevelingOptions()

        assert options.preserve_critical_path is True
        assert options.max_iterations == 100
        assert options.target_resources is None
        assert options.level_within_float is True

    def test_custom_options(self) -> None:
        """Should accept custom values."""
        resource_ids = [uuid4(), uuid4()]
        options = LevelingOptions(
            preserve_critical_path=False,
            max_iterations=50,
            target_resources=resource_ids,
            level_within_float=False,
        )

        assert options.preserve_critical_path is False
        assert options.max_iterations == 50
        assert options.target_resources == resource_ids
        assert options.level_within_float is False


class TestActivityShift:
    """Tests for ActivityShift dataclass."""

    def test_shift_creation(self) -> None:
        """Should create shift with all fields."""
        activity_id = uuid4()
        shift = ActivityShift(
            activity_id=activity_id,
            activity_code="ACT-001",
            original_start=date(2024, 1, 15),
            original_finish=date(2024, 1, 19),
            new_start=date(2024, 1, 22),
            new_finish=date(2024, 1, 26),
            delay_days=7,
            reason="Resource ENG-001 overallocated",
        )

        assert shift.activity_id == activity_id
        assert shift.delay_days == 7
        assert shift.reason == "Resource ENG-001 overallocated"


class TestLevelingResult:
    """Tests for LevelingResult dataclass."""

    def test_successful_result(self) -> None:
        """Should represent successful leveling."""
        program_id = uuid4()
        result = LevelingResult(
            program_id=program_id,
            success=True,
            iterations_used=5,
            activities_shifted=3,
            shifts=[],
            remaining_overallocations=0,
            new_project_finish=date(2024, 2, 28),
            original_project_finish=date(2024, 2, 15),
            schedule_extension_days=13,
        )

        assert result.success is True
        assert result.schedule_extension_days == 13

    def test_result_with_warnings(self) -> None:
        """Should include warnings."""
        result = LevelingResult(
            program_id=uuid4(),
            success=False,
            iterations_used=100,
            activities_shifted=10,
            shifts=[],
            remaining_overallocations=2,
            new_project_finish=date(2024, 3, 15),
            original_project_finish=date(2024, 2, 15),
            schedule_extension_days=28,
            warnings=["Cannot delay critical activity ACT-001"],
        )

        assert result.success is False
        assert len(result.warnings) == 1


class TestGetLevelingPriority:
    """Tests for _get_leveling_priority method."""

    def test_priority_by_early_start(self) -> None:
        """Should prioritize earlier start dates."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        activity1 = MagicMock()
        activity1.id = uuid4()
        activity1.early_start = date(2024, 1, 15)
        activity1.total_float = 5

        activity2 = MagicMock()
        activity2.id = uuid4()
        activity2.early_start = date(2024, 1, 10)
        activity2.total_float = 5

        working_dates = {
            activity1.id: (date(2024, 1, 15), date(2024, 1, 19)),
            activity2.id: (date(2024, 1, 10), date(2024, 1, 14)),
        }

        priority1 = service._get_leveling_priority(activity1, working_dates)
        priority2 = service._get_leveling_priority(activity2, working_dates)

        # Activity2 should come first (earlier start)
        assert priority2 < priority1

    def test_priority_by_float_when_same_start(self) -> None:
        """Should prioritize less float when same start date."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        activity1 = MagicMock()
        activity1.id = uuid4()
        activity1.total_float = 10

        activity2 = MagicMock()
        activity2.id = uuid4()
        activity2.total_float = 2

        # Same start date
        working_dates = {
            activity1.id: (date(2024, 1, 15), date(2024, 1, 19)),
            activity2.id: (date(2024, 1, 15), date(2024, 1, 19)),
        }

        priority1 = service._get_leveling_priority(activity1, working_dates)
        priority2 = service._get_leveling_priority(activity2, working_dates)

        # Activity2 should come first (less float = more constrained)
        assert priority2 < priority1


class TestCanDelayActivity:
    """Tests for _can_delay_activity method."""

    def test_cannot_delay_critical_when_preserved(self) -> None:
        """Should not delay critical activities when preserve_critical_path is True."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        activity = MagicMock()
        activity.is_critical = True
        activity.total_float = 0

        options = LevelingOptions(preserve_critical_path=True)
        working_dates = {}

        result = service._can_delay_activity(activity, 5, options, working_dates)

        assert result is False

    def test_can_delay_critical_when_not_preserved(self) -> None:
        """Should allow delaying critical activities when preserve_critical_path is False."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        activity = MagicMock()
        activity.is_critical = True
        activity.total_float = 0

        options = LevelingOptions(preserve_critical_path=False, level_within_float=False)
        working_dates = {}

        result = service._can_delay_activity(activity, 5, options, working_dates)

        assert result is True

    def test_cannot_delay_beyond_float(self) -> None:
        """Should not delay beyond total float when level_within_float is True."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        activity = MagicMock()
        activity.is_critical = False
        activity.total_float = 3

        options = LevelingOptions(level_within_float=True)
        working_dates = {}

        # 5 days delay > 3 days float
        result = service._can_delay_activity(activity, 5, options, working_dates)

        assert result is False

    def test_can_delay_within_float(self) -> None:
        """Should allow delay within total float."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        activity = MagicMock()
        activity.is_critical = False
        activity.total_float = 10

        options = LevelingOptions(level_within_float=True)
        working_dates = {}

        # 5 days delay < 10 days float
        result = service._can_delay_activity(activity, 5, options, working_dates)

        assert result is True

    def test_can_delay_beyond_float_when_disabled(self) -> None:
        """Should allow delay beyond float when level_within_float is False."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        activity = MagicMock()
        activity.is_critical = False
        activity.total_float = 3

        options = LevelingOptions(level_within_float=False)
        working_dates = {}

        # 10 days delay > 3 days float, but constraint disabled
        result = service._can_delay_activity(activity, 10, options, working_dates)

        assert result is True

    def test_cannot_delay_zero_days(self) -> None:
        """Should not allow zero or negative delays."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        activity = MagicMock()
        activity.is_critical = False
        activity.total_float = 10

        options = LevelingOptions()
        working_dates = {}

        assert service._can_delay_activity(activity, 0, options, working_dates) is False
        assert service._can_delay_activity(activity, -1, options, working_dates) is False


class TestLevelingSimpleOverallocation:
    """Tests for leveling simple over-allocation scenarios."""

    @pytest.mark.asyncio
    async def test_leveling_simple_overallocation(self) -> None:
        """Should resolve simple over-allocation by delaying activity."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        program_id = uuid4()
        activity_id = uuid4()
        resource_id = uuid4()

        # Mock program
        mock_program = MagicMock()
        mock_program.start_date = date(2024, 1, 1)
        mock_program.end_date = date(2024, 12, 31)
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        # Mock activity
        mock_activity = MagicMock()
        mock_activity.id = activity_id
        mock_activity.code = "ACT-001"
        mock_activity.early_start = date(2024, 1, 15)
        mock_activity.early_finish = date(2024, 1, 19)
        mock_activity.planned_start = date(2024, 1, 15)
        mock_activity.planned_finish = date(2024, 1, 19)
        mock_activity.is_critical = False
        mock_activity.total_float = 10

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[mock_activity])

        # Mock resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "ENG-001"
        mock_resource.capacity_per_day = Decimal("8.0")
        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._resource_repo.get_by_program = AsyncMock(return_value=[mock_resource])

        # Mock assignment
        mock_assignment = MagicMock()
        mock_assignment.activity_id = activity_id
        mock_assignment.resource_id = resource_id
        mock_assignment.units = Decimal("1.0")
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[mock_assignment])
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[mock_assignment]
        )

        # Mock no dependencies
        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = AsyncMock(return_value=[])

        # Mock over-allocation detection (first call: overallocated, second: not)
        call_count = [0]

        async def mock_is_overallocated(*args, **kwargs):
            call_count[0] += 1
            return call_count[0] == 1  # Only overallocated on first check

        service._is_overallocated_on_dates = mock_is_overallocated

        # Mock finding available slot
        service._find_next_available_slot = AsyncMock(
            return_value=date(2024, 1, 22)  # 7 days later
        )

        # Mock counting remaining
        service._count_remaining_overallocations = AsyncMock(return_value=0)

        # Act
        result = await service.level_program(program_id)

        # Assert
        assert result.success is True
        assert result.activities_shifted == 1
        assert len(result.shifts) == 1
        assert result.shifts[0].delay_days == 7

    @pytest.mark.asyncio
    async def test_leveling_no_change_when_no_overallocation(self) -> None:
        """Should not make changes when no over-allocation exists."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        program_id = uuid4()
        activity_id = uuid4()
        resource_id = uuid4()

        # Mock program
        mock_program = MagicMock()
        mock_program.start_date = date(2024, 1, 1)
        mock_program.end_date = date(2024, 12, 31)
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        # Mock activity
        mock_activity = MagicMock()
        mock_activity.id = activity_id
        mock_activity.code = "ACT-001"
        mock_activity.early_start = date(2024, 1, 15)
        mock_activity.early_finish = date(2024, 1, 19)
        mock_activity.planned_start = date(2024, 1, 15)
        mock_activity.planned_finish = date(2024, 1, 19)
        mock_activity.is_critical = False
        mock_activity.total_float = 10

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[mock_activity])

        # Mock resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "ENG-001"
        mock_resource.capacity_per_day = Decimal("8.0")
        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._resource_repo.get_by_program = AsyncMock(return_value=[mock_resource])

        # Mock assignment
        mock_assignment = MagicMock()
        mock_assignment.activity_id = activity_id
        mock_assignment.resource_id = resource_id
        mock_assignment.units = Decimal("0.5")  # 50% - no over-allocation
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[mock_assignment])

        # No over-allocation
        service._is_overallocated_on_dates = AsyncMock(return_value=False)
        service._count_remaining_overallocations = AsyncMock(return_value=0)

        # Act
        result = await service.level_program(program_id)

        # Assert
        assert result.success is True
        assert result.activities_shifted == 0
        assert len(result.shifts) == 0
        assert result.iterations_used == 1


class TestLevelingRespectsConstraints:
    """Tests for leveling constraint handling."""

    @pytest.mark.asyncio
    async def test_leveling_respects_critical_path(self) -> None:
        """Should not delay critical path activities when preserve_critical_path is True."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        program_id = uuid4()
        activity_id = uuid4()
        resource_id = uuid4()

        # Mock program
        mock_program = MagicMock()
        mock_program.start_date = date(2024, 1, 1)
        mock_program.end_date = date(2024, 12, 31)
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        # Mock CRITICAL activity
        mock_activity = MagicMock()
        mock_activity.id = activity_id
        mock_activity.code = "ACT-001"
        mock_activity.early_start = date(2024, 1, 15)
        mock_activity.early_finish = date(2024, 1, 19)
        mock_activity.planned_start = date(2024, 1, 15)
        mock_activity.planned_finish = date(2024, 1, 19)
        mock_activity.is_critical = True  # Critical path!
        mock_activity.total_float = 0

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[mock_activity])

        # Mock resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "ENG-001"
        mock_resource.capacity_per_day = Decimal("8.0")
        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._resource_repo.get_by_program = AsyncMock(return_value=[mock_resource])

        # Mock assignment
        mock_assignment = MagicMock()
        mock_assignment.activity_id = activity_id
        mock_assignment.resource_id = resource_id
        mock_assignment.units = Decimal("1.5")  # Over-allocated
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[mock_assignment])

        # Over-allocation exists
        service._is_overallocated_on_dates = AsyncMock(return_value=True)
        service._find_next_available_slot = AsyncMock(return_value=date(2024, 1, 22))
        service._count_remaining_overallocations = AsyncMock(return_value=1)

        # Act - preserve critical path
        options = LevelingOptions(preserve_critical_path=True)
        result = await service.level_program(program_id, options)

        # Assert - should not have shifted the critical activity
        assert result.activities_shifted == 0
        assert result.remaining_overallocations == 1
        assert "Cannot delay critical activity ACT-001" in result.warnings

    @pytest.mark.asyncio
    async def test_leveling_within_float_only(self) -> None:
        """Should only delay within float when level_within_float is True."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        program_id = uuid4()
        activity_id = uuid4()
        resource_id = uuid4()

        # Mock program
        mock_program = MagicMock()
        mock_program.start_date = date(2024, 1, 1)
        mock_program.end_date = date(2024, 12, 31)
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        # Mock activity with LIMITED float
        mock_activity = MagicMock()
        mock_activity.id = activity_id
        mock_activity.code = "ACT-001"
        mock_activity.early_start = date(2024, 1, 15)
        mock_activity.early_finish = date(2024, 1, 19)
        mock_activity.planned_start = date(2024, 1, 15)
        mock_activity.planned_finish = date(2024, 1, 19)
        mock_activity.is_critical = False
        mock_activity.total_float = 3  # Only 3 days of float

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[mock_activity])

        # Mock resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "ENG-001"
        mock_resource.capacity_per_day = Decimal("8.0")
        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._resource_repo.get_by_program = AsyncMock(return_value=[mock_resource])

        # Mock assignment
        mock_assignment = MagicMock()
        mock_assignment.activity_id = activity_id
        mock_assignment.resource_id = resource_id
        mock_assignment.units = Decimal("1.5")
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[mock_assignment])

        # Over-allocation exists, needs 7 days delay
        service._is_overallocated_on_dates = AsyncMock(return_value=True)
        service._find_next_available_slot = AsyncMock(
            return_value=date(2024, 1, 22)  # 7 days later
        )
        service._count_remaining_overallocations = AsyncMock(return_value=1)

        # Act - level within float only
        options = LevelingOptions(level_within_float=True)
        result = await service.level_program(program_id, options)

        # Assert - should not shift (7 days > 3 days float)
        assert result.activities_shifted == 0
        assert result.remaining_overallocations == 1


class TestLevelingMaxIterations:
    """Tests for max iterations limit."""

    @pytest.mark.asyncio
    async def test_leveling_max_iterations_limit(self) -> None:
        """Should stop after max iterations."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        program_id = uuid4()
        activity_id = uuid4()
        resource_id = uuid4()

        # Mock program
        mock_program = MagicMock()
        mock_program.start_date = date(2024, 1, 1)
        mock_program.end_date = date(2024, 12, 31)
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        # Mock activity
        mock_activity = MagicMock()
        mock_activity.id = activity_id
        mock_activity.code = "ACT-001"
        mock_activity.early_start = date(2024, 1, 15)
        mock_activity.early_finish = date(2024, 1, 19)
        mock_activity.planned_start = date(2024, 1, 15)
        mock_activity.planned_finish = date(2024, 1, 19)
        mock_activity.is_critical = False
        mock_activity.total_float = 100

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[mock_activity])

        # Mock resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "ENG-001"
        mock_resource.capacity_per_day = Decimal("8.0")
        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._resource_repo.get_by_program = AsyncMock(return_value=[mock_resource])

        # Mock assignment
        mock_assignment = MagicMock()
        mock_assignment.activity_id = activity_id
        mock_assignment.resource_id = resource_id
        mock_assignment.units = Decimal("1.5")
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[mock_assignment])

        # Always overallocated (infinite loop scenario)
        service._is_overallocated_on_dates = AsyncMock(return_value=True)

        call_count = [0]
        original_start = date(2024, 1, 15)

        async def incrementing_slot(*args, **kwargs):
            call_count[0] += 1
            return original_start + timedelta(days=call_count[0])

        service._find_next_available_slot = incrementing_slot
        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = AsyncMock(return_value=[])
        service._count_remaining_overallocations = AsyncMock(return_value=1)

        # Act - very low max iterations
        options = LevelingOptions(max_iterations=5)
        result = await service.level_program(program_id, options)

        # Assert - should stop at max iterations
        assert result.iterations_used == 5
        assert result.success is False


class TestLevelingEmptyProgram:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_leveling_empty_program(self) -> None:
        """Should handle program with no activities."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        program_id = uuid4()

        # Mock program
        mock_program = MagicMock()
        mock_program.start_date = date(2024, 1, 1)
        mock_program.end_date = date(2024, 12, 31)
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        # No activities
        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[])

        # Act
        result = await service.level_program(program_id)

        # Assert
        assert result.success is True
        assert result.activities_shifted == 0
        assert result.iterations_used == 0

    @pytest.mark.asyncio
    async def test_leveling_nonexistent_program(self) -> None:
        """Should handle nonexistent program."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        # Program not found
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=None)

        # Act
        result = await service.level_program(uuid4())

        # Assert
        assert result.success is False
        assert "Program not found" in result.warnings


class TestGetTargetResources:
    """Tests for _get_target_resources method."""

    @pytest.mark.asyncio
    async def test_target_resources_none(self) -> None:
        """Should return None when no target resources specified."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        options = LevelingOptions()
        result = await service._get_target_resources(uuid4(), options)

        assert result is None

    @pytest.mark.asyncio
    async def test_target_resources_specified(self) -> None:
        """Should return set of target resource IDs."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        resource_ids = [uuid4(), uuid4()]
        options = LevelingOptions(target_resources=resource_ids)
        result = await service._get_target_resources(uuid4(), options)

        assert result == set(resource_ids)


class TestGetProjectFinish:
    """Tests for _get_project_finish method."""

    @pytest.mark.asyncio
    async def test_project_finish_with_activities(self) -> None:
        """Should return latest activity finish date."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        activity1 = MagicMock()
        activity1.early_finish = date(2024, 2, 15)
        activity1.planned_finish = date(2024, 2, 15)

        activity2 = MagicMock()
        activity2.early_finish = date(2024, 3, 1)
        activity2.planned_finish = date(2024, 3, 1)

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[activity1, activity2])

        result = await service._get_project_finish(uuid4())

        assert result == date(2024, 3, 1)

    @pytest.mark.asyncio
    async def test_project_finish_no_activities(self) -> None:
        """Should return program end date when no activities."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        mock_program = MagicMock()
        mock_program.end_date = date(2024, 12, 31)

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[])
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        result = await service._get_project_finish(uuid4())

        assert result == date(2024, 12, 31)

    @pytest.mark.asyncio
    async def test_project_finish_no_program(self) -> None:
        """Should return today when no program found."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[])
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=None)

        result = await service._get_project_finish(uuid4())

        assert result == date.today()


class TestIsOverallocatedOnDates:
    """Tests for _is_overallocated_on_dates method."""

    @pytest.mark.asyncio
    async def test_not_overallocated_no_resource(self) -> None:
        """Should return False when resource not found."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=None)

        result = await service._is_overallocated_on_dates(
            uuid4(),
            date(2024, 1, 15),
            date(2024, 1, 19),
            {},
            {},
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_overallocated_on_weekday(self) -> None:
        """Should detect over-allocation on weekdays."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        resource_id = uuid4()
        activity_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        # Assignment with 150% allocation
        mock_assignment = MagicMock()
        mock_assignment.activity_id = activity_id
        mock_assignment.units = Decimal("1.5")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[mock_assignment]
        )

        # Working dates that overlap with check range
        working_dates = {
            activity_id: (date(2024, 1, 15), date(2024, 1, 19))  # Monday-Friday
        }

        result = await service._is_overallocated_on_dates(
            resource_id,
            date(2024, 1, 15),
            date(2024, 1, 19),
            working_dates,
            {},
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_not_overallocated_within_capacity(self) -> None:
        """Should return False when within capacity."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        resource_id = uuid4()
        activity_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        # Assignment with 50% allocation
        mock_assignment = MagicMock()
        mock_assignment.activity_id = activity_id
        mock_assignment.units = Decimal("0.5")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[mock_assignment]
        )

        working_dates = {
            activity_id: (date(2024, 1, 15), date(2024, 1, 19))
        }

        result = await service._is_overallocated_on_dates(
            resource_id,
            date(2024, 1, 15),
            date(2024, 1, 19),
            working_dates,
            {},
        )

        assert result is False


class TestFindNextAvailableSlot:
    """Tests for _find_next_available_slot method."""

    @pytest.mark.asyncio
    async def test_find_slot_no_resource(self) -> None:
        """Should return earliest_start when resource not found."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        mock_activity = MagicMock()
        mock_activity.id = uuid4()

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=None)

        result = await service._find_next_available_slot(
            mock_activity,
            uuid4(),
            date(2024, 1, 15),
            {},
            {},
        )

        assert result == date(2024, 1, 15)

    @pytest.mark.asyncio
    async def test_find_slot_no_assignment(self) -> None:
        """Should return earliest_start when no assignment for activity."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        mock_activity = MagicMock()
        mock_activity.id = uuid4()

        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[])

        result = await service._find_next_available_slot(
            mock_activity,
            uuid4(),
            date(2024, 1, 15),
            {},
            {},
        )

        assert result == date(2024, 1, 15)


class TestRecalculateSuccessors:
    """Tests for _recalculate_successors method."""

    @pytest.mark.asyncio
    async def test_recalculate_fs_dependency(self) -> None:
        """Should recalculate successor dates for FS dependency."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        mock_dependency = MagicMock()
        mock_dependency.successor_id = successor_id
        mock_dependency.lag = 0
        mock_dependency.dependency_type = MagicMock()
        mock_dependency.dependency_type.value = "FS"

        mock_successor = MagicMock()
        mock_successor.id = successor_id

        # First call returns the dependency, subsequent calls return empty (to stop recursion)
        call_count = [0]

        async def get_successors_mock(activity_id):
            call_count[0] += 1
            if call_count[0] == 1:
                return [mock_dependency]
            return []

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = get_successors_mock

        working_dates = {
            predecessor_id: (date(2024, 1, 15), date(2024, 1, 19)),
            successor_id: (date(2024, 1, 18), date(2024, 1, 22)),  # Overlapping
        }
        activity_lookup = {successor_id: mock_successor}

        await service._recalculate_successors(predecessor_id, working_dates, activity_lookup)

        # Successor should be pushed to start after predecessor finishes
        new_start, _ = working_dates[successor_id]
        assert new_start == date(2024, 1, 20)  # Day after predecessor finish + 1

    @pytest.mark.asyncio
    async def test_recalculate_ss_dependency(self) -> None:
        """Should recalculate successor dates for SS dependency."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        mock_dependency = MagicMock()
        mock_dependency.successor_id = successor_id
        mock_dependency.lag = 2
        mock_dependency.dependency_type = MagicMock()
        mock_dependency.dependency_type.value = "SS"

        mock_successor = MagicMock()
        mock_successor.id = successor_id

        # First call returns the dependency, subsequent calls return empty (to stop recursion)
        call_count = [0]

        async def get_successors_mock(activity_id):
            call_count[0] += 1
            if call_count[0] == 1:
                return [mock_dependency]
            return []

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = get_successors_mock

        working_dates = {
            predecessor_id: (date(2024, 1, 15), date(2024, 1, 19)),
            successor_id: (date(2024, 1, 14), date(2024, 1, 18)),  # Before with lag
        }
        activity_lookup = {successor_id: mock_successor}

        await service._recalculate_successors(predecessor_id, working_dates, activity_lookup)

        # Successor should start at predecessor start + lag
        new_start, _ = working_dates[successor_id]
        assert new_start == date(2024, 1, 17)  # 15 + 2 days lag

    @pytest.mark.asyncio
    async def test_recalculate_no_successors(self) -> None:
        """Should do nothing when no successors."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        predecessor_id = uuid4()

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = AsyncMock(return_value=[])

        working_dates = {
            predecessor_id: (date(2024, 1, 15), date(2024, 1, 19)),
        }

        await service._recalculate_successors(predecessor_id, working_dates, {})

        # No changes expected
        assert working_dates[predecessor_id] == (date(2024, 1, 15), date(2024, 1, 19))


class TestApplyLevelingResult:
    """Tests for apply_leveling_result method."""

    @pytest.mark.asyncio
    async def test_apply_no_shifts(self) -> None:
        """Should return True when no shifts to apply."""
        mock_session = AsyncMock()
        service = ResourceLevelingService(mock_session)

        result = LevelingResult(
            program_id=uuid4(),
            success=True,
            iterations_used=0,
            activities_shifted=0,
            shifts=[],
            remaining_overallocations=0,
            new_project_finish=date(2024, 2, 15),
            original_project_finish=date(2024, 2, 15),
            schedule_extension_days=0,
        )

        success = await service.apply_leveling_result(result)

        assert success is True

    @pytest.mark.asyncio
    async def test_apply_with_shifts(self) -> None:
        """Should apply shifts to activities."""
        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()
        service = ResourceLevelingService(mock_session)

        activity_id = uuid4()
        mock_activity = MagicMock()
        mock_activity.id = activity_id

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_id = AsyncMock(return_value=mock_activity)

        shift = ActivityShift(
            activity_id=activity_id,
            activity_code="ACT-001",
            original_start=date(2024, 1, 15),
            original_finish=date(2024, 1, 19),
            new_start=date(2024, 1, 22),
            new_finish=date(2024, 1, 26),
            delay_days=7,
            reason="Resource overallocated",
        )

        result = LevelingResult(
            program_id=uuid4(),
            success=True,
            iterations_used=1,
            activities_shifted=1,
            shifts=[shift],
            remaining_overallocations=0,
            new_project_finish=date(2024, 2, 22),
            original_project_finish=date(2024, 2, 15),
            schedule_extension_days=7,
        )

        success = await service.apply_leveling_result(result)

        assert success is True
        assert mock_activity.planned_start == date(2024, 1, 22)
        assert mock_activity.planned_finish == date(2024, 1, 26)


class TestCountRemainingOverallocations:
    """Tests for _count_remaining_overallocations method."""

    @pytest.mark.asyncio
    async def test_count_no_resources(self) -> None:
        """Should return 0 when no resources."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_program = AsyncMock(return_value=([], 0))

        count = await service._count_remaining_overallocations(
            uuid4(),
            None,
            {},
            {},
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_with_target_resources(self) -> None:
        """Should only count target resources."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        resource1_id = uuid4()
        resource2_id = uuid4()

        resource1 = MagicMock()
        resource1.id = resource1_id
        resource2 = MagicMock()
        resource2.id = resource2_id

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_program = AsyncMock(
            return_value=([resource1, resource2], 2)
        )

        # Only check resource1
        service._is_overallocated_on_dates = AsyncMock(return_value=True)

        working_dates = {
            uuid4(): (date(2024, 1, 15), date(2024, 1, 19))
        }

        count = await service._count_remaining_overallocations(
            uuid4(),
            {resource1_id},  # Only target resource1
            working_dates,
            {},
        )

        # Should only count resource1
        assert count == 1


class TestFindNextAvailableSlotExtended:
    """Tests for _find_next_available_slot method."""

    @pytest.mark.asyncio
    async def test_find_slot_resource_not_found(self) -> None:
        """Should return earliest_start when resource not found."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        activity = MagicMock()
        activity.id = uuid4()

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=None)

        earliest_start = date(2024, 1, 15)
        working_dates = {}
        activity_lookup = {activity.id: activity}

        result = await service._find_next_available_slot(
            activity, uuid4(), earliest_start, working_dates, activity_lookup
        )

        assert result == earliest_start

    @pytest.mark.asyncio
    async def test_find_slot_no_activity_assignment(self) -> None:
        """Should return earliest_start when activity has no assignment."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        activity = MagicMock()
        activity.id = uuid4()

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)

        # Assignment is for different resource
        other_assignment = MagicMock()
        other_assignment.resource_id = uuid4()

        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[other_assignment])

        earliest_start = date(2024, 1, 15)
        working_dates = {}
        activity_lookup = {activity.id: activity}

        result = await service._find_next_available_slot(
            activity, resource_id, earliest_start, working_dates, activity_lookup
        )

        assert result == earliest_start

    @pytest.mark.asyncio
    async def test_find_slot_skips_weekends(self) -> None:
        """Should skip weekend days when finding slot."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        activity_id = uuid4()
        activity = MagicMock()
        activity.id = activity_id

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)

        mock_assignment = MagicMock()
        mock_assignment.resource_id = resource_id
        mock_assignment.units = Decimal("1.0")

        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[mock_assignment])
        service._assignment_repo.get_assignments_with_activities = AsyncMock(return_value=[])

        # Saturday
        earliest_start = date(2024, 1, 13)  # Saturday
        working_dates = {activity_id: (earliest_start, earliest_start)}
        activity_lookup = {activity_id: activity}

        result = await service._find_next_available_slot(
            activity, resource_id, earliest_start, working_dates, activity_lookup
        )

        # Should skip to Monday
        assert result >= date(2024, 1, 15)  # Monday

    @pytest.mark.asyncio
    async def test_find_slot_with_other_assignments(self) -> None:
        """Should find slot when other assignments exist."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        activity_id = uuid4()
        other_activity_id = uuid4()
        activity = MagicMock()
        activity.id = activity_id

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)

        # This activity's assignment
        mock_assignment = MagicMock()
        mock_assignment.resource_id = resource_id
        mock_assignment.activity_id = activity_id
        mock_assignment.units = Decimal("1.0")

        # Other activity's assignment
        other_assignment = MagicMock()
        other_assignment.resource_id = resource_id
        other_assignment.activity_id = other_activity_id
        other_assignment.units = Decimal("0.5")

        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[mock_assignment])
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[mock_assignment, other_assignment]
        )

        earliest_start = date(2024, 1, 15)  # Monday
        working_dates = {
            activity_id: (earliest_start, earliest_start),
            other_activity_id: (earliest_start, date(2024, 1, 19)),
        }
        activity_lookup = {activity_id: activity}

        result = await service._find_next_available_slot(
            activity, resource_id, earliest_start, working_dates, activity_lookup
        )

        # Should find a slot (either same day if no conflict, or later)
        assert result >= earliest_start


class TestRecalculateSuccessorsExtended:
    """Extended tests for _recalculate_successors method."""

    @pytest.mark.asyncio
    async def test_recalculate_ff_dependency(self) -> None:
        """Should recalculate successor with FF dependency correctly."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        working_dates = {
            predecessor_id: (date(2024, 1, 15), date(2024, 1, 25)),  # 10 days
            successor_id: (date(2024, 1, 10), date(2024, 1, 15)),  # 5 days, finishes early
        }
        activity_lookup = {
            predecessor_id: MagicMock(id=predecessor_id),
            successor_id: MagicMock(id=successor_id),
        }

        mock_dep = MagicMock()
        mock_dep.successor_id = successor_id
        mock_dep.lag = 0
        mock_dep.dependency_type = MagicMock()
        mock_dep.dependency_type.value = "FF"  # Finish-to-Finish

        call_count = [0]

        async def get_successors_mock(aid):
            call_count[0] += 1
            if aid == predecessor_id and call_count[0] == 1:
                return [mock_dep]
            return []

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = get_successors_mock

        await service._recalculate_successors(predecessor_id, working_dates, activity_lookup)

        # FF: successor should finish when predecessor finishes
        # Predecessor finishes Jan 25, successor has 5 day duration
        _, new_finish = working_dates[successor_id]
        assert new_finish == date(2024, 1, 25)

    @pytest.mark.asyncio
    async def test_recalculate_sf_dependency(self) -> None:
        """Should recalculate successor with SF dependency correctly."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        working_dates = {
            predecessor_id: (date(2024, 1, 20), date(2024, 1, 25)),
            successor_id: (date(2024, 1, 10), date(2024, 1, 15)),  # 5 days, finishes before pred starts
        }
        activity_lookup = {
            predecessor_id: MagicMock(id=predecessor_id),
            successor_id: MagicMock(id=successor_id),
        }

        mock_dep = MagicMock()
        mock_dep.successor_id = successor_id
        mock_dep.lag = 0
        mock_dep.dependency_type = MagicMock()
        mock_dep.dependency_type.value = "SF"  # Start-to-Finish

        call_count = [0]

        async def get_successors_mock(aid):
            call_count[0] += 1
            if aid == predecessor_id and call_count[0] == 1:
                return [mock_dep]
            return []

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = get_successors_mock

        await service._recalculate_successors(predecessor_id, working_dates, activity_lookup)

        # SF: successor finish at predecessor start (Jan 20)
        _, new_finish = working_dates[successor_id]
        assert new_finish == date(2024, 1, 20)

    @pytest.mark.asyncio
    async def test_recalculate_unknown_dependency_type(self) -> None:
        """Should handle unknown dependency type as FS."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        working_dates = {
            predecessor_id: (date(2024, 1, 15), date(2024, 1, 19)),
            successor_id: (date(2024, 1, 16), date(2024, 1, 20)),  # Overlaps
        }
        activity_lookup = {
            predecessor_id: MagicMock(id=predecessor_id),
            successor_id: MagicMock(id=successor_id),
        }

        mock_dep = MagicMock()
        mock_dep.successor_id = successor_id
        mock_dep.lag = 0
        mock_dep.dependency_type = MagicMock()
        mock_dep.dependency_type.value = "UNKNOWN"

        call_count = [0]

        async def get_successors_mock(aid):
            call_count[0] += 1
            if aid == predecessor_id and call_count[0] == 1:
                return [mock_dep]
            return []

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = get_successors_mock

        await service._recalculate_successors(predecessor_id, working_dates, activity_lookup)

        # Unknown should default to FS behavior
        new_start, _ = working_dates[successor_id]
        assert new_start == date(2024, 1, 20)  # Day after predecessor finishes

    @pytest.mark.asyncio
    async def test_recalculate_with_lag(self) -> None:
        """Should include lag in calculation."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        working_dates = {
            predecessor_id: (date(2024, 1, 15), date(2024, 1, 19)),
            successor_id: (date(2024, 1, 16), date(2024, 1, 20)),  # Overlaps
        }
        activity_lookup = {
            predecessor_id: MagicMock(id=predecessor_id),
            successor_id: MagicMock(id=successor_id),
        }

        mock_dep = MagicMock()
        mock_dep.successor_id = successor_id
        mock_dep.lag = 5  # 5 day lag
        mock_dep.dependency_type = MagicMock()
        mock_dep.dependency_type.value = "FS"

        call_count = [0]

        async def get_successors_mock(aid):
            call_count[0] += 1
            if aid == predecessor_id and call_count[0] == 1:
                return [mock_dep]
            return []

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = get_successors_mock

        await service._recalculate_successors(predecessor_id, working_dates, activity_lookup)

        # FS with 5 day lag: successor starts 6 days after predecessor finish (1 + 5)
        new_start, _ = working_dates[successor_id]
        assert new_start == date(2024, 1, 25)  # Jan 19 + 1 + 5 = Jan 25


class TestLevelProgramEdgeCases:
    """Edge case tests for level_program method."""

    @pytest.mark.asyncio
    async def test_level_program_not_found(self) -> None:
        """Should handle program not found."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=None)

        result = await service.level_program(uuid4())

        assert result.success is False
        assert "Program not found" in result.warnings

    @pytest.mark.asyncio
    async def test_level_program_no_activities(self) -> None:
        """Should handle program with no activities."""
        mock_session = MagicMock()
        service = ResourceLevelingService(mock_session)

        mock_program = MagicMock()
        mock_program.start_date = date(2024, 1, 1)
        mock_program.end_date = date(2024, 12, 31)

        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[])

        result = await service.level_program(uuid4())

        assert result.success is True
        assert result.activities_shifted == 0


class TestApplyLevelingResultEdgeCases:
    """Edge case tests for apply_leveling_result method."""

    @pytest.mark.asyncio
    async def test_apply_result_activity_not_found(self) -> None:
        """Should handle activity not found gracefully."""
        mock_session = MagicMock()
        mock_session.flush = AsyncMock()
        service = ResourceLevelingService(mock_session)

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_id = AsyncMock(return_value=None)

        shift = ActivityShift(
            activity_id=uuid4(),
            activity_code="ACT-001",
            original_start=date(2024, 1, 15),
            original_finish=date(2024, 1, 19),
            new_start=date(2024, 1, 22),
            new_finish=date(2024, 1, 26),
            delay_days=7,
            reason="Resource overallocated",
        )

        result = LevelingResult(
            program_id=uuid4(),
            success=True,
            iterations_used=1,
            activities_shifted=1,
            shifts=[shift],
            remaining_overallocations=0,
            new_project_finish=date(2024, 2, 22),
            original_project_finish=date(2024, 2, 15),
            schedule_extension_days=7,
        )

        success = await service.apply_leveling_result(result)

        # Should not fail even if activity not found
        assert success is True

    @pytest.mark.asyncio
    async def test_apply_result_multiple_shifts_same_activity(self) -> None:
        """Should use latest shift for same activity."""
        mock_session = MagicMock()
        mock_session.flush = AsyncMock()
        service = ResourceLevelingService(mock_session)

        activity_id = uuid4()
        mock_activity = MagicMock()
        mock_activity.id = activity_id

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_id = AsyncMock(return_value=mock_activity)

        shift1 = ActivityShift(
            activity_id=activity_id,
            activity_code="ACT-001",
            original_start=date(2024, 1, 15),
            original_finish=date(2024, 1, 19),
            new_start=date(2024, 1, 18),
            new_finish=date(2024, 1, 22),
            delay_days=3,
            reason="First shift",
        )

        shift2 = ActivityShift(
            activity_id=activity_id,
            activity_code="ACT-001",
            original_start=date(2024, 1, 18),
            original_finish=date(2024, 1, 22),
            new_start=date(2024, 1, 25),
            new_finish=date(2024, 1, 29),
            delay_days=7,
            reason="Second shift",
        )

        result = LevelingResult(
            program_id=uuid4(),
            success=True,
            iterations_used=2,
            activities_shifted=1,
            shifts=[shift1, shift2],  # Two shifts for same activity
            remaining_overallocations=0,
            new_project_finish=date(2024, 2, 28),
            original_project_finish=date(2024, 2, 15),
            schedule_extension_days=13,
        )

        success = await service.apply_leveling_result(result)

        assert success is True
        # Should use latest shift dates
        assert mock_activity.planned_start == date(2024, 1, 25)
        assert mock_activity.planned_finish == date(2024, 1, 29)
