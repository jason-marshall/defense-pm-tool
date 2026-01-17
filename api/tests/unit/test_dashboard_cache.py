"""Unit tests for dashboard cache service."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.cache import CacheManager
from src.services.dashboard_cache import DashboardCache, DashboardCacheKeys


class TestDashboardCacheKeys:
    """Tests for cache key generation."""

    def test_metrics_key(self):
        """Should generate metrics cache key."""
        program_id = "test-program-123"
        key = DashboardCacheKeys.metrics_key(program_id)
        assert key == "dashboard:metrics:test-program-123"

    def test_scurve_key_basic(self):
        """Should generate basic S-curve cache key."""
        program_id = "test-program-123"
        key = DashboardCacheKeys.scurve_key(program_id, enhanced=False)
        assert key == "dashboard:scurve:test-program-123:basic"

    def test_scurve_key_enhanced(self):
        """Should generate enhanced S-curve cache key."""
        program_id = "test-program-123"
        key = DashboardCacheKeys.scurve_key(program_id, enhanced=True)
        assert key == "dashboard:scurve:test-program-123:enhanced"

    def test_wbs_key(self):
        """Should generate WBS tree cache key."""
        program_id = "test-program-123"
        key = DashboardCacheKeys.wbs_key(program_id)
        assert key == "dashboard:wbs:test-program-123"

    def test_activities_key(self):
        """Should generate activities list cache key."""
        program_id = "test-program-123"
        key = DashboardCacheKeys.activities_key(program_id)
        assert key == "dashboard:activities:test-program-123"

    def test_schedule_key(self):
        """Should generate schedule cache key."""
        program_id = "test-program-123"
        key = DashboardCacheKeys.schedule_key(program_id)
        assert key == "dashboard:schedule:test-program-123"

    def test_ttl_values(self):
        """Should have correct TTL values."""
        assert DashboardCacheKeys.METRICS_TTL == 300  # 5 minutes
        assert DashboardCacheKeys.SCURVE_TTL == 900  # 15 minutes
        assert DashboardCacheKeys.WBS_TTL == 3600  # 1 hour
        assert DashboardCacheKeys.ACTIVITIES_TTL == 300  # 5 minutes
        assert DashboardCacheKeys.SCHEDULE_TTL == 600  # 10 minutes


class TestDashboardCacheIsAvailable:
    """Tests for cache availability."""

    def test_is_available_when_manager_available(self):
        """Should return True when manager is available."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True

        cache = DashboardCache(mock_manager)

        assert cache.is_available is True

    def test_is_available_when_manager_unavailable(self):
        """Should return False when manager is unavailable."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = False

        cache = DashboardCache(mock_manager)

        assert cache.is_available is False


class TestDashboardCacheMetrics:
    """Tests for metrics caching."""

    @pytest.mark.asyncio
    async def test_get_metrics_cache_hit(self):
        """Should return cached metrics on hit."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value={"spi": "1.05", "cpi": "0.98"})

        cache = DashboardCache(mock_manager)
        program_id = uuid4()

        result = await cache.get_metrics(program_id)

        assert result == {"spi": "1.05", "cpi": "0.98"}
        mock_manager.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_metrics_cache_miss(self):
        """Should return None on cache miss."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value=None)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()

        result = await cache.get_metrics(program_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_set_metrics_success(self):
        """Should cache metrics successfully."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.set = AsyncMock(return_value=True)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()
        data = {"spi": "1.05", "cpi": "0.98"}

        success = await cache.set_metrics(program_id, data)

        assert success is True
        mock_manager.set.assert_called_once()
        call_args = mock_manager.set.call_args
        assert call_args[1]["ttl"] == DashboardCacheKeys.METRICS_TTL

    @pytest.mark.asyncio
    async def test_set_metrics_custom_ttl(self):
        """Should use custom TTL when provided."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.set = AsyncMock(return_value=True)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()
        custom_ttl = 120

        await cache.set_metrics(program_id, {"data": "test"}, ttl=custom_ttl)

        call_args = mock_manager.set.call_args
        assert call_args[1]["ttl"] == custom_ttl


class TestDashboardCacheSCurve:
    """Tests for S-curve caching."""

    @pytest.mark.asyncio
    async def test_get_scurve_basic_cache_hit(self):
        """Should return cached basic S-curve on hit."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value={"data_points": []})

        cache = DashboardCache(mock_manager)
        program_id = uuid4()

        result = await cache.get_scurve(program_id, enhanced=False)

        assert result == {"data_points": []}
        # Verify the key includes ":basic"
        call_args = mock_manager.get.call_args[0][0]
        assert ":basic" in call_args

    @pytest.mark.asyncio
    async def test_get_scurve_enhanced_cache_hit(self):
        """Should return cached enhanced S-curve on hit."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value={"data_points": [], "eac_range": {}})

        cache = DashboardCache(mock_manager)
        program_id = uuid4()

        result = await cache.get_scurve(program_id, enhanced=True)

        assert result == {"data_points": [], "eac_range": {}}
        # Verify the key includes ":enhanced"
        call_args = mock_manager.get.call_args[0][0]
        assert ":enhanced" in call_args

    @pytest.mark.asyncio
    async def test_set_scurve_success(self):
        """Should cache S-curve successfully."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.set = AsyncMock(return_value=True)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()
        data = {"data_points": []}

        success = await cache.set_scurve(program_id, data, enhanced=True)

        assert success is True
        mock_manager.set.assert_called_once()
        call_args = mock_manager.set.call_args
        assert call_args[1]["ttl"] == DashboardCacheKeys.SCURVE_TTL


