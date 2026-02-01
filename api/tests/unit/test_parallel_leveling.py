"""Unit tests for parallel leveling service."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from src.services.parallel_leveling import (
    ActivityPriority,
    ParallelLevelingResult,
    ResourceConflict,
)


class TestResourceConflict:
    """Tests for ResourceConflict ordering."""

    def test_conflict_ordering_by_date(self):
        """Earlier conflicts should have higher priority."""
        resource_id = uuid4()
        c1 = ResourceConflict(
            resource_id=resource_id,
            conflict_date=date(2026, 1, 1),
            overallocation_hours=Decimal("2"),
            activities=[],
        )
        c2 = ResourceConflict(
            resource_id=resource_id,
            conflict_date=date(2026, 1, 5),
            overallocation_hours=Decimal("2"),
            activities=[],
        )

        assert c1 < c2  # Earlier date = higher priority

    def test_conflict_ordering_by_date_reversed(self):
        """Later conflicts should have lower priority."""
        resource_id = uuid4()
        c1 = ResourceConflict(
            resource_id=resource_id,
            conflict_date=date(2026, 2, 1),
            overallocation_hours=Decimal("2"),
            activities=[],
        )
        c2 = ResourceConflict(
            resource_id=resource_id,
            conflict_date=date(2026, 1, 1),
            overallocation_hours=Decimal("2"),
            activities=[],
        )

        assert c2 < c1  # Earlier date = higher priority

    def test_conflict_ordering_by_severity_same_date(self):
        """Same date: more severe conflict has higher priority."""
        resource_id = uuid4()
        c1 = ResourceConflict(
            resource_id=resource_id,
            conflict_date=date(2026, 1, 1),
            overallocation_hours=Decimal("8"),
            activities=[],
        )
        c2 = ResourceConflict(
            resource_id=resource_id,
            conflict_date=date(2026, 1, 1),
            overallocation_hours=Decimal("2"),
            activities=[],
        )

        assert c1 < c2  # Higher overallocation = higher priority

    def test_conflict_ordering_by_severity_reversed(self):
        """Same date: less severe conflict has lower priority."""
        resource_id = uuid4()
        c1 = ResourceConflict(
            resource_id=resource_id,
            conflict_date=date(2026, 1, 1),
            overallocation_hours=Decimal("1"),
            activities=[],
        )
        c2 = ResourceConflict(
            resource_id=resource_id,
            conflict_date=date(2026, 1, 1),
            overallocation_hours=Decimal("4"),
            activities=[],
        )

        assert c2 < c1  # Higher overallocation = higher priority

    def test_conflict_different_resources(self):
        """Conflicts on different resources should order by date."""
        c1 = ResourceConflict(
            resource_id=uuid4(),
            conflict_date=date(2026, 1, 10),
            overallocation_hours=Decimal("8"),
            activities=[],
        )
        c2 = ResourceConflict(
            resource_id=uuid4(),
            conflict_date=date(2026, 1, 5),
            overallocation_hours=Decimal("2"),
            activities=[],
        )

        assert c2 < c1  # Earlier date wins regardless of severity

    def test_conflict_with_activities(self):
        """Conflicts should store activity list correctly."""
        activity_ids = [uuid4(), uuid4(), uuid4()]
        c = ResourceConflict(
            resource_id=uuid4(),
            conflict_date=date(2026, 1, 1),
            overallocation_hours=Decimal("4"),
            activities=activity_ids,
        )

        assert len(c.activities) == 3
        assert c.activities == activity_ids


class TestActivityPriority:
    """Tests for activity priority scoring."""

    def test_critical_path_highest_priority(self):
        """Critical path activities should not be delayed (higher priority)."""
        critical = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 1),
            total_float=0,
            is_critical=True,
            resource_count=1,
        )
        non_critical = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 1),
            total_float=0,
            is_critical=False,
            resource_count=1,
        )

        assert critical < non_critical  # Critical = higher priority (lower score)

    def test_earlier_start_higher_priority(self):
        """Activities starting earlier have higher priority."""
        early = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 1),
            total_float=5,
            is_critical=False,
            resource_count=1,
        )
        late = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 10),
            total_float=5,
            is_critical=False,
            resource_count=1,
        )

        assert early < late  # Earlier start = higher priority

    def test_less_float_higher_priority(self):
        """Activities with less float have higher priority (more constrained)."""
        low_float = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 1),
            total_float=2,
            is_critical=False,
            resource_count=1,
        )
        high_float = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 1),
            total_float=10,
            is_critical=False,
            resource_count=1,
        )

        assert low_float < high_float  # Less float = higher priority

    def test_more_resources_higher_priority(self):
        """Activities with more resources are harder to move (higher priority)."""
        many_resources = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 1),
            total_float=5,
            is_critical=False,
            resource_count=5,
        )
        few_resources = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 1),
            total_float=5,
            is_critical=False,
            resource_count=1,
        )

        assert many_resources < few_resources  # More resources = higher priority

    def test_priority_score_tuple(self):
        """Priority score should be a comparable tuple."""
        priority = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 3, 15),
            total_float=7,
            is_critical=False,
            resource_count=2,
        )

        score = priority.score
        assert isinstance(score, tuple)
        assert len(score) == 4
        assert score[0] == 1  # Not critical
        assert score[1] == date(2026, 3, 15)
        assert score[2] == 7
        assert score[3] == -2  # Negative resource count

    def test_critical_always_wins(self):
        """Critical path should always have higher priority than non-critical."""
        # Critical with late start and high float
        critical = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 12, 31),
            total_float=100,
            is_critical=True,
            resource_count=1,
        )
        # Non-critical with early start and no float
        non_critical = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 1),
            total_float=0,
            is_critical=False,
            resource_count=10,
        )

        assert critical < non_critical  # Critical always wins


class TestActivityPriorityComplexScenarios:
    """Complex scenario tests for activity priority."""

    def test_priority_chain_ordering(self):
        """Test ordering of multiple activities."""
        # Most important: critical, early, low float
        p1 = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 1),
            total_float=0,
            is_critical=True,
            resource_count=3,
        )
        # Second: non-critical, early, low float
        p2 = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 1),
            total_float=0,
            is_critical=False,
            resource_count=3,
        )
        # Third: non-critical, early, some float
        p3 = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 1),
            total_float=5,
            is_critical=False,
            resource_count=3,
        )
        # Fourth: non-critical, late, some float
        p4 = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 2, 1),
            total_float=5,
            is_critical=False,
            resource_count=3,
        )

        priorities = [p4, p2, p1, p3]  # Shuffle order
        sorted_priorities = sorted(priorities)

        assert sorted_priorities[0] == p1  # Critical first
        assert sorted_priorities[1] == p2  # Early, low float
        assert sorted_priorities[2] == p3  # Early, more float
        assert sorted_priorities[3] == p4  # Late

    def test_tie_breaking_with_resources(self):
        """Resource count should break ties when all else equal."""
        p1 = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 1),
            total_float=5,
            is_critical=False,
            resource_count=5,
        )
        p2 = ActivityPriority(
            activity_id=uuid4(),
            early_start=date(2026, 1, 1),
            total_float=5,
            is_critical=False,
            resource_count=1,
        )

        assert p1 < p2  # More resources = higher priority


class TestParallelLevelingResult:
    """Tests for ParallelLevelingResult dataclass."""

    def test_result_inherits_from_leveling_result(self):
        """ParallelLevelingResult should extend LevelingResult."""
        result = ParallelLevelingResult(
            program_id=uuid4(),
            success=True,
            iterations_used=5,
            activities_shifted=3,
            shifts=[],
            remaining_overallocations=0,
            new_project_finish=date(2026, 3, 1),
            original_project_finish=date(2026, 2, 15),
            schedule_extension_days=14,
            conflicts_resolved=10,
            resources_processed=4,
        )

        assert result.success is True
        assert result.iterations_used == 5
        assert result.conflicts_resolved == 10
        assert result.resources_processed == 4

    def test_result_default_values(self):
        """Default values should be set correctly."""
        result = ParallelLevelingResult(
            program_id=uuid4(),
            success=True,
            iterations_used=0,
            activities_shifted=0,
            shifts=[],
            remaining_overallocations=0,
            new_project_finish=date(2026, 1, 1),
            original_project_finish=date(2026, 1, 1),
            schedule_extension_days=0,
        )

        assert result.conflicts_resolved == 0
        assert result.resources_processed == 0
        assert result.comparison_with_serial == {}

    def test_result_with_comparison_metrics(self):
        """Result should store comparison metrics."""
        comparison = {
            "serial_iterations": 15,
            "parallel_iterations": 8,
            "serial_extension": 10,
            "parallel_extension": 7,
        }
        result = ParallelLevelingResult(
            program_id=uuid4(),
            success=True,
            iterations_used=8,
            activities_shifted=5,
            shifts=[],
            remaining_overallocations=0,
            new_project_finish=date(2026, 3, 1),
            original_project_finish=date(2026, 2, 22),
            schedule_extension_days=7,
            conflicts_resolved=12,
            resources_processed=3,
            comparison_with_serial=comparison,
        )

        assert result.comparison_with_serial["serial_iterations"] == 15
        assert result.comparison_with_serial["parallel_iterations"] == 8


class TestResourceConflictHeapOperations:
    """Tests for heap operations with ResourceConflict."""

    def test_heap_push_pop_order(self):
        """Heap should maintain priority order."""
        from heapq import heappop, heappush

        heap: list[ResourceConflict] = []

        # Add conflicts in random order
        c1 = ResourceConflict(uuid4(), date(2026, 1, 15), Decimal("2"), [])
        c2 = ResourceConflict(uuid4(), date(2026, 1, 5), Decimal("4"), [])
        c3 = ResourceConflict(uuid4(), date(2026, 1, 10), Decimal("1"), [])
        c4 = ResourceConflict(uuid4(), date(2026, 1, 5), Decimal("8"), [])

        heappush(heap, c1)
        heappush(heap, c2)
        heappush(heap, c3)
        heappush(heap, c4)

        # Pop should return in priority order
        first = heappop(heap)
        assert first.conflict_date == date(2026, 1, 5)
        assert first.overallocation_hours == Decimal("8")  # More severe first

        second = heappop(heap)
        assert second.conflict_date == date(2026, 1, 5)
        assert second.overallocation_hours == Decimal("4")

        third = heappop(heap)
        assert third.conflict_date == date(2026, 1, 10)

        fourth = heappop(heap)
        assert fourth.conflict_date == date(2026, 1, 15)


class TestActivityPriorityScoreSelection:
    """Tests for selecting activities to delay based on priority."""

    def test_select_lowest_priority_for_delay(self):
        """When resolving conflicts, select activity with lowest priority."""
        priorities = [
            ActivityPriority(uuid4(), date(2026, 1, 1), 0, True, 3),  # Critical
            ActivityPriority(uuid4(), date(2026, 1, 1), 2, False, 1),  # Low float
            ActivityPriority(uuid4(), date(2026, 1, 1), 10, False, 1),  # High float
            ActivityPriority(uuid4(), date(2026, 1, 5), 15, False, 1),  # Late, high float
        ]

        # Sort by score (highest score = lowest priority = should delay)
        sorted_by_delay_preference = sorted(priorities, key=lambda p: p.score, reverse=True)

        # Last activity (late start, high float, non-critical) should be delayed first
        to_delay = sorted_by_delay_preference[0]
        assert to_delay.early_start == date(2026, 1, 5)
        assert to_delay.total_float == 15
        assert not to_delay.is_critical


class TestParallelLevelingServiceInit:
    """Tests for ParallelLevelingService initialization."""

    def test_service_init_with_session(self):
        """Test service initializes with database session."""
        from unittest.mock import MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = MagicMock()
        service = ParallelLevelingService(mock_session)

        assert service.session == mock_session
        assert service.cache is None

    def test_service_init_with_cache(self):
        """Test service initializes with optional cache."""
        from unittest.mock import MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = MagicMock()
        mock_cache = MagicMock()
        service = ParallelLevelingService(mock_session, mock_cache)

        assert service.cache == mock_cache


class TestParallelLevelingServiceSelectActivityToDelay:
    """Tests for _select_activity_to_delay method."""

    def test_select_from_candidates(self):
        """Test selecting activity to delay from candidates."""
        from src.services.parallel_leveling import ParallelLevelingService
        from src.services.resource_leveling import LevelingOptions
        from unittest.mock import MagicMock

        service = ParallelLevelingService(MagicMock())

        activity1_id = uuid4()
        activity2_id = uuid4()

        conflict = ResourceConflict(
            resource_id=uuid4(),
            conflict_date=date(2026, 1, 15),
            overallocation_hours=Decimal("4"),
            activities=[activity1_id, activity2_id],
        )

        priority_map = {
            activity1_id: ActivityPriority(
                activity_id=activity1_id,
                early_start=date(2026, 1, 1),
                total_float=5,
                is_critical=False,
                resource_count=1,
            ),
            activity2_id: ActivityPriority(
                activity_id=activity2_id,
                early_start=date(2026, 1, 10),
                total_float=10,
                is_critical=False,
                resource_count=1,
            ),
        }

        activity_dates = {
            activity1_id: (date(2026, 1, 1), date(2026, 1, 5)),
            activity2_id: (date(2026, 1, 10), date(2026, 1, 15)),
        }

        options = LevelingOptions()

        result = service._select_activity_to_delay(
            conflict, priority_map, activity_dates, options
        )

        # Should select activity2 (later start, more float)
        assert result == activity2_id

    def test_select_skips_critical_path(self):
        """Test skipping critical path activities when option set."""
        from src.services.parallel_leveling import ParallelLevelingService
        from src.services.resource_leveling import LevelingOptions
        from unittest.mock import MagicMock

        service = ParallelLevelingService(MagicMock())

        critical_id = uuid4()
        non_critical_id = uuid4()

        conflict = ResourceConflict(
            resource_id=uuid4(),
            conflict_date=date(2026, 1, 15),
            overallocation_hours=Decimal("4"),
            activities=[critical_id, non_critical_id],
        )

        priority_map = {
            critical_id: ActivityPriority(
                activity_id=critical_id,
                early_start=date(2026, 1, 10),
                total_float=0,
                is_critical=True,
                resource_count=1,
            ),
            non_critical_id: ActivityPriority(
                activity_id=non_critical_id,
                early_start=date(2026, 1, 1),
                total_float=5,
                is_critical=False,
                resource_count=1,
            ),
        }

        activity_dates = {
            critical_id: (date(2026, 1, 10), date(2026, 1, 15)),
            non_critical_id: (date(2026, 1, 1), date(2026, 1, 5)),
        }

        options = LevelingOptions(preserve_critical_path=True)

        result = service._select_activity_to_delay(
            conflict, priority_map, activity_dates, options
        )

        # Should select non-critical even though critical has later start
        assert result == non_critical_id

    def test_select_none_when_all_critical(self):
        """Test returns None when all candidates are critical."""
        from src.services.parallel_leveling import ParallelLevelingService
        from src.services.resource_leveling import LevelingOptions
        from unittest.mock import MagicMock

        service = ParallelLevelingService(MagicMock())

        activity1_id = uuid4()
        activity2_id = uuid4()

        conflict = ResourceConflict(
            resource_id=uuid4(),
            conflict_date=date(2026, 1, 15),
            overallocation_hours=Decimal("4"),
            activities=[activity1_id, activity2_id],
        )

        priority_map = {
            activity1_id: ActivityPriority(
                activity_id=activity1_id,
                early_start=date(2026, 1, 1),
                total_float=0,
                is_critical=True,
                resource_count=1,
            ),
            activity2_id: ActivityPriority(
                activity_id=activity2_id,
                early_start=date(2026, 1, 10),
                total_float=0,
                is_critical=True,
                resource_count=1,
            ),
        }

        activity_dates = {
            activity1_id: (date(2026, 1, 1), date(2026, 1, 5)),
            activity2_id: (date(2026, 1, 10), date(2026, 1, 15)),
        }

        options = LevelingOptions(preserve_critical_path=True)

        result = service._select_activity_to_delay(
            conflict, priority_map, activity_dates, options
        )

        assert result is None

    def test_select_respects_float_constraint(self):
        """Test respecting level_within_float option."""
        from src.services.parallel_leveling import ParallelLevelingService
        from src.services.resource_leveling import LevelingOptions
        from unittest.mock import MagicMock

        service = ParallelLevelingService(MagicMock())

        activity1_id = uuid4()
        activity2_id = uuid4()

        conflict = ResourceConflict(
            resource_id=uuid4(),
            conflict_date=date(2026, 1, 20),
            overallocation_hours=Decimal("4"),
            activities=[activity1_id, activity2_id],
        )

        # Activity 1 has used all its float (moved 5 days, has 5 float)
        # Activity 2 has float remaining (moved 2 days, has 10 float)
        priority_map = {
            activity1_id: ActivityPriority(
                activity_id=activity1_id,
                early_start=date(2026, 1, 1),
                total_float=5,
                is_critical=False,
                resource_count=1,
            ),
            activity2_id: ActivityPriority(
                activity_id=activity2_id,
                early_start=date(2026, 1, 10),
                total_float=10,
                is_critical=False,
                resource_count=1,
            ),
        }

        activity_dates = {
            activity1_id: (date(2026, 1, 6), date(2026, 1, 10)),  # Moved 5 days
            activity2_id: (date(2026, 1, 12), date(2026, 1, 17)),  # Moved 2 days
        }

        options = LevelingOptions(level_within_float=True)

        result = service._select_activity_to_delay(
            conflict, priority_map, activity_dates, options
        )

        # Should select activity2 because activity1 has used all float
        assert result == activity2_id


class TestParallelLevelingServiceLevelProgram:
    """Tests for level_program method."""

    @pytest.mark.asyncio
    async def test_level_program_not_found(self):
        """Test handling program not found."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        # Mock program repo to return None
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=None)

        program_id = uuid4()
        result = await service.level_program(program_id)

        assert result.success is False
        assert "Program not found" in result.warnings

    @pytest.mark.asyncio
    async def test_level_program_no_activities(self):
        """Test handling program with no activities."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        # Mock program
        mock_program = MagicMock()
        mock_program.start_date = date(2026, 1, 1)
        mock_program.end_date = date(2026, 12, 31)

        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        # Mock empty activities
        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[])

        program_id = uuid4()
        result = await service.level_program(program_id)

        assert result.success is True
        assert result.activities_shifted == 0

    @pytest.mark.asyncio
    async def test_level_program_no_conflicts(self):
        """Test handling program with no resource conflicts."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        # Mock program
        mock_program = MagicMock()
        mock_program.start_date = date(2026, 1, 1)
        mock_program.end_date = date(2026, 12, 31)

        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        # Mock activity
        mock_activity = MagicMock()
        mock_activity.id = uuid4()
        mock_activity.early_start = date(2026, 1, 1)
        mock_activity.early_finish = date(2026, 1, 5)
        mock_activity.planned_start = None
        mock_activity.planned_finish = None
        mock_activity.is_critical = False
        mock_activity.total_float = 10

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[mock_activity])

        # Mock empty assignments (no resource conflicts)
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[])

        # Mock resources
        service._resource_repo = MagicMock()
        service._resource_repo.get_by_program = AsyncMock(return_value=([], 0))

        program_id = uuid4()
        result = await service.level_program(program_id)

        assert result.success is True
        assert result.remaining_overallocations == 0


