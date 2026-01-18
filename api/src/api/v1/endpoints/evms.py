"""EVMS Period endpoints for earned value tracking."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import Response

from src.core.cache import CacheKeys, cache_manager
from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.models.enums import EVMethod
from src.models.evms_period import PeriodStatus
from src.repositories.activity import ActivityRepository
from src.repositories.evms_period import EVMSPeriodDataRepository, EVMSPeriodRepository
from src.repositories.program import ProgramRepository
from src.repositories.wbs import WBSElementRepository
from src.schemas.evms_period import (
    EVMSPeriodCreate,
    EVMSPeriodDataCreate,
    EVMSPeriodDataResponse,
    EVMSPeriodDataUpdate,
    EVMSPeriodListResponse,
    EVMSPeriodResponse,
    EVMSPeriodUpdate,
    EVMSPeriodWithDataResponse,
    EVMSSummaryResponse,
)
from src.services.dashboard_cache import dashboard_cache
from src.services.ev_methods import get_ev_method_info, validate_milestone_weights
from src.services.evms import EVMSCalculator

router = APIRouter()


@router.get("/periods", response_model=EVMSPeriodListResponse)
async def list_periods(
    program_id: Annotated[UUID, Query(description="Program ID")],
    db: DbSession,
    current_user: CurrentUser,
    status: Annotated[PeriodStatus | None, Query(description="Filter by status")] = None,
    skip: int = 0,
    limit: int = 50,
) -> EVMSPeriodListResponse:
    """List all EVMS periods for a program."""
    # Verify program exists and user has access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to view EVMS periods for this program",
            "NOT_AUTHORIZED",
        )

    repo = EVMSPeriodRepository(db)
    periods = await repo.get_by_program(
        program_id,
        skip=skip,
        limit=limit,
        status=status,
    )

    return EVMSPeriodListResponse(
        items=[EVMSPeriodResponse.model_validate(p) for p in periods],
        total=len(periods),
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.get("/periods/{period_id}", response_model=EVMSPeriodWithDataResponse)
async def get_period(
    period_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> EVMSPeriodWithDataResponse:
    """Get an EVMS period with all its data."""
    repo = EVMSPeriodRepository(db)
    period = await repo.get_with_data(period_id)

    if not period:
        raise NotFoundError(f"EVMS period {period_id} not found", "PERIOD_NOT_FOUND")

    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(period.program_id)

    if not program:
        raise NotFoundError(f"Program {period.program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to view this EVMS period",
            "NOT_AUTHORIZED",
        )

    return EVMSPeriodWithDataResponse.model_validate(period)


@router.post("/periods", response_model=EVMSPeriodResponse, status_code=201)
async def create_period(
    period_in: EVMSPeriodCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> EVMSPeriodResponse:
    """Create a new EVMS reporting period."""
    # Verify program exists and user has access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(period_in.program_id)

    if not program:
        raise NotFoundError(
            f"Program {period_in.program_id} not found",
            "PROGRAM_NOT_FOUND",
        )

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to create EVMS periods for this program",
            "NOT_AUTHORIZED",
        )

    # Verify dates are valid
    if period_in.period_end < period_in.period_start:
        raise ValidationError(
            "Period end date must be after start date",
            "INVALID_DATES",
        )

    # Check for duplicate period
    repo = EVMSPeriodRepository(db)
    if await repo.period_exists(
        period_in.program_id,
        period_in.period_start,
        period_in.period_end,
    ):
        raise ConflictError(
            "An EVMS period with these dates already exists",
            "DUPLICATE_PERIOD",
        )

    period = await repo.create(period_in.model_dump())
    await db.commit()
    await db.refresh(period)

    # Invalidate dashboard caches for this program
    await dashboard_cache.invalidate_on_period_update(period_in.program_id)

    return EVMSPeriodResponse.model_validate(period)


@router.patch("/periods/{period_id}", response_model=EVMSPeriodResponse)
async def update_period(
    period_id: UUID,
    period_in: EVMSPeriodUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> EVMSPeriodResponse:
    """Update an EVMS period."""
    repo = EVMSPeriodRepository(db)
    period = await repo.get_by_id(period_id)

    if not period:
        raise NotFoundError(f"EVMS period {period_id} not found", "PERIOD_NOT_FOUND")

    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(period.program_id)

    if not program:
        raise NotFoundError(f"Program {period.program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to modify this EVMS period",
            "NOT_AUTHORIZED",
        )

    # Don't allow updating approved periods
    if period.status == PeriodStatus.APPROVED and not current_user.is_admin:
        raise ValidationError(
            "Cannot modify an approved period",
            "PERIOD_APPROVED",
        )

    updated = await repo.update(period, period_in.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(updated)

    # Invalidate dashboard caches for this program
    await dashboard_cache.invalidate_on_period_update(period.program_id)

    return EVMSPeriodResponse.model_validate(updated)


@router.delete("/periods/{period_id}", status_code=204)
async def delete_period(
    period_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete an EVMS period."""
    repo = EVMSPeriodRepository(db)
    period = await repo.get_by_id(period_id)

    if not period:
        raise NotFoundError(f"EVMS period {period_id} not found", "PERIOD_NOT_FOUND")

    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(period.program_id)

    if not program:
        raise NotFoundError(f"Program {period.program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to delete this EVMS period",
            "NOT_AUTHORIZED",
        )

    # Don't allow deleting approved periods
    if period.status == PeriodStatus.APPROVED and not current_user.is_admin:
        raise ValidationError(
            "Cannot delete an approved period",
            "PERIOD_APPROVED",
        )

    # Store program_id before deletion
    program_id_for_cache = period.program_id

    await repo.delete(period_id)
    await db.commit()

    # Invalidate dashboard caches for this program
    await dashboard_cache.invalidate_on_period_update(program_id_for_cache)


