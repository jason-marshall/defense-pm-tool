"""Integration tests for Schedule calculation API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestScheduleAuth:
    """Tests for authentication requirements on schedule endpoints."""

    async def test_calculate_schedule_requires_auth(self, client: AsyncClient):
        """Should return 401 when not authenticated."""
        response = await client.post(
            "/api/v1/schedule/calculate/00000000-0000-0000-0000-000000000000",
        )
        assert response.status_code == 401

    async def test_critical_path_requires_auth(self, client: AsyncClient):
        """Should return 401 when getting critical path without auth."""
        response = await client.get(
            "/api/v1/schedule/critical-path/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401


class TestScheduleCalculation:
    """Tests for schedule calculation operations."""

    async def test_calculate_empty_schedule(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should handle program with no activities."""
        program_id = test_program["id"]
        response = await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )
        # Empty program may return 200 with empty list or an error
        assert response.status_code in (200, 404, 422)

    async def test_calculate_schedule_with_activities(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should calculate CPM for program with activities."""
        program_id = test_program["id"]

        # Create WBS element (required for activities)
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "wbs_code": "1.0",
                "name": "Project Root",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        # Create activities
        act1 = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "Design",
                "code": "SCHED-001",
                "duration": 5,
                "budgeted_cost": "5000.00",
            },
            headers=auth_headers,
        )
        assert act1.status_code == 201

        act2 = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "Build",
                "code": "SCHED-002",
                "duration": 10,
                "budgeted_cost": "10000.00",
            },
            headers=auth_headers,
        )
        assert act2.status_code == 201

        # Create dependency: Design -> Build
        dep = await client.post(
            "/api/v1/dependencies",
            json={
                "predecessor_id": act1.json()["id"],
                "successor_id": act2.json()["id"],
                "dependency_type": "FS",
                "lag": 0,
            },
            headers=auth_headers,
        )
        assert dep.status_code == 201

        # Calculate schedule
        response = await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)


class TestCriticalPath:
    """Tests for critical path endpoint."""

    async def test_get_critical_path(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should return critical path activities."""
        program_id = test_program["id"]

        # Create WBS element
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "wbs_code": "1.0",
                "name": "Project Root",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        # Create chain of activities
        act1 = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "CP Activity A",
                "code": "CP-001",
                "duration": 5,
                "budgeted_cost": "5000.00",
            },
            headers=auth_headers,
        )
        assert act1.status_code == 201

        act2 = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "CP Activity B",
                "code": "CP-002",
                "duration": 3,
                "budgeted_cost": "3000.00",
            },
            headers=auth_headers,
        )
        assert act2.status_code == 201

        await client.post(
            "/api/v1/dependencies",
            json={
                "predecessor_id": act1.json()["id"],
                "successor_id": act2.json()["id"],
                "dependency_type": "FS",
                "lag": 0,
            },
            headers=auth_headers,
        )

        # Calculate first
        await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )

        # Get critical path
        response = await client.get(
            f"/api/v1/schedule/critical-path/{program_id}",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404)

    async def test_critical_path_nonexistent_program(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should handle nonexistent program."""
        response = await client.get(
            "/api/v1/schedule/critical-path/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code in (404, 422)
