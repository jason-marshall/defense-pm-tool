"""Redis caching for Monte Carlo simulation results.

Provides caching layer for expensive simulation computations.
Results are cached by config_id with a 24-hour TTL by default.

Per architecture: Probabilistic Analysis Module caching layer.
"""

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

import structlog

from src.core.cache import CacheKeys, CacheManager, cache_manager

logger = structlog.get_logger(__name__)


class SimulationCacheKeys(CacheKeys):
    """Cache key prefixes for simulation results."""

    # Key prefixes
    SIMULATION_RESULT = "simulation:result"
    SIMULATION_TORNADO = "simulation:tornado"
    SIMULATION_HISTOGRAM = "simulation:histogram"

    # TTLs in seconds
    RESULT_TTL = 86400  # 24 hours - simulation results are expensive to compute
    TORNADO_TTL = 86400  # 24 hours - derived from results
    HISTOGRAM_TTL = 86400  # 24 hours - derived from results

    @staticmethod
    def result_key(config_id: str, result_id: str | None = None) -> str:
        """Generate simulation result cache key.

        Args:
            config_id: Simulation config UUID as string
            result_id: Optional specific result UUID (uses latest if None)

        Returns:
            Cache key string
        """
        if result_id:
            return f"{SimulationCacheKeys.SIMULATION_RESULT}:{config_id}:{result_id}"
        return f"{SimulationCacheKeys.SIMULATION_RESULT}:{config_id}:latest"

    @staticmethod
    def tornado_key(config_id: str, result_id: str, top_n: int) -> str:
        """Generate tornado chart cache key.

        Args:
            config_id: Simulation config UUID as string
            result_id: Result UUID as string
            top_n: Number of top drivers

        Returns:
            Cache key string
        """
        return f"{SimulationCacheKeys.SIMULATION_TORNADO}:{config_id}:{result_id}:top{top_n}"

    @staticmethod
    def histogram_key(config_id: str, result_id: str, hist_type: str) -> str:
        """Generate histogram cache key.

        Args:
            config_id: Simulation config UUID as string
            result_id: Result UUID as string
            hist_type: "duration" or "cost"

        Returns:
            Cache key string
        """
        return f"{SimulationCacheKeys.SIMULATION_HISTOGRAM}:{config_id}:{result_id}:{hist_type}"


