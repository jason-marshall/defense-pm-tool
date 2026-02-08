"""Rate limiting configuration using slowapi.

Provides rate limiting middleware and decorators for API endpoints.
Different limits for different endpoint categories:
- Default: 100/minute
- Auth: 10/minute (prevent brute force)
- Reports: 5/minute (resource intensive)
- Sync: 20/minute (external API calls)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from starlette.requests import Request

# Check if rate limiting is enabled (can be disabled for testing)
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"


def get_client_ip(request: Request) -> str:
    """
    Get client IP address for rate limiting.

    Handles X-Forwarded-For header for proxied requests.

    Args:
        request: The incoming request

    Returns:
        Client IP address string
    """
    # Check for forwarded header (behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP in chain (original client)
        return forwarded.split(",")[0].strip()

    # Fall back to direct client
    return get_remote_address(request)


# Determine rate limit storage backend
# Use Redis in production for multi-instance safety; in-memory for dev/test
def _get_rate_limit_storage() -> str:
    """Get the appropriate storage URI for rate limiting."""
    try:
        from src.config import settings  # noqa: PLC0415

        if settings.ENVIRONMENT == "production":
            return str(settings.REDIS_URL)
    except Exception:
        pass
    return "memory://"


RATE_LIMIT_STORAGE = _get_rate_limit_storage()

# Create limiter instance
# When RATE_LIMIT_ENABLED=false, the limiter is disabled and passes all requests
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["100/minute"],
    storage_uri=RATE_LIMIT_STORAGE,
    enabled=RATE_LIMIT_ENABLED,
)


# Rate limit categories
RATE_LIMIT_DEFAULT = "100/minute"
RATE_LIMIT_AUTH = "10/minute"
RATE_LIMIT_REPORTS = "5/minute"
RATE_LIMIT_SYNC = "20/minute"
RATE_LIMIT_WEBHOOK = "60/minute"


def rate_limit_exceeded_handler(_request: Request, exc: Exception) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Returns a JSON response with rate limit information and
    appropriate headers for client retry logic.

    Args:
        request: The incoming request
        exc: The rate limit exceeded exception

    Returns:
        JSONResponse with 429 status and retry information
    """
    retry_after = getattr(exc, "retry_after", 60)
    detail = getattr(exc, "detail", None)
    limit_detail = str(detail) if detail else "100/minute"

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded: {limit_detail}",
            "retry_after": retry_after,
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": limit_detail,
        },
    )
