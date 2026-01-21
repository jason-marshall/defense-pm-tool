"""API endpoints for Scenario management (what-if analysis)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from src.repositories.activity import ActivityRepository
from src.repositories.baseline import BaselineRepository
from src.repositories.dependency import DependencyRepository
from src.repositories.program import ProgramRepository
from src.repositories.scenario import ScenarioRepository
from src.repositories.wbs import WBSElementRepository
from src.schemas.scenario import (
    ScenarioChangeCreate,
    ScenarioChangeResponse,
    ScenarioCreate,
    ScenarioDiffSummary,
    ScenarioListResponse,
    ScenarioPromoteRequest,
    ScenarioResponse,
    ScenarioSummary,
    ScenarioUpdate,
)
from src.services.scenario_simulation import ScenarioSimulationService

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

# Note: DbSession and CurrentUser imported from src.core.deps


@router.get("", response_model=ScenarioListResponse)
async def list_scenarios(
    db: DbSession,
    current_user: CurrentUser,
    program_id: UUID = Query(..., description="Program ID to list scenarios for"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    active_only: bool = Query(False, description="Filter to active scenarios only"),
) -> ScenarioListResponse:
    """
    List all scenarios for a program.

    Returns scenarios ordered by creation date (newest first).
    Use active_only=true to filter out promoted/archived scenarios.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    repo = ScenarioRepository(db)
    skip = (page - 1) * per_page

    scenarios = await repo.get_by_program(
        program_id, skip=skip, limit=per_page, active_only=active_only
    )
    total = await repo.count_by_program(program_id, active_only=active_only)

    # Build summaries with change counts
    items = []
    for scenario in scenarios:
        summary = ScenarioSummary(
            id=scenario.id,
            program_id=scenario.program_id,
            baseline_id=scenario.baseline_id,
            parent_scenario_id=scenario.parent_scenario_id,
            name=scenario.name,
            description=scenario.description,
            status=scenario.status,
            is_active=scenario.is_active,
            change_count=scenario.change_count,
            has_cached_results=scenario.has_cached_results,
            created_at=scenario.created_at,
            created_by_id=scenario.created_by_id,
            promoted_at=scenario.promoted_at,
            promoted_baseline_id=scenario.promoted_baseline_id,
        )
        items.append(summary)

    return ScenarioListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 1,
    )


