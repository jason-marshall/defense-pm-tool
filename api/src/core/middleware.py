"""Custom middleware for request tracing and metrics."""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.metrics import http_request_duration_seconds, http_requests_total

if TYPE_CHECKING:
    from starlette.types import ASGIApp

logger = structlog.get_logger()


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Add correlation ID and timing to all requests."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with tracing and metrics."""
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        # Bind correlation ID to logger context
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        # Track request timing
        start_time = time.perf_counter()

        # Extract endpoint for metrics (normalize path parameters)
        endpoint = self._normalize_endpoint(request)

        try:
            response = await call_next(request)

            # Record metrics
            duration = time.perf_counter() - start_time
            self._record_metrics(request.method, endpoint, response.status_code, duration)

            # Add correlation ID to response
            response.headers["X-Correlation-ID"] = correlation_id

            # Log request completion
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                client_ip=self._get_client_ip(request),
            )

            return response

        except Exception as e:
            duration = time.perf_counter() - start_time
            self._record_metrics(request.method, endpoint, 500, duration)

            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration * 1000, 2),
                client_ip=self._get_client_ip(request),
            )
            raise
        finally:
            structlog.contextvars.unbind_contextvars("correlation_id")

    def _normalize_endpoint(self, request: Request) -> str:
        """Normalize endpoint path by replacing path parameters with placeholders."""
        endpoint = request.url.path

        # Replace UUIDs with placeholder
        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        endpoint = re.sub(uuid_pattern, "{id}", endpoint, flags=re.IGNORECASE)

        # Replace numeric IDs with placeholder
        endpoint = re.sub(r"/\d+(?=/|$)", "/{id}", endpoint)

        return endpoint

    def _record_metrics(
        self, method: str, endpoint: str, status_code: int, duration: float
    ) -> None:
        """Record request metrics."""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code),
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, considering proxies."""
        # Check for forwarded header (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    def __init__(self, app: ASGIApp, csp_enabled: bool = True, hsts_enabled: bool = False) -> None:
        super().__init__(app)
        self.csp_enabled = csp_enabled
        self.hsts_enabled = hsts_enabled

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        if self.csp_enabled:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )

        # HTTP Strict Transport Security
        if self.hsts_enabled:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Remove server header if present
        if "server" in response.headers:
            del response.headers["server"]

        return response
