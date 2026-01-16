"""Unit tests for ScenarioRepository methods using mocks."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.scenario import (
    ChangeType,
    EntityType,
    Scenario,
    ScenarioChange,
    ScenarioStatus,
)
from src.repositories.scenario import ScenarioRepository


class TestScenarioRepositoryGetWithChanges:
    """Tests for get_with_changes method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ScenarioRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_with_changes_found(self, repo, mock_session):
        """Should return scenario with changes loaded."""
        scenario_id = uuid4()
        scenario = Scenario(
            id=scenario_id,
            program_id=uuid4(),
            name="Test Scenario",
            status=ScenarioStatus.DRAFT,
            created_by_id=uuid4(),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = scenario
        mock_session.execute.return_value = mock_result

        result = await repo.get_with_changes(scenario_id)

        assert result == scenario
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_changes_not_found(self, repo, mock_session):
        """Should return None when scenario not found."""
        scenario_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_with_changes(scenario_id)

        assert result is None


class TestScenarioRepositoryGetByProgram:
    """Tests for get_by_program method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ScenarioRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_program_returns_list(self, repo, mock_session):
        """Should return list of scenarios for a program."""
        program_id = uuid4()
        scenario = Scenario(
            id=uuid4(),
            program_id=program_id,
            name="Test",
            status=ScenarioStatus.DRAFT,
            created_by_id=uuid4(),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [scenario]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_program(program_id)

        assert result == [scenario]

    @pytest.mark.asyncio
    async def test_get_by_program_active_only(self, repo, mock_session):
        """Should filter to active scenarios only."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_by_program(program_id, active_only=True)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_program_include_deleted(self, repo, mock_session):
        """Should include deleted when flag set."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_by_program(program_id, include_deleted=True)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_program_with_pagination(self, repo, mock_session):
        """Should apply skip and limit."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_by_program(program_id, skip=10, limit=50)

        mock_session.execute.assert_called_once()


class TestScenarioRepositoryCountByProgram:
    """Tests for count_by_program method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ScenarioRepository(mock_session)

    @pytest.mark.asyncio
    async def test_count_by_program_returns_count(self, repo, mock_session):
        """Should return count of scenarios."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        result = await repo.count_by_program(program_id)

        assert result == 5

    @pytest.mark.asyncio
    async def test_count_by_program_returns_zero(self, repo, mock_session):
        """Should return 0 when no scenarios."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.count_by_program(program_id)

        assert result == 0

    @pytest.mark.asyncio
    async def test_count_by_program_active_only(self, repo, mock_session):
        """Should count only active scenarios."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute.return_value = mock_result

        result = await repo.count_by_program(program_id, active_only=True)

        assert result == 3


class TestScenarioRepositoryAddChange:
    """Tests for add_change method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ScenarioRepository(mock_session)

    @pytest.mark.asyncio
    async def test_add_change_creates_change(self, repo, mock_session):
        """Should create a new change record."""
        scenario_id = uuid4()
        entity_id = uuid4()
        scenario = Scenario(
            id=scenario_id,
            program_id=uuid4(),
            name="Test",
            status=ScenarioStatus.DRAFT,
            created_by_id=uuid4(),
            results_cache={"data": "test"},
        )

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=scenario):
            result = await repo.add_change(
                scenario_id=scenario_id,
                entity_type="activity",
                entity_id=entity_id,
                change_type="update",
                entity_code="ACT-001",
                field_name="duration",
                old_value=10,
                new_value=15,
            )

        assert result.scenario_id == scenario_id
        assert result.entity_type == "activity"
        assert result.change_type == "update"
        assert result.field_name == "duration"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_change_invalidates_cache(self, repo, mock_session):
        """Should invalidate scenario cache when adding change."""
        scenario_id = uuid4()
        entity_id = uuid4()
        scenario = Scenario(
            id=scenario_id,
            program_id=uuid4(),
            name="Test",
            status=ScenarioStatus.DRAFT,
            created_by_id=uuid4(),
            results_cache={"data": "cached"},
        )

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=scenario):
            await repo.add_change(
                scenario_id=scenario_id,
                entity_type="activity",
                entity_id=entity_id,
                change_type="create",
            )

        assert scenario.results_cache is None


class TestScenarioRepositoryGetChanges:
    """Tests for get_changes method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ScenarioRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_changes_returns_list(self, repo, mock_session):
        """Should return list of changes."""
        scenario_id = uuid4()
        change = ScenarioChange(
            id=uuid4(),
            scenario_id=scenario_id,
            entity_type=EntityType.ACTIVITY,
            entity_id=uuid4(),
            change_type=ChangeType.UPDATE,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [change]
        mock_session.execute.return_value = mock_result

        result = await repo.get_changes(scenario_id)

        assert result == [change]

    @pytest.mark.asyncio
    async def test_get_changes_filter_by_entity_type(self, repo, mock_session):
        """Should filter by entity type when specified."""
        scenario_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_changes(scenario_id, entity_type="activity")

        mock_session.execute.assert_called_once()


class TestScenarioRepositoryGetChangesForEntity:
    """Tests for get_changes_for_entity method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ScenarioRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_changes_for_entity_returns_list(self, repo, mock_session):
        """Should return changes for specific entity."""
        scenario_id = uuid4()
        entity_id = uuid4()
        change = ScenarioChange(
            id=uuid4(),
            scenario_id=scenario_id,
            entity_type=EntityType.ACTIVITY,
            entity_id=entity_id,
            change_type=ChangeType.UPDATE,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [change]
        mock_session.execute.return_value = mock_result

        result = await repo.get_changes_for_entity(scenario_id, entity_id)

        assert result == [change]


class TestScenarioRepositoryRemoveChange:
    """Tests for remove_change method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ScenarioRepository(mock_session)

    @pytest.mark.asyncio
    async def test_remove_change_success(self, repo, mock_session):
        """Should remove change and invalidate cache."""
        change_id = uuid4()
        scenario_id = uuid4()

        change = ScenarioChange(
            id=change_id,
            scenario_id=scenario_id,
            entity_type=EntityType.ACTIVITY,
            entity_id=uuid4(),
            change_type=ChangeType.UPDATE,
        )

        scenario = Scenario(
            id=scenario_id,
            program_id=uuid4(),
            name="Test",
            status=ScenarioStatus.DRAFT,
            created_by_id=uuid4(),
            results_cache={"data": "cached"},
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = change
        mock_session.execute.return_value = mock_result

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=scenario):
            result = await repo.remove_change(change_id)

        assert result is True
        assert scenario.results_cache is None
        mock_session.delete.assert_called_once_with(change)

    @pytest.mark.asyncio
    async def test_remove_change_not_found(self, repo, mock_session):
        """Should return False when change not found."""
        change_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.remove_change(change_id)

        assert result is False


class TestScenarioRepositoryUpdateCache:
    """Tests for update_cache method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ScenarioRepository(mock_session)

    @pytest.mark.asyncio
    async def test_update_cache_success(self, repo, mock_session):
        """Should update cached results."""
        scenario_id = uuid4()
        scenario = Scenario(
            id=scenario_id,
            program_id=uuid4(),
            name="Test",
            status=ScenarioStatus.DRAFT,
            created_by_id=uuid4(),
            results_cache=None,
        )

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=scenario):
            result = await repo.update_cache(
                scenario_id, {"duration": 100, "critical_path": ["A", "B"]}
            )

        assert result.results_cache == {"duration": 100, "critical_path": ["A", "B"]}
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_cache_not_found(self, repo, mock_session):
        """Should return None when scenario not found."""
        scenario_id = uuid4()

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=None):
            result = await repo.update_cache(scenario_id, {"data": "test"})

        assert result is None


class TestScenarioRepositoryMarkPromoted:
    """Tests for mark_promoted method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ScenarioRepository(mock_session)

    @pytest.mark.asyncio
    async def test_mark_promoted_success(self, repo, mock_session):
        """Should mark scenario as promoted."""
        scenario_id = uuid4()
        baseline_id = uuid4()
        scenario = Scenario(
            id=scenario_id,
            program_id=uuid4(),
            name="Test",
            status=ScenarioStatus.DRAFT,
            is_active=True,
            created_by_id=uuid4(),
        )

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=scenario):
            result = await repo.mark_promoted(scenario_id, baseline_id)

        assert result.status == "promoted"
        assert result.promoted_baseline_id == baseline_id
        assert result.is_active is False
        assert result.promoted_at is not None

    @pytest.mark.asyncio
    async def test_mark_promoted_not_found(self, repo, mock_session):
        """Should return None when scenario not found."""
        scenario_id = uuid4()
        baseline_id = uuid4()

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=None):
            result = await repo.mark_promoted(scenario_id, baseline_id)

        assert result is None


