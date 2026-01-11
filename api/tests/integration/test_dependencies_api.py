"""Integration tests for Dependencies API."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestDependenciesAPIAuth:
    """Tests for authentication requirements on dependency endpoints."""

    async def test_list_dependencies_requires_auth(self, client: AsyncClient):
        """Should return 401 when not authenticated."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/dependencies/activity/{fake_id}")
        assert response.status_code == 401

    async def test_create_dependency_requires_auth(self, client: AsyncClient):
        """Should return 401 when creating without auth."""
        response = await client.post(
            "/api/v1/dependencies",
            json={
                "predecessor_id": str(uuid4()),
                "successor_id": str(uuid4()),
            },
        )
        assert response.status_code == 401

    async def test_get_dependency_requires_auth(self, client: AsyncClient):
        """Should return 401 when getting without auth."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/dependencies/{fake_id}")
        assert response.status_code == 401

    async def test_delete_dependency_requires_auth(self, client: AsyncClient):
        """Should return 401 when deleting without auth."""
        fake_id = str(uuid4())
        response = await client.delete(f"/api/v1/dependencies/{fake_id}")
        assert response.status_code == 401


class TestDependenciesAPICRUD:
    """Tests for authenticated dependency CRUD operations."""

    @pytest.fixture
    async def auth_context(self, client: AsyncClient) -> dict:
        """Create user, program, WBS, and activities for testing dependencies."""
        # Register and login user
        email = f"dep_test_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPass123!",
                "full_name": "Dependency Tester",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            headers=headers,
            json={
                "name": "Dependency Test Program",
                "code": f"DTP-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        program_id = program_response.json()["id"]

        # Create WBS element
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "name": "Work Package 1",
                "wbs_code": "1.1",
            },
        )
        wbs_id = wbs_response.json()["id"]

        # Create activities
        activity_ids = []
        for i, name in enumerate(["Activity A", "Activity B", "Activity C"]):
            activity_response = await client.post(
                "/api/v1/activities",
                headers=headers,
                json={
                    "program_id": program_id,
                    "wbs_id": wbs_id,
                    "name": name,
                    "code": f"{chr(65 + i)}",
                    "duration": 5,
                },
            )
            activity_ids.append(activity_response.json()["id"])

        return {
            "headers": headers,
            "program_id": program_id,
            "wbs_id": wbs_id,
            "activity_ids": activity_ids,
        }

    async def test_create_dependency_success(self, client: AsyncClient, auth_context: dict):
        """Should create dependency with valid data."""
        activity_ids = auth_context["activity_ids"]

        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
                "dependency_type": "FS",
                "lag": 0,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["predecessor_id"] == activity_ids[0]
        assert data["successor_id"] == activity_ids[1]
        assert data["dependency_type"] == "FS"
        assert data["lag"] == 0

    async def test_create_dependency_with_lag(self, client: AsyncClient, auth_context: dict):
        """Should create dependency with positive lag."""
        activity_ids = auth_context["activity_ids"]

        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
                "dependency_type": "FS",
                "lag": 3,
            },
        )
        assert response.status_code == 201
        assert response.json()["lag"] == 3

    async def test_create_dependency_with_lead(self, client: AsyncClient, auth_context: dict):
        """Should create dependency with negative lag (lead)."""
        activity_ids = auth_context["activity_ids"]

        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
                "dependency_type": "SS",
                "lag": -2,
            },
        )
        assert response.status_code == 201
        assert response.json()["lag"] == -2
        assert response.json()["dependency_type"] == "SS"

    async def test_create_dependency_invalid_predecessor(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should return 404 for non-existent predecessor."""
        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": str(uuid4()),
                "successor_id": auth_context["activity_ids"][1],
            },
        )
        assert response.status_code == 404
        assert "PREDECESSOR_NOT_FOUND" in response.json()["code"]

    async def test_create_dependency_invalid_successor(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should return 404 for non-existent successor."""
        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][0],
                "successor_id": str(uuid4()),
            },
        )
        assert response.status_code == 404
        assert "SUCCESSOR_NOT_FOUND" in response.json()["code"]

    async def test_create_duplicate_dependency(self, client: AsyncClient, auth_context: dict):
        """Should reject duplicate dependency."""
        activity_ids = auth_context["activity_ids"]

        # Create first dependency
        await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
            },
        )

        # Try to create duplicate
        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
            },
        )
        assert response.status_code == 409
        assert "DUPLICATE_DEPENDENCY" in response.json()["code"]

    async def test_list_dependencies_for_activity(self, client: AsyncClient, auth_context: dict):
        """Should list dependencies for an activity."""
        activity_ids = auth_context["activity_ids"]

        # Create dependencies: A -> B, B -> C
        await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
            },
        )
        await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": activity_ids[1],
                "successor_id": activity_ids[2],
            },
        )

        # List dependencies for B (should have 2 - one as successor, one as predecessor)
        response = await client.get(
            f"/api/v1/dependencies/activity/{activity_ids[1]}",
            headers=auth_context["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_get_dependency_success(self, client: AsyncClient, auth_context: dict):
        """Should get dependency by ID."""
        activity_ids = auth_context["activity_ids"]

        # Create dependency
        create_response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
            },
        )
        dep_id = create_response.json()["id"]

        # Get dependency
        response = await client.get(
            f"/api/v1/dependencies/{dep_id}",
            headers=auth_context["headers"],
        )
        assert response.status_code == 200
        assert response.json()["id"] == dep_id

    async def test_delete_dependency_success(self, client: AsyncClient, auth_context: dict):
        """Should delete dependency."""
        activity_ids = auth_context["activity_ids"]

        # Create dependency
        create_response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
            },
        )
        dep_id = create_response.json()["id"]

        # Delete dependency
        response = await client.delete(
            f"/api/v1/dependencies/{dep_id}",
            headers=auth_context["headers"],
        )
        assert response.status_code == 204

        # Verify deleted
        get_response = await client.get(
            f"/api/v1/dependencies/{dep_id}",
            headers=auth_context["headers"],
        )
        assert get_response.status_code == 404


class TestDependencyCycleDetection:
    """Tests for cycle detection when creating dependencies."""

    @pytest.fixture
    async def cycle_context(self, client: AsyncClient) -> dict:
        """Create user, program, WBS, and activities for cycle testing."""
        email = f"cycle_test_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPass123!",
                "full_name": "Cycle Tester",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        program_response = await client.post(
            "/api/v1/programs",
            headers=headers,
            json={
                "name": "Cycle Test Program",
                "code": f"CYC-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        program_id = program_response.json()["id"]

        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "name": "WBS 1",
                "wbs_code": "1.1",
            },
        )
        wbs_id = wbs_response.json()["id"]

        # Create 3 activities
        activity_ids = []
        for i in range(3):
            activity_response = await client.post(
                "/api/v1/activities",
                headers=headers,
                json={
                    "program_id": program_id,
                    "wbs_id": wbs_id,
                    "name": f"Activity {chr(65 + i)}",
                    "code": chr(65 + i),
                    "duration": 5,
                },
            )
            activity_ids.append(activity_response.json()["id"])

        return {
            "headers": headers,
            "program_id": program_id,
            "activity_ids": activity_ids,
        }

    async def test_cycle_detection_prevents_direct_cycle(
        self, client: AsyncClient, cycle_context: dict
    ):
        """Should prevent A -> B -> A cycle."""
        activity_ids = cycle_context["activity_ids"]
        headers = cycle_context["headers"]

        # Create A -> B
        await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
            },
        )

        # Try to create B -> A (would create cycle)
        response = await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[1],
                "successor_id": activity_ids[0],
            },
        )

        assert response.status_code == 400
        assert "CIRCULAR_DEPENDENCY" in response.json()["code"]

    async def test_cycle_detection_prevents_indirect_cycle(
        self, client: AsyncClient, cycle_context: dict
    ):
        """Should prevent A -> B -> C -> A cycle."""
        activity_ids = cycle_context["activity_ids"]
        headers = cycle_context["headers"]

        # Create A -> B
        await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
            },
        )

        # Create B -> C
        await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[1],
                "successor_id": activity_ids[2],
            },
        )

        # Try to create C -> A (would create cycle)
        response = await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[2],
                "successor_id": activity_ids[0],
            },
        )

        assert response.status_code == 400
        assert "CIRCULAR_DEPENDENCY" in response.json()["code"]

    async def test_valid_chain_allowed(self, client: AsyncClient, cycle_context: dict):
        """Should allow valid chain A -> B -> C."""
        activity_ids = cycle_context["activity_ids"]
        headers = cycle_context["headers"]

        # Create A -> B
        response1 = await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
            },
        )
        assert response1.status_code == 201

        # Create B -> C
        response2 = await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[1],
                "successor_id": activity_ids[2],
            },
        )
        assert response2.status_code == 201
