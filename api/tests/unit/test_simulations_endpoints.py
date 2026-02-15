"""Unit tests for Monte Carlo simulation endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest
from fastapi import HTTPException

from src.api.v1.endpoints.simulations import (
    create_simulation_config,
    delete_simulation_config,
    get_simulation_config,
    get_simulation_result,
    get_tornado_chart,
    list_simulation_configs,
    list_simulation_results,
    quick_simulation,
    run_network_simulation,
    run_simulation,
    update_simulation_config,
)
from src.core.exceptions import AuthorizationError, NotFoundError
from src.models.simulation import SimulationStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_user(*, is_admin: bool = False) -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.is_admin = is_admin
    return user


def _make_mock_program(owner_id=None) -> MagicMock:
    program = MagicMock()
    program.id = uuid4()
    program.owner_id = owner_id or uuid4()
    return program


def _make_mock_config(program_id=None, created_by_id=None) -> MagicMock:
    config = MagicMock()
    config.id = uuid4()
    config.program_id = program_id or uuid4()
    config.scenario_id = None
    config.name = "Risk Analysis Config"
    config.description = "Test simulation"
    config.iterations = 1000
    act_id = str(uuid4())
    config.activity_distributions = {
        act_id: {"distribution": "triangular", "min": 5, "mode": 10, "max": 20}
    }
    config.cost_distributions = None
    config.created_by_id = created_by_id or uuid4()
    config.created_at = datetime.now(UTC)
    config.activity_count = 1
    return config


def _make_mock_result(config_id=None) -> MagicMock:
    result = MagicMock()
    result.id = uuid4()
    result.config_id = config_id or uuid4()
    result.status = SimulationStatus.COMPLETED
    result.started_at = datetime.now(UTC)
    result.completed_at = datetime.now(UTC)
    result.iterations_completed = 1000
    result.duration_results = {
        "p10": 110.0,
        "p50": 145.0,
        "p80": 165.0,
        "p90": 180.0,
        "mean": 147.5,
        "std": 22.3,
        "min": 95.0,
        "max": 210.0,
    }
    result.cost_results = None
    result.duration_histogram = {
        "bins": [100.0, 120.0, 140.0, 160.0, 180.0, 200.0],
        "counts": [50, 200, 400, 250, 100],
    }
    result.cost_histogram = None
    result.activity_results = None
    result.error_message = None
    result.random_seed = 42
    result.duration_seconds = 1.5
    result.created_at = datetime.now(UTC)
    return result


def _make_mock_simulation_output() -> MagicMock:
    """Create a mock MonteCarloEngine SimulationOutput."""
    output = MagicMock()
    output.duration_p10 = 110.0
    output.duration_p50 = 145.0
    output.duration_p80 = 165.0
    output.duration_p90 = 180.0
    output.duration_mean = 147.5
    output.duration_std = 22.3
    output.duration_min = 95.0
    output.duration_max = 210.0
    output.cost_p50 = None
    output.cost_p10 = None
    output.cost_p80 = None
    output.cost_p90 = None
    output.cost_mean = None
    output.cost_std = None
    output.cost_min = None
    output.cost_max = None
    output.iterations = 1000
    output.elapsed_seconds = 1.5
    output.seed = 42
    output.activity_stats = None
    # numpy arrays with .tolist()
    output.duration_histogram_bins = np.array([100.0, 120.0, 140.0, 160.0, 180.0, 200.0])
    output.duration_histogram_counts = np.array([50, 200, 400, 250, 100])
    output.cost_histogram_bins = None
    output.cost_histogram_counts = None
    return output


def _make_mock_network_output() -> MagicMock:
    """Create a mock OptimizedNetworkMonteCarloEngine output."""
    act_id = uuid4()
    output = MagicMock()
    output.project_duration_p10 = 110.0
    output.project_duration_p50 = 145.0
    output.project_duration_p80 = 165.0
    output.project_duration_p90 = 180.0
    output.project_duration_mean = 147.5
    output.project_duration_std = 22.3
    output.project_duration_min = 95.0
    output.project_duration_max = 210.0
    output.activity_criticality = {act_id: 0.85}
    output.sensitivity = {act_id: 0.72}
    # Use empty dict so no finish_distribution sub-dict is added to activity_stats,
    # which avoids Pydantic validation errors (schema expects dict[str, float] leaves).
    output.activity_finish_distributions = {}
    output.iterations = 1000
    output.elapsed_seconds = 3.1
    output.duration_histogram_bins = np.array([100.0, 120.0, 140.0, 160.0, 180.0, 200.0])
    output.duration_histogram_counts = np.array([50, 200, 400, 250, 100])
    return output


# ===========================================================================
# list_simulation_configs
# ===========================================================================


class TestListSimulationConfigs:
    """Tests for list_simulation_configs endpoint."""

    @pytest.mark.asyncio
    async def test_list_configs_success(self):
        """Should return list of configs for a program."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program_id = uuid4()

        config1 = _make_mock_config(program_id=program_id)
        config2 = _make_mock_config(program_id=program_id)

        with patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_by_program = AsyncMock(return_value=[config1, config2])
            MockRepo.return_value = mock_repo

            result = await list_simulation_configs(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
                page=1,
                page_size=20,
            )

            assert len(result) == 2
            assert result[0].id == config1.id
            assert result[1].id == config2.id
            mock_repo.get_by_program.assert_called_once_with(
                program_id=program_id, skip=0, limit=20
            )

    @pytest.mark.asyncio
    async def test_list_configs_pagination(self):
        """Should apply pagination offset correctly."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program_id = uuid4()

        with patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_by_program = AsyncMock(return_value=[])
            MockRepo.return_value = mock_repo

            result = await list_simulation_configs(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
                page=3,
                page_size=10,
            )

            assert result == []
            mock_repo.get_by_program.assert_called_once_with(
                program_id=program_id, skip=20, limit=10
            )


# ===========================================================================
# create_simulation_config
# ===========================================================================


class TestCreateSimulationConfig:
    """Tests for create_simulation_config endpoint."""

    @pytest.mark.asyncio
    async def test_create_config_success(self):
        """Should create simulation config successfully."""
        from src.schemas.simulation import (
            DistributionParamsSchema,
            SimulationConfigCreate,
        )

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program = _make_mock_program(owner_id=mock_user.id)
        created_config = _make_mock_config(program_id=program.id, created_by_id=mock_user.id)

        act_id = str(uuid4())
        config_data = SimulationConfigCreate(
            program_id=program.id,
            name="Test Config",
            iterations=1000,
            activity_distributions={
                act_id: DistributionParamsSchema(
                    distribution="triangular", min_value=5, mode=10, max_value=20
                )
            },
        )

        with (
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            mock_config_repo = MagicMock()
            mock_config_repo.create_config = AsyncMock(return_value=created_config)
            MockConfigRepo.return_value = mock_config_repo

            result = await create_simulation_config(
                db=mock_db, current_user=mock_user, config_data=config_data
            )

            assert result.id == created_config.id
            assert result.name == created_config.name
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_config_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        from src.schemas.simulation import (
            DistributionParamsSchema,
            SimulationConfigCreate,
        )

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program_id = uuid4()

        config_data = SimulationConfigCreate(
            program_id=program_id,
            name="Test Config",
            iterations=1000,
            activity_distributions={
                str(uuid4()): DistributionParamsSchema(
                    distribution="triangular", min_value=5, mode=10, max_value=20
                )
            },
        )

        with patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            MockProgRepo.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_simulation_config(
                    db=mock_db, current_user=mock_user, config_data=config_data
                )

            assert "PROGRAM_NOT_FOUND" in str(exc_info.value.code)

    @pytest.mark.asyncio
    async def test_create_config_auth_denied(self):
        """Should raise AuthorizationError when user is not program owner."""
        from src.schemas.simulation import (
            DistributionParamsSchema,
            SimulationConfigCreate,
        )

        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)
        program = _make_mock_program()  # owner_id differs from mock_user.id

        config_data = SimulationConfigCreate(
            program_id=program.id,
            name="Test Config",
            iterations=1000,
            activity_distributions={
                str(uuid4()): DistributionParamsSchema(
                    distribution="triangular", min_value=5, mode=10, max_value=20
                )
            },
        )

        with patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError):
                await create_simulation_config(
                    db=mock_db, current_user=mock_user, config_data=config_data
                )

    @pytest.mark.asyncio
    async def test_create_config_with_cost_distributions(self):
        """Should create config with cost distributions included."""
        from src.schemas.simulation import (
            DistributionParamsSchema,
            SimulationConfigCreate,
        )

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program = _make_mock_program(owner_id=mock_user.id)
        created_config = _make_mock_config(program_id=program.id, created_by_id=mock_user.id)
        created_config.cost_distributions = {
            str(uuid4()): {"distribution": "normal", "mean": 5000, "std": 500}
        }

        act_id = str(uuid4())
        config_data = SimulationConfigCreate(
            program_id=program.id,
            name="Cost Risk Config",
            iterations=2000,
            activity_distributions={
                act_id: DistributionParamsSchema(
                    distribution="triangular", min_value=5, mode=10, max_value=20
                )
            },
            cost_distributions={
                act_id: DistributionParamsSchema(distribution="normal", mean=5000, std=500)
            },
        )

        with (
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            mock_config_repo = MagicMock()
            mock_config_repo.create_config = AsyncMock(return_value=created_config)
            MockConfigRepo.return_value = mock_config_repo

            result = await create_simulation_config(
                db=mock_db, current_user=mock_user, config_data=config_data
            )

            assert result.cost_distributions is not None
            # Verify cost_dists was passed (not None) to create_config
            call_kwargs = mock_config_repo.create_config.call_args
            assert call_kwargs.kwargs.get("cost_distributions") is not None


# ===========================================================================
# quick_simulation
# ===========================================================================


class TestQuickSimulation:
    """Tests for quick_simulation endpoint."""

    @pytest.mark.asyncio
    async def test_quick_simulation_success(self):
        """Should run quick simulation and return results."""
        from src.schemas.simulation import (
            DistributionParamsSchema,
            QuickSimulationRequest,
        )

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program = _make_mock_program(owner_id=mock_user.id)
        mock_output = _make_mock_simulation_output()

        act_id = str(uuid4())
        request = QuickSimulationRequest(
            program_id=program.id,
            activity_distributions={
                act_id: DistributionParamsSchema(
                    distribution="triangular", min_value=5, mode=10, max_value=20
                )
            },
            iterations=500,
            seed=42,
        )

        with (
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
            patch("src.api.v1.endpoints.simulations.MonteCarloEngine") as MockEngine,
            patch("src.api.v1.endpoints.simulations.parse_distribution_params"),
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            mock_engine_instance = MagicMock()
            mock_engine_instance.simulate.return_value = mock_output
            MockEngine.return_value = mock_engine_instance

            result = await quick_simulation(db=mock_db, current_user=mock_user, request=request)

            assert result.status == SimulationStatus.COMPLETED
            assert result.duration_results is not None
            assert result.duration_results.p50 == 145.0
            assert result.iterations_completed == 1000
            assert result.progress_percent == 100.0

    @pytest.mark.asyncio
    async def test_quick_simulation_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        from src.schemas.simulation import (
            DistributionParamsSchema,
            QuickSimulationRequest,
        )

        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        request = QuickSimulationRequest(
            program_id=uuid4(),
            activity_distributions={
                str(uuid4()): DistributionParamsSchema(
                    distribution="triangular", min_value=5, mode=10, max_value=20
                )
            },
            iterations=500,
        )

        with patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            MockProgRepo.return_value = mock_prog_repo

            with pytest.raises(NotFoundError):
                await quick_simulation(db=mock_db, current_user=mock_user, request=request)

    @pytest.mark.asyncio
    async def test_quick_simulation_auth_denied(self):
        """Should raise AuthorizationError when user has no access."""
        from src.schemas.simulation import (
            DistributionParamsSchema,
            QuickSimulationRequest,
        )

        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)
        program = _make_mock_program()  # Different owner

        request = QuickSimulationRequest(
            program_id=program.id,
            activity_distributions={
                str(uuid4()): DistributionParamsSchema(
                    distribution="triangular", min_value=5, mode=10, max_value=20
                )
            },
            iterations=500,
        )

        with patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError):
                await quick_simulation(db=mock_db, current_user=mock_user, request=request)

    @pytest.mark.asyncio
    async def test_quick_simulation_failure_returns_500(self):
        """Should raise HTTPException 500 when simulation engine fails."""
        from src.schemas.simulation import (
            DistributionParamsSchema,
            QuickSimulationRequest,
        )

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program = _make_mock_program(owner_id=mock_user.id)

        request = QuickSimulationRequest(
            program_id=program.id,
            activity_distributions={
                str(uuid4()): DistributionParamsSchema(
                    distribution="triangular", min_value=5, mode=10, max_value=20
                )
            },
            iterations=500,
        )

        with (
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
            patch("src.api.v1.endpoints.simulations.MonteCarloEngine") as MockEngine,
            patch("src.api.v1.endpoints.simulations.parse_distribution_params"),
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            mock_engine_instance = MagicMock()
            mock_engine_instance.simulate.side_effect = RuntimeError("Engine exploded")
            MockEngine.return_value = mock_engine_instance

            with pytest.raises(HTTPException) as exc_info:
                await quick_simulation(db=mock_db, current_user=mock_user, request=request)

            assert exc_info.value.status_code == 500
            assert "Simulation failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_quick_simulation_with_cost_distributions(self):
        """Should include cost results when cost distributions are provided."""
        from src.schemas.simulation import (
            DistributionParamsSchema,
            QuickSimulationRequest,
        )

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program = _make_mock_program(owner_id=mock_user.id)
        mock_output = _make_mock_simulation_output()
        # Enable cost results on the output
        mock_output.cost_p50 = 50000.0
        mock_output.cost_p10 = 45000.0
        mock_output.cost_p80 = 55000.0
        mock_output.cost_p90 = 58000.0
        mock_output.cost_mean = 50500.0
        mock_output.cost_std = 3000.0
        mock_output.cost_min = 40000.0
        mock_output.cost_max = 65000.0

        act_id = str(uuid4())
        request = QuickSimulationRequest(
            program_id=program.id,
            activity_distributions={
                act_id: DistributionParamsSchema(
                    distribution="triangular", min_value=5, mode=10, max_value=20
                )
            },
            cost_distributions={
                act_id: DistributionParamsSchema(distribution="normal", mean=5000, std=500)
            },
            iterations=500,
        )

        with (
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
            patch("src.api.v1.endpoints.simulations.MonteCarloEngine") as MockEngine,
            patch("src.api.v1.endpoints.simulations.parse_distribution_params"),
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            mock_engine_instance = MagicMock()
            mock_engine_instance.simulate.return_value = mock_output
            MockEngine.return_value = mock_engine_instance

            result = await quick_simulation(db=mock_db, current_user=mock_user, request=request)

            assert result.cost_results is not None
            assert result.cost_results.p50 == 50000.0


# ===========================================================================
# get_simulation_config
# ===========================================================================


class TestGetSimulationConfig:
    """Tests for get_simulation_config endpoint."""

    @pytest.mark.asyncio
    async def test_get_config_success(self):
        """Should return simulation config by ID."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config = _make_mock_config()

        with patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_with_results = AsyncMock(return_value=config)
            MockRepo.return_value = mock_repo

            result = await get_simulation_config(
                db=mock_db, current_user=mock_user, config_id=config.id
            )

            assert result.id == config.id
            assert result.name == config.name

    @pytest.mark.asyncio
    async def test_get_config_not_found(self):
        """Should raise NotFoundError when config does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config_id = uuid4()

        with patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_with_results = AsyncMock(return_value=None)
            MockRepo.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_simulation_config(db=mock_db, current_user=mock_user, config_id=config_id)

            assert "SIMULATION_CONFIG_NOT_FOUND" in str(exc_info.value.code)


# ===========================================================================
# update_simulation_config
# ===========================================================================


class TestUpdateSimulationConfig:
    """Tests for update_simulation_config endpoint."""

    @pytest.mark.asyncio
    async def test_update_config_success(self):
        """Should update simulation config fields."""
        from src.schemas.simulation import SimulationConfigUpdate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program = _make_mock_program(owner_id=mock_user.id)
        config = _make_mock_config(program_id=program.id)

        update_data = SimulationConfigUpdate(name="Updated Name")

        with (
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
            patch("src.api.v1.endpoints.simulations.simulation_cache") as mock_cache,
        ):
            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            mock_cache.is_available = False

            result = await update_simulation_config(
                db=mock_db,
                current_user=mock_user,
                config_id=config.id,
                update_data=update_data,
            )

            assert result.id == config.id
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_config_not_found(self):
        """Should raise NotFoundError when config does not exist."""
        from src.schemas.simulation import SimulationConfigUpdate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config_id = uuid4()
        update_data = SimulationConfigUpdate(name="Updated")

        with patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            MockRepo.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await update_simulation_config(
                    db=mock_db,
                    current_user=mock_user,
                    config_id=config_id,
                    update_data=update_data,
                )

            assert "SIMULATION_CONFIG_NOT_FOUND" in str(exc_info.value.code)

    @pytest.mark.asyncio
    async def test_update_config_auth_denied(self):
        """Should raise AuthorizationError when user is not owner."""
        from src.schemas.simulation import SimulationConfigUpdate

        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)
        program = _make_mock_program()  # Different owner
        config = _make_mock_config(program_id=program.id)

        update_data = SimulationConfigUpdate(name="Updated")

        with (
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
        ):
            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError):
                await update_simulation_config(
                    db=mock_db,
                    current_user=mock_user,
                    config_id=config.id,
                    update_data=update_data,
                )

    @pytest.mark.asyncio
    async def test_update_config_cache_invalidation(self):
        """Should invalidate cache when iterations change."""
        from src.schemas.simulation import SimulationConfigUpdate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program = _make_mock_program(owner_id=mock_user.id)
        config = _make_mock_config(program_id=program.id)

        update_data = SimulationConfigUpdate(iterations=5000)

        with (
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
            patch("src.api.v1.endpoints.simulations.simulation_cache") as mock_cache,
        ):
            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            mock_cache.is_available = True
            mock_cache.invalidate_config = AsyncMock()

            await update_simulation_config(
                db=mock_db,
                current_user=mock_user,
                config_id=config.id,
                update_data=update_data,
            )

            mock_cache.invalidate_config.assert_called_once_with(config.id)


# ===========================================================================
# delete_simulation_config
# ===========================================================================


class TestDeleteSimulationConfig:
    """Tests for delete_simulation_config endpoint."""

    @pytest.mark.asyncio
    async def test_delete_config_success(self):
        """Should delete simulation config and commit."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program = _make_mock_program(owner_id=mock_user.id)
        config = _make_mock_config(program_id=program.id)

        with (
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
            patch("src.api.v1.endpoints.simulations.simulation_cache") as mock_cache,
        ):
            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            mock_config_repo.delete = AsyncMock()
            MockConfigRepo.return_value = mock_config_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            mock_cache.is_available = False

            result = await delete_simulation_config(
                db=mock_db, current_user=mock_user, config_id=config.id
            )

            assert result is None
            mock_config_repo.delete.assert_called_once_with(config.id)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_config_not_found(self):
        """Should raise NotFoundError when config does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config_id = uuid4()

        with patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            MockRepo.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await delete_simulation_config(
                    db=mock_db, current_user=mock_user, config_id=config_id
                )

            assert "SIMULATION_CONFIG_NOT_FOUND" in str(exc_info.value.code)

    @pytest.mark.asyncio
    async def test_delete_config_auth_denied(self):
        """Should raise AuthorizationError when user is not owner."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)
        program = _make_mock_program()  # Different owner
        config = _make_mock_config(program_id=program.id)

        with (
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
        ):
            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError):
                await delete_simulation_config(
                    db=mock_db, current_user=mock_user, config_id=config.id
                )

    @pytest.mark.asyncio
    async def test_delete_config_cache_invalidation(self):
        """Should invalidate cache when config is deleted."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program = _make_mock_program(owner_id=mock_user.id)
        config = _make_mock_config(program_id=program.id)

        with (
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
            patch("src.api.v1.endpoints.simulations.simulation_cache") as mock_cache,
        ):
            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            mock_config_repo.delete = AsyncMock()
            MockConfigRepo.return_value = mock_config_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            mock_cache.is_available = True
            mock_cache.invalidate_config = AsyncMock()

            await delete_simulation_config(db=mock_db, current_user=mock_user, config_id=config.id)

            mock_cache.invalidate_config.assert_called_once_with(config.id)


# ===========================================================================
# run_simulation
# ===========================================================================


class TestRunSimulation:
    """Tests for run_simulation endpoint."""

    @pytest.mark.asyncio
    async def test_run_simulation_success(self):
        """Should execute simulation and return results."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config = _make_mock_config()
        mock_output = _make_mock_simulation_output()

        mock_result = _make_mock_result(config_id=config.id)
        mock_completed_result = _make_mock_result(config_id=config.id)

        with (
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.SimulationResultRepository") as MockResultRepo,
            patch("src.api.v1.endpoints.simulations.MonteCarloEngine") as MockEngine,
            patch("src.api.v1.endpoints.simulations.parse_distribution_params"),
        ):
            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_result_repo = MagicMock()
            mock_result_repo.create_result = AsyncMock(return_value=mock_result)
            mock_result_repo.mark_running = AsyncMock()
            mock_result_repo.mark_completed = AsyncMock(return_value=mock_completed_result)
            MockResultRepo.return_value = mock_result_repo

            mock_engine_instance = MagicMock()
            mock_engine_instance.simulate.return_value = mock_output
            MockEngine.return_value = mock_engine_instance

            result = await run_simulation(
                db=mock_db,
                current_user=mock_user,
                config_id=config.id,
                run_request=None,
            )

            assert result.id == mock_completed_result.id
            assert result.status == SimulationStatus.COMPLETED
            assert result.progress_percent == 100.0
            mock_result_repo.mark_running.assert_called_once_with(mock_result.id)

    @pytest.mark.asyncio
    async def test_run_simulation_config_not_found(self):
        """Should raise NotFoundError when config does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config_id = uuid4()

        with patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            MockRepo.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await run_simulation(
                    db=mock_db,
                    current_user=mock_user,
                    config_id=config_id,
                    run_request=None,
                )

            assert "SIMULATION_CONFIG_NOT_FOUND" in str(exc_info.value.code)

    @pytest.mark.asyncio
    async def test_run_simulation_engine_failure(self):
        """Should mark result as failed and raise HTTPException on engine error."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config = _make_mock_config()
        mock_result = _make_mock_result(config_id=config.id)

        with (
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.SimulationResultRepository") as MockResultRepo,
            patch("src.api.v1.endpoints.simulations.MonteCarloEngine") as MockEngine,
            patch("src.api.v1.endpoints.simulations.parse_distribution_params"),
        ):
            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_result_repo = MagicMock()
            mock_result_repo.create_result = AsyncMock(return_value=mock_result)
            mock_result_repo.mark_running = AsyncMock()
            mock_result_repo.mark_failed = AsyncMock()
            MockResultRepo.return_value = mock_result_repo

            mock_engine_instance = MagicMock()
            mock_engine_instance.simulate.side_effect = RuntimeError("Computation error")
            MockEngine.return_value = mock_engine_instance

            with pytest.raises(HTTPException) as exc_info:
                await run_simulation(
                    db=mock_db,
                    current_user=mock_user,
                    config_id=config.id,
                    run_request=None,
                )

            assert exc_info.value.status_code == 500
            mock_result_repo.mark_failed.assert_called_once()


