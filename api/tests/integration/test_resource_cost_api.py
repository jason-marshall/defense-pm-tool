"""Integration tests for Resource Cost and Material Tracking API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def cost_context(client: AsyncClient) -> dict:
    """Create user, program, WBS, activities, and resources for cost testing."""
    email = f"cost_{uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "TestPass123!",
            "full_name": "Cost Tester",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TestPass123!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create program
    prog_resp = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={
            "name": "Cost Test Program",
            "code": f"CT-{uuid4().hex[:6]}",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "budget_at_completion": "500000.00",
        },
    )
    assert prog_resp.status_code == 201
    program = prog_resp.json()
    program_id = program["id"]

    # Create WBS
    wbs_resp = await client.post(
        "/api/v1/wbs",
        json={"program_id": program_id, "name": "Cost WP", "wbs_code": "1.1"},
        headers=headers,
    )
    assert wbs_resp.status_code == 201
    wbs = wbs_resp.json()

    # Create activity
    act_resp = await client.post(
        "/api/v1/activities",
        json={
            "program_id": program_id,
            "wbs_id": wbs["id"],
            "name": "Costed Activity",
            "code": "COST-001",
            "duration": 20,
            "budgeted_cost": "10000.00",
        },
        headers=headers,
    )
    assert act_resp.status_code == 201
    activity = act_resp.json()

    # Create labor resource
    labor_resp = await client.post(
        "/api/v1/resources",
        json={
            "program_id": program_id,
            "name": "Engineer",
            "code": "ENG-001",
            "resource_type": "labor",
            "cost_rate": "100.00",
            "capacity_per_day": "8.00",
        },
        headers=headers,
    )
    assert labor_resp.status_code == 201
    labor = labor_resp.json()

    # Create material resource
    mat_resp = await client.post(
        "/api/v1/resources",
        json={
            "program_id": program_id,
            "name": "Steel Plates",
            "code": "MAT-001",
            "resource_type": "material",
            "cost_rate": "50.00",
            "capacity_per_day": "0",
            "quantity_unit": "kg",
            "unit_cost": "50.00",
            "quantity_available": "1000.00",
        },
        headers=headers,
    )
    assert mat_resp.status_code == 201
    material = mat_resp.json()

    # Create labor assignment
    labor_asgn_resp = await client.post(
        f"/api/v1/resources/{labor['id']}/assignments",
        json={
            "activity_id": activity["id"],
            "resource_id": labor["id"],
            "units": "1.0",
            "start_date": "2024-03-01",
            "finish_date": "2024-03-20",
            "planned_hours": "160.00",
        },
        headers=headers,
    )
    assert labor_asgn_resp.status_code == 201
    labor_assignment = labor_asgn_resp.json()

    # Create material assignment
    mat_asgn_resp = await client.post(
        f"/api/v1/resources/{material['id']}/assignments",
        json={
            "activity_id": activity["id"],
            "resource_id": material["id"],
            "units": "1.0",
            "start_date": "2024-03-01",
            "finish_date": "2024-03-20",
            "quantity_assigned": "100.00",
        },
        headers=headers,
    )
    assert mat_asgn_resp.status_code == 201
    material_assignment = mat_asgn_resp.json()

    return {
        "headers": headers,
        "program_id": program_id,
        "wbs_id": wbs["id"],
        "activity_id": activity["id"],
        "labor_id": labor["id"],
        "material_id": material["id"],
        "labor_assignment_id": labor_assignment["id"],
        "material_assignment_id": material_assignment["id"],
    }


class TestActivityCost:
    """Tests for GET /api/v1/cost/activities/{activity_id}."""

    async def test_get_cost_breakdown(
        self, client: AsyncClient, cost_context: dict
    ) -> None:
        """Should return activity cost breakdown."""
        resp = await client.get(
            f"/api/v1/cost/activities/{cost_context['activity_id']}",
            headers=cost_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["activity_id"] == cost_context["activity_id"]
        assert "planned_cost" in data
        assert "actual_cost" in data

    async def test_activity_not_found(
        self, client: AsyncClient, cost_context: dict
    ) -> None:
        """Should return 404 for nonexistent activity."""
        resp = await client.get(
            f"/api/v1/cost/activities/{uuid4()}",
            headers=cost_context["headers"],
        )
        assert resp.status_code == 404

    async def test_unauthenticated(
        self, client: AsyncClient, cost_context: dict
    ) -> None:
        """Should return 401 without auth."""
        resp = await client.get(
            f"/api/v1/cost/activities/{cost_context['activity_id']}",
        )
        assert resp.status_code == 401


class TestWBSCost:
    """Tests for GET /api/v1/cost/wbs/{wbs_id}."""

    async def test_get_wbs_rollup_no_children(
        self, client: AsyncClient, cost_context: dict
    ) -> None:
        """Should return WBS cost rollup without children (avoids ltree)."""
        resp = await client.get(
            f"/api/v1/cost/wbs/{cost_context['wbs_id']}",
            params={"include_children": False},
            headers=cost_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["wbs_id"] == cost_context["wbs_id"]
        assert "planned_cost" in data
        assert "activity_count" in data

    async def test_wbs_not_found(
        self, client: AsyncClient, cost_context: dict
    ) -> None:
        """Should return 404 for nonexistent WBS."""
        resp = await client.get(
            f"/api/v1/cost/wbs/{uuid4()}",
            headers=cost_context["headers"],
        )
        assert resp.status_code == 404


class TestProgramCost:
    """Tests for GET /api/v1/cost/programs/{program_id}.

    Note: Program cost summary uses WBS ltree traversal (PostgreSQL-specific).
    Tests that invoke WBS rollup with include_children=True will fail on SQLite.
    We test the endpoint is reachable and returns the expected status.
    """

    @pytest.mark.skip(reason="Requires PostgreSQL ltree extension for WBS rollup")
    async def test_program_summary(
        self, client: AsyncClient, cost_context: dict
    ) -> None:
        """Should return program cost summary (requires PostgreSQL)."""
        resp = await client.get(
            f"/api/v1/cost/programs/{cost_context['program_id']}",
            headers=cost_context["headers"],
        )
        assert resp.status_code == 200


class TestCostEntries:
    """Tests for POST /api/v1/cost/assignments/{assignment_id}/entries."""

    async def test_record_entry(
        self, client: AsyncClient, cost_context: dict
    ) -> None:
        """Should record a cost entry."""
        resp = await client.post(
            f"/api/v1/cost/assignments/{cost_context['labor_assignment_id']}/entries",
            json={
                "entry_date": "2024-03-05",
                "hours_worked": "8.00",
                "notes": "Full day of work",
            },
            headers=cost_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    async def test_record_entry_with_quantity(
        self, client: AsyncClient, cost_context: dict
    ) -> None:
        """Should record a cost entry with quantity."""
        resp = await client.post(
            f"/api/v1/cost/assignments/{cost_context['material_assignment_id']}/entries",
            json={
                "entry_date": "2024-03-06",
                "hours_worked": "0",
                "quantity_used": "10.00",
            },
            headers=cost_context["headers"],
        )
        assert resp.status_code == 200

    async def test_unauthenticated(
        self, client: AsyncClient, cost_context: dict
    ) -> None:
        """Should return 401 without auth."""
        resp = await client.post(
            f"/api/v1/cost/assignments/{cost_context['labor_assignment_id']}/entries",
            json={
                "entry_date": "2024-03-05",
                "hours_worked": "8.00",
            },
        )
        assert resp.status_code == 401


class TestMaterialTracking:
    """Tests for /api/v1/materials/ endpoints."""

    async def test_material_status(
        self, client: AsyncClient, cost_context: dict
    ) -> None:
        """Should return material resource status."""
        resp = await client.get(
            f"/api/v1/materials/resources/{cost_context['material_id']}",
            headers=cost_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["resource_id"] == cost_context["material_id"]
        assert "quantity_available" in data
        assert "quantity_consumed" in data

    async def test_consume_material(
        self, client: AsyncClient, cost_context: dict
    ) -> None:
        """Should consume material from assignment."""
        resp = await client.post(
            f"/api/v1/materials/assignments/{cost_context['material_assignment_id']}/consume",
            json={"quantity": "5.00"},
            headers=cost_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "quantity_consumed" in data
        assert "cost_incurred" in data

    async def test_program_materials(
        self, client: AsyncClient, cost_context: dict
    ) -> None:
        """Should return program material summary."""
        resp = await client.get(
            f"/api/v1/materials/programs/{cost_context['program_id']}",
            headers=cost_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["program_id"] == cost_context["program_id"]
        assert data["material_count"] >= 1

    async def test_material_not_found(
        self, client: AsyncClient, cost_context: dict
    ) -> None:
        """Should return 404 for nonexistent material resource."""
        resp = await client.get(
            f"/api/v1/materials/resources/{uuid4()}",
            headers=cost_context["headers"],
        )
        assert resp.status_code == 404
