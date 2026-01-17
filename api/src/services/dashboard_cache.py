"""Dashboard caching service for optimized dashboard performance.

Provides Redis caching for dashboard components with intelligent invalidation.
Extends the core CacheManager with dashboard-specific functionality.

Performance targets per Risk Playbook Week 8:
- Individual endpoints: <500ms
- Full dashboard load: <3s

Cache TTLs:
- EVMS metrics: 5 minutes (data changes with period updates)
- S-curve: 15 minutes (includes simulation data, less frequent changes)
- WBS tree: 1 hour (structural changes are rare)
"""

from typing import Any
from uuid import UUID

import structlog

from src.core.cache import CacheManager, cache_manager

logger = structlog.get_logger(__name__)


class DashboardCacheKeys:
    """Cache key prefixes for dashboard components."""

    # Key prefixes
    DASHBOARD_METRICS = "dashboard:metrics"
    DASHBOARD_SCURVE = "dashboard:scurve"
    DASHBOARD_WBS = "dashboard:wbs"
    DASHBOARD_ACTIVITIES = "dashboard:activities"
    DASHBOARD_SCHEDULE = "dashboard:schedule"

    # TTLs in seconds
    METRICS_TTL = 300  # 5 minutes
    SCURVE_TTL = 900  # 15 minutes
    WBS_TTL = 3600  # 1 hour
    ACTIVITIES_TTL = 300  # 5 minutes
    SCHEDULE_TTL = 600  # 10 minutes

    @staticmethod
    def metrics_key(program_id: str) -> str:
        """Generate dashboard metrics cache key."""
        return f"{DashboardCacheKeys.DASHBOARD_METRICS}:{program_id}"

    @staticmethod
    def scurve_key(program_id: str, enhanced: bool = False) -> str:
        """Generate S-curve cache key."""
        suffix = ":enhanced" if enhanced else ":basic"
        return f"{DashboardCacheKeys.DASHBOARD_SCURVE}:{program_id}{suffix}"

    @staticmethod
    def wbs_key(program_id: str) -> str:
        """Generate WBS tree cache key."""
        return f"{DashboardCacheKeys.DASHBOARD_WBS}:{program_id}"

    @staticmethod
    def activities_key(program_id: str) -> str:
        """Generate activities list cache key."""
        return f"{DashboardCacheKeys.DASHBOARD_ACTIVITIES}:{program_id}"

    @staticmethod
    def schedule_key(program_id: str) -> str:
        """Generate schedule cache key."""
        return f"{DashboardCacheKeys.DASHBOARD_SCHEDULE}:{program_id}"


