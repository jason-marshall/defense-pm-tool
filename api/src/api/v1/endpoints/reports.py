"""Report generation endpoints."""

import hashlib
from dataclasses import asdict
from decimal import Decimal
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, Response

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import AuthorizationError, NotFoundError
from src.core.rate_limit import RATE_LIMIT_REPORTS, limiter
from src.repositories.baseline import BaselineRepository
from src.repositories.evms_period import EVMSPeriodRepository
from src.repositories.management_reserve_log import ManagementReserveLogRepository
from src.repositories.program import ProgramRepository
from src.repositories.report_audit import ReportAuditRepository
from src.repositories.variance_explanation import VarianceExplanationRepository
from src.repositories.wbs import WBSElementRepository
from src.schemas.cpr_format5 import Format5ExportConfig
from src.schemas.report_audit import (
    ReportAuditListResponse,
    ReportAuditResponse,
    ReportAuditStats,
)
from src.services.cpr_format3_generator import CPRFormat3Generator
from src.services.cpr_format5_generator import CPRFormat5Generator
from src.services.report_generator import ReportGenerator
from src.services.report_pdf_generator import PDFConfig, ReportPDFGenerator

router = APIRouter()


def _compute_checksum(data: bytes) -> str:
    """Compute SHA256 checksum of data."""
    return hashlib.sha256(data).hexdigest()


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
        latest_period = await period_repo.get_latest_period(program_id)
        if not latest_period:
            raise NotFoundError(
                "No EVMS periods found for this program",
                "NO_PERIODS_FOUND",
            )
        # Load period data
        period = await period_repo.get_with_data(latest_period.id)
        if not period:
            raise NotFoundError(
                "Failed to load period data",
                "PERIOD_NOT_FOUND",
            )

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
        latest_period = await period_repo.get_latest_period(program_id)
        if not latest_period:
            raise NotFoundError(
                "No EVMS periods found for this program",
                "NO_PERIODS_FOUND",
            )
        period = await period_repo.get_with_data(latest_period.id)
        if not period:
            raise NotFoundError(
                "Failed to load period data",
                "PERIOD_NOT_FOUND",
            )

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
            {
                "report_type": "cpr_format5",
                "name": "CPR Format 5 - EVMS",
                "description": (
                    "Detailed EVMS report with 6 EAC methods, "
                    "variance explanations, and MR tracking"
                ),
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
    generator = CPRFormat3Generator(cast("Any", program), baseline, cast("Any", periods))
    return generator.to_dict()


@router.get("/cpr-format5/{program_id}")
async def generate_cpr_format5(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    periods_to_include: Annotated[
        int, Query(description="Number of periods to include", ge=1, le=36)
    ] = 12,
    variance_threshold: Annotated[
        Decimal, Query(description="Variance threshold percentage for explanations")
    ] = Decimal("10"),
    include_mr: Annotated[bool, Query(description="Include Management Reserve tracking")] = True,
    include_explanations: Annotated[
        bool, Query(description="Include variance explanations")
    ] = True,
    manager_etc: Annotated[
        Decimal | None, Query(description="Manager's estimate to complete for independent EAC")
    ] = None,
) -> dict[str, Any]:
    """
    Generate CPR Format 5 (EVMS) report.

    Provides detailed EVMS performance data per DFARS requirements:
    - Monthly/quarterly BCWS, BCWP, ACWP data
    - All 6 EAC calculation methods per GL 27
    - Variance percentages and trends
    - Management Reserve (MR) changes
    - Narrative variance explanations

    Args:
        program_id: Program ID to generate report for
        periods_to_include: Number of periods to include (default 12)
        variance_threshold: Percentage threshold for variance explanations
        include_mr: Whether to include MR tracking
        include_explanations: Whether to include variance explanations
        manager_etc: Optional manager's ETC for independent EAC method

    Returns:
        Complete CPR Format 5 report as JSON
    """
    # Get program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Check authorization
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied to this program")

    # Get EVMS periods
    evms_repo = EVMSPeriodRepository(db)
    periods = await evms_repo.get_by_program(program_id)

    if not periods:
        raise NotFoundError(
            "No EVMS periods found for this program",
            "NO_PERIODS_FOUND",
        )

    # Get variance explanations if requested
    variance_explanations = []
    if include_explanations:
        ve_repo = VarianceExplanationRepository(db)
        variance_explanations = await ve_repo.get_by_program(program_id)

    # Get MR logs if requested
    mr_logs = []
    if include_mr:
        mr_repo = ManagementReserveLogRepository(db)
        mr_logs = await mr_repo.get_history(program_id, limit=periods_to_include)

    # Create configuration
    config = Format5ExportConfig(
        include_mr=include_mr,
        include_explanations=include_explanations,
        variance_threshold_percent=variance_threshold,
        periods_to_include=periods_to_include,
        include_eac_analysis=True,
    )

    # Generate report
    generator = CPRFormat5Generator(
        program=program,
        periods=periods,
        config=config,
        variance_explanations=variance_explanations,
        mr_logs=mr_logs,
        manager_etc=manager_etc,
    )
    report = generator.generate()

    # Convert to dictionary for JSON response
    return _format5_to_dict(report)


def _format5_to_dict(report: Any) -> dict[str, Any]:
    """Convert CPRFormat5Report dataclass to JSON-serializable dictionary.

    Args:
        report: CPRFormat5Report dataclass instance

    Returns:
        Dictionary with all values converted to JSON-serializable types
    """
    result = asdict(report)

    # Convert Decimal to string for JSON serialization
    def convert_decimals(obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_decimals(item) for item in obj]
        return obj

    return cast("dict[str, Any]", convert_decimals(result))


# ============================================================================
# PDF Export Endpoints
# ============================================================================


@router.get("/cpr/{program_id}/pdf")
@limiter.limit(RATE_LIMIT_REPORTS)
async def generate_cpr_format1_pdf(
    request: Request,
    program_id: UUID,
    db: DbSession,
    period_id: Annotated[UUID | None, Query(description="Specific period ID")] = None,
    landscape: Annotated[bool, Query(description="Use landscape orientation")] = True,
) -> Response:
    """
    Generate CPR Format 1 (WBS Summary) report as PDF.

    Returns a downloadable PDF file.
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
        latest_period = await period_repo.get_latest_period(program_id)
        if not latest_period:
            raise NotFoundError(
                "No EVMS periods found for this program",
                "NO_PERIODS_FOUND",
            )
        period = await period_repo.get_with_data(latest_period.id)
        if not period:
            raise NotFoundError(
                "Failed to load period data",
                "PERIOD_NOT_FOUND",
            )

    # Get WBS elements
    wbs_repo = WBSElementRepository(db)
    wbs_elements = await wbs_repo.get_by_program(program_id)

    # Generate report data
    generator = ReportGenerator(
        program=program,
        period=period,
        period_data=list(period.period_data) if period.period_data else [],
        wbs_elements=wbs_elements,
    )
    report = generator.generate_cpr_format1()

    # Generate PDF
    pdf_config = PDFConfig(landscape_mode=landscape)
    pdf_generator = ReportPDFGenerator(config=pdf_config)
    pdf_bytes = pdf_generator.generate_format1_pdf(report)

    filename = f"CPR_Format1_{program.code}_{period.period_name.replace(' ', '_')}.pdf"

    # Log audit trail
    audit_repo = ReportAuditRepository(db)
    await audit_repo.log_generation(
        report_type="cpr_format_1",
        program_id=program_id,
        generated_by=None,  # Format 1 doesn't require auth in current impl
        parameters={
            "period_id": str(period_id) if period_id else None,
            "landscape": landscape,
        },
        file_format="pdf",
        file_size=len(pdf_bytes),
        checksum=_compute_checksum(pdf_bytes),
    )
    await db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cpr-format3/{program_id}/pdf")
@limiter.limit(RATE_LIMIT_REPORTS)
async def generate_cpr_format3_pdf(
    request: Request,
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    baseline_id: Annotated[
        UUID | None, Query(description="Specific baseline ID (defaults to approved PMB)")
    ] = None,
    landscape: Annotated[bool, Query(description="Use landscape orientation")] = True,
) -> Response:
    """
    Generate CPR Format 3 (Baseline) report as PDF.

    Shows time-phased Performance Measurement Baseline (PMB)
    with actual performance overlay per DFARS requirements.
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
        baseline = await baseline_repo.get_approved_baseline(program_id)
        if not baseline:
            baselines = await baseline_repo.get_by_program(program_id)
            if baselines:
                baseline = baselines[0]
            else:
                raise NotFoundError(
                    "No baseline found for program. Create a baseline first.",
                    "NO_BASELINE_FOUND",
                )

    # Get EVMS periods
    evms_repo = EVMSPeriodRepository(db)
    periods = await evms_repo.get_by_program(program_id)

    # Generate report data
    generator = CPRFormat3Generator(cast("Any", program), baseline, cast("Any", periods))
    report = generator.generate()

    # Generate PDF
    pdf_config = PDFConfig(landscape_mode=landscape)
    pdf_generator = ReportPDFGenerator(config=pdf_config)
    pdf_bytes = pdf_generator.generate_format3_pdf(report)

    filename = f"CPR_Format3_{program.code}_{baseline.name.replace(' ', '_')}.pdf"

    # Log audit trail
    audit_repo = ReportAuditRepository(db)
    await audit_repo.log_generation(
        report_type="cpr_format_3",
        program_id=program_id,
        generated_by=current_user.id,
        parameters={
            "baseline_id": str(baseline_id) if baseline_id else None,
            "landscape": landscape,
        },
        file_format="pdf",
        file_size=len(pdf_bytes),
        checksum=_compute_checksum(pdf_bytes),
    )
    await db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cpr-format5/{program_id}/pdf")
@limiter.limit(RATE_LIMIT_REPORTS)
async def generate_cpr_format5_pdf(
    request: Request,
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    periods_to_include: Annotated[
        int, Query(description="Number of periods to include", ge=1, le=36)
    ] = 12,
    variance_threshold: Annotated[
        Decimal, Query(description="Variance threshold percentage for explanations")
    ] = Decimal("10"),
    include_mr: Annotated[bool, Query(description="Include Management Reserve tracking")] = True,
    include_explanations: Annotated[
        bool, Query(description="Include variance explanations")
    ] = True,
    manager_etc: Annotated[
        Decimal | None, Query(description="Manager's estimate to complete for independent EAC")
    ] = None,
    landscape: Annotated[bool, Query(description="Use landscape orientation")] = True,
) -> Response:
    """
    Generate CPR Format 5 (EVMS) report as PDF.

    Provides detailed EVMS performance data per DFARS requirements:
    - Monthly/quarterly BCWS, BCWP, ACWP data
    - All 6 EAC calculation methods per GL 27
    - Variance percentages and trends
    - Management Reserve (MR) changes
    - Narrative variance explanations
    """
    # Get program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Check authorization
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied to this program")

    # Get EVMS periods
    evms_repo = EVMSPeriodRepository(db)
    periods = await evms_repo.get_by_program(program_id)

    if not periods:
        raise NotFoundError(
            "No EVMS periods found for this program",
            "NO_PERIODS_FOUND",
        )

    # Get variance explanations if requested
    variance_explanations = []
    if include_explanations:
        ve_repo = VarianceExplanationRepository(db)
        variance_explanations = await ve_repo.get_by_program(program_id)

    # Get MR logs if requested
    mr_logs = []
    if include_mr:
        mr_repo = ManagementReserveLogRepository(db)
        mr_logs = await mr_repo.get_history(program_id, limit=periods_to_include)

    # Create configuration
    config = Format5ExportConfig(
        include_mr=include_mr,
        include_explanations=include_explanations,
        variance_threshold_percent=variance_threshold,
        periods_to_include=periods_to_include,
        include_eac_analysis=True,
    )

    # Generate report data
    generator = CPRFormat5Generator(
        program=program,
        periods=periods,
        config=config,
        variance_explanations=variance_explanations,
        mr_logs=mr_logs,
        manager_etc=manager_etc,
    )
    report = generator.generate()

    # Generate PDF
    pdf_config = PDFConfig(landscape_mode=landscape)
    pdf_generator = ReportPDFGenerator(config=pdf_config)
    pdf_bytes = pdf_generator.generate_format5_pdf(report)

    # Get latest period for filename
    latest_period = periods[-1] if periods else None
    period_name = latest_period.period_name.replace(" ", "_") if latest_period else "current"
    filename = f"CPR_Format5_{program.code}_{period_name}.pdf"

    # Log audit trail
    audit_repo = ReportAuditRepository(db)
    await audit_repo.log_generation(
        report_type="cpr_format_5",
        program_id=program_id,
        generated_by=current_user.id,
        parameters={
            "periods_to_include": periods_to_include,
            "variance_threshold": str(variance_threshold),
            "include_mr": include_mr,
            "include_explanations": include_explanations,
            "manager_etc": str(manager_etc) if manager_etc else None,
            "landscape": landscape,
        },
        file_format="pdf",
        file_size=len(pdf_bytes),
        checksum=_compute_checksum(pdf_bytes),
    )
    await db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============================================================================
# Report Audit Endpoints
# ============================================================================


@router.get("/audit/{program_id}", response_model=ReportAuditListResponse)
async def get_report_audit_history(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    report_type: Annotated[str | None, Query(description="Filter by report type")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> ReportAuditListResponse:
    """
    Get report generation audit history for a program.

    Returns paginated list of all report generations for compliance tracking.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Check authorization
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied to this program")

    # Get audit entries
    audit_repo = ReportAuditRepository(db)
    entries = await audit_repo.get_by_program(program_id, report_type=report_type)

    # Calculate pagination
    total = len(entries)
    skip = (page - 1) * per_page
    paginated = entries[skip : skip + per_page]

    return ReportAuditListResponse(
        items=[ReportAuditResponse.model_validate(e) for e in paginated],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 1,
    )


@router.get("/audit/{program_id}/stats", response_model=ReportAuditStats)
async def get_report_audit_stats(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> ReportAuditStats:
    """
    Get statistics about report generations for a program.

    Returns counts by type, format, and total size.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Check authorization
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied to this program")

    # Get all audit entries
    audit_repo = ReportAuditRepository(db)
    entries = await audit_repo.get_by_program(program_id)

    # Calculate statistics
    by_type: dict[str, int] = {}
    by_format: dict[str, int] = {}
    total_size = 0
    last_generated = None

    for entry in entries:
        # Count by type
        by_type[entry.report_type] = by_type.get(entry.report_type, 0) + 1

        # Count by format
        if entry.file_format:
            by_format[entry.file_format] = by_format.get(entry.file_format, 0) + 1

        # Sum file sizes
        if entry.file_size:
            total_size += entry.file_size

        # Track most recent
        if last_generated is None or entry.generated_at > last_generated:
            last_generated = entry.generated_at

    return ReportAuditStats(
        total_reports=len(entries),
        by_type=by_type,
        by_format=by_format,
        total_size_bytes=total_size,
        last_generated=last_generated,
    )


@router.get("/audit/{program_id}/recent", response_model=list[ReportAuditResponse])
async def get_recent_report_generations(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=50, description="Number of entries")] = 10,
) -> list[ReportAuditResponse]:
    """
    Get recent report generations for a program.

    Returns the most recent report generations for quick access.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    # Check authorization
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied to this program")

    # Get recent entries
    audit_repo = ReportAuditRepository(db)
    entries = await audit_repo.get_recent(program_id, limit=limit)

    return [ReportAuditResponse.model_validate(e) for e in entries]
