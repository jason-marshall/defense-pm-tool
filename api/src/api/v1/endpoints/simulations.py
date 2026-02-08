"""API endpoints for Monte Carlo simulations."""

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import AuthorizationError, NotFoundError
from src.models.simulation import SimulationStatus
from src.repositories.activity import ActivityRepository
from src.repositories.dependency import DependencyRepository
from src.repositories.program import ProgramRepository
from src.repositories.simulation import SimulationConfigRepository, SimulationResultRepository
from src.schemas.errors import (
    AuthenticationErrorResponse,
    AuthorizationErrorResponse,
    NotFoundErrorResponse,
    RateLimitErrorResponse,
    ValidationErrorResponse,
)
from src.schemas.simulation import (
    DurationResultsSchema,
    HistogramSchema,
    QuickSimulationRequest,
    SimulationConfigCreate,
    SimulationConfigResponse,
    SimulationConfigUpdate,
    SimulationResultResponse,
    SimulationRunRequest,
    SimulationSummaryResponse,
)
from src.services.monte_carlo import (
    MonteCarloEngine,
    SimulationInput,
    parse_distribution_params,
)
from src.services.monte_carlo_optimized import OptimizedNetworkMonteCarloEngine
from src.services.simulation_cache import simulation_cache
from src.services.tornado_chart import TornadoChartService

router = APIRouter(tags=["Simulations"])


# ============================================================================
# Simulation Configuration Endpoints
# ============================================================================


