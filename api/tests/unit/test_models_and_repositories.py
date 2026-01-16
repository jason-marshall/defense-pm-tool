"""Unit tests for models and repositories with low coverage."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.activity import Activity
from src.models.dependency import Dependency
from src.models.enums import DependencyType, ProgramStatus
from src.models.program import Program
from src.models.wbs import WBSElement
from src.repositories.activity import ActivityRepository
from src.repositories.dependency import DependencyRepository
from src.repositories.program import ProgramRepository


class TestDependencyModel:
    """Tests for Dependency model."""

    def test_dependency_repr(self):
        """Test dependency string representation."""
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=2,
        )
        repr_str = repr(dep)
        assert "Dependency" in repr_str
        assert "FS" in repr_str
        assert "lag=2" in repr_str

    def test_has_lag_with_positive_lag(self):
        """Test has_lag returns True for positive lag."""
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=5,
        )
        assert dep.has_lag is True

    def test_has_lag_with_negative_lag(self):
        """Test has_lag returns True for negative lag (lead)."""
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=-3,
        )
        assert dep.has_lag is True

    def test_has_lag_with_zero_lag(self):
        """Test has_lag returns False for zero lag."""
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=0,
        )
        assert dep.has_lag is False

    def test_has_lead_with_negative_lag(self):
        """Test has_lead returns True for negative lag."""
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=-2,
        )
        assert dep.has_lead is True

    def test_has_lead_with_positive_lag(self):
        """Test has_lead returns False for positive lag."""
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=5,
        )
        assert dep.has_lead is False

    def test_has_lead_with_zero_lag(self):
        """Test has_lead returns False for zero lag."""
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=0,
        )
        assert dep.has_lead is False

    def test_calculate_successor_constraint_fs(self):
        """Test FS: Successor ES = Predecessor EF + lag."""
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=2,
        )
        result = dep.calculate_successor_constraint(
            predecessor_es=0,
            predecessor_ef=10,
        )
        assert result == 12  # EF (10) + lag (2)

    def test_calculate_successor_constraint_ss(self):
        """Test SS: Successor ES = Predecessor ES + lag."""
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.SS,
            lag=3,
        )
        result = dep.calculate_successor_constraint(
            predecessor_es=5,
            predecessor_ef=15,
        )
        assert result == 8  # ES (5) + lag (3)

    def test_calculate_successor_constraint_ff(self):
        """Test FF: Successor EF = Predecessor EF + lag."""
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FF,
            lag=1,
        )
        result = dep.calculate_successor_constraint(
            predecessor_es=0,
            predecessor_ef=20,
        )
        assert result == 21  # EF (20) + lag (1)

    def test_calculate_successor_constraint_sf(self):
        """Test SF: Successor EF = Predecessor ES + lag."""
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.SF,
            lag=0,
        )
        result = dep.calculate_successor_constraint(
            predecessor_es=10,
            predecessor_ef=25,
        )
        assert result == 10  # ES (10) + lag (0)


class TestActivityRepositoryMethods:
    """Tests for ActivityRepository methods."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ActivityRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_program(self, repo, mock_session):
        """Should return activities for a program."""
        program_id = uuid4()
        activity = Activity(
            id=uuid4(),
            program_id=program_id,
            code="ACT-001",
            name="Test Activity",
            duration=10,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [activity]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_program(program_id)

        assert len(result) == 1
        assert result[0].code == "ACT-001"

    @pytest.mark.asyncio
    async def test_get_by_program_with_pagination(self, repo, mock_session):
        """Should apply pagination to get_by_program."""
        program_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_by_program(program_id, skip=10, limit=25)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_dependencies(self, repo, mock_session):
        """Should get activity with dependencies loaded."""
        activity_id = uuid4()
        activity = Activity(
            id=activity_id,
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = activity
        mock_session.execute.return_value = mock_result

        result = await repo.get_with_dependencies(activity_id)

        assert result == activity

    @pytest.mark.asyncio
    async def test_get_with_dependencies_not_found(self, repo, mock_session):
        """Should return None when activity not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_with_dependencies(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_with_dependencies(self, repo, mock_session):
        """Should get all activities with dependencies."""
        program_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_all_with_dependencies(program_id)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_code(self, repo, mock_session):
        """Should get activity by code."""
        program_id = uuid4()
        activity = Activity(
            id=uuid4(),
            program_id=program_id,
            code="ACT-001",
            name="Test",
            duration=5,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = activity
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_code(program_id, "ACT-001")

        assert result == activity

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(self, repo, mock_session):
        """Should return None when code not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_code(uuid4(), "NONEXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_critical_path(self, repo, mock_session):
        """Should get critical path activities."""
        program_id = uuid4()
        critical_activity = Activity(
            id=uuid4(),
            program_id=program_id,
            code="CRIT-001",
            name="Critical Task",
            duration=10,
            total_float=0,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [critical_activity]
        mock_session.execute.return_value = mock_result

        result = await repo.get_critical_path(program_id)

        assert len(result) == 1
        assert result[0].total_float == 0


class TestDependencyRepositoryMethods:
    """Tests for DependencyRepository methods."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return DependencyRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_activities(self, repo, mock_session):
        """Should get dependency by predecessor and successor."""
        pred_id = uuid4()
        succ_id = uuid4()
        dep = Dependency(
            id=uuid4(),
            predecessor_id=pred_id,
            successor_id=succ_id,
            dependency_type=DependencyType.FS,
            lag=0,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = dep
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_activities(pred_id, succ_id)

        assert result == dep

    @pytest.mark.asyncio
    async def test_get_by_activities_not_found(self, repo, mock_session):
        """Should return None when dependency not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_activities(uuid4(), uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_for_activity(self, repo, mock_session):
        """Should get all dependencies for an activity."""
        activity_id = uuid4()
        dep = Dependency(
            id=uuid4(),
            predecessor_id=activity_id,
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=0,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [dep]
        mock_session.execute.return_value = mock_result

        result = await repo.get_for_activity(activity_id)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_predecessors(self, repo, mock_session):
        """Should get predecessor dependencies."""
        activity_id = uuid4()
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=activity_id,
            dependency_type=DependencyType.FS,
            lag=0,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [dep]
        mock_session.execute.return_value = mock_result

        result = await repo.get_predecessors(activity_id)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_successors(self, repo, mock_session):
        """Should get successor dependencies."""
        activity_id = uuid4()
        dep = Dependency(
            id=uuid4(),
            predecessor_id=activity_id,
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=0,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [dep]
        mock_session.execute.return_value = mock_result

        result = await repo.get_successors(activity_id)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_dependency_exists_true(self, repo, mock_session):
        """Should return True when dependency exists."""
        dep = Dependency(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=0,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = dep
        mock_session.execute.return_value = mock_result

        result = await repo.dependency_exists(uuid4(), uuid4())

        assert result is True

    @pytest.mark.asyncio
    async def test_dependency_exists_false(self, repo, mock_session):
        """Should return False when dependency doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.dependency_exists(uuid4(), uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_get_by_program_with_activities(self, repo, mock_session):
        """Should get dependencies for program with activities."""
        program_id = uuid4()
        activity_id = uuid4()
        dep = Dependency(
            id=uuid4(),
            predecessor_id=activity_id,
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=0,
        )

        # First call returns activity IDs
        mock_activity_result = MagicMock()
        mock_activity_result.all.return_value = [(activity_id,)]

        # Second call returns dependencies
        mock_dep_result = MagicMock()
        mock_dep_result.scalars.return_value.all.return_value = [dep]

        mock_session.execute.side_effect = [mock_activity_result, mock_dep_result]

        result = await repo.get_by_program(program_id)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_program_no_activities(self, repo, mock_session):
        """Should return empty list when program has no activities."""
        program_id = uuid4()

        # Returns no activity IDs
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_program(program_id)

        assert result == []


class TestProgramRepositoryMethods:
    """Tests for ProgramRepository methods."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ProgramRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_code(self, repo, mock_session):
        """Should get program by code."""
        program = Program(
            id=uuid4(),
            code="PROG-001",
            name="Test Program",
            owner_id=uuid4(),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = program
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_code("PROG-001")

        assert result == program

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(self, repo, mock_session):
        """Should return None when code not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_code("NONEXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_code_exists_true(self, repo, mock_session):
        """Should return True when code exists."""
        program = Program(
            id=uuid4(),
            code="PROG-001",
            name="Test",
            owner_id=uuid4(),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = program
        mock_session.execute.return_value = mock_result

        result = await repo.code_exists("PROG-001")

        assert result is True

    @pytest.mark.asyncio
    async def test_code_exists_false(self, repo, mock_session):
        """Should return False when code doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.code_exists("NONEXISTENT")

        assert result is False

    @pytest.mark.asyncio
    async def test_code_exists_with_exclude_id(self, repo, mock_session):
        """Should exclude specific ID when checking code exists."""
        exclude_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.code_exists("PROG-001", exclude_id=exclude_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_by_owner(self, repo, mock_session):
        """Should get programs by owner."""
        owner_id = uuid4()
        program = Program(
            id=uuid4(),
            code="PROG-001",
            name="Test",
            owner_id=owner_id,
        )

        # Mock count result
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        # Mock programs result
        mock_programs_result = MagicMock()
        mock_programs_result.scalars.return_value.all.return_value = [program]

        mock_session.execute.side_effect = [mock_count_result, mock_programs_result]

        programs, total = await repo.get_by_owner(owner_id)

        assert total == 1
        assert len(programs) == 1

    @pytest.mark.asyncio
    async def test_get_by_owner_with_pagination(self, repo, mock_session):
        """Should paginate get_by_owner results."""
        owner_id = uuid4()

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 100

        mock_programs_result = MagicMock()
        mock_programs_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_programs_result]

        _, total = await repo.get_by_owner(owner_id, skip=20, limit=10)

        assert total == 100

    @pytest.mark.asyncio
    async def test_user_owns_program_true(self, repo, mock_session):
        """Should return True when user owns program."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 1
        mock_session.execute.return_value = mock_result

        result = await repo.user_owns_program(uuid4(), uuid4())

        assert result is True

    @pytest.mark.asyncio
    async def test_user_owns_program_false(self, repo, mock_session):
        """Should return False when user doesn't own program."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        result = await repo.user_owns_program(uuid4(), uuid4())

        assert result is False


class TestWBSModel:
    """Tests for WBSElement model properties."""

    def test_wbs_repr(self):
        """Test WBS element string representation."""
        wbs = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1.1.1",
            name="Work Package",
            path="1.1.1",
        )
        repr_str = repr(wbs)
        assert "WBSElement" in repr_str


class TestProgramModel:
    """Tests for Program model properties."""

    def test_program_repr(self):
        """Test program string representation."""
        program = Program(
            id=uuid4(),
            code="PROG-001",
            name="Test Program",
            owner_id=uuid4(),
            status=ProgramStatus.PLANNING,
        )
        repr_str = repr(program)
        assert "Program" in repr_str
        assert "PROG-001" in repr_str
