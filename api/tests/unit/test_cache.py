"""Unit tests for Redis caching utilities."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import redis.asyncio as redis

from src.core.cache import (
    CacheKeys,
    CacheManager,
    compute_activities_hash,
)


class TestCacheKeys:
    """Tests for CacheKeys class."""

    def test_cpm_key_generation(self) -> None:
        """Test CPM cache key generation."""
        key = CacheKeys.cpm_key("program-123", "hash-abc")
        assert key == "cpm:result:program-123:hash-abc"

    def test_evms_summary_key_generation(self) -> None:
        """Test EVMS summary cache key generation."""
        key = CacheKeys.evms_summary_key("program-123")
        assert key == "evms:summary:program-123"

    def test_wbs_tree_key_generation(self) -> None:
        """Test WBS tree cache key generation."""
        key = CacheKeys.wbs_tree_key("program-123")
        assert key == "wbs:tree:program-123"

    def test_program_stats_key_generation(self) -> None:
        """Test program stats cache key generation."""
        key = CacheKeys.program_stats_key("program-123")
        assert key == "program:stats:program-123"

    def test_ttl_values(self) -> None:
        """Test that TTL values are set correctly."""
        assert CacheKeys.CPM_TTL == 3600  # 1 hour
        assert CacheKeys.EVMS_TTL == 300  # 5 minutes
        assert CacheKeys.WBS_TTL == 1800  # 30 minutes
        assert CacheKeys.STATS_TTL == 60  # 1 minute


class TestComputeActivitiesHash:
    """Tests for activities hash computation."""

    def test_hash_consistency(self) -> None:
        """Test that same data produces same hash."""
        data = [
            {"id": "123", "duration": 5},
            {"id": "456", "duration": 10},
        ]
        hash1 = compute_activities_hash(data)
        hash2 = compute_activities_hash(data)
        assert hash1 == hash2

    def test_hash_order_independence(self) -> None:
        """Test that order of activities doesn't affect hash."""
        data1 = [
            {"id": "123", "duration": 5},
            {"id": "456", "duration": 10},
        ]
        data2 = [
            {"id": "456", "duration": 10},
            {"id": "123", "duration": 5},
        ]
        hash1 = compute_activities_hash(data1)
        hash2 = compute_activities_hash(data2)
        assert hash1 == hash2

    def test_hash_changes_with_data(self) -> None:
        """Test that different data produces different hash."""
        data1 = [{"id": "123", "duration": 5}]
        data2 = [{"id": "123", "duration": 10}]
        hash1 = compute_activities_hash(data1)
        hash2 = compute_activities_hash(data2)
        assert hash1 != hash2

    def test_hash_length(self) -> None:
        """Test that hash is truncated to 16 characters."""
        data = [{"id": "123", "duration": 5}]
        hash_value = compute_activities_hash(data)
        assert len(hash_value) == 16

    def test_empty_data(self) -> None:
        """Test hash of empty data."""
        hash_value = compute_activities_hash([])
        assert len(hash_value) == 16