# ===========================================================================
# run_network_simulation
# ===========================================================================


class TestRunNetworkSimulation:
    """Tests for run_network_simulation endpoint."""

    @pytest.mark.asyncio
    async def test_run_network_simulation_success(self):
        """Should execute network simulation and return results."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program = _make_mock_program(owner_id=mock_user.id)
        config = _make_mock_config(program_id=program.id)
        mock_output = _make_mock_network_output()

        mock_result = _make_mock_result(config_id=config.id)
        mock_completed = _make_mock_result(config_id=config.id)

        mock_activity = MagicMock()
        mock_activity.id = uuid4()
        mock_activity.duration = 10

        mock_dependency = MagicMock()
        mock_dependency.predecessor_id = mock_activity.id
        mock_dependency.successor_id = uuid4()

        with (
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
            patch("src.api.v1.endpoints.simulations.SimulationResultRepository") as MockResultRepo,
            patch("src.api.v1.endpoints.simulations.ActivityRepository") as MockActRepo,
            patch("src.api.v1.endpoints.simulations.DependencyRepository") as MockDepRepo,
            patch(
                "src.api.v1.endpoints.simulations.OptimizedNetworkMonteCarloEngine"
            ) as MockEngine,
            patch("src.api.v1.endpoints.simulations.parse_distribution_params"),
        ):
            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            mock_result_repo = MagicMock()
            mock_result_repo.create_result = AsyncMock(return_value=mock_result)
            mock_result_repo.mark_running = AsyncMock()
            mock_result_repo.mark_completed = AsyncMock(return_value=mock_completed)
            mock_result_repo.mark_failed = AsyncMock()
            MockResultRepo.return_value = mock_result_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=[mock_activity])
            MockActRepo.return_value = mock_act_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_program = AsyncMock(return_value=[mock_dependency])
            MockDepRepo.return_value = mock_dep_repo

            mock_engine_instance = MagicMock()
            mock_engine_instance.simulate.return_value = mock_output
            MockEngine.return_value = mock_engine_instance

            result = await run_network_simulation(
                db=mock_db,
                current_user=mock_user,
                config_id=config.id,
                run_request=None,
            )

            assert result.id == mock_completed.id
            assert result.status == SimulationStatus.COMPLETED
            assert result.progress_percent == 100.0

    @pytest.mark.asyncio
    async def test_run_network_simulation_config_not_found(self):
        """Should raise NotFoundError when config does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config_id = uuid4()

        with patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            MockRepo.return_value = mock_repo

            with pytest.raises(NotFoundError):
                await run_network_simulation(
                    db=mock_db,
                    current_user=mock_user,
                    config_id=config_id,
                    run_request=None,
                )

    @pytest.mark.asyncio
    async def test_run_network_simulation_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config = _make_mock_config()

        with (
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
        ):
            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            MockProgRepo.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await run_network_simulation(
                    db=mock_db,
                    current_user=mock_user,
                    config_id=config.id,
                    run_request=None,
                )

            assert "PROGRAM_NOT_FOUND" in str(exc_info.value.code)

    @pytest.mark.asyncio
    async def test_run_network_simulation_auth_denied(self):
        """Should raise AuthorizationError when user has no access."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)
        program = _make_mock_program()  # Different owner
        config = _make_mock_config(program_id=program.id)

        with (
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
        ):
            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError):
                await run_network_simulation(
                    db=mock_db,
                    current_user=mock_user,
                    config_id=config.id,
                    run_request=None,
                )

    @pytest.mark.asyncio
    async def test_run_network_simulation_no_activities(self):
        """Should raise HTTPException 400 when program has no activities."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program = _make_mock_program(owner_id=mock_user.id)
        config = _make_mock_config(program_id=program.id)
        mock_result = _make_mock_result(config_id=config.id)

        with (
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
            patch("src.api.v1.endpoints.simulations.SimulationResultRepository") as MockResultRepo,
            patch("src.api.v1.endpoints.simulations.ActivityRepository") as MockActRepo,
            patch("src.api.v1.endpoints.simulations.DependencyRepository") as MockDepRepo,
        ):
            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            mock_result_repo = MagicMock()
            mock_result_repo.create_result = AsyncMock(return_value=mock_result)
            mock_result_repo.mark_running = AsyncMock()
            mock_result_repo.mark_failed = AsyncMock()
            MockResultRepo.return_value = mock_result_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=[])
            MockActRepo.return_value = mock_act_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_program = AsyncMock(return_value=[])
            MockDepRepo.return_value = mock_dep_repo

            with pytest.raises(HTTPException) as exc_info:
                await run_network_simulation(
                    db=mock_db,
                    current_user=mock_user,
                    config_id=config.id,
                    run_request=None,
                )

            assert exc_info.value.status_code == 400
            assert "No activities found" in exc_info.value.detail


