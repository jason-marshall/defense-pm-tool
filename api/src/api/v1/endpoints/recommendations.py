"""API endpoints for automated resource recommendations."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import AuthorizationError, NotFoundError
from src.repositories.activity import ActivityRepository
from src.repositories.program import ProgramRepository
from src.repositories.resource import ResourceRepository
from src.schemas.recommendation import (
    BulkRecommendationRequest,
    BulkRecommendationResponse,
    RecommendationResponse,
    RecommendationWeights,
    ResourceActivityRecommendationResponse,
)
from src.services.cache_service import CACHE_TTL, get_cache_service
from src.services.resource_recommendation import ResourceRecommendationService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get(
    "/activities/{activity_id}",
    response_model=RecommendationResponse,
    summary="Get Resource Recommendations for Activity",
)
async def get_activity_recommendations(
    db: DbSession,
    current_user: CurrentUser,
    activity_id: UUID,
    top_n: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum score threshold"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    date_range_start: date | None = Query(None, description="Start of availability window"),
    date_range_end: date | None = Query(None, description="End of availability window"),
) -> RecommendationResponse:
    """Get ranked resource recommendations for an activity based on skill matching."""
    activity_repo = ActivityRepository(db)
    activity = await activity_repo.get_by_id(activity_id)
    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")

    # Verify program access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity.program_id)
    if not program:
        raise NotFoundError("Program not found", "PROGRAM_NOT_FOUND")
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied to this program")

    # Check cache
    cache = get_cache_service()
    cache_key = cache.make_key(
        "recommendation",
        activity_id,
        top_n=top_n,
        min_score=min_score,
        resource_type=resource_type,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
    )
    cached = await cache.get(cache_key, "recommendation")
    if cached is not None:
        return RecommendationResponse(**cached)

    service = ResourceRecommendationService(db)
    recommendations, total_candidates, requirements_count = await service.recommend_for_activity(
        activity_id=activity.id,
        program_id=activity.program_id,
        top_n=top_n,
        min_score=min_score,
        resource_type=resource_type,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
    )

    response = RecommendationResponse(
        activity_id=activity.id,
        activity_name=activity.name,
        recommendations=recommendations,
        total_candidates=total_candidates,
        requirements_count=requirements_count,
    )

    await cache.set(
        cache_key,
        response.model_dump(mode="json"),
        CACHE_TTL.get("recommendation"),
        "recommendation",
    )

    return response


@router.get(
    "/resources/{resource_id}",
    response_model=ResourceActivityRecommendationResponse,
    summary="Get Activity Recommendations for Resource",
)
async def get_resource_recommendations(
    db: DbSession,
    current_user: CurrentUser,
    resource_id: UUID,
    top_n: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum score threshold"),
) -> ResourceActivityRecommendationResponse:
    """Find activities that best match a resource's skills."""
    resource_repo = ResourceRepository(db)
    resource = await resource_repo.get_by_id(resource_id)
    if not resource:
        raise NotFoundError(f"Resource {resource_id} not found", "RESOURCE_NOT_FOUND")

    # Verify program access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(resource.program_id)
    if not program:
        raise NotFoundError("Program not found", "PROGRAM_NOT_FOUND")
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied to this program")

    service = ResourceRecommendationService(db)
    recommendations, total_evaluated = await service.recommend_activities_for_resource(
        resource_id=resource.id,
        program_id=resource.program_id,
        top_n=top_n,
        min_score=min_score,
    )

    return ResourceActivityRecommendationResponse(
        resource_id=resource.id,
        resource_name=resource.name,
        recommendations=recommendations,
        total_activities_evaluated=total_evaluated,
    )


@router.post(
    "/bulk",
    response_model=BulkRecommendationResponse,
    summary="Bulk Resource Recommendations",
)
async def get_bulk_recommendations(
    db: DbSession,
    current_user: CurrentUser,
    request: BulkRecommendationRequest,
) -> BulkRecommendationResponse:
    """Get resource recommendations for multiple activities at once."""
    activity_repo = ActivityRepository(db)
    program_repo = ProgramRepository(db)
    service = ResourceRecommendationService(db)

    weights = request.weights or RecommendationWeights()
    results: list[RecommendationResponse] = []

    for activity_id in request.activity_ids:
        activity = await activity_repo.get_by_id(activity_id)
        if not activity:
            continue

        # Verify program access
        program = await program_repo.get_by_id(activity.program_id)
        if not program:
            continue
        if program.owner_id != current_user.id and not current_user.is_admin:
            continue

        (
            recommendations,
            total_candidates,
            requirements_count,
        ) = await service.recommend_for_activity(
            activity_id=activity.id,
            program_id=activity.program_id,
            top_n=request.top_n,
            min_score=request.min_score,
            weights=weights,
        )

        results.append(
            RecommendationResponse(
                activity_id=activity.id,
                activity_name=activity.name,
                recommendations=recommendations,
                total_candidates=total_candidates,
                requirements_count=requirements_count,
            )
        )

    return BulkRecommendationResponse(
        results=results,
        total_activities=len(results),
    )
