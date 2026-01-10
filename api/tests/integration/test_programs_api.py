"""Integration tests for Programs API with authentication."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestProgramsAPIAuth:
    """Tests for authentication requirements on program endpoints."""

    async def test_list_programs_requires_auth(self, client: AsyncClient):
        """Should return 401 when not authenticated."""
        response = await client.get("/api/v1/programs")
        assert response.status_code == 401

    async def test_create_program_requires_auth(
        self,
        client: AsyncClient,
        sample_program_data: dict,
    ):
        """Should return 401 when creating without auth."""
        response = await client.post("/api/v1/programs", json=sample_program_data)
        assert response.status_code == 401

    async def test_get_program_requires_auth(self, client: AsyncClient):
        """Should return 401 when getting without auth."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/programs/{fake_id}")
        assert response.status_code == 401

    async def test_update_program_requires_auth(self, client: AsyncClient):
        """Should return 401 when updating without auth."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.patch(
            f"/api/v1/programs/{fake_id}",
            json={"name": "Updated"},
        )
        assert response.status_code == 401

    async def test_delete_program_requires_auth(self, client: AsyncClient):
        """Should return 401 when deleting without auth."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.delete(f"/api/v1/programs/{fake_id}")
        assert response.status_code == 401


class TestProgramsAPICRUD:
    """Tests for authenticated program CRUD operations."""

    async def test_list_programs_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should return empty list when no programs exist."""
        response = await client.get("/api/v1/programs", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_create_program(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_program_data: dict,
    ):
        """Should create a new program with current user as owner."""
        response = await client.post(
            "/api/v1/programs",
            json=sample_program_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_program_data["name"]
        assert data["code"] == sample_program_data["code"]
        assert "id" in data
        assert "owner_id" in data  # Owner should be set

    async def test_create_program_duplicate_code(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_program_data: dict,
    ):
        """Should reject duplicate program codes."""
        # Create first program
        await client.post(
            "/api/v1/programs",
            json=sample_program_data,
            headers=auth_headers,
        )

        # Try to create second with same code
        response = await client.post(
            "/api/v1/programs",
            json=sample_program_data,
            headers=auth_headers,
        )

        assert response.status_code == 409
        assert "DUPLICATE_PROGRAM_CODE" in response.json()["code"]

    async def test_get_program(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_program_data: dict,
    ):
        """Should retrieve a program by ID."""
        # Create program
        create_response = await client.post(
            "/api/v1/programs",
            json=sample_program_data,
            headers=auth_headers,
        )
        program_id = create_response.json()["id"]

        # Get program
        response = await client.get(
            f"/api/v1/programs/{program_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["id"] == program_id

    async def test_get_program_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should return 404 for non-existent program."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(
            f"/api/v1/programs/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_update_program(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_program_data: dict,
    ):
        """Should update a program owned by current user."""
        # Create program
        create_response = await client.post(
            "/api/v1/programs",
            json=sample_program_data,
            headers=auth_headers,
        )
        program_id = create_response.json()["id"]

        # Update program
        update_data = {"name": "Updated Program Name"}
        response = await client.patch(
            f"/api/v1/programs/{program_id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Program Name"

    async def test_delete_program(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_program_data: dict,
    ):
        """Should delete a program owned by current user."""
        # Create program
        create_response = await client.post(
            "/api/v1/programs",
            json=sample_program_data,
            headers=auth_headers,
        )
        program_id = create_response.json()["id"]

        # Delete program
        response = await client.delete(
            f"/api/v1/programs/{program_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify deleted (soft delete - should return 404)
        get_response = await client.get(
            f"/api/v1/programs/{program_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    async def test_list_programs_shows_owned(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_program_data: dict,
    ):
        """Should list programs owned by current user."""
        # Create program
        await client.post(
            "/api/v1/programs",
            json=sample_program_data,
            headers=auth_headers,
        )

        # List programs
        response = await client.get("/api/v1/programs", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["code"] == sample_program_data["code"]


class TestProgramsAPIAuthorization:
    """Tests for authorization (ownership) checks."""

    async def test_cannot_access_other_users_program(
        self,
        client: AsyncClient,
        sample_program_data: dict,
    ):
        """User should not be able to access another user's program."""
        # Create first user and their program
        user1_data = {
            "email": "user1@example.com",
            "password": "Password123!",
            "full_name": "User One",
        }
        await client.post("/api/v1/auth/register", json=user1_data)
        login1 = await client.post(
            "/api/v1/auth/login",
            json={"email": user1_data["email"], "password": user1_data["password"]},
        )
        token1 = login1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Create program as user1
        create_response = await client.post(
            "/api/v1/programs",
            json=sample_program_data,
            headers=headers1,
        )
        program_id = create_response.json()["id"]

        # Create second user
        user2_data = {
            "email": "user2@example.com",
            "password": "Password123!",
            "full_name": "User Two",
        }
        await client.post("/api/v1/auth/register", json=user2_data)
        login2 = await client.post(
            "/api/v1/auth/login",
            json={"email": user2_data["email"], "password": user2_data["password"]},
        )
        token2 = login2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # User2 tries to access User1's program
        response = await client.get(
            f"/api/v1/programs/{program_id}",
            headers=headers2,
        )

        assert response.status_code == 403
        assert "PROGRAM_ACCESS_DENIED" in response.json()["code"]

    async def test_cannot_update_other_users_program(
        self,
        client: AsyncClient,
        sample_program_data: dict,
    ):
        """User should not be able to update another user's program."""
        # Create first user and their program
        user1_data = {
            "email": "owner@example.com",
            "password": "Password123!",
            "full_name": "Owner",
        }
        await client.post("/api/v1/auth/register", json=user1_data)
        login1 = await client.post(
            "/api/v1/auth/login",
            json={"email": user1_data["email"], "password": user1_data["password"]},
        )
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

        create_response = await client.post(
            "/api/v1/programs",
            json=sample_program_data,
            headers=headers1,
        )
        program_id = create_response.json()["id"]

        # Create second user
        user2_data = {
            "email": "other@example.com",
            "password": "Password123!",
            "full_name": "Other User",
        }
        await client.post("/api/v1/auth/register", json=user2_data)
        login2 = await client.post(
            "/api/v1/auth/login",
            json={"email": user2_data["email"], "password": user2_data["password"]},
        )
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        # User2 tries to update User1's program
        response = await client.patch(
            f"/api/v1/programs/{program_id}",
            json={"name": "Hacked!"},
            headers=headers2,
        )

        assert response.status_code == 403
        assert "PROGRAM_MODIFICATION_DENIED" in response.json()["code"]

    async def test_cannot_delete_other_users_program(
        self,
        client: AsyncClient,
        sample_program_data: dict,
    ):
        """User should not be able to delete another user's program."""
        # Create first user and their program
        user1_data = {
            "email": "delowner@example.com",
            "password": "Password123!",
            "full_name": "Delete Owner",
        }
        await client.post("/api/v1/auth/register", json=user1_data)
        login1 = await client.post(
            "/api/v1/auth/login",
            json={"email": user1_data["email"], "password": user1_data["password"]},
        )
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

        create_response = await client.post(
            "/api/v1/programs",
            json=sample_program_data,
            headers=headers1,
        )
        program_id = create_response.json()["id"]

        # Create second user
        user2_data = {
            "email": "delother@example.com",
            "password": "Password123!",
            "full_name": "Delete Other",
        }
        await client.post("/api/v1/auth/register", json=user2_data)
        login2 = await client.post(
            "/api/v1/auth/login",
            json={"email": user2_data["email"], "password": user2_data["password"]},
        )
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        # User2 tries to delete User1's program
        response = await client.delete(
            f"/api/v1/programs/{program_id}",
            headers=headers2,
        )

        assert response.status_code == 403
        assert "PROGRAM_DELETION_DENIED" in response.json()["code"]

    async def test_user_list_only_shows_own_programs(
        self,
        client: AsyncClient,
        sample_program_data: dict,
    ):
        """User should only see their own programs in the list."""
        # Create first user and their program
        user1_data = {
            "email": "listuser1@example.com",
            "password": "Password123!",
            "full_name": "List User 1",
        }
        await client.post("/api/v1/auth/register", json=user1_data)
        login1 = await client.post(
            "/api/v1/auth/login",
            json={"email": user1_data["email"], "password": user1_data["password"]},
        )
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

        await client.post(
            "/api/v1/programs",
            json=sample_program_data,
            headers=headers1,
        )

        # Create second user
        user2_data = {
            "email": "listuser2@example.com",
            "password": "Password123!",
            "full_name": "List User 2",
        }
        await client.post("/api/v1/auth/register", json=user2_data)
        login2 = await client.post(
            "/api/v1/auth/login",
            json={"email": user2_data["email"], "password": user2_data["password"]},
        )
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        # User2 lists programs - should see empty list
        response = await client.get("/api/v1/programs", headers=headers2)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0