class TestDashboardCacheWBS:
    """Tests for WBS tree caching."""

    @pytest.mark.asyncio
    async def test_get_wbs_tree_cache_hit(self):
        """Should return cached WBS tree on hit."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value={"elements": []})

        cache = DashboardCache(mock_manager)
        program_id = uuid4()

        result = await cache.get_wbs_tree(program_id)

        assert result == {"elements": []}

    @pytest.mark.asyncio
    async def test_set_wbs_tree_success(self):
        """Should cache WBS tree successfully."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.set = AsyncMock(return_value=True)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()
        data = {"elements": []}

        success = await cache.set_wbs_tree(program_id, data)

        assert success is True
        call_args = mock_manager.set.call_args
        assert call_args[1]["ttl"] == DashboardCacheKeys.WBS_TTL


class TestDashboardCacheActivities:
    """Tests for activities caching."""

    @pytest.mark.asyncio
    async def test_get_activities_cache_hit(self):
        """Should return cached activities on hit."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value={"items": []})

        cache = DashboardCache(mock_manager)
        program_id = uuid4()

        result = await cache.get_activities(program_id)

        assert result == {"items": []}

    @pytest.mark.asyncio
    async def test_set_activities_success(self):
        """Should cache activities successfully."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.set = AsyncMock(return_value=True)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()
        data = {"items": []}

        success = await cache.set_activities(program_id, data)

        assert success is True
        call_args = mock_manager.set.call_args
        assert call_args[1]["ttl"] == DashboardCacheKeys.ACTIVITIES_TTL


class TestDashboardCacheSchedule:
    """Tests for schedule caching."""

    @pytest.mark.asyncio
    async def test_get_schedule_cache_hit(self):
        """Should return cached schedule on hit."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value={"activities": []})

        cache = DashboardCache(mock_manager)
        program_id = uuid4()

        result = await cache.get_schedule(program_id)

        assert result == {"activities": []}

    @pytest.mark.asyncio
    async def test_set_schedule_success(self):
        """Should cache schedule successfully."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.set = AsyncMock(return_value=True)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()
        data = {"activities": []}

        success = await cache.set_schedule(program_id, data)

        assert success is True
        call_args = mock_manager.set.call_args
        assert call_args[1]["ttl"] == DashboardCacheKeys.SCHEDULE_TTL


