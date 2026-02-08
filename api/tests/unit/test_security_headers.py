"""Unit tests for security headers middleware."""

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


class TestSecurityHeaders:
    """Tests for security headers on responses."""

    @pytest.mark.asyncio
    async def test_x_content_type_options(self, client: AsyncClient) -> None:
        """Response should include X-Content-Type-Options: nosniff."""
        response = await client.get("/health")
        assert response.headers.get("x-content-type-options") == "nosniff"

    @pytest.mark.asyncio
    async def test_x_frame_options(self, client: AsyncClient) -> None:
        """Response should include X-Frame-Options: DENY."""
        response = await client.get("/health")
        assert response.headers.get("x-frame-options") == "DENY"

    @pytest.mark.asyncio
    async def test_x_xss_protection(self, client: AsyncClient) -> None:
        """Response should include X-XSS-Protection header."""
        response = await client.get("/health")
        assert response.headers.get("x-xss-protection") == "1; mode=block"

    @pytest.mark.asyncio
    async def test_referrer_policy(self, client: AsyncClient) -> None:
        """Response should include Referrer-Policy header."""
        response = await client.get("/health")
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    @pytest.mark.asyncio
    async def test_csp_header_present(self, client: AsyncClient) -> None:
        """Response should include Content-Security-Policy header (CSP enabled by default)."""
        response = await client.get("/health")
        csp = response.headers.get("content-security-policy")
        assert csp is not None
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "base-uri 'self'" in csp

    @pytest.mark.asyncio
    async def test_hsts_header_absent_by_default(self, client: AsyncClient) -> None:
        """Response should NOT include HSTS header by default (HSTS_ENABLED=False)."""
        response = await client.get("/health")
        assert response.headers.get("strict-transport-security") is None


class TestSecurityHeadersMiddlewareConfig:
    """Tests for SecurityHeadersMiddleware configuration options."""

    @pytest.mark.asyncio
    async def test_csp_disabled(self) -> None:
        """CSP header should not be present when CSP is disabled."""
        from fastapi import FastAPI

        from src.core.middleware import SecurityHeadersMiddleware

        test_app = FastAPI()
        test_app.add_middleware(SecurityHeadersMiddleware, csp_enabled=False, hsts_enabled=False)

        @test_app.get("/test")
        async def test_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            response = await ac.get("/test")
            assert response.headers.get("content-security-policy") is None
            # Other security headers should still be present
            assert response.headers.get("x-content-type-options") == "nosniff"

    @pytest.mark.asyncio
    async def test_hsts_enabled(self) -> None:
        """HSTS header should be present when enabled."""
        from fastapi import FastAPI

        from src.core.middleware import SecurityHeadersMiddleware

        test_app = FastAPI()
        test_app.add_middleware(SecurityHeadersMiddleware, csp_enabled=False, hsts_enabled=True)

        @test_app.get("/test")
        async def test_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            response = await ac.get("/test")
            hsts = response.headers.get("strict-transport-security")
            assert hsts is not None
            assert "max-age=31536000" in hsts
            assert "includeSubDomains" in hsts