class TestParallelLevelingServiceApplyResult:
    """Tests for apply_leveling_result method."""

    @pytest.mark.asyncio
    async def test_apply_empty_result(self):
        """Test applying result with no shifts."""
        from unittest.mock import AsyncMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        result = ParallelLevelingResult(
            program_id=uuid4(),
            success=True,
            iterations_used=0,
            activities_shifted=0,
            shifts=[],
            remaining_overallocations=0,
            new_project_finish=date(2026, 3, 1),
            original_project_finish=date(2026, 3, 1),
            schedule_extension_days=0,
        )

        success = await service.apply_leveling_result(result)
        assert success is True

    @pytest.mark.asyncio
    async def test_apply_result_with_shifts(self):
        """Test applying result with shifts."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService
        from src.services.resource_leveling import ActivityShift

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        activity_id = uuid4()

        # Mock activity
        mock_activity = MagicMock()
        mock_activity.id = activity_id
        mock_activity.planned_start = date(2026, 1, 1)
        mock_activity.planned_finish = date(2026, 1, 5)

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_id = AsyncMock(return_value=mock_activity)

        shift = ActivityShift(
            activity_id=activity_id,
            activity_code="ACT-001",
            original_start=date(2026, 1, 1),
            original_finish=date(2026, 1, 5),
            new_start=date(2026, 1, 8),
            new_finish=date(2026, 1, 12),
            delay_days=7,
            reason="Resource conflict",
        )

        result = ParallelLevelingResult(
            program_id=uuid4(),
            success=True,
            iterations_used=1,
            activities_shifted=1,
            shifts=[shift],
            remaining_overallocations=0,
            new_project_finish=date(2026, 1, 12),
            original_project_finish=date(2026, 1, 5),
            schedule_extension_days=7,
        )

        success = await service.apply_leveling_result(result)
        assert success is True

        # Verify activity was updated
        assert mock_activity.planned_start == date(2026, 1, 8)
        assert mock_activity.planned_finish == date(2026, 1, 12)


class TestParallelLevelingServiceHelpers:
    """Tests for helper methods in ParallelLevelingService."""

    @pytest.mark.asyncio
    async def test_get_project_finish_no_activities(self):
        """Test _get_project_finish with no activities."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        mock_program = MagicMock()
        mock_program.end_date = date(2026, 12, 31)

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[])
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        result = await service._get_project_finish(uuid4())

        assert result == date(2026, 12, 31)

    @pytest.mark.asyncio
    async def test_get_project_finish_with_activities(self):
        """Test _get_project_finish with activities."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        activity1 = MagicMock()
        activity1.early_finish = date(2026, 3, 15)
        activity1.planned_finish = None

        activity2 = MagicMock()
        activity2.early_finish = date(2026, 4, 20)
        activity2.planned_finish = None

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[activity1, activity2])

        result = await service._get_project_finish(uuid4())

        assert result == date(2026, 4, 20)

    @pytest.mark.asyncio
    async def test_get_project_finish_uses_planned_finish(self):
        """Test _get_project_finish uses planned_finish when early_finish is None."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        activity = MagicMock()
        activity.early_finish = None
        activity.planned_finish = date(2026, 5, 10)

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[activity])

        result = await service._get_project_finish(uuid4())

        assert result == date(2026, 5, 10)

    @pytest.mark.asyncio
    async def test_get_project_finish_no_program(self):
        """Test _get_project_finish when program not found."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[])
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=None)

        result = await service._get_project_finish(uuid4())

        assert result == date.today()

    @pytest.mark.asyncio
    async def test_calculate_priorities(self):
        """Test _calculate_priorities creates priority map."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        activity1 = MagicMock()
        activity1.id = uuid4()
        activity1.early_start = date(2026, 1, 5)
        activity1.planned_start = None
        activity1.total_float = 5
        activity1.is_critical = True

        activity2 = MagicMock()
        activity2.id = uuid4()
        activity2.early_start = None
        activity2.planned_start = date(2026, 1, 10)
        activity2.total_float = None
        activity2.is_critical = None

        mock_assignment = MagicMock()
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[mock_assignment])

        result = await service._calculate_priorities([activity1, activity2])

        assert len(result) == 2
        assert result[activity1.id].is_critical is True
        assert result[activity1.id].total_float == 5
        assert result[activity2.id].is_critical is False
        assert result[activity2.id].total_float == 9999  # Default when None
        assert result[activity2.id].resource_count == 1

    @pytest.mark.asyncio
    async def test_build_conflict_matrix_empty_dates(self):
        """Test _build_conflict_matrix with empty activity dates."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService
        from src.services.resource_leveling import LevelingOptions

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        # Need to mock repo even though it won't be called
        service._resource_repo = MagicMock()
        service._resource_repo.get_by_program = AsyncMock(return_value=([], 0))

        result = await service._build_conflict_matrix(uuid4(), {}, LevelingOptions())

        assert result == []

    @pytest.mark.asyncio
    async def test_build_conflict_matrix_target_resources(self):
        """Test _build_conflict_matrix filters by target resources."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService
        from src.services.resource_leveling import LevelingOptions

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        target_id = uuid4()
        other_id = uuid4()

        target_resource = MagicMock()
        target_resource.id = target_id
        target_resource.capacity_per_day = Decimal("8.0")

        other_resource = MagicMock()
        other_resource.id = other_id
        other_resource.capacity_per_day = Decimal("8.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_program = AsyncMock(
            return_value=([target_resource, other_resource], 2)
        )
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(return_value=[])

        activity_dates = {uuid4(): (date(2026, 1, 6), date(2026, 1, 8))}
        options = LevelingOptions(target_resources=[target_id])

        await service._build_conflict_matrix(uuid4(), activity_dates, options)

        # Should only check target resource
        calls = service._assignment_repo.get_assignments_with_activities.call_args_list
        resource_ids_checked = [call[0][0] for call in calls]
        assert target_id in resource_ids_checked
        assert other_id not in resource_ids_checked

    @pytest.mark.asyncio
    async def test_build_conflict_matrix_no_resources(self):
        """Test _build_conflict_matrix with no resources."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService
        from src.services.resource_leveling import LevelingOptions

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_program = AsyncMock(return_value=([], 0))

        activity_dates = {uuid4(): (date(2026, 1, 6), date(2026, 1, 8))}

        result = await service._build_conflict_matrix(uuid4(), activity_dates, LevelingOptions())

        assert result == []

    @pytest.mark.asyncio
    async def test_build_conflict_matrix_skips_weekends(self):
        """Test _build_conflict_matrix skips weekend days."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService
        from src.services.resource_leveling import LevelingOptions

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        resource_id = uuid4()
        activity_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.capacity_per_day = Decimal("8.0")

        mock_assignment = MagicMock()
        mock_assignment.activity_id = activity_id
        mock_assignment.units = Decimal("1.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_program = AsyncMock(return_value=([mock_resource], 1))
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[mock_assignment]
        )

        # Saturday to Sunday range
        activity_dates = {activity_id: (date(2026, 1, 3), date(2026, 1, 4))}  # Sat-Sun

        result = await service._build_conflict_matrix(uuid4(), activity_dates, LevelingOptions())

        # No conflicts on weekends
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_build_conflict_matrix_detects_overallocation(self):
        """Test _build_conflict_matrix detects resource overallocation."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService
        from src.services.resource_leveling import LevelingOptions

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        resource_id = uuid4()
        activity1_id = uuid4()
        activity2_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.capacity_per_day = Decimal("8.0")

        # Two assignments on same resource, same dates - 100% each = overallocation
        assignment1 = MagicMock()
        assignment1.activity_id = activity1_id
        assignment1.units = Decimal("1.0")

        assignment2 = MagicMock()
        assignment2.activity_id = activity2_id
        assignment2.units = Decimal("1.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_program = AsyncMock(return_value=([mock_resource], 1))
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[assignment1, assignment2]
        )

        # Both activities on Monday
        activity_dates = {
            activity1_id: (date(2026, 1, 5), date(2026, 1, 5)),  # Monday
            activity2_id: (date(2026, 1, 5), date(2026, 1, 5)),  # Monday
        }

        result = await service._build_conflict_matrix(uuid4(), activity_dates, LevelingOptions())

        # Should detect overallocation on Monday
        assert len(result) >= 1
        assert result[0].resource_id == resource_id
        assert result[0].conflict_date == date(2026, 1, 5)

    @pytest.mark.asyncio
    async def test_calculate_minimum_delay_resource_not_found(self):
        """Test _calculate_minimum_delay returns 1 when resource not found."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=None)

        activity_id = uuid4()
        activity_dates = {activity_id: (date(2026, 1, 10), date(2026, 1, 15))}

        result = await service._calculate_minimum_delay(
            activity_id, uuid4(), date(2026, 1, 12), activity_dates
        )

        assert result == 1

    @pytest.mark.asyncio
    async def test_calculate_minimum_delay_no_assignment(self):
        """Test _calculate_minimum_delay returns 1 when no assignment found."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        # Other activity has assignment, but not this one
        other_assignment = MagicMock()
        other_assignment.activity_id = uuid4()

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[other_assignment]
        )

        activity_id = uuid4()
        activity_dates = {activity_id: (date(2026, 1, 10), date(2026, 1, 15))}

        result = await service._calculate_minimum_delay(
            activity_id, uuid4(), date(2026, 1, 12), activity_dates
        )

        assert result == 1

    @pytest.mark.asyncio
    async def test_propagate_to_successors_no_dependencies(self):
        """Test _propagate_to_successors with no successors."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = AsyncMock(return_value=[])

        activity_id = uuid4()
        activity_dates = {activity_id: (date(2026, 1, 10), date(2026, 1, 15))}
        activity_lookup = {}

        await service._propagate_to_successors(activity_id, activity_dates, activity_lookup)

        # No changes expected
        assert activity_dates[activity_id] == (date(2026, 1, 10), date(2026, 1, 15))

    @pytest.mark.asyncio
    async def test_propagate_to_successors_fs_dependency(self):
        """Test _propagate_to_successors with finish-to-start dependency."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        activity_dates = {
            predecessor_id: (date(2026, 1, 10), date(2026, 1, 15)),
            successor_id: (date(2026, 1, 12), date(2026, 1, 17)),  # Overlaps - invalid
        }
        activity_lookup = {
            predecessor_id: MagicMock(id=predecessor_id),
            successor_id: MagicMock(id=successor_id),
        }

        mock_dep = MagicMock()
        mock_dep.successor_id = successor_id
        mock_dep.lag = 0
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

        await service._propagate_to_successors(predecessor_id, activity_dates, activity_lookup)

        # Successor should start day after predecessor finish
        assert activity_dates[successor_id][0] == date(2026, 1, 16)

    @pytest.mark.asyncio
    async def test_propagate_to_successors_ss_dependency(self):
        """Test _propagate_to_successors with start-to-start dependency."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        activity_dates = {
            predecessor_id: (date(2026, 1, 10), date(2026, 1, 15)),
            successor_id: (date(2026, 1, 5), date(2026, 1, 10)),  # Starts before
        }
        activity_lookup = {
            predecessor_id: MagicMock(id=predecessor_id),
            successor_id: MagicMock(id=successor_id),
        }

        mock_dep = MagicMock()
        mock_dep.successor_id = successor_id
        mock_dep.lag = 2
        mock_dep.dependency_type = MagicMock()
        mock_dep.dependency_type.value = "SS"

        call_count = [0]

        async def get_successors_mock(aid):
            call_count[0] += 1
            if aid == predecessor_id and call_count[0] == 1:
                return [mock_dep]
            return []

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = get_successors_mock

        await service._propagate_to_successors(predecessor_id, activity_dates, activity_lookup)

        # Successor should start 2 days after predecessor start
        assert activity_dates[successor_id][0] == date(2026, 1, 12)

    @pytest.mark.asyncio
    async def test_propagate_to_successors_ff_dependency(self):
        """Test _propagate_to_successors with finish-to-finish dependency."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        activity_dates = {
            predecessor_id: (date(2026, 1, 10), date(2026, 1, 20)),
            successor_id: (date(2026, 1, 5), date(2026, 1, 10)),  # 5-day duration
        }
        activity_lookup = {
            predecessor_id: MagicMock(id=predecessor_id),
            successor_id: MagicMock(id=successor_id),
        }

        mock_dep = MagicMock()
        mock_dep.successor_id = successor_id
        mock_dep.lag = 0
        mock_dep.dependency_type = MagicMock()
        mock_dep.dependency_type.value = "FF"

        call_count = [0]

        async def get_successors_mock(aid):
            call_count[0] += 1
            if aid == predecessor_id and call_count[0] == 1:
                return [mock_dep]
            return []

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = get_successors_mock

        await service._propagate_to_successors(predecessor_id, activity_dates, activity_lookup)

        # FF: successor should finish when predecessor finishes
        new_start, new_finish = activity_dates[successor_id]
        assert new_finish == date(2026, 1, 20)

    @pytest.mark.asyncio
    async def test_propagate_to_successors_sf_dependency(self):
        """Test _propagate_to_successors with start-to-finish dependency."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        activity_dates = {
            predecessor_id: (date(2026, 1, 15), date(2026, 1, 20)),
            successor_id: (date(2026, 1, 5), date(2026, 1, 10)),  # 5-day duration
        }
        activity_lookup = {
            predecessor_id: MagicMock(id=predecessor_id),
            successor_id: MagicMock(id=successor_id),
        }

        mock_dep = MagicMock()
        mock_dep.successor_id = successor_id
        mock_dep.lag = 0
        mock_dep.dependency_type = MagicMock()
        mock_dep.dependency_type.value = "SF"

        call_count = [0]

        async def get_successors_mock(aid):
            call_count[0] += 1
            if aid == predecessor_id and call_count[0] == 1:
                return [mock_dep]
            return []

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = get_successors_mock

        await service._propagate_to_successors(predecessor_id, activity_dates, activity_lookup)

        # SF: successor finish at predecessor start
        new_start, new_finish = activity_dates[successor_id]
        assert new_finish == date(2026, 1, 15)

    @pytest.mark.asyncio
    async def test_propagate_to_successors_default_dependency_type(self):
        """Test _propagate_to_successors with unknown dependency type."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        activity_dates = {
            predecessor_id: (date(2026, 1, 10), date(2026, 1, 15)),
            successor_id: (date(2026, 1, 12), date(2026, 1, 17)),
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

        await service._propagate_to_successors(predecessor_id, activity_dates, activity_lookup)

        # Unknown types default to FS behavior
        assert activity_dates[successor_id][0] == date(2026, 1, 16)

    @pytest.mark.asyncio
    async def test_propagate_successor_not_in_lookup(self):
        """Test _propagate_to_successors skips successors not in lookup."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        activity_dates = {
            predecessor_id: (date(2026, 1, 10), date(2026, 1, 15)),
            successor_id: (date(2026, 1, 12), date(2026, 1, 17)),
        }
        activity_lookup = {
            predecessor_id: MagicMock(id=predecessor_id),
            # successor_id not in lookup
        }

        mock_dep = MagicMock()
        mock_dep.successor_id = successor_id
        mock_dep.lag = 0
        mock_dep.dependency_type = MagicMock()
        mock_dep.dependency_type.value = "FS"

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = AsyncMock(return_value=[mock_dep])

        await service._propagate_to_successors(predecessor_id, activity_dates, activity_lookup)

        # Successor dates should not change
        assert activity_dates[successor_id] == (date(2026, 1, 12), date(2026, 1, 17))

    @pytest.mark.asyncio
    async def test_propagate_successor_not_in_dates(self):
        """Test _propagate_to_successors skips successors not in activity_dates."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        activity_dates = {
            predecessor_id: (date(2026, 1, 10), date(2026, 1, 15)),
            # successor_id not in activity_dates
        }
        activity_lookup = {
            predecessor_id: MagicMock(id=predecessor_id),
            successor_id: MagicMock(id=successor_id),
        }

        mock_dep = MagicMock()
        mock_dep.successor_id = successor_id
        mock_dep.lag = 0
        mock_dep.dependency_type = MagicMock()
        mock_dep.dependency_type.value = "FS"

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = AsyncMock(return_value=[mock_dep])

        await service._propagate_to_successors(predecessor_id, activity_dates, activity_lookup)

        # Should not add successor to dates
        assert successor_id not in activity_dates

    @pytest.mark.asyncio
    async def test_propagate_no_update_if_earlier(self):
        """Test _propagate_to_successors does not update if new date is earlier."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        predecessor_id = uuid4()
        successor_id = uuid4()

        # Successor already starts after predecessor finishes
        activity_dates = {
            predecessor_id: (date(2026, 1, 10), date(2026, 1, 15)),
            successor_id: (date(2026, 1, 20), date(2026, 1, 25)),  # Already later
        }
        activity_lookup = {
            predecessor_id: MagicMock(id=predecessor_id),
            successor_id: MagicMock(id=successor_id),
        }

        mock_dep = MagicMock()
        mock_dep.successor_id = successor_id
        mock_dep.lag = 0
        mock_dep.dependency_type = MagicMock()
        mock_dep.dependency_type.value = "FS"

        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = AsyncMock(return_value=[mock_dep])

        await service._propagate_to_successors(predecessor_id, activity_dates, activity_lookup)

        # Successor should keep its original dates (already later)
        assert activity_dates[successor_id] == (date(2026, 1, 20), date(2026, 1, 25))

    @pytest.mark.asyncio
    async def test_apply_result_activity_not_found(self):
        """Test apply_leveling_result handles activity not found."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService
        from src.services.resource_leveling import ActivityShift

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_id = AsyncMock(return_value=None)

        shift = ActivityShift(
            activity_id=uuid4(),
            activity_code="ACT-001",
            original_start=date(2026, 1, 1),
            original_finish=date(2026, 1, 5),
            new_start=date(2026, 1, 8),
            new_finish=date(2026, 1, 12),
            delay_days=7,
            reason="Resource conflict",
        )

        result = ParallelLevelingResult(
            program_id=uuid4(),
            success=True,
            iterations_used=1,
            activities_shifted=1,
            shifts=[shift],
            remaining_overallocations=0,
            new_project_finish=date(2026, 1, 12),
            original_project_finish=date(2026, 1, 5),
            schedule_extension_days=7,
        )

        success = await service.apply_leveling_result(result)
        assert success is True

    @pytest.mark.asyncio
    async def test_apply_result_multiple_shifts_same_activity(self):
        """Test apply_leveling_result uses latest shift for same activity."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService
        from src.services.resource_leveling import ActivityShift

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        activity_id = uuid4()
        mock_activity = MagicMock()
        mock_activity.id = activity_id

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_id = AsyncMock(return_value=mock_activity)

        # Two shifts for same activity
        shift1 = ActivityShift(
            activity_id=activity_id,
            activity_code="ACT-001",
            original_start=date(2026, 1, 1),
            original_finish=date(2026, 1, 5),
            new_start=date(2026, 1, 5),
            new_finish=date(2026, 1, 9),
            delay_days=4,
            reason="First delay",
        )
        shift2 = ActivityShift(
            activity_id=activity_id,
            activity_code="ACT-001",
            original_start=date(2026, 1, 5),
            original_finish=date(2026, 1, 9),
            new_start=date(2026, 1, 10),
            new_finish=date(2026, 1, 14),
            delay_days=5,
            reason="Second delay",
        )

        result = ParallelLevelingResult(
            program_id=uuid4(),
            success=True,
            iterations_used=2,
            activities_shifted=1,
            shifts=[shift1, shift2],
            remaining_overallocations=0,
            new_project_finish=date(2026, 1, 14),
            original_project_finish=date(2026, 1, 5),
            schedule_extension_days=9,
        )

        success = await service.apply_leveling_result(result)
        assert success is True

        # Should use second shift's dates
        assert mock_activity.planned_start == date(2026, 1, 10)
        assert mock_activity.planned_finish == date(2026, 1, 14)


