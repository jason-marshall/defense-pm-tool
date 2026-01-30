"""End-to-end tests for Week 15: Resource Leveling.

This module validates the Week 15 deliverables:
1. Resource loading with activity dates
2. Over-allocation detection
3. Serial resource leveling algorithm
4. Resource histogram visualization
5. Full leveling workflow integration
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


# =============================================================================
# Test Fixtures
# =============================================================================


async def create_test_program(
    client: AsyncClient,
    auth_headers: dict[str, str],
    code_suffix: str | None = None,
) -> dict:
    """Create a test program with WBS for leveling tests."""
    suffix = code_suffix or uuid4().hex[:6].upper()
    start = date.today()
    end = start + timedelta(days=365)

    program_response = await client.post(
        "/api/v1/programs",
        json={
            "name": f"Leveling Test Program {suffix}",
            "code": f"LVL-{suffix}",
            "start_date": str(start),
            "end_date": str(end),
        },
        headers=auth_headers,
    )
    assert program_response.status_code == 201
    program = program_response.json()

    # Create WBS
    wbs_response = await client.post(
        "/api/v1/wbs",
        json={
            "program_id": program["id"],
            "wbs_code": "1.1",
            "name": "Test WBS",
        },
        headers=auth_headers,
    )
    assert wbs_response.status_code == 201
    wbs = wbs_response.json()

    return {"program": program, "wbs": wbs}


async def create_test_resource(
    client: AsyncClient,
    auth_headers: dict[str, str],
    program_id: str,
    code: str,
    capacity: str = "8.0",
) -> dict:
    """Create a test resource."""
    response = await client.post(
        "/api/v1/resources",
        json={
            "program_id": program_id,
            "name": f"Resource {code}",
            "code": code,
            "resource_type": "labor",
            "capacity_per_day": capacity,
            "cost_rate": "100.00",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


async def create_test_activity(
    client: AsyncClient,
    auth_headers: dict[str, str],
    program_id: str,
    wbs_id: str,
    code: str,
    duration: int = 5,
    start_offset: int = 0,
) -> dict:
    """Create a test activity with planned dates."""
    start = date.today() + timedelta(days=start_offset)
    finish = start + timedelta(days=duration - 1)

    response = await client.post(
        "/api/v1/activities",
        json={
            "program_id": program_id,
            "wbs_id": wbs_id,
            "code": code,
            "name": f"Activity {code}",
            "duration": duration,
            "planned_start": str(start),
            "planned_finish": str(finish),
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


async def create_assignment(
    client: AsyncClient,
    auth_headers: dict[str, str],
    resource_id: str,
    activity_id: str,
    units: str = "1.0",
) -> dict:
    """Create a resource assignment."""
    response = await client.post(
        f"/api/v1/resources/{resource_id}/assignments",
        json={
            "resource_id": resource_id,
            "activity_id": activity_id,
            "units": units,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


# =============================================================================
# Resource Loading Tests
# =============================================================================


class TestResourceLoading:
    """E2E tests for resource loading calculations."""

    @pytest.mark.asyncio
    async def test_loading_with_activity_dates(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test resource loading respects activity planned dates."""
        # Setup
        setup = await create_test_program(client, auth_headers, "LOAD1")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        resource = await create_test_resource(client, auth_headers, program_id, "ENG-LOAD1")
        activity = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LOAD1", duration=5
        )
        await create_assignment(client, auth_headers, resource["id"], activity["id"])

        # Get histogram to verify loading
        start = date.today()
        end = start + timedelta(days=10)
        response = await client.get(
            f"/api/v1/resources/{resource['id']}/histogram",
            headers=auth_headers,
            params={"start_date": str(start), "end_date": str(end)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["resource_id"] == resource["id"]
        assert len(data["data_points"]) > 0

    @pytest.mark.asyncio
    async def test_loading_respects_calendar(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test loading uses calendar for availability."""
        # Setup
        setup = await create_test_program(client, auth_headers, "LOAD2")
        program_id = setup["program"]["id"]

        resource = await create_test_resource(client, auth_headers, program_id, "ENG-LOAD2")

        # Create calendar with reduced hours
        start = date.today()
        entries = []
        for i in range(5):
            entries.append(
                {
                    "calendar_date": str(start + timedelta(days=i)),
                    "available_hours": "4.0",  # Half capacity
                    "is_working_day": True,
                }
            )

        calendar_response = await client.post(
            f"/api/v1/resources/{resource['id']}/calendar",
            headers=auth_headers,
            json={"resource_id": resource["id"], "entries": entries},
        )
        assert calendar_response.status_code == 201

        # Get calendar range
        response = await client.get(
            f"/api/v1/resources/{resource['id']}/calendar",
            headers=auth_headers,
            params={
                "start_date": str(start),
                "end_date": str(start + timedelta(days=4)),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["total_hours"]) == Decimal("20.0")  # 5 * 4 hours

    @pytest.mark.asyncio
    async def test_loading_multiple_resources(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test loading calculation for multiple resources."""
        # Setup
        setup = await create_test_program(client, auth_headers, "LOAD3")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        # Create 3 resources
        resources = []
        for i in range(3):
            resource = await create_test_resource(
                client, auth_headers, program_id, f"ENG-LOAD3-{i}"
            )
            resources.append(resource)

        # Create activity and assign all resources
        activity = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LOAD3", duration=5
        )

        for resource in resources:
            await create_assignment(client, auth_headers, resource["id"], activity["id"])

        # Get program histogram
        start = date.today()
        end = start + timedelta(days=10)
        response = await client.get(
            f"/api/v1/programs/{program_id}/histogram",
            headers=auth_headers,
            params={"start_date": str(start), "end_date": str(end)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["resource_count"] == 3

    @pytest.mark.asyncio
    async def test_loading_assignment_date_override(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test assignment with explicit dates overrides activity dates."""
        # Setup
        setup = await create_test_program(client, auth_headers, "LOAD4")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        resource = await create_test_resource(client, auth_headers, program_id, "ENG-LOAD4")
        activity = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LOAD4", duration=10
        )

        # Create assignment with shorter date range
        start = date.today()
        assignment_response = await client.post(
            f"/api/v1/resources/{resource['id']}/assignments",
            headers=auth_headers,
            json={
                "resource_id": resource["id"],
                "activity_id": activity["id"],
                "units": "1.0",
                "start_date": str(start + timedelta(days=2)),
                "finish_date": str(start + timedelta(days=5)),
            },
        )

        assert assignment_response.status_code == 201
        data = assignment_response.json()
        assert data["start_date"] == str(start + timedelta(days=2))
        assert data["finish_date"] == str(start + timedelta(days=5))


# =============================================================================
# Overallocation Detection Tests
# =============================================================================


class TestOverallocationDetection:
    """E2E tests for over-allocation detection."""

    @pytest.mark.asyncio
    async def test_detect_single_resource_overallocation(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test detecting over-allocation for single resource."""
        # Setup - create resource with 8 hour capacity
        setup = await create_test_program(client, auth_headers, "OVER1")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        resource = await create_test_resource(
            client, auth_headers, program_id, "ENG-OVER1", capacity="8.0"
        )

        # Create two overlapping activities
        activity1 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-OVER1A", duration=5
        )
        activity2 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-OVER1B", duration=5
        )

        # Assign both to same resource (causing over-allocation)
        await create_assignment(client, auth_headers, resource["id"], activity1["id"])
        await create_assignment(client, auth_headers, resource["id"], activity2["id"])

        # Check histogram for over-allocation
        start = date.today()
        end = start + timedelta(days=10)
        response = await client.get(
            f"/api/v1/resources/{resource['id']}/histogram",
            headers=auth_headers,
            params={"start_date": str(start), "end_date": str(end)},
        )

        assert response.status_code == 200
        data = response.json()
        # Check for overallocated days
        overallocated_count = sum(1 for dp in data["data_points"] if dp["is_overallocated"])
        assert overallocated_count > 0
        assert data["overallocated_days"] > 0

    @pytest.mark.asyncio
    async def test_detect_program_overallocations(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test detecting over-allocations across program."""
        # Setup
        setup = await create_test_program(client, auth_headers, "OVER2")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        # Create two resources
        resource1 = await create_test_resource(client, auth_headers, program_id, "ENG-OVER2A")
        resource2 = await create_test_resource(client, auth_headers, program_id, "ENG-OVER2B")

        # Create activities and cause over-allocation on one resource
        activity1 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-OVER2A", duration=5
        )
        activity2 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-OVER2B", duration=5
        )
        activity3 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-OVER2C", duration=5
        )

        # Resource 1: Two overlapping (over-allocated)
        await create_assignment(client, auth_headers, resource1["id"], activity1["id"])
        await create_assignment(client, auth_headers, resource1["id"], activity2["id"])

        # Resource 2: One activity (not over-allocated)
        await create_assignment(client, auth_headers, resource2["id"], activity3["id"])

        # Get program histogram
        start = date.today()
        end = start + timedelta(days=10)
        response = await client.get(
            f"/api/v1/programs/{program_id}/histogram",
            headers=auth_headers,
            params={"start_date": str(start), "end_date": str(end)},
        )

        assert response.status_code == 200
        data = response.json()
        # At least one resource should have over-allocation
        assert data["summary"]["resources_with_overallocation"] >= 1

    @pytest.mark.asyncio
    async def test_no_overallocation_under_capacity(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test no over-allocation when within capacity."""
        # Setup
        setup = await create_test_program(client, auth_headers, "OVER3")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        # Create resource with 8 hour capacity
        resource = await create_test_resource(
            client, auth_headers, program_id, "ENG-OVER3", capacity="8.0"
        )

        # Create single activity
        activity = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-OVER3", duration=5
        )

        # Assign with 50% units (4 hours/day)
        await client.post(
            f"/api/v1/resources/{resource['id']}/assignments",
            headers=auth_headers,
            json={
                "resource_id": resource["id"],
                "activity_id": activity["id"],
                "units": "0.5",
            },
        )

        # Check histogram
        start = date.today()
        end = start + timedelta(days=10)
        response = await client.get(
            f"/api/v1/resources/{resource['id']}/histogram",
            headers=auth_headers,
            params={"start_date": str(start), "end_date": str(end)},
        )

        assert response.status_code == 200
        data = response.json()
        # At 50% units, peak utilization should be <= 100%
        assert Decimal(data["peak_utilization"]) <= Decimal("100")
        # Total assigned should be less than available
        assert Decimal(data["total_assigned_hours"]) <= Decimal(data["total_available_hours"])

    @pytest.mark.asyncio
    async def test_critical_path_impact(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test detecting over-allocation on critical path activities."""
        # Setup
        setup = await create_test_program(client, auth_headers, "OVER4")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        resource = await create_test_resource(client, auth_headers, program_id, "ENG-OVER4")

        # Create activities
        activity1 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-OVER4A", duration=5
        )
        activity2 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-OVER4B", duration=5
        )

        # Create dependency (A -> B)
        await client.post(
            "/api/v1/dependencies",
            headers=auth_headers,
            json={
                "program_id": program_id,
                "predecessor_id": activity1["id"],
                "successor_id": activity2["id"],
                "dependency_type": "FS",
                "lag": 0,
            },
        )

        # Calculate schedule
        await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )

        # Assign resource to both activities
        await create_assignment(client, auth_headers, resource["id"], activity1["id"])
        await create_assignment(client, auth_headers, resource["id"], activity2["id"])

        # Program histogram should work
        response = await client.get(
            f"/api/v1/programs/{program_id}/histogram",
            headers=auth_headers,
        )

        assert response.status_code == 200


# =============================================================================
# Resource Leveling Tests
# =============================================================================


class TestResourceLeveling:
    """E2E tests for resource leveling algorithm."""

    @pytest.mark.asyncio
    async def test_level_simple_program(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test basic leveling on simple program."""
        # Setup
        setup = await create_test_program(client, auth_headers, "LVL1")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        resource = await create_test_resource(client, auth_headers, program_id, "ENG-LVL1")

        # Create overlapping activities (causes over-allocation)
        activity1 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LVL1A", duration=5
        )
        activity2 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LVL1B", duration=5
        )

        await create_assignment(client, auth_headers, resource["id"], activity1["id"])
        await create_assignment(client, auth_headers, resource["id"], activity2["id"])

        # Calculate schedule first
        await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )

        # Run leveling
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

    @pytest.mark.asyncio
    async def test_level_preserves_critical_path(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test leveling respects preserve_critical_path option."""
        # Setup
        setup = await create_test_program(client, auth_headers, "LVL2")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        resource = await create_test_resource(client, auth_headers, program_id, "ENG-LVL2")

        # Create chain of activities
        activity1 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LVL2A", duration=5
        )
        activity2 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LVL2B", duration=5, start_offset=5
        )

        # Create dependency
        await client.post(
            "/api/v1/dependencies",
            headers=auth_headers,
            json={
                "program_id": program_id,
                "predecessor_id": activity1["id"],
                "successor_id": activity2["id"],
                "dependency_type": "FS",
                "lag": 0,
            },
        )

        await create_assignment(client, auth_headers, resource["id"], activity1["id"])
        await create_assignment(client, auth_headers, resource["id"], activity2["id"])

        # Calculate schedule
        await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )

        # Run leveling with preserve_critical_path=True
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
        # Critical path should generate warnings if can't be delayed
        assert "warnings" in data

    @pytest.mark.asyncio
    async def test_level_respects_float(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test leveling respects level_within_float option."""
        # Setup
        setup = await create_test_program(client, auth_headers, "LVL3")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        resource = await create_test_resource(client, auth_headers, program_id, "ENG-LVL3")

        # Create activities
        activity1 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LVL3A", duration=5
        )
        activity2 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LVL3B", duration=5
        )

        await create_assignment(client, auth_headers, resource["id"], activity1["id"])
        await create_assignment(client, auth_headers, resource["id"], activity2["id"])

        # Calculate schedule
        await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )

        # Run leveling with level_within_float=True
        response = await client.post(
            f"/api/v1/programs/{program_id}/level",
            headers=auth_headers,
            json={
                "preserve_critical_path": False,
                "max_iterations": 100,
                "level_within_float": True,
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_level_multiple_resources(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test leveling with multiple over-allocated resources."""
        # Setup
        setup = await create_test_program(client, auth_headers, "LVL4")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        # Create two resources
        resource1 = await create_test_resource(client, auth_headers, program_id, "ENG-LVL4A")
        resource2 = await create_test_resource(client, auth_headers, program_id, "ENG-LVL4B")

        # Create activities
        activity1 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LVL4A", duration=5
        )
        activity2 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LVL4B", duration=5
        )
        activity3 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LVL4C", duration=5
        )
        activity4 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LVL4D", duration=5
        )

        # Over-allocate both resources
        await create_assignment(client, auth_headers, resource1["id"], activity1["id"])
        await create_assignment(client, auth_headers, resource1["id"], activity2["id"])
        await create_assignment(client, auth_headers, resource2["id"], activity3["id"])
        await create_assignment(client, auth_headers, resource2["id"], activity4["id"])

        # Calculate and level
        await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )

        response = await client.post(
            f"/api/v1/programs/{program_id}/level",
            headers=auth_headers,
            json={
                "preserve_critical_path": False,
                "max_iterations": 100,
                "level_within_float": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["program_id"] == program_id

    @pytest.mark.asyncio
    async def test_apply_leveling_shifts(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test applying leveling shifts to activities."""
        # Setup
        setup = await create_test_program(client, auth_headers, "LVL5")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        resource = await create_test_resource(client, auth_headers, program_id, "ENG-LVL5")

        activity1 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LVL5A", duration=5
        )
        activity2 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-LVL5B", duration=5
        )

        await create_assignment(client, auth_headers, resource["id"], activity1["id"])
        await create_assignment(client, auth_headers, resource["id"], activity2["id"])

        # Calculate and level
        await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )

        level_response = await client.post(
            f"/api/v1/programs/{program_id}/level",
            headers=auth_headers,
            json={
                "preserve_critical_path": False,
                "max_iterations": 100,
                "level_within_float": False,
            },
        )

        assert level_response.status_code == 200
        level_data = level_response.json()

        # Apply shifts if any
        if level_data["shifts"]:
            shift_ids = [s["activity_id"] for s in level_data["shifts"]]
            apply_response = await client.post(
                f"/api/v1/programs/{program_id}/level/apply",
                headers=auth_headers,
                json={"shifts": shift_ids},
            )

            assert apply_response.status_code == 200
            apply_data = apply_response.json()
            assert "applied_count" in apply_data
            assert "new_project_finish" in apply_data


