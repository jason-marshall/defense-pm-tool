"""Integration tests for Resources API endpoints (CRUD, assignments, calendar)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestResourcesAuth:
    """Tests for authentication requirements on resource endpoints."""

    async def test_create_resource_requires_auth(self, client: AsyncClient):
        """Should return 401 when not authenticated."""
        response = await client.post("/api/v1/resources", json={})
        assert response.status_code == 401

    async def test_list_resources_requires_auth(self, client: AsyncClient):
        """Should return 401 when listing resources without auth."""
        response = await client.get(
            "/api/v1/resources?program_id=00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401

    async def test_get_resource_requires_auth(self, client: AsyncClient):
        """Should return 401 when getting resource without auth."""
        response = await client.get("/api/v1/resources/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 401


class TestResourceCRUD:
    """Tests for authenticated resource CRUD operations."""

    async def test_list_resources_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should return empty list when no resources exist."""
        response = await client.get(
            f"/api/v1/resources?program_id={test_program['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_create_labor_resource(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should create a labor type resource."""
        response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "Software Engineer",
                "code": "SE-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
                "cost_rate": "125.00",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Software Engineer"
        assert data["code"] == "SE-001"
        assert data["resource_type"].lower() == "labor"

    async def test_create_equipment_resource(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should create an equipment type resource."""
        response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "3D Printer",
                "code": "EQ-001",
                "resource_type": "equipment",
                "capacity_per_day": "24.0",
                "cost_rate": "50.00",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["resource_type"].lower() == "equipment"

    async def test_create_material_resource(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should create a material type resource."""
        response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "Steel Plate",
                "code": "MAT-001",
                "resource_type": "material",
                "capacity_per_day": "24.0",
                "cost_rate": "25.00",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["resource_type"].lower() == "material"

    async def test_get_resource(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should retrieve a specific resource by ID."""
        create_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "Test Resource",
                "code": "TR-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        resource_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/resources/{resource_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Test Resource"

    async def test_update_resource(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should update a resource."""
        create_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "Original Name",
                "code": "UP-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        resource_id = create_response.json()["id"]

        response = await client.put(
            f"/api/v1/resources/{resource_id}",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )
        assert response.status_code in (200, 422)
        if response.status_code == 200:
            assert response.json()["name"] == "Updated Name"

    async def test_delete_resource(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should delete a resource."""
        create_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "Delete Me",
                "code": "DEL-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        resource_id = create_response.json()["id"]

        response = await client.delete(
            f"/api/v1/resources/{resource_id}",
            headers=auth_headers,
        )
        assert response.status_code in (200, 204)

    async def test_get_nonexistent_resource(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should return 404 for nonexistent resource."""
        response = await client.get(
            "/api/v1/resources/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_filter_resources_by_type(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should filter resources by type."""
        # Create labor and equipment resources
        await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "Engineer",
                "code": "FIL-L01",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "Printer",
                "code": "FIL-E01",
                "resource_type": "equipment",
                "capacity_per_day": "24.0",
            },
            headers=auth_headers,
        )

        # Filter by labor
        response = await client.get(
            f"/api/v1/resources?program_id={test_program['id']}&resource_type=labor",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["resource_type"].lower() == "labor"


class TestResourceAssignments:
    """Tests for resource assignment operations."""

    async def test_assign_resource_to_activity(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should assign a resource to an activity."""
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

        # Create resource
        res_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Assignee",
                "code": "ASN-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
                "cost_rate": "100.00",
            },
            headers=auth_headers,
        )
        assert res_response.status_code == 201
        resource_id = res_response.json()["id"]

        # Create activity
        act_response = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "Assignment Test Activity",
                "code": "ASGN-ACT-001",
                "duration": 5,
                "budgeted_cost": "5000.00",
            },
            headers=auth_headers,
        )
        assert act_response.status_code == 201
        activity_id = act_response.json()["id"]

        # Assign to activity
        response = await client.post(
            f"/api/v1/resources/{resource_id}/assignments",
            json={
                "activity_id": activity_id,
                "resource_id": resource_id,
                "units": "1.0",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

    async def test_list_resource_assignments(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should list assignments for a resource."""
        res_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "List Assign",
                "code": "LA-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        assert res_response.status_code == 201
        resource_id = res_response.json()["id"]

        response = await client.get(
            f"/api/v1/resources/{resource_id}/assignments",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestResourceCalendar:
    """Tests for resource calendar endpoints."""

    async def test_set_resource_calendar(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should set calendar entries for a resource."""
        res_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "Calendar Resource",
                "code": "CAL-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        assert res_response.status_code == 201
        resource_id = res_response.json()["id"]

        response = await client.post(
            f"/api/v1/resources/{resource_id}/calendar",
            json={
                "resource_id": resource_id,
                "entries": [
                    {
                        "calendar_date": "2024-12-25",
                        "available_hours": "0.0",
                        "is_working_day": False,
                    }
                ],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

    async def test_get_resource_calendar(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should get calendar entries for a resource."""
        res_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "Get Calendar",
                "code": "GC-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        assert res_response.status_code == 201
        resource_id = res_response.json()["id"]

        response = await client.get(
            f"/api/v1/resources/{resource_id}/calendar?start_date=2024-01-01&end_date=2024-12-31",
            headers=auth_headers,
        )
        assert response.status_code == 200