class DashboardCache:
    """Cache for dashboard data with component-level granularity.

    Provides methods for caching and invalidating dashboard components:
    - EVMS metrics (summary data)
    - S-curve data (historical + forecast)
    - WBS tree structure
    - Activities list
    - Schedule calculations

    Uses intelligent invalidation to maintain data consistency while
    maximizing cache hit rates.

    Example usage:
        cache = DashboardCache()

        # Get or compute cached data
        metrics = await cache.get_metrics(program_id)
        if not metrics:
            metrics = await compute_metrics(program_id)
            await cache.set_metrics(program_id, metrics)

        # Invalidate when data changes
        await cache.invalidate_on_period_update(program_id)
    """

    def __init__(self, manager: CacheManager | None = None) -> None:
        """Initialize dashboard cache.

        Args:
            manager: Optional CacheManager instance. Uses global if not provided.
        """
        self._manager = manager or cache_manager

    @property
    def is_available(self) -> bool:
        """Check if cache is available."""
        return self._manager.is_available

    # =========================================================================
    # EVMS Metrics
    # =========================================================================

    async def get_metrics(self, program_id: UUID) -> dict[str, Any] | None:
        """Get cached EVMS metrics.

        Args:
            program_id: Program UUID

        Returns:
            Cached metrics dict or None if not found
        """
        key = DashboardCacheKeys.metrics_key(str(program_id))
        result = await self._manager.get(key)

        if result:
            logger.debug("dashboard_metrics_cache_hit", program_id=str(program_id))
        else:
            logger.debug("dashboard_metrics_cache_miss", program_id=str(program_id))

        return result

    async def set_metrics(
        self,
        program_id: UUID,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Cache EVMS metrics.

        Args:
            program_id: Program UUID
            data: Metrics data to cache
            ttl: Optional TTL override in seconds

        Returns:
            True if cached successfully
        """
        key = DashboardCacheKeys.metrics_key(str(program_id))
        ttl = ttl or DashboardCacheKeys.METRICS_TTL

        success = await self._manager.set(key, data, ttl=ttl)

        if success:
            logger.debug(
                "dashboard_metrics_cache_set",
                program_id=str(program_id),
                ttl=ttl,
            )

        return success

    # =========================================================================
    # S-Curve
    # =========================================================================

    async def get_scurve(
        self,
        program_id: UUID,
        enhanced: bool = False,
    ) -> dict[str, Any] | None:
        """Get cached S-curve data.

        Args:
            program_id: Program UUID
            enhanced: Whether to get enhanced S-curve with Monte Carlo bands

        Returns:
            Cached S-curve dict or None if not found
        """
        key = DashboardCacheKeys.scurve_key(str(program_id), enhanced=enhanced)
        result = await self._manager.get(key)

        if result:
            logger.debug(
                "dashboard_scurve_cache_hit",
                program_id=str(program_id),
                enhanced=enhanced,
            )
        else:
            logger.debug(
                "dashboard_scurve_cache_miss",
                program_id=str(program_id),
                enhanced=enhanced,
            )

        return result

    async def set_scurve(
        self,
        program_id: UUID,
        data: dict[str, Any],
        enhanced: bool = False,
        ttl: int | None = None,
    ) -> bool:
        """Cache S-curve data.

        Args:
            program_id: Program UUID
            data: S-curve data to cache
            enhanced: Whether this is enhanced S-curve data
            ttl: Optional TTL override in seconds

        Returns:
            True if cached successfully
        """
        key = DashboardCacheKeys.scurve_key(str(program_id), enhanced=enhanced)
        ttl = ttl or DashboardCacheKeys.SCURVE_TTL

        success = await self._manager.set(key, data, ttl=ttl)

        if success:
            logger.debug(
                "dashboard_scurve_cache_set",
                program_id=str(program_id),
                enhanced=enhanced,
                ttl=ttl,
            )

        return success

    # =========================================================================
    # WBS Tree
    # =========================================================================

    async def get_wbs_tree(self, program_id: UUID) -> dict[str, Any] | None:
        """Get cached WBS tree.

        Args:
            program_id: Program UUID

        Returns:
            Cached WBS tree dict or None if not found
        """
        key = DashboardCacheKeys.wbs_key(str(program_id))
        result = await self._manager.get(key)

        if result:
            logger.debug("dashboard_wbs_cache_hit", program_id=str(program_id))
        else:
            logger.debug("dashboard_wbs_cache_miss", program_id=str(program_id))

        return result

    async def set_wbs_tree(
        self,
        program_id: UUID,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Cache WBS tree.

        Args:
            program_id: Program UUID
            data: WBS tree data to cache
            ttl: Optional TTL override in seconds

        Returns:
            True if cached successfully
        """
        key = DashboardCacheKeys.wbs_key(str(program_id))
        ttl = ttl or DashboardCacheKeys.WBS_TTL

        success = await self._manager.set(key, data, ttl=ttl)

        if success:
            logger.debug(
                "dashboard_wbs_cache_set",
                program_id=str(program_id),
                ttl=ttl,
            )

        return success

    # =========================================================================
    # Activities List
    # =========================================================================

    async def get_activities(self, program_id: UUID) -> dict[str, Any] | None:
        """Get cached activities list.

        Args:
            program_id: Program UUID

        Returns:
            Cached activities list or None if not found
        """
        key = DashboardCacheKeys.activities_key(str(program_id))
        result = await self._manager.get(key)

        if result:
            logger.debug("dashboard_activities_cache_hit", program_id=str(program_id))
        else:
            logger.debug("dashboard_activities_cache_miss", program_id=str(program_id))

        return result

    async def set_activities(
        self,
        program_id: UUID,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Cache activities list.

        Args:
            program_id: Program UUID
            data: Activities data to cache
            ttl: Optional TTL override in seconds

        Returns:
            True if cached successfully
        """
        key = DashboardCacheKeys.activities_key(str(program_id))
        ttl = ttl or DashboardCacheKeys.ACTIVITIES_TTL

        success = await self._manager.set(key, data, ttl=ttl)

        if success:
            logger.debug(
                "dashboard_activities_cache_set",
                program_id=str(program_id),
                ttl=ttl,
            )

        return success

    # =========================================================================
    # Schedule
    # =========================================================================

    async def get_schedule(self, program_id: UUID) -> dict[str, Any] | None:
        """Get cached schedule calculation.

        Args:
            program_id: Program UUID

        Returns:
            Cached schedule or None if not found
        """
        key = DashboardCacheKeys.schedule_key(str(program_id))
        result = await self._manager.get(key)

        if result:
            logger.debug("dashboard_schedule_cache_hit", program_id=str(program_id))
        else:
            logger.debug("dashboard_schedule_cache_miss", program_id=str(program_id))

        return result

    async def set_schedule(
        self,
        program_id: UUID,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Cache schedule calculation.

        Args:
            program_id: Program UUID
            data: Schedule data to cache
            ttl: Optional TTL override in seconds

        Returns:
            True if cached successfully
        """
        key = DashboardCacheKeys.schedule_key(str(program_id))
        ttl = ttl or DashboardCacheKeys.SCHEDULE_TTL

        success = await self._manager.set(key, data, ttl=ttl)

        if success:
            logger.debug(
                "dashboard_schedule_cache_set",
                program_id=str(program_id),
                ttl=ttl,
            )

        return success

    # =========================================================================
    # Invalidation Methods
    # =========================================================================

    async def invalidate_program(self, program_id: UUID) -> int:
        """Invalidate all dashboard caches for a program.

        Use when program-level data changes (delete, major update).

        Args:
            program_id: Program UUID

        Returns:
            Number of keys deleted
        """
        patterns = [
            f"{DashboardCacheKeys.DASHBOARD_METRICS}:{program_id}",
            f"{DashboardCacheKeys.DASHBOARD_SCURVE}:{program_id}:*",
            f"{DashboardCacheKeys.DASHBOARD_WBS}:{program_id}",
            f"{DashboardCacheKeys.DASHBOARD_ACTIVITIES}:{program_id}",
            f"{DashboardCacheKeys.DASHBOARD_SCHEDULE}:{program_id}",
        ]

        total_deleted = 0
        for pattern in patterns:
            if "*" in pattern:
                deleted = await self._manager.delete_pattern(pattern)
            else:
                success = await self._manager.delete(pattern)
                deleted = 1 if success else 0
            total_deleted += deleted

        logger.info(
            "dashboard_cache_invalidate_program",
            program_id=str(program_id),
            keys_deleted=total_deleted,
        )

        return total_deleted

    async def invalidate_on_period_update(self, program_id: UUID) -> None:
        """Invalidate caches affected by EVMS period changes.

        Invalidates metrics and S-curve but keeps WBS tree.

        Args:
            program_id: Program UUID
        """
        keys_to_delete = [
            DashboardCacheKeys.metrics_key(str(program_id)),
            DashboardCacheKeys.scurve_key(str(program_id), enhanced=False),
            DashboardCacheKeys.scurve_key(str(program_id), enhanced=True),
        ]

        for key in keys_to_delete:
            await self._manager.delete(key)

        logger.info(
            "dashboard_cache_invalidate_period",
            program_id=str(program_id),
        )

    async def invalidate_on_activity_update(self, program_id: UUID) -> None:
        """Invalidate caches affected by activity changes.

        Invalidates activities, schedule, and S-curve but keeps WBS and metrics.

        Args:
            program_id: Program UUID
        """
        keys_to_delete = [
            DashboardCacheKeys.activities_key(str(program_id)),
            DashboardCacheKeys.schedule_key(str(program_id)),
            DashboardCacheKeys.scurve_key(str(program_id), enhanced=False),
            DashboardCacheKeys.scurve_key(str(program_id), enhanced=True),
        ]

        for key in keys_to_delete:
            await self._manager.delete(key)

        logger.info(
            "dashboard_cache_invalidate_activity",
            program_id=str(program_id),
        )

    async def invalidate_on_wbs_update(self, program_id: UUID) -> None:
        """Invalidate caches affected by WBS changes.

        Invalidates WBS tree and activities (since activities reference WBS).

        Args:
            program_id: Program UUID
        """
        keys_to_delete = [
            DashboardCacheKeys.wbs_key(str(program_id)),
            DashboardCacheKeys.activities_key(str(program_id)),
        ]

        for key in keys_to_delete:
            await self._manager.delete(key)

        logger.info(
            "dashboard_cache_invalidate_wbs",
            program_id=str(program_id),
        )

    async def invalidate_on_simulation_update(self, program_id: UUID) -> None:
        """Invalidate caches affected by simulation result changes.

        Invalidates enhanced S-curve (which uses simulation data).

        Args:
            program_id: Program UUID
        """
        key = DashboardCacheKeys.scurve_key(str(program_id), enhanced=True)
        await self._manager.delete(key)

        logger.info(
            "dashboard_cache_invalidate_simulation",
            program_id=str(program_id),
        )


# Global dashboard cache instance
dashboard_cache = DashboardCache()
