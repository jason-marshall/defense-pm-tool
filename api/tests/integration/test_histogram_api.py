"""Integration tests for resource histogram API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import AsyncClient  # noqa: TC002

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def program_with_resources(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> dict:
    """Create a program with resources and activities for histogram testing."""
    # Create program
    program_response = await client.post(
        "/api/v1/programs",
        headers=auth_headers,
        json={
            "code": "HIST-TEST",
            "name": "Histogram Test Program",
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

    # Create resources
    resource1_response = await client.post(
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
    assert resource1_response.status_code == 201
    resource1 = resource1_response.json()

    resource2_response = await client.post(
        "/api/v1/resources",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "code": "ENG-002",
            "name": "Engineer 2",
            "resource_type": "labor",
            "capacity_per_day": "8.0",
            "cost_rate": "100.00",
        },
    )
    assert resource2_response.status_code == 201
    resource2 = resource2_response.json()

    # Create activity
    activity_response = await client.post(
        "/api/v1/activities",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "wbs_id": wbs_id,
            "code": "ACT-001",
            "name": "Test Activity",
            "planned_start": "2024-01-15",
            "planned_finish": "2024-01-19",
            "duration": 5,
        },
    )
    assert activity_response.status_code == 201
    activity = activity_response.json()

    # Create assignment
    assign_response = await client.post(
        f"/api/v1/resources/{resource1['id']}/assignments",
        headers=auth_headers,
        json={
            "activity_id": activity["id"],
            "resource_id": resource1["id"],
            "units": "1.0",
        },
    )
    assert assign_response.status_code == 201

    return {
        "program_id": program_id,
        "resource1_id": resource1["id"],
        "resource2_id": resource2["id"],
        "activity_id": activity["id"],
    }


class TestGetResourceHistogram:
    """Tests for GET /resources/{id}/histogram endpoint."""

    @pytest.mark.asyncio
    async def test_get_resource_histogram(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        program_with_resources: dict,
    ) -> None:
        """Should return histogram data for resource."""
        resource_id = program_with_resources["resource1_id"]

        response = await client.get(
            f"/api/v1/resources/{resource_id}/histogram",
            headers=auth_headers,
            params={
                "start_date": "2024-01-15",
                "end_date": "2024-01-19",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["resource_id"] == resource_id
        assert data["resource_code"] == "ENG-001"
        assert "data_points" in data
        assert len(data["data_points"]) == 5
        assert "peak_utilization" in data
        assert "average_utilization" in data
        assert "overallocated_days" in data

    @pytest.mark.asyncio
    async def test_get_resource_histogram_weekly(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        program_with_resources: dict,
    ) -> None:
        """Should return weekly aggregated histogram."""
        resource_id = program_with_resources["resource1_id"]

        response = await client.get(
            f"/api/v1/resources/{resource_id}/histogram",
            headers=auth_headers,
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "granularity": "weekly",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Weekly should have fewer data points than daily
        assert len(data["data_points"]) < 31

    @pytest.mark.asyncio
    async def test_resource_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent resource."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await client.get(
            f"/api/v1/resources/{fake_id}/histogram",
            headers=auth_headers,
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_date_range(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        program_with_resources: dict,
    ) -> None:
        """Should return 400 for invalid date range."""
        resource_id = program_with_resources["resource1_id"]

        response = await client.get(
            f"/api/v1/resources/{resource_id}/histogram",
            headers=auth_headers,
            params={
                "start_date": "2024-01-31",
                "end_date": "2024-01-01",  # End before start
            },
        )

        assert response.status_code == 400


class TestGetProgramHistogram:
    """Tests for GET /programs/{id}/histogram endpoint."""

    @pytest.mark.asyncio
    async def test_get_program_histogram(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        program_with_resources: dict,
    ) -> None:
        """Should return histogram data for all program resources."""
        program_id = program_with_resources["program_id"]

        response = await client.get(
            f"/api/v1/programs/{program_id}/histogram",
            headers=auth_headers,
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "summary" in data
        assert "histograms" in data
        assert data["summary"]["program_id"] == program_id
        assert data["summary"]["resource_count"] == 2
        assert len(data["histograms"]) == 2

    @pytest.mark.asyncio
    async def test_program_histogram_with_filter(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        program_with_resources: dict,
    ) -> None:
        """Should filter to specific resources."""
        program_id = program_with_resources["program_id"]
        resource1_id = program_with_resources["resource1_id"]

        response = await client.get(
            f"/api/v1/programs/{program_id}/histogram",
            headers=auth_headers,
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "resource_ids": [resource1_id],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["summary"]["resource_count"] == 1
        assert len(data["histograms"]) == 1
        assert data["histograms"][0]["resource_id"] == resource1_id

    @pytest.mark.asyncio
    async def test_program_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent program."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await client.get(
            f"/api/v1/programs/{fake_id}/histogram",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_program_histogram_default_dates(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        program_with_resources: dict,
    ) -> None:
        """Should use program dates when not specified."""
        program_id = program_with_resources["program_id"]

        response = await client.get(
            f"/api/v1/programs/{program_id}/histogram",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should use program's date range
        assert data["summary"]["start_date"] == "2024-01-01"
        assert data["summary"]["end_date"] == "2024-12-31"
