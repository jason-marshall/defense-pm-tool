"""Redis caching service with decorator support and metrics tracking.

Provides a high-level caching interface with:
- @cached decorator for easy function result caching
- Automatic cache metrics tracking (hits/misses)
- Configurable TTLs per cache type
- Integration with existing CacheManager
"""

from __future__ import annotations

import hashlib
from datetime import timedelta
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

from src.core.cache import CacheManager, cache_manager
from src.core.metrics import record_cache_hit, record_cache_miss

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

# Cache TTL configurations
CACHE_TTL = {
    "cpm_result": timedelta(minutes=15),
    "dashboard_metrics": timedelta(minutes=5),
    "wbs_tree": timedelta(minutes=10),
    "program_summary": timedelta(minutes=5),
    "activity_list": timedelta(minutes=2),
    "evms_summary": timedelta(minutes=5),
    "schedule": timedelta(minutes=10),
    "recommendation": timedelta(minutes=3),
}


class CacheService:
    """Enhanced caching service with metrics and decorator support.

    Provides a high-level interface for caching with:
    - Automatic metrics tracking (hits/misses via Prometheus)
    - Flexible key generation
    - TTL configuration per cache type
    - Integration with existing CacheManager

    Example usage:
        cache = CacheService()

        # Manual caching
        result = await cache.get("my_key", "my_cache")
        if result is None:
            result = await expensive_computation()
            await cache.set("my_key", result, CACHE_TTL["cpm_result"], "my_cache")

        # Or use the @cached decorator (see module-level function)
    """

    def __init__(self, manager: CacheManager | None = None) -> None:
        """Initialize cache service.

        Args:
            manager: Optional CacheManager instance. Uses global if not provided.
        """
        self._manager = manager or cache_manager

    @property
    def is_available(self) -> bool:
        """Check if cache is available."""
        return self._manager.is_available

    def make_key(self, prefix: str, *args: Any, **kwargs: Any) -> str:
        """Generate cache key from prefix and arguments.

        Creates a deterministic cache key by hashing the arguments.
        Handles UUIDs and other non-string types gracefully.

        Args:
            prefix: Key prefix (e.g., "cpm_result", "evms_summary")
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key

        Returns:
            Cache key string in format "dpm:{prefix}:{hash}"
        """
        key_parts = []

        for arg in args:
            if isinstance(arg, UUID) or arg is not None:
                key_parts.append(str(arg))

        for k, v in sorted(kwargs.items()):
            if isinstance(v, UUID) or v is not None:
                key_parts.append(f"{k}={v}")

        key_data = ":".join(key_parts)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
        return f"dpm:{prefix}:{key_hash}"

    async def get(self, key: str, cache_name: str = "default") -> Any | None:
        """Get value from cache with metrics tracking.

        Args:
            key: Cache key
            cache_name: Name for metrics tracking

        Returns:
            Cached value or None if not found
        """
        result = await self._manager.get(key)

        if result is not None:
            record_cache_hit(cache_name)
            logger.debug("cache_service_hit", key=key, cache_name=cache_name)
        else:
            record_cache_miss(cache_name)
            logger.debug("cache_service_miss", key=key, cache_name=cache_name)

        return result

    async def set(
        self,
        key: str,
        value: Any,
        ttl: timedelta | None = None,
        cache_name: str = "default",
    ) -> bool:
        """Set value in cache with metrics tracking.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live (optional)
            cache_name: Name for metrics tracking

        Returns:
            True if successful, False otherwise
        """
        ttl_seconds = int(ttl.total_seconds()) if ttl else None
        success = await self._manager.set(key, value, ttl=ttl_seconds)

        if success:
            logger.debug(
                "cache_service_set",
                key=key,
                cache_name=cache_name,
                ttl_seconds=ttl_seconds,
            )

        return success

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        return await self._manager.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern.

        Args:
            pattern: Key pattern with wildcards (e.g., "dpm:cpm_result:*")

        Returns:
            Number of keys deleted
        """
        return await self._manager.delete_pattern(pattern)

    async def invalidate_program(self, program_id: UUID) -> None:
        """Invalidate all caches for a program.

        Args:
            program_id: Program UUID
        """
        await self._manager.invalidate_program(str(program_id))
        logger.info("cache_service_invalidate_program", program_id=str(program_id))

    async def invalidate_cpm(self, program_id: UUID) -> None:
        """Invalidate CPM cache for a program.

        Args:
            program_id: Program UUID
        """
        await self._manager.invalidate_cpm(str(program_id))
        logger.info("cache_service_invalidate_cpm", program_id=str(program_id))

    async def invalidate_evms(self, program_id: UUID) -> None:
        """Invalidate EVMS cache for a program.

        Args:
            program_id: Program UUID
        """
        await self._manager.invalidate_evms(str(program_id))
        logger.info("cache_service_invalidate_evms", program_id=str(program_id))


# Global cache service instance
_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    """Get or create cache service singleton.

    Returns:
        CacheService instance
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


def cached(
    cache_name: str,
    ttl: timedelta | None = None,
    key_prefix: str | None = None,
    skip_first_arg: bool = True,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator to cache async function results.

    Caches the return value of an async function using the function name
    and arguments as the cache key.

    Args:
        cache_name: Name for cache TTL lookup and metrics
        ttl: Optional TTL override (defaults to CACHE_TTL[cache_name])
        key_prefix: Optional key prefix (defaults to function name)
        skip_first_arg: Skip first argument (self) in key generation

    Returns:
        Decorated function

    Example:
        class MyService:
            @cached("evms_summary", ttl=timedelta(minutes=5))
            async def get_summary(self, program_id: UUID) -> dict:
                # Expensive computation
                return {"data": "..."}
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache = get_cache_service()

            # Skip caching if cache is not available
            if not cache.is_available:
                return await func(*args, **kwargs)

            # Generate cache key
            prefix = key_prefix or func.__name__

            # Skip 'self' argument for instance methods
            key_args = args[1:] if skip_first_arg and args else args

            cache_key = cache.make_key(prefix, *key_args, **kwargs)

            # Try cache
            cached_value = await cache.get(cache_key, cache_name)
            if cached_value is not None:
                return cached_value  # type: ignore[no-any-return]

            # Call function
            result = await func(*args, **kwargs)

            # Store in cache
            cache_ttl = ttl or CACHE_TTL.get(cache_name, timedelta(minutes=5))
            await cache.set(cache_key, result, cache_ttl, cache_name)

            return result

        return wrapper

    return decorator