@router.post("", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    db: DbSession,
    current_user: CurrentUser,
    scenario_data: ScenarioCreate,
) -> ScenarioResponse:
    """
    Create a new scenario for what-if analysis.

    Scenarios can be based on:
    - Current program state (no baseline_id or parent_scenario_id)
    - A specific baseline (baseline_id set)
    - Another scenario (parent_scenario_id set, inherits all changes)
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get(scenario_data.program_id)
    if not program:
        raise NotFoundError(
            f"Program {scenario_data.program_id} not found",
            "PROGRAM_NOT_FOUND",
        )

    # Verify baseline exists if specified
    if scenario_data.baseline_id:
        baseline_repo = BaselineRepository(db)
        baseline = await baseline_repo.get(scenario_data.baseline_id)
        if not baseline:
            raise NotFoundError(
                f"Baseline {scenario_data.baseline_id} not found",
                "BASELINE_NOT_FOUND",
            )

    repo = ScenarioRepository(db)

    # If branching from parent scenario, use special method
    if scenario_data.parent_scenario_id:
        scenario = await repo.branch_from_scenario(
            parent_scenario_id=scenario_data.parent_scenario_id,
            name=scenario_data.name,
            description=scenario_data.description,
            created_by_id=current_user.id,
        )
        if not scenario:
            raise NotFoundError(
                f"Parent scenario {scenario_data.parent_scenario_id} not found",
                "PARENT_SCENARIO_NOT_FOUND",
            )
    else:
        # Create new scenario from scratch
        from src.models.scenario import Scenario

        scenario = Scenario(
            program_id=scenario_data.program_id,
            baseline_id=scenario_data.baseline_id,
            name=scenario_data.name,
            description=scenario_data.description,
            status="draft",
            is_active=True,
            created_by_id=current_user.id,
        )
        db.add(scenario)
        await db.flush()

    await db.commit()
    await db.refresh(scenario)

    return _build_scenario_response(scenario)


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    db: DbSession,
    current_user: CurrentUser,
    scenario_id: UUID,
    include_changes: bool = Query(True, description="Include change details"),
) -> ScenarioResponse:
    """
    Get a specific scenario by ID.

    Use include_changes=false for faster response when only
    metadata is needed.
    """
    repo = ScenarioRepository(db)

    if include_changes:
        scenario = await repo.get_with_changes(scenario_id)
    else:
        scenario = await repo.get(scenario_id)

    if not scenario:
        raise NotFoundError(f"Scenario {scenario_id} not found", "SCENARIO_NOT_FOUND")

    return _build_scenario_response(scenario, include_changes=include_changes)


@router.patch("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    db: DbSession,
    current_user: CurrentUser,
    scenario_id: UUID,
    update_data: ScenarioUpdate,
) -> ScenarioResponse:
    """
    Update scenario metadata.

    Promoted scenarios cannot be modified.
    """
    repo = ScenarioRepository(db)
    scenario = await repo.get(scenario_id)

    if not scenario:
        raise NotFoundError(f"Scenario {scenario_id} not found", "SCENARIO_NOT_FOUND")

    if scenario.status == "promoted":
        raise ValidationError(
            "Cannot modify promoted scenario",
            "PROMOTED_SCENARIO_MODIFY",
        )

    # Update allowed fields
    update_dict = update_data.model_dump(exclude_unset=True)
    if update_dict:
        for key, value in update_dict.items():
            if key == "status" and value:
                setattr(scenario, key, value.value if hasattr(value, "value") else value)
            else:
                setattr(scenario, key, value)

    await db.commit()
    await db.refresh(scenario)

    return _build_scenario_response(scenario)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    db: DbSession,
    current_user: CurrentUser,
    scenario_id: UUID,
) -> None:
    """
    Soft delete a scenario.

    Promoted scenarios cannot be deleted.
    """
    repo = ScenarioRepository(db)
    scenario = await repo.get(scenario_id)

    if not scenario:
        raise NotFoundError(f"Scenario {scenario_id} not found", "SCENARIO_NOT_FOUND")

    if scenario.status == "promoted":
        raise ValidationError(
            "Cannot delete promoted scenario",
            "PROMOTED_SCENARIO_DELETE",
        )

    await repo.delete(scenario_id)
    await db.commit()


@router.post("/{scenario_id}/changes", response_model=ScenarioChangeResponse)
async def add_change(
    db: DbSession,
    current_user: CurrentUser,
    scenario_id: UUID,
    change_data: ScenarioChangeCreate,
) -> ScenarioChangeResponse:
    """
    Add a change to a scenario.

    Changes track modifications to activities, dependencies, or WBS elements.
    Adding a change invalidates any cached CPM results.
    """
    repo = ScenarioRepository(db)
    scenario = await repo.get(scenario_id)

    if not scenario:
        raise NotFoundError(f"Scenario {scenario_id} not found", "SCENARIO_NOT_FOUND")

    if scenario.status == "promoted":
        raise ValidationError(
            "Cannot modify promoted scenario",
            "PROMOTED_SCENARIO_MODIFY",
        )

    change = await repo.add_change(
        scenario_id=scenario_id,
        entity_type=change_data.entity_type.value,
        entity_id=change_data.entity_id,
        entity_code=change_data.entity_code,
        change_type=change_data.change_type.value,
        field_name=change_data.field_name,
        old_value=change_data.old_value,
        new_value=change_data.new_value,
    )

    await db.commit()
    await db.refresh(change)

    return ScenarioChangeResponse.model_validate(change)


@router.get("/{scenario_id}/changes", response_model=list[ScenarioChangeResponse])
async def list_changes(
    db: DbSession,
    current_user: CurrentUser,
    scenario_id: UUID,
    entity_type: str | None = Query(None, description="Filter by entity type"),
) -> list[ScenarioChangeResponse]:
    """
    List all changes in a scenario.

    Optionally filter by entity type (activity, dependency, wbs).
    """
    repo = ScenarioRepository(db)
    scenario = await repo.get(scenario_id)

    if not scenario:
        raise NotFoundError(f"Scenario {scenario_id} not found", "SCENARIO_NOT_FOUND")

    changes = await repo.get_changes(scenario_id, entity_type=entity_type)

    return [ScenarioChangeResponse.model_validate(c) for c in changes]


@router.delete("/{scenario_id}/changes/{change_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_change(
    db: DbSession,
    current_user: CurrentUser,
    scenario_id: UUID,
    change_id: UUID,
) -> None:
    """
    Remove a specific change from a scenario.

    Removing a change invalidates any cached CPM results.
    """
    repo = ScenarioRepository(db)
    scenario = await repo.get(scenario_id)

    if not scenario:
        raise NotFoundError(f"Scenario {scenario_id} not found", "SCENARIO_NOT_FOUND")

    if scenario.status == "promoted":
        raise ValidationError(
            "Cannot modify promoted scenario",
            "PROMOTED_SCENARIO_MODIFY",
        )

    removed = await repo.remove_change(change_id)
    if not removed:
        raise NotFoundError(f"Change {change_id} not found", "CHANGE_NOT_FOUND")

    await db.commit()


@router.post("/{scenario_id}/archive", response_model=ScenarioResponse)
async def archive_scenario(
    db: DbSession,
    current_user: CurrentUser,
    scenario_id: UUID,
) -> ScenarioResponse:
    """
    Archive a scenario.

    Archived scenarios are kept for historical reference but marked inactive.
    """
    repo = ScenarioRepository(db)
    scenario = await repo.archive(scenario_id)

    if not scenario:
        raise NotFoundError(f"Scenario {scenario_id} not found", "SCENARIO_NOT_FOUND")

    await db.commit()
    await db.refresh(scenario)

    return _build_scenario_response(scenario)


@router.post("/{scenario_id}/activate", response_model=ScenarioResponse)
async def activate_scenario(
    db: DbSession,
    current_user: CurrentUser,
    scenario_id: UUID,
) -> ScenarioResponse:
    """
    Activate a draft scenario.

    Changes status from 'draft' to 'active'.
    """
    repo = ScenarioRepository(db)
    scenario = await repo.get(scenario_id)

    if not scenario:
        raise NotFoundError(f"Scenario {scenario_id} not found", "SCENARIO_NOT_FOUND")

    if scenario.status != "draft":
        raise ValidationError(
            f"Cannot activate scenario in '{scenario.status}' status",
            "INVALID_STATUS_TRANSITION",
        )

    scenario.status = "active"
    await db.commit()
    await db.refresh(scenario)

    return _build_scenario_response(scenario)


@router.post("/{scenario_id}/promote")
async def promote_scenario(
    db: DbSession,
    current_user: CurrentUser,
    scenario_id: UUID,
    promote_request: ScenarioPromoteRequest,
) -> dict[str, Any]:
    """
    Promote a scenario to a new baseline.

    Creates a new baseline with all scenario changes applied.
    The scenario is marked as promoted and cannot be further modified.

    Requirements:
    - Scenario must exist and not already be promoted or archived
    - User must have access to the program

    Returns:
        Promotion result including new baseline ID and version.
    """
    from src.services.scenario_promotion import (
        BaselineCreationError,
        ScenarioNotEligibleError,
        ScenarioNotFoundError,
        ScenarioPromotionService,
    )

    # Get scenario to verify access
    scenario_repo = ScenarioRepository(db)
    scenario = await scenario_repo.get(scenario_id)

    if not scenario:
        raise NotFoundError(f"Scenario {scenario_id} not found", "SCENARIO_NOT_FOUND")

    # Verify user has access to the program
    program_repo = ProgramRepository(db)
    program = await program_repo.get(scenario.program_id)

    if not program:
        raise NotFoundError(f"Program {scenario.program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to promote scenarios for this program",
            "NOT_AUTHORIZED",
        )

    # Create promotion service with all required repositories
    baseline_repo = BaselineRepository(db)
    activity_repo = ActivityRepository(db)
    wbs_repo = WBSElementRepository(db)

    promotion_service = ScenarioPromotionService(
        scenario_repo=scenario_repo,
        baseline_repo=baseline_repo,
        activity_repo=activity_repo,
        wbs_repo=wbs_repo,
    )

    try:
        result = await promotion_service.promote_scenario(
            scenario_id=scenario_id,
            baseline_name=promote_request.baseline_name,
            baseline_description=promote_request.baseline_description,
            created_by_id=current_user.id,
        )

        await db.commit()

        return {
            "success": result.success,
            "scenario_id": str(result.scenario_id),
            "baseline_id": str(result.baseline_id) if result.baseline_id else None,
            "baseline_name": result.baseline_name,
            "baseline_version": result.baseline_version,
            "changes_count": result.changes_count,
            "duration_ms": result.duration_ms,
            "message": f"Scenario promoted to baseline '{result.baseline_name}' (v{result.baseline_version})",
        }

    except ScenarioNotFoundError as e:
        raise NotFoundError(e.message, e.code) from e
    except ScenarioNotEligibleError as e:
        raise ValidationError(e.message, e.code) from e
    except BaselineCreationError as e:
        raise ValidationError(e.message, e.code) from e


@router.get("/{scenario_id}/summary", response_model=ScenarioDiffSummary)
async def get_scenario_summary(
    db: DbSession,
    current_user: CurrentUser,
    scenario_id: UUID,
) -> ScenarioDiffSummary:
    """
    Get summary of changes in a scenario.

    Returns counts of changes by entity type and change type.
    """
    repo = ScenarioRepository(db)
    scenario = await repo.get(scenario_id)

    if not scenario:
        raise NotFoundError(f"Scenario {scenario_id} not found", "SCENARIO_NOT_FOUND")

    summary_data = await repo.get_change_summary(scenario_id)

    return ScenarioDiffSummary(
        scenario_id=scenario.id,
        scenario_name=scenario.name,
        activities_created=summary_data.get("activities_created", 0),
        activities_updated=summary_data.get("activities_updated", 0),
        activities_deleted=summary_data.get("activities_deleted", 0),
        dependencies_created=summary_data.get("dependencies_created", 0),
        dependencies_updated=summary_data.get("dependencies_updated", 0),
        dependencies_deleted=summary_data.get("dependencies_deleted", 0),
        wbs_created=summary_data.get("wbs_created", 0),
        wbs_updated=summary_data.get("wbs_updated", 0),
        wbs_deleted=summary_data.get("wbs_deleted", 0),
        total_changes=summary_data.get("total_changes", 0),
    )


def _build_scenario_response(
    scenario: Any,
    include_changes: bool = True,
) -> ScenarioResponse:
    """Build a ScenarioResponse from a Scenario model."""
    changes = []
    if include_changes and hasattr(scenario, "changes") and scenario.changes:
        changes = [ScenarioChangeResponse.model_validate(c) for c in scenario.changes]

    return ScenarioResponse(
        id=scenario.id,
        program_id=scenario.program_id,
        baseline_id=scenario.baseline_id,
        parent_scenario_id=scenario.parent_scenario_id,
        name=scenario.name,
        description=scenario.description,
        status=scenario.status,
        is_active=scenario.is_active,
        change_count=scenario.change_count,
        has_cached_results=scenario.has_cached_results,
        created_at=scenario.created_at,
        created_by_id=scenario.created_by_id,
        promoted_at=scenario.promoted_at,
        promoted_baseline_id=scenario.promoted_baseline_id,
        changes=changes,
        results_cache=scenario.results_cache,
        updated_at=scenario.updated_at,
    )


# =============================================================================
# Scenario Simulation Endpoints
# =============================================================================


@router.post("/{scenario_id}/simulate")
async def simulate_scenario(
    db: DbSession,
    current_user: CurrentUser,
    scenario_id: UUID,
    iterations: int = Query(1000, ge=100, le=10000, description="Number of iterations"),
    seed: int | None = Query(None, description="Random seed for reproducibility"),
) -> dict[str, Any]:
    """
    Run Monte Carlo simulation on a scenario.

    Applies scenario changes to activities and simulates through the CPM
    network to evaluate schedule risk with the proposed changes.

    Returns:
    - Project duration distribution (P10, P50, P80, P90)
    - Activity criticality (% of iterations on critical path)
    - Top schedule risk drivers (sensitivity analysis)

    Use this endpoint for what-if analysis to understand the impact
    of proposed changes before committing them.
    """
    # Get scenario
    scenario_repo = ScenarioRepository(db)
    scenario = await scenario_repo.get_with_changes(scenario_id)

    if not scenario:
        raise NotFoundError(f"Scenario {scenario_id} not found", "SCENARIO_NOT_FOUND")

    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get(scenario.program_id)

    if not program:
        raise NotFoundError(f"Program {scenario.program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to simulate this scenario",
            "NOT_AUTHORIZED",
        )

    # Get activities and dependencies
    activity_repo = ActivityRepository(db)
    dependency_repo = DependencyRepository(db)

    activities = await activity_repo.get_by_program(scenario.program_id)
    dependencies = await dependency_repo.get_by_program(scenario.program_id)

    if not activities:
        raise ValidationError(
            "No activities found for program - cannot simulate",
            "NO_ACTIVITIES",
        )

    # Get scenario changes
    changes = await scenario_repo.get_changes(scenario_id)

    # Run simulation
    service = ScenarioSimulationService(
        activities=activities,
        dependencies=dependencies,
        scenario=scenario,
        changes=changes,
    )

    output = service.simulate(iterations=iterations, seed=seed)

    # Build response
    return {
        "scenario_id": str(scenario_id),
        "scenario_name": scenario.name,
        "iterations": output.iterations,
        "elapsed_seconds": round(output.elapsed_seconds, 3),
        "seed": output.seed,
        "project_duration": {
            "p10": round(output.project_duration_p10, 1),
            "p50": round(output.project_duration_p50, 1),
            "p80": round(output.project_duration_p80, 1),
            "p90": round(output.project_duration_p90, 1),
            "mean": round(output.project_duration_mean, 1),
            "std": round(output.project_duration_std, 2),
            "min": round(output.project_duration_min, 1),
            "max": round(output.project_duration_max, 1),
        },
        "top_critical_activities": sorted(
            [
                {"activity_id": str(k), "criticality_pct": round(v, 1)}
                for k, v in output.activity_criticality.items()
                if v > 0
            ],
            key=lambda x: float(str(x["criticality_pct"])),
            reverse=True,
        )[:10],
        "top_sensitivity_drivers": sorted(
            [
                {"activity_id": str(k), "correlation": round(v, 3)}
                for k, v in output.sensitivity.items()
                if abs(v) > 0.1
            ],
            key=lambda x: abs(float(str(x["correlation"]))),
            reverse=True,
        )[:10],
        "changes_applied": len(changes),
    }


@router.post("/{scenario_id}/compare")
async def compare_scenario_to_baseline(
    db: DbSession,
    current_user: CurrentUser,
    scenario_id: UUID,
    iterations: int = Query(1000, ge=100, le=10000, description="Number of iterations"),
    seed: int | None = Query(None, description="Random seed for reproducibility"),
) -> dict[str, Any]:
    """
    Compare scenario simulation to baseline (no changes).

    Runs Monte Carlo simulation twice:
    1. Without scenario changes (baseline)
    2. With scenario changes applied

    Returns comparison showing impact of the proposed changes
    on project duration and risk.
    """
    from src.services.scenario_simulation import compare_scenario_simulations

    # Get scenario
    scenario_repo = ScenarioRepository(db)
    scenario = await scenario_repo.get_with_changes(scenario_id)

    if not scenario:
        raise NotFoundError(f"Scenario {scenario_id} not found", "SCENARIO_NOT_FOUND")

    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get(scenario.program_id)

    if not program:
        raise NotFoundError(f"Program {scenario.program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to compare this scenario",
            "NOT_AUTHORIZED",
        )

    # Get activities and dependencies
    activity_repo = ActivityRepository(db)
    dependency_repo = DependencyRepository(db)

    activities = await activity_repo.get_by_program(scenario.program_id)
    dependencies = await dependency_repo.get_by_program(scenario.program_id)

    if not activities:
        raise ValidationError(
            "No activities found for program - cannot compare",
            "NO_ACTIVITIES",
        )

    # Get scenario changes
    changes = await scenario_repo.get_changes(scenario_id)

    # Run baseline simulation (no changes)
    baseline_service = ScenarioSimulationService(
        activities=activities,
        dependencies=dependencies,
        scenario=scenario,
        changes=[],  # No changes for baseline
    )
    baseline_output = baseline_service.simulate(iterations=iterations, seed=seed)

    # Run scenario simulation (with changes)
    scenario_service = ScenarioSimulationService(
        activities=activities,
        dependencies=dependencies,
        scenario=scenario,
        changes=changes,
    )
    scenario_output = scenario_service.simulate(iterations=iterations, seed=seed)

    # Compare results
    comparison = compare_scenario_simulations(baseline_output, scenario_output)

    return {
        "scenario_id": str(scenario_id),
        "scenario_name": scenario.name,
        "iterations": iterations,
        "baseline": {
            "p50": round(baseline_output.project_duration_p50, 1),
            "p90": round(baseline_output.project_duration_p90, 1),
            "mean": round(baseline_output.project_duration_mean, 1),
            "std": round(baseline_output.project_duration_std, 2),
        },
        "scenario": {
            "p50": round(scenario_output.project_duration_p50, 1),
            "p90": round(scenario_output.project_duration_p90, 1),
            "mean": round(scenario_output.project_duration_mean, 1),
            "std": round(scenario_output.project_duration_std, 2),
        },
        "comparison": {
            "p50_delta": round(comparison.p50_delta, 1),
            "p90_delta": round(comparison.p90_delta, 1),
            "mean_delta": round(comparison.mean_delta, 1),
            "std_delta": round(comparison.std_delta, 2),
            "risk_improved": comparison.risk_improved,
            "summary": comparison.summary,
        },
        "changes_applied": len(changes),
    }