# ===========================================================================
# list_simulation_results
# ===========================================================================


class TestListSimulationResults:
    """Tests for list_simulation_results endpoint."""

    @pytest.mark.asyncio
    async def test_list_results_success(self):
        """Should return list of simulation results for a config."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config = _make_mock_config()
        config.iterations = 1000

        result1 = _make_mock_result(config_id=config.id)
        result2 = _make_mock_result(config_id=config.id)

        with (
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.SimulationResultRepository") as MockResultRepo,
        ):
            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_result_repo = MagicMock()
            mock_result_repo.get_by_config = AsyncMock(return_value=[result1, result2])
            MockResultRepo.return_value = mock_result_repo

            results = await list_simulation_results(
                db=mock_db,
                current_user=mock_user,
                config_id=config.id,
                page=1,
                page_size=20,
            )

            assert len(results) == 2
            assert results[0].id == result1.id
            assert results[0].config_name == config.name

    @pytest.mark.asyncio
    async def test_list_results_config_not_found(self):
        """Should raise NotFoundError when config does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config_id = uuid4()

        with patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            MockRepo.return_value = mock_repo

            with pytest.raises(NotFoundError):
                await list_simulation_results(
                    db=mock_db,
                    current_user=mock_user,
                    config_id=config_id,
                    page=1,
                    page_size=20,
                )


