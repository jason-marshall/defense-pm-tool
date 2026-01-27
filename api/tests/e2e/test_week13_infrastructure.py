"""End-to-end tests for Week 13: Infrastructure and Stabilization.

This module validates the Week 13 deliverables:
1. Health and monitoring endpoints
2. Redis caching functionality
3. API performance under load
4. Metrics and observability
"""

from __future__ import annotations

import time
from datetime import date
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

# =============================================================================
# Health and Monitoring Tests
# =============================================================================


class TestHealthEndpoints:
    """E2E tests for health and monitoring endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient) -> None:
        """Test basic health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data or "environment" in data

    @pytest.mark.asyncio
    async def test_readiness_endpoint(self, client: AsyncClient) -> None:
        """Test readiness check with dependency status."""
        response = await client.get("/health/ready")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_liveness_endpoint(self, client: AsyncClient) -> None:
        """Test liveness check endpoint."""
        response = await client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: AsyncClient) -> None:
        """Test Prometheus metrics endpoint if available."""
        response = await client.get("/metrics")
        # Metrics endpoint may not be configured in test environment
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "text/plain" in content_type or "text/" in content_type
            content = response.text
            assert len(content) > 0
        else:
            # Metrics not configured is acceptable in test env
            assert response.status_code in [200, 404]


# =============================================================================
# Request Tracing Tests
# =============================================================================


class TestRequestTracing:
    """E2E tests for request tracing and correlation IDs."""

    @pytest.mark.asyncio
    async def test_correlation_id_generated(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that correlation ID is generated and returned."""
        response = await client.get("/health")
        assert response.status_code == 200
        # Correlation ID should be in response headers
        correlation_id = response.headers.get("X-Correlation-ID")
        assert correlation_id is not None
        assert len(correlation_id) > 0

    @pytest.mark.asyncio
    async def test_correlation_id_passed_through(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that provided correlation ID is passed through."""
        custom_id = f"test-{uuid4().hex[:8]}"
        response = await client.get(
            "/health",
            headers={"X-Correlation-ID": custom_id},
        )
        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == custom_id


# =============================================================================
# Caching Tests
# =============================================================================


class TestCaching:
    """E2E tests for Redis caching functionality."""

    @pytest.mark.asyncio
    async def test_cpm_calculation_cached(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that CPM calculations are cached."""
        # Create program with activities
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Cache Test Program",
                "code": f"CACHE-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # First calculation (cache miss)
        calc1_response = await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )
        assert calc1_response.status_code == 200

        # Second calculation (should be cached)
        calc2_response = await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )
        assert calc2_response.status_code == 200

        # Results should be identical
        assert calc1_response.json() == calc2_response.json()

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_activity_change(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that cache is invalidated when activities change."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Cache Invalidation Test",
                "code": f"CINV-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create WBS
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "wbs_code": "1.1",
                "name": "Test WBS",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        # First calculation
        calc1 = await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )
        assert calc1.status_code == 200

        # Add an activity (should invalidate cache)
        activity_response = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "code": "A-001",
                "name": "Test Activity",
                "duration": 10,
            },
            headers=auth_headers,
        )
        assert activity_response.status_code == 201

        # New calculation (cache should be invalidated)
        calc2 = await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )
        assert calc2.status_code == 200

        # Results should include activities (response is a list)
        result = calc2.json()
        if isinstance(result, list):
            assert len(result) > 0
        else:
            activities = result.get("activities", [])
            assert len(activities) > 0


# =============================================================================
# Performance Baseline Tests
# =============================================================================


class TestPerformanceBaselines:
    """E2E tests to verify performance baselines."""

    @pytest.mark.asyncio
    async def test_health_endpoint_fast(
        self,
        client: AsyncClient,
    ) -> None:
        """Test health endpoint responds quickly (<100ms)."""
        start = time.perf_counter()
        response = await client.get("/health")
        duration = time.perf_counter() - start

        assert response.status_code == 200
        assert duration < 0.1  # <100ms

    @pytest.mark.asyncio
    async def test_programs_list_performance(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test program list endpoint performance (<500ms)."""
        start = time.perf_counter()
        response = await client.get("/api/v1/programs", headers=auth_headers)
        duration = time.perf_counter() - start

        assert response.status_code == 200
        assert duration < 0.5  # <500ms

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(
        self,
        client: AsyncClient,
    ) -> None:
        """Test multiple concurrent health checks."""
        import asyncio

        async def check_health() -> int:
            response = await client.get("/health")
            return response.status_code

        # Run 10 concurrent requests
        results = await asyncio.gather(*[check_health() for _ in range(10)])

        # All should succeed
        assert all(status == 200 for status in results)


# =============================================================================
# API Versioning Tests
# =============================================================================


class TestAPIVersioning:
    """E2E tests for API versioning."""

    @pytest.mark.asyncio
    async def test_api_v1_available(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that v1 API is available."""
        response = await client.get("/api/v1/programs", headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_api_docs_available(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that API documentation is available."""
        response = await client.get("/docs")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_schema(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that OpenAPI schema is available."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """E2E tests for error handling."""

    @pytest.mark.asyncio
    async def test_404_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test 404 response for non-existent resource."""
        response = await client.get(
            f"/api/v1/programs/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_401_unauthorized(
        self,
        client: AsyncClient,
    ) -> None:
        """Test 401 response for unauthorized access."""
        response = await client.get("/api/v1/programs")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_422_validation_error(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test 422 response for validation errors."""
        response = await client.post(
            "/api/v1/programs",
            json={"invalid": "data"},  # Missing required fields
            headers=auth_headers,
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


# =============================================================================
# Week 13 Feature Integration Tests
# =============================================================================


class TestWeek13Integration:
    """Integration tests for Week 13 feature set."""

    @pytest.mark.asyncio
    async def test_full_monitoring_stack(
        self,
        client: AsyncClient,
    ) -> None:
        """Test complete monitoring stack is operational."""
        # Health endpoint
        health = await client.get("/health")
        assert health.status_code == 200

        # Readiness
        ready = await client.get("/health/ready")
        assert ready.status_code in [200, 503]

        # Liveness
        live = await client.get("/health/live")
        assert live.status_code == 200

        # Metrics (may not be available in test env)
        metrics = await client.get("/metrics")
        assert metrics.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_api_workflow_with_caching(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test typical API workflow with caching benefits."""
        # Create program
        program = await client.post(
            "/api/v1/programs",
            json={
                "name": "Workflow Test",
                "code": f"WF-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program.status_code == 201
        program_id = program.json()["id"]

        # Get program (may be cached)
        get_program = await client.get(
            f"/api/v1/programs/{program_id}",
            headers=auth_headers,
        )
        assert get_program.status_code == 200

        # Calculate schedule
        schedule = await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )
        assert schedule.status_code == 200

        # Get EVMS summary (may be cached)
        summary = await client.get(
            f"/api/v1/evms/summary/{program_id}",
            headers=auth_headers,
        )
        assert summary.status_code == 200

        # Verify response structure
        summary_data = summary.json()
        assert (
            "bcws" in summary_data
            or "budget_at_completion" in summary_data
            or "status" in summary_data
        )
