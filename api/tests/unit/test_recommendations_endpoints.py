"""Unit tests for resource recommendation endpoints."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.recommendations import (
    get_activity_recommendations,
    get_bulk_recommendations,
    get_resource_recommendations,
)
from src.core.exceptions import AuthorizationError, NotFoundError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, is_admin: bool = False, user_id=None):
    user = MagicMock()
    user.id = user_id or uuid4()
    user.is_admin = is_admin
    return user


def _make_activity(*, program_id=None, activity_id=None, name="Design Review"):
    activity = MagicMock()
    activity.id = activity_id or uuid4()
    activity.program_id = program_id or uuid4()
    activity.name = name
    return activity


def _make_program(*, owner_id, program_id=None):
    program = MagicMock()
    program.id = program_id or uuid4()
    program.owner_id = owner_id
    return program


def _make_resource(*, program_id=None, resource_id=None, name="Engineer A"):
    resource = MagicMock()
    resource.id = resource_id or uuid4()
    resource.program_id = program_id or uuid4()
    resource.name = name
    return resource


def _cache_mock(*, cached_value=None):
    """Return an AsyncMock cache service that optionally returns a cached value."""
    cache = AsyncMock()
    cache.make_key = MagicMock(return_value="test_cache_key")
    cache.get = AsyncMock(return_value=cached_value)
    cache.set = AsyncMock()
    return cache


# ---------------------------------------------------------------------------
# get_activity_recommendations
# ---------------------------------------------------------------------------


class TestGetActivityRecommendations:
    """Tests for get_activity_recommendations endpoint."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Should return recommendations for a valid activity."""
        mock_db = AsyncMock()
        user = _make_user()
        program_id = uuid4()
        activity = _make_activity(program_id=program_id)
        program = _make_program(owner_id=user.id, program_id=program_id)

        total_candidates = 5
        requirements_count = 3

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
            patch("src.api.v1.endpoints.recommendations.get_cache_service") as mock_get_cache,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=activity)
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            cache = _cache_mock()
            mock_get_cache.return_value = cache

            mock_service = MagicMock()
            mock_service.recommend_for_activity = AsyncMock(
                return_value=([], total_candidates, requirements_count)
            )
            mock_service_cls.return_value = mock_service

            result = await get_activity_recommendations(
                db=mock_db,
                current_user=user,
                activity_id=activity.id,
            )

            assert result.activity_id == activity.id
            assert result.activity_name == activity.name
            assert result.recommendations == []
            assert result.total_candidates == total_candidates
            assert result.requirements_count == requirements_count
            mock_service.recommend_for_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_activity_not_found(self):
        """Should raise NotFoundError when activity does not exist."""
        mock_db = AsyncMock()
        user = _make_user()
        activity_id = uuid4()

        with patch(
            "src.api.v1.endpoints.recommendations.ActivityRepository"
        ) as mock_activity_repo_cls:
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=None)
            mock_activity_repo_cls.return_value = mock_activity_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_activity_recommendations(
                    db=mock_db,
                    current_user=user,
                    activity_id=activity_id,
                )

            assert exc_info.value.code == "ACTIVITY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        user = _make_user()
        activity = _make_activity()

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=activity)
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=None)
            mock_program_repo_cls.return_value = mock_program_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_activity_recommendations(
                    db=mock_db,
                    current_user=user,
                    activity_id=activity.id,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_authorization_error_not_owner(self):
        """Should raise AuthorizationError when user is not owner and not admin."""
        mock_db = AsyncMock()
        user = _make_user(is_admin=False)
        other_owner_id = uuid4()
        program_id = uuid4()
        activity = _make_activity(program_id=program_id)
        program = _make_program(owner_id=other_owner_id, program_id=program_id)

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=activity)
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            with pytest.raises(AuthorizationError):
                await get_activity_recommendations(
                    db=mock_db,
                    current_user=user,
                    activity_id=activity.id,
                )

    @pytest.mark.asyncio
    async def test_admin_bypasses_ownership_check(self):
        """Should allow admin users even if they are not the program owner."""
        mock_db = AsyncMock()
        admin_user = _make_user(is_admin=True)
        other_owner_id = uuid4()
        program_id = uuid4()
        activity = _make_activity(program_id=program_id)
        program = _make_program(owner_id=other_owner_id, program_id=program_id)

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
            patch("src.api.v1.endpoints.recommendations.get_cache_service") as mock_get_cache,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=activity)
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            cache = _cache_mock()
            mock_get_cache.return_value = cache

            mock_service = MagicMock()
            mock_service.recommend_for_activity = AsyncMock(return_value=([], 0, 0))
            mock_service_cls.return_value = mock_service

            result = await get_activity_recommendations(
                db=mock_db,
                current_user=admin_user,
                activity_id=activity.id,
            )

            assert result.activity_id == activity.id

    @pytest.mark.asyncio
    async def test_returns_cached_result(self):
        """Should return cached response when cache hit occurs."""
        mock_db = AsyncMock()
        user = _make_user()
        program_id = uuid4()
        activity = _make_activity(program_id=program_id)
        program = _make_program(owner_id=user.id, program_id=program_id)

        cached_data = {
            "activity_id": str(activity.id),
            "activity_name": activity.name,
            "recommendations": [],
            "total_candidates": 7,
            "requirements_count": 2,
        }

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
            patch("src.api.v1.endpoints.recommendations.get_cache_service") as mock_get_cache,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=activity)
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            cache = _cache_mock(cached_value=cached_data)
            mock_get_cache.return_value = cache

            mock_service = MagicMock()
            mock_service_cls.return_value = mock_service

            result = await get_activity_recommendations(
                db=mock_db,
                current_user=user,
                activity_id=activity.id,
            )

            # The cached branch returns a RecommendationResponse built from the dict
            assert result.total_candidates == 7
            assert result.requirements_count == 2
            # Service should NOT have been called
            mock_service.recommend_for_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_passes_optional_filters(self):
        """Should forward optional query parameters to the service."""
        mock_db = AsyncMock()
        user = _make_user()
        program_id = uuid4()
        activity = _make_activity(program_id=program_id)
        program = _make_program(owner_id=user.id, program_id=program_id)

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
            patch("src.api.v1.endpoints.recommendations.get_cache_service") as mock_get_cache,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=activity)
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            cache = _cache_mock()
            mock_get_cache.return_value = cache

            mock_service = MagicMock()
            mock_service.recommend_for_activity = AsyncMock(return_value=([], 0, 0))
            mock_service_cls.return_value = mock_service

            start_date = date(2026, 3, 1)
            end_date = date(2026, 6, 30)

            await get_activity_recommendations(
                db=mock_db,
                current_user=user,
                activity_id=activity.id,
                top_n=20,
                min_score=0.5,
                resource_type="LABOR",
                date_range_start=start_date,
                date_range_end=end_date,
            )

            mock_service.recommend_for_activity.assert_called_once_with(
                activity_id=activity.id,
                program_id=activity.program_id,
                top_n=20,
                min_score=0.5,
                resource_type="LABOR",
                date_range_start=start_date,
                date_range_end=end_date,
            )

    @pytest.mark.asyncio
    async def test_cache_set_called_on_miss(self):
        """Should store the result in cache after a cache miss."""
        mock_db = AsyncMock()
        user = _make_user()
        program_id = uuid4()
        activity = _make_activity(program_id=program_id)
        program = _make_program(owner_id=user.id, program_id=program_id)

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
            patch("src.api.v1.endpoints.recommendations.get_cache_service") as mock_get_cache,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=activity)
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            cache = _cache_mock()  # returns None -> cache miss
            mock_get_cache.return_value = cache

            mock_service = MagicMock()
            mock_service.recommend_for_activity = AsyncMock(return_value=([], 0, 0))
            mock_service_cls.return_value = mock_service

            await get_activity_recommendations(
                db=mock_db,
                current_user=user,
                activity_id=activity.id,
            )

            cache.set.assert_called_once()


