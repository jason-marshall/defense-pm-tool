"""Health check endpoints for monitoring and observability."""

from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.core.database import get_session_maker
from src.core.metrics import db_connections_active

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


async def check_database() -> dict[str, Any]:
    """Check database connectivity and response time."""
    start = time.perf_counter()
    try:
        async with get_session_maker()() as session:
            await session.execute(text("SELECT 1"))
        duration_ms = (time.perf_counter() - start) * 1000
        return {
            "status": "healthy",
            "response_time_ms": round(duration_ms, 2),
        }
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def check_redis(request: Request) -> dict[str, Any]:
    """Check Redis connectivity and response time."""
    start = time.perf_counter()
    try:
        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return {
                "status": "disabled",
                "message": "Redis not configured",
            }
        await redis.ping()
        duration_ms = (time.perf_counter() - start) * 1000
        return {
            "status": "healthy",
            "response_time_ms": round(duration_ms, 2),
        }
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.get("")
async def health_check(request: Request) -> dict[str, Any]:
    """
    Comprehensive health check endpoint.

    Returns detailed status of the API and its dependencies including
    database and Redis connectivity.

    This endpoint is used by:
    - Load balancers for health monitoring
    - Kubernetes liveness/readiness probes
    - Monitoring systems (Prometheus, Grafana, etc.)
    """
    from src.config import settings

    db_status = await check_database()
    redis_status = await check_redis(request)

    # Overall status is healthy only if all critical dependencies are healthy
    overall_status = "healthy"
    if db_status["status"] == "unhealthy":
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "database": db_status,
            "redis": redis_status,
        },
    }


@router.get("/live")
async def liveness_probe() -> dict[str, str]:
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if the application is running.
    Used to determine if the container should be restarted.
    """
    return {"status": "alive"}


@router.get("/ready", response_model=None)
async def readiness_probe(request: Request) -> dict[str, Any] | Response:
    """
    Kubernetes readiness probe endpoint.

    Returns 200 if the application is ready to receive traffic.
    Checks database connectivity to ensure the app can process requests.
    """
    db_status = await check_database()

    if db_status["status"] == "unhealthy":
        return Response(
            content='{"status": "not ready", "reason": "database unavailable"}',
            status_code=503,
            media_type="application/json",
        )

    return {"status": "ready"}


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Exposes application metrics in Prometheus format for scraping.
    Includes:
    - HTTP request counts and durations
    - Database connection metrics
    - Business metrics (programs, activities, simulations)
    - CPM calculation performance
    - Cache hit/miss rates
    """
    # Update database connection gauge
    try:
        async with get_session_maker()() as session:
            result = await session.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            )
            active_connections = result.scalar() or 0
            db_connections_active.set(active_connections)
    except SQLAlchemyError:
        pass  # Don't fail metrics endpoint if DB query fails

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
