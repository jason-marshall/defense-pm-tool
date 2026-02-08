"""Unit tests for SecurityHeadersMiddleware and RequestTracingMiddleware."""

from unittest.mock import MagicMock, patch

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.core.middleware import RequestTracingMiddleware, SecurityHeadersMiddleware


def _homepage(request: Request) -> PlainTextResponse:
    """Simple endpoint for testing middleware."""
    return PlainTextResponse("OK")


def _build_app_with_security_middleware(
    csp_enabled: bool = True,
    hsts_enabled: bool = False,
) -> Starlette:
    """Build a Starlette app with SecurityHeadersMiddleware."""
    app = Starlette(routes=[Route("/", _homepage)])
    app.add_middleware(
        SecurityHeadersMiddleware,
        csp_enabled=csp_enabled,
        hsts_enabled=hsts_enabled,
    )
    return app


def _build_app_with_tracing_middleware() -> Starlette:
    """Build a Starlette app with RequestTracingMiddleware."""
    app = Starlette(
        routes=[
            Route("/", _homepage),
            Route("/api/v1/programs/{program_id}", _homepage),
            Route("/api/v1/activities/123", _homepage),
        ]
    )
    app.add_middleware(RequestTracingMiddleware)
    return app


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    def test_security_headers_present(self):
        """Should add core security headers to every response."""
        # Arrange
        app = _build_app_with_security_middleware()
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_csp_header_content(self):
        """Should include Content-Security-Policy with correct directives."""
        # Arrange
        app = _build_app_with_security_middleware(csp_enabled=True)
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_csp_header_disabled(self):
        """Should not include CSP header when csp_enabled is False."""
        # Arrange
        app = _build_app_with_security_middleware(csp_enabled=False)
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        assert "Content-Security-Policy" not in response.headers

    def test_hsts_header_when_enabled(self):
        """Should include HSTS header when hsts_enabled is True."""
        # Arrange
        app = _build_app_with_security_middleware(hsts_enabled=True)
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts

    def test_hsts_header_not_present_when_disabled(self):
        """Should not include HSTS header when hsts_enabled is False."""
        # Arrange
        app = _build_app_with_security_middleware(hsts_enabled=False)
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        assert "Strict-Transport-Security" not in response.headers

    def test_x_content_type_options_header(self):
        """Should set X-Content-Type-Options to nosniff."""
        # Arrange
        app = _build_app_with_security_middleware()
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options_header(self):
        """Should set X-Frame-Options to DENY."""
        # Arrange
        app = _build_app_with_security_middleware()
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_referrer_policy_header(self):
        """Should set Referrer-Policy to strict-origin-when-cross-origin."""
        # Arrange
        app = _build_app_with_security_middleware()
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_x_xss_protection_header(self):
        """Should set X-XSS-Protection to '1; mode=block'."""
        # Arrange
        app = _build_app_with_security_middleware()
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        assert response.headers["X-XSS-Protection"] == "1; mode=block"


class TestRequestTracingMiddleware:
    """Tests for RequestTracingMiddleware."""

    @patch("src.core.middleware.http_requests_total")
    @patch("src.core.middleware.http_request_duration_seconds")
    def test_correlation_id_added(self, mock_duration, mock_total):
        """Should add X-Correlation-ID to response."""
        # Arrange
        app = _build_app_with_tracing_middleware()
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        assert "X-Correlation-ID" in response.headers
        # Should be a valid UUID-like string
        corr_id = response.headers["X-Correlation-ID"]
        assert len(corr_id) > 0

    @patch("src.core.middleware.http_requests_total")
    @patch("src.core.middleware.http_request_duration_seconds")
    def test_correlation_id_passed_through(self, mock_duration, mock_total):
        """Should use the provided X-Correlation-ID from the request."""
        # Arrange
        app = _build_app_with_tracing_middleware()
        client = TestClient(app)
        custom_id = "my-custom-correlation-id-12345"

        # Act
        response = client.get("/", headers={"X-Correlation-ID": custom_id})

        # Assert
        assert response.headers["X-Correlation-ID"] == custom_id

    @patch("src.core.middleware.http_requests_total")
    @patch("src.core.middleware.http_request_duration_seconds")
    @patch("src.core.middleware.logger")
    def test_request_logs_method_and_path(self, mock_logger, mock_duration, mock_total):
        """Should log request completion with method and path."""
        # Arrange
        app = _build_app_with_tracing_middleware()
        client = TestClient(app)

        # Act
        client.get("/")

        # Assert
        mock_logger.info.assert_called()
        call_kwargs = mock_logger.info.call_args
        # The log call should include method and path
        assert call_kwargs[1]["method"] == "GET"
        assert call_kwargs[1]["path"] == "/"


