"""Unit tests for simulation cache service."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.cache import CacheManager
from src.services.simulation_cache import SimulationCache, SimulationCacheKeys


class TestSimulationCacheKeys:
    """Tests for cache key generation."""

    def test_result_key_with_result_id(self):
        """Should generate key with config and result IDs."""
        config_id = "config-123"
        result_id = "result-456"

        key = SimulationCacheKeys.result_key(config_id, result_id)

        assert key == "simulation:result:config-123:result-456"

    def test_result_key_without_result_id(self):
        """Should generate 'latest' key when result_id is None."""
        config_id = "config-123"

        key = SimulationCacheKeys.result_key(config_id, None)

        assert key == "simulation:result:config-123:latest"

    def test_tornado_key(self):
        """Should generate tornado chart key with top_n."""
        config_id = "config-123"
        result_id = "result-456"
        top_n = 10

        key = SimulationCacheKeys.tornado_key(config_id, result_id, top_n)

        assert key == "simulation:tornado:config-123:result-456:top10"

    def test_tornado_key_different_top_n(self):
        """Different top_n values should produce different keys."""
        config_id = "config-123"
        result_id = "result-456"

        key1 = SimulationCacheKeys.tornado_key(config_id, result_id, 5)
        key2 = SimulationCacheKeys.tornado_key(config_id, result_id, 10)

        assert key1 != key2
        assert "top5" in key1
        assert "top10" in key2

    def test_histogram_key(self):
        """Should generate histogram key with type."""
        config_id = "config-123"
        result_id = "result-456"

        duration_key = SimulationCacheKeys.histogram_key(config_id, result_id, "duration")
        cost_key = SimulationCacheKeys.histogram_key(config_id, result_id, "cost")

        assert duration_key == "simulation:histogram:config-123:result-456:duration"
        assert cost_key == "simulation:histogram:config-123:result-456:cost"

    def test_ttl_values(self):
        """Should have correct TTL values."""
        assert SimulationCacheKeys.RESULT_TTL == 86400  # 24 hours
        assert SimulationCacheKeys.TORNADO_TTL == 86400
        assert SimulationCacheKeys.HISTOGRAM_TTL == 86400


class TestSimulationCacheIsAvailable:
    """Tests for cache availability check."""

    def test_is_available_when_manager_available(self):
        """Should return True when manager is available."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True

        cache = SimulationCache(mock_manager)

        assert cache.is_available is True

    def test_is_available_when_manager_unavailable(self):
        """Should return False when manager is unavailable."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = False

        cache = SimulationCache(mock_manager)

        assert cache.is_available is False


class TestSimulationCacheGetResult:
    """Tests for get_result method."""

    @pytest.mark.asyncio
    async def test_get_result_cache_hit(self):
        """Should return cached result on hit."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value={"status": "completed", "mean": 100.5})

        cache = SimulationCache(mock_manager)
        config_id = uuid4()
        result_id = uuid4()

        result = await cache.get_result(config_id, result_id)

        assert result == {"status": "completed", "mean": 100.5}
        mock_manager.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_result_cache_miss(self):
        """Should return None on cache miss."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value=None)

        cache = SimulationCache(mock_manager)
        config_id = uuid4()
        result_id = uuid4()

        result = await cache.get_result(config_id, result_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_result_without_result_id(self):
        """Should use 'latest' key when result_id is None."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value=None)

        cache = SimulationCache(mock_manager)
        config_id = uuid4()

        await cache.get_result(config_id, None)

        # Verify the key contains 'latest'
        call_args = mock_manager.get.call_args[0][0]
        assert "latest" in call_args


