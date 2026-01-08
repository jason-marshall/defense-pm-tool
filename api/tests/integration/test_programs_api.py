"""Integration tests for Programs API."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestProgramsAPI:
    """Integration tests for /api/v1/programs endpoints."""

    async def test_list_programs_empty(self, client: AsyncClient):
        """Should return empty list when no programs exist."""
        response = await client.get("/api/v1/programs")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_create_program(self, client: AsyncClient, sample_program_data: dict):
        """Should create a new program."""
        response = await client.post("/api/v1/programs", json=sample_program_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_program_data["name"]
        assert data["code"] == sample_program_data["code"]
        assert "id" in data

    async def test_create_program_duplicate_code(
        self,
        client: AsyncClient,
        sample_program_data: dict,
    ):
        """Should reject duplicate program codes."""
        # Create first program
        await client.post("/api/v1/programs", json=sample_program_data)

        # Try to create second with same code
        response = await client.post("/api/v1/programs", json=sample_program_data)

        assert response.status_code == 409
        assert "DUPLICATE_PROGRAM_CODE" in response.json()["code"]

    async def test_get_program(self, client: AsyncClient, sample_program_data: dict):
        """Should retrieve a program by ID."""
        # Create program
        create_response = await client.post("/api/v1/programs", json=sample_program_data)
        program_id = create_response.json()["id"]

        # Get program
        response = await client.get(f"/api/v1/programs/{program_id}")

        assert response.status_code == 200
        assert response.json()["id"] == program_id

    async def test_get_program_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent program."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/programs/{fake_id}")

        assert response.status_code == 404

    async def test_update_program(self, client: AsyncClient, sample_program_data: dict):
        """Should update a program."""
        # Create program
        create_response = await client.post("/api/v1/programs", json=sample_program_data)
        program_id = create_response.json()["id"]

        # Update program
        update_data = {"name": "Updated Program Name"}
        response = await client.patch(
            f"/api/v1/programs/{program_id}",
            json=update_data,
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Program Name"

    async def test_delete_program(self, client: AsyncClient, sample_program_data: dict):
        """Should delete a program."""
        # Create program
        create_response = await client.post("/api/v1/programs", json=sample_program_data)
        program_id = create_response.json()["id"]

        # Delete program
        response = await client.delete(f"/api/v1/programs/{program_id}")

        assert response.status_code == 204

        # Verify deleted
        get_response = await client.get(f"/api/v1/programs/{program_id}")
        assert get_response.status_code == 404