# ---------------------------------------------------------------------------
# get_resource_recommendations
# ---------------------------------------------------------------------------


class TestGetResourceRecommendations:
    """Tests for get_resource_recommendations endpoint."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Should return activity recommendations for a valid resource."""
        mock_db = AsyncMock()
        user = _make_user()
        program_id = uuid4()
        resource = _make_resource(program_id=program_id)
        program = _make_program(owner_id=user.id, program_id=program_id)

        total_evaluated = 12

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRepository"
            ) as mock_resource_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
        ):
            mock_resource_repo = MagicMock()
            mock_resource_repo.get_by_id = AsyncMock(return_value=resource)
            mock_resource_repo_cls.return_value = mock_resource_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            mock_service = MagicMock()
            mock_service.recommend_activities_for_resource = AsyncMock(
                return_value=([], total_evaluated)
            )
            mock_service_cls.return_value = mock_service

            result = await get_resource_recommendations(
                db=mock_db,
                current_user=user,
                resource_id=resource.id,
            )

            assert result.resource_id == resource.id
            assert result.resource_name == resource.name
            assert result.recommendations == []
            assert result.total_activities_evaluated == total_evaluated
            mock_service.recommend_activities_for_resource.assert_called_once()

    @pytest.mark.asyncio
    async def test_resource_not_found(self):
        """Should raise NotFoundError when resource does not exist."""
        mock_db = AsyncMock()
        user = _make_user()
        resource_id = uuid4()

        with patch(
            "src.api.v1.endpoints.recommendations.ResourceRepository"
        ) as mock_resource_repo_cls:
            mock_resource_repo = MagicMock()
            mock_resource_repo.get_by_id = AsyncMock(return_value=None)
            mock_resource_repo_cls.return_value = mock_resource_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_resource_recommendations(
                    db=mock_db,
                    current_user=user,
                    resource_id=resource_id,
                )

            assert exc_info.value.code == "RESOURCE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program for resource does not exist."""
        mock_db = AsyncMock()
        user = _make_user()
        resource = _make_resource()

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRepository"
            ) as mock_resource_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
        ):
            mock_resource_repo = MagicMock()
            mock_resource_repo.get_by_id = AsyncMock(return_value=resource)
            mock_resource_repo_cls.return_value = mock_resource_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=None)
            mock_program_repo_cls.return_value = mock_program_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_resource_recommendations(
                    db=mock_db,
                    current_user=user,
                    resource_id=resource.id,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_authorization_error_not_owner(self):
        """Should raise AuthorizationError when user is not owner and not admin."""
        mock_db = AsyncMock()
        user = _make_user(is_admin=False)
        other_owner_id = uuid4()
        program_id = uuid4()
        resource = _make_resource(program_id=program_id)
        program = _make_program(owner_id=other_owner_id, program_id=program_id)

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRepository"
            ) as mock_resource_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
        ):
            mock_resource_repo = MagicMock()
            mock_resource_repo.get_by_id = AsyncMock(return_value=resource)
            mock_resource_repo_cls.return_value = mock_resource_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            with pytest.raises(AuthorizationError):
                await get_resource_recommendations(
                    db=mock_db,
                    current_user=user,
                    resource_id=resource.id,
                )

    @pytest.mark.asyncio
    async def test_admin_bypasses_ownership_check(self):
        """Should allow admin users even if they are not the program owner."""
        mock_db = AsyncMock()
        admin_user = _make_user(is_admin=True)
        other_owner_id = uuid4()
        program_id = uuid4()
        resource = _make_resource(program_id=program_id)
        program = _make_program(owner_id=other_owner_id, program_id=program_id)

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRepository"
            ) as mock_resource_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
        ):
            mock_resource_repo = MagicMock()
            mock_resource_repo.get_by_id = AsyncMock(return_value=resource)
            mock_resource_repo_cls.return_value = mock_resource_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            mock_service = MagicMock()
            mock_service.recommend_activities_for_resource = AsyncMock(return_value=([], 0))
            mock_service_cls.return_value = mock_service

            result = await get_resource_recommendations(
                db=mock_db,
                current_user=admin_user,
                resource_id=resource.id,
            )

            assert result.resource_id == resource.id

    @pytest.mark.asyncio
    async def test_custom_top_n_and_min_score(self):
        """Should forward custom top_n and min_score to the service."""
        mock_db = AsyncMock()
        user = _make_user()
        program_id = uuid4()
        resource = _make_resource(program_id=program_id)
        program = _make_program(owner_id=user.id, program_id=program_id)

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRepository"
            ) as mock_resource_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
        ):
            mock_resource_repo = MagicMock()
            mock_resource_repo.get_by_id = AsyncMock(return_value=resource)
            mock_resource_repo_cls.return_value = mock_resource_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            mock_service = MagicMock()
            mock_service.recommend_activities_for_resource = AsyncMock(return_value=([], 0))
            mock_service_cls.return_value = mock_service

            await get_resource_recommendations(
                db=mock_db,
                current_user=user,
                resource_id=resource.id,
                top_n=25,
                min_score=0.75,
            )

            mock_service.recommend_activities_for_resource.assert_called_once_with(
                resource_id=resource.id,
                program_id=resource.program_id,
                top_n=25,
                min_score=0.75,
            )


