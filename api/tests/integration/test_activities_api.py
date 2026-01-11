"""Integration tests for Activities API."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestActivitiesAPIAuth:
    """Tests for authentication requirements on activity endpoints."""

    async def test_list_activities_requires_auth(self, client: AsyncClient):
        """Should return 401 when not authenticated."""
        fake_program_id = str(uuid4())
        response = await client.get(f"/api/v1/activities?program_id={fake_program_id}")
        assert response.status_code == 401

    async def test_create_activity_requires_auth(self, client: AsyncClient):
        """Should return 401 when creating without auth."""
        response = await client.post(
            "/api/v1/activities",
            json={
                "program_id": str(uuid4()),
                "wbs_id": str(uuid4()),
                "name": "Test Activity",
                "code": "TA-001",
            },
        )
        assert response.status_code == 401

    async def test_get_activity_requires_auth(self, client: AsyncClient):
        """Should return 401 when getting without auth."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/activities/{fake_id}")
        assert response.status_code == 401

    async def test_update_activity_requires_auth(self, client: AsyncClient):
        """Should return 401 when updating without auth."""
        fake_id = str(uuid4())
        response = await client.patch(
            f"/api/v1/activities/{fake_id}",
            json={"name": "Updated"},
        )
        assert response.status_code == 401

    async def test_delete_activity_requires_auth(self, client: AsyncClient):
        """Should return 401 when deleting without auth."""
        fake_id = str(uuid4())
        response = await client.delete(f"/api/v1/activities/{fake_id}")
        assert response.status_code == 401


