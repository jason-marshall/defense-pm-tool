"""EVMS Period endpoints for earned value tracking."""

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.models.evms_period import PeriodStatus
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

    await repo.delete(period_id)
    await db.commit()


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

    return EVMSPeriodDataResponse.model_validate(updated)


@router.get("/summary/{program_id}", response_model=EVMSSummaryResponse)
async def get_evms_summary(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    as_of_date: Annotated[date | None, Query(description="As-of date for summary")] = None,
) -> EVMSSummaryResponse:
    """Get current EVMS summary for a program."""
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

    return EVMSSummaryResponse(
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