# ===========================================================================
# get_simulation_result
# ===========================================================================


class TestGetSimulationResult:
    """Tests for get_simulation_result endpoint."""

    @pytest.mark.asyncio
    async def test_get_result_success(self):
        """Should return simulation result by ID."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config_id = uuid4()
        config = _make_mock_config()
        config.id = config_id
        config.iterations = 1000

        result = _make_mock_result(config_id=config_id)

        with (
            patch("src.api.v1.endpoints.simulations.simulation_cache") as mock_cache,
            patch("src.api.v1.endpoints.simulations.SimulationResultRepository") as MockResultRepo,
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
        ):
            mock_cache.is_available = False

            mock_result_repo = MagicMock()
            mock_result_repo.get_by_id = AsyncMock(return_value=result)
            MockResultRepo.return_value = mock_result_repo

            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            response = await get_simulation_result(
                db=mock_db,
                current_user=mock_user,
                config_id=config_id,
                result_id=result.id,
                use_cache=True,
            )

            assert response.id == result.id
            assert response.duration_results is not None

    @pytest.mark.asyncio
    async def test_get_result_not_found(self):
        """Should raise NotFoundError when result does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config_id = uuid4()
        result_id = uuid4()

        with (
            patch("src.api.v1.endpoints.simulations.simulation_cache") as mock_cache,
            patch("src.api.v1.endpoints.simulations.SimulationResultRepository") as MockResultRepo,
        ):
            mock_cache.is_available = False

            mock_result_repo = MagicMock()
            mock_result_repo.get_by_id = AsyncMock(return_value=None)
            MockResultRepo.return_value = mock_result_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_simulation_result(
                    db=mock_db,
                    current_user=mock_user,
                    config_id=config_id,
                    result_id=result_id,
                    use_cache=False,
                )

            assert "SIMULATION_RESULT_NOT_FOUND" in str(exc_info.value.code)

    @pytest.mark.asyncio
    async def test_get_result_cache_hit(self):
        """Should return cached result when cache is available."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config_id = uuid4()
        result_id = uuid4()

        cached_data = {
            "id": str(result_id),
            "config_id": str(config_id),
            "status": SimulationStatus.COMPLETED,
            "started_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "iterations_completed": 1000,
            "duration_results": {
                "p10": 110.0,
                "p50": 145.0,
                "p80": 165.0,
                "p90": 180.0,
                "mean": 147.5,
                "std": 22.3,
                "min": 95.0,
                "max": 210.0,
            },
            "cost_results": None,
            "duration_histogram": None,
            "cost_histogram": None,
            "activity_stats": None,
            "error_message": None,
            "random_seed": 42,
            "duration_seconds": 1.5,
            "progress_percent": 100.0,
        }

        with patch("src.api.v1.endpoints.simulations.simulation_cache") as mock_cache:
            mock_cache.is_available = True
            mock_cache.get_result = AsyncMock(return_value=cached_data)

            response = await get_simulation_result(
                db=mock_db,
                current_user=mock_user,
                config_id=config_id,
                result_id=result_id,
                use_cache=True,
            )

            assert response.iterations_completed == 1000
            mock_cache.get_result.assert_called_once_with(config_id, result_id)

    @pytest.mark.asyncio
    async def test_get_result_cache_miss(self):
        """Should fall back to database when cache misses."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config_id = uuid4()
        config = _make_mock_config()
        config.id = config_id
        config.iterations = 1000

        result = _make_mock_result(config_id=config_id)

        with (
            patch("src.api.v1.endpoints.simulations.simulation_cache") as mock_cache,
            patch("src.api.v1.endpoints.simulations.SimulationResultRepository") as MockResultRepo,
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
        ):
            mock_cache.is_available = True
            mock_cache.get_result = AsyncMock(return_value=None)
            mock_cache.set_result = AsyncMock()

            mock_result_repo = MagicMock()
            mock_result_repo.get_by_id = AsyncMock(return_value=result)
            MockResultRepo.return_value = mock_result_repo

            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            response = await get_simulation_result(
                db=mock_db,
                current_user=mock_user,
                config_id=config_id,
                result_id=result.id,
                use_cache=True,
            )

            assert response.id == result.id
            mock_cache.set_result.assert_called_once()


