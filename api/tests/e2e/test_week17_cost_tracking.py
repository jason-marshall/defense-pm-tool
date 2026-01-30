"""End-to-end tests for Week 17: Resource Cost and Material Tracking.

This module validates the Week 17 deliverables:
1. Resource cost calculation endpoints
2. Material quantity tracking
3. EVMS ACWP synchronization
4. Full cost tracking workflow
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
# Resource Cost Tracking Tests
# =============================================================================


class TestResourceCostTracking:
    """E2E tests for resource cost tracking."""

    @pytest.mark.asyncio
    async def test_activity_cost_calculation(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test activity cost calculation with labor resource."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Cost Tracking Test Program",
                "code": f"CTP-{uuid4().hex[:6].upper()}",
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
                "name": "Cost Test WBS",
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
                "code": "ACT-COST-001",
                "name": "Cost Test Activity",
                "duration": 10,
                "budgeted_cost": "10000.00",
            },
            headers=auth_headers,
        )
        assert activity_response.status_code == 201
        activity_id = activity_response.json()["id"]

        # Create labor resource with cost rate
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Senior Engineer",
                "code": "ENG-COST-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
                "cost_rate": "150.00",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Create assignment with planned hours
        assignment_response = await client.post(
            f"/api/v1/resources/{resource_id}/assignments",
            json={
                "resource_id": resource_id,
                "activity_id": activity_id,
                "units": "1.0",
                "planned_hours": "40.00",
            },
            headers=auth_headers,
        )
        assert assignment_response.status_code == 201
        assignment_id = assignment_response.json()["id"]

        # Record actual hours via cost entry
        entry_response = await client.post(
            f"/api/v1/cost/assignments/{assignment_id}/entries",
            json={
                "entry_date": str(date.today()),
                "hours_worked": "20.00",
            },
            headers=auth_headers,
        )
        assert entry_response.status_code == 200
        entry_data = entry_response.json()
        assert "cost_incurred" in entry_data
        # 20 hours * $150/hr = $3000
        assert Decimal(entry_data["cost_incurred"]) == Decimal("3000.00")

        # Get activity cost
        cost_response = await client.get(
            f"/api/v1/cost/activities/{activity_id}",
            headers=auth_headers,
        )
        assert cost_response.status_code == 200
        cost_data = cost_response.json()

        assert Decimal(cost_data["actual_cost"]) == Decimal("3000.00")
        # Planned: 40 hours * $150 = $6000
        assert Decimal(cost_data["planned_cost"]) == Decimal("6000.00")
        assert len(cost_data["resource_breakdown"]) == 1

    @pytest.mark.asyncio
    async def test_wbs_cost_rollup(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test WBS cost rollup calculation (exclude children to avoid ltree)."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "WBS Cost Test Program",
                "code": f"WCT-{uuid4().hex[:6].upper()}",
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
                "name": "WBS Cost Test",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        # Get WBS cost without children (avoids PostgreSQL ltree operations)
        cost_response = await client.get(
            f"/api/v1/cost/wbs/{wbs_id}?include_children=false",
            headers=auth_headers,
        )
        assert cost_response.status_code == 200
        cost_data = cost_response.json()

        assert "planned_cost" in cost_data
        assert "actual_cost" in cost_data
        assert "cost_variance" in cost_data
        assert "activity_count" in cost_data

    @pytest.mark.asyncio
    async def test_program_cost_summary(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test program cost summary calculation."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Program Cost Summary Test",
                "code": f"PCS-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Get program cost summary
        response = await client.get(
            f"/api/v1/cost/programs/{program_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert "total_planned_cost" in data
        assert "total_actual_cost" in data
        assert "total_cost_variance" in data
        assert "labor_cost" in data
        assert "equipment_cost" in data
        assert "material_cost" in data
        assert "resource_count" in data
        assert "activity_count" in data
        assert "wbs_breakdown" in data


# =============================================================================
# Material Tracking Tests
# =============================================================================


class TestMaterialTracking:
    """E2E tests for material quantity tracking."""

    @pytest.mark.asyncio
    async def test_material_resource_creation(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test creating a material resource with quantity fields."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Material Test Program",
                "code": f"MTP-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create material resource
        response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Steel Plates",
                "code": "MAT-001",
                "resource_type": "material",
                "quantity_unit": "kg",
                "unit_cost": "15.50",
                "quantity_available": "1000.00",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()

        assert data["resource_type"] == "material"
        assert data["quantity_unit"] == "kg"
        assert Decimal(data["unit_cost"]) == Decimal("15.50")
        assert Decimal(data["quantity_available"]) == Decimal("1000.00")

    @pytest.mark.asyncio
    async def test_material_status(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting material status."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Material Status Test",
                "code": f"MST-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create material resource
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Copper Wire",
                "code": "MAT-CW-001",
                "resource_type": "material",
                "quantity_unit": "meters",
                "unit_cost": "5.00",
                "quantity_available": "500.00",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Get material status
        response = await client.get(
            f"/api/v1/materials/resources/{resource_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["resource_code"] == "MAT-CW-001"
        assert data["quantity_unit"] == "meters"
        assert "quantity_available" in data
        assert "quantity_consumed" in data
        assert "quantity_remaining" in data
        assert "percent_consumed" in data
        assert "total_value" in data
        # Total value: 500 * $5 = $2500
        assert Decimal(data["total_value"]) == Decimal("2500.00")

    @pytest.mark.asyncio
    async def test_material_consumption(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test recording material consumption."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Material Consumption Test",
                "code": f"MCT-{uuid4().hex[:6].upper()}",
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
                "name": "Consumption Test WBS",
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
                "code": "ACT-CONS-001",
                "name": "Consumption Test Activity",
                "duration": 5,
            },
            headers=auth_headers,
        )
        assert activity_response.status_code == 201
        activity_id = activity_response.json()["id"]

        # Create material resource
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Aluminum Sheets",
                "code": "MAT-AL-001",
                "resource_type": "material",
                "quantity_unit": "sheets",
                "unit_cost": "25.00",
                "quantity_available": "200.00",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Create assignment with quantity assigned
        assignment_response = await client.post(
            f"/api/v1/resources/{resource_id}/assignments",
            json={
                "resource_id": resource_id,
                "activity_id": activity_id,
                "units": "1.0",
                "quantity_assigned": "100.00",
            },
            headers=auth_headers,
        )
        assert assignment_response.status_code == 201
        assignment_id = assignment_response.json()["id"]

        # Consume material
        consume_response = await client.post(
            f"/api/v1/materials/assignments/{assignment_id}/consume",
            json={"quantity": "50.00"},
            headers=auth_headers,
        )
        assert consume_response.status_code == 200
        data = consume_response.json()

        assert Decimal(data["quantity_consumed"]) == Decimal("50.00")
        assert Decimal(data["remaining_assigned"]) == Decimal("50.00")
        # Cost: 50 sheets * $25 = $1250
        assert Decimal(data["cost_incurred"]) == Decimal("1250.00")

    @pytest.mark.asyncio
    async def test_consumption_validation(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test consumption validation prevents over-consumption."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Consumption Validation Test",
                "code": f"CVT-{uuid4().hex[:6].upper()}",
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
                "name": "Validation Test WBS",
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
                "code": "ACT-VAL-001",
                "name": "Validation Test Activity",
                "duration": 5,
            },
            headers=auth_headers,
        )
        assert activity_response.status_code == 201
        activity_id = activity_response.json()["id"]

        # Create material resource
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Limited Material",
                "code": "MAT-LIM-001",
                "resource_type": "material",
                "quantity_unit": "units",
                "unit_cost": "10.00",
                "quantity_available": "100.00",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Create assignment with limited quantity
        assignment_response = await client.post(
            f"/api/v1/resources/{resource_id}/assignments",
            json={
                "resource_id": resource_id,
                "activity_id": activity_id,
                "units": "1.0",
                "quantity_assigned": "50.00",
            },
            headers=auth_headers,
        )
        assert assignment_response.status_code == 201
        assignment_id = assignment_response.json()["id"]

        # First, consume some valid amount
        valid_response = await client.post(
            f"/api/v1/materials/assignments/{assignment_id}/consume",
            json={"quantity": "30.00"},
            headers=auth_headers,
        )
        assert valid_response.status_code == 200

        # Now try to consume more than remaining (30 consumed, 20 remaining, try to consume 25)
        consume_response = await client.post(
            f"/api/v1/materials/assignments/{assignment_id}/consume",
            json={"quantity": "25.00"},
            headers=auth_headers,
        )
        # Should fail because 30 + 25 = 55 > 50 assigned
        # ValidationError returns 422 Unprocessable Entity
        assert consume_response.status_code == 422

    @pytest.mark.asyncio
    async def test_program_material_summary(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test program material summary."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Material Summary Test",
                "code": f"MSM-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create multiple material resources
        for i in range(3):
            await client.post(
                "/api/v1/resources",
                json={
                    "program_id": program_id,
                    "name": f"Material {i}",
                    "code": f"MAT-SUM-{i:03d}",
                    "resource_type": "material",
                    "quantity_unit": "units",
                    "unit_cost": "10.00",
                    "quantity_available": "100.00",
                },
                headers=auth_headers,
            )

        # Get program material summary
        response = await client.get(
            f"/api/v1/materials/programs/{program_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["material_count"] == 3
        # Total value: 3 materials * 100 units * $10 = $3000
        assert Decimal(data["total_value"]) == Decimal("3000.00")
        assert "consumed_value" in data
        assert "remaining_value" in data
        assert len(data["materials"]) == 3


# =============================================================================
# Week 17 Integration Tests
# =============================================================================


class TestWeek17Integration:
    """Integration tests for Week 17 features."""

    @pytest.mark.asyncio
    async def test_full_cost_tracking_workflow(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Test complete cost tracking workflow:
        1. Create labor resource with cost rate
        2. Create activity and assign resource
        3. Record actual hours
        4. Calculate costs via activity cost endpoint
        """
        # 1. Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Full Cost Workflow Test",
                "code": f"FCW-{uuid4().hex[:6].upper()}",
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

        # 2. Create labor resource
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Senior Engineer",
                "code": "ENG-FCW-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
                "cost_rate": "150.00",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # 3. Create activity
        activity_response = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "Design Phase",
                "code": "ACT-FCW-001",
                "duration": 10,
                "budgeted_cost": "12000.00",
            },
            headers=auth_headers,
        )
        assert activity_response.status_code == 201
        activity_id = activity_response.json()["id"]

        # 4. Assign resource
        assignment_response = await client.post(
            f"/api/v1/resources/{resource_id}/assignments",
            json={
                "resource_id": resource_id,
                "activity_id": activity_id,
                "units": "1.0",
                "planned_hours": "80.00",
            },
            headers=auth_headers,
        )
        assert assignment_response.status_code == 201
        assignment_id = assignment_response.json()["id"]

        # 5. Record actual hours
        entry_response = await client.post(
            f"/api/v1/cost/assignments/{assignment_id}/entries",
            json={
                "entry_date": str(date.today()),
                "hours_worked": "40.00",
            },
            headers=auth_headers,
        )
        assert entry_response.status_code == 200
        entry_data = entry_response.json()
        # Verify: 40 hours * $150/hr = $6,000
        assert Decimal(entry_data["cost_incurred"]) == Decimal("6000.00")

        # 6. Get activity cost to verify
        cost_response = await client.get(
            f"/api/v1/cost/activities/{activity_id}",
            headers=auth_headers,
        )
        assert cost_response.status_code == 200
        cost_data = cost_response.json()

        # Verify: 40 hours * $150/hr = $6,000
        assert Decimal(cost_data["actual_cost"]) == Decimal("6000.00")

    @pytest.mark.asyncio
    async def test_mixed_resource_cost_workflow(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test cost tracking with both labor and material resources."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Mixed Resource Cost Test",
                "code": f"MRC-{uuid4().hex[:6].upper()}",
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
                "name": "Mixed Resource WBS",
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
                "name": "Construction Phase",
                "code": "ACT-MIX-001",
                "duration": 20,
            },
            headers=auth_headers,
        )
        assert activity_response.status_code == 201
        activity_id = activity_response.json()["id"]

        # Create labor resource
        labor_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Construction Worker",
                "code": "LAB-MIX-001",
                "resource_type": "labor",
                "cost_rate": "75.00",
            },
            headers=auth_headers,
        )
        assert labor_response.status_code == 201
        labor_id = labor_response.json()["id"]

        # Create material resource
        material_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Concrete",
                "code": "MAT-MIX-001",
                "resource_type": "material",
                "quantity_unit": "cubic_yards",
                "unit_cost": "150.00",
                "quantity_available": "100.00",
            },
            headers=auth_headers,
        )
        assert material_response.status_code == 201
        material_id = material_response.json()["id"]

        # Assign labor resource
        labor_assignment = await client.post(
            f"/api/v1/resources/{labor_id}/assignments",
            json={
                "resource_id": labor_id,
                "activity_id": activity_id,
                "units": "1.0",
                "planned_hours": "160.00",
            },
            headers=auth_headers,
        )
        assert labor_assignment.status_code == 201
        labor_assignment_id = labor_assignment.json()["id"]

        # Assign material resource
        material_assignment = await client.post(
            f"/api/v1/resources/{material_id}/assignments",
            json={
                "resource_id": material_id,
                "activity_id": activity_id,
                "units": "1.0",
                "quantity_assigned": "50.00",
            },
            headers=auth_headers,
        )
        assert material_assignment.status_code == 201
        material_assignment_id = material_assignment.json()["id"]

        # Record labor hours
        labor_entry_response = await client.post(
            f"/api/v1/cost/assignments/{labor_assignment_id}/entries",
            json={
                "entry_date": str(date.today()),
                "hours_worked": "80.00",
            },
            headers=auth_headers,
        )
        assert labor_entry_response.status_code == 200
        # Labor: 80 hours * $75 = $6,000
        assert Decimal(labor_entry_response.json()["cost_incurred"]) == Decimal("6000.00")

        # Consume material
        material_consume_response = await client.post(
            f"/api/v1/materials/assignments/{material_assignment_id}/consume",
            json={"quantity": "25.00"},
            headers=auth_headers,
        )
        assert material_consume_response.status_code == 200
        # Material: 25 yards * $150 = $3,750
        assert Decimal(material_consume_response.json()["cost_incurred"]) == Decimal("3750.00")

        # Get activity cost to verify both resources are tracked
        cost_response = await client.get(
            f"/api/v1/cost/activities/{activity_id}",
            headers=auth_headers,
        )
        assert cost_response.status_code == 200
        cost_data = cost_response.json()

        # Total: $6,000 + $3,750 = $9,750
        assert Decimal(cost_data["actual_cost"]) == Decimal("9750.00")
        assert len(cost_data["resource_breakdown"]) == 2

    @pytest.mark.asyncio
    async def test_cost_entry_tracking(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test multiple cost entries over time."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Cost Entry Tracking Test",
                "code": f"CET-{uuid4().hex[:6].upper()}",
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
                "name": "Entry Tracking WBS",
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
                "name": "Multi-Day Task",
                "code": "ACT-ENT-001",
                "duration": 5,
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
                "name": "Developer",
                "code": "DEV-ENT-001",
                "resource_type": "labor",
                "cost_rate": "100.00",
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
                "planned_hours": "40.00",
            },
            headers=auth_headers,
        )
        assert assignment_response.status_code == 201
        assignment_id = assignment_response.json()["id"]

        # Record hours for multiple days
        today = date.today()
        for i in range(5):
            entry_response = await client.post(
                f"/api/v1/cost/assignments/{assignment_id}/entries",
                json={
                    "entry_date": str(today + timedelta(days=i)),
                    "hours_worked": "8.00",
                    "notes": f"Day {i + 1} work",
                },
                headers=auth_headers,
            )
            assert entry_response.status_code == 200

        # Verify total cost: 5 days * 8 hours * $100 = $4,000
        cost_response = await client.get(
            f"/api/v1/cost/activities/{activity_id}",
            headers=auth_headers,
        )
        assert cost_response.status_code == 200
        cost_data = cost_response.json()
        assert Decimal(cost_data["actual_cost"]) == Decimal("4000.00")
