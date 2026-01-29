"""Integration tests for resource leveling API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import AsyncClient  # noqa: TC002

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def program_with_overallocation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> dict:
    """Create a program with activities that cause over-allocation."""
    # Create program
    program_response = await client.post(
        "/api/v1/programs",
        headers=auth_headers,
        json={
            "code": "LEVEL-TEST",
            "name": "Leveling Test Program",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
        },
    )
    assert program_response.status_code == 201
    program = program_response.json()
    program_id = program["id"]

    # Create WBS element
    wbs_response = await client.post(
        "/api/v1/wbs",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "wbs_code": "1.0",
            "name": "Project Root",
        },
    )
    assert wbs_response.status_code == 201
    wbs = wbs_response.json()
    wbs_id = wbs["id"]

    # Create resource
    resource_response = await client.post(
        "/api/v1/resources",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "code": "ENG-001",
            "name": "Engineer 1",
            "resource_type": "labor",
            "capacity_per_day": "8.0",
            "cost_rate": "100.00",
        },
    )
    assert resource_response.status_code == 201
    resource = resource_response.json()
    resource_id = resource["id"]

    # Create two overlapping activities
    activity1_response = await client.post(
        "/api/v1/activities",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "wbs_id": wbs_id,
            "code": "ACT-001",
            "name": "Activity 1",
            "planned_start": "2024-01-15",
            "planned_finish": "2024-01-19",
            "duration": 5,
        },
    )
    assert activity1_response.status_code == 201
    activity1 = activity1_response.json()

    activity2_response = await client.post(
        "/api/v1/activities",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "wbs_id": wbs_id,
            "code": "ACT-002",
            "name": "Activity 2",
            "planned_start": "2024-01-15",
            "planned_finish": "2024-01-19",
            "duration": 5,
        },
    )
    assert activity2_response.status_code == 201
    activity2 = activity2_response.json()

    # Assign same resource to both activities (causes over-allocation)
    assign1_response = await client.post(
        f"/api/v1/resources/{resource_id}/assignments",
        headers=auth_headers,
        json={
            "activity_id": activity1["id"],
            "resource_id": resource_id,
            "units": "1.0",
        },
    )
    assert assign1_response.status_code == 201

    assign2_response = await client.post(
        f"/api/v1/resources/{resource_id}/assignments",
        headers=auth_headers,
        json={
            "activity_id": activity2["id"],
            "resource_id": resource_id,
            "units": "1.0",
        },
    )
    assert assign2_response.status_code == 201

    return {
        "program_id": program_id,
        "resource_id": resource_id,
        "activity1_id": activity1["id"],
        "activity2_id": activity2["id"],
    }


class TestLevelProgramEndpoint:
    """Tests for POST /programs/{id}/level endpoint."""

    @pytest.mark.asyncio
    async def test_level_program_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        program_with_overallocation: dict,
    ) -> None:
        """Should return leveling result for program."""
        program_id = program_with_overallocation["program_id"]

        response = await client.post(
            f"/api/v1/programs/{program_id}/level",
            headers=auth_headers,
            json={
                "preserve_critical_path": True,
                "max_iterations": 100,
                "level_within_float": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["program_id"] == program_id
        assert "success" in data
        assert "iterations_used" in data
        assert "activities_shifted" in data
        assert "shifts" in data
        assert "remaining_overallocations" in data
        assert "new_project_finish" in data
        assert "original_project_finish" in data
        assert "schedule_extension_days" in data
        assert "warnings" in data

    @pytest.mark.asyncio
    async def test_level_program_with_options(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        program_with_overallocation: dict,
    ) -> None:
        """Should respect leveling options."""
        program_id = program_with_overallocation["program_id"]
        resource_id = program_with_overallocation["resource_id"]

        response = await client.post(
            f"/api/v1/programs/{program_id}/level",
            headers=auth_headers,
            json={
                "preserve_critical_path": False,
                "max_iterations": 50,
                "target_resources": [resource_id],
                "level_within_float": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should have processed the leveling
        assert data["iterations_used"] <= 50

    @pytest.mark.asyncio
    async def test_level_program_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent program."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await client.post(
            f"/api/v1/programs/{fake_id}/level",
            headers=auth_headers,
            json={"preserve_critical_path": True},
        )

        assert response.status_code == 404
        assert "Program not found" in response.json()["detail"]


class TestPreviewLevelingEndpoint:
    """Tests for GET /programs/{id}/level/preview endpoint."""

    @pytest.mark.asyncio
    async def test_preview_leveling(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        program_with_overallocation: dict,
    ) -> None:
        """Should preview leveling via GET request."""
        program_id = program_with_overallocation["program_id"]

        response = await client.get(
            f"/api/v1/programs/{program_id}/level/preview",
            headers=auth_headers,
            params={
                "preserve_critical_path": True,
                "level_within_float": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["program_id"] == program_id
        assert "shifts" in data

    @pytest.mark.asyncio
    async def test_preview_with_target_resources(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        program_with_overallocation: dict,
    ) -> None:
        """Should accept target_resources query param."""
        program_id = program_with_overallocation["program_id"]
        resource_id = program_with_overallocation["resource_id"]

        response = await client.get(
            f"/api/v1/programs/{program_id}/level/preview",
            headers=auth_headers,
            params={
                "target_resources": [resource_id],
            },
        )

        assert response.status_code == 200


class TestApplyLevelingEndpoint:
    """Tests for POST /programs/{id}/level/apply endpoint."""

    @pytest.mark.asyncio
    async def test_apply_shifts(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        program_with_overallocation: dict,
    ) -> None:
        """Should apply selected shifts to activities."""
        program_id = program_with_overallocation["program_id"]

        # First run leveling to get shifts
        level_response = await client.post(
            f"/api/v1/programs/{program_id}/level",
            headers=auth_headers,
            json={"level_within_float": False},
        )
        assert level_response.status_code == 200
        level_data = level_response.json()

        # Get activity IDs that were shifted
        shifted_ids = [s["activity_id"] for s in level_data["shifts"]]

        if shifted_ids:
            # Apply the shifts
            apply_response = await client.post(
                f"/api/v1/programs/{program_id}/level/apply",
                headers=auth_headers,
                json={"shifts": shifted_ids},
            )

            assert apply_response.status_code == 200
            apply_data = apply_response.json()

            # Note: applied_count may vary since apply re-runs leveling
            assert "applied_count" in apply_data
            assert "skipped_count" in apply_data
            assert "new_project_finish" in apply_data

    @pytest.mark.asyncio
    async def test_apply_partial_shifts(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        program_with_overallocation: dict,
    ) -> None:
        """Should apply only selected shifts."""
        program_id = program_with_overallocation["program_id"]

        # First run leveling
        level_response = await client.post(
            f"/api/v1/programs/{program_id}/level",
            headers=auth_headers,
            json={"level_within_float": False},
        )
        level_data = level_response.json()

        # Apply only first shift if any exist
        shifted_ids = [s["activity_id"] for s in level_data["shifts"]]

        if len(shifted_ids) >= 2:
            # Apply only first one
            apply_response = await client.post(
                f"/api/v1/programs/{program_id}/level/apply",
                headers=auth_headers,
                json={"shifts": [shifted_ids[0]]},
            )

            assert apply_response.status_code == 200
            apply_data = apply_response.json()

            assert apply_data["applied_count"] == 1

    @pytest.mark.asyncio
    async def test_apply_nonexistent_shift(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        program_with_overallocation: dict,
    ) -> None:
        """Should skip nonexistent activity IDs."""
        program_id = program_with_overallocation["program_id"]
        fake_id = "00000000-0000-0000-0000-000000000000"

        apply_response = await client.post(
            f"/api/v1/programs/{program_id}/level/apply",
            headers=auth_headers,
            json={"shifts": [fake_id]},
        )

        assert apply_response.status_code == 200
        apply_data = apply_response.json()

        # Should skip the nonexistent shift
        assert apply_data["skipped_count"] == 1
        assert apply_data["applied_count"] == 0