# ===========================================================================
# get_tornado_chart
# ===========================================================================


class TestGetTornadoChart:
    """Tests for get_tornado_chart endpoint."""

    @pytest.mark.asyncio
    async def test_get_tornado_success(self):
        """Should return tornado chart data."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program = _make_mock_program(owner_id=mock_user.id)
        config = _make_mock_config(program_id=program.id)
        act_id = uuid4()

        result = _make_mock_result(config_id=config.id)
        result.activity_results = {str(act_id): {"sensitivity": 0.72, "criticality": 0.85}}

        mock_activity = MagicMock()
        mock_activity.id = act_id
        mock_activity.name = "Design Phase"

        mock_bar = MagicMock()
        mock_bar.activity_id = act_id
        mock_bar.activity_name = "Design Phase"
        mock_bar.correlation = 0.72
        mock_bar.low_impact = 130.0
        mock_bar.high_impact = 160.0
        mock_bar.base_value = 147.5
        mock_bar.impact_range = 30.0
        mock_bar.rank = 1
        mock_bar.impact_direction = "direct"

        mock_chart_data = MagicMock()
        mock_chart_data.base_project_duration = 147.5
        mock_chart_data.top_drivers_count = 1
        mock_chart_data.min_duration = 130.0
        mock_chart_data.max_duration = 160.0
        mock_chart_data.chart_range = 30.0
        mock_chart_data.bars = [mock_bar]

        with (
            patch("src.api.v1.endpoints.simulations.simulation_cache") as mock_cache,
            patch("src.api.v1.endpoints.simulations.SimulationResultRepository") as MockResultRepo,
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
            patch("src.api.v1.endpoints.simulations.ActivityRepository") as MockActRepo,
            patch("src.api.v1.endpoints.simulations.TornadoChartService") as MockTornadoService,
        ):
            mock_cache.is_available = False

            mock_result_repo = MagicMock()
            mock_result_repo.get_by_id = AsyncMock(return_value=result)
            MockResultRepo.return_value = mock_result_repo

            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=[mock_activity])
            MockActRepo.return_value = mock_act_repo

            mock_tornado_instance = MagicMock()
            mock_tornado_instance.generate.return_value = mock_chart_data
            MockTornadoService.return_value = mock_tornado_instance

            response = await get_tornado_chart(
                db=mock_db,
                current_user=mock_user,
                config_id=config.id,
                result_id=result.id,
                top_n=10,
                use_cache=True,
            )

            assert response["base_project_duration"] == 147.5
            assert response["top_drivers_count"] == 1
            assert len(response["bars"]) == 1
            assert response["bars"][0]["activity_name"] == "Design Phase"
            assert response["from_cache"] is False

    @pytest.mark.asyncio
    async def test_get_tornado_result_not_found(self):
        """Should raise NotFoundError when result does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config_id = uuid4()
        result_id = uuid4()

        with (
            patch("src.api.v1.endpoints.simulations.simulation_cache") as mock_cache,
            patch("src.api.v1.endpoints.simulations.SimulationResultRepository") as MockResultRepo,
        ):
            mock_cache.is_available = False

            mock_result_repo = MagicMock()
            mock_result_repo.get_by_id = AsyncMock(return_value=None)
            MockResultRepo.return_value = mock_result_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_tornado_chart(
                    db=mock_db,
                    current_user=mock_user,
                    config_id=config_id,
                    result_id=result_id,
                    top_n=10,
                    use_cache=False,
                )

            assert "SIMULATION_RESULT_NOT_FOUND" in str(exc_info.value.code)

    @pytest.mark.asyncio
    async def test_get_tornado_auth_denied(self):
        """Should raise AuthorizationError when user has no access."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)
        program = _make_mock_program()  # Different owner
        config = _make_mock_config(program_id=program.id)
        result = _make_mock_result(config_id=config.id)

        with (
            patch("src.api.v1.endpoints.simulations.simulation_cache") as mock_cache,
            patch("src.api.v1.endpoints.simulations.SimulationResultRepository") as MockResultRepo,
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
        ):
            mock_cache.is_available = False

            mock_result_repo = MagicMock()
            mock_result_repo.get_by_id = AsyncMock(return_value=result)
            MockResultRepo.return_value = mock_result_repo

            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError):
                await get_tornado_chart(
                    db=mock_db,
                    current_user=mock_user,
                    config_id=config.id,
                    result_id=result.id,
                    top_n=10,
                    use_cache=False,
                )

    @pytest.mark.asyncio
    async def test_get_tornado_no_sensitivity_data(self):
        """Should raise HTTPException 404 when no sensitivity data is found."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program = _make_mock_program(owner_id=mock_user.id)
        config = _make_mock_config(program_id=program.id)

        result = _make_mock_result(config_id=config.id)
        result.activity_results = None
        result.duration_results = {
            "p50": 145.0,
            "mean": 147.5,
        }  # No sensitivity key

        mock_activity = MagicMock()
        mock_activity.id = uuid4()
        mock_activity.name = "Task A"

        with (
            patch("src.api.v1.endpoints.simulations.simulation_cache") as mock_cache,
            patch("src.api.v1.endpoints.simulations.SimulationResultRepository") as MockResultRepo,
            patch("src.api.v1.endpoints.simulations.SimulationConfigRepository") as MockConfigRepo,
            patch("src.api.v1.endpoints.simulations.ProgramRepository") as MockProgRepo,
            patch("src.api.v1.endpoints.simulations.ActivityRepository") as MockActRepo,
        ):
            mock_cache.is_available = False

            mock_result_repo = MagicMock()
            mock_result_repo.get_by_id = AsyncMock(return_value=result)
            MockResultRepo.return_value = mock_result_repo

            mock_config_repo = MagicMock()
            mock_config_repo.get_by_id = AsyncMock(return_value=config)
            MockConfigRepo.return_value = mock_config_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgRepo.return_value = mock_prog_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=[mock_activity])
            MockActRepo.return_value = mock_act_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_tornado_chart(
                    db=mock_db,
                    current_user=mock_user,
                    config_id=config.id,
                    result_id=result.id,
                    top_n=10,
                    use_cache=False,
                )

            assert exc_info.value.status_code == 404
            assert "No sensitivity data" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_tornado_cache_hit(self):
        """Should return cached tornado chart when available."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        config_id = uuid4()
        result_id = uuid4()

        cached_tornado = {
            "base_project_duration": 147.5,
            "top_drivers_count": 1,
            "min_duration": 130.0,
            "max_duration": 160.0,
            "chart_range": 30.0,
            "bars": [
                {
                    "activity_id": str(uuid4()),
                    "activity_name": "Cached Activity",
                    "correlation": 0.85,
                    "low_impact": 130.0,
                    "high_impact": 160.0,
                    "base_value": 147.5,
                    "impact_range": 30.0,
                    "rank": 1,
                    "impact_direction": "direct",
                }
            ],
            "from_cache": False,
        }

        with patch("src.api.v1.endpoints.simulations.simulation_cache") as mock_cache:
            mock_cache.is_available = True
            mock_cache.get_tornado = AsyncMock(return_value=cached_tornado)

            response = await get_tornado_chart(
                db=mock_db,
                current_user=mock_user,
                config_id=config_id,
                result_id=result_id,
                top_n=10,
                use_cache=True,
            )

            assert response["from_cache"] is True
            assert response["base_project_duration"] == 147.5
            mock_cache.get_tornado.assert_called_once_with(config_id, result_id, 10)
