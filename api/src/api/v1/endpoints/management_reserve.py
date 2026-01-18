"""API endpoints for Management Reserve tracking.

Per EVMS Guideline 28, Management Reserve changes must be tracked and
documented with reasons. This module provides endpoints for MR management.
"""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import NotFoundError, ValidationError
from src.repositories.evms_period import EVMSPeriodRepository
from src.repositories.management_reserve_log import ManagementReserveLogRepository
from src.repositories.program import ProgramRepository
from src.schemas.management_reserve import (
    ManagementReserveChangeCreate,
    ManagementReserveHistoryResponse,
    ManagementReserveLogResponse,
    ManagementReserveStatus,
)

router = APIRouter()


@router.get("/{program_id}", response_model=ManagementReserveStatus)
async def get_management_reserve_status(
    db: DbSession,
    current_user: CurrentUser,
    program_id: UUID,
) -> ManagementReserveStatus:
    """
    Get current Management Reserve status for a program.

    Returns the current MR balance and summary statistics.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    repo = ManagementReserveLogRepository(db)
    logs = await repo.get_by_program(program_id)

    if not logs:
        # No MR history - return zero status
        return ManagementReserveStatus(
            program_id=program_id,
            current_balance=Decimal("0"),
            initial_mr=Decimal("0"),
            total_changes_in=Decimal("0"),
            total_changes_out=Decimal("0"),
            change_count=0,
            last_change_at=None,
        )

    # Calculate aggregates
    initial_mr = logs[0].beginning_mr
    total_in = sum((log.changes_in for log in logs), Decimal("0"))
    total_out = sum((log.changes_out for log in logs), Decimal("0"))
    current_balance = logs[-1].ending_mr
    last_change = logs[-1].created_at

    return ManagementReserveStatus(
        program_id=program_id,
        current_balance=current_balance,
        initial_mr=initial_mr,
        total_changes_in=total_in,
        total_changes_out=total_out,
        change_count=len(logs),
        last_change_at=last_change,
    )


@router.post(
    "/{program_id}/change",
    response_model=ManagementReserveLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_mr_change(
    db: DbSession,
    current_user: CurrentUser,
    program_id: UUID,
    change_data: ManagementReserveChangeCreate,
) -> ManagementReserveLogResponse:
    """
    Record a Management Reserve change.

    Creates a new MR log entry documenting the change with:
    - Amount added to MR (changes_in)
    - Amount released from MR (changes_out)
    - Reason for the change

    Per GL 28, MR changes must be documented for audit purposes.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Verify period if provided
    if change_data.period_id:
        period_repo = EVMSPeriodRepository(db)
        period = await period_repo.get(change_data.period_id)
        if not period:
            raise NotFoundError(
                f"Period {change_data.period_id} not found",
                "PERIOD_NOT_FOUND",
            )
        if period.program_id != program_id:
            raise ValidationError(
                "Period does not belong to the specified program",
                "PERIOD_PROGRAM_MISMATCH",
            )

    # Validate that at least one change is specified
    if change_data.changes_in == 0 and change_data.changes_out == 0:
        raise ValidationError(
            "At least one of changes_in or changes_out must be non-zero",
            "NO_MR_CHANGE",
        )

    repo = ManagementReserveLogRepository(db)

    # Get current MR balance
    latest = await repo.get_latest_for_program(program_id)
    beginning_mr = latest.ending_mr if latest else Decimal("0")

    # Calculate ending MR
    ending_mr = beginning_mr + change_data.changes_in - change_data.changes_out

    # Validate ending MR is not negative
    if ending_mr < 0:
        raise ValidationError(
            f"MR change would result in negative balance: {ending_mr}",
            "NEGATIVE_MR_BALANCE",
        )

    # Create the log entry
    log_data = {
        "program_id": program_id,
        "period_id": change_data.period_id,
        "beginning_mr": beginning_mr,
        "changes_in": change_data.changes_in,
        "changes_out": change_data.changes_out,
        "ending_mr": ending_mr,
        "reason": change_data.reason,
        "approved_by": current_user.id,
    }

    log_entry = await repo.create(log_data)
    await db.commit()
    await db.refresh(log_entry)

    return ManagementReserveLogResponse.model_validate(log_entry)


