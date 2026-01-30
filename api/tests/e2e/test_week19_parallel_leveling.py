"""End-to-end tests for Week 19: Parallel Resource Leveling.

This module validates the Week 19 deliverables:
1. ParallelLevelingService execution
2. Multi-resource conflict resolution
3. Algorithm comparison (serial vs parallel)
4. Recommendation logic
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


# =============================================================================
# Test Fixtures (reused from Week 15 pattern)
# =============================================================================


async def create_test_program(
    client: AsyncClient,
    auth_headers: dict[str, str],
    code_suffix: str | None = None,
) -> dict:
    """Create a test program with WBS for parallel leveling tests."""
    suffix = code_suffix or uuid4().hex[:6].upper()
    start = date.today()
    end = start + timedelta(days=365)

    program_response = await client.post(
        "/api/v1/programs",
        json={
            "name": f"Parallel Leveling Test Program {suffix}",
            "code": f"PLV-{suffix}",
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


async def setup_program_with_conflicts(
    client: AsyncClient,
    auth_headers: dict[str, str],
    suffix: str,
) -> dict:
    """Create a program with resource conflicts for leveling tests."""
    setup = await create_test_program(client, auth_headers, suffix)
    program_id = setup["program"]["id"]
    wbs_id = setup["wbs"]["id"]

    # Create resource
    resource = await create_test_resource(client, auth_headers, program_id, f"ENG-{suffix}")

    # Create overlapping activities (causes over-allocation)
    activity1 = await create_test_activity(
        client, auth_headers, program_id, wbs_id, f"ACT-{suffix}-A", duration=5
    )
    activity2 = await create_test_activity(
        client, auth_headers, program_id, wbs_id, f"ACT-{suffix}-B", duration=5
    )

    # Assign both to same resource
    await create_assignment(client, auth_headers, resource["id"], activity1["id"])
    await create_assignment(client, auth_headers, resource["id"], activity2["id"])

    # Calculate schedule
    await client.post(
        f"/api/v1/schedule/calculate/{program_id}",
        headers=auth_headers,
    )

    return {
        "program_id": program_id,
        "wbs_id": wbs_id,
        "resource": resource,
        "activities": [activity1, activity2],
    }


# =============================================================================
# Parallel Leveling Tests
# =============================================================================


class TestParallelLeveling:
    """E2E tests for parallel leveling endpoint."""

    @pytest.mark.asyncio
    async def test_parallel_leveling_basic(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test basic parallel leveling execution."""
        setup = await setup_program_with_conflicts(client, auth_headers, "PAR1")

        response = await client.post(
            f"/api/v1/programs/{setup['program_id']}/level-parallel",
            json={"preserve_critical_path": True},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert "activities_shifted" in data
        assert "schedule_extension_days" in data
        assert "conflicts_resolved" in data
        assert "resources_processed" in data
        assert data["program_id"] == setup["program_id"]

    @pytest.mark.asyncio
    async def test_parallel_leveling_preview(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test parallel leveling preview endpoint."""
        setup = await setup_program_with_conflicts(client, auth_headers, "PAR2")

        response = await client.get(
            f"/api/v1/programs/{setup['program_id']}/level-parallel/preview",
            headers=auth_headers,
            params={"preserve_critical_path": True, "level_within_float": False},
        )

        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert "shifts" in data
        assert "iterations_used" in data

    @pytest.mark.asyncio
    async def test_parallel_leveling_with_options(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test parallel leveling with various options."""
        setup = await setup_program_with_conflicts(client, auth_headers, "PAR3")

        # Test with preserve_critical_path=False and level_within_float=False
        response = await client.post(
            f"/api/v1/programs/{setup['program_id']}/level-parallel",
            json={
                "preserve_critical_path": False,
                "max_iterations": 50,
                "level_within_float": False,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["iterations_used"] <= 50

    @pytest.mark.asyncio
    async def test_parallel_leveling_returns_shifts(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that parallel leveling returns activity shifts."""
        setup = await setup_program_with_conflicts(client, auth_headers, "PAR4")

        response = await client.post(
            f"/api/v1/programs/{setup['program_id']}/level-parallel",
            json={
                "preserve_critical_path": False,
                "level_within_float": False,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should have shifts for resolving the conflict
        if data["activities_shifted"] > 0:
            assert len(data["shifts"]) > 0
            shift = data["shifts"][0]
            assert "activity_id" in shift
            assert "activity_code" in shift
            assert "original_start" in shift
            assert "new_start" in shift
            assert "delay_days" in shift
            assert "reason" in shift

    @pytest.mark.asyncio
    async def test_parallel_leveling_program_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test parallel leveling with non-existent program."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/programs/{fake_id}/level-parallel",
            json={"preserve_critical_path": True},
            headers=auth_headers,
        )

        assert response.status_code == 404


# =============================================================================
# Algorithm Comparison Tests
# =============================================================================


class TestLevelingComparison:
    """Tests for comparing serial vs parallel leveling algorithms."""

    @pytest.mark.asyncio
    async def test_compare_algorithms_basic(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test basic algorithm comparison endpoint."""
        setup = await setup_program_with_conflicts(client, auth_headers, "CMP1")

        response = await client.get(
            f"/api/v1/programs/{setup['program_id']}/level/compare",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "serial" in data
        assert "parallel" in data
        assert "recommendation" in data
        assert "improvement" in data
        assert data["recommendation"] in ["serial", "parallel"]

    @pytest.mark.asyncio
    async def test_compare_algorithms_returns_metrics(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that comparison returns proper metrics for both algorithms."""
        setup = await setup_program_with_conflicts(client, auth_headers, "CMP2")

        response = await client.get(
            f"/api/v1/programs/{setup['program_id']}/level/compare",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Check serial metrics
        assert "success" in data["serial"]
        assert "iterations" in data["serial"]
        assert "activities_shifted" in data["serial"]
        assert "schedule_extension_days" in data["serial"]
        assert "remaining_conflicts" in data["serial"]

        # Check parallel metrics
        assert "success" in data["parallel"]
        assert "iterations" in data["parallel"]
        assert "activities_shifted" in data["parallel"]
        assert "schedule_extension_days" in data["parallel"]
        assert "remaining_conflicts" in data["parallel"]

    @pytest.mark.asyncio
    async def test_compare_algorithms_with_options(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test comparison with various leveling options."""
        setup = await setup_program_with_conflicts(client, auth_headers, "CMP3")

        response = await client.get(
            f"/api/v1/programs/{setup['program_id']}/level/compare",
            headers=auth_headers,
            params={
                "preserve_critical_path": False,
                "level_within_float": False,
                "max_iterations": 50,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "recommendation" in data

    @pytest.mark.asyncio
    async def test_compare_algorithms_improvement_metrics(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that comparison includes improvement metrics."""
        setup = await setup_program_with_conflicts(client, auth_headers, "CMP4")

        response = await client.get(
            f"/api/v1/programs/{setup['program_id']}/level/compare",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Check improvement metrics
        assert "extension_days_saved" in data["improvement"]
        assert "fewer_shifts" in data["improvement"]
        assert "fewer_iterations" in data["improvement"]

    @pytest.mark.asyncio
    async def test_compare_algorithms_program_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test comparison with non-existent program."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/programs/{fake_id}/level/compare",
            headers=auth_headers,
        )

        assert response.status_code == 404


# =============================================================================
# Multi-Resource Conflict Tests
# =============================================================================


class TestMultiResourceConflicts:
    """Tests for parallel leveling with multiple resources."""

    @pytest.mark.asyncio
    async def test_parallel_leveling_multiple_resources(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test parallel leveling with multiple over-allocated resources."""
        setup = await create_test_program(client, auth_headers, "MULT1")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        # Create two resources
        resource1 = await create_test_resource(client, auth_headers, program_id, "ENG-MULT1A")
        resource2 = await create_test_resource(client, auth_headers, program_id, "ENG-MULT1B")

        # Create activities
        activity1 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-MULT1A", duration=5
        )
        activity2 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-MULT1B", duration=5
        )
        activity3 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-MULT1C", duration=5
        )
        activity4 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-MULT1D", duration=5
        )

        # Over-allocate both resources
        await create_assignment(client, auth_headers, resource1["id"], activity1["id"])
        await create_assignment(client, auth_headers, resource1["id"], activity2["id"])
        await create_assignment(client, auth_headers, resource2["id"], activity3["id"])
        await create_assignment(client, auth_headers, resource2["id"], activity4["id"])

        # Calculate schedule
        await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )

        # Run parallel leveling
        response = await client.post(
            f"/api/v1/programs/{program_id}/level-parallel",
            json={"preserve_critical_path": False, "level_within_float": False},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["resources_processed"] >= 1

    @pytest.mark.asyncio
    async def test_parallel_leveling_shared_resource(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test parallel leveling when one resource is shared across many activities."""
        setup = await create_test_program(client, auth_headers, "MULT2")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        # Create one resource shared by many activities
        resource = await create_test_resource(
            client, auth_headers, program_id, "ENG-MULT2", capacity="8.0"
        )

        # Create multiple overlapping activities
        activities = []
        for i in range(4):
            activity = await create_test_activity(
                client, auth_headers, program_id, wbs_id, f"ACT-MULT2-{i}", duration=5
            )
            activities.append(activity)
            await create_assignment(client, auth_headers, resource["id"], activity["id"])

        # Calculate schedule
        await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )

        # Run parallel leveling
        response = await client.post(
            f"/api/v1/programs/{program_id}/level-parallel",
            json={"preserve_critical_path": False, "level_within_float": False},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should resolve or attempt to resolve conflicts
        assert data["iterations_used"] > 0


# =============================================================================
# Week 19 Integration Tests
# =============================================================================


class TestWeek19Integration:
    """Integration tests for full Week 19 parallel leveling workflow."""

    @pytest.mark.asyncio
    async def test_full_parallel_leveling_workflow(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test complete parallel leveling workflow.

        Steps:
        1. Create program with activities and dependencies
        2. Create resources and assignments (causing overallocation)
        3. Run parallel leveling
        4. Compare with serial leveling
        5. Verify recommendation
        """
        # 1. Create program with activities and dependencies
        setup = await create_test_program(client, auth_headers, "INTEG")
        program_id = setup["program"]["id"]
        wbs_id = setup["wbs"]["id"]

        # Create chain of activities
        activity1 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-INTEG-A", duration=5
        )
        activity2 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-INTEG-B", duration=5
        )
        activity3 = await create_test_activity(
            client, auth_headers, program_id, wbs_id, "ACT-INTEG-C", duration=5
        )

        # Create dependencies
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

        # Calculate schedule
        await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=auth_headers,
        )

        # 2. Create resource and cause overallocation
        resource = await create_test_resource(
            client, auth_headers, program_id, "ENG-INTEG", capacity="8.0"
        )

        await create_assignment(client, auth_headers, resource["id"], activity1["id"])
        await create_assignment(client, auth_headers, resource["id"], activity2["id"])
        await create_assignment(client, auth_headers, resource["id"], activity3["id"])

        # 3. Run parallel leveling
        parallel_response = await client.post(
            f"/api/v1/programs/{program_id}/level-parallel",
            json={"preserve_critical_path": False, "level_within_float": False},
            headers=auth_headers,
        )
        assert parallel_response.status_code == 200
        parallel_data = parallel_response.json()

        # 4. Compare with serial leveling
        compare_response = await client.get(
            f"/api/v1/programs/{program_id}/level/compare",
            headers=auth_headers,
        )
        assert compare_response.status_code == 200
        compare_data = compare_response.json()

        # 5. Verify recommendation
        assert compare_data["recommendation"] in ["serial", "parallel"]

        # Verify parallel result structure
        assert "conflicts_resolved" in parallel_data
        assert "resources_processed" in parallel_data
        assert "original_project_finish" in parallel_data
        assert "new_project_finish" in parallel_data

    @pytest.mark.asyncio
    async def test_parallel_vs_serial_consistency(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that both algorithms produce consistent results."""
        setup = await setup_program_with_conflicts(client, auth_headers, "CONS")

        # Run serial leveling
        serial_response = await client.post(
            f"/api/v1/programs/{setup['program_id']}/level",
            json={"preserve_critical_path": False, "level_within_float": False},
            headers=auth_headers,
        )
        assert serial_response.status_code == 200
        serial_data = serial_response.json()

        # Run parallel leveling
        parallel_response = await client.post(
            f"/api/v1/programs/{setup['program_id']}/level-parallel",
            json={"preserve_critical_path": False, "level_within_float": False},
            headers=auth_headers,
        )
        assert parallel_response.status_code == 200
        parallel_data = parallel_response.json()

        # Both should have same program_id
        assert serial_data["program_id"] == parallel_data["program_id"]

        # Both should have valid dates
        assert "original_project_finish" in serial_data
        assert "original_project_finish" in parallel_data
        assert "new_project_finish" in serial_data
        assert "new_project_finish" in parallel_data
