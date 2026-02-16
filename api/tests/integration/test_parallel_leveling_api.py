"""Integration tests for Parallel Resource Leveling API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def leveling_context(client: AsyncClient) -> dict:
    """Create user, program, WBS, activities, dependency, resource, and overlapping assignments."""
    email = f"level_{uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "TestPass123!",
            "full_name": "Leveling Tester",
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
            "name": "Leveling Test Program",
            "code": f"LV-{uuid4().hex[:6]}",
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
        json={"program_id": program_id, "name": "Level WP", "wbs_code": "1.1"},
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
            "name": "Level Activity A",
            "code": "LV-A",
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
            "name": "Level Activity B",
            "code": "LV-B",
            "duration": 10,
        },
        headers=headers,
    )
    assert act2_resp.status_code == 201
    act2 = act2_resp.json()

    # Create resource
    res_resp = await client.post(
        "/api/v1/resources",
        json={
            "program_id": program_id,
            "name": "Level Worker",
            "code": "LW-001",
            "resource_type": "labor",
            "cost_rate": "100.00",
            "capacity_per_day": "8.00",
        },
        headers=headers,
    )
    assert res_resp.status_code == 201
    resource = res_resp.json()

    # Create overlapping assignments
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
    }


class TestRunParallelLeveling:
    """Tests for POST /api/v1/programs/{id}/level-parallel."""

    async def test_run_success(
        self, client: AsyncClient, leveling_context: dict
    ) -> None:
        """Should run parallel leveling successfully."""
        resp = await client.post(
            f"/api/v1/programs/{leveling_context['program_id']}/level-parallel",
            json={
                "preserve_critical_path": True,
                "max_iterations": 100,
                "level_within_float": True,
            },
            headers=leveling_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["program_id"] == leveling_context["program_id"]
        assert "success" in data
        assert "iterations_used" in data
        assert "shifts" in data

    async def test_program_not_found(
        self, client: AsyncClient, leveling_context: dict
    ) -> None:
        """Should return 404 for nonexistent program."""
        resp = await client.post(
            f"/api/v1/programs/{uuid4()}/level-parallel",
            json={"preserve_critical_path": True, "max_iterations": 100},
            headers=leveling_context["headers"],
        )
        assert resp.status_code == 404

    async def test_with_target_resources(
        self, client: AsyncClient, leveling_context: dict
    ) -> None:
        """Should accept target_resources parameter."""
        resp = await client.post(
            f"/api/v1/programs/{leveling_context['program_id']}/level-parallel",
            json={
                "preserve_critical_path": True,
                "max_iterations": 50,
                "target_resources": [leveling_context["resource_id"]],
            },
            headers=leveling_context["headers"],
        )
        assert resp.status_code == 200

    async def test_unauthenticated(
        self, client: AsyncClient, leveling_context: dict
    ) -> None:
        """Should return 401 without auth."""
        resp = await client.post(
            f"/api/v1/programs/{leveling_context['program_id']}/level-parallel",
            json={"preserve_critical_path": True, "max_iterations": 100},
        )
        assert resp.status_code == 401

    async def test_result_structure(
        self, client: AsyncClient, leveling_context: dict
    ) -> None:
        """Should return complete result structure."""
        resp = await client.post(
            f"/api/v1/programs/{leveling_context['program_id']}/level-parallel",
            json={"preserve_critical_path": True, "max_iterations": 100},
            headers=leveling_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "activities_shifted" in data
        assert "remaining_overallocations" in data
        assert "schedule_extension_days" in data
        assert "warnings" in data
        assert "conflicts_resolved" in data
        assert "resources_processed" in data


class TestPreviewParallelLeveling:
    """Tests for GET /api/v1/programs/{id}/level-parallel/preview."""

    async def test_preview_success(
        self, client: AsyncClient, leveling_context: dict
    ) -> None:
        """Should preview leveling without applying."""
        resp = await client.get(
            f"/api/v1/programs/{leveling_context['program_id']}/level-parallel/preview",
            headers=leveling_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["program_id"] == leveling_context["program_id"]

    async def test_preview_program_not_found(
        self, client: AsyncClient, leveling_context: dict
    ) -> None:
        """Should return 404 for nonexistent program."""
        resp = await client.get(
            f"/api/v1/programs/{uuid4()}/level-parallel/preview",
            headers=leveling_context["headers"],
        )
        assert resp.status_code == 404

    async def test_preview_with_params(
        self, client: AsyncClient, leveling_context: dict
    ) -> None:
        """Should accept query parameters."""
        resp = await client.get(
            f"/api/v1/programs/{leveling_context['program_id']}/level-parallel/preview",
            params={
                "preserve_critical_path": False,
                "level_within_float": False,
                "max_iterations": 50,
            },
            headers=leveling_context["headers"],
        )
        assert resp.status_code == 200


class TestCompareLevelingAlgorithms:
    """Tests for GET /api/v1/programs/{id}/level/compare."""

    async def test_compare_success(
        self, client: AsyncClient, leveling_context: dict
    ) -> None:
        """Should compare serial and parallel algorithms."""
        resp = await client.get(
            f"/api/v1/programs/{leveling_context['program_id']}/level/compare",
            headers=leveling_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "serial" in data
        assert "parallel" in data
        assert "recommendation" in data
        assert "improvement" in data

    async def test_compare_returns_recommendation(
        self, client: AsyncClient, leveling_context: dict
    ) -> None:
        """Should recommend either serial or parallel."""
        resp = await client.get(
            f"/api/v1/programs/{leveling_context['program_id']}/level/compare",
            headers=leveling_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["recommendation"] in ("serial", "parallel")

    async def test_compare_metrics_structure(
        self, client: AsyncClient, leveling_context: dict
    ) -> None:
        """Should include algorithm metrics."""
        resp = await client.get(
            f"/api/v1/programs/{leveling_context['program_id']}/level/compare",
            headers=leveling_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        for algo in ("serial", "parallel"):
            assert "success" in data[algo]
            assert "iterations" in data[algo]
            assert "activities_shifted" in data[algo]
            assert "schedule_extension_days" in data[algo]

    async def test_compare_program_not_found(
        self, client: AsyncClient, leveling_context: dict
    ) -> None:
        """Should return 404 for nonexistent program."""
        resp = await client.get(
            f"/api/v1/programs/{uuid4()}/level/compare",
            headers=leveling_context["headers"],
        )
        assert resp.status_code == 404

    async def test_compare_with_options(
        self, client: AsyncClient, leveling_context: dict
    ) -> None:
        """Should accept leveling options."""
        resp = await client.get(
            f"/api/v1/programs/{leveling_context['program_id']}/level/compare",
            params={
                "preserve_critical_path": False,
                "max_iterations": 50,
            },
            headers=leveling_context["headers"],
        )
        assert resp.status_code == 200
