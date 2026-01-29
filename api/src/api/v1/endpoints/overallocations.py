"""API endpoints for over-allocation detection.

Provides endpoints for querying resource over-allocations to support
resource leveling decisions.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from src.core.deps import CurrentUser, DbSession
from src.schemas.overallocation import (
    OverallocationPeriodResponse,
    ProgramOverallocationReportResponse,
)
from src.services.overallocation import OverallocationPeriod, OverallocationService

router = APIRouter(prefix="/overallocations", tags=["overallocations"])


def _period_to_response(period: OverallocationPeriod) -> OverallocationPeriodResponse:
    """Convert OverallocationPeriod dataclass to response schema."""
    return OverallocationPeriodResponse(
        resource_id=period.resource_id,
        resource_code=period.resource_code,
        resource_name=period.resource_name,
        start_date=period.start_date,
        end_date=period.end_date,
        duration_days=period.duration_days,
        peak_assigned=period.peak_assigned,
        peak_available=period.peak_available,
        peak_excess=period.peak_excess,
        severity=period.severity,
        affected_activities=period.affected_activities,
    )


@router.get(
    "/resources/{resource_id}",
    response_model=list[OverallocationPeriodResponse],
    summary="Get resource over-allocations",
    description="Find all over-allocated periods for a single resource.",
)
async def get_resource_overallocations(
    resource_id: UUID,
    start_date: Annotated[date, Query(description="Start of analysis period")],
    end_date: Annotated[date, Query(description="End of analysis period")],
    db: DbSession,
    current_user: CurrentUser,
) -> list[OverallocationPeriodResponse]:
    """Get all over-allocation periods for a resource.

    Analyzes daily loading and identifies continuous periods where
    assigned hours exceed available hours.

    Args:
        resource_id: UUID of the resource to analyze
        start_date: Start of analysis period (inclusive)
        end_date: End of analysis period (inclusive)
        db: Database session
        current_user: Authenticated user

    Returns:
        List of over-allocation periods with details
    """
    service = OverallocationService(db)
    periods = await service.detect_resource_overallocations(resource_id, start_date, end_date)
    return [_period_to_response(p) for p in periods]


@router.get(
    "/programs/{program_id}",
    response_model=ProgramOverallocationReportResponse,
    summary="Get program over-allocation report",
    description="Analyze entire program for resource over-allocations.",
)
async def get_program_overallocations(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    start_date: Annotated[
        date | None,
        Query(description="Start of analysis period (defaults to program start)"),
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="End of analysis period (defaults to program end)"),
    ] = None,
) -> ProgramOverallocationReportResponse:
    """Get over-allocation report for entire program.

    Examines all active resources in the program and identifies
    over-allocation periods for each.

    Args:
        program_id: UUID of the program to analyze
        start_date: Start of analysis period (defaults to program start)
        end_date: End of analysis period (defaults to program end)
        db: Database session
        current_user: Authenticated user

    Returns:
        Program-wide over-allocation report
    """
    service = OverallocationService(db)
    report = await service.detect_program_overallocations(program_id, start_date, end_date)

    return ProgramOverallocationReportResponse(
        program_id=report.program_id,
        analysis_start=report.analysis_start,
        analysis_end=report.analysis_end,
        total_overallocations=report.total_overallocations,
        resources_affected=report.resources_affected,
        total_affected_days=report.total_affected_days,
        has_high_severity=report.has_high_severity,
        critical_path_affected=report.critical_path_affected,
        periods=[_period_to_response(p) for p in report.periods],
    )


@router.get(
    "/resources/{resource_id}/affected-activities",
    response_model=list[UUID],
    summary="Get affected activities",
    description="Get activity IDs contributing to over-allocation on a date.",
)
async def get_affected_activities(
    resource_id: UUID,
    check_date: Annotated[date, Query(description="Date to check for over-allocation")],
    db: DbSession,
    current_user: CurrentUser,
) -> list[UUID]:
    """Get activities contributing to over-allocation on a specific date.

    Args:
        resource_id: UUID of the resource
        check_date: Date to check
        db: Database session
        current_user: Authenticated user

    Returns:
        List of activity UUIDs with active assignments on the date
    """
    service = OverallocationService(db)
    return await service.get_affected_activities(resource_id, check_date)
