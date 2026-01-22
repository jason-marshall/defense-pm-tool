"""Tests for rate limiting functionality."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

from src.core.rate_limit import (
    RATE_LIMIT_AUTH,
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_REPORTS,
    RATE_LIMIT_SYNC,
    RATE_LIMIT_WEBHOOK,
    get_client_ip,
    rate_limit_exceeded_handler,
)

# =============================================================================
# Test: get_client_ip
# =============================================================================


class TestGetClientIp:
    """Tests for client IP extraction."""

    def test_uses_forwarded_header_single_ip(self):
        """Should use X-Forwarded-For when present with single IP."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "1.2.3.4"}

        result = get_client_ip(request)
        assert result == "1.2.3.4"

    def test_uses_forwarded_header_multiple_ips(self):
        """Should use first IP from X-Forwarded-For when multiple present."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 9.10.11.12"}

        result = get_client_ip(request)
        assert result == "1.2.3.4"

    def test_strips_whitespace_from_forwarded_ip(self):
        """Should strip whitespace from forwarded IP."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "  1.2.3.4  , 5.6.7.8"}

        result = get_client_ip(request)
        assert result == "1.2.3.4"

    def test_falls_back_to_remote_address(self):
        """Should fall back to remote address when no forwarded header."""
        request = MagicMock(spec=Request)
        request.headers = {}

        with patch("src.core.rate_limit.get_remote_address") as mock_get:
            mock_get.return_value = "10.0.0.1"
            result = get_client_ip(request)
            assert result == "10.0.0.1"
            mock_get.assert_called_once_with(request)

    def test_handles_empty_forwarded_header(self):
        """Should fall back when forwarded header is empty."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": ""}

        with patch("src.core.rate_limit.get_remote_address") as mock_get:
            mock_get.return_value = "10.0.0.1"
            result = get_client_ip(request)
            assert result == "10.0.0.1"


# =============================================================================
# Test: rate_limit_exceeded_handler
# =============================================================================


class TestRateLimitExceededHandler:
    """Tests for rate limit exceeded response."""

    def test_returns_429_status(self):
        """Should return 429 status code."""
        request = MagicMock(spec=Request)
        exc = MagicMock(spec=RateLimitExceeded)
        exc.detail = "100/minute"
        exc.retry_after = 60

        response = rate_limit_exceeded_handler(request, exc)

        assert response.status_code == 429

    def test_includes_retry_after_header(self):
        """Should include Retry-After header."""
        request = MagicMock(spec=Request)
        exc = MagicMock(spec=RateLimitExceeded)
        exc.detail = "100/minute"
        exc.retry_after = 30

        response = rate_limit_exceeded_handler(request, exc)

        assert response.headers.get("Retry-After") == "30"

    def test_includes_rate_limit_header(self):
        """Should include X-RateLimit-Limit header."""
        request = MagicMock(spec=Request)
        exc = MagicMock(spec=RateLimitExceeded)
        exc.detail = "10/minute"
        exc.retry_after = 60

        response = rate_limit_exceeded_handler(request, exc)

        assert response.headers.get("X-RateLimit-Limit") == "10/minute"

    def test_response_body_contains_error_info(self):
        """Should include error information in response body."""
        request = MagicMock(spec=Request)
        exc = MagicMock(spec=RateLimitExceeded)
        exc.detail = "5/minute"
        exc.retry_after = 45

        response = rate_limit_exceeded_handler(request, exc)

        # Decode response body
        import json

        body = json.loads(response.body.decode())

        assert body["error"] == "rate_limit_exceeded"
        assert "5/minute" in body["message"]
        assert body["retry_after"] == 45

    def test_handles_missing_retry_after(self):
        """Should default retry_after to 60 if not present."""
        request = MagicMock(spec=Request)
        exc = MagicMock(spec=RateLimitExceeded)
        exc.detail = "100/minute"
        # Simulate missing retry_after attribute
        del exc.retry_after

        response = rate_limit_exceeded_handler(request, exc)

        assert response.headers.get("Retry-After") == "60"

    def test_handles_none_detail(self):
        """Should default to 100/minute if detail is None."""
        request = MagicMock(spec=Request)
        exc = MagicMock(spec=RateLimitExceeded)
        exc.detail = None
        exc.retry_after = 60

        response = rate_limit_exceeded_handler(request, exc)

        assert response.headers.get("X-RateLimit-Limit") == "100/minute"


# =============================================================================
# Test: Rate Limit Constants
# =============================================================================


class TestRateLimitConstants:
    """Tests for rate limit constants."""

    def test_default_limit(self):
        """Default limit should be 100/minute."""
        assert RATE_LIMIT_DEFAULT == "100/minute"

    def test_auth_limit_stricter_than_default(self):
        """Auth limit should be stricter than default."""
        assert RATE_LIMIT_AUTH == "10/minute"
        # Parse and compare
        auth_rate = int(RATE_LIMIT_AUTH.split("/")[0])
        default_rate = int(RATE_LIMIT_DEFAULT.split("/")[0])
        assert auth_rate < default_rate

    def test_reports_limit_is_strictest(self):
        """Reports limit should be strictest for resource protection."""
        assert RATE_LIMIT_REPORTS == "5/minute"
        # Parse and compare
        reports_rate = int(RATE_LIMIT_REPORTS.split("/")[0])
        auth_rate = int(RATE_LIMIT_AUTH.split("/")[0])
        assert reports_rate < auth_rate

    def test_sync_limit_for_external_api(self):
        """Sync limit should be moderate for external API calls."""
        assert RATE_LIMIT_SYNC == "20/minute"

    def test_webhook_limit_higher_for_events(self):
        """Webhook limit should be higher to handle bursts."""
        assert RATE_LIMIT_WEBHOOK == "60/minute"
        # Parse and compare
        webhook_rate = int(RATE_LIMIT_WEBHOOK.split("/")[0])
        sync_rate = int(RATE_LIMIT_SYNC.split("/")[0])
        assert webhook_rate > sync_rate

    def test_all_limits_use_minute_unit(self):
        """All limits should use per-minute rate."""
        limits = [
            RATE_LIMIT_DEFAULT,
            RATE_LIMIT_AUTH,
            RATE_LIMIT_REPORTS,
            RATE_LIMIT_SYNC,
            RATE_LIMIT_WEBHOOK,
        ]
        for limit in limits:
            assert limit.endswith("/minute"), f"{limit} should end with /minute"

    def test_all_limits_are_positive(self):
        """All limits should have positive rate values."""
        limits = [
            RATE_LIMIT_DEFAULT,
            RATE_LIMIT_AUTH,
            RATE_LIMIT_REPORTS,
            RATE_LIMIT_SYNC,
            RATE_LIMIT_WEBHOOK,
        ]
        for limit in limits:
            rate = int(limit.split("/")[0])
            assert rate > 0, f"{limit} should have positive rate"


# =============================================================================
# Test: Limiter Instance
# =============================================================================


class TestLimiterInstance:
    """Tests for limiter instance configuration."""

    def test_limiter_exists(self):
        """Limiter instance should be importable."""
        from src.core.rate_limit import limiter

        assert limiter is not None

    def test_limiter_has_default_limits(self):
        """Limiter should have default limits configured."""
        from src.core.rate_limit import limiter

        assert limiter._default_limits is not None

    def test_limiter_uses_custom_key_func(self):
        """Limiter should use custom key function."""
        from src.core.rate_limit import limiter

        assert limiter._key_func is not None
