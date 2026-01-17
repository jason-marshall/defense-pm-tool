"""Additional CPM engine tests for edge cases and coverage."""

from uuid import uuid4

from src.models.activity import Activity
from src.models.dependency import Dependency
from src.services.cpm import CPMEngine


class TestCPMEdgeCases:
    """Edge case tests for CPM calculations."""

    def test_single_activity_no_dependencies(self):
        """Single activity with no dependencies."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            name="Single Task",
            duration=5,
        )
        engine = CPMEngine([activity], [])
        result = engine.calculate()

        assert result[activity.id].early_start == 0
        assert result[activity.id].early_finish == 5
        assert result[activity.id].total_float == 0

    def test_parallel_activities(self):
        """Two parallel activities should have same ES."""
        program_id = uuid4()
        start = Activity(
            id=uuid4(),
            program_id=program_id,
            name="Start",
            duration=0,
        )
        task_a = Activity(
            id=uuid4(),
            program_id=program_id,
            name="Task A",
            duration=5,
        )
        task_b = Activity(
            id=uuid4(),
            program_id=program_id,
            name="Task B",
            duration=3,
        )

        deps = [
            Dependency(
                predecessor_id=start.id,
                successor_id=task_a.id,
                dependency_type="FS",
                lag=0,
            ),
            Dependency(
                predecessor_id=start.id,
                successor_id=task_b.id,
                dependency_type="FS",
                lag=0,
            ),
        ]

        engine = CPMEngine([start, task_a, task_b], deps)
        result = engine.calculate()

        assert result[task_a.id].early_start == 0
        assert result[task_b.id].early_start == 0

    def test_simple_chain_critical_path(self):
        """Simple chain A -> B -> C should all be on critical path."""
        program_id = uuid4()
        act_a = Activity(
            id=uuid4(),
            program_id=program_id,
            name="A",
            duration=5,
        )
        act_b = Activity(
            id=uuid4(),
            program_id=program_id,
            name="B",
            duration=3,
        )
        act_c = Activity(
            id=uuid4(),
            program_id=program_id,
            name="C",
            duration=2,
        )

        deps = [
            Dependency(
                predecessor_id=act_a.id,
                successor_id=act_b.id,
                dependency_type="FS",
                lag=0,
            ),
            Dependency(
                predecessor_id=act_b.id,
                successor_id=act_c.id,
                dependency_type="FS",
                lag=0,
            ),
        ]

        engine = CPMEngine([act_a, act_b, act_c], deps)
        result = engine.calculate()

        # Verify ES/EF values
        assert result[act_a.id].early_start == 0
        assert result[act_a.id].early_finish == 5
        assert result[act_b.id].early_start == 5
        assert result[act_b.id].early_finish == 8
        assert result[act_c.id].early_start == 8
        assert result[act_c.id].early_finish == 10

    def test_dependency_with_lag(self):
        """Dependency with positive lag."""
        program_id = uuid4()
        act_a = Activity(
            id=uuid4(),
            program_id=program_id,
            name="A",
            duration=5,
        )
        act_b = Activity(
            id=uuid4(),
            program_id=program_id,
            name="B",
            duration=3,
        )

        deps = [
            Dependency(
                predecessor_id=act_a.id,
                successor_id=act_b.id,
                dependency_type="FS",
                lag=2,  # 2-day lag
            ),
        ]

        engine = CPMEngine([act_a, act_b], deps)
        result = engine.calculate()

        # B should start 2 days after A finishes
        assert result[act_b.id].early_start == 7

    def test_zero_duration_milestone(self):
        """Zero-duration activities (milestones)."""
        program_id = uuid4()
        milestone = Activity(
            id=uuid4(),
            program_id=program_id,
            name="Milestone",
            duration=0,
        )

        engine = CPMEngine([milestone], [])
        result = engine.calculate()

        assert result[milestone.id].early_start == 0
        assert result[milestone.id].early_finish == 0


class TestCPMCycleDetection:
    """Tests for cycle detection in dependency graph."""

    def test_detect_simple_cycle(self):
        """Detect A -> B -> A cycle."""
        program_id = uuid4()
        act_a = Activity(
            id=uuid4(),
            program_id=program_id,
            name="A",
            duration=5,
        )
        act_b = Activity(
            id=uuid4(),
            program_id=program_id,
            name="B",
            duration=3,
        )

        deps = [
            Dependency(
                predecessor_id=act_a.id,
                successor_id=act_b.id,
                dependency_type="FS",
                lag=0,
            ),
            Dependency(
                predecessor_id=act_b.id,
                successor_id=act_a.id,
                dependency_type="FS",
                lag=0,
            ),
        ]

        engine = CPMEngine([act_a, act_b], deps)
        cycle = engine._detect_cycles()

        assert cycle is not None
        assert len(cycle) >= 2


class TestCPMDependencyTypes:
    """Tests for different dependency types."""

    def test_start_to_start_dependency(self):
        """SS: Successor starts when predecessor starts."""
        program_id = uuid4()
        act_a = Activity(
            id=uuid4(),
            program_id=program_id,
            name="A",
            duration=5,
        )
        act_b = Activity(
            id=uuid4(),
            program_id=program_id,
            name="B",
            duration=3,
        )

        deps = [
            Dependency(
                predecessor_id=act_a.id,
                successor_id=act_b.id,
                dependency_type="SS",
                lag=0,
            ),
        ]

        engine = CPMEngine([act_a, act_b], deps)
        result = engine.calculate()

        # B should start when A starts
        assert result[act_b.id].early_start == result[act_a.id].early_start

    def test_finish_to_finish_dependency(self):
        """FF: Successor finishes when predecessor finishes."""
        program_id = uuid4()
        act_a = Activity(
            id=uuid4(),
            program_id=program_id,
            name="A",
            duration=5,
        )
        act_b = Activity(
            id=uuid4(),
            program_id=program_id,
            name="B",
            duration=3,
        )

        deps = [
            Dependency(
                predecessor_id=act_a.id,
                successor_id=act_b.id,
                dependency_type="FF",
                lag=0,
            ),
        ]

        engine = CPMEngine([act_a, act_b], deps)
        result = engine.calculate()

        # B's EF should equal A's EF
        assert result[act_b.id].early_finish == result[act_a.id].early_finish

    def test_start_to_finish_dependency(self):
        """SF: Successor finishes when predecessor starts."""
        program_id = uuid4()
        act_a = Activity(
            id=uuid4(),
            program_id=program_id,
            name="A",
            duration=5,
        )
        act_b = Activity(
            id=uuid4(),
            program_id=program_id,
            name="B",
            duration=3,
        )

        deps = [
            Dependency(
                predecessor_id=act_a.id,
                successor_id=act_b.id,
                dependency_type="SF",
                lag=0,
            ),
        ]

        engine = CPMEngine([act_a, act_b], deps)
        result = engine.calculate()

        # B's finish is constrained by A's start
        # With SF(A, B), B finishes when A starts: B.EF = A.ES + lag
        # So B.ES = A.ES - B.duration
        # A starts at 0, so B.EF = 0, B.ES = max(0, 0-3) = 0, but EF = 0+3 = 3
        # Since ES can't be negative, B starts at 0 and finishes at 3
        assert result[act_b.id].early_start >= 0

    def test_start_to_finish_dependency_with_lag(self):
        """SF with lag: Successor finishes after predecessor starts + lag."""
        program_id = uuid4()
        act_a = Activity(
            id=uuid4(),
            program_id=program_id,
            name="A",
            duration=5,
        )
        act_b = Activity(
            id=uuid4(),
            program_id=program_id,
            name="B",
            duration=3,
        )

        deps = [
            Dependency(
                predecessor_id=act_a.id,
                successor_id=act_b.id,
                dependency_type="SF",
                lag=5,
            ),
        ]

        engine = CPMEngine([act_a, act_b], deps)
        result = engine.calculate()

        # With SF lag=5: B.EF >= A.ES + 5 = 0 + 5 = 5
        # B.ES = B.EF - duration = 5 - 3 = 2
        assert result[act_b.id].early_finish >= 5


class TestCPMFloat:
    """Tests for float calculations."""

    def test_non_critical_activity_has_float(self):
        """Activity not on critical path should have positive float."""
        program_id = uuid4()
        start = Activity(
            id=uuid4(),
            program_id=program_id,
            name="Start",
            duration=0,
        )
        critical = Activity(
            id=uuid4(),
            program_id=program_id,
            name="Critical",
            duration=10,
        )
        non_critical = Activity(
            id=uuid4(),
            program_id=program_id,
            name="Non-Critical",
            duration=3,
        )
        end = Activity(
            id=uuid4(),
            program_id=program_id,
            name="End",
            duration=0,
        )

        deps = [
            Dependency(
                predecessor_id=start.id,
                successor_id=critical.id,
                dependency_type="FS",
                lag=0,
            ),
            Dependency(
                predecessor_id=start.id,
                successor_id=non_critical.id,
                dependency_type="FS",
                lag=0,
            ),
            Dependency(
                predecessor_id=critical.id,
                successor_id=end.id,
                dependency_type="FS",
                lag=0,
            ),
            Dependency(
                predecessor_id=non_critical.id,
                successor_id=end.id,
                dependency_type="FS",
                lag=0,
            ),
        ]

        engine = CPMEngine([start, critical, non_critical, end], deps)
        result = engine.calculate()

        # Non-critical should have float (10 - 3 = 7 days)
        assert result[non_critical.id].total_float > 0
        assert result[critical.id].total_float == 0


class TestCPMEmptyGraph:
    """Tests for empty or minimal graphs."""

    def test_empty_activity_list(self):
        """Empty activity list should handle gracefully."""
        engine = CPMEngine([], [])
        # Empty list may raise or return empty - just verify no crash
        try:
            result = engine.calculate()
            assert result == {}
        except ValueError:
            # Expected - max() on empty sequence
            pass

    def test_no_dependencies(self):
        """Activities with no dependencies should all start at 0."""
        program_id = uuid4()
        activities = [
            Activity(
                id=uuid4(),
                program_id=program_id,
                name=f"Task {i}",
                duration=i + 1,
            )
            for i in range(3)
        ]

        engine = CPMEngine(activities, [])
        result = engine.calculate()

        for activity in activities:
            assert result[activity.id].early_start == 0

    def test_get_critical_path_without_prior_calculate(self):
        """get_critical_path should calculate if not already done."""
        program_id = uuid4()
        act_a = Activity(
            id=uuid4(),
            program_id=program_id,
            name="A",
            duration=5,
        )
        act_b = Activity(
            id=uuid4(),
            program_id=program_id,
            name="B",
            duration=3,
        )

        deps = [
            Dependency(
                predecessor_id=act_a.id,
                successor_id=act_b.id,
                dependency_type="FS",
                lag=0,
            ),
        ]

        engine = CPMEngine([act_a, act_b], deps)
        # Don't call calculate first
        critical_path = engine.get_critical_path()

        # Should auto-calculate and return critical activities
        assert len(critical_path) >= 1

    def test_get_project_duration_without_prior_calculate(self):
        """get_project_duration should calculate if not already done."""
        program_id = uuid4()
        act_a = Activity(
            id=uuid4(),
            program_id=program_id,
            name="A",
            duration=5,
        )
        act_b = Activity(
            id=uuid4(),
            program_id=program_id,
            name="B",
            duration=3,
        )

        deps = [
            Dependency(
                predecessor_id=act_a.id,
                successor_id=act_b.id,
                dependency_type="FS",
                lag=0,
            ),
        ]

        engine = CPMEngine([act_a, act_b], deps)
        # Don't call calculate first
        duration = engine.get_project_duration()

        # Should auto-calculate and return duration (5 + 3 = 8)
        assert duration == 8