class TestNormalizeEndpoint:
    """Tests for RequestTracingMiddleware._normalize_endpoint()."""

    @patch("src.core.middleware.http_requests_total")
    @patch("src.core.middleware.http_request_duration_seconds")
    def test_normalize_endpoint_replaces_uuid(self, mock_duration, mock_total):
        """Should replace UUIDs in path with {id} placeholder."""
        # Arrange
        app = _build_app_with_tracing_middleware()
        middleware = RequestTracingMiddleware(app)

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/programs/550e8400-e29b-41d4-a716-446655440000"

        # Act
        result = middleware._normalize_endpoint(mock_request)

        # Assert
        assert result == "/api/v1/programs/{id}"

    @patch("src.core.middleware.http_requests_total")
    @patch("src.core.middleware.http_request_duration_seconds")
    def test_normalize_endpoint_replaces_numeric_id(self, mock_duration, mock_total):
        """Should replace numeric path segments with {id} placeholder."""
        # Arrange
        app = _build_app_with_tracing_middleware()
        middleware = RequestTracingMiddleware(app)

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/activities/12345"

        # Act
        result = middleware._normalize_endpoint(mock_request)

        # Assert
        assert result == "/api/v1/activities/{id}"

    @patch("src.core.middleware.http_requests_total")
    @patch("src.core.middleware.http_request_duration_seconds")
    def test_normalize_endpoint_preserves_non_id_segments(self, mock_duration, mock_total):
        """Should not modify non-ID path segments."""
        # Arrange
        app = _build_app_with_tracing_middleware()
        middleware = RequestTracingMiddleware(app)

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/health"

        # Act
        result = middleware._normalize_endpoint(mock_request)

        # Assert
        assert result == "/api/v1/health"


class TestGetClientIP:
    """Tests for RequestTracingMiddleware._get_client_ip()."""

    @patch("src.core.middleware.http_requests_total")
    @patch("src.core.middleware.http_request_duration_seconds")
    def test_get_client_ip_direct(self, mock_duration, mock_total):
        """Should return client host when no proxy headers present."""
        # Arrange
        app = _build_app_with_tracing_middleware()
        middleware = RequestTracingMiddleware(app)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.100"

        # Act
        result = middleware._get_client_ip(mock_request)

        # Assert
        assert result == "192.168.1.100"

    @patch("src.core.middleware.http_requests_total")
    @patch("src.core.middleware.http_request_duration_seconds")
    def test_get_client_ip_forwarded(self, mock_duration, mock_total):
        """Should return first IP from X-Forwarded-For header."""
        # Arrange
        app = _build_app_with_tracing_middleware()
        middleware = RequestTracingMiddleware(app)

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2, 10.0.0.3"}

        # Act
        result = middleware._get_client_ip(mock_request)

        # Assert
        assert result == "10.0.0.1"

    @patch("src.core.middleware.http_requests_total")
    @patch("src.core.middleware.http_request_duration_seconds")
    def test_get_client_ip_real_ip_header(self, mock_duration, mock_total):
        """Should use X-Real-IP when X-Forwarded-For is absent."""
        # Arrange
        app = _build_app_with_tracing_middleware()
        middleware = RequestTracingMiddleware(app)

        mock_request = MagicMock()
        mock_request.headers = {"X-Real-IP": "172.16.0.5"}

        # Act
        result = middleware._get_client_ip(mock_request)

        # Assert
        assert result == "172.16.0.5"

    @patch("src.core.middleware.http_requests_total")
    @patch("src.core.middleware.http_request_duration_seconds")
    def test_get_client_ip_unknown_fallback(self, mock_duration, mock_total):
        """Should return 'unknown' when no IP info is available."""
        # Arrange
        app = _build_app_with_tracing_middleware()
        middleware = RequestTracingMiddleware(app)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = None

        # Act
        result = middleware._get_client_ip(mock_request)

        # Assert
        assert result == "unknown"
