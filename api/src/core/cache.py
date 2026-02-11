"""Redis caching utilities for the Defense PM Tool."""

from __future__ import annotations

import hashlib
import json
from typing import Any, TypeVar

import redis.asyncio as aioredis
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CacheKeys:
    """Cache key prefixes and generation utilities."""

    # Key prefixes
    CPM_RESULT = "cpm:result"
    EVMS_SUMMARY = "evms:summary"
    WBS_TREE = "wbs:tree"
    PROGRAM_STATS = "program:stats"

    # Default TTLs in seconds
    CPM_TTL = 3600  # 1 hour - CPM results don't change unless activities do
    EVMS_TTL = 300  # 5 minutes - Summary data refreshes more often
    WBS_TTL = 1800  # 30 minutes - WBS tree is relatively stable
    STATS_TTL = 60  # 1 minute - Stats refresh frequently

    @staticmethod
    def cpm_key(program_id: str, activities_hash: str) -> str:
        """Generate CPM result cache key."""
        return f"{CacheKeys.CPM_RESULT}:{program_id}:{activities_hash}"

    @staticmethod
    def evms_summary_key(program_id: str) -> str:
        """Generate EVMS summary cache key."""
        return f"{CacheKeys.EVMS_SUMMARY}:{program_id}"

    @staticmethod
    def wbs_tree_key(program_id: str) -> str:
        """Generate WBS tree cache key."""
        return f"{CacheKeys.WBS_TREE}:{program_id}"

    @staticmethod
    def program_stats_key(program_id: str) -> str:
        """Generate program stats cache key."""
        return f"{CacheKeys.PROGRAM_STATS}:{program_id}"


class CacheManager:
    """
    Redis cache manager with async support.

    Provides methods for caching and invalidation of application data.
    """

    def __init__(self, redis_client: aioredis.Redis[bytes] | None = None) -> None:
        """
        Initialize cache manager.

        Args:
            redis_client: Optional Redis client. If not provided, will be set later.
        """
        self._redis: aioredis.Redis[bytes] | None = redis_client
        self._enabled = True

    @property
    def redis(self) -> aioredis.Redis[bytes] | None:
        """Get Redis client."""
        return self._redis

    @redis.setter
    def redis(self, client: aioredis.Redis[bytes]) -> None:
        """Set Redis client."""
        self._redis = client

    @property
    def is_available(self) -> bool:
        """Check if cache is available."""
        return self._redis is not None and self._enabled

    def disable(self) -> None:
        """Disable caching."""
        self._enabled = False

    def enable(self) -> None:
        """Enable caching."""
        self._enabled = True

    async def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.is_available:
            return None

        redis = self._redis
        assert redis is not None  # guarded by is_available above

        try:
            data = await redis.get(key)
            if data:
                logger.debug("cache_hit", key=key)
                return json.loads(data)
            logger.debug("cache_miss", key=key)
            return None
        except aioredis.RedisError as e:
            logger.warning("cache_get_error", key=key, error=str(e))
            return None
        except json.JSONDecodeError as e:
            logger.warning("cache_decode_error", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds (optional)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available:
            return False

        redis = self._redis
        assert redis is not None  # guarded by is_available above

        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                await redis.setex(key, ttl, serialized)
            else:
                await redis.set(key, serialized)
            logger.debug("cache_set", key=key, ttl=ttl)
            return True
        except (aioredis.RedisError, TypeError, ValueError) as e:
            logger.warning("cache_set_error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available:
            return False

        redis = self._redis
        assert redis is not None  # guarded by is_available above

        try:
            await redis.delete(key)
            logger.debug("cache_delete", key=key)
            return True
        except aioredis.RedisError as e:
            logger.warning("cache_delete_error", key=key, error=str(e))
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Key pattern with wildcards (e.g., "cpm:result:*")

        Returns:
            Number of keys deleted
        """
        if not self.is_available:
            return 0

        redis = self._redis
        assert redis is not None  # guarded by is_available above

        try:
            keys = []
            async for key in redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await redis.delete(*keys)
                logger.debug("cache_delete_pattern", pattern=pattern, count=deleted)
                return deleted
            return 0
        except aioredis.RedisError as e:
            logger.warning("cache_delete_pattern_error", pattern=pattern, error=str(e))
            return 0

    async def invalidate_program(self, program_id: str) -> None:
        """
        Invalidate all caches for a program.

        Args:
            program_id: Program ID to invalidate
        """
        patterns = [
            f"{CacheKeys.CPM_RESULT}:{program_id}:*",
            f"{CacheKeys.EVMS_SUMMARY}:{program_id}",
            f"{CacheKeys.WBS_TREE}:{program_id}",
            f"{CacheKeys.PROGRAM_STATS}:{program_id}",
        ]

        for pattern in patterns:
            await self.delete_pattern(pattern)

        logger.info("cache_invalidate_program", program_id=program_id)

    async def invalidate_cpm(self, program_id: str) -> None:
        """
        Invalidate CPM cache for a program.

        Args:
            program_id: Program ID to invalidate
        """
        pattern = f"{CacheKeys.CPM_RESULT}:{program_id}:*"
        await self.delete_pattern(pattern)
        logger.info("cache_invalidate_cpm", program_id=program_id)

    async def invalidate_evms(self, program_id: str) -> None:
        """
        Invalidate EVMS cache for a program.

        Args:
            program_id: Program ID to invalidate
        """
        await self.delete(CacheKeys.evms_summary_key(program_id))
        logger.info("cache_invalidate_evms", program_id=program_id)

    async def invalidate_wbs(self, program_id: str) -> None:
        """
        Invalidate WBS tree cache for a program.

        Args:
            program_id: Program ID to invalidate
        """
        await self.delete(CacheKeys.wbs_tree_key(program_id))
        logger.info("cache_invalidate_wbs", program_id=program_id)

    async def health_check(self) -> dict[str, Any]:
        """
        Check Redis health.

        Returns:
            Health status dictionary
        """
        if not self._redis:
            return {"status": "disabled", "message": "Redis client not configured"}

        try:
            info = await self._redis.info()
            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
            }
        except aioredis.RedisError as e:
            return {"status": "unhealthy", "error": str(e)}


def compute_activities_hash(activities_data: list[dict[str, Any]]) -> str:
    """
    Compute a hash of activities for cache key generation.

    The hash captures the essential scheduling data: IDs, durations,
    and dependency information.

    Args:
        activities_data: List of activity dictionaries

    Returns:
        SHA256 hash string (first 16 characters)
    """
    # Sort for consistency
    sorted_data = sorted(activities_data, key=lambda x: str(x.get("id", "")))

    # Create a normalized string representation
    normalized = json.dumps(sorted_data, sort_keys=True, default=str)

    # Compute SHA256 hash
    hash_obj = hashlib.sha256(normalized.encode())
    return hash_obj.hexdigest()[:16]


async def init_redis() -> aioredis.Redis[bytes]:
    """
    Initialize Redis connection.

    Returns:
        Redis client instance
    """
    redis_url = str(settings.REDIS_URL)
    client = aioredis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    logger.info("redis_initialized", url=redis_url.split("@")[-1])
    return client


async def close_redis(client: aioredis.Redis[bytes]) -> None:
    """
    Close Redis connection.

    Args:
        client: Redis client to close
    """
    await client.close()
    logger.info("redis_closed")


# Global cache manager instance
cache_manager = CacheManager()
