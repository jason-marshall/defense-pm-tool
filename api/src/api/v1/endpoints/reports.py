"""Report generation endpoints."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.api.v1.endpoints.dependencies import CurrentUser
from src.core.deps import DbSession
from src.core.exceptions import AuthorizationError, NotFoundError
from src.repositories.baseline import BaselineRepository
from src.repositories.evms_period import EVMSPeriodRepository
from src.repositories.program import ProgramRepository
from src.repositories.wbs import WBSElementRepository
from src.services.cpr_format3_generator import CPRFormat3Generator
from src.services.report_generator import ReportGenerator

router = APIRouter()


@router.get("/cpr/{program_id}")
async def generate_cpr_format1(
    program_id: UUID,
    db: DbSession,
    period_id: Annotated[UUID | None, Query(description="Specific period ID")] = None,
) -> dict[str, Any]:
    """
    Generate CPR Format 1 (WBS Summary) report.

    Returns JSON representation of the report.
    If period_id is not specified, uses the latest approved period
    (or latest period if none approved).
    """
    # Get program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Get period
    period_repo = EVMSPeriodRepository(db)

    if period_id:
        period = await period_repo.get_with_data(period_id)
        if not period:
            raise NotFoundError(f"Period {period_id} not found", "PERIOD_NOT_FOUND")
    else:
        # Get latest period
        period = await period_repo.get_latest_period(program_id)
        if not period:
            raise NotFoundError(
                "No EVMS periods found for this program",
                "NO_PERIODS_FOUND",
            )
        # Load period data
        period = await period_repo.get_with_data(period.id)

    # Get WBS elements
    wbs_repo = WBSElementRepository(db)
    wbs_elements = await wbs_repo.get_by_program(program_id)

    # Generate report
    generator = ReportGenerator(
        program=program,
        period=period,
        period_data=list(period.period_data) if period.period_data else [],
        wbs_elements=wbs_elements,
    )

    report = generator.generate_cpr_format1()
    return generator.to_dict(report)


@router.get("/cpr/{program_id}/html", response_class=HTMLResponse)
async def generate_cpr_format1_html(
    program_id: UUID,
    db: DbSession,
    period_id: Annotated[UUID | None, Query(description="Specific period ID")] = None,
) -> HTMLResponse:
    """
    Generate CPR Format 1 (WBS Summary) report as HTML.

    Returns HTML that can be viewed in browser or printed to PDF.
    """
    # Get program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Get period
    period_repo = EVMSPeriodRepository(db)

    if period_id:
        period = await period_repo.get_with_data(period_id)
        if not period:
            raise NotFoundError(f"Period {period_id} not found", "PERIOD_NOT_FOUND")
    else:
        period = await period_repo.get_latest_period(program_id)
        if not period:
            raise NotFoundError(
                "No EVMS periods found for this program",
                "NO_PERIODS_FOUND",
            )
        period = await period_repo.get_with_data(period.id)

    # Get WBS elements
    wbs_repo = WBSElementRepository(db)
    wbs_elements = await wbs_repo.get_by_program(program_id)

    # Generate report
    generator = ReportGenerator(
        program=program,
        period=period,
        period_data=list(period.period_data) if period.period_data else [],
        wbs_elements=wbs_elements,
    )

    report = generator.generate_cpr_format1()
    html_content = generator.to_html(report)

    return HTMLResponse(content=html_content)


@router.get("/summary/{program_id}")
async def get_program_report_summary(
    program_id: UUID,
    db: DbSession,
) -> dict[str, Any]:
    """
    Get a summary of available reports for a program.

    Returns list of available periods and their status.
    """
    # Get program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Get periods
    period_repo = EVMSPeriodRepository(db)
    periods = await period_repo.get_by_program(program_id)

    return {
        "program_id": str(program_id),
        "program_name": program.name,
        "available_periods": [
            {
                "period_id": str(p.id),
                "period_name": p.period_name,
                "period_start": p.period_start.isoformat(),
                "period_end": p.period_end.isoformat(),
                "status": p.status.value,
            }
            for p in periods
        ],
        "available_reports": [
            {
                "report_type": "cpr_format1",
                "name": "CPR Format 1 - WBS Summary",
                "description": "Contract Performance Report showing WBS-level EVMS metrics",
                "formats": ["json", "html"],
            },
            {
                "report_type": "cpr_format3",
                "name": "CPR Format 3 - Baseline",
                "description": "Time-phased PMB with actual performance overlay",
                "formats": ["json"],
            },
        ],
    }


@router.get("/cpr-format3/{program_id}")
async def generate_cpr_format3(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    baseline_id: Annotated[
        UUID | None, Query(description="Specific baseline ID (defaults to approved PMB)")
    ] = None,
) -> dict[str, Any]:
    """
    Generate CPR Format 3 (Baseline) report.

    Shows time-phased Performance Measurement Baseline (PMB)
    with actual performance overlay per DFARS requirements.

    Returns:
    - Time-phased BCWS/BCWP/ACWP data
    - Cumulative performance metrics
    - Schedule variance in days
    - Forecast completion date based on SPI

    Args:
        program_id: Program ID to generate report for
        baseline_id: Optional specific baseline (defaults to approved PMB)
    """
    # Get program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Check authorization
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied to this program")

    # Get baseline
    baseline_repo = BaselineRepository(db)
    if baseline_id:
        baseline = await baseline_repo.get_by_id(baseline_id)
        if not baseline:
            raise NotFoundError(f"Baseline {baseline_id} not found", "BASELINE_NOT_FOUND")
        if baseline.program_id != program_id:
            raise NotFoundError("Baseline does not belong to this program", "BASELINE_MISMATCH")
    else:
        # Default to approved baseline (PMB)
        baseline = await baseline_repo.get_approved_baseline(program_id)
        if not baseline:
            # Fall back to latest baseline
            baselines = await baseline_repo.get_by_program(program_id)
            if baselines:
                baseline = baselines[0]  # Latest by version
            else:
                raise NotFoundError(
                    "No baseline found for program. Create a baseline first.",
                    "NO_BASELINE_FOUND",
                )

    # Get EVMS periods
    evms_repo = EVMSPeriodRepository(db)
    periods = await evms_repo.get_by_program(program_id)

    # Generate report
    generator = CPRFormat3Generator(program, baseline, periods)
    return generator.to_dict()