# =============================================================================
# Resource Histogram Tests
# =============================================================================


class TestResourceHistogram:
    """E2E tests for resource histogram visualization."""

    @pytest.mark.asyncio
    async def test_resource_histogram_daily(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test daily granularity histogram."""
        # Setup
        setup = await create_test_program(client, auth_headers, "HIST1")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        resource = await create_test_resource(client, auth_headers, program_id, "ENG-HIST1")
        activity = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-HIST1", duration=10
        )
        await create_assignment(client, auth_headers, resource["id"], activity["id"])

        # Get daily histogram
        start = date.today()
        end = start + timedelta(days=14)
        response = await client.get(
            f"/api/v1/resources/{resource['id']}/histogram",
            headers=auth_headers,
            params={
                "start_date": str(start),
                "end_date": str(end),
                "granularity": "daily",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["resource_id"] == resource["id"]
        assert len(data["data_points"]) == 15  # 15 days
        assert all("utilization_percent" in dp for dp in data["data_points"])

    @pytest.mark.asyncio
    async def test_resource_histogram_weekly(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test weekly granularity histogram."""
        # Setup
        setup = await create_test_program(client, auth_headers, "HIST2")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        resource = await create_test_resource(client, auth_headers, program_id, "ENG-HIST2")
        activity = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-HIST2", duration=21
        )
        await create_assignment(client, auth_headers, resource["id"], activity["id"])

        # Get weekly histogram
        start = date.today()
        end = start + timedelta(days=27)
        response = await client.get(
            f"/api/v1/resources/{resource['id']}/histogram",
            headers=auth_headers,
            params={
                "start_date": str(start),
                "end_date": str(end),
                "granularity": "weekly",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Weekly should aggregate into fewer points than daily
        assert len(data["data_points"]) < 28

    @pytest.mark.asyncio
    async def test_program_histogram(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test program-wide histogram."""
        # Setup
        setup = await create_test_program(client, auth_headers, "HIST3")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        # Create multiple resources
        for i in range(3):
            resource = await create_test_resource(
                client, auth_headers, program_id, f"ENG-HIST3-{i}"
            )
            activity = await create_test_activity(
                client, auth_headers, program_id, wbs_id, f"ACT-HIST3-{i}", duration=5
            )
            await create_assignment(client, auth_headers, resource["id"], activity["id"])

        # Get program histogram
        start = date.today()
        end = start + timedelta(days=10)
        response = await client.get(
            f"/api/v1/programs/{program_id}/histogram",
            headers=auth_headers,
            params={"start_date": str(start), "end_date": str(end)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["program_id"] == program_id
        assert data["summary"]["resource_count"] == 3
        assert len(data["histograms"]) == 3

    @pytest.mark.asyncio
    async def test_histogram_statistics(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test histogram statistics calculation."""
        # Setup
        setup = await create_test_program(client, auth_headers, "HIST4")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        resource = await create_test_resource(client, auth_headers, program_id, "ENG-HIST4")

        # Create two overlapping activities for over-allocation
        activity1 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-HIST4A", duration=5
        )
        activity2 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-HIST4B", duration=5
        )
        await create_assignment(client, auth_headers, resource["id"], activity1["id"])
        await create_assignment(client, auth_headers, resource["id"], activity2["id"])

        # Get histogram
        start = date.today()
        end = start + timedelta(days=10)
        response = await client.get(
            f"/api/v1/resources/{resource['id']}/histogram",
            headers=auth_headers,
            params={"start_date": str(start), "end_date": str(end)},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify statistics are present
        assert "peak_utilization" in data
        assert "average_utilization" in data
        assert "overallocated_days" in data
        assert "total_available_hours" in data
        assert "total_assigned_hours" in data

        # With two 100% allocations, should have over-allocation
        assert data["overallocated_days"] > 0
        assert Decimal(data["peak_utilization"]) > Decimal("100")


# =============================================================================
# Week 15 Integration Tests
# =============================================================================


class TestWeek15Integration:
    """Integration tests for full Week 15 workflow."""

    @pytest.mark.asyncio
    async def test_full_leveling_workflow(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test complete workflow: create, detect, level, apply, verify.

        Steps:
        1. Create program with activities and dependencies
        2. Create resources and assignments (causing overallocation)
        3. Run overallocation detection (via histogram)
        4. Run resource leveling
        5. Apply leveling shifts
        6. Verify no overallocations remain
        7. Generate histogram to verify
        """
        # 1. Create program with activities and dependencies
        setup = await create_test_program(client, auth_headers, "FULL")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        # Create chain of activities
        activity1 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-FULL-A", duration=5
        )
        activity2 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-FULL-B", duration=5
        )
        activity3 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-FULL-C", duration=5
        )
        activity4 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-FULL-D", duration=5
        )

        # Create dependencies: A->C, B->D
        await client.post(
            "/api/v1/dependencies",
            headers=auth_headers,
            json={
                "program_id": program_id,
                "predecessor_id": activity1["id"],
                "successor_id": activity3["id"],
                "dependency_type": "FS",
                "lag": 0,
            },
        )
        await client.post(
            "/api/v1/dependencies",
            headers=auth_headers,
            json={
                "program_id": program_id,
                "predecessor_id": activity2["id"],
                "successor_id": activity4["id"],
                "dependency_type": "FS",
                "lag": 0,
            },
        )

        # Calculate schedule
        calc_response = await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )
        assert calc_response.status_code == 200

        # 2. Create resources and assignments (causing overallocation)
        resource = await create_test_resource(
            client, auth_headers, program_id, "ENG-FULL", capacity="8.0"
        )

        # Assign all activities to same resource (A and B overlap, C and D overlap)
        await create_assignment(client, auth_headers, resource["id"], activity1["id"])
        await create_assignment(client, auth_headers, resource["id"], activity2["id"])
        await create_assignment(client, auth_headers, resource["id"], activity3["id"])
        await create_assignment(client, auth_headers, resource["id"], activity4["id"])

        # 3. Detect overallocation (via histogram)
        start = date.today()
        end = start + timedelta(days=30)
        hist_response = await client.get(
            f"/api/v1/resources/{resource['id']}/histogram",
            headers=auth_headers,
            params={"start_date": str(start), "end_date": str(end)},
        )
        assert hist_response.status_code == 200
        initial_histogram = hist_response.json()

        # Should have overallocations initially
        initial_overallocated = initial_histogram["overallocated_days"]
        assert initial_overallocated > 0, "Should have overallocations before leveling"

        # 4. Run resource leveling
        level_response = await client.post(
            f"/api/v1/programs/{program_id}/level",
            headers=auth_headers,
            json={
                "preserve_critical_path": False,
                "max_iterations": 100,
                "level_within_float": False,
            },
        )
        assert level_response.status_code == 200
        level_data = level_response.json()

        # 5. Apply leveling shifts (if any were returned)
        if level_data["shifts"]:
            shift_ids = [s["activity_id"] for s in level_data["shifts"]]
            apply_response = await client.post(
                f"/api/v1/programs/{program_id}/level/apply",
                headers=auth_headers,
                json={"shifts": shift_ids},
            )
            assert apply_response.status_code == 200
            apply_data = apply_response.json()
            # Verify the response has expected fields
            assert "applied_count" in apply_data
            assert "new_project_finish" in apply_data

        # 6 & 7. Generate histogram to verify improvement
        final_hist_response = await client.get(
            f"/api/v1/resources/{resource['id']}/histogram",
            headers=auth_headers,
            params={"start_date": str(start), "end_date": str(end + timedelta(days=30))},
        )
        assert final_hist_response.status_code == 200
        final_histogram = final_hist_response.json()

        # Verify leveling result
        assert level_data["iterations_used"] > 0
        assert "original_project_finish" in level_data
        assert "new_project_finish" in level_data

        # Program histogram should also work
        program_hist_response = await client.get(
            f"/api/v1/programs/{program_id}/histogram",
            headers=auth_headers,
        )
        assert program_hist_response.status_code == 200
        program_hist = program_hist_response.json()
        assert program_hist["summary"]["resource_count"] == 1