class TestDashboardCacheInvalidation:
    """Tests for cache invalidation methods."""

    @pytest.mark.asyncio
    async def test_invalidate_program_deletes_all_keys(self):
        """Should delete all dashboard caches for a program."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.delete = AsyncMock(return_value=True)
        mock_manager.delete_pattern = AsyncMock(return_value=2)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()

        deleted = await cache.invalidate_program(program_id)

        # Should delete multiple keys
        assert deleted >= 4  # At least 4 component keys
        assert mock_manager.delete.call_count >= 3
        assert mock_manager.delete_pattern.call_count >= 1  # For S-curve pattern

    @pytest.mark.asyncio
    async def test_invalidate_on_period_update(self):
        """Should invalidate metrics and S-curve on period update."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.delete = AsyncMock(return_value=True)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()

        await cache.invalidate_on_period_update(program_id)

        # Should delete 3 keys: metrics, basic s-curve, enhanced s-curve
        assert mock_manager.delete.call_count == 3

    @pytest.mark.asyncio
    async def test_invalidate_on_activity_update(self):
        """Should invalidate activities, schedule, and S-curve on activity update."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.delete = AsyncMock(return_value=True)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()

        await cache.invalidate_on_activity_update(program_id)

        # Should delete 4 keys: activities, schedule, basic s-curve, enhanced s-curve
        assert mock_manager.delete.call_count == 4

    @pytest.mark.asyncio
    async def test_invalidate_on_wbs_update(self):
        """Should invalidate WBS tree and activities on WBS update."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.delete = AsyncMock(return_value=True)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()

        await cache.invalidate_on_wbs_update(program_id)

        # Should delete 2 keys: wbs, activities
        assert mock_manager.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_invalidate_on_simulation_update(self):
        """Should invalidate enhanced S-curve on simulation update."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.delete = AsyncMock(return_value=True)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()

        await cache.invalidate_on_simulation_update(program_id)

        # Should delete 1 key: enhanced s-curve
        mock_manager.delete.assert_called_once()
        call_args = mock_manager.delete.call_args[0][0]
        assert ":enhanced" in call_args


class TestDashboardCacheIntegration:
    """Integration tests for dashboard cache workflow."""

    @pytest.mark.asyncio
    async def test_full_cache_workflow(self):
        """Test complete cache workflow: set, get, invalidate."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True

        stored_data: dict = {}

        async def mock_get(key):
            return stored_data.get(key)

        async def mock_set(key, value, ttl=None):
            stored_data[key] = value
            return True

        async def mock_delete(key):
            if key in stored_data:
                del stored_data[key]
                return True
            return False

        mock_manager.get = AsyncMock(side_effect=mock_get)
        mock_manager.set = AsyncMock(side_effect=mock_set)
        mock_manager.delete = AsyncMock(side_effect=mock_delete)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()
        metrics_data = {"spi": "1.05", "cpi": "0.98"}

        # Initially empty
        result = await cache.get_metrics(program_id)
        assert result is None

        # Set metrics
        success = await cache.set_metrics(program_id, metrics_data)
        assert success is True

        # Get cached metrics
        result = await cache.get_metrics(program_id)
        assert result == metrics_data

        # Invalidate on period update
        await cache.invalidate_on_period_update(program_id)

        # Verify deleted
        result = await cache.get_metrics(program_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_different_enhanced_flags_cached_separately(self):
        """Basic and enhanced S-curves should be cached separately."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True

        stored_data: dict = {}

        async def mock_get(key):
            return stored_data.get(key)

        async def mock_set(key, value, ttl=None):
            stored_data[key] = value
            return True

        mock_manager.get = AsyncMock(side_effect=mock_get)
        mock_manager.set = AsyncMock(side_effect=mock_set)

        cache = DashboardCache(mock_manager)
        program_id = uuid4()

        # Set basic and enhanced S-curve
        await cache.set_scurve(program_id, {"type": "basic"}, enhanced=False)
        await cache.set_scurve(program_id, {"type": "enhanced"}, enhanced=True)

        # Get each separately
        basic = await cache.get_scurve(program_id, enhanced=False)
        enhanced = await cache.get_scurve(program_id, enhanced=True)

        assert basic["type"] == "basic"
        assert enhanced["type"] == "enhanced"
