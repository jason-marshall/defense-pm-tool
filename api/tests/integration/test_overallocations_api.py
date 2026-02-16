"""Integration tests for Over-Allocation Detection API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def overalloc_context(client: AsyncClient) -> dict:
    """Create user, program, WBS, activities, resource, and overlapping assignments."""
    email = f"overalloc_{uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "TestPass123!",
            "full_name": "Overalloc Tester",
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
            "name": "Overalloc Test Program",
            "code": f"OA-{uuid4().hex[:6]}",
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
        json={"program_id": program_id, "name": "OA Work Package", "wbs_code": "1.1"},
        headers=headers,
    )
    assert wbs_resp.status_code == 201
    wbs = wbs_resp.json()

    # Create two activities
    act1_resp = await client.post(
        "/api/v1/activities",
        json={
            "program_id": program_id,
            "wbs_id": wbs["id"],
            "name": "Activity Alpha",
            "code": "ACT-A",
            "duration": 10,
        },
        headers=headers,
    )
    assert act1_resp.status_code == 201
    act1 = act1_resp.json()

    act2_resp = await client.post(
        "/api/v1/activities",
        json={
            "program_id": program_id,
            "wbs_id": wbs["id"],
            "name": "Activity Beta",
            "code": "ACT-B",
            "duration": 10,
        },
        headers=headers,
    )
    assert act2_resp.status_code == 201
    act2 = act2_resp.json()

    # Create resource (8h/day capacity)
    res_resp = await client.post(
        "/api/v1/resources",
        json={
            "program_id": program_id,
            "name": "Shared Worker",
            "code": "SW-001",
            "resource_type": "labor",
            "cost_rate": "100.00",
            "capacity_per_day": "8.00",
        },
        headers=headers,
    )
    assert res_resp.status_code == 201
    resource = res_resp.json()

    # Create overlapping assignments (both full-time = 200% overalloc)
    asgn1_resp = await client.post(
        f"/api/v1/resources/{resource['id']}/assignments",
        json={
            "activity_id": act1["id"],
            "resource_id": resource["id"],
            "units": "1.0",
            "start_date": "2024-03-01",
            "finish_date": "2024-03-15",
        },
        headers=headers,
    )
    assert asgn1_resp.status_code == 201

    asgn2_resp = await client.post(
        f"/api/v1/resources/{resource['id']}/assignments",
        json={
            "activity_id": act2["id"],
            "resource_id": resource["id"],
            "units": "1.0",
            "start_date": "2024-03-05",
            "finish_date": "2024-03-20",
        },
        headers=headers,
    )
    assert asgn2_resp.status_code == 201

    return {
        "headers": headers,
        "program_id": program_id,
        "resource_id": resource["id"],
        "activity_ids": [act1["id"], act2["id"]],
        "wbs_id": wbs["id"],
    }


class TestResourceOverallocations:
    """Tests for GET /api/v1/overallocations/resources/{resource_id}."""

    async def test_detect_overlap(
        self, client: AsyncClient, overalloc_context: dict
    ) -> None:
        """Should detect overallocation for overlapping assignments."""
        resp = await client.get(
            f"/api/v1/overallocations/resources/{overalloc_context['resource_id']}",
            params={"start_date": "2024-03-01", "end_date": "2024-03-31"},
            headers=overalloc_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        # Overallocation period should exist in overlap range (Mar 5-15)
        period = data[0]
        assert "peak_assigned" in period
        assert "peak_available" in period

    async def test_no_overallocation_outside_range(
        self, client: AsyncClient, overalloc_context: dict
    ) -> None:
        """Should return no overallocations outside assignment dates."""
        resp = await client.get(
            f"/api/v1/overallocations/resources/{overalloc_context['resource_id']}",
            params={"start_date": "2024-06-01", "end_date": "2024-06-30"},
            headers=overalloc_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0

    async def test_unauthenticated(
        self, client: AsyncClient, overalloc_context: dict
    ) -> None:
        """Should return 401 without auth."""
        resp = await client.get(
            f"/api/v1/overallocations/resources/{overalloc_context['resource_id']}",
            params={"start_date": "2024-03-01", "end_date": "2024-03-31"},
        )
        assert resp.status_code == 401


class TestProgramOverallocations:
    """Tests for GET /api/v1/overallocations/programs/{program_id}."""

    async def test_program_report(
        self, client: AsyncClient, overalloc_context: dict
    ) -> None:
        """Should return program overallocation report."""
        resp = await client.get(
            f"/api/v1/overallocations/programs/{overalloc_context['program_id']}",
            headers=overalloc_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["program_id"] == overalloc_context["program_id"]
        assert data["total_overallocations"] >= 1
        assert data["resources_affected"] >= 1

    async def test_program_report_no_overallocations(
        self, client: AsyncClient, overalloc_context: dict
    ) -> None:
        """Should handle date range with no overallocations."""
        resp = await client.get(
            f"/api/v1/overallocations/programs/{overalloc_context['program_id']}",
            params={"start_date": "2024-10-01", "end_date": "2024-10-31"},
            headers=overalloc_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_overallocations"] == 0

    async def test_program_report_custom_dates(
        self, client: AsyncClient, overalloc_context: dict
    ) -> None:
        """Should accept custom date range."""
        resp = await client.get(
            f"/api/v1/overallocations/programs/{overalloc_context['program_id']}",
            params={"start_date": "2024-03-01", "end_date": "2024-03-31"},
            headers=overalloc_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_start" in data
        assert "analysis_end" in data


class TestAffectedActivities:
    """Tests for GET /api/v1/overallocations/resources/{resource_id}/affected-activities."""

    async def test_get_affected_activities(
        self, client: AsyncClient, overalloc_context: dict
    ) -> None:
        """Should return activity IDs on overallocated date."""
        resp = await client.get(
            f"/api/v1/overallocations/resources/{overalloc_context['resource_id']}/affected-activities",
            params={"check_date": "2024-03-10"},
            headers=overalloc_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        # Both activities overlap on Mar 10
        assert len(data) >= 2

    async def test_no_affected_activities_outside_range(
        self, client: AsyncClient, overalloc_context: dict
    ) -> None:
        """Should return empty list outside assignment dates."""
        resp = await client.get(
            f"/api/v1/overallocations/resources/{overalloc_context['resource_id']}/affected-activities",
            params={"check_date": "2024-06-01"},
            headers=overalloc_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0

    async def test_affected_activities_single_assignment(
        self, client: AsyncClient, overalloc_context: dict
    ) -> None:
        """Should return single activity on non-overlap date."""
        # Mar 1-4: only act1 is assigned, Mar 16-20: only act2
        resp = await client.get(
            f"/api/v1/overallocations/resources/{overalloc_context['resource_id']}/affected-activities",
            params={"check_date": "2024-03-02"},
            headers=overalloc_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