class TestScenarioRepositoryArchive:
    """Tests for archive method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ScenarioRepository(mock_session)

    @pytest.mark.asyncio
    async def test_archive_success(self, repo, mock_session):
        """Should archive scenario."""
        scenario_id = uuid4()
        scenario = Scenario(
            id=scenario_id,
            program_id=uuid4(),
            name="Test",
            status=ScenarioStatus.DRAFT,
            is_active=True,
            created_by_id=uuid4(),
        )

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=scenario):
            result = await repo.archive(scenario_id)

        assert result.status == "archived"
        assert result.is_active is False

    @pytest.mark.asyncio
    async def test_archive_not_found(self, repo, mock_session):
        """Should return None when scenario not found."""
        scenario_id = uuid4()

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=None):
            result = await repo.archive(scenario_id)

        assert result is None


class TestScenarioRepositoryBranchFromScenario:
    """Tests for branch_from_scenario method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ScenarioRepository(mock_session)

    @pytest.mark.asyncio
    async def test_branch_from_scenario_success(self, repo, mock_session):
        """Should create branched scenario with copied changes."""
        parent_id = uuid4()
        program_id = uuid4()
        user_id = uuid4()

        parent = Scenario(
            id=parent_id,
            program_id=program_id,
            name="Parent",
            status=ScenarioStatus.DRAFT,
            created_by_id=uuid4(),
        )
        # Add a mock change list
        parent.changes = [
            ScenarioChange(
                id=uuid4(),
                scenario_id=parent_id,
                entity_type=EntityType.ACTIVITY,
                entity_id=uuid4(),
                change_type=ChangeType.UPDATE,
                field_name="duration",
                old_value=10,
                new_value=15,
            )
        ]

        with patch.object(repo, "get_with_changes", new_callable=AsyncMock, return_value=parent):
            result = await repo.branch_from_scenario(
                parent_id, "Branch", "Branched scenario", user_id
            )

        assert result.name == "Branch"
        assert result.description == "Branched scenario"
        assert result.parent_scenario_id == parent_id
        assert result.program_id == program_id
        assert result.status == "draft"
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_branch_from_scenario_parent_not_found(self, repo, mock_session):
        """Should return None when parent not found."""
        parent_id = uuid4()
        user_id = uuid4()

        with patch.object(repo, "get_with_changes", new_callable=AsyncMock, return_value=None):
            result = await repo.branch_from_scenario(parent_id, "Branch", None, user_id)

        assert result is None


