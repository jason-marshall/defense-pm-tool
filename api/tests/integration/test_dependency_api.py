"""Integration tests for Dependency API endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestDependencyAPIAuth:
    """Tests for Dependency authentication requirements."""

    async def test_get_dependency_requires_auth(self, client: AsyncClient):
        """Should return 401 when not authenticated."""
        response = await client.get(f"/api/v1/dependencies/{uuid4()}")
        assert response.status_code == 401

    async def test_create_dependency_requires_auth(self, client: AsyncClient):
        """Should return 401 when creating without auth."""
        response = await client.post(
            "/api/v1/dependencies",
            json={
                "predecessor_id": str(uuid4()),
                "successor_id": str(uuid4()),
                "dependency_type": "FS",
            },
        )
        assert response.status_code == 401


class TestDependencyAPICRUD:
    """Integration tests for Dependency CRUD operations."""

    @pytest.fixture
    async def auth_context(self, client: AsyncClient) -> dict:
        """Create user, program, and activities for testing dependencies."""
        email = f"dep_test_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "DepTest123!",
                "full_name": "Dep Tester",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "DepTest123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            headers=headers,
            json={
                "name": "Dependency Test Program",
                "code": f"DEP-{uuid4().hex[:6]}",
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
                "name": "Test WBS",
                "wbs_code": "1",
            },
        )
        wbs_id = wbs_response.json()["id"]

        # Create activities
        act1_response = await client.post(
            "/api/v1/activities",
            headers=headers,
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "Activity 1",
                "code": f"ACT1-{uuid4().hex[:6]}",
                "duration": 5,
            },
        )
        act1_id = act1_response.json()["id"]

        act2_response = await client.post(
            "/api/v1/activities",
            headers=headers,
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "Activity 2",
                "code": f"ACT2-{uuid4().hex[:6]}",
                "duration": 3,
            },
        )
        act2_id = act2_response.json()["id"]

        act3_response = await client.post(
            "/api/v1/activities",
            headers=headers,
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "Activity 3",
                "code": f"ACT3-{uuid4().hex[:6]}",
                "duration": 4,
            },
        )
        act3_id = act3_response.json()["id"]

        return {
            "headers": headers,
            "program_id": program_id,
            "activity_ids": [act1_id, act2_id, act3_id],
        }

    async def test_create_fs_dependency(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should create finish-to-start dependency."""
        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][0],
                "successor_id": auth_context["activity_ids"][1],
                "dependency_type": "FS",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["dependency_type"] == "FS"
        assert data["predecessor_id"] == auth_context["activity_ids"][0]
        assert data["successor_id"] == auth_context["activity_ids"][1]

    async def test_create_dependency_with_lag(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should create dependency with lag."""
        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][0],
                "successor_id": auth_context["activity_ids"][1],
                "dependency_type": "FS",
                "lag": 2,
            },
        )
        assert response.status_code == 201
        assert response.json()["lag"] == 2

    async def test_get_dependency(self, client: AsyncClient, auth_context: dict):
        """Should get dependency by ID."""
        # Create dependency
        create_response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][0],
                "successor_id": auth_context["activity_ids"][1],
                "dependency_type": "FS",
            },
        )
        dep_id = create_response.json()["id"]

        # Get dependency
        get_response = await client.get(
            f"/api/v1/dependencies/{dep_id}",
            headers=auth_context["headers"],
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == dep_id

    async def test_update_dependency(self, client: AsyncClient, auth_context: dict):
        """Should update dependency type and lag."""
        # Create dependency
        create_response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][0],
                "successor_id": auth_context["activity_ids"][1],
                "dependency_type": "FS",
                "lag": 0,
            },
        )
        dep_id = create_response.json()["id"]

        # Update dependency
        update_response = await client.patch(
            f"/api/v1/dependencies/{dep_id}",
            headers=auth_context["headers"],
            json={"dependency_type": "SS", "lag": 3},
        )
        assert update_response.status_code == 200
        assert update_response.json()["dependency_type"] == "SS"
        assert update_response.json()["lag"] == 3

    async def test_delete_dependency(self, client: AsyncClient, auth_context: dict):
        """Should delete dependency."""
        # Create dependency
        create_response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][0],
                "successor_id": auth_context["activity_ids"][1],
                "dependency_type": "FS",
            },
        )
        dep_id = create_response.json()["id"]

        # Delete dependency
        delete_response = await client.delete(
            f"/api/v1/dependencies/{dep_id}",
            headers=auth_context["headers"],
        )
        assert delete_response.status_code == 204

        # Verify deleted
        get_response = await client.get(
            f"/api/v1/dependencies/{dep_id}",
            headers=auth_context["headers"],
        )
        assert get_response.status_code == 404

    async def test_list_dependencies_for_activity(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should list all dependencies for an activity."""
        # Create dependencies
        await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][0],
                "successor_id": auth_context["activity_ids"][1],
                "dependency_type": "FS",
            },
        )
        await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][1],
                "successor_id": auth_context["activity_ids"][2],
                "dependency_type": "FS",
            },
        )

        # List dependencies for middle activity (both predecessor and successor)
        response = await client.get(
            f"/api/v1/dependencies/activity/{auth_context['activity_ids'][1]}",
            headers=auth_context["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_list_dependencies_for_program(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should list all dependencies for a program."""
        # Create dependencies
        await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][0],
                "successor_id": auth_context["activity_ids"][1],
                "dependency_type": "FS",
            },
        )

        # List dependencies for program
        response = await client.get(
            f"/api/v1/dependencies/program/{auth_context['program_id']}",
            headers=auth_context["headers"],
        )
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    async def test_prevent_duplicate_dependency(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should prevent creating duplicate dependency."""
        # Create first dependency
        await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][0],
                "successor_id": auth_context["activity_ids"][1],
                "dependency_type": "FS",
            },
        )

        # Try to create duplicate
        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][0],
                "successor_id": auth_context["activity_ids"][1],
                "dependency_type": "FS",
            },
        )
        assert response.status_code == 409

    async def test_prevent_circular_dependency(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should prevent creating circular dependency."""
        # Create A -> B
        await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][0],
                "successor_id": auth_context["activity_ids"][1],
                "dependency_type": "FS",
            },
        )

        # Create B -> C
        await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][1],
                "successor_id": auth_context["activity_ids"][2],
                "dependency_type": "FS",
            },
        )

        # Try to create C -> A (would create cycle)
        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][2],
                "successor_id": auth_context["activity_ids"][0],
                "dependency_type": "FS",
            },
        )
        assert response.status_code == 400

    async def test_nonexistent_predecessor_returns_404(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should return 404 for nonexistent predecessor."""
        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": str(uuid4()),
                "successor_id": auth_context["activity_ids"][1],
                "dependency_type": "FS",
            },
        )
        assert response.status_code == 404

    async def test_nonexistent_successor_returns_404(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should return 404 for nonexistent successor."""
        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_context["headers"],
            json={
                "predecessor_id": auth_context["activity_ids"][0],
                "successor_id": str(uuid4()),
                "dependency_type": "FS",
            },
        )
        assert response.status_code == 404
