"""Unit tests for parallel leveling service."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

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