class TestSimulationCacheSetResult:
    """Tests for set_result method."""

    @pytest.mark.asyncio
    async def test_set_result_success(self):
        """Should cache result successfully."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.set = AsyncMock(return_value=True)

        cache = SimulationCache(mock_manager)
        config_id = uuid4()
        result_id = uuid4()
        result_data = {"status": "completed", "mean": 100.5}

        success = await cache.set_result(config_id, result_data, result_id)

        assert success is True
        mock_manager.set.assert_called_once()
        call_args = mock_manager.set.call_args
        assert call_args[1]["ttl"] == SimulationCacheKeys.RESULT_TTL

    @pytest.mark.asyncio
    async def test_set_result_custom_ttl(self):
        """Should use custom TTL when provided."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.set = AsyncMock(return_value=True)

        cache = SimulationCache(mock_manager)
        config_id = uuid4()
        custom_ttl = 3600  # 1 hour

        await cache.set_result(config_id, {"data": "test"}, ttl=custom_ttl)

        call_args = mock_manager.set.call_args
        assert call_args[1]["ttl"] == custom_ttl

    @pytest.mark.asyncio
    async def test_set_result_failure(self):
        """Should return False when caching fails."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.set = AsyncMock(return_value=False)

        cache = SimulationCache(mock_manager)
        config_id = uuid4()

        success = await cache.set_result(config_id, {"data": "test"})

        assert success is False


class TestSimulationCacheInvalidateResult:
    """Tests for invalidate_result method."""

    @pytest.mark.asyncio
    async def test_invalidate_specific_result(self):
        """Should invalidate specific result."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.delete = AsyncMock(return_value=True)

        cache = SimulationCache(mock_manager)
        config_id = uuid4()
        result_id = uuid4()

        success = await cache.invalidate_result(config_id, result_id)

        assert success is True
        mock_manager.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_all_results_for_config(self):
        """Should invalidate all results when result_id is None."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.delete_pattern = AsyncMock(return_value=5)

        cache = SimulationCache(mock_manager)
        config_id = uuid4()

        success = await cache.invalidate_result(config_id, None)

        assert success is True
        mock_manager.delete_pattern.assert_called_once()
        # Verify pattern includes config_id
        call_args = mock_manager.delete_pattern.call_args[0][0]
        assert str(config_id) in call_args


class TestSimulationCacheGetOrCompute:
    """Tests for get_or_compute method."""

    @pytest.mark.asyncio
    async def test_get_or_compute_cache_hit(self):
        """Should return cached result without computing."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value={"status": "completed"})

        cache = SimulationCache(mock_manager)
        config_id = uuid4()
        compute_func = AsyncMock(return_value={"status": "new"})

        result = await cache.get_or_compute(config_id, compute_func)

        assert result["status"] == "completed"
        assert result["from_cache"] is True
        compute_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_compute_cache_miss(self):
        """Should compute and cache on miss."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value=None)
        mock_manager.set = AsyncMock(return_value=True)

        cache = SimulationCache(mock_manager)
        config_id = uuid4()
        compute_func = AsyncMock(return_value={"status": "computed"})

        result = await cache.get_or_compute(config_id, compute_func)

        assert result["status"] == "computed"
        assert result["from_cache"] is False
        compute_func.assert_called_once()
        mock_manager.set.assert_called_once()


class TestSimulationCacheTornado:
    """Tests for tornado chart caching."""

    @pytest.mark.asyncio
    async def test_get_tornado_cache_hit(self):
        """Should return cached tornado data."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value={"base_project_duration": 100, "bars": []})

        cache = SimulationCache(mock_manager)
        config_id = uuid4()
        result_id = uuid4()

        result = await cache.get_tornado(config_id, result_id, 10)

        assert result["base_project_duration"] == 100
        mock_manager.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tornado_cache_miss(self):
        """Should return None on cache miss."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value=None)

        cache = SimulationCache(mock_manager)
        config_id = uuid4()
        result_id = uuid4()

        result = await cache.get_tornado(config_id, result_id, 10)

        assert result is None

    @pytest.mark.asyncio
    async def test_set_tornado(self):
        """Should cache tornado data."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.set = AsyncMock(return_value=True)

        cache = SimulationCache(mock_manager)
        config_id = uuid4()
        result_id = uuid4()
        tornado_data = {"base_project_duration": 100, "bars": []}

        success = await cache.set_tornado(config_id, result_id, 10, tornado_data)

        assert success is True
        mock_manager.set.assert_called_once()
        call_args = mock_manager.set.call_args
        assert call_args[1]["ttl"] == SimulationCacheKeys.TORNADO_TTL


class TestSimulationCacheInvalidateConfig:
    """Tests for invalidate_config method."""

    @pytest.mark.asyncio
    async def test_invalidate_config_deletes_all_patterns(self):
        """Should delete results, tornado charts, and histograms."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.delete_pattern = AsyncMock(return_value=2)

        cache = SimulationCache(mock_manager)
        config_id = uuid4()

        deleted = await cache.invalidate_config(config_id)

        # Should call delete_pattern 3 times (results, tornado, histogram)
        assert mock_manager.delete_pattern.call_count == 3
        assert deleted == 6  # 2 * 3 patterns

    @pytest.mark.asyncio
    async def test_invalidate_config_returns_total_deleted(self):
        """Should return total count of deleted keys."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True
        mock_manager.delete_pattern = AsyncMock(side_effect=[3, 2, 1])

        cache = SimulationCache(mock_manager)
        config_id = uuid4()

        deleted = await cache.invalidate_config(config_id)

        assert deleted == 6  # 3 + 2 + 1


class TestSimulationCacheIntegration:
    """Integration tests for cache workflow."""

    @pytest.mark.asyncio
    async def test_full_cache_workflow(self):
        """Test complete cache workflow: set, get, invalidate."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True

        stored_data = {}

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

        cache = SimulationCache(mock_manager)
        config_id = uuid4()
        result_id = uuid4()
        result_data = {"status": "completed", "mean": 100.5}

        # Initially empty
        result = await cache.get_result(config_id, result_id)
        assert result is None

        # Set result
        success = await cache.set_result(config_id, result_data, result_id)
        assert success is True

        # Get cached result
        result = await cache.get_result(config_id, result_id)
        assert result == result_data

        # Invalidate
        success = await cache.invalidate_result(config_id, result_id)
        assert success is True

        # Verify deleted
        result = await cache.get_result(config_id, result_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_different_top_n_cached_separately(self):
        """Different top_n values should be cached separately."""
        mock_manager = MagicMock(spec=CacheManager)
        mock_manager.is_available = True

        stored_data = {}

        async def mock_get(key):
            return stored_data.get(key)

        async def mock_set(key, value, ttl=None):
            stored_data[key] = value
            return True

        mock_manager.get = AsyncMock(side_effect=mock_get)
        mock_manager.set = AsyncMock(side_effect=mock_set)

        cache = SimulationCache(mock_manager)
        config_id = uuid4()
        result_id = uuid4()

        # Set tornado data with different top_n
        await cache.set_tornado(config_id, result_id, 5, {"top_n": 5, "bars": []})
        await cache.set_tornado(config_id, result_id, 10, {"top_n": 10, "bars": []})

        # Get each separately
        result5 = await cache.get_tornado(config_id, result_id, 5)
        result10 = await cache.get_tornado(config_id, result_id, 10)

        assert result5["top_n"] == 5
        assert result10["top_n"] == 10
