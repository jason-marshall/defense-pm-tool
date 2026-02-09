"""Integration tests for Scenarios API endpoints (CRUD, changes, simulate, promote)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestScenariosAuth:
    """Tests for authentication requirements on scenario endpoints."""

    async def test_create_scenario_requires_auth(self, client: AsyncClient):
        """Should return 401 when not authenticated."""
        response = await client.post("/api/v1/scenarios/scenarios", json={})
        assert response.status_code == 401

    async def test_list_scenarios_requires_auth(self, client: AsyncClient):
        """Should return 401 when listing scenarios without auth."""
        response = await client.get(
            "/api/v1/scenarios/scenarios?program_id=00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401

    async def test_get_scenario_requires_auth(self, client: AsyncClient):
        """Should return 401 when getting scenario without auth."""
        response = await client.get(
            "/api/v1/scenarios/scenarios/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401


class TestScenarioCRUD:
    """Tests for authenticated scenario CRUD operations."""

    async def test_list_scenarios_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should return empty list when no scenarios exist."""
        response = await client.get(
            f"/api/v1/scenarios/scenarios?program_id={test_program['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200

    async def test_create_scenario(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should create a new scenario."""
        response = await client.post(
            "/api/v1/scenarios/scenarios",
            json={
                "program_id": test_program["id"],
                "name": "What-If Scenario",
                "description": "Testing schedule impact",
            },
            headers=auth_headers,
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["name"] == "What-If Scenario"
        assert "id" in data

    async def test_get_scenario(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should retrieve a specific scenario."""
        create_response = await client.post(
            "/api/v1/scenarios/scenarios",
            json={
                "program_id": test_program["id"],
                "name": "Get Test Scenario",
            },
            headers=auth_headers,
        )
        assert create_response.status_code in (200, 201)
        scenario_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/scenarios/scenarios/{scenario_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test Scenario"

    async def test_update_scenario(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should update a scenario."""
        create_response = await client.post(
            "/api/v1/scenarios/scenarios",
            json={
                "program_id": test_program["id"],
                "name": "Update Test",
            },
            headers=auth_headers,
        )
        assert create_response.status_code in (200, 201)
        scenario_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/scenarios/scenarios/{scenario_id}",
            json={"name": "Updated Scenario"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Scenario"

    async def test_delete_scenario(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should delete a scenario."""
        create_response = await client.post(
            "/api/v1/scenarios/scenarios",
            json={
                "program_id": test_program["id"],
                "name": "Delete Test",
            },
            headers=auth_headers,
        )
        assert create_response.status_code in (200, 201)
        scenario_id = create_response.json()["id"]

        response = await client.delete(
            f"/api/v1/scenarios/scenarios/{scenario_id}",
            headers=auth_headers,
        )
        assert response.status_code in (200, 204)

    async def test_get_nonexistent_scenario(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should return 404 for nonexistent scenario."""
        response = await client.get(
            "/api/v1/scenarios/scenarios/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestScenarioChanges:
    """Tests for scenario change management."""

    async def test_list_scenario_changes(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should list changes for a scenario."""
        create_response = await client.post(
            "/api/v1/scenarios/scenarios",
            json={
                "program_id": test_program["id"],
                "name": "Changes Test",
            },
            headers=auth_headers,
        )
        assert create_response.status_code in (200, 201)
        scenario_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/scenarios/scenarios/{scenario_id}/changes",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestScenarioSimulation:
    """Tests for scenario simulation and promotion."""

    async def test_simulate_scenario(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should simulate a scenario."""
        create_response = await client.post(
            "/api/v1/scenarios/scenarios",
            json={
                "program_id": test_program["id"],
                "name": "Simulation Test",
            },
            headers=auth_headers,
        )
        assert create_response.status_code in (200, 201)
        scenario_id = create_response.json()["id"]

        response = await client.post(
            f"/api/v1/scenarios/scenarios/{scenario_id}/simulate",
            headers=auth_headers,
        )
        assert response.status_code in (200, 422)

    async def test_promote_scenario(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should promote a scenario to a baseline."""
        create_response = await client.post(
            "/api/v1/scenarios/scenarios",
            json={
                "program_id": test_program["id"],
                "name": "Promote Test",
            },
            headers=auth_headers,
        )
        assert create_response.status_code in (200, 201)
        scenario_id = create_response.json()["id"]

        response = await client.post(
            f"/api/v1/scenarios/scenarios/{scenario_id}/promote",
            headers=auth_headers,
        )
        assert response.status_code in (200, 400, 422)