class SimulationCache:
    """Cache for Monte Carlo simulation results.

    Wraps CacheManager with simulation-specific key generation
    and TTL management.

    Example usage:
        cache = SimulationCache()
        result = await cache.get_or_compute(
            config_id=config_id,
            compute_func=run_simulation,
        )
    """

    def __init__(self, manager: CacheManager | None = None) -> None:
        """Initialize simulation cache.

        Args:
            manager: Optional CacheManager instance. Uses global if not provided.
        """
        self._manager = manager or cache_manager

    @property
    def is_available(self) -> bool:
        """Check if cache is available."""
        return self._manager.is_available

    async def get_result(
        self,
        config_id: UUID,
        result_id: UUID | None = None,
    ) -> dict[str, Any] | None:
        """Get cached simulation result.

        Args:
            config_id: Simulation config UUID
            result_id: Optional specific result UUID

        Returns:
            Cached result dictionary or None if not found
        """
        key = SimulationCacheKeys.result_key(str(config_id), str(result_id) if result_id else None)
        result = await self._manager.get(key)

        if result:
            logger.debug(
                "simulation_cache_hit",
                config_id=str(config_id),
                result_id=str(result_id) if result_id else "latest",
            )
        else:
            logger.debug(
                "simulation_cache_miss",
                config_id=str(config_id),
                result_id=str(result_id) if result_id else "latest",
            )

        return result

    async def set_result(
        self,
        config_id: UUID,
        result: dict[str, Any],
        result_id: UUID | None = None,
        ttl: int | None = None,
    ) -> bool:
        """Cache simulation result.

        Args:
            config_id: Simulation config UUID
            result: Result dictionary to cache
            result_id: Optional specific result UUID
            ttl: Optional TTL override in seconds

        Returns:
            True if cached successfully
        """
        key = SimulationCacheKeys.result_key(str(config_id), str(result_id) if result_id else None)
        ttl = ttl or SimulationCacheKeys.RESULT_TTL

        success = await self._manager.set(key, result, ttl=ttl)

        if success:
            logger.debug(
                "simulation_cache_set",
                config_id=str(config_id),
                result_id=str(result_id) if result_id else "latest",
                ttl=ttl,
            )

        return success

    async def invalidate_result(
        self,
        config_id: UUID,
        result_id: UUID | None = None,
    ) -> bool:
        """Invalidate cached simulation result.

        Args:
            config_id: Simulation config UUID
            result_id: Optional specific result UUID (invalidates all if None)

        Returns:
            True if invalidated successfully
        """
        if result_id:
            key = SimulationCacheKeys.result_key(str(config_id), str(result_id))
            success = await self._manager.delete(key)
        else:
            # Invalidate all results for this config
            pattern = f"{SimulationCacheKeys.SIMULATION_RESULT}:{config_id}:*"
            deleted = await self._manager.delete_pattern(pattern)
            success = deleted > 0

        logger.info(
            "simulation_cache_invalidate",
            config_id=str(config_id),
            result_id=str(result_id) if result_id else "all",
        )

        return success

    async def get_or_compute(
        self,
        config_id: UUID,
        compute_func: Callable[[], Awaitable[dict[str, Any]]],
        result_id: UUID | None = None,
        ttl: int | None = None,
    ) -> dict[str, Any]:
        """Get from cache or compute and cache.

        If result is cached, returns it with from_cache=True.
        Otherwise, calls compute_func, caches result, and returns
        with from_cache=False.

        Args:
            config_id: Simulation config UUID
            compute_func: Async function to compute result if not cached
            result_id: Optional specific result UUID
            ttl: Optional TTL override in seconds

        Returns:
            Result dictionary with from_cache indicator
        """
        # Try to get from cache first
        cached = await self.get_result(config_id, result_id)
        if cached is not None:
            cached["from_cache"] = True
            return cached

        # Compute fresh result
        result = await compute_func()

        # Cache the result
        await self.set_result(config_id, result, result_id, ttl)

        result["from_cache"] = False
        return result

    async def get_tornado(
        self,
        config_id: UUID,
        result_id: UUID,
        top_n: int,
    ) -> dict[str, Any] | None:
        """Get cached tornado chart data.

        Args:
            config_id: Simulation config UUID
            result_id: Result UUID
            top_n: Number of top drivers

        Returns:
            Cached tornado data or None
        """
        key = SimulationCacheKeys.tornado_key(str(config_id), str(result_id), top_n)
        return await self._manager.get(key)

    async def set_tornado(
        self,
        config_id: UUID,
        result_id: UUID,
        top_n: int,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Cache tornado chart data.

        Args:
            config_id: Simulation config UUID
            result_id: Result UUID
            top_n: Number of top drivers
            data: Tornado chart data
            ttl: Optional TTL override

        Returns:
            True if cached successfully
        """
        key = SimulationCacheKeys.tornado_key(str(config_id), str(result_id), top_n)
        ttl = ttl or SimulationCacheKeys.TORNADO_TTL
        return await self._manager.set(key, data, ttl=ttl)

    async def invalidate_config(self, config_id: UUID) -> int:
        """Invalidate all caches for a simulation config.

        Removes results, tornado charts, and histograms.

        Args:
            config_id: Simulation config UUID

        Returns:
            Number of keys deleted
        """
        patterns = [
            f"{SimulationCacheKeys.SIMULATION_RESULT}:{config_id}:*",
            f"{SimulationCacheKeys.SIMULATION_TORNADO}:{config_id}:*",
            f"{SimulationCacheKeys.SIMULATION_HISTOGRAM}:{config_id}:*",
        ]

        total_deleted = 0
        for pattern in patterns:
            deleted = await self._manager.delete_pattern(pattern)
            total_deleted += deleted

        logger.info(
            "simulation_cache_invalidate_config",
            config_id=str(config_id),
            keys_deleted=total_deleted,
        )

        return total_deleted


# Global simulation cache instance
simulation_cache = SimulationCache()
