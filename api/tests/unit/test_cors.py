"""Unit tests for CORS configuration."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


class TestCORSConfiguration:
    """Tests for CORS middleware configuration."""

    @pytest.mark.asyncio
    async def test_preflight_allowed_method(self, client: AsyncClient) -> None:
        """Preflight request for allowed method should succeed."""
        response = await client.options(
            "/api/v1/programs",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert "GET" in response.headers.get("access-control-allow-methods", "")

    @pytest.mark.asyncio
    async def test_preflight_post_method(self, client: AsyncClient) -> None:
        """Preflight request for POST method should succeed."""
        response = await client.options(
            "/api/v1/programs",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        allow_methods = response.headers.get("access-control-allow-methods", "")
        assert "POST" in allow_methods

    @pytest.mark.asyncio
    async def test_preflight_allowed_header_authorization(self, client: AsyncClient) -> None:
        """Preflight request for Authorization header should be allowed."""
        response = await client.options(
            "/api/v1/programs",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        assert response.status_code == 200
        allow_headers = response.headers.get("access-control-allow-headers", "")
        assert "Authorization" in allow_headers

    @pytest.mark.asyncio
    async def test_preflight_allowed_header_content_type(self, client: AsyncClient) -> None:
        """Preflight request for Content-Type header should be allowed."""
        response = await client.options(
            "/api/v1/programs",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200
        allow_headers = response.headers.get("access-control-allow-headers", "")
        assert "Content-Type" in allow_headers

    @pytest.mark.asyncio
    async def test_preflight_allowed_header_api_key(self, client: AsyncClient) -> None:
        """Preflight request for X-API-Key header should be allowed."""
        response = await client.options(
            "/api/v1/programs",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-API-Key",
            },
        )
        assert response.status_code == 200
        allow_headers = response.headers.get("access-control-allow-headers", "")
        assert "X-API-Key" in allow_headers

    @pytest.mark.asyncio
    async def test_preflight_allowed_header_correlation_id(self, client: AsyncClient) -> None:
        """Preflight request for X-Correlation-ID header should be allowed."""
        response = await client.options(
            "/api/v1/programs",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Correlation-ID",
            },
        )
        assert response.status_code == 200
        allow_headers = response.headers.get("access-control-allow-headers", "")
        assert "X-Correlation-ID" in allow_headers

    @pytest.mark.asyncio
    async def test_cors_disallowed_origin(self, client: AsyncClient) -> None:
        """Request from disallowed origin should not include CORS headers."""
        response = await client.options(
            "/api/v1/programs",
            headers={
                "Origin": "http://evil-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Disallowed origin should not get access-control-allow-origin
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin is None or "evil-site.com" not in allow_origin

    @pytest.mark.asyncio
    async def test_cors_credentials_allowed(self, client: AsyncClient) -> None:
        """CORS should allow credentials for valid origins."""
        response = await client.options(
            "/api/v1/programs",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-credentials") == "true"