class TestScenarioRepositoryGetChangeSummary:
    """Tests for get_change_summary method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ScenarioRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_change_summary_empty(self, repo, mock_session):
        """Should return empty summary when no changes."""
        scenario_id = uuid4()

        with patch.object(repo, "get_changes", new_callable=AsyncMock, return_value=[]):
            result = await repo.get_change_summary(scenario_id)

        assert result["total_changes"] == 0
        assert result["activities_created"] == 0
        assert result["activities_updated"] == 0
        assert result["activities_deleted"] == 0

    @pytest.mark.asyncio
    async def test_get_change_summary_with_changes(self, repo, mock_session):
        """Should return correct summary counts for all change types."""
        scenario_id = uuid4()

        # Use actual entity types - the code now properly pluralizes them
        changes = [
            MagicMock(entity_type="activity", change_type="create"),
            MagicMock(entity_type="activity", change_type="update"),
            MagicMock(entity_type="activity", change_type="update"),
            MagicMock(entity_type="dependency", change_type="create"),
            MagicMock(entity_type="wbs", change_type="delete"),
        ]

        with patch.object(repo, "get_changes", new_callable=AsyncMock, return_value=changes):
            result = await repo.get_change_summary(scenario_id)

        assert result["total_changes"] == 5
        assert result["activities_created"] == 1
        assert result["activities_updated"] == 2
        assert result["dependencies_created"] == 1
        assert result["wbs_deleted"] == 1
