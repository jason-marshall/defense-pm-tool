"""Integration tests for WBS API endpoints."""

from uuid import uuid4
from decimal import Decimal

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestWBSAPICRUD:
    """Integration tests for WBS CRUD operations."""

    @pytest.fixture
    async def auth_context(self, client: AsyncClient) -> dict:
        """Create user and program for testing WBS."""
        email = f"wbs_test_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "WBSTest123!",
                "full_name": "WBS Tester",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WBSTest123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            headers=headers,
            json={
                "name": "WBS Test Program",
                "code": f"WBS-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        program_id = program_response.json()["id"]

        return {"headers": headers, "program_id": program_id}

    async def test_create_root_wbs(self, client: AsyncClient, auth_context: dict):
        """Should create root WBS element."""
        response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": auth_context["program_id"],
                "name": "Program Root",
                "wbs_code": "1",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["wbs_code"] == "1"
        assert data["name"] == "Program Root"
        assert data["level"] == 1

    async def test_create_child_wbs(self, client: AsyncClient, auth_context: dict):
        """Should create child WBS element."""
        # Create root first
        root_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": auth_context["program_id"],
                "name": "Root",
                "wbs_code": "1",
            },
        )
        root_id = root_response.json()["id"]

        # Create child
        child_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": auth_context["program_id"],
                "parent_id": root_id,
                "name": "Phase 1",
                "wbs_code": "1.1",
            },
        )
        assert child_response.status_code == 201
        data = child_response.json()
        assert data["wbs_code"] == "1.1"
        assert data["parent_id"] == root_id
        assert data["level"] == 2

    async def test_create_control_account(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should create control account WBS element."""
        response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": auth_context["program_id"],
                "name": "CA 1.1",
                "wbs_code": "1.1",
                "is_control_account": True,
                "budget_at_completion": "100000.00",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_control_account"] is True

    async def test_get_wbs_element(self, client: AsyncClient, auth_context: dict):
        """Should get WBS element by ID."""
        # Create element
        create_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": auth_context["program_id"],
                "name": "Test Element",
                "wbs_code": "1",
            },
        )
        wbs_id = create_response.json()["id"]

        # Get element
        get_response = await client.get(f"/api/v1/wbs/{wbs_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == wbs_id

    async def test_update_wbs_element(self, client: AsyncClient, auth_context: dict):
        """Should update WBS element."""
        # Create element
        create_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": auth_context["program_id"],
                "name": "Original Name",
                "wbs_code": "1",
            },
        )
        wbs_id = create_response.json()["id"]

        # Update element
        update_response = await client.patch(
            f"/api/v1/wbs/{wbs_id}",
            json={"name": "Updated Name", "description": "New description"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Name"
        assert update_response.json()["description"] == "New description"

    async def test_delete_wbs_element(self, client: AsyncClient, auth_context: dict):
        """Should delete WBS element."""
        # Create element
        create_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": auth_context["program_id"],
                "name": "To Delete",
                "wbs_code": "1",
            },
        )
        wbs_id = create_response.json()["id"]

        # Delete element
        delete_response = await client.delete(f"/api/v1/wbs/{wbs_id}")
        assert delete_response.status_code == 204

        # Verify deleted
        get_response = await client.get(f"/api/v1/wbs/{wbs_id}")
        assert get_response.status_code == 404

    async def test_get_wbs_tree(self, client: AsyncClient, auth_context: dict):
        """Should return WBS tree structure."""
        # Create hierarchy: 1 -> 1.1 -> 1.1.1
        root = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": auth_context["program_id"],
                "name": "Root",
                "wbs_code": "1",
            },
        )
        root_id = root.json()["id"]

        level2 = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": auth_context["program_id"],
                "parent_id": root_id,
                "name": "Level 2",
                "wbs_code": "1.1",
            },
        )
        level2_id = level2.json()["id"]

        await client.post(
            "/api/v1/wbs",
            json={
                "program_id": auth_context["program_id"],
                "parent_id": level2_id,
                "name": "Level 3",
                "wbs_code": "1.1.1",
            },
        )

        # Get tree
        tree_response = await client.get(
            f"/api/v1/wbs/tree?program_id={auth_context['program_id']}",
        )
        assert tree_response.status_code == 200

    async def test_get_nonexistent_wbs_returns_404(self, client: AsyncClient):
        """Should return 404 for nonexistent WBS element."""
        response = await client.get(f"/api/v1/wbs/{uuid4()}")
        assert response.status_code == 404

    async def test_create_wbs_with_nonexistent_program_returns_404(
        self, client: AsyncClient
    ):
        """Should return 404 when program doesn't exist."""
        response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": str(uuid4()),
                "name": "Test",
                "wbs_code": "1",
            },
        )
        assert response.status_code == 404

    async def test_create_wbs_with_nonexistent_parent_returns_404(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should return 404 when parent doesn't exist."""
        response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": auth_context["program_id"],
                "parent_id": str(uuid4()),
                "name": "Test",
                "wbs_code": "1.1",
            },
        )
        assert response.status_code == 404

    async def test_create_deep_hierarchy(self, client: AsyncClient, auth_context: dict):
        """Should create WBS elements with deep hierarchy."""
        # Create hierarchy 5 levels deep
        parent_id = None
        for level in range(1, 6):
            wbs_code = ".".join(["1"] * level)
            response = await client.post(
                "/api/v1/wbs",
                json={
                    "program_id": auth_context["program_id"],
                    "parent_id": parent_id,
                    "name": f"Level {level}",
                    "wbs_code": wbs_code,
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["level"] == level
            parent_id = data["id"]

    async def test_update_budget_at_completion(
        self, client: AsyncClient, auth_context: dict
    ):
        """Should update budget at completion."""
        # Create CA element
        create_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": auth_context["program_id"],
                "name": "Control Account",
                "wbs_code": "1",
                "is_control_account": True,
                "budget_at_completion": "50000.00",
            },
        )
        wbs_id = create_response.json()["id"]

        # Update budget
        update_response = await client.patch(
            f"/api/v1/wbs/{wbs_id}",
            json={"budget_at_completion": "75000.00"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["budget_at_completion"] == "75000.00"

    async def test_wbs_response_includes_timestamps(
        self, client: AsyncClient, auth_context: dict
    ):
        """WBS response should include created_at and updated_at."""
        response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": auth_context["program_id"],
                "name": "Test Element",
                "wbs_code": "1",
            },
        )
        data = response.json()
        assert "created_at" in data
        assert "updated_at" in data
