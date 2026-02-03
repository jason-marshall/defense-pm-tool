"""Unit tests for SimulationConfigRepository and SimulationResultRepository."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.simulation import SimulationConfig, SimulationResult, SimulationStatus
from src.repositories.simulation import (
    SimulationConfigRepository,
    SimulationResultRepository,
)


class TestSimulationConfigRepositoryGetByProgram:
    """Tests for get_by_program method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return SimulationConfigRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_program_returns_list(self, repo, mock_session):
        """Should return list of configs for a program."""
        program_id = uuid4()
        config = SimulationConfig(
            id=uuid4(),
            program_id=program_id,
            name="Test Config",
            iterations=1000,
            activity_distributions={},
            created_by_id=uuid4(),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [config]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_program(program_id)

        assert result == [config]

    @pytest.mark.asyncio
    async def test_get_by_program_with_results(self, repo, mock_session):
        """Should eagerly load results when requested."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_by_program(program_id, include_results=True)

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


class TestSimulationConfigRepositoryGetByScenario:
    """Tests for get_by_scenario method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return SimulationConfigRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_scenario_returns_list(self, repo, mock_session):
        """Should return configs for a scenario."""
        scenario_id = uuid4()
        config = SimulationConfig(
            id=uuid4(),
            program_id=uuid4(),
            scenario_id=scenario_id,
            name="Scenario Config",
            iterations=1000,
            activity_distributions={},
            created_by_id=uuid4(),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [config]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_scenario(scenario_id)

        assert result == [config]


class TestSimulationConfigRepositoryGetWithResults:
    """Tests for get_with_results method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return SimulationConfigRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_with_results_found(self, repo, mock_session):
        """Should return config with results."""
        config_id = uuid4()
        config = SimulationConfig(
            id=config_id,
            program_id=uuid4(),
            name="Test",
            iterations=100,
            activity_distributions={},
            created_by_id=uuid4(),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        result = await repo.get_with_results(config_id)

        assert result == config

    @pytest.mark.asyncio
    async def test_get_with_results_not_found(self, repo, mock_session):
        """Should return None when config not found."""
        config_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_with_results(config_id)

        assert result is None


class TestSimulationConfigRepositoryCreateConfig:
    """Tests for create_config method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        # add/expire are synchronous methods in AsyncSession
        session.add = MagicMock()
        session.expire = MagicMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return SimulationConfigRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_config_basic(self, repo, mock_session):
        """Should create a basic config."""
        program_id = uuid4()
        user_id = uuid4()

        result = await repo.create_config(
            program_id=program_id,
            name="Test Config",
            created_by_id=user_id,
        )

        assert result.program_id == program_id
        assert result.name == "Test Config"
        assert result.iterations == 1000
        assert result.activity_distributions == {}
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_config_with_all_options(self, repo, mock_session):
        """Should create config with all options."""
        program_id = uuid4()
        user_id = uuid4()
        scenario_id = uuid4()
        activity_id = str(uuid4())

        result = await repo.create_config(
            program_id=program_id,
            name="Full Config",
            created_by_id=user_id,
            iterations=5000,
            activity_distributions={
                activity_id: {"distribution": "triangular", "min": 5, "mode": 10, "max": 15}
            },
            cost_distributions={activity_id: {"distribution": "normal", "mean": 1000, "std": 100}},
            scenario_id=scenario_id,
            description="Test description",
        )

        assert result.iterations == 5000
        assert result.scenario_id == scenario_id
        assert result.description == "Test description"
        assert activity_id in result.activity_distributions


class TestSimulationResultRepositoryGetByConfig:
    """Tests for get_by_config method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return SimulationResultRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_config_returns_list(self, repo, mock_session):
        """Should return results for a config."""
        config_id = uuid4()
        sim_result = SimulationResult(
            id=uuid4(),
            config_id=config_id,
            status=SimulationStatus.COMPLETED,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sim_result]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_config(config_id)

        assert result == [sim_result]


class TestSimulationResultRepositoryGetLatestByConfig:
    """Tests for get_latest_by_config method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return SimulationResultRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_latest_by_config_found(self, repo, mock_session):
        """Should return latest result."""
        config_id = uuid4()
        sim_result = SimulationResult(
            id=uuid4(),
            config_id=config_id,
            status=SimulationStatus.COMPLETED,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sim_result
        mock_session.execute.return_value = mock_result

        result = await repo.get_latest_by_config(config_id)

        assert result == sim_result

    @pytest.mark.asyncio
    async def test_get_latest_by_config_not_found(self, repo, mock_session):
        """Should return None when no results."""
        config_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_latest_by_config(config_id)

        assert result is None


class TestSimulationResultRepositoryGetCompletedByConfig:
    """Tests for get_completed_by_config method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return SimulationResultRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_completed_by_config_found(self, repo, mock_session):
        """Should return completed result."""
        config_id = uuid4()
        sim_result = SimulationResult(
            id=uuid4(),
            config_id=config_id,
            status=SimulationStatus.COMPLETED,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sim_result
        mock_session.execute.return_value = mock_result

        result = await repo.get_completed_by_config(config_id)

        assert result == sim_result
        assert result.status == SimulationStatus.COMPLETED


class TestSimulationResultRepositoryCreateResult:
    """Tests for create_result method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        # add/expire are synchronous methods in AsyncSession
        session.add = MagicMock()
        session.expire = MagicMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return SimulationResultRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_result_basic(self, repo, mock_session):
        """Should create a pending result."""
        config_id = uuid4()

        result = await repo.create_result(config_id)

        assert result.config_id == config_id
        assert result.status == SimulationStatus.PENDING
        assert result.random_seed is None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_result_with_seed(self, repo, mock_session):
        """Should create result with random seed."""
        config_id = uuid4()

        result = await repo.create_result(config_id, seed=12345)

        assert result.random_seed == 12345


class TestSimulationResultRepositoryMarkRunning:
    """Tests for mark_running method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return SimulationResultRepository(mock_session)

    @pytest.mark.asyncio
    async def test_mark_running_success(self, repo, mock_session):
        """Should mark result as running."""
        result_id = uuid4()
        sim_result = SimulationResult(
            id=result_id,
            config_id=uuid4(),
            status=SimulationStatus.PENDING,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sim_result
        mock_session.execute.return_value = mock_result

        result = await repo.mark_running(result_id)

        assert result.status == SimulationStatus.RUNNING
        assert result.started_at is not None

    @pytest.mark.asyncio
    async def test_mark_running_not_found(self, repo, mock_session):
        """Should return None when result not found."""
        result_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.mark_running(result_id)

        assert result is None


class TestSimulationResultRepositoryMarkCompleted:
    """Tests for mark_completed method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        # add/expire are synchronous methods in AsyncSession
        session.add = MagicMock()
        session.expire = MagicMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return SimulationResultRepository(mock_session)

    @pytest.mark.asyncio
    async def test_mark_completed_success(self, repo, mock_session):
        """Should mark result as completed with data."""
        result_id = uuid4()
        sim_result = SimulationResult(
            id=result_id,
            config_id=uuid4(),
            status=SimulationStatus.RUNNING,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sim_result
        mock_session.execute.return_value = mock_result

        duration_results = {"p50": 10.5, "p90": 15.2}
        cost_results = {"p50": 5000.0, "p90": 7500.0}

        result = await repo.mark_completed(
            result_id=result_id,
            duration_results=duration_results,
            cost_results=cost_results,
            duration_histogram={"bins": [5, 10, 15], "counts": [10, 50, 40]},
            cost_histogram=None,
            activity_results=None,
            iterations_completed=100,
        )

        assert result.status == SimulationStatus.COMPLETED
        assert result.completed_at is not None
        assert result.duration_results == duration_results
        assert result.cost_results == cost_results
        assert result.iterations_completed == 100

    @pytest.mark.asyncio
    async def test_mark_completed_not_found(self, repo, mock_session):
        """Should return None when result not found."""
        result_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.mark_completed(
            result_id=result_id,
            duration_results={},
            cost_results=None,
            duration_histogram=None,
            cost_histogram=None,
            activity_results=None,
            iterations_completed=0,
        )

        assert result is None


class TestSimulationResultRepositoryMarkFailed:
    """Tests for mark_failed method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        # add/expire are synchronous methods in AsyncSession
        session.add = MagicMock()
        session.expire = MagicMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return SimulationResultRepository(mock_session)

    @pytest.mark.asyncio
    async def test_mark_failed_success(self, repo, mock_session):
        """Should mark result as failed with error message."""
        result_id = uuid4()
        sim_result = SimulationResult(
            id=result_id,
            config_id=uuid4(),
            status=SimulationStatus.RUNNING,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sim_result
        mock_session.execute.return_value = mock_result

        result = await repo.mark_failed(result_id, "Simulation error occurred")

        assert result.status == SimulationStatus.FAILED
        assert result.completed_at is not None
        assert result.error_message == "Simulation error occurred"

    @pytest.mark.asyncio
    async def test_mark_failed_not_found(self, repo, mock_session):
        """Should return None when result not found."""
        result_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.mark_failed(result_id, "Error")

        assert result is None


class TestSimulationResultRepositoryUpdateProgress:
    """Tests for update_progress method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return SimulationResultRepository(mock_session)

    @pytest.mark.asyncio
    async def test_update_progress_success(self, repo, mock_session):
        """Should update iterations completed."""
        result_id = uuid4()
        sim_result = SimulationResult(
            id=result_id,
            config_id=uuid4(),
            status=SimulationStatus.RUNNING,
            iterations_completed=0,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sim_result
        mock_session.execute.return_value = mock_result

        result = await repo.update_progress(result_id, 500)

        assert result.iterations_completed == 500

    @pytest.mark.asyncio
    async def test_update_progress_not_found(self, repo, mock_session):
        """Should return None when result not found."""
        result_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.update_progress(result_id, 100)

        assert result is None