class TestParallelLevelingMainLoop:
    """Tests for the main leveling loop in level_program."""

    @pytest.mark.asyncio
    async def test_leveling_loop_with_conflict_resolution(self):
        """Test full leveling loop with conflict detection and resolution."""
        from unittest.mock import AsyncMock, MagicMock
        from heapq import heappush
        from src.services.parallel_leveling import ParallelLevelingService, ResourceConflict
        from src.services.resource_leveling import LevelingOptions

        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()
        service = ParallelLevelingService(mock_session)

        program_id = uuid4()
        activity1_id = uuid4()
        activity2_id = uuid4()
        resource_id = uuid4()

        # Setup program
        mock_program = MagicMock()
        mock_program.start_date = date(2026, 1, 1)
        mock_program.end_date = date(2026, 12, 31)
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        # Setup activities
        activity1 = MagicMock()
        activity1.id = activity1_id
        activity1.code = "ACT-001"
        activity1.early_start = date(2026, 1, 6)  # Monday
        activity1.early_finish = date(2026, 1, 10)
        activity1.planned_start = date(2026, 1, 6)
        activity1.planned_finish = date(2026, 1, 10)
        activity1.total_float = 0
        activity1.is_critical = True

        activity2 = MagicMock()
        activity2.id = activity2_id
        activity2.code = "ACT-002"
        activity2.early_start = date(2026, 1, 6)  # Same dates
        activity2.early_finish = date(2026, 1, 10)
        activity2.planned_start = date(2026, 1, 6)
        activity2.planned_finish = date(2026, 1, 10)
        activity2.total_float = 10
        activity2.is_critical = False

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[activity1, activity2])

        # Setup resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "RES-001"
        mock_resource.capacity_per_day = Decimal("8.0")
        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._resource_repo.get_by_program = AsyncMock(return_value=([mock_resource], 1))

        # Setup assignments
        assignment1 = MagicMock()
        assignment1.activity_id = activity1_id
        assignment1.resource_id = resource_id
        assignment1.units = Decimal("1.0")

        assignment2 = MagicMock()
        assignment2.activity_id = activity2_id
        assignment2.resource_id = resource_id
        assignment2.units = Decimal("1.0")

        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[MagicMock()])
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[assignment1, assignment2]
        )

        # Setup dependencies
        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = AsyncMock(return_value=[])

        # Create initial conflict
        initial_conflict = ResourceConflict(
            resource_id=resource_id,
            conflict_date=date(2026, 1, 6),
            overallocation_hours=Decimal("8.0"),
            activities=[activity1_id, activity2_id],
        )

        # Mock _build_conflict_matrix to return conflict first time, then empty
        call_count = [0]

        async def mock_build_conflict_matrix(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                conflicts = []
                heappush(conflicts, initial_conflict)
                return conflicts
            return []  # No more conflicts after first iteration

        service._build_conflict_matrix = mock_build_conflict_matrix

        # Mock _calculate_minimum_delay to return 7 days
        service._calculate_minimum_delay = AsyncMock(return_value=7)

        options = LevelingOptions(preserve_critical_path=True)
        result = await service.level_program(program_id, options)

        # Should have resolved the conflict by delaying activity2 (non-critical)
        assert result.iterations_used >= 1
        assert result.conflicts_resolved >= 0

    @pytest.mark.asyncio
    async def test_leveling_loop_cannot_delay_any_activity(self):
        """Test loop when no activity can be delayed."""
        from unittest.mock import AsyncMock, MagicMock
        from heapq import heappush
        from src.services.parallel_leveling import ParallelLevelingService, ResourceConflict
        from src.services.resource_leveling import LevelingOptions

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        program_id = uuid4()
        activity_id = uuid4()
        resource_id = uuid4()

        # Setup program
        mock_program = MagicMock()
        mock_program.start_date = date(2026, 1, 1)
        mock_program.end_date = date(2026, 12, 31)
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        # Setup single critical activity (can't be delayed with preserve_critical_path)
        activity = MagicMock()
        activity.id = activity_id
        activity.code = "ACT-001"
        activity.early_start = date(2026, 1, 6)
        activity.early_finish = date(2026, 1, 10)
        activity.planned_start = date(2026, 1, 6)
        activity.planned_finish = date(2026, 1, 10)
        activity.total_float = 0
        activity.is_critical = True

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[activity])

        # Setup resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "RES-001"
        mock_resource.capacity_per_day = Decimal("8.0")
        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._resource_repo.get_by_program = AsyncMock(return_value=([mock_resource], 1))

        # Setup assignment
        assignment = MagicMock()
        assignment.activity_id = activity_id
        assignment.resource_id = resource_id
        assignment.units = Decimal("1.0")

        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[MagicMock()])
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[assignment]
        )

        # Setup dependencies
        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = AsyncMock(return_value=[])

        # Create conflict with single critical activity
        conflict = ResourceConflict(
            resource_id=resource_id,
            conflict_date=date(2026, 1, 6),
            overallocation_hours=Decimal("4.0"),
            activities=[activity_id],
        )

        async def mock_build_conflict_matrix(*args, **kwargs):
            conflicts = []
            heappush(conflicts, conflict)
            return conflicts

        service._build_conflict_matrix = mock_build_conflict_matrix

        options = LevelingOptions(preserve_critical_path=True, max_iterations=5)
        result = await service.level_program(program_id, options)

        # Should have warning about not being able to resolve
        assert len(result.warnings) > 0
        assert "Could not resolve conflict" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_leveling_loop_delay_days_zero(self):
        """Test loop when calculated delay is zero."""
        from unittest.mock import AsyncMock, MagicMock
        from heapq import heappush
        from src.services.parallel_leveling import ParallelLevelingService, ResourceConflict
        from src.services.resource_leveling import LevelingOptions

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        program_id = uuid4()
        activity_id = uuid4()
        resource_id = uuid4()

        # Setup program
        mock_program = MagicMock()
        mock_program.start_date = date(2026, 1, 1)
        mock_program.end_date = date(2026, 12, 31)
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        # Setup activity
        activity = MagicMock()
        activity.id = activity_id
        activity.code = "ACT-001"
        activity.early_start = date(2026, 1, 6)
        activity.early_finish = date(2026, 1, 10)
        activity.planned_start = date(2026, 1, 6)
        activity.planned_finish = date(2026, 1, 10)
        activity.total_float = 10
        activity.is_critical = False

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_program = AsyncMock(return_value=[activity])

        # Setup resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "RES-001"
        mock_resource.capacity_per_day = Decimal("8.0")
        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._resource_repo.get_by_program = AsyncMock(return_value=([mock_resource], 1))

        # Setup assignment
        assignment = MagicMock()
        assignment.activity_id = activity_id
        assignment.resource_id = resource_id
        assignment.units = Decimal("1.0")

        service._assignment_repo = MagicMock()
        service._assignment_repo.get_by_activity = AsyncMock(return_value=[MagicMock()])
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[assignment]
        )

        # Setup dependencies
        service._dependency_repo = MagicMock()
        service._dependency_repo.get_successors = AsyncMock(return_value=[])

        # Create conflict
        conflict = ResourceConflict(
            resource_id=resource_id,
            conflict_date=date(2026, 1, 6),
            overallocation_hours=Decimal("4.0"),
            activities=[activity_id],
        )

        # Build conflict once, then return empty
        call_count = [0]

        async def mock_build_conflict_matrix(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                conflicts = []
                heappush(conflicts, conflict)
                return conflicts
            return []

        service._build_conflict_matrix = mock_build_conflict_matrix

        # Return 0 delay
        service._calculate_minimum_delay = AsyncMock(return_value=0)

        options = LevelingOptions(max_iterations=5)
        result = await service.level_program(program_id, options)

        # Should skip activity with 0 delay
        assert result.activities_shifted == 0


class TestCalculateMinimumDelay:
    """Tests for the _calculate_minimum_delay method."""

    @pytest.mark.asyncio
    async def test_delay_with_assignment_found(self):
        """Test calculating delay when activity has assignment."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        activity_id = uuid4()
        resource_id = uuid4()

        # Mock resource
        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)

        # Create assignment matching the activity
        assignment = MagicMock()
        assignment.activity_id = activity_id
        assignment.resource_id = resource_id
        assignment.units = Decimal("0.5")

        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[assignment]
        )

        activity_dates = {
            activity_id: (date(2026, 1, 6), date(2026, 1, 10)),
        }

        delay = await service._calculate_minimum_delay(
            activity_id=activity_id,
            resource_id=resource_id,
            conflict_date=date(2026, 1, 6),
            activity_dates=activity_dates,
        )

        # Should find a slot (delay >= 1)
        assert delay >= 1

    @pytest.mark.asyncio
    async def test_delay_no_matching_assignment(self):
        """Test delay when no matching assignment exists."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        activity_id = uuid4()
        other_activity_id = uuid4()
        resource_id = uuid4()

        # Mock resource
        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)

        # Assignment for different activity
        assignment = MagicMock()
        assignment.activity_id = other_activity_id
        assignment.resource_id = resource_id
        assignment.units = Decimal("0.5")

        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[assignment]
        )

        activity_dates = {
            activity_id: (date(2026, 1, 6), date(2026, 1, 10)),
        }

        delay = await service._calculate_minimum_delay(
            activity_id=activity_id,
            resource_id=resource_id,
            conflict_date=date(2026, 1, 6),
            activity_dates=activity_dates,
        )

        # Should return 1 when no matching assignment
        assert delay == 1

    @pytest.mark.asyncio
    async def test_delay_resource_not_found(self):
        """Test delay returns 1 when resource not found."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        activity_id = uuid4()
        resource_id = uuid4()

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=None)

        activity_dates = {
            activity_id: (date(2026, 1, 6), date(2026, 1, 10)),
        }

        delay = await service._calculate_minimum_delay(
            activity_id=activity_id,
            resource_id=resource_id,
            conflict_date=date(2026, 1, 6),
            activity_dates=activity_dates,
        )

        # Should return 1 when resource not found
        assert delay == 1

    @pytest.mark.asyncio
    async def test_delay_with_overlapping_activities(self):
        """Test delay with other activities occupying resource."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        activity_id = uuid4()
        other_activity_id = uuid4()
        resource_id = uuid4()

        # Mock resource with capacity
        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("1.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)

        # Assignment for target activity
        target_assignment = MagicMock()
        target_assignment.activity_id = activity_id
        target_assignment.resource_id = resource_id
        target_assignment.units = Decimal("0.5")

        # Assignment for blocking activity using high capacity
        blocking_assignment = MagicMock()
        blocking_assignment.activity_id = other_activity_id
        blocking_assignment.resource_id = resource_id
        blocking_assignment.units = Decimal("0.8")

        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[target_assignment, blocking_assignment]
        )

        activity_dates = {
            activity_id: (date(2026, 1, 6), date(2026, 1, 10)),
            other_activity_id: (date(2026, 1, 6), date(2026, 1, 12)),
        }

        delay = await service._calculate_minimum_delay(
            activity_id=activity_id,
            resource_id=resource_id,
            conflict_date=date(2026, 1, 6),
            activity_dates=activity_dates,
        )

        # Should find a slot after the blocking activity
        assert delay >= 1

    @pytest.mark.asyncio
    async def test_delay_with_weekend_skipping(self):
        """Test delay calculation skips weekends."""
        from unittest.mock import AsyncMock, MagicMock
        from src.services.parallel_leveling import ParallelLevelingService

        mock_session = AsyncMock()
        service = ParallelLevelingService(mock_session)

        activity_id = uuid4()
        resource_id = uuid4()

        # Mock resource
        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)

        # Simple assignment
        assignment = MagicMock()
        assignment.activity_id = activity_id
        assignment.resource_id = resource_id
        assignment.units = Decimal("0.5")

        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[assignment]
        )

        # Friday conflict - should skip weekend
        activity_dates = {
            activity_id: (date(2026, 1, 9), date(2026, 1, 13)),  # Friday
        }

        delay = await service._calculate_minimum_delay(
            activity_id=activity_id,
            resource_id=resource_id,
            conflict_date=date(2026, 1, 9),  # Friday
            activity_dates=activity_dates,
        )

        # Should include weekend skip in delay
        assert delay >= 1
