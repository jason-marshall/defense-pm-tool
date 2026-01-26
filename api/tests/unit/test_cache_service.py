"""Unit tests for cache service."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.cache_service import (
    CACHE_TTL,
    CacheService,
    cached,
    get_cache_service,
)


class TestCacheService:
    """Tests for CacheService class."""

    def test_make_key_basic(self) -> None:
        """Test cache key generation with basic arguments."""
        mock_manager = MagicMock()
        service = CacheService(manager=mock_manager)

        key = service.make_key("test", "arg1", "arg2")
        assert key.startswith("dpm:test:")
        assert len(key) > 15  # Has hash component

    def test_make_key_with_uuid(self) -> None:
        """Test cache key generation with UUID arguments."""
        mock_manager = MagicMock()
        service = CacheService(manager=mock_manager)

        test_uuid = uuid4()
        key = service.make_key("program", test_uuid)
        assert key.startswith("dpm:program:")
        assert str(test_uuid)[:8] not in key  # UUID is hashed

    def test_make_key_with_kwargs(self) -> None:
        """Test cache key generation with keyword arguments."""
        mock_manager = MagicMock()
        service = CacheService(manager=mock_manager)

        key = service.make_key("test", foo="bar", baz=123)
        assert key.startswith("dpm:test:")

    def test_make_key_deterministic(self) -> None:
        """Test that same arguments produce same key."""
        mock_manager = MagicMock()
        service = CacheService(manager=mock_manager)

        key1 = service.make_key("test", "arg1", foo="bar")
        key2 = service.make_key("test", "arg1", foo="bar")
        assert key1 == key2

    def test_make_key_different_args(self) -> None:
        """Test that different arguments produce different keys."""
        mock_manager = MagicMock()
        service = CacheService(manager=mock_manager)

        key1 = service.make_key("test", "arg1")
        key2 = service.make_key("test", "arg2")
        assert key1 != key2

    def test_is_available(self) -> None:
        """Test is_available property."""
        mock_manager = MagicMock()
        mock_manager.is_available = True
        service = CacheService(manager=mock_manager)

        assert service.is_available is True

    @pytest.mark.asyncio
    async def test_get_cache_hit(self) -> None:
        """Test get with cache hit."""
        mock_manager = MagicMock()
        mock_manager.get = AsyncMock(return_value={"data": "test"})
        mock_manager.is_available = True
        service = CacheService(manager=mock_manager)

        with patch("src.services.cache_service.record_cache_hit") as mock_hit:
            result = await service.get("test_key", "test_cache")

        assert result == {"data": "test"}
        mock_hit.assert_called_once_with("test_cache")

    @pytest.mark.asyncio
    async def test_get_cache_miss(self) -> None:
        """Test get with cache miss."""
        mock_manager = MagicMock()
        mock_manager.get = AsyncMock(return_value=None)
        mock_manager.is_available = True
        service = CacheService(manager=mock_manager)

        with patch("src.services.cache_service.record_cache_miss") as mock_miss:
            result = await service.get("test_key", "test_cache")

        assert result is None
        mock_miss.assert_called_once_with("test_cache")

    @pytest.mark.asyncio
    async def test_set(self) -> None:
        """Test set method."""
        mock_manager = MagicMock()
        mock_manager.set = AsyncMock(return_value=True)
        mock_manager.is_available = True
        service = CacheService(manager=mock_manager)

        result = await service.set(
            "test_key",
            {"data": "test"},
            ttl=timedelta(minutes=5),
            cache_name="test_cache",
        )

        assert result is True
        mock_manager.set.assert_called_once_with("test_key", {"data": "test"}, ttl=300)

    @pytest.mark.asyncio
    async def test_set_without_ttl(self) -> None:
        """Test set method without TTL."""
        mock_manager = MagicMock()
        mock_manager.set = AsyncMock(return_value=True)
        mock_manager.is_available = True
        service = CacheService(manager=mock_manager)

        result = await service.set("test_key", {"data": "test"})

        assert result is True
        mock_manager.set.assert_called_once_with("test_key", {"data": "test"}, ttl=None)

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """Test delete method."""
        mock_manager = MagicMock()
        mock_manager.delete = AsyncMock(return_value=True)
        service = CacheService(manager=mock_manager)

        result = await service.delete("test_key")

        assert result is True
        mock_manager.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_pattern(self) -> None:
        """Test delete_pattern method."""
        mock_manager = MagicMock()
        mock_manager.delete_pattern = AsyncMock(return_value=5)
        service = CacheService(manager=mock_manager)

        result = await service.delete_pattern("dpm:test:*")

        assert result == 5
        mock_manager.delete_pattern.assert_called_once_with("dpm:test:*")

    @pytest.mark.asyncio
    async def test_invalidate_program(self) -> None:
        """Test invalidate_program method."""
        mock_manager = MagicMock()
        mock_manager.invalidate_program = AsyncMock()
        service = CacheService(manager=mock_manager)

        program_id = uuid4()
        await service.invalidate_program(program_id)

        mock_manager.invalidate_program.assert_called_once_with(str(program_id))

    @pytest.mark.asyncio
    async def test_invalidate_cpm(self) -> None:
        """Test invalidate_cpm method."""
        mock_manager = MagicMock()
        mock_manager.invalidate_cpm = AsyncMock()
        service = CacheService(manager=mock_manager)

        program_id = uuid4()
        await service.invalidate_cpm(program_id)

        mock_manager.invalidate_cpm.assert_called_once_with(str(program_id))

    @pytest.mark.asyncio
    async def test_invalidate_evms(self) -> None:
        """Test invalidate_evms method."""
        mock_manager = MagicMock()
        mock_manager.invalidate_evms = AsyncMock()
        service = CacheService(manager=mock_manager)

        program_id = uuid4()
        await service.invalidate_evms(program_id)

        mock_manager.invalidate_evms.assert_called_once_with(str(program_id))


class TestGetCacheService:
    """Tests for get_cache_service function."""

    def test_returns_singleton(self) -> None:
        """Test that get_cache_service returns a singleton."""
        # Reset the global
        import src.services.cache_service as module

        module._cache_service = None

        service1 = get_cache_service()
        service2 = get_cache_service()

        assert service1 is service2


class TestCachedDecorator:
    """Tests for @cached decorator."""

    @pytest.mark.asyncio
    async def test_cached_miss_then_hit(self) -> None:
        """Test decorator caches result on miss."""
        call_count = 0

        mock_manager = MagicMock()
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(side_effect=[None, {"result": "cached"}])
        mock_manager.set = AsyncMock(return_value=True)

        # Patch the get_cache_service to return our mock
        mock_service = CacheService(manager=mock_manager)

        with patch("src.services.cache_service.get_cache_service", return_value=mock_service):

            @cached(cache_name="test_cache", ttl=timedelta(minutes=5))
            async def test_func(self: object, arg1: str) -> dict:
                nonlocal call_count
                call_count += 1
                return {"result": arg1}

            # First call - cache miss, function executed
            result1 = await test_func(None, "test")
            assert result1 == {"result": "test"}
            assert call_count == 1

            # Second call - cache hit
            result2 = await test_func(None, "test")
            assert result2 == {"result": "cached"}
            assert call_count == 1  # Function not called again

    @pytest.mark.asyncio
    async def test_cached_skips_when_unavailable(self) -> None:
        """Test decorator skips caching when cache unavailable."""
        call_count = 0

        mock_manager = MagicMock()
        mock_manager.is_available = False

        mock_service = CacheService(manager=mock_manager)

        with patch("src.services.cache_service.get_cache_service", return_value=mock_service):

            @cached(cache_name="test_cache")
            async def test_func(self: object) -> str:
                nonlocal call_count
                call_count += 1
                return "result"

            # Multiple calls should all execute function
            await test_func(None)
            await test_func(None)

            assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_with_custom_prefix(self) -> None:
        """Test decorator with custom key prefix."""
        mock_manager = MagicMock()
        mock_manager.is_available = True
        mock_manager.get = AsyncMock(return_value=None)
        mock_manager.set = AsyncMock(return_value=True)

        mock_service = CacheService(manager=mock_manager)

        with patch("src.services.cache_service.get_cache_service", return_value=mock_service):

            @cached(cache_name="test", key_prefix="custom_prefix")
            async def test_func(self: object) -> str:
                return "result"

            await test_func(None)

            # Verify set was called (cache key generation uses our prefix)
            mock_manager.set.assert_called_once()
            call_args = mock_manager.set.call_args
            assert "custom_prefix" in call_args[0][0]


class TestCacheTTL:
    """Tests for CACHE_TTL configuration."""

    def test_cache_ttl_values(self) -> None:
        """Test CACHE_TTL has expected values."""
        assert "cpm_result" in CACHE_TTL
        assert "dashboard_metrics" in CACHE_TTL
        assert "wbs_tree" in CACHE_TTL
        assert "evms_summary" in CACHE_TTL

    def test_cache_ttl_types(self) -> None:
        """Test CACHE_TTL values are timedeltas."""
        for key, value in CACHE_TTL.items():
            assert isinstance(value, timedelta), f"{key} should be timedelta"

    def test_cache_ttl_reasonable(self) -> None:
        """Test CACHE_TTL values are reasonable."""
        for key, value in CACHE_TTL.items():
            # At least 1 minute, at most 1 hour
            assert value >= timedelta(minutes=1), f"{key} TTL too short"
            assert value <= timedelta(hours=1), f"{key} TTL too long"