class TestActivitiesAPICRUD:
    """Tests for authenticated activity CRUD operations."""

    @pytest.fixture
    async def auth_context(self, client: AsyncClient) -> dict:
        """Create user, program, and WBS element for testing activities."""
        # Register and login user
        email = f"activity_test_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPass123!",
                "full_name": "Activity Tester",
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
                "name": "Test Program",
                "code": f"TP-{uuid4().hex[:6]}",
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

        return {
            "headers": headers,
            "program_id": program_id,
            "wbs_id": wbs_id,
        }

    async def test_create_activity_success(self, client: AsyncClient, auth_context: dict):
        """Should create activity with valid data."""
        response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": auth_context["program_id"],
                "wbs_id": auth_context["wbs_id"],
                "name": "Design Review",
                "code": "DR-001",
                "duration": 5,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Design Review"
        assert data["code"] == "DR-001"
        assert data["duration"] == 5

    async def test_create_activity_auto_code(self, client: AsyncClient, auth_context: dict):
        """Should auto-generate code if not provided."""
        response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": auth_context["program_id"],
                "wbs_id": auth_context["wbs_id"],
                "name": "Auto Code Activity",
                "duration": 3,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] is not None
        assert data["code"].startswith("A-")

    async def test_create_activity_invalid_program(self, client: AsyncClient, auth_context: dict):
        """Should return 404 for non-existent program."""
        response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": str(uuid4()),
                "wbs_id": auth_context["wbs_id"],
                "name": "Test Activity",
                "code": "TA-001",
            },
        )
        assert response.status_code == 404
        assert "PROGRAM_NOT_FOUND" in response.json()["code"]

    async def test_create_activity_invalid_wbs(self, client: AsyncClient, auth_context: dict):
        """Should return 404 for non-existent WBS element."""
        response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": auth_context["program_id"],
                "wbs_id": str(uuid4()),
                "name": "Test Activity",
                "code": "TA-001",
            },
        )
        assert response.status_code == 404
        assert "WBS_NOT_FOUND" in response.json()["code"]

    async def test_list_activities_by_program(self, client: AsyncClient, auth_context: dict):
        """Should list activities filtered by program."""
        # Create multiple activities
        for i in range(3):
            await client.post(
                "/api/v1/activities",
                headers=auth_context["headers"],
                json={
                    "program_id": auth_context["program_id"],
                    "wbs_id": auth_context["wbs_id"],
                    "name": f"Activity {i}",
                    "code": f"A-{i:03d}",
                    "duration": i + 1,
                },
            )

        response = await client.get(
            f"/api/v1/activities?program_id={auth_context['program_id']}",
            headers=auth_context["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_list_activities_empty_program(self, client: AsyncClient, auth_context: dict):
        """Should return empty list for program with no activities."""
        response = await client.get(
            f"/api/v1/activities?program_id={auth_context['program_id']}",
            headers=auth_context["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_get_activity_success(self, client: AsyncClient, auth_context: dict):
        """Should get activity by ID."""
        # Create activity
        create_response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": auth_context["program_id"],
                "wbs_id": auth_context["wbs_id"],
                "name": "Test Activity",
                "code": "TA-001",
                "duration": 5,
            },
        )
        activity_id = create_response.json()["id"]

        # Get activity
        response = await client.get(
            f"/api/v1/activities/{activity_id}",
            headers=auth_context["headers"],
        )
        assert response.status_code == 200
        assert response.json()["id"] == activity_id

    async def test_get_activity_not_found(self, client: AsyncClient, auth_context: dict):
        """Should return 404 for non-existent activity."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/activities/{fake_id}",
            headers=auth_context["headers"],
        )
        assert response.status_code == 404

    async def test_update_activity_success(self, client: AsyncClient, auth_context: dict):
        """Should update activity."""
        # Create activity
        create_response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": auth_context["program_id"],
                "wbs_id": auth_context["wbs_id"],
                "name": "Original Name",
                "code": "ON-001",
                "duration": 5,
            },
        )
        activity_id = create_response.json()["id"]

        # Update activity
        response = await client.patch(
            f"/api/v1/activities/{activity_id}",
            headers=auth_context["headers"],
            json={"name": "Updated Name", "duration": 10},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["duration"] == 10

    async def test_update_activity_partial(self, client: AsyncClient, auth_context: dict):
        """Should allow partial updates."""
        # Create activity
        create_response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": auth_context["program_id"],
                "wbs_id": auth_context["wbs_id"],
                "name": "Original Name",
                "code": "ON-002",
                "duration": 5,
            },
        )
        activity_id = create_response.json()["id"]

        # Update only duration
        response = await client.patch(
            f"/api/v1/activities/{activity_id}",
            headers=auth_context["headers"],
            json={"duration": 15},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Original Name"  # Unchanged
        assert response.json()["duration"] == 15

    async def test_delete_activity_success(self, client: AsyncClient, auth_context: dict):
        """Should delete activity."""
        # Create activity
        create_response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": auth_context["program_id"],
                "wbs_id": auth_context["wbs_id"],
                "name": "To Delete",
                "code": "TD-001",
                "duration": 5,
            },
        )
        activity_id = create_response.json()["id"]

        # Delete activity
        response = await client.delete(
            f"/api/v1/activities/{activity_id}",
            headers=auth_context["headers"],
        )
        assert response.status_code == 204

        # Verify deleted
        get_response = await client.get(
            f"/api/v1/activities/{activity_id}",
            headers=auth_context["headers"],
        )
        assert get_response.status_code == 404

    async def test_create_milestone(self, client: AsyncClient, auth_context: dict):
        """Should create milestone with zero duration."""
        response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": auth_context["program_id"],
                "wbs_id": auth_context["wbs_id"],
                "name": "Phase Complete",
                "code": "M-001",
                "duration": 5,  # Should be overridden to 0
                "is_milestone": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_milestone"] is True
        assert data["duration"] == 0


class TestActivitiesAPIAuthorization:
    """Tests for authorization (ownership) checks."""

    async def test_unauthorized_access_other_user_program(self, client: AsyncClient):
        """Should not allow access to other user's program activities."""
        # Create first user and their program + WBS
        user1_email = f"owner_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": user1_email,
                "password": "TestPass123!",
                "full_name": "Owner",
            },
        )
        login1 = await client.post(
            "/api/v1/auth/login",
            json={"email": user1_email, "password": "TestPass123!"},
        )
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            headers=headers1,
            json={
                "name": "Owner's Program",
                "code": f"OP-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        program_id = program_response.json()["id"]

        # Create second user
        user2_email = f"other_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": user2_email,
                "password": "TestPass123!",
                "full_name": "Other",
            },
        )
        login2 = await client.post(
            "/api/v1/auth/login",
            json={"email": user2_email, "password": "TestPass123!"},
        )
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        # Other user tries to list activities from owner's program
        response = await client.get(
            f"/api/v1/activities?program_id={program_id}",
            headers=headers2,
        )
        assert response.status_code == 403

    async def test_unauthorized_create_activity_other_program(self, client: AsyncClient):
        """Should not allow creating activity in other user's program."""
        # Create first user and their program + WBS
        user1_email = f"creator_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": user1_email,
                "password": "TestPass123!",
                "full_name": "Creator",
            },
        )
        login1 = await client.post(
            "/api/v1/auth/login",
            json={"email": user1_email, "password": "TestPass123!"},
        )
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

        program_response = await client.post(
            "/api/v1/programs",
            headers=headers1,
            json={
                "name": "Creator's Program",
                "code": f"CP-{uuid4().hex[:6]}",
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

        # Create second user
        user2_email = f"intruder_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": user2_email,
                "password": "TestPass123!",
                "full_name": "Intruder",
            },
        )
        login2 = await client.post(
            "/api/v1/auth/login",
            json={"email": user2_email, "password": "TestPass123!"},
        )
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        # Other user tries to create activity in owner's program
        response = await client.post(
            "/api/v1/activities",
            headers=headers2,
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "Unauthorized Activity",
                "code": "UA-001",
            },
        )
        assert response.status_code == 403
