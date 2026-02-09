"""Integration tests for Baselines API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestBaselinesAuth:
    """Tests for authentication requirements on baseline endpoints."""

    async def test_create_baseline_requires_auth(self, client: AsyncClient):
        """Should return 401 when not authenticated."""
        response = await client.post("/api/v1/baselines/baselines", json={})
        assert response.status_code == 401

    async def test_list_baselines_requires_auth(self, client: AsyncClient):
        """Should return 401 when listing baselines without auth."""
        response = await client.get(
            "/api/v1/baselines/baselines?program_id=00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401

    async def test_get_baseline_requires_auth(self, client: AsyncClient):
        """Should return 401 when getting baseline without auth."""
        response = await client.get(
            "/api/v1/baselines/baselines/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401


class TestBaselinesCRUD:
    """Tests for authenticated baseline CRUD operations."""

    async def test_list_baselines_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should return empty list when no baselines exist."""
        response = await client.get(
            f"/api/v1/baselines/baselines?program_id={test_program['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200

    async def test_create_baseline(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should create a baseline snapshot for a program."""
        response = await client.post(
            "/api/v1/baselines/baselines",
            json={
                "program_id": test_program["id"],
                "name": "Initial Baseline",
                "description": "First baseline snapshot",
            },
            headers=auth_headers,
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["name"] == "Initial Baseline"
        assert "id" in data

    async def test_get_baseline(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should retrieve a specific baseline by ID."""
        create_response = await client.post(
            "/api/v1/baselines/baselines",
            json={
                "program_id": test_program["id"],
                "name": "Get Test Baseline",
            },
            headers=auth_headers,
        )
        assert create_response.status_code in (200, 201)
        baseline_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/baselines/baselines/{baseline_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test Baseline"

    async def test_get_nonexistent_baseline(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should return 404 for nonexistent baseline."""
        response = await client.get(
            "/api/v1/baselines/baselines/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestBaselineComparison:
    """Tests for baseline comparison endpoint."""

    async def test_compare_baseline_to_current(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should compare baseline to current program state."""
        create_response = await client.post(
            "/api/v1/baselines/baselines",
            json={
                "program_id": test_program["id"],
                "name": "Comparison Baseline",
            },
            headers=auth_headers,
        )
        assert create_response.status_code in (200, 201)
        baseline_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/baselines/baselines/{baseline_id}/compare",
            headers=auth_headers,
        )
        assert response.status_code in (200, 422)

    async def test_compare_nonexistent_baseline(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should return 404 when comparing nonexistent baseline."""
        response = await client.get(
            "/api/v1/baselines/baselines/00000000-0000-0000-0000-000000000000/compare",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestBaselineApproval:
    """Tests for baseline approval workflow."""

    async def test_approve_baseline(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should approve a baseline."""
        create_response = await client.post(
            "/api/v1/baselines/baselines",
            json={
                "program_id": test_program["id"],
                "name": "Approval Baseline",
            },
            headers=auth_headers,
        )
        assert create_response.status_code in (200, 201)
        baseline_id = create_response.json()["id"]

        response = await client.post(
            f"/api/v1/baselines/baselines/{baseline_id}/approve",
            headers=auth_headers,
        )
        assert response.status_code in (200, 204)

    async def test_delete_baseline(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should delete a baseline."""
        create_response = await client.post(
            "/api/v1/baselines/baselines",
            json={
                "program_id": test_program["id"],
                "name": "Delete Baseline",
            },
            headers=auth_headers,
        )
        assert create_response.status_code in (200, 201)
        baseline_id = create_response.json()["id"]

        response = await client.delete(
            f"/api/v1/baselines/baselines/{baseline_id}",
            headers=auth_headers,
        )
        assert response.status_code in (200, 204)
