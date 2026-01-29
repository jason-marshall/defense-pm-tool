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
