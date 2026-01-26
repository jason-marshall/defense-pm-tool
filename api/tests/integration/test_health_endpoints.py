"""Integration tests for health check endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for the health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, client: AsyncClient):
        """Should return healthy status with dependencies."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data
        assert "dependencies" in data
        assert "database" in data["dependencies"]

    @pytest.mark.asyncio
    async def test_health_check_database_status(self, client: AsyncClient):
        """Should include database health status."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()

        db_status = data["dependencies"]["database"]
        assert db_status["status"] == "healthy"
        assert "response_time_ms" in db_status

    @pytest.mark.asyncio
    async def test_liveness_probe(self, client: AsyncClient):
        """Should return alive status for liveness probe."""
        response = await client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_readiness_probe(self, client: AsyncClient):
        """Should return ready status when database is available."""
        response = await client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: AsyncClient):
        """Should return Prometheus metrics."""
        response = await client.get("/health/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

        # Verify some expected metrics are present
        content = response.text
        assert "http_requests_total" in content or "defense_pm_tool" in content

    @pytest.mark.asyncio
    async def test_health_no_auth_required(self, client: AsyncClient):
        """Should not require authentication for health endpoints."""
        # All health endpoints should work without auth headers
        endpoints = ["/health", "/health/live", "/health/ready", "/health/metrics"]

        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code in [200, 503], (
                f"Endpoint {endpoint} returned {response.status_code}"
            )


class TestSecurityHeaders:
    """Tests for security headers middleware."""

    @pytest.mark.asyncio
    async def test_security_headers_present(self, client: AsyncClient):
        """Should include security headers in responses."""
        response = await client.get("/health")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    @pytest.mark.asyncio
    async def test_security_headers_on_api_endpoints(self, client: AsyncClient, auth_headers: dict):
        """Should include security headers on API endpoints."""
        response = await client.get("/api/v1/programs", headers=auth_headers)

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"


class TestCorrelationId:
    """Tests for request tracing with correlation IDs."""

    @pytest.mark.asyncio
    async def test_correlation_id_returned(self, client: AsyncClient):
        """Should return correlation ID in response header."""
        response = await client.get("/health")

        correlation_id = response.headers.get("X-Correlation-ID")
        assert correlation_id is not None
        # UUID format validation
        assert len(correlation_id) == 36

    @pytest.mark.asyncio
    async def test_correlation_id_propagated(self, client: AsyncClient):
        """Should propagate provided correlation ID."""
        custom_id = "test-correlation-123"
        response = await client.get("/health", headers={"X-Correlation-ID": custom_id})

        assert response.headers.get("X-Correlation-ID") == custom_id