class TestCacheManager:
    """Tests for CacheManager class."""

    @pytest.fixture
    def mock_redis(self) -> MagicMock:
        """Create a mock Redis client."""
        mock = MagicMock(spec=redis.Redis)
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.setex = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.scan_iter = AsyncMock(return_value=iter([]))
        mock.info = AsyncMock(return_value={
            "connected_clients": 1,
            "used_memory_human": "1M",
            "uptime_in_seconds": 3600,
        })
        return mock

    @pytest.fixture
    def cache_manager(self, mock_redis: MagicMock) -> CacheManager:
        """Create a CacheManager with mock Redis."""
        manager = CacheManager(mock_redis)
        return manager

    def test_is_available_with_redis(self, cache_manager: CacheManager) -> None:
        """Test is_available returns True when Redis is configured."""
        assert cache_manager.is_available is True

    def test_is_available_without_redis(self) -> None:
        """Test is_available returns False when Redis is not configured."""
        manager = CacheManager()
        assert manager.is_available is False

    def test_disable_cache(self, cache_manager: CacheManager) -> None:
        """Test disabling cache."""
        cache_manager.disable()
        assert cache_manager.is_available is False

    def test_enable_cache(self, cache_manager: CacheManager) -> None:
        """Test enabling cache after disable."""
        cache_manager.disable()
        cache_manager.enable()
        assert cache_manager.is_available is True

    @pytest.mark.asyncio
    async def test_get_cache_miss(
        self,
        cache_manager: CacheManager,
        mock_redis: MagicMock,
    ) -> None:
        """Test get returns None on cache miss."""
        mock_redis.get.return_value = None
        result = await cache_manager.get("test-key")
        assert result is None
        mock_redis.get.assert_called_once_with("test-key")

    @pytest.mark.asyncio
    async def test_get_cache_hit(
        self,
        cache_manager: CacheManager,
        mock_redis: MagicMock,
    ) -> None:
        """Test get returns cached value on hit."""
        mock_redis.get.return_value = '{"foo": "bar"}'
        result = await cache_manager.get("test-key")
        assert result == {"foo": "bar"}

    @pytest.mark.asyncio
    async def test_get_returns_none_when_disabled(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Test get returns None when cache is disabled."""
        cache_manager.disable()
        result = await cache_manager.get("test-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_ttl(
        self,
        cache_manager: CacheManager,
        mock_redis: MagicMock,
    ) -> None:
        """Test set with TTL uses setex."""
        result = await cache_manager.set("test-key", {"foo": "bar"}, ttl=60)
        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_without_ttl(
        self,
        cache_manager: CacheManager,
        mock_redis: MagicMock,
    ) -> None:
        """Test set without TTL uses set."""
        result = await cache_manager.set("test-key", {"foo": "bar"})
        assert result is True
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_returns_false_when_disabled(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Test set returns False when cache is disabled."""
        cache_manager.disable()
        result = await cache_manager.set("test-key", {"foo": "bar"})
        assert result is False

    @pytest.mark.asyncio
    async def test_delete(
        self,
        cache_manager: CacheManager,
        mock_redis: MagicMock,
    ) -> None:
        """Test delete removes key."""
        result = await cache_manager.delete("test-key")
        assert result is True
        mock_redis.delete.assert_called_once_with("test-key")

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_disabled(
        self,
        cache_manager: CacheManager,
    ) -> None:
        """Test delete returns False when cache is disabled."""
        cache_manager.disable()
        result = await cache_manager.delete("test-key")
        assert result is False

    @pytest.mark.asyncio
    async def test_invalidate_program(
        self,
        cache_manager: CacheManager,
        mock_redis: MagicMock,
    ) -> None:
        """Test invalidate_program deletes all program keys."""
        # Mock scan_iter to return some keys
        async def mock_scan(*args, **kwargs):
            for key in [b"cpm:result:prog-123:hash1", b"cpm:result:prog-123:hash2"]:
                yield key

        mock_redis.scan_iter = mock_scan
        mock_redis.delete = AsyncMock(return_value=2)

        await cache_manager.invalidate_program("prog-123")

        # Should have attempted delete operations
        assert mock_redis.delete.call_count >= 1

    @pytest.mark.asyncio
    async def test_invalidate_cpm(
        self,
        cache_manager: CacheManager,
        mock_redis: MagicMock,
    ) -> None:
        """Test invalidate_cpm deletes CPM keys for program."""
        async def mock_scan(*args, **kwargs):
            for key in [b"cpm:result:prog-123:hash1"]:
                yield key

        mock_redis.scan_iter = mock_scan
        mock_redis.delete = AsyncMock(return_value=1)

        await cache_manager.invalidate_cpm("prog-123")

    @pytest.mark.asyncio
    async def test_invalidate_evms(
        self,
        cache_manager: CacheManager,
        mock_redis: MagicMock,
    ) -> None:
        """Test invalidate_evms deletes EVMS key."""
        await cache_manager.invalidate_evms("prog-123")
        mock_redis.delete.assert_called_once_with("evms:summary:prog-123")

    @pytest.mark.asyncio
    async def test_health_check_healthy(
        self,
        cache_manager: CacheManager,
        mock_redis: MagicMock,
    ) -> None:
        """Test health check when Redis is healthy."""
        result = await cache_manager.health_check()
        assert result["status"] == "healthy"
        assert "connected_clients" in result

    @pytest.mark.asyncio
    async def test_health_check_no_redis(self) -> None:
        """Test health check when Redis is not configured."""
        manager = CacheManager()
        result = await manager.health_check()
        assert result["status"] == "disabled"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(
        self,
        cache_manager: CacheManager,
        mock_redis: MagicMock,
    ) -> None:
        """Test health check when Redis fails."""
        mock_redis.info.side_effect = redis.RedisError("Connection failed")
        result = await cache_manager.health_check()
        assert result["status"] == "unhealthy"
        assert "error" in result
