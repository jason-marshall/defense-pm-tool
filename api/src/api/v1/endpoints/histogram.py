"""API endpoints for resource histograms."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from src.core.deps import CurrentUser, DbSession
from src.repositories.program import ProgramRepository
from src.repositories.resource import ResourceRepository
from src.schemas.histogram import (
    HistogramDataPointResponse,
    ProgramHistogramResponse,
    ProgramHistogramSummaryResponse,
    ResourceHistogramResponse,
)
from src.services.resource_histogram import ResourceHistogram, ResourceHistogramService

router = APIRouter(tags=["Histograms"])


def _convert_histogram_to_response(
    histogram: ResourceHistogram,
) -> ResourceHistogramResponse:
    """Convert ResourceHistogram dataclass to response schema."""
    data_points = [
        HistogramDataPointResponse(
            date=p.date,
            available_hours=p.available_hours,
            assigned_hours=p.assigned_hours,
            utilization_percent=p.utilization_percent,
            is_overallocated=p.is_overallocated,
        )
        for p in histogram.data_points
    ]

    return ResourceHistogramResponse(
        resource_id=histogram.resource_id,
        resource_code=histogram.resource_code,
        resource_name=histogram.resource_name,
        resource_type=histogram.resource_type,
        start_date=histogram.start_date,
        end_date=histogram.end_date,
        data_points=data_points,
        peak_utilization=histogram.peak_utilization,
        peak_date=histogram.peak_date,
        average_utilization=histogram.average_utilization,
        overallocated_days=histogram.overallocated_days,
        total_available_hours=histogram.total_available_hours,
        total_assigned_hours=histogram.total_assigned_hours,
    )


@router.get(
    "/resources/{resource_id}/histogram",
    response_model=ResourceHistogramResponse,
    summary="Get resource histogram",
)
async def get_resource_histogram(
    resource_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    start_date: date = Query(..., description="Start date for histogram"),
    end_date: date = Query(..., description="End date for histogram"),
    granularity: str = Query(
        default="daily",
        description="Granularity: 'daily' or 'weekly'",
        pattern="^(daily|weekly)$",
    ),
) -> ResourceHistogramResponse:
    """Get histogram data for a single resource.

    Returns utilization data points for the specified date range.
    Supports daily or weekly granularity.

    Args:
        resource_id: UUID of the resource
        start_date: Start of histogram period
        end_date: End of histogram period
        granularity: "daily" or "weekly"
        db: Database session
        current_user: Authenticated user

    Returns:
        ResourceHistogramResponse with data points and statistics

    Raises:
        HTTPException: 404 if resource not found
        HTTPException: 400 if date range invalid
    """
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    # Verify resource exists and user has access
    resource_repo = ResourceRepository(db)
    resource = await resource_repo.get_by_id(resource_id)

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Generate histogram
    service = ResourceHistogramService(db)
    histogram = await service.get_resource_histogram(resource_id, start_date, end_date, granularity)

    if not histogram:
        raise HTTPException(status_code=404, detail="Resource not found")

    return _convert_histogram_to_response(histogram)


@router.get(
    "/programs/{program_id}/histogram",
    response_model=ProgramHistogramResponse,
    summary="Get program histogram",
)
async def get_program_histogram(
    program_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    start_date: date | None = Query(default=None, description="Start date"),
    end_date: date | None = Query(default=None, description="End date"),
    resource_ids: list[UUID] | None = Query(
        default=None, description="Filter to specific resources"
    ),
) -> ProgramHistogramResponse:
    """Get histogram data for all resources in a program.

    Returns utilization data for all active resources in the program.
    Optionally filter to specific resources.

    Args:
        program_id: UUID of the program
        start_date: Start of period (defaults to program start)
        end_date: End of period (defaults to program end)
        resource_ids: Optional filter for specific resources
        db: Database session
        current_user: Authenticated user

    Returns:
        ProgramHistogramResponse with summary and resource histograms

    Raises:
        HTTPException: 404 if program not found
        HTTPException: 400 if date range invalid
    """
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)

    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Generate histograms
    service = ResourceHistogramService(db)
    summary, histograms = await service.get_program_histogram(
        program_id, start_date, end_date, resource_ids
    )

    # Convert to response schemas
    histogram_responses = [_convert_histogram_to_response(h) for h in histograms]

    summary_response = ProgramHistogramSummaryResponse(
        program_id=summary.program_id,
        start_date=summary.start_date,
        end_date=summary.end_date,
        resource_count=summary.resource_count,
        total_overallocated_days=summary.total_overallocated_days,
        resources_with_overallocation=summary.resources_with_overallocation,
    )

    return ProgramHistogramResponse(
        summary=summary_response,
        histograms=histogram_responses,
    )
