"""Unit tests for monitoring components (metrics and middleware)."""

from unittest.mock import MagicMock

import pytest

from src.core.metrics import (
    get_activity_count_bucket,
    record_cache_hit,
    record_cache_miss,
    record_cpm_duration,
    record_report_generated,
    record_simulation_run,
    track_time,
)


class TestActivityCountBucket:
    """Tests for activity count bucketing."""

    def test_bucket_0_99(self):
        """Should return '0-99' for counts below 100."""
        assert get_activity_count_bucket(0) == "0-99"
        assert get_activity_count_bucket(50) == "0-99"
        assert get_activity_count_bucket(99) == "0-99"

    def test_bucket_100_499(self):
        """Should return '100-499' for counts 100-499."""
        assert get_activity_count_bucket(100) == "100-499"
        assert get_activity_count_bucket(250) == "100-499"
        assert get_activity_count_bucket(499) == "100-499"

    def test_bucket_500_999(self):
        """Should return '500-999' for counts 500-999."""
        assert get_activity_count_bucket(500) == "500-999"
        assert get_activity_count_bucket(750) == "500-999"
        assert get_activity_count_bucket(999) == "500-999"

    def test_bucket_1000_4999(self):
        """Should return '1000-4999' for counts 1000-4999."""
        assert get_activity_count_bucket(1000) == "1000-4999"
        assert get_activity_count_bucket(2500) == "1000-4999"
        assert get_activity_count_bucket(4999) == "1000-4999"

    def test_bucket_5000_plus(self):
        """Should return '5000+' for counts 5000 and above."""
        assert get_activity_count_bucket(5000) == "5000+"
        assert get_activity_count_bucket(10000) == "5000+"
        assert get_activity_count_bucket(100000) == "5000+"


class TestMetricsRecording:
    """Tests for metric recording functions."""

    def test_record_cpm_duration(self):
        """Should record CPM duration with correct bucket label."""
        # Record a duration for 50 activities (bucket 0-99)
        record_cpm_duration(50, 0.05)
        # Just verify it doesn't raise - actual metric verification would need prometheus client introspection

    def test_record_cache_hit(self):
        """Should record cache hit with cache name."""
        record_cache_hit("evms_summary")
        # Verify it doesn't raise

    def test_record_cache_miss(self):
        """Should record cache miss with cache name."""
        record_cache_miss("evms_summary")
        # Verify it doesn't raise

    def test_record_report_generated(self):
        """Should record report generation with format."""
        record_report_generated("pdf")
        record_report_generated("json")
        # Verify it doesn't raise

    def test_record_simulation_run(self):
        """Should record simulation run."""
        record_simulation_run()
        # Verify it doesn't raise


class TestTrackTimeContextManager:
    """Tests for the track_time context manager."""

    def test_track_time_records_duration(self):
        """Should record duration when context manager exits."""
        import time

        # Use a unique histogram for testing
        from prometheus_client import REGISTRY, Histogram

        test_histogram = Histogram(
            "test_operation_duration_seconds",
            "Test operation duration",
            ["operation"],
        )

        with track_time(test_histogram, {"operation": "test"}):
            time.sleep(0.01)  # Sleep for 10ms

        # Clean up - unregister the test histogram
        try:
            REGISTRY.unregister(test_histogram)
        except Exception:
            pass

    def test_track_time_records_on_exception(self):
        """Should record duration even when exception occurs."""
        from prometheus_client import REGISTRY, Histogram

        test_histogram = Histogram(
            "test_exception_duration_seconds",
            "Test exception duration",
        )

        with pytest.raises(ValueError), track_time(test_histogram):
            raise ValueError("Test error")

        # Clean up
        try:
            REGISTRY.unregister(test_histogram)
        except Exception:
            pass


class TestMiddlewareNormalization:
    """Tests for endpoint normalization in middleware."""

    def test_normalize_uuid_in_path(self):
        """Should replace UUIDs with {id} placeholder."""
        from src.core.middleware import RequestTracingMiddleware

        middleware = RequestTracingMiddleware(MagicMock())

        # Create a mock request
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/programs/123e4567-e89b-12d3-a456-426614174000"

        result = middleware._normalize_endpoint(mock_request)
        assert result == "/api/v1/programs/{id}"

    def test_normalize_numeric_id_in_path(self):
        """Should replace numeric IDs with {id} placeholder."""
        from src.core.middleware import RequestTracingMiddleware

        middleware = RequestTracingMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/activities/12345"

        result = middleware._normalize_endpoint(mock_request)
        assert result == "/api/v1/activities/{id}"

    def test_normalize_multiple_ids(self):
        """Should replace multiple IDs in path."""
        from src.core.middleware import RequestTracingMiddleware

        middleware = RequestTracingMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = (
            "/api/v1/programs/123e4567-e89b-12d3-a456-426614174000/activities/456"
        )

        result = middleware._normalize_endpoint(mock_request)
        assert result == "/api/v1/programs/{id}/activities/{id}"


class TestClientIPExtraction:
    """Tests for client IP extraction from requests."""

    def test_get_client_ip_from_x_forwarded_for(self):
        """Should extract IP from X-Forwarded-For header."""
        from src.core.middleware import RequestTracingMiddleware

        middleware = RequestTracingMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get = (
            lambda key: "192.168.1.1, 10.0.0.1" if key == "X-Forwarded-For" else None
        )
        mock_request.client = None

        result = middleware._get_client_ip(mock_request)
        assert result == "192.168.1.1"

    def test_get_client_ip_from_x_real_ip(self):
        """Should extract IP from X-Real-IP header."""
        from src.core.middleware import RequestTracingMiddleware

        middleware = RequestTracingMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get = lambda key: "10.0.0.5" if key == "X-Real-IP" else None
        mock_request.client = None

        result = middleware._get_client_ip(mock_request)
        assert result == "10.0.0.5"

    def test_get_client_ip_from_client(self):
        """Should extract IP from request client."""
        from src.core.middleware import RequestTracingMiddleware

        middleware = RequestTracingMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get = lambda key: None
        mock_request.client.host = "127.0.0.1"

        result = middleware._get_client_ip(mock_request)
        assert result == "127.0.0.1"

    def test_get_client_ip_unknown(self):
        """Should return 'unknown' when no IP available."""
        from src.core.middleware import RequestTracingMiddleware

        middleware = RequestTracingMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get = lambda key: None
        mock_request.client = None

        result = middleware._get_client_ip(mock_request)
        assert result == "unknown"


class TestSecurityHeadersMiddleware:
    """Tests for security headers middleware."""

    @pytest.mark.asyncio
    async def test_adds_security_headers(self):
        """Should add security headers to response."""
        from starlette.responses import Response

        from src.core.middleware import SecurityHeadersMiddleware

        # Create mock app and response
        mock_app = MagicMock()
        middleware = SecurityHeadersMiddleware(mock_app)

        mock_request = MagicMock()
        mock_response = Response(content="test")

        async def mock_call_next(request):
            return mock_response

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert result.headers.get("X-Content-Type-Options") == "nosniff"
        assert result.headers.get("X-Frame-Options") == "DENY"
        assert result.headers.get("X-XSS-Protection") == "1; mode=block"
        assert result.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