@router.get(
    "",
    response_model=list[SimulationConfigResponse],
    summary="List Simulation Configs",
    responses={
        200: {"description": "Simulation configurations retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def list_simulation_configs(
    db: DbSession,
    current_user: CurrentUser,
    program_id: UUID = Query(..., description="Program ID to list configs for"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> list[SimulationConfigResponse]:
    """
    List all simulation configurations for a program.

    Returns paginated list of simulation configs.
    """
    skip = (page - 1) * page_size

    config_repo = SimulationConfigRepository(db)
    configs = await config_repo.get_by_program(
        program_id=program_id,
        skip=skip,
        limit=page_size,
    )

    return [
        SimulationConfigResponse(
            id=config.id,
            program_id=config.program_id,
            scenario_id=config.scenario_id,
            name=config.name,
            description=config.description,
            iterations=config.iterations,
            activity_distributions=config.activity_distributions,
            cost_distributions=config.cost_distributions,
            created_by_id=config.created_by_id,
            created_at=config.created_at,
            activity_count=config.activity_count,
        )
        for config in configs
    ]


@router.post(
    "",
    response_model=SimulationConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Simulation Config",
    responses={
        201: {"description": "Simulation configuration created successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Program not found"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def create_simulation_config(
    db: DbSession,
    current_user: CurrentUser,
    config_data: SimulationConfigCreate,
) -> SimulationConfigResponse:
    """
    Create a new simulation configuration.

    Defines which activities have uncertainty and their distribution parameters.
    """
    # Verify program access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(config_data.program_id)

    if not program:
        raise NotFoundError(f"Program {config_data.program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied to this program")

    # Convert distribution schemas to dicts
    activity_dists = {
        k: v.model_dump(by_alias=True, exclude_none=True)
        for k, v in config_data.activity_distributions.items()
    }

    cost_dists = None
    if config_data.cost_distributions:
        cost_dists = {
            k: v.model_dump(by_alias=True, exclude_none=True)
            for k, v in config_data.cost_distributions.items()
        }

    config_repo = SimulationConfigRepository(db)
    config = await config_repo.create_config(
        program_id=config_data.program_id,
        name=config_data.name,
        created_by_id=current_user.id,
        iterations=config_data.iterations,
        activity_distributions=activity_dists,
        cost_distributions=cost_dists,
        scenario_id=config_data.scenario_id,
        description=config_data.description,
    )

    await db.commit()

    return SimulationConfigResponse(
        id=config.id,
        program_id=config.program_id,
        scenario_id=config.scenario_id,
        name=config.name,
        description=config.description,
        iterations=config.iterations,
        activity_distributions=config.activity_distributions,
        cost_distributions=config.cost_distributions,
        created_by_id=config.created_by_id,
        created_at=config.created_at,
        activity_count=config.activity_count,
    )


# ============================================================================
# Quick Simulation (No Config Storage) - MUST be before /{config_id} routes
# ============================================================================


@router.post(
    "/quick",
    response_model=SimulationResultResponse,
    summary="Quick Simulation",
    responses={
        200: {"description": "Quick simulation completed successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Program not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"description": "Simulation failed"},
    },
)
async def quick_simulation(
    db: DbSession,
    current_user: CurrentUser,
    request: QuickSimulationRequest,
) -> SimulationResultResponse:
    """
    Run a quick simulation without saving the configuration.

    Useful for one-off analysis or testing distribution parameters.
    Limited to 10000 iterations.
    """
    from datetime import UTC, datetime
    from uuid import uuid4

    # Verify program access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(request.program_id)

    if not program:
        raise NotFoundError(f"Program {request.program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied to this program")

    try:
        # Parse distributions
        activity_distributions = {}
        for activity_id, dist_schema in request.activity_distributions.items():
            dist_data = dist_schema.model_dump(by_alias=True, exclude_none=True)
            activity_distributions[UUID(activity_id)] = parse_distribution_params(dist_data)

        cost_distributions = None
        if request.cost_distributions:
            cost_distributions = {}
            for activity_id, dist_schema in request.cost_distributions.items():
                dist_data = dist_schema.model_dump(by_alias=True, exclude_none=True)
                cost_distributions[UUID(activity_id)] = parse_distribution_params(dist_data)

        # Run simulation
        engine = MonteCarloEngine(seed=request.seed)
        sim_input = SimulationInput(
            activity_durations=activity_distributions,
            activity_costs=cost_distributions,
            iterations=request.iterations,
            seed=request.seed,
        )

        output = engine.simulate(sim_input)

        # Build response (no stored result)
        duration_results = DurationResultsSchema(
            p10=output.duration_p10,
            p50=output.duration_p50,
            p80=output.duration_p80,
            p90=output.duration_p90,
            mean=output.duration_mean,
            std=output.duration_std,
            min=output.duration_min,
            max=output.duration_max,
        )

        cost_results = None
        if output.cost_p50 is not None:
            cost_results = DurationResultsSchema(
                p10=output.cost_p10 or 0.0,
                p50=output.cost_p50,
                p80=output.cost_p80 or 0.0,
                p90=output.cost_p90 or 0.0,
                mean=output.cost_mean or 0.0,
                std=output.cost_std or 0.0,
                min=output.cost_min or 0.0,
                max=output.cost_max or 0.0,
            )

        duration_histogram = None
        if output.duration_histogram_bins is not None:
            duration_histogram = HistogramSchema(
                bins=output.duration_histogram_bins.tolist(),
                counts=[int(c) for c in output.duration_histogram_counts]
                if output.duration_histogram_counts is not None
                else [],
            )

        return SimulationResultResponse(
            id=uuid4(),  # Temporary ID
            config_id=uuid4(),  # No config
            status=SimulationStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            iterations_completed=output.iterations,
            duration_results=duration_results,
            cost_results=cost_results,
            duration_histogram=duration_histogram,
            random_seed=output.seed,
            duration_seconds=output.elapsed_seconds,
            progress_percent=100.0,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {e!s}",
        ) from e


# ============================================================================
# Configuration CRUD Operations (with /{config_id} paths)
# ============================================================================


@router.get(
    "/{config_id}",
    response_model=SimulationConfigResponse,
    summary="Get Simulation Config",
    responses={
        200: {"description": "Simulation configuration retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Config not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def get_simulation_config(
    db: DbSession,
    current_user: CurrentUser,
    config_id: UUID,
) -> SimulationConfigResponse:
    """Get a simulation configuration by ID."""
    config_repo = SimulationConfigRepository(db)
    config = await config_repo.get_with_results(config_id)

    if not config:
        raise NotFoundError(
            f"SimulationConfig {config_id} not found", "SIMULATION_CONFIG_NOT_FOUND"
        )

    return SimulationConfigResponse(
        id=config.id,
        program_id=config.program_id,
        scenario_id=config.scenario_id,
        name=config.name,
        description=config.description,
        iterations=config.iterations,
        activity_distributions=config.activity_distributions,
        cost_distributions=config.cost_distributions,
        created_by_id=config.created_by_id,
        created_at=config.created_at,
        activity_count=config.activity_count,
    )


@router.patch(
    "/{config_id}",
    response_model=SimulationConfigResponse,
    summary="Update Simulation Config",
    responses={
        200: {"description": "Simulation configuration updated successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Config not found"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def update_simulation_config(
    db: DbSession,
    current_user: CurrentUser,
    config_id: UUID,
    update_data: SimulationConfigUpdate,
) -> SimulationConfigResponse:
    """Update a simulation configuration.

    Invalidates cached results when distributions or iterations change.
    """
    config_repo = SimulationConfigRepository(db)
    config = await config_repo.get_by_id(config_id)

    if not config:
        raise NotFoundError(
            f"SimulationConfig {config_id} not found", "SIMULATION_CONFIG_NOT_FOUND"
        )

    # Verify ownership
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(config.program_id)

    if program and program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    # Check if we need to invalidate cache (distributions or iterations changed)
    should_invalidate = (
        update_data.iterations is not None
        or update_data.activity_distributions is not None
        or update_data.cost_distributions is not None
    )

    # Update fields
    if update_data.name is not None:
        config.name = update_data.name
    if update_data.description is not None:
        config.description = update_data.description
    if update_data.iterations is not None:
        config.iterations = update_data.iterations
    if update_data.activity_distributions is not None:
        config.activity_distributions = {
            k: v.model_dump(by_alias=True, exclude_none=True)
            for k, v in update_data.activity_distributions.items()
        }
    if update_data.cost_distributions is not None:
        config.cost_distributions = {
            k: v.model_dump(by_alias=True, exclude_none=True)
            for k, v in update_data.cost_distributions.items()
        }

    # Invalidate cache if simulation parameters changed
    if should_invalidate and simulation_cache.is_available:
        await simulation_cache.invalidate_config(config_id)

    await db.commit()

    return SimulationConfigResponse(
        id=config.id,
        program_id=config.program_id,
        scenario_id=config.scenario_id,
        name=config.name,
        description=config.description,
        iterations=config.iterations,
        activity_distributions=config.activity_distributions,
        cost_distributions=config.cost_distributions,
        created_by_id=config.created_by_id,
        created_at=config.created_at,
        activity_count=config.activity_count,
    )


@router.delete(
    "/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Simulation Config",
    responses={
        204: {"description": "Simulation configuration deleted successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Config not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def delete_simulation_config(
    db: DbSession,
    current_user: CurrentUser,
    config_id: UUID,
) -> None:
    """Delete a simulation configuration (soft delete).

    Also invalidates all cached results for this configuration.
    """
    config_repo = SimulationConfigRepository(db)
    config = await config_repo.get_by_id(config_id)

    if not config:
        raise NotFoundError(
            f"SimulationConfig {config_id} not found", "SIMULATION_CONFIG_NOT_FOUND"
        )

    # Verify ownership
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(config.program_id)

    if program and program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    # Invalidate all cached results for this config
    if simulation_cache.is_available:
        await simulation_cache.invalidate_config(config_id)

    await config_repo.delete(config_id)
    await db.commit()


# ============================================================================
# Simulation Execution Endpoints
# ============================================================================


@router.post(
    "/{config_id}/run",
    response_model=SimulationResultResponse,
    summary="Run Simulation",
    responses={
        200: {"description": "Simulation completed successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Config not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"description": "Simulation failed"},
    },
)
async def run_simulation(
    db: DbSession,
    current_user: CurrentUser,
    config_id: UUID,
    run_request: SimulationRunRequest | None = None,
) -> SimulationResultResponse:
    """
    Run a Monte Carlo simulation.

    Executes the simulation synchronously and returns results.
    For large simulations (>10000 iterations), consider using async endpoint.
    """
    config_repo = SimulationConfigRepository(db)
    config = await config_repo.get_by_id(config_id)

    if not config:
        raise NotFoundError(
            f"SimulationConfig {config_id} not found", "SIMULATION_CONFIG_NOT_FOUND"
        )

    # Parse seed from request
    seed = run_request.seed if run_request else None
    include_activity_stats = run_request.include_activity_stats if run_request else False

    # Create result record
    result_repo = SimulationResultRepository(db)
    result = await result_repo.create_result(config_id, seed=seed)
    await result_repo.mark_running(result.id)
    await db.commit()

    try:
        # Parse distributions from config
        activity_distributions = {}
        for activity_id, dist_data in config.activity_distributions.items():
            activity_distributions[UUID(activity_id)] = parse_distribution_params(dist_data)

        cost_distributions = None
        if config.cost_distributions:
            cost_distributions = {}
            for activity_id, dist_data in config.cost_distributions.items():
                cost_distributions[UUID(activity_id)] = parse_distribution_params(dist_data)

        # Run simulation
        engine = MonteCarloEngine(seed=seed)
        sim_input = SimulationInput(
            activity_durations=activity_distributions,
            activity_costs=cost_distributions,
            iterations=config.iterations,
            seed=seed,
            include_activity_stats=include_activity_stats,
        )

        output = engine.simulate(sim_input)

        # Convert output to storage format
        duration_results: dict[str, float] = {
            "p10": output.duration_p10,
            "p50": output.duration_p50,
            "p80": output.duration_p80,
            "p90": output.duration_p90,
            "mean": output.duration_mean,
            "std": output.duration_std,
            "min": output.duration_min,
            "max": output.duration_max,
        }

        cost_results: dict[str, float] | None = None
        if output.cost_p50 is not None:
            cost_results = {
                "p10": output.cost_p10 or 0.0,
                "p50": output.cost_p50,
                "p80": output.cost_p80 or 0.0,
                "p90": output.cost_p90 or 0.0,
                "mean": output.cost_mean or 0.0,
                "std": output.cost_std or 0.0,
                "min": output.cost_min or 0.0,
                "max": output.cost_max or 0.0,
            }

        duration_histogram = None
        if output.duration_histogram_bins is not None:
            duration_histogram = {
                "bins": output.duration_histogram_bins.tolist(),
                "counts": output.duration_histogram_counts.tolist()
                if output.duration_histogram_counts is not None
                else [],
            }

        cost_histogram = None
        if output.cost_histogram_bins is not None:
            cost_histogram = {
                "bins": output.cost_histogram_bins.tolist(),
                "counts": output.cost_histogram_counts.tolist()
                if output.cost_histogram_counts is not None
                else [],
            }

        # Mark completed
        updated_result = await result_repo.mark_completed(
            result_id=result.id,
            duration_results=duration_results,
            cost_results=cost_results,
            duration_histogram=duration_histogram,
            cost_histogram=cost_histogram,
            activity_results=output.activity_stats,
            iterations_completed=output.iterations,
        )
        await db.commit()

        if not updated_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save simulation result",
            )

        # Build response
        return SimulationResultResponse(
            id=updated_result.id,
            config_id=updated_result.config_id,
            status=updated_result.status,
            started_at=updated_result.started_at,
            completed_at=updated_result.completed_at,
            iterations_completed=updated_result.iterations_completed,
            duration_results=DurationResultsSchema(**duration_results),
            cost_results=DurationResultsSchema(**cost_results) if cost_results else None,
            duration_histogram=HistogramSchema(
                bins=duration_histogram["bins"],
                counts=[int(c) for c in duration_histogram["counts"]],
            )
            if duration_histogram
            else None,
            cost_histogram=HistogramSchema(
                bins=cost_histogram["bins"],
                counts=[int(c) for c in cost_histogram["counts"]],
            )
            if cost_histogram
            else None,
            activity_stats=output.activity_stats,
            random_seed=updated_result.random_seed,
            duration_seconds=output.elapsed_seconds,
            progress_percent=100.0,
        )

    except Exception as e:
        # Mark failed
        await result_repo.mark_failed(result.id, str(e))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {e!s}",
        ) from e


@router.post(
    "/{config_id}/run-network",
    response_model=SimulationResultResponse,
    summary="Run Network Simulation",
    responses={
        200: {"description": "Network simulation completed successfully"},
        400: {"description": "No activities found for program"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {"model": NotFoundErrorResponse, "description": "Config or program not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"description": "Simulation failed"},
    },
)
async def run_network_simulation(
    db: DbSession,
    current_user: CurrentUser,
    config_id: UUID,
    run_request: SimulationRunRequest | None = None,
) -> SimulationResultResponse:
    """
    Run a network-aware Monte Carlo simulation using optimized engine.

    This endpoint uses the OptimizedNetworkMonteCarloEngine which:
    - Pre-computes network topology once
    - Vectorizes CPM forward pass across all iterations
    - Achieves <5s for 1000 iterations with 100 activities

    Returns additional network-aware metrics:
    - Activity criticality (% of iterations on critical path)
    - Sensitivity (correlation with project duration)
    - Activity finish date distributions
    """
    config_repo = SimulationConfigRepository(db)
    config = await config_repo.get_by_id(config_id)

    if not config:
        raise NotFoundError(
            f"SimulationConfig {config_id} not found", "SIMULATION_CONFIG_NOT_FOUND"
        )

    # Verify program access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(config.program_id)

    if not program:
        raise NotFoundError(f"Program {config.program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied to this program")

    # Parse seed from request
    seed = run_request.seed if run_request else None

    # Create result record
    result_repo = SimulationResultRepository(db)
    result = await result_repo.create_result(config_id, seed=seed)
    await result_repo.mark_running(result.id)
    await db.commit()

    try:
        # Fetch activities and dependencies for the program
        activity_repo = ActivityRepository(db)
        dependency_repo = DependencyRepository(db)

        activities = await activity_repo.get_by_program(config.program_id)
        dependencies = await dependency_repo.get_by_program(config.program_id)

        if not activities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No activities found for program. Network simulation requires activities.",
            )

        # Parse distributions from config
        distributions = {}
        for activity_id, dist_data in config.activity_distributions.items():
            distributions[UUID(activity_id)] = parse_distribution_params(dist_data)

        # Run optimized network simulation
        engine = OptimizedNetworkMonteCarloEngine(seed=seed)
        output = engine.simulate(
            activities=cast("Any", activities),
            dependencies=cast("Any", dependencies),
            distributions=distributions,
            iterations=config.iterations,
        )

        # Convert output to storage format
        duration_results = {
            "p10": output.project_duration_p10,
            "p50": output.project_duration_p50,
            "p80": output.project_duration_p80,
            "p90": output.project_duration_p90,
            "mean": output.project_duration_mean,
            "std": output.project_duration_std,
            "min": output.project_duration_min,
            "max": output.project_duration_max,
        }

        duration_histogram = None
        if output.duration_histogram_bins is not None:
            duration_histogram = {
                "bins": output.duration_histogram_bins.tolist(),
                "counts": output.duration_histogram_counts.tolist()
                if output.duration_histogram_counts is not None
                else [],
            }

        # Build activity stats from criticality and sensitivity
        activity_stats: dict[str, dict[str, Any]] = {}
        for act_id in output.activity_criticality:
            act_id_str = str(act_id)
            activity_stats[act_id_str] = {
                "criticality": output.activity_criticality.get(act_id, 0.0),
                "sensitivity": output.sensitivity.get(act_id, 0.0),
            }
            if act_id in output.activity_finish_distributions:
                activity_stats[act_id_str]["finish_distribution"] = (
                    output.activity_finish_distributions[act_id]
                )

        # Mark completed
        completed_result = await result_repo.mark_completed(
            result_id=result.id,
            duration_results=duration_results,
            cost_results=None,
            duration_histogram=duration_histogram,
            cost_histogram=None,
            activity_results=activity_stats,
            iterations_completed=output.iterations,
        )
        await db.commit()

        if not completed_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save simulation result",
            )

        # Build response
        return SimulationResultResponse(
            id=completed_result.id,
            config_id=completed_result.config_id,
            status=completed_result.status,
            started_at=completed_result.started_at,
            completed_at=completed_result.completed_at,
            iterations_completed=completed_result.iterations_completed,
            duration_results=DurationResultsSchema(**duration_results),
            cost_results=None,
            duration_histogram=HistogramSchema(
                bins=duration_histogram["bins"],
                counts=[int(c) for c in duration_histogram["counts"]],
            )
            if duration_histogram
            else None,
            cost_histogram=None,
            activity_stats=activity_stats,
            random_seed=completed_result.random_seed,
            duration_seconds=output.elapsed_seconds,
            progress_percent=100.0,
        )

    except HTTPException:
        raise
    except Exception as e:
        # Mark failed
        await result_repo.mark_failed(result.id, str(e))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Network simulation failed: {e!s}",
        ) from e


@router.get(
    "/{config_id}/results",
    response_model=list[SimulationSummaryResponse],
    summary="List Simulation Results",
    responses={
        200: {"description": "Simulation results retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Config not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def list_simulation_results(
    db: DbSession,
    current_user: CurrentUser,
    config_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> list[SimulationSummaryResponse]:
    """List all results for a simulation configuration."""
    config_repo = SimulationConfigRepository(db)
    config = await config_repo.get_by_id(config_id)

    if not config:
        raise NotFoundError(
            f"SimulationConfig {config_id} not found", "SIMULATION_CONFIG_NOT_FOUND"
        )

    skip = (page - 1) * page_size

    result_repo = SimulationResultRepository(db)
    results = await result_repo.get_by_config(config_id, skip=skip, limit=page_size)

    return [
        SimulationSummaryResponse(
            id=r.id,
            config_id=r.config_id,
            config_name=config.name,
            status=r.status,
            iterations_completed=r.iterations_completed,
            total_iterations=config.iterations,
            progress_percent=(r.iterations_completed / config.iterations * 100)
            if config.iterations > 0
            else 0,
            duration_p50=r.duration_results.get("p50") if r.duration_results else None,
            duration_p90=r.duration_results.get("p90") if r.duration_results else None,
            cost_p50=r.cost_results.get("p50") if r.cost_results else None,
            created_at=r.created_at,
            completed_at=r.completed_at,
        )
        for r in results
    ]


@router.get(
    "/{config_id}/results/{result_id}",
    response_model=SimulationResultResponse,
    summary="Get Simulation Result",
    responses={
        200: {"description": "Simulation result retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        404: {"model": NotFoundErrorResponse, "description": "Result not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def get_simulation_result(
    db: DbSession,
    current_user: CurrentUser,
    config_id: UUID,
    result_id: UUID,
    use_cache: bool = Query(True, description="Use cached result if available"),
) -> SimulationResultResponse:
    """Get detailed results for a specific simulation run.

    Results are cached for 24 hours to improve performance.
    Set use_cache=false to bypass the cache and get fresh data.
    """
    # Try to get from cache first
    if use_cache and simulation_cache.is_available:
        cached = await simulation_cache.get_result(config_id, result_id)
        if cached is not None:
            # Return cached response with cache indicator
            response = SimulationResultResponse(**cached)
            return response

    result_repo = SimulationResultRepository(db)
    result = await result_repo.get_by_id(result_id)

    if not result or result.config_id != config_id:
        raise NotFoundError(
            f"SimulationResult {result_id} not found", "SIMULATION_RESULT_NOT_FOUND"
        )

    config_repo = SimulationConfigRepository(db)
    config = await config_repo.get_by_id(config_id)

    progress = (
        (result.iterations_completed / config.iterations * 100)
        if config and config.iterations > 0
        else 0
    )

    response_data = {
        "id": result.id,
        "config_id": result.config_id,
        "status": result.status,
        "started_at": result.started_at,
        "completed_at": result.completed_at,
        "iterations_completed": result.iterations_completed,
        "duration_results": result.duration_results,
        "cost_results": result.cost_results,
        "duration_histogram": result.duration_histogram,
        "cost_histogram": result.cost_histogram,
        "activity_stats": result.activity_results,
        "error_message": result.error_message,
        "random_seed": result.random_seed,
        "duration_seconds": result.duration_seconds,
        "progress_percent": progress,
    }

    # Cache the result for future requests
    if simulation_cache.is_available:
        await simulation_cache.set_result(config_id, response_data, result_id)

    return SimulationResultResponse(
        id=result.id,
        config_id=result.config_id,
        status=result.status,
        started_at=result.started_at,
        completed_at=result.completed_at,
        iterations_completed=result.iterations_completed,
        duration_results=DurationResultsSchema(**result.duration_results)
        if result.duration_results
        else None,
        cost_results=DurationResultsSchema(**result.cost_results) if result.cost_results else None,
        duration_histogram=HistogramSchema(
            bins=result.duration_histogram["bins"],
            counts=[int(c) for c in result.duration_histogram["counts"]],
        )
        if result.duration_histogram
        else None,
        cost_histogram=HistogramSchema(
            bins=result.cost_histogram["bins"],
            counts=[int(c) for c in result.cost_histogram["counts"]],
        )
        if result.cost_histogram
        else None,
        activity_stats=result.activity_results,
        error_message=result.error_message,
        random_seed=result.random_seed,
        duration_seconds=result.duration_seconds,
        progress_percent=progress,
    )


# ============================================================================
# Sensitivity Analysis Endpoints
# ============================================================================


def _extract_sensitivity_data(result: Any) -> dict[str, float]:
    """Extract sensitivity data from simulation result.

    Args:
        result: SimulationResult with duration_results or activity_results

    Returns:
        Dictionary mapping activity ID strings to sensitivity values
    """
    # Sensitivity may be in duration_results or activity_results
    if result.duration_results and "sensitivity" in result.duration_results:
        sens = result.duration_results.get("sensitivity", {})
        return cast("dict[str, float]", sens)

    if not result.activity_results:
        return {}

    # Extract sensitivity from activity_results if available
    sensitivity_raw: dict[str, float] = {}
    for act_id_str, stats in result.activity_results.items():
        if isinstance(stats, dict) and "sensitivity" in stats:
            sensitivity_raw[act_id_str] = stats["sensitivity"]
    return sensitivity_raw


def _extract_activity_ranges(
    distributions: dict[str, Any] | None,
) -> dict[UUID, tuple[float, float]]:
    """Extract activity duration ranges from distributions config.

    Args:
        distributions: Activity distributions from config

    Returns:
        Dictionary mapping activity UUIDs to (min, max) tuples
    """
    activity_ranges: dict[UUID, tuple[float, float]] = {}
    for act_id_str, params in (distributions or {}).items():
        try:
            act_id = UUID(act_id_str)
            min_val = float(params.get("min_value", params.get("min", 0)))
            max_val = float(params.get("max_value", params.get("max", min_val + 10)))
            activity_ranges[act_id] = (min_val, max_val)
        except (ValueError, TypeError):
            continue
    return activity_ranges


@router.get(
    "/{config_id}/results/{result_id}/tornado",
    summary="Get Tornado Chart",
    responses={
        200: {"description": "Tornado chart data retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
        403: {"model": AuthorizationErrorResponse, "description": "Not authorized"},
        404: {
            "model": NotFoundErrorResponse,
            "description": "Result or sensitivity data not found",
        },
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def get_tornado_chart(
    db: DbSession,
    current_user: CurrentUser,
    config_id: UUID,
    result_id: UUID,
    top_n: int = Query(10, ge=1, le=50, description="Number of top drivers to include"),
    use_cache: bool = Query(True, description="Use cached tornado chart if available"),
) -> dict[str, Any]:
    """
    Get tornado chart data for sensitivity analysis.

    Shows top N activities by impact on project duration.
    Bars are sorted by absolute correlation (highest impact first).

    The tornado chart visualizes:
    - Activity name and rank
    - Correlation with project duration
    - Impact range (low to high estimate effect on project)
    - Base (mean) project duration reference line

    Tornado charts are cached for 24 hours per top_n value.
    Set use_cache=false to bypass the cache.

    Returns:
        Tornado chart data with bars for visualization
    """
    # Try to get from cache first
    if use_cache and simulation_cache.is_available:
        cached = await simulation_cache.get_tornado(config_id, result_id, top_n)
        if cached is not None:
            cached["from_cache"] = True
            return cached

    # Get simulation result
    result_repo = SimulationResultRepository(db)
    result = await result_repo.get_by_id(result_id)

    if not result or result.config_id != config_id:
        raise NotFoundError(
            f"SimulationResult {result_id} not found", "SIMULATION_RESULT_NOT_FOUND"
        )

    # Get config for activity info
    config_repo = SimulationConfigRepository(db)
    config = await config_repo.get_by_id(config_id)

    if not config:
        raise NotFoundError(
            f"SimulationConfig {config_id} not found", "SIMULATION_CONFIG_NOT_FOUND"
        )

    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(config.program_id)

    if not program:
        raise NotFoundError(f"Program {config.program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied to this program")

    # Get activity names
    activity_repo = ActivityRepository(db)
    activities = await activity_repo.get_by_program(config.program_id)
    activity_names = {a.id: a.name for a in activities}

    # Get activity ranges from config distributions
    activity_ranges = _extract_activity_ranges(config.activity_distributions)

    # Get sensitivity data from result
    sensitivity_raw = _extract_sensitivity_data(result)

    if not sensitivity_raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sensitivity data found in simulation result. "
            "Run a network simulation with sensitivity analysis enabled.",
        )

    # Convert string UUIDs to UUID objects
    sensitivity = {UUID(k): float(v) for k, v in sensitivity_raw.items()}

    # Get base duration from result
    base_duration = (
        float(result.duration_results.get("mean", 0)) if result.duration_results else 0.0
    )

    # Generate tornado chart
    service = TornadoChartService(
        sensitivity=sensitivity,
        activity_names=activity_names,
        base_duration=base_duration,
        activity_ranges=activity_ranges,
    )

    chart_data = service.generate(top_n)

    response = {
        "base_project_duration": chart_data.base_project_duration,
        "top_drivers_count": chart_data.top_drivers_count,
        "min_duration": chart_data.min_duration,
        "max_duration": chart_data.max_duration,
        "chart_range": chart_data.chart_range,
        "bars": [
            {
                "activity_id": str(bar.activity_id),
                "activity_name": bar.activity_name,
                "correlation": bar.correlation,
                "low_impact": bar.low_impact,
                "high_impact": bar.high_impact,
                "base_value": bar.base_value,
                "impact_range": bar.impact_range,
                "rank": bar.rank,
                "impact_direction": bar.impact_direction,
            }
            for bar in chart_data.bars
        ],
        "from_cache": False,
    }

    # Cache the tornado chart
    if simulation_cache.is_available:
        await simulation_cache.set_tornado(config_id, result_id, top_n, response)

    return response