@router.post(
    "/periods/{period_id}/data",
    response_model=EVMSPeriodDataResponse,
    status_code=201,
)
async def add_period_data(
    period_id: UUID,
    data_in: EVMSPeriodDataCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> EVMSPeriodDataResponse:
    """Add EVMS data for a WBS element to a period."""
    # Get period and verify access
    period_repo = EVMSPeriodRepository(db)
    period = await period_repo.get_by_id(period_id)

    if not period:
        raise NotFoundError(f"EVMS period {period_id} not found", "PERIOD_NOT_FOUND")

    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(period.program_id)

    if not program:
        raise NotFoundError(f"Program {period.program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to modify this EVMS period",
            "NOT_AUTHORIZED",
        )

    # Verify period is not approved
    if period.status == PeriodStatus.APPROVED:
        raise ValidationError(
            "Cannot add data to an approved period",
            "PERIOD_APPROVED",
        )

    # Verify WBS element exists and belongs to same program
    wbs_repo = WBSElementRepository(db)
    wbs = await wbs_repo.get_by_id(data_in.wbs_id)

    if not wbs:
        raise NotFoundError(
            f"WBS element {data_in.wbs_id} not found",
            "WBS_NOT_FOUND",
        )

    if wbs.program_id != period.program_id:
        raise ValidationError(
            "WBS element does not belong to the same program",
            "WBS_PROGRAM_MISMATCH",
        )

    # Check for duplicate
    data_repo = EVMSPeriodDataRepository(db)
    if await data_repo.data_exists(period_id, data_in.wbs_id):
        raise ConflictError(
            "Data for this WBS element already exists in this period",
            "DUPLICATE_PERIOD_DATA",
        )

    # Get previous period data for cumulative calculations
    prev_data = await data_repo.get_previous_period_data(
        period.program_id,
        data_in.wbs_id,
        period.period_start,
    )

    # Calculate cumulative values
    data_dict = data_in.model_dump()
    data_dict["period_id"] = period_id

    if prev_data:
        data_dict["cumulative_bcws"] = prev_data.cumulative_bcws + data_in.bcws
        data_dict["cumulative_bcwp"] = prev_data.cumulative_bcwp + data_in.bcwp
        data_dict["cumulative_acwp"] = prev_data.cumulative_acwp + data_in.acwp
    else:
        data_dict["cumulative_bcws"] = data_in.bcws
        data_dict["cumulative_bcwp"] = data_in.bcwp
        data_dict["cumulative_acwp"] = data_in.acwp

    # Calculate derived metrics
    cumulative_bcwp = data_dict["cumulative_bcwp"]
    cumulative_bcws = data_dict["cumulative_bcws"]
    cumulative_acwp = data_dict["cumulative_acwp"]

    data_dict["cv"] = cumulative_bcwp - cumulative_acwp
    data_dict["sv"] = cumulative_bcwp - cumulative_bcws
    data_dict["cpi"] = EVMSCalculator.calculate_cpi(cumulative_bcwp, cumulative_acwp)
    data_dict["spi"] = EVMSCalculator.calculate_spi(cumulative_bcwp, cumulative_bcws)

    period_data = await data_repo.create(data_dict)

    # Update period totals
    await period_repo.update_cumulative_totals(period_id)

    await db.commit()
    await db.refresh(period_data)

    # Invalidate EVMS cache for this program
    await cache_manager.invalidate_evms(str(period.program_id))

    return EVMSPeriodDataResponse.model_validate(period_data)


@router.patch(
    "/periods/{period_id}/data/{data_id}",
    response_model=EVMSPeriodDataResponse,
)
async def update_period_data(
    period_id: UUID,
    data_id: UUID,
    data_in: EVMSPeriodDataUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> EVMSPeriodDataResponse:
    """Update EVMS data for a period."""
    # Get period and verify access
    period_repo = EVMSPeriodRepository(db)
    period = await period_repo.get_by_id(period_id)

    if not period:
        raise NotFoundError(f"EVMS period {period_id} not found", "PERIOD_NOT_FOUND")

    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(period.program_id)

    if not program:
        raise NotFoundError(f"Program {period.program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to modify this EVMS period",
            "NOT_AUTHORIZED",
        )

    if period.status == PeriodStatus.APPROVED:
        raise ValidationError(
            "Cannot modify data in an approved period",
            "PERIOD_APPROVED",
        )

    # Get the period data
    data_repo = EVMSPeriodDataRepository(db)
    period_data = await data_repo.get_by_id(data_id)

    if not period_data or period_data.period_id != period_id:
        raise NotFoundError(
            f"Period data {data_id} not found in period {period_id}",
            "PERIOD_DATA_NOT_FOUND",
        )

    # Update values
    update_dict = data_in.model_dump(exclude_unset=True)

    # Recalculate cumulative and derived values if base values changed
    if any(k in update_dict for k in ["bcws", "bcwp", "acwp"]):
        # Get previous period data
        prev_data = await data_repo.get_previous_period_data(
            period.program_id,
            period_data.wbs_id,
            period.period_start,
        )

        new_bcws = update_dict.get("bcws", period_data.bcws)
        new_bcwp = update_dict.get("bcwp", period_data.bcwp)
        new_acwp = update_dict.get("acwp", period_data.acwp)

        if prev_data:
            update_dict["cumulative_bcws"] = prev_data.cumulative_bcws + new_bcws
            update_dict["cumulative_bcwp"] = prev_data.cumulative_bcwp + new_bcwp
            update_dict["cumulative_acwp"] = prev_data.cumulative_acwp + new_acwp
        else:
            update_dict["cumulative_bcws"] = new_bcws
            update_dict["cumulative_bcwp"] = new_bcwp
            update_dict["cumulative_acwp"] = new_acwp

        # Recalculate metrics
        cumulative_bcwp = update_dict["cumulative_bcwp"]
        cumulative_bcws = update_dict["cumulative_bcws"]
        cumulative_acwp = update_dict["cumulative_acwp"]

        update_dict["cv"] = cumulative_bcwp - cumulative_acwp
        update_dict["sv"] = cumulative_bcwp - cumulative_bcws
        update_dict["cpi"] = EVMSCalculator.calculate_cpi(cumulative_bcwp, cumulative_acwp)
        update_dict["spi"] = EVMSCalculator.calculate_spi(cumulative_bcwp, cumulative_bcws)

    updated = await data_repo.update(period_data, update_dict)

    # Update period totals
    await period_repo.update_cumulative_totals(period_id)

    await db.commit()
    await db.refresh(updated)

    # Invalidate EVMS cache for this program
    await cache_manager.invalidate_evms(str(period.program_id))

    return EVMSPeriodDataResponse.model_validate(updated)


@router.get("/summary/{program_id}", response_model=EVMSSummaryResponse)
async def get_evms_summary(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    as_of_date: Annotated[date | None, Query(description="As-of date for summary")] = None,
    skip_cache: Annotated[bool, Query(description="Skip cache and fetch fresh data")] = False,
) -> EVMSSummaryResponse:
    """
    Get current EVMS summary for a program.

    Summary data is cached for 5 minutes to improve performance.
    """
    # Verify program exists and user has access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to view EVMS summary for this program",
            "NOT_AUTHORIZED",
        )

    # Try cache for current summary (no as_of_date filter)
    cache_key = CacheKeys.evms_summary_key(str(program_id))
    if not as_of_date and not skip_cache:
        cached = await cache_manager.get(cache_key)
        if cached:
            return EVMSSummaryResponse(**cached)

    # Get the latest period (or period as of the given date)
    period_repo = EVMSPeriodRepository(db)

    if as_of_date:
        periods = await period_repo.get_by_date_range(program_id, program.start_date, as_of_date)
        period = periods[-1] if periods else None
    else:
        period = await period_repo.get_latest_period(program_id)

    # Calculate summary metrics
    bac = program.budget_at_completion
    bcws = period.cumulative_bcws if period else Decimal("0.00")
    bcwp = period.cumulative_bcwp if period else Decimal("0.00")
    acwp = period.cumulative_acwp if period else Decimal("0.00")

    cv = EVMSCalculator.calculate_cost_variance(bcwp, acwp)
    sv = EVMSCalculator.calculate_schedule_variance(bcwp, bcws)
    cpi = EVMSCalculator.calculate_cpi(bcwp, acwp)
    spi = EVMSCalculator.calculate_spi(bcwp, bcws)

    eac = EVMSCalculator.calculate_eac(bac, acwp, bcwp, "cpi") if cpi else None
    etc = EVMSCalculator.calculate_etc(eac, acwp) if eac else None
    vac = EVMSCalculator.calculate_vac(bac, eac) if eac else None
    tcpi = EVMSCalculator.calculate_tcpi(bac, bcwp, acwp, "bac")

    percent_complete = (bcwp / bac * 100).quantize(Decimal("0.01")) if bac > 0 else Decimal("0.00")

    response = EVMSSummaryResponse(
        program_id=program_id,
        as_of_date=as_of_date or (period.period_end if period else date.today()),
        bac=bac,
        bcws=bcws,
        bcwp=bcwp,
        acwp=acwp,
        cv=cv,
        sv=sv,
        cpi=cpi,
        spi=spi,
        eac=eac,
        etc=etc,
        vac=vac,
        tcpi=tcpi,
        percent_complete=percent_complete,
    )

    # Cache current summary (not historical as_of_date queries)
    if not as_of_date:
        await cache_manager.set(
            cache_key,
            response.model_dump(mode="json"),
            ttl=CacheKeys.EVMS_TTL,
        )

    return response


# =============================================================================
# EV Method Endpoints
# =============================================================================


@router.get("/ev-methods")
async def list_ev_methods() -> list[dict[str, Any]]:
    """
    List all available EV calculation methods.

    Returns information about each method including:
    - Value (used in API)
    - Display name
    - Description
    - Recommended task duration
    """
    return get_ev_method_info()


@router.post("/activities/{activity_id}/ev-method")
async def set_activity_ev_method(
    activity_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    ev_method: Annotated[str, Query(description="EV method to set")],
    milestones: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Set the EV calculation method for an activity.

    For milestone-weight method, provide milestones with weights summing to 1.0.
    """
    activity_repo = ActivityRepository(db)
    activity = await activity_repo.get_by_id(activity_id)

    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")

    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity.program_id)

    if not program:
        raise NotFoundError(f"Program {activity.program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to modify this activity",
            "NOT_AUTHORIZED",
        )

    # Validate EV method value
    try:
        method = EVMethod(ev_method)
    except ValueError as e:
        valid_methods = [m.value for m in EVMethod]
        raise ValidationError(
            f"Invalid EV method '{ev_method}'. Valid methods: {valid_methods}",
            "INVALID_EV_METHOD",
        ) from e

    # Validate milestone weights if using milestone method
    if method == EVMethod.MILESTONE_WEIGHT:
        if not milestones:
            raise ValidationError(
                "Milestones are required for milestone-weight method",
                "MILESTONES_REQUIRED",
            )
        if not validate_milestone_weights(milestones):
            raise ValidationError(
                "Milestone weights must sum to 1.0 (100%)",
                "INVALID_MILESTONE_WEIGHTS",
            )

    # Update activity
    update_dict: dict[str, Any] = {"ev_method": method.value}
    if milestones:
        update_dict["milestones_json"] = milestones

    await activity_repo.update(activity, update_dict)
    await db.commit()

    return {
        "activity_id": str(activity_id),
        "ev_method": method.value,
        "ev_method_display": method.display_name,
        "milestones": milestones,
    }


# =============================================================================
# EAC Methods Comparison Endpoint
# =============================================================================


@router.get("/eac-methods/{program_id}")
async def calculate_all_eac_methods(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    period_id: Annotated[UUID | None, Query(description="Specific period ID")] = None,
) -> list[dict[str, Any]]:
    """
    Calculate EAC using all available methods for comparison.

    Returns EAC results from all applicable methods:
    - CPI Method: BAC / CPI
    - Typical Method: ACWP + (BAC - BCWP)
    - Mathematical Method: ACWP + (BAC - BCWP) / CPI
    - Comprehensive Method: ACWP + (BAC - BCWP) / (CPI x SPI)
    - Composite Method: Weighted average based on completion %

    Per EVMS GL 27, comparing multiple EAC methods helps identify
    the most appropriate estimate for the program's situation.
    """
    # Verify program exists and user has access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to view EAC methods for this program",
            "NOT_AUTHORIZED",
        )

    # Get EVMS period data
    period_repo = EVMSPeriodRepository(db)

    if period_id:
        period = await period_repo.get_by_id(period_id)
        if not period:
            raise NotFoundError(f"Period {period_id} not found", "PERIOD_NOT_FOUND")
        if period.program_id != program_id:
            raise ValidationError(
                "Period does not belong to this program",
                "PERIOD_PROGRAM_MISMATCH",
            )
    else:
        # Use latest period
        period = await period_repo.get_latest_period(program_id)

    if not period:
        raise NotFoundError(
            "No EVMS periods found for this program",
            "NO_PERIODS",
        )

    # Get cumulative values
    bcws = period.cumulative_bcws or Decimal("0")
    bcwp = period.cumulative_bcwp or Decimal("0")
    acwp = period.cumulative_acwp or Decimal("0")
    bac = program.budget_at_completion or Decimal("0")

    if bac == 0:
        raise ValidationError(
            "Program BAC is zero - cannot calculate EAC methods",
            "ZERO_BAC",
        )

    # Calculate all EAC methods
    results = EVMSCalculator.calculate_all_eac_methods(
        bcws=bcws,
        bcwp=bcwp,
        acwp=acwp,
        bac=bac,
    )

    return [
        {
            "method": r.method.value,
            "method_name": r.method.name,
            "eac": str(r.eac),
            "etc": str(r.etc),
            "vac": str(r.vac),
            "description": r.description,
        }
        for r in results
    ]


# =============================================================================
# Enhanced S-Curve Endpoint
# =============================================================================


@router.get("/s-curve-enhanced/{program_id}")
async def get_enhanced_scurve(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    skip_cache: Annotated[bool, Query(description="Skip cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """
    Get S-curve with Monte Carlo confidence bands.

    Returns historical BCWS/BCWP/ACWP data with forecast ranges derived
    from Monte Carlo simulation results.

    Response includes:
    - Historical data points with cumulative BCWS, BCWP, ACWP
    - EAC range (P10/P50/P90) based on simulation uncertainty
    - Completion date range (P10/P50/P90) from duration simulation
    - Percent complete
    """
    from src.repositories.simulation import (
        SimulationConfigRepository,
        SimulationResultRepository,
    )
    from src.services.scurve_enhanced import (
        EnhancedSCurveService,
        build_simulation_metrics_from_result,
    )

    # Verify program exists and user has access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError(
            "Not authorized to view S-curve for this program",
            "NOT_AUTHORIZED",
        )

    # Check cache first
    if not skip_cache:
        cached = await dashboard_cache.get_scurve(program_id, enhanced=True)
        if cached:
            cached["from_cache"] = True
            return cached

    # Get EVMS periods for S-curve data
    period_repo = EVMSPeriodRepository(db)
    periods = await period_repo.get_by_program(program_id, limit=1000)

    # Sort by period end date (ascending for chronological order)
    periods = sorted(periods, key=lambda p: p.period_end)

    # Get latest simulation result if available
    simulation_metrics = None
    config_repo = SimulationConfigRepository(db)
    result_repo = SimulationResultRepository(db)

    configs = await config_repo.get_by_program(program_id, limit=1)
    if configs:
        latest_result = await result_repo.get_completed_by_config(configs[0].id)
        if latest_result:
            simulation_metrics = build_simulation_metrics_from_result(latest_result)

    # Generate enhanced S-curve
    service = EnhancedSCurveService(
        program_id=program_id,
        periods=periods,
        bac=program.budget_at_completion or Decimal("0"),
        simulation_metrics=simulation_metrics,
        start_date=program.start_date,
    )

    result = service.generate()

    # Build response
    response: dict[str, Any] = {
        "program_id": str(result.program_id),
        "bac": str(result.bac),
        "current_period": result.current_period,
        "percent_complete": str(result.percent_complete),
        "simulation_available": result.simulation_available,
        "data_points": [
            {
                "period_number": dp.period_number,
                "period_date": dp.period_date.isoformat(),
                "period_name": dp.period_name,
                "bcws": str(dp.bcws),
                "bcwp": str(dp.bcwp),
                "acwp": str(dp.acwp),
                "cumulative_bcws": str(dp.cumulative_bcws),
                "cumulative_bcwp": str(dp.cumulative_bcwp),
                "cumulative_acwp": str(dp.cumulative_acwp),
                "is_forecast": dp.is_forecast,
            }
            for dp in result.data_points
        ],
    }

    # Add EAC range if available
    if result.eac_range:
        response["eac_range"] = {
            "p10": str(result.eac_range.p10),
            "p50": str(result.eac_range.p50),
            "p90": str(result.eac_range.p90),
            "method": result.eac_range.method,
        }

    # Add completion range if available
    if result.completion_range:
        response["completion_range"] = {
            "p10_days": result.completion_range.p10_days,
            "p50_days": result.completion_range.p50_days,
            "p90_days": result.completion_range.p90_days,
            "p10_date": (
                result.completion_range.p10_date.isoformat()
                if result.completion_range.p10_date
                else None
            ),
            "p50_date": (
                result.completion_range.p50_date.isoformat()
                if result.completion_range.p50_date
                else None
            ),
            "p90_date": (
                result.completion_range.p90_date.isoformat()
                if result.completion_range.p90_date
                else None
            ),
        }

    # Cache the result
    await dashboard_cache.set_scurve(program_id, response, enhanced=True)
    response["from_cache"] = False

    return response


# =============================================================================
# S-Curve Export Endpoint
# =============================================================================


@router.get("/s-curve/{program_id}/export")
async def export_scurve(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    format: Annotated[str, Query(description="Export format: png or svg")] = "png",
    width: Annotated[int, Query(description="Image width in inches", ge=6, le=24)] = 12,
    height: Annotated[int, Query(description="Image height in inches", ge=4, le=18)] = 8,
    dpi: Annotated[int, Query(description="DPI for PNG export", ge=72, le=300)] = 150,
    title: Annotated[str | None, Query(description="Custom chart title")] = None,
    show_confidence_bands: Annotated[
        bool, Query(description="Show Monte Carlo confidence bands")
    ] = True,
) -> Response:
    """
    Export S-curve chart as PNG or SVG image.

    Generates a publication-quality S-curve visualization with:
    - Planned Value (BCWS) line
    - Earned Value (BCWP) line
    - Actual Cost (ACWP) line
    - Optional confidence bands from Monte Carlo simulation

    Returns the image file as bytes with appropriate content type.
    """
    from fastapi.responses import Response

    from src.services.scurve_export import SCurveExportConfig, scurve_exporter

    # Validate format
    format_lower = format.lower()
    if format_lower not in ["png", "svg"]:
        raise ValidationError(
            f"Invalid export format '{format}'. Use 'png' or 'svg'.",
            "INVALID_FORMAT",
        )

    # Get the enhanced S-curve data (reuse the endpoint logic)
    scurve_data = await get_enhanced_scurve(
        program_id=program_id,
        db=db,
        current_user=current_user,
        skip_cache=False,
    )

    # Create export config
    config = SCurveExportConfig(
        width=width,
        height=height,
        dpi=dpi,
        title=title or f"S-Curve Analysis - Program {program_id}",
        show_confidence_bands=show_confidence_bands,
    )

    # Export to requested format
    if format_lower == "png":
        image_bytes = scurve_exporter.export_png(scurve_data, config)
        media_type = "image/png"
        filename = f"scurve_{program_id}.png"
    else:
        image_bytes = scurve_exporter.export_svg(scurve_data, config)
        media_type = "image/svg+xml"
        filename = f"scurve_{program_id}.svg"

    return Response(
        content=image_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
