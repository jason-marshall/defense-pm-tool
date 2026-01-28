"""End-to-end tests for Week 14: Resource Management Foundation.

This module validates the Week 14 deliverables:
1. Resource CRUD operations
2. Resource assignments to activities
3. Resource calendar management
4. Full resource workflow integration
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
# Resource CRUD Tests
# =============================================================================


class TestResourceCRUD:
    """E2E tests for resource CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_resource_labor(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test creating a LABOR type resource."""
        # Create program first
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Resource Test Program",
                "code": f"RTP-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create labor resource
        response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Senior Engineer",
                "code": "ENG-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
                "cost_rate": "150.00",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Senior Engineer"
        assert data["code"] == "ENG-001"
        assert data["resource_type"] == "labor"
        assert Decimal(data["capacity_per_day"]) == Decimal("8.0")
        assert Decimal(data["cost_rate"]) == Decimal("150.00")
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_resource_equipment(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test creating an EQUIPMENT type resource."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Equipment Test Program",
                "code": f"EQP-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create equipment resource
        response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "CNC Machine",
                "code": "MACH-001",
                "resource_type": "equipment",
                "capacity_per_day": "24.0",
                "cost_rate": "500.00",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["resource_type"] == "equipment"

    @pytest.mark.asyncio
    async def test_create_resource_code_uppercase(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that resource code is converted to uppercase."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Code Test Program",
                "code": f"CTP-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create resource with lowercase code
        response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Test Resource",
                "code": "lower-case-code",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "LOWER-CASE-CODE"

    @pytest.mark.asyncio
    async def test_create_resource_duplicate_code_rejected(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that duplicate resource codes are rejected with 409."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Duplicate Test Program",
                "code": f"DUP-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create first resource
        response1 = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "First Resource",
                "code": "UNIQUE-CODE",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        assert response1.status_code == 201

        # Try to create second resource with same code
        response2 = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Second Resource",
                "code": "UNIQUE-CODE",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )

        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_resources_by_program(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test listing resources filtered by program."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "List Test Program",
                "code": f"LST-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create multiple resources
        for i in range(3):
            await client.post(
                "/api/v1/resources",
                json={
                    "program_id": program_id,
                    "name": f"Resource {i}",
                    "code": f"RES-{i:03d}",
                    "resource_type": "labor",
                },
                headers=auth_headers,
            )

        # List resources
        response = await client.get(
            f"/api/v1/resources?program_id={program_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_resources_filter_by_type(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test listing resources filtered by type."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Filter Test Program",
                "code": f"FLT-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create resources of different types
        await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Labor Resource",
                "code": "LAB-001",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Equipment Resource",
                "code": "EQP-001",
                "resource_type": "equipment",
            },
            headers=auth_headers,
        )

        # Filter by LABOR
        response = await client.get(
            f"/api/v1/resources?program_id={program_id}&resource_type=labor",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["resource_type"] == "labor"

    @pytest.mark.asyncio
    async def test_update_resource(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test updating a resource."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Update Test Program",
                "code": f"UPD-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create resource
        create_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Original Name",
                "code": "UPD-001",
                "resource_type": "labor",
                "cost_rate": "100.00",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        resource_id = create_response.json()["id"]

        # Update resource
        update_response = await client.put(
            f"/api/v1/resources/{resource_id}",
            json={
                "name": "Updated Name",
                "cost_rate": "125.00",
            },
            headers=auth_headers,
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "Updated Name"
        assert Decimal(data["cost_rate"]) == Decimal("125.00")

    @pytest.mark.asyncio
    async def test_delete_resource(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test deleting a resource."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Delete Test Program",
                "code": f"DEL-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create resource
        create_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "To Be Deleted",
                "code": "DEL-001",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        resource_id = create_response.json()["id"]

        # Delete resource
        delete_response = await client.delete(
            f"/api/v1/resources/{resource_id}",
            headers=auth_headers,
        )

        assert delete_response.status_code == 200
        assert "deleted" in delete_response.json()["message"].lower()

        # Verify resource is gone
        get_response = await client.get(
            f"/api/v1/resources/{resource_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404


# =============================================================================
# Resource Assignment Tests
# =============================================================================


class TestResourceAssignments:
    """E2E tests for resource assignment operations."""

    @pytest.mark.asyncio
    async def test_create_assignment(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test creating a resource assignment."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Assignment Test Program",
                "code": f"ASN-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create WBS
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "wbs_code": "1.1",
                "name": "Test WBS",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        # Create activity
        activity_response = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "code": "ACT-001",
                "name": "Test Activity",
                "duration": 10,
            },
            headers=auth_headers,
        )
        assert activity_response.status_code == 201
        activity_id = activity_response.json()["id"]

        # Create resource
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Test Resource",
                "code": "RES-001",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Create assignment
        assignment_response = await client.post(
            f"/api/v1/resources/{resource_id}/assignments",
            json={
                "resource_id": resource_id,
                "activity_id": activity_id,
                "units": "1.0",
            },
            headers=auth_headers,
        )

        assert assignment_response.status_code == 201
        data = assignment_response.json()
        assert data["activity_id"] == activity_id
        assert data["resource_id"] == resource_id
        assert Decimal(data["units"]) == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_create_assignment_with_dates(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test creating an assignment with start and finish dates."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Date Assignment Test",
                "code": f"DAT-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create WBS
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "wbs_code": "1.1",
                "name": "Test WBS",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        # Create activity
        activity_response = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "code": "ACT-001",
                "name": "Test Activity",
                "duration": 10,
            },
            headers=auth_headers,
        )
        assert activity_response.status_code == 201
        activity_id = activity_response.json()["id"]

        # Create resource
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Test Resource",
                "code": "RES-001",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Create assignment with dates
        start = date.today()
        finish = start + timedelta(days=10)
        assignment_response = await client.post(
            f"/api/v1/resources/{resource_id}/assignments",
            json={
                "resource_id": resource_id,
                "activity_id": activity_id,
                "units": "0.5",
                "start_date": str(start),
                "finish_date": str(finish),
            },
            headers=auth_headers,
        )

        assert assignment_response.status_code == 201
        data = assignment_response.json()
        assert data["start_date"] == str(start)
        assert data["finish_date"] == str(finish)
        assert Decimal(data["units"]) == Decimal("0.5")

    @pytest.mark.asyncio
    async def test_duplicate_assignment_rejected(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that duplicate assignments are rejected with 409."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Dup Assignment Test",
                "code": f"DAS-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create WBS
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "wbs_code": "1.1",
                "name": "Test WBS",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        # Create activity
        activity_response = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "code": "ACT-001",
                "name": "Test Activity",
                "duration": 10,
            },
            headers=auth_headers,
        )
        assert activity_response.status_code == 201
        activity_id = activity_response.json()["id"]

        # Create resource
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Test Resource",
                "code": "RES-001",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Create first assignment
        await client.post(
            f"/api/v1/resources/{resource_id}/assignments",
            json={
                "resource_id": resource_id,
                "activity_id": activity_id,
                "units": "1.0",
            },
            headers=auth_headers,
        )

        # Try to create duplicate assignment
        dup_response = await client.post(
            f"/api/v1/resources/{resource_id}/assignments",
            json={
                "resource_id": resource_id,
                "activity_id": activity_id,
                "units": "0.5",
            },
            headers=auth_headers,
        )

        assert dup_response.status_code == 409
        assert "already exists" in dup_response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_resource_assignments(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test listing assignments for a resource."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "List Assignment Test",
                "code": f"LAS-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create WBS
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "wbs_code": "1.1",
                "name": "Test WBS",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        # Create resource
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Test Resource",
                "code": "RES-001",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Create multiple activities and assignments
        for i in range(3):
            activity_response = await client.post(
                "/api/v1/activities",
                json={
                    "program_id": program_id,
                    "wbs_id": wbs_id,
                    "code": f"ACT-{i:03d}",
                    "name": f"Activity {i}",
                    "duration": 5,
                },
                headers=auth_headers,
            )
            activity_id = activity_response.json()["id"]

            await client.post(
                f"/api/v1/resources/{resource_id}/assignments",
                json={
                    "resource_id": resource_id,
                    "activity_id": activity_id,
                    "units": "1.0",
                },
                headers=auth_headers,
            )

        # List assignments
        response = await client.get(
            f"/api/v1/resources/{resource_id}/assignments",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3


# =============================================================================
# Resource Calendar Tests
# =============================================================================


class TestResourceCalendar:
    """E2E tests for resource calendar operations."""

    @pytest.mark.asyncio
    async def test_create_calendar_entries(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test bulk creating calendar entries."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Calendar Test Program",
                "code": f"CAL-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create resource
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Test Resource",
                "code": "RES-001",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Create calendar entries (5 working days)
        start = date.today()
        entries = []
        for i in range(5):
            entries.append(
                {
                    "calendar_date": str(start + timedelta(days=i)),
                    "available_hours": "8.0",
                    "is_working_day": True,
                }
            )

        response = await client.post(
            f"/api/v1/resources/{resource_id}/calendar",
            json={
                "resource_id": resource_id,
                "entries": entries,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data) == 5
        assert all(e["is_working_day"] is True for e in data)

    @pytest.mark.asyncio
    async def test_get_calendar_range(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting calendar range with working_days and total_hours."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Calendar Range Test",
                "code": f"CRT-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create resource
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Test Resource",
                "code": "RES-001",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Create calendar entries (5 working days at 8 hours + 2 non-working days)
        start = date.today()
        entries = []
        for i in range(7):
            is_working = i < 5
            entries.append(
                {
                    "calendar_date": str(start + timedelta(days=i)),
                    "available_hours": "8.0" if is_working else "0.0",
                    "is_working_day": is_working,
                }
            )

        await client.post(
            f"/api/v1/resources/{resource_id}/calendar",
            json={
                "resource_id": resource_id,
                "entries": entries,
            },
            headers=auth_headers,
        )

        # Get calendar range
        end = start + timedelta(days=6)
        response = await client.get(
            f"/api/v1/resources/{resource_id}/calendar?start_date={start}&end_date={end}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["working_days"] == 5
        assert Decimal(data["total_hours"]) == Decimal("40.0")
        assert len(data["entries"]) == 7


# =============================================================================
# Week 14 Integration Tests
# =============================================================================


class TestWeek14Integration:
    """Integration tests for Week 14 resource management workflow."""

    @pytest.mark.asyncio
    async def test_full_resource_workflow(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test complete resource workflow: create, assign, calendar, verify."""
        # 1. Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Full Workflow Test",
                "code": f"FWT-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create WBS
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "wbs_code": "1.1",
                "name": "Integration Test WBS",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        # Create activity
        activity_response = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "code": "INTEG-001",
                "name": "Integration Test Activity",
                "duration": 10,
                "budgeted_cost": "10000.00",
            },
            headers=auth_headers,
        )
        assert activity_response.status_code == 201
        activity_id = activity_response.json()["id"]

        # 2. Create resource
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Integration Engineer",
                "code": "ENG-INT-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
                "cost_rate": "175.00",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # 3. Create assignment to activity
        assignment_response = await client.post(
            f"/api/v1/resources/{resource_id}/assignments",
            json={
                "resource_id": resource_id,
                "activity_id": activity_id,
                "units": "1.0",
            },
            headers=auth_headers,
        )
        assert assignment_response.status_code == 201

        # 4. Create calendar entries (5 working days + 2 weekend days)
        start = date.today()
        entries = []
        # 5 working days at 8 hours each
        for i in range(5):
            entries.append(
                {
                    "calendar_date": str(start + timedelta(days=i)),
                    "available_hours": "8.0",
                    "is_working_day": True,
                }
            )
        # 2 weekend days at 0 hours
        for i in range(5, 7):
            entries.append(
                {
                    "calendar_date": str(start + timedelta(days=i)),
                    "available_hours": "0.0",
                    "is_working_day": False,
                }
            )

        calendar_response = await client.post(
            f"/api/v1/resources/{resource_id}/calendar",
            json={
                "resource_id": resource_id,
                "entries": entries,
            },
            headers=auth_headers,
        )
        assert calendar_response.status_code == 201

        # 5. Verify resource exists and is correct
        get_resource = await client.get(
            f"/api/v1/resources/{resource_id}",
            headers=auth_headers,
        )
        assert get_resource.status_code == 200
        resource_data = get_resource.json()
        assert resource_data["name"] == "Integration Engineer"
        assert resource_data["code"] == "ENG-INT-001"
        assert resource_data["resource_type"] == "labor"
        assert resource_data["is_active"] is True

        # 6. Verify calendar (5 working days, 40 total hours)
        end = start + timedelta(days=6)
        calendar_check = await client.get(
            f"/api/v1/resources/{resource_id}/calendar?start_date={start}&end_date={end}",
            headers=auth_headers,
        )
        assert calendar_check.status_code == 200
        calendar_data = calendar_check.json()
        assert calendar_data["working_days"] == 5
        assert Decimal(calendar_data["total_hours"]) == Decimal("40.0")

        # Verify all steps completed successfully
        assert resource_data["id"] == resource_id
        assert len(calendar_data["entries"]) == 7

    @pytest.mark.asyncio
    async def test_resource_types_complete(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test all resource types can be created."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Resource Types Test",
                "code": f"RTT-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create all three resource types
        resource_types = ["labor", "equipment", "material"]
        for i, resource_type in enumerate(resource_types):
            response = await client.post(
                "/api/v1/resources",
                json={
                    "program_id": program_id,
                    "name": f"Test {resource_type}",
                    "code": f"TYPE-{i:03d}",
                    "resource_type": resource_type,
                },
                headers=auth_headers,
            )
            assert response.status_code == 201
            assert response.json()["resource_type"] == resource_type

        # Verify all types were created
        list_response = await client.get(
            f"/api/v1/resources?program_id={program_id}",
            headers=auth_headers,
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 3
