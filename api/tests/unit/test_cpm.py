"""Unit tests for CPM engine."""

from uuid import uuid4

import pytest

from src.core.exceptions import CircularDependencyError
from src.models.activity import Activity
from src.models.dependency import Dependency, DependencyType
from src.services.cpm import CPMEngine


class TestCPMForwardPass:
    """Tests for CPM forward pass calculation."""

    def test_simple_chain_calculates_correct_dates(self):
        """A(5d) -> B(3d) -> C(2d) should give ES/EF: 0/5, 5/8, 8/10."""
        # Arrange
        program_id = uuid4()
        activities = [
            Activity(id=uuid4(), program_id=program_id, name="A", code="A", duration=5),
            Activity(id=uuid4(), program_id=program_id, name="B", code="B", duration=3),
            Activity(id=uuid4(), program_id=program_id, name="C", code="C", duration=2),
        ]
        dependencies = [
            Dependency(
                id=uuid4(),
                predecessor_id=activities[0].id,
                successor_id=activities[1].id,
                dependency_type=DependencyType.FS.value,
                lag=0,
            ),
            Dependency(
                id=uuid4(),
                predecessor_id=activities[1].id,
                successor_id=activities[2].id,
                dependency_type=DependencyType.FS.value,
                lag=0,
            ),
        ]
        engine = CPMEngine(activities, dependencies)

        # Act
        result = engine.calculate()

        # Assert
        assert result[activities[0].id].early_start == 0
        assert result[activities[0].id].early_finish == 5
        assert result[activities[1].id].early_start == 5
        assert result[activities[1].id].early_finish == 8
        assert result[activities[2].id].early_start == 8
        assert result[activities[2].id].early_finish == 10

    def test_parallel_paths_takes_longest(self):
        """Two parallel paths should use the longest for ES."""
        # Arrange
        program_id = uuid4()
        activities = [
            Activity(id=uuid4(), program_id=program_id, name="Start", code="S", duration=0),
            Activity(id=uuid4(), program_id=program_id, name="A", code="A", duration=5),
            Activity(id=uuid4(), program_id=program_id, name="B", code="B", duration=3),
            Activity(id=uuid4(), program_id=program_id, name="End", code="E", duration=0),
        ]
        dependencies = [
            Dependency(
                id=uuid4(),
                predecessor_id=activities[0].id,
                successor_id=activities[1].id,
                dependency_type=DependencyType.FS.value,
                lag=0,
            ),
            Dependency(
                id=uuid4(),
                predecessor_id=activities[0].id,
                successor_id=activities[2].id,
                dependency_type=DependencyType.FS.value,
                lag=0,
            ),
            Dependency(
                id=uuid4(),
                predecessor_id=activities[1].id,
                successor_id=activities[3].id,
                dependency_type=DependencyType.FS.value,
                lag=0,
            ),
            Dependency(
                id=uuid4(),
                predecessor_id=activities[2].id,
                successor_id=activities[3].id,
                dependency_type=DependencyType.FS.value,
                lag=0,
            ),
        ]
        engine = CPMEngine(activities, dependencies)

        # Act
        result = engine.calculate()

        # Assert - End should start at 5 (after longer path A)
        assert result[activities[3].id].early_start == 5

    def test_fs_with_positive_lag(self):
        """FS dependency with lag should delay successor."""
        # Arrange
        program_id = uuid4()
        activities = [
            Activity(id=uuid4(), program_id=program_id, name="A", code="A", duration=5),
            Activity(id=uuid4(), program_id=program_id, name="B", code="B", duration=3),
        ]
        dependencies = [
            Dependency(
                id=uuid4(),
                predecessor_id=activities[0].id,
                successor_id=activities[1].id,
                dependency_type=DependencyType.FS.value,
                lag=2,  # 2 days lag
            ),
        ]
        engine = CPMEngine(activities, dependencies)

        # Act
        result = engine.calculate()

        # Assert - B should start at 7 (5 + 2 lag)
        assert result[activities[1].id].early_start == 7
        assert result[activities[1].id].early_finish == 10


