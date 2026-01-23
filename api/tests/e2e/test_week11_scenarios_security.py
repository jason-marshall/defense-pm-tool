"""End-to-end tests for Week 11: Scenario Promotion & Security.

This module validates the complete Week 11 implementation:
1. Scenario Promotion Workflow
2. Apply Scenario Changes
3. Input Validation (Security)
4. Rate Limiting
5. OpenAPI Documentation

Week 11 Focus Areas:
1. Scenario Promotion Workflow - complete E2E test
2. Security Hardening - XSS, SQL injection prevention
3. Rate Limiting - verify headers and configuration
4. API Documentation - OpenAPI completeness
"""

from datetime import date
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_week11_program_data() -> dict[str, Any]:
    """Sample program for Week 11 testing."""
    return {
        "name": "Week 11 Test Program",
        "code": f"W11-{uuid4().hex[:6].upper()}",
        "description": "Test program for Week 11 E2E tests",
        "start_date": str(date.today()),
        "end_date": str(date.today().replace(year=date.today().year + 1)),
        "budget_at_completion": "1000000.00",
    }


# =============================================================================
# Scenario Promotion Workflow Tests
# =============================================================================


class TestScenarioPromotionWorkflow:
    """E2E tests for scenario promotion to baseline."""

    @pytest.mark.asyncio
    async def test_scenario_list_endpoint_exists(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_week11_program_data: dict[str, Any],
    ) -> None:
        """Verify scenario list endpoint is accessible."""
        # Create program first
        program_response = await client.post(
            "/api/v1/programs",
            json=sample_week11_program_data,
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # List scenarios (should work even if empty)
        # Note: Path is /api/v1/scenarios/scenarios due to doubled prefix
        response = await client.get(
            f"/api/v1/scenarios/scenarios?program_id={program_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_scenario_creation_requires_auth(
        self,
        client: AsyncClient,
        sample_week11_program_data: dict[str, Any],
    ) -> None:
        """Scenario creation should require authentication."""
        response = await client.post(
            "/api/v1/scenarios/scenarios",
            json={
                "program_id": str(uuid4()),
                "name": "Unauthorized Test",
            },
        )
        assert response.status_code == 401


# =============================================================================
# Security Hardening Tests
# =============================================================================


class TestSecurityHardening:
    """E2E tests for security hardening features."""

    @pytest.mark.asyncio
    async def test_xss_prevention_in_program_name(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should sanitize or reject XSS attempts in program name."""
        response = await client.post(
            "/api/v1/programs",
            json={
                "name": "<script>alert('xss')</script>Test Program",
                "code": "XSS-TEST",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )

        if response.status_code == 201:
            # If accepted, script tags should be sanitized (stripped)
            name = response.json()["name"]
            # Script tags should be removed
            assert "<script>" not in name
            assert "</script>" not in name
        else:
            # Or rejected entirely
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should handle SQL injection attempts safely."""
        response = await client.post(
            "/api/v1/programs",
            json={
                "name": "'; DROP TABLE programs; --",
                "code": "SQL-INJ",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )

        # Should either accept (SQLAlchemy parameterizes) or reject
        assert response.status_code in [201, 400, 422]

        if response.status_code == 201:
            # Verify the table still exists by listing programs
            list_response = await client.get(
                "/api/v1/programs",
                headers=auth_headers,
            )
            assert list_response.status_code == 200

    @pytest.mark.asyncio
    async def test_max_length_enforcement(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should enforce maximum field lengths."""
        response = await client.post(
            "/api/v1/programs",
            json={
                "name": "x" * 1000,  # Exceeds 255 character limit
                "code": "LEN-TEST",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_special_characters_handled(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should handle special characters safely."""
        response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Test & Program with 'special' chars",
                "code": "SPEC-CHAR",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )

        # Should accept but safely handle
        assert response.status_code == 201
        assert "Test" in response.json()["name"]


# =============================================================================
# Rate Limiting Tests
# =============================================================================


class TestRateLimiting:
    """E2E tests for API rate limiting."""

    @pytest.mark.asyncio
    async def test_health_endpoint_accessible(
        self,
        client: AsyncClient,
    ) -> None:
        """Health endpoint should always be accessible."""
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_disabled_in_tests(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Rate limiting should be disabled in test environment."""
        # Make multiple rapid requests - should not be rate limited in tests
        for _ in range(10):
            response = await client.get("/api/v1/programs", headers=auth_headers)
            # Should all succeed (not 429)
            assert response.status_code != 429


# =============================================================================
# OpenAPI Documentation Tests
# =============================================================================


class TestOpenAPIDocumentation:
    """E2E tests for OpenAPI documentation completeness."""

    @pytest.mark.asyncio
    async def test_openapi_schema_available(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return OpenAPI schema."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        assert "info" in data
        assert "components" in data

    @pytest.mark.asyncio
    async def test_openapi_has_tags(
        self,
        client: AsyncClient,
    ) -> None:
        """OpenAPI schema should have tag definitions."""
        response = await client.get("/openapi.json")
        data = response.json()

        assert "tags" in data
        tag_names = [tag["name"] for tag in data["tags"]]

        # Check expected tags
        expected_tags = ["Authentication", "Programs", "Activities"]
        for tag in expected_tags:
            assert tag in tag_names, f"Expected tag '{tag}' not found"

    @pytest.mark.asyncio
    async def test_all_endpoints_have_responses(
        self,
        client: AsyncClient,
    ) -> None:
        """All endpoints should have at least one response defined."""
        response = await client.get("/openapi.json")
        data = response.json()
        paths = data.get("paths", {})

        methods_to_check = ["get", "post", "put", "patch", "delete"]

        for path, methods in paths.items():
            for method, details in methods.items():
                if method in methods_to_check:
                    assert "responses" in details, f"{method.upper()} {path} missing responses"
                    assert len(details["responses"]) > 0, (
                        f"{method.upper()} {path} has no responses"
                    )

    @pytest.mark.asyncio
    async def test_scenario_endpoints_documented(
        self,
        client: AsyncClient,
    ) -> None:
        """Scenario endpoints should be documented."""
        response = await client.get("/openapi.json")
        data = response.json()
        paths = data.get("paths", {})

        scenario_paths = [p for p in paths if "scenario" in p.lower()]
        assert len(scenario_paths) > 0, "Scenario endpoints should be documented"

        # Verify promote endpoint exists
        promote_paths = [p for p in scenario_paths if "promote" in p]
        assert len(promote_paths) > 0, "Promote endpoint should be documented"

    @pytest.mark.asyncio
    async def test_jira_endpoints_documented(
        self,
        client: AsyncClient,
    ) -> None:
        """Jira integration endpoints should be documented."""
        response = await client.get("/openapi.json")
        data = response.json()
        paths = data.get("paths", {})

        jira_paths = [p for p in paths if "jira" in p.lower()]
        assert len(jira_paths) > 0, "Jira endpoints should be documented"

    @pytest.mark.asyncio
    async def test_docs_ui_accessible(
        self,
        client: AsyncClient,
    ) -> None:
        """Swagger UI should be accessible."""
        response = await client.get("/docs")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_redoc_accessible(
        self,
        client: AsyncClient,
    ) -> None:
        """ReDoc should be accessible."""
        response = await client.get("/redoc")
        assert response.status_code == 200


# =============================================================================
# Week 11 Feature Verification Tests
# =============================================================================


class TestWeek11Features:
    """Tests to verify Week 11 features are available."""

    @pytest.mark.asyncio
    async def test_scenario_promote_endpoint_exists(
        self,
        client: AsyncClient,
    ) -> None:
        """Scenario promote endpoint should exist in OpenAPI."""
        response = await client.get("/openapi.json")
        data = response.json()
        paths = data.get("paths", {})

        # Look for promote endpoint
        promote_endpoints = [p for p in paths if "promote" in p]
        assert len(promote_endpoints) > 0, "Promote endpoint should exist"

    @pytest.mark.asyncio
    async def test_scenario_apply_endpoint_exists(
        self,
        client: AsyncClient,
    ) -> None:
        """Scenario apply endpoint should exist in OpenAPI."""
        response = await client.get("/openapi.json")
        data = response.json()
        paths = data.get("paths", {})

        # Look for apply endpoint
        apply_endpoints = [p for p in paths if "apply" in p]
        assert len(apply_endpoints) > 0, "Apply endpoint should exist"

    @pytest.mark.asyncio
    async def test_scenario_simulate_endpoint_exists(
        self,
        client: AsyncClient,
    ) -> None:
        """Scenario simulate endpoint should exist in OpenAPI."""
        response = await client.get("/openapi.json")
        data = response.json()
        paths = data.get("paths", {})

        # Look for simulate endpoint
        simulate_endpoints = [p for p in paths if "simulate" in p]
        assert len(simulate_endpoints) > 0, "Simulate endpoint should exist"

    @pytest.mark.asyncio
    async def test_scenario_compare_endpoint_exists(
        self,
        client: AsyncClient,
    ) -> None:
        """Scenario compare endpoint should exist in OpenAPI."""
        response = await client.get("/openapi.json")
        data = response.json()
        paths = data.get("paths", {})

        # Look for compare endpoint
        compare_endpoints = [p for p in paths if "compare" in p]
        assert len(compare_endpoints) > 0, "Compare endpoint should exist"

    @pytest.mark.asyncio
    async def test_error_schemas_defined(
        self,
        client: AsyncClient,
    ) -> None:
        """Error response schemas should be defined."""
        response = await client.get("/openapi.json")
        data = response.json()
        schemas = data.get("components", {}).get("schemas", {})

        # Check for error schemas
        expected_schemas = [
            "ValidationErrorResponse",
            "AuthenticationErrorResponse",
            "AuthorizationErrorResponse",
            "NotFoundErrorResponse",
        ]
        for schema in expected_schemas:
            assert schema in schemas, f"Error schema '{schema}' should exist"
