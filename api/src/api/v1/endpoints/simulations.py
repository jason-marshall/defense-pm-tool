"""API endpoints for Monte Carlo simulations."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.v1.endpoints.dependencies import CurrentUser, DbSession
from src.core.exceptions import AuthorizationError, NotFoundError
from src.models.simulation import SimulationStatus
from src.repositories.program import ProgramRepository
from src.repositories.simulation import SimulationConfigRepository, SimulationResultRepository
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

router = APIRouter()


# ============================================================================
# Simulation Configuration Endpoints
# ============================================================================


@router.get("", response_model=list[SimulationConfigResponse])
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


@router.post("", response_model=SimulationConfigResponse, status_code=status.HTTP_201_CREATED)
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


@router.post("/quick", response_model=SimulationResultResponse)
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
    from datetime import datetime
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
                p10=output.cost_p10,
                p50=output.cost_p50,
                p80=output.cost_p80,
                p90=output.cost_p90,
                mean=output.cost_mean,
                std=output.cost_std,
                min=output.cost_min,
                max=output.cost_max,
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
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
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


@router.get("/{config_id}", response_model=SimulationConfigResponse)
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


@router.patch("/{config_id}", response_model=SimulationConfigResponse)
async def update_simulation_config(
    db: DbSession,
    current_user: CurrentUser,
    config_id: UUID,
    update_data: SimulationConfigUpdate,
) -> SimulationConfigResponse:
    """Update a simulation configuration."""
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


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_simulation_config(
    db: DbSession,
    current_user: CurrentUser,
    config_id: UUID,
) -> None:
    """Delete a simulation configuration (soft delete)."""
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

    await config_repo.delete(config_id)
    await db.commit()


# ============================================================================
# Simulation Execution Endpoints
# ============================================================================


@router.post("/{config_id}/run", response_model=SimulationResultResponse)
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
        duration_results = {
            "p10": output.duration_p10,
            "p50": output.duration_p50,
            "p80": output.duration_p80,
            "p90": output.duration_p90,
            "mean": output.duration_mean,
            "std": output.duration_std,
            "min": output.duration_min,
            "max": output.duration_max,
        }

        cost_results = None
        if output.cost_p50 is not None:
            cost_results = {
                "p10": output.cost_p10,
                "p50": output.cost_p50,
                "p80": output.cost_p80,
                "p90": output.cost_p90,
                "mean": output.cost_mean,
                "std": output.cost_std,
                "min": output.cost_min,
                "max": output.cost_max,
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
        result = await result_repo.mark_completed(
            result_id=result.id,
            duration_results=duration_results,
            cost_results=cost_results,
            duration_histogram=duration_histogram,
            cost_histogram=cost_histogram,
            activity_results=output.activity_stats,
            iterations_completed=output.iterations,
        )
        await db.commit()

        # Build response
        return SimulationResultResponse(
            id=result.id,
            config_id=result.config_id,
            status=result.status,
            started_at=result.started_at,
            completed_at=result.completed_at,
            iterations_completed=result.iterations_completed,
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
            random_seed=result.random_seed,
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


@router.get("/{config_id}/results", response_model=list[SimulationSummaryResponse])
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


@router.get("/{config_id}/results/{result_id}", response_model=SimulationResultResponse)
async def get_simulation_result(
    db: DbSession,
    current_user: CurrentUser,
    config_id: UUID,
    result_id: UUID,
) -> SimulationResultResponse:
    """Get detailed results for a specific simulation run."""
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