class TestCPMBackwardPass:
    """Tests for CPM backward pass calculation."""

    def test_simple_chain_calculates_late_dates(self):
        """Simple chain should have correct late dates."""
        # Arrange
        program_id = uuid4()
        activities = [
            Activity(id=uuid4(), program_id=program_id, name="A", code="A", duration=5),
            Activity(id=uuid4(), program_id=program_id, name="B", code="B", duration=3),
        ]
        dependencies = [
            Dependency(
                id=uuid4(),
                predecessor_id=activities[0].id,
                successor_id=activities[1].id,
                dependency_type=DependencyType.FS.value,
                lag=0,
            ),
        ]
        engine = CPMEngine(activities, dependencies)

        # Act
        result = engine.calculate()

        # Assert - All activities on critical path, so LS=ES, LF=EF
        assert result[activities[0].id].late_start == 0
        assert result[activities[0].id].late_finish == 5
        assert result[activities[1].id].late_start == 5
        assert result[activities[1].id].late_finish == 8


class TestCPMFloat:
    """Tests for float calculation."""

    def test_critical_path_has_zero_float(self):
        """Activities on critical path should have zero total float."""
        # Arrange
        program_id = uuid4()
        activities = [
            Activity(id=uuid4(), program_id=program_id, name="A", code="A", duration=5),
            Activity(id=uuid4(), program_id=program_id, name="B", code="B", duration=3),
        ]
        dependencies = [
            Dependency(
                id=uuid4(),
                predecessor_id=activities[0].id,
                successor_id=activities[1].id,
                dependency_type=DependencyType.FS.value,
                lag=0,
            ),
        ]
        engine = CPMEngine(activities, dependencies)

        # Act
        result = engine.calculate()

        # Assert
        assert result[activities[0].id].total_float == 0
        assert result[activities[1].id].total_float == 0
        assert result[activities[0].id].is_critical
        assert result[activities[1].id].is_critical


class TestCPMCycleDetection:
    """Tests for circular dependency detection."""

    def test_detects_circular_dependency(self):
        """Should raise error when circular dependency exists."""
        # Arrange
        program_id = uuid4()
        activities = [
            Activity(id=uuid4(), program_id=program_id, name="A", code="A", duration=5),
            Activity(id=uuid4(), program_id=program_id, name="B", code="B", duration=3),
            Activity(id=uuid4(), program_id=program_id, name="C", code="C", duration=2),
        ]
        dependencies = [
            Dependency(
                id=uuid4(),
                predecessor_id=activities[0].id,
                successor_id=activities[1].id,
                dependency_type=DependencyType.FS.value,
                lag=0,
            ),
            Dependency(
                id=uuid4(),
                predecessor_id=activities[1].id,
                successor_id=activities[2].id,
                dependency_type=DependencyType.FS.value,
                lag=0,
            ),
            Dependency(
                id=uuid4(),
                predecessor_id=activities[2].id,
                successor_id=activities[0].id,  # Creates cycle: A -> B -> C -> A
                dependency_type=DependencyType.FS.value,
                lag=0,
            ),
        ]
        engine = CPMEngine(activities, dependencies)

        # Act & Assert
        with pytest.raises(CircularDependencyError):
            engine.calculate()


class TestCPMProjectDuration:
    """Tests for project duration calculation."""

    def test_get_project_duration(self):
        """Should return total project duration."""
        # Arrange
        program_id = uuid4()
        activities = [
            Activity(id=uuid4(), program_id=program_id, name="A", code="A", duration=5),
            Activity(id=uuid4(), program_id=program_id, name="B", code="B", duration=3),
        ]
        dependencies = [
            Dependency(
                id=uuid4(),
                predecessor_id=activities[0].id,
                successor_id=activities[1].id,
                dependency_type=DependencyType.FS.value,
                lag=0,
            ),
        ]
        engine = CPMEngine(activities, dependencies)
        engine.calculate()

        # Act
        duration = engine.get_project_duration()

        # Assert
        assert duration == 8


class TestCPMCriticalPath:
    """Tests for critical path identification."""

    def test_get_critical_path(self):
        """Should return activities on critical path in order."""
        # Arrange
        program_id = uuid4()
        activities = [
            Activity(id=uuid4(), program_id=program_id, name="A", code="A", duration=5),
            Activity(id=uuid4(), program_id=program_id, name="B", code="B", duration=3),
        ]
        dependencies = [
            Dependency(
                id=uuid4(),
                predecessor_id=activities[0].id,
                successor_id=activities[1].id,
                dependency_type=DependencyType.FS.value,
                lag=0,
            ),
        ]
        engine = CPMEngine(activities, dependencies)
        engine.calculate()

        # Act
        critical_path = engine.get_critical_path()

        # Assert
        assert len(critical_path) == 2
        assert critical_path[0] == activities[0].id
        assert critical_path[1] == activities[1].id