# ---------------------------------------------------------------------------
# get_bulk_recommendations
# ---------------------------------------------------------------------------


class TestGetBulkRecommendations:
    """Tests for get_bulk_recommendations endpoint."""

    @pytest.mark.asyncio
    async def test_success_single_activity(self):
        """Should return recommendations for a single activity in bulk request."""
        from src.schemas.recommendation import BulkRecommendationRequest

        mock_db = AsyncMock()
        user = _make_user()
        program_id = uuid4()
        activity = _make_activity(program_id=program_id)
        program = _make_program(owner_id=user.id, program_id=program_id)

        request = BulkRecommendationRequest(
            activity_ids=[activity.id],
            top_n=5,
            min_score=0.0,
        )

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=activity)
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            mock_service = MagicMock()
            mock_service.recommend_for_activity = AsyncMock(return_value=([], 3, 1))
            mock_service_cls.return_value = mock_service

            result = await get_bulk_recommendations(
                db=mock_db,
                current_user=user,
                request=request,
            )

            assert result.total_activities == 1
            assert len(result.results) == 1
            assert result.results[0].activity_id == activity.id

    @pytest.mark.asyncio
    async def test_success_multiple_activities(self):
        """Should return recommendations for multiple activities."""
        from src.schemas.recommendation import BulkRecommendationRequest

        mock_db = AsyncMock()
        user = _make_user()
        program_id = uuid4()
        activity1 = _make_activity(program_id=program_id, name="Activity 1")
        activity2 = _make_activity(program_id=program_id, name="Activity 2")
        program = _make_program(owner_id=user.id, program_id=program_id)

        request = BulkRecommendationRequest(
            activity_ids=[activity1.id, activity2.id],
            top_n=5,
            min_score=0.0,
        )

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(side_effect=[activity1, activity2])
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            mock_service = MagicMock()
            mock_service.recommend_for_activity = AsyncMock(return_value=([], 2, 1))
            mock_service_cls.return_value = mock_service

            result = await get_bulk_recommendations(
                db=mock_db,
                current_user=user,
                request=request,
            )

            assert result.total_activities == 2
            assert len(result.results) == 2
            assert mock_service.recommend_for_activity.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_missing_activities(self):
        """Should skip activities that are not found (no error raised)."""
        from src.schemas.recommendation import BulkRecommendationRequest

        mock_db = AsyncMock()
        user = _make_user()
        missing_id = uuid4()

        request = BulkRecommendationRequest(
            activity_ids=[missing_id],
            top_n=5,
            min_score=0.0,
        )

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch("src.api.v1.endpoints.recommendations.ProgramRepository"),
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=None)
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_service = MagicMock()
            mock_service_cls.return_value = mock_service

            result = await get_bulk_recommendations(
                db=mock_db,
                current_user=user,
                request=request,
            )

            assert result.total_activities == 0
            assert len(result.results) == 0
            mock_service.recommend_for_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_unauthorized_activities(self):
        """Should skip activities the user does not have access to."""
        from src.schemas.recommendation import BulkRecommendationRequest

        mock_db = AsyncMock()
        user = _make_user(is_admin=False)
        other_owner = uuid4()
        program_id = uuid4()
        activity = _make_activity(program_id=program_id)
        program = _make_program(owner_id=other_owner, program_id=program_id)

        request = BulkRecommendationRequest(
            activity_ids=[activity.id],
            top_n=5,
            min_score=0.0,
        )

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=activity)
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            mock_service = MagicMock()
            mock_service_cls.return_value = mock_service

            result = await get_bulk_recommendations(
                db=mock_db,
                current_user=user,
                request=request,
            )

            assert result.total_activities == 0
            assert len(result.results) == 0
            mock_service.recommend_for_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_activity_with_missing_program(self):
        """Should skip activities whose program cannot be found."""
        from src.schemas.recommendation import BulkRecommendationRequest

        mock_db = AsyncMock()
        user = _make_user()
        activity = _make_activity()

        request = BulkRecommendationRequest(
            activity_ids=[activity.id],
            top_n=5,
            min_score=0.0,
        )

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=activity)
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=None)
            mock_program_repo_cls.return_value = mock_program_repo

            mock_service = MagicMock()
            mock_service_cls.return_value = mock_service

            result = await get_bulk_recommendations(
                db=mock_db,
                current_user=user,
                request=request,
            )

            assert result.total_activities == 0
            mock_service.recommend_for_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_custom_weights(self):
        """Should pass custom weights to the service when provided."""
        from src.schemas.recommendation import (
            BulkRecommendationRequest,
            RecommendationWeights,
        )

        mock_db = AsyncMock()
        user = _make_user()
        program_id = uuid4()
        activity = _make_activity(program_id=program_id)
        program = _make_program(owner_id=user.id, program_id=program_id)

        custom_weights = RecommendationWeights(
            skill_match=0.7,
            availability=0.1,
            cost=0.1,
            certification=0.1,
        )
        request = BulkRecommendationRequest(
            activity_ids=[activity.id],
            top_n=3,
            min_score=0.2,
            weights=custom_weights,
        )

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=activity)
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            mock_service = MagicMock()
            mock_service.recommend_for_activity = AsyncMock(return_value=([], 0, 0))
            mock_service_cls.return_value = mock_service

            await get_bulk_recommendations(
                db=mock_db,
                current_user=user,
                request=request,
            )

            call_kwargs = mock_service.recommend_for_activity.call_args[1]
            assert call_kwargs["weights"] == custom_weights
            assert call_kwargs["top_n"] == 3
            assert call_kwargs["min_score"] == 0.2

    @pytest.mark.asyncio
    async def test_uses_default_weights_when_none(self):
        """Should use default RecommendationWeights when request.weights is None."""
        from src.schemas.recommendation import BulkRecommendationRequest

        mock_db = AsyncMock()
        user = _make_user()
        program_id = uuid4()
        activity = _make_activity(program_id=program_id)
        program = _make_program(owner_id=user.id, program_id=program_id)

        request = BulkRecommendationRequest(
            activity_ids=[activity.id],
            top_n=5,
            min_score=0.0,
            weights=None,
        )

        with (
            patch(
                "src.api.v1.endpoints.recommendations.ActivityRepository"
            ) as mock_activity_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ProgramRepository"
            ) as mock_program_repo_cls,
            patch(
                "src.api.v1.endpoints.recommendations.ResourceRecommendationService"
            ) as mock_service_cls,
        ):
            mock_activity_repo = MagicMock()
            mock_activity_repo.get_by_id = AsyncMock(return_value=activity)
            mock_activity_repo_cls.return_value = mock_activity_repo

            mock_program_repo = MagicMock()
            mock_program_repo.get_by_id = AsyncMock(return_value=program)
            mock_program_repo_cls.return_value = mock_program_repo

            mock_service = MagicMock()
            mock_service.recommend_for_activity = AsyncMock(return_value=([], 0, 0))
            mock_service_cls.return_value = mock_service

            await get_bulk_recommendations(
                db=mock_db,
                current_user=user,
                request=request,
            )

            call_kwargs = mock_service.recommend_for_activity.call_args[1]
            weights = call_kwargs["weights"]
            # Should be a default RecommendationWeights instance
            assert weights.skill_match == 0.50
            assert weights.availability == 0.25
            assert weights.cost == 0.15
            assert weights.certification == 0.10