@router.post(
    "/{program_id}/initialize",
    response_model=ManagementReserveLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def initialize_mr(
    db: DbSession,
    current_user: CurrentUser,
    program_id: UUID,
    initial_amount: Decimal = Query(..., gt=0, description="Initial MR amount"),
    reason: str | None = Query(None, description="Reason for initial MR"),
) -> ManagementReserveLogResponse:
    """
    Initialize Management Reserve for a program.

    Creates the first MR log entry with the initial MR amount.
    This should be called once at program baseline.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    repo = ManagementReserveLogRepository(db)

    # Check if MR already initialized
    existing = await repo.get_latest_for_program(program_id)
    if existing:
        raise ValidationError(
            "Management Reserve already initialized for this program. Use /change endpoint.",
            "MR_ALREADY_INITIALIZED",
        )

    # Create initial log entry
    log_data = {
        "program_id": program_id,
        "period_id": None,
        "beginning_mr": Decimal("0"),
        "changes_in": initial_amount,
        "changes_out": Decimal("0"),
        "ending_mr": initial_amount,
        "reason": reason or "Initial Management Reserve allocation",
        "approved_by": current_user.id,
    }

    log_entry = await repo.create(log_data)
    await db.commit()
    await db.refresh(log_entry)

    return ManagementReserveLogResponse.model_validate(log_entry)


@router.get("/{program_id}/history", response_model=ManagementReserveHistoryResponse)
async def get_mr_history(
    db: DbSession,
    current_user: CurrentUser,
    program_id: UUID,
    limit: int = Query(12, ge=1, le=100, description="Maximum entries to return"),
) -> ManagementReserveHistoryResponse:
    """
    Get Management Reserve change history for a program.

    Returns MR log entries ordered by creation date (oldest first).
    Used for Format 5 reporting and audit trail.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    repo = ManagementReserveLogRepository(db)
    logs = await repo.get_history(program_id, limit=limit)

    # Get all logs for total count
    all_logs = await repo.get_by_program(program_id)
    total = len(all_logs)

    # Current balance from latest entry
    latest = await repo.get_latest_for_program(program_id)
    current_balance = latest.ending_mr if latest else Decimal("0")

    return ManagementReserveHistoryResponse(
        items=[ManagementReserveLogResponse.model_validate(log) for log in logs],
        total=total,
        program_id=program_id,
        current_balance=current_balance,
    )


@router.get("/{program_id}/log/{log_id}", response_model=ManagementReserveLogResponse)
async def get_mr_log_entry(
    db: DbSession,
    current_user: CurrentUser,
    program_id: UUID,
    log_id: UUID,
) -> ManagementReserveLogResponse:
    """
    Get a specific MR log entry by ID.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    repo = ManagementReserveLogRepository(db)
    log_entry = await repo.get(log_id)

    if not log_entry:
        raise NotFoundError(
            f"MR log entry {log_id} not found",
            "MR_LOG_NOT_FOUND",
        )

    # Verify log belongs to the program
    if log_entry.program_id != program_id:
        raise NotFoundError(
            f"MR log entry {log_id} not found in program {program_id}",
            "MR_LOG_NOT_FOUND",
        )

    return ManagementReserveLogResponse.model_validate(log_entry)


@router.get("/period/{period_id}", response_model=list[ManagementReserveLogResponse])
async def get_mr_logs_by_period(
    db: DbSession,
    current_user: CurrentUser,
    period_id: UUID,
) -> list[ManagementReserveLogResponse]:
    """
    Get MR log entries for a specific EVMS period.

    Returns all MR changes recorded in the specified period.
    """
    # Verify period exists
    period_repo = EVMSPeriodRepository(db)
    period = await period_repo.get(period_id)
    if not period:
        raise NotFoundError(f"Period {period_id} not found", "PERIOD_NOT_FOUND")

    repo = ManagementReserveLogRepository(db)
    logs = await repo.get_by_period(period_id)

    return [ManagementReserveLogResponse.model_validate(log) for log in logs]
