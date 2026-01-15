"""Integration tests for EV Methods API."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestEVMethodsAPIAuth:
    """Tests for authentication requirements on EV method endpoints."""

    async def test_list_ev_methods_public(self, client: AsyncClient):
        """EV methods list is publicly accessible (no auth required)."""
        response = await client.get("/api/v1/evms/ev-methods")
        assert response.status_code == 200

        methods = response.json()
        assert isinstance(methods, list)
        assert len(methods) >= 5

    async def test_set_activity_ev_method_requires_auth(self, client: AsyncClient):
        """Should return 401 when setting EV method without auth."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/evms/activities/{fake_id}/ev-method",
            params={"ev_method": "percent_complete"},
        )
        assert response.status_code == 401


class TestEVMethodsAPICRUD:
    """Tests for authenticated EV method operations."""

    @pytest.fixture
    async def auth_context(self, client: AsyncClient) -> dict:
        """Create user, program, WBS element, and activity for testing EV methods."""
        # Register and login user
        email = f"ev_test_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPass123!",
                "full_name": "EV Method Tester",
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

        # Create activity
        activity_response = await client.post(
            "/api/v1/activities",
            headers=headers,
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "Test Activity",
                "code": f"ACT-{uuid4().hex[:6]}",
                "duration": 10,
                "budgeted_cost": "10000.00",
            },
        )
        activity_id = activity_response.json()["id"]

        return {
            "headers": headers,
            "program_id": program_id,
            "wbs_id": wbs_id,
            "activity_id": activity_id,
        }

    async def test_list_ev_methods(self, client: AsyncClient, auth_context: dict):
        """Should return list of available EV methods."""
        response = await client.get(
            "/api/v1/evms/ev-methods",
            headers=auth_context["headers"],
        )
        assert response.status_code == 200

        methods = response.json()
        assert isinstance(methods, list)
        assert len(methods) >= 5  # At least 5 methods defined

        # Verify each method has required fields
        for method in methods:
            assert "value" in method
            assert "display_name" in method
            assert "description" in method
            assert "recommended_duration" in method

        # Verify specific methods exist
        method_values = [m["value"] for m in methods]
        assert "0/100" in method_values
        assert "50/50" in method_values
        assert "percent_complete" in method_values
        assert "milestone_weight" in method_values
        assert "loe" in method_values

    async def test_set_activity_ev_method_percent_complete(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should set percent_complete EV method on activity."""
        response = await client.post(
            f"/api/v1/evms/activities/{auth_context['activity_id']}/ev-method",
            headers=auth_context["headers"],
            params={"ev_method": "percent_complete"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["activity_id"] == auth_context["activity_id"]
        assert data["ev_method"] == "percent_complete"
        assert "ev_method_display" in data

    async def test_set_activity_ev_method_zero_hundred(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should set 0/100 EV method on activity."""
        response = await client.post(
            f"/api/v1/evms/activities/{auth_context['activity_id']}/ev-method",
            headers=auth_context["headers"],
            params={"ev_method": "0/100"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["ev_method"] == "0/100"

    async def test_set_activity_ev_method_fifty_fifty(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should set 50/50 EV method on activity."""
        response = await client.post(
            f"/api/v1/evms/activities/{auth_context['activity_id']}/ev-method",
            headers=auth_context["headers"],
            params={"ev_method": "50/50"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["ev_method"] == "50/50"

    async def test_set_activity_ev_method_loe(self, client: AsyncClient, auth_context: dict):
        """Should set LOE EV method on activity."""
        response = await client.post(
            f"/api/v1/evms/activities/{auth_context['activity_id']}/ev-method",
            headers=auth_context["headers"],
            params={"ev_method": "loe"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["ev_method"] == "loe"

    async def test_set_activity_ev_method_milestone_weight_with_milestones(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should set milestone_weight EV method with milestone definitions."""
        milestones = [
            {"name": "Design", "weight": 0.25, "is_complete": False},
            {"name": "Build", "weight": 0.50, "is_complete": False},
            {"name": "Test", "weight": 0.25, "is_complete": False},
        ]

        response = await client.post(
            f"/api/v1/evms/activities/{auth_context['activity_id']}/ev-method",
            headers=auth_context["headers"],
            params={"ev_method": "milestone_weight"},
            json=milestones,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["ev_method"] == "milestone_weight"
        assert data["milestones"] is not None

    async def test_set_activity_ev_method_milestone_weight_invalid_weights(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should reject milestone_weight with weights not summing to 1.0."""
        milestones = [
            {"name": "Design", "weight": 0.25, "is_complete": False},
            {"name": "Build", "weight": 0.25, "is_complete": False},
            # Missing 0.50 weight - total is only 0.50
        ]

        response = await client.post(
            f"/api/v1/evms/activities/{auth_context['activity_id']}/ev-method",
            headers=auth_context["headers"],
            params={"ev_method": "milestone_weight"},
            json=milestones,
        )
        assert response.status_code == 422  # ValidationError

    async def test_set_activity_ev_method_invalid_method(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should reject invalid EV method."""
        response = await client.post(
            f"/api/v1/evms/activities/{auth_context['activity_id']}/ev-method",
            headers=auth_context["headers"],
            params={"ev_method": "invalid_method"},
        )
        assert response.status_code == 422  # ValidationError

    async def test_set_activity_ev_method_not_found(self, client: AsyncClient, auth_context: dict):
        """Should return 404 for non-existent activity."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/evms/activities/{fake_id}/ev-method",
            headers=auth_context["headers"],
            params={"ev_method": "percent_complete"},
        )
        assert response.status_code == 404


class TestEVMethodsIntegration:
    """Tests for EV method integration with activity CRUD."""

    @pytest.fixture
    async def auth_context(self, client: AsyncClient) -> dict:
        """Create user, program, and WBS element for testing."""
        email = f"ev_integ_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPass123!",
                "full_name": "Integration Tester",
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
                "name": "Test Program",
                "code": f"TP-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        program_id = program_response.json()["id"]

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

    async def test_create_activity_with_ev_method(self, client: AsyncClient, auth_context: dict):
        """Should create activity with specified EV method."""
        response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": auth_context["program_id"],
                "wbs_id": auth_context["wbs_id"],
                "name": "Activity with EV Method",
                "code": f"ACT-{uuid4().hex[:6]}",
                "duration": 10,
                "budgeted_cost": "10000.00",
                "ev_method": "50/50",
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["ev_method"] == "50/50"

    async def test_create_activity_default_ev_method(self, client: AsyncClient, auth_context: dict):
        """Should default to percent_complete EV method when not specified."""
        response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": auth_context["program_id"],
                "wbs_id": auth_context["wbs_id"],
                "name": "Default EV Method Activity",
                "code": f"ACT-{uuid4().hex[:6]}",
                "duration": 5,
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["ev_method"] == "percent_complete"

    async def test_create_activity_with_milestones(self, client: AsyncClient, auth_context: dict):
        """Should create activity with milestone_weight and milestones."""
        milestones = [
            {"name": "Requirements", "weight": 0.20, "is_complete": False},
            {"name": "Design", "weight": 0.30, "is_complete": False},
            {"name": "Implementation", "weight": 0.35, "is_complete": False},
            {"name": "Testing", "weight": 0.15, "is_complete": False},
        ]

        response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": auth_context["program_id"],
                "wbs_id": auth_context["wbs_id"],
                "name": "Milestone Weight Activity",
                "code": f"ACT-{uuid4().hex[:6]}",
                "duration": 30,
                "budgeted_cost": "50000.00",
                "ev_method": "milestone_weight",
                "milestones_json": milestones,
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["ev_method"] == "milestone_weight"
        assert data["milestones_json"] is not None
        assert len(data["milestones_json"]) == 4

    async def test_update_activity_ev_method(self, client: AsyncClient, auth_context: dict):
        """Should update activity's EV method via PATCH."""
        # Create activity
        create_response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": auth_context["program_id"],
                "wbs_id": auth_context["wbs_id"],
                "name": "Activity to Update",
                "code": f"ACT-{uuid4().hex[:6]}",
                "duration": 10,
            },
        )
        activity_id = create_response.json()["id"]

        # Update EV method
        update_response = await client.patch(
            f"/api/v1/activities/{activity_id}",
            headers=auth_context["headers"],
            json={"ev_method": "0/100"},
        )
        assert update_response.status_code == 200

        data = update_response.json()
        assert data["ev_method"] == "0/100"

    async def test_get_activity_includes_ev_method(self, client: AsyncClient, auth_context: dict):
        """Should return EV method when getting activity."""
        # Create activity with specific EV method
        create_response = await client.post(
            "/api/v1/activities",
            headers=auth_context["headers"],
            json={
                "program_id": auth_context["program_id"],
                "wbs_id": auth_context["wbs_id"],
                "name": "Activity with LOE",
                "code": f"ACT-{uuid4().hex[:6]}",
                "duration": 10,
                "ev_method": "loe",
            },
        )
        activity_id = create_response.json()["id"]

        # Get activity
        get_response = await client.get(
            f"/api/v1/activities/{activity_id}",
            headers=auth_context["headers"],
        )
        assert get_response.status_code == 200

        data = get_response.json()
        assert data["ev_method"] == "loe"
