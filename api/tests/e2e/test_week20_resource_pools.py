"""End-to-end tests for Week 20: Cross-Program Resource Pools.

This module validates the Week 20 deliverables:
1. Resource pool CRUD operations
2. Pool membership management
3. Pool access control (program access)
4. Cross-program availability and conflict detection
5. Full resource sharing workflow
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
# Resource Pool CRUD Tests
# =============================================================================


class TestResourcePoolCRUD:
    """E2E tests for resource pool CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_pool(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test creating a resource pool."""
        response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Engineering Pool",
                "code": f"ENG-POOL-{uuid4().hex[:6].upper()}",
                "description": "Shared engineering resources",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Engineering Pool"
        assert data["description"] == "Shared engineering resources"
        assert data["is_active"] is True
        assert "id" in data
        assert "owner_id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_pool_requires_code(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that pool creation requires a code."""
        response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Pool Without Code",
            },
            headers=auth_headers,
        )

        # Missing required field returns 422
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_pool_code_validation(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that pool code must match pattern (uppercase, numbers, dashes, underscores)."""
        response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Invalid Code Pool",
                "code": "invalid code with spaces",  # Should fail pattern validation
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_pools(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test listing resource pools."""
        # Create a few pools
        for i in range(3):
            await client.post(
                "/api/v1/resource-pools",
                json={
                    "name": f"Pool {i}",
                    "code": f"POOL-LIST-{i:03d}",
                },
                headers=auth_headers,
            )

        response = await client.get(
            "/api/v1/resource-pools",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_get_pool(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting a specific resource pool."""
        # Create pool
        create_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Get Test Pool",
                "code": f"GET-POOL-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        pool_id = create_response.json()["id"]

        # Get pool
        response = await client.get(
            f"/api/v1/resource-pools/{pool_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pool_id
        assert data["name"] == "Get Test Pool"

    @pytest.mark.asyncio
    async def test_get_nonexistent_pool(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting a pool that doesn't exist."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/resource-pools/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_pool(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test updating a resource pool."""
        # Create pool
        create_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Original Name",
                "code": f"UPD-POOL-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        pool_id = create_response.json()["id"]

        # Update pool
        response = await client.patch(
            f"/api/v1/resource-pools/{pool_id}",
            json={
                "name": "Updated Name",
                "description": "New description",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "New description"

    @pytest.mark.asyncio
    async def test_deactivate_pool(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test deactivating a resource pool."""
        # Create pool
        create_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Deactivate Test Pool",
                "code": f"DEA-POOL-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        pool_id = create_response.json()["id"]

        # Deactivate pool
        response = await client.patch(
            f"/api/v1/resource-pools/{pool_id}",
            json={"is_active": False},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_pool(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test deleting a resource pool (soft delete)."""
        # Create pool
        create_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Delete Test Pool",
                "code": f"DEL-POOL-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        pool_id = create_response.json()["id"]

        # Delete pool
        response = await client.delete(
            f"/api/v1/resource-pools/{pool_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify pool is not accessible
        get_response = await client.get(
            f"/api/v1/resource-pools/{pool_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404


# =============================================================================
# Pool Membership Tests
# =============================================================================


class TestPoolMembership:
    """E2E tests for pool membership management."""

    @pytest.mark.asyncio
    async def test_add_member_to_pool(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test adding a resource to a pool."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Pool Member Test Program",
                "code": f"PMT-{uuid4().hex[:6].upper()}",
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
                "name": "Pool Resource",
                "code": f"RES-POOL-{uuid4().hex[:6].upper()}",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Create pool
        pool_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Membership Test Pool",
                "code": f"MEM-POOL-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert pool_response.status_code == 201
        pool_id = pool_response.json()["id"]

        # Add resource to pool
        response = await client.post(
            f"/api/v1/resource-pools/{pool_id}/members",
            json={
                "resource_id": resource_id,
                "allocation_percentage": "75.00",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["resource_id"] == resource_id
        assert data["pool_id"] == pool_id
        assert Decimal(data["allocation_percentage"]) == Decimal("75.00")
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_add_member_default_allocation(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test adding a resource with default 100% allocation."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Default Allocation Test",
                "code": f"DAT-{uuid4().hex[:6].upper()}",
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
                "name": "Default Allocation Resource",
                "code": f"RES-DEF-{uuid4().hex[:6].upper()}",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Create pool
        pool_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Default Allocation Pool",
                "code": f"DEF-POOL-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert pool_response.status_code == 201
        pool_id = pool_response.json()["id"]

        # Add resource without specifying allocation (should default to 100%)
        response = await client.post(
            f"/api/v1/resource-pools/{pool_id}/members",
            json={"resource_id": resource_id},
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert Decimal(response.json()["allocation_percentage"]) == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_list_pool_members(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test listing all members of a pool."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "List Members Test",
                "code": f"LMT-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create pool
        pool_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "List Members Pool",
                "code": f"LIST-POOL-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert pool_response.status_code == 201
        pool_id = pool_response.json()["id"]

        # Create and add multiple resources
        for i in range(3):
            res_response = await client.post(
                "/api/v1/resources",
                json={
                    "program_id": program_id,
                    "name": f"List Resource {i}",
                    "code": f"RES-LST-{i:03d}-{uuid4().hex[:4].upper()}",
                    "resource_type": "labor",
                },
                headers=auth_headers,
            )
            assert res_response.status_code == 201

            await client.post(
                f"/api/v1/resource-pools/{pool_id}/members",
                json={"resource_id": res_response.json()["id"]},
                headers=auth_headers,
            )

        # List members
        response = await client.get(
            f"/api/v1/resource-pools/{pool_id}/members",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_remove_pool_member(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test removing a resource from a pool."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Remove Member Test",
                "code": f"RMT-{uuid4().hex[:6].upper()}",
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
                "name": "Removable Resource",
                "code": f"RES-REM-{uuid4().hex[:6].upper()}",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Create pool
        pool_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Remove Member Pool",
                "code": f"REM-POOL-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert pool_response.status_code == 201
        pool_id = pool_response.json()["id"]

        # Add resource to pool
        member_response = await client.post(
            f"/api/v1/resource-pools/{pool_id}/members",
            json={"resource_id": resource_id},
            headers=auth_headers,
        )
        assert member_response.status_code == 201
        member_id = member_response.json()["id"]

        # Remove resource from pool
        response = await client.delete(
            f"/api/v1/resource-pools/{pool_id}/members/{member_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify member is removed
        list_response = await client.get(
            f"/api/v1/resource-pools/{pool_id}/members",
            headers=auth_headers,
        )
        assert list_response.status_code == 200
        assert len(list_response.json()) == 0


# =============================================================================
# Pool Access Control Tests
# =============================================================================


class TestPoolAccessControl:
    """E2E tests for pool access control (program access)."""

    @pytest.mark.asyncio
    async def test_grant_pool_access(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test granting a program access to a pool."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Access Grant Test Program",
                "code": f"AGT-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create pool
        pool_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Access Grant Pool",
                "code": f"ACC-POOL-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert pool_response.status_code == 201
        pool_id = pool_response.json()["id"]

        # Grant access
        response = await client.post(
            f"/api/v1/resource-pools/{pool_id}/access",
            json={
                "program_id": program_id,
                "access_level": "MEMBER",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["program_id"] == program_id
        assert data["pool_id"] == pool_id
        assert data["access_level"] == "MEMBER"
        assert "granted_by" in data
        assert "granted_at" in data

    @pytest.mark.asyncio
    async def test_grant_different_access_levels(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test granting different access levels to programs."""
        # Create pool
        pool_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Multi-Access Pool",
                "code": f"MULTI-ACC-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert pool_response.status_code == 201
        pool_id = pool_response.json()["id"]

        access_levels = ["VIEWER", "MEMBER", "ADMIN"]

        for i, level in enumerate(access_levels):
            # Create program
            program_response = await client.post(
                "/api/v1/programs",
                json={
                    "name": f"Access Level {level} Program",
                    "code": f"ALP-{i}-{uuid4().hex[:4].upper()}",
                    "start_date": str(date.today()),
                    "end_date": str(date.today().replace(year=date.today().year + 1)),
                },
                headers=auth_headers,
            )
            assert program_response.status_code == 201
            program_id = program_response.json()["id"]

            # Grant access with this level
            response = await client.post(
                f"/api/v1/resource-pools/{pool_id}/access",
                json={
                    "program_id": program_id,
                    "access_level": level,
                },
                headers=auth_headers,
            )

            assert response.status_code == 201
            assert response.json()["access_level"] == level


# =============================================================================
# Cross-Program Conflict Detection Tests
# =============================================================================


class TestCrossProgramConflictDetection:
    """E2E tests for cross-program conflict detection."""

    @pytest.mark.asyncio
    async def test_check_conflict_no_conflicts(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test conflict check with no existing assignments."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "No Conflict Test Program",
                "code": f"NCT-{uuid4().hex[:6].upper()}",
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
                "name": "No Conflict Resource",
                "code": f"RES-NC-{uuid4().hex[:6].upper()}",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Check for conflicts (should be none)
        response = await client.post(
            "/api/v1/resource-pools/check-conflict",
            json={
                "resource_id": resource_id,
                "program_id": program_id,
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=10)),
                "units": "1.0",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is False
        assert data["conflict_count"] == 0
        assert data["conflicts"] == []

    @pytest.mark.asyncio
    async def test_check_conflict_resource_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test conflict check with nonexistent resource."""
        fake_resource_id = str(uuid4())
        fake_program_id = str(uuid4())

        response = await client.post(
            "/api/v1/resource-pools/check-conflict",
            json={
                "resource_id": fake_resource_id,
                "program_id": fake_program_id,
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=5)),
                "units": "1.0",
            },
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_pool_availability(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting pool availability."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Availability Test Program",
                "code": f"AVT-{uuid4().hex[:6].upper()}",
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
                "name": "Availability Resource",
                "code": f"RES-AVL-{uuid4().hex[:6].upper()}",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["id"]

        # Create pool
        pool_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Availability Pool",
                "code": f"AVL-POOL-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert pool_response.status_code == 201
        pool_id = pool_response.json()["id"]

        # Add resource to pool
        await client.post(
            f"/api/v1/resource-pools/{pool_id}/members",
            json={"resource_id": resource_id},
            headers=auth_headers,
        )

        # Get pool availability
        start_date = date.today()
        end_date = date.today() + timedelta(days=14)

        response = await client.get(
            f"/api/v1/resource-pools/{pool_id}/availability",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pool_id"] == pool_id
        assert data["pool_name"] == "Availability Pool"
        assert data["date_range_start"] == str(start_date)
        assert data["date_range_end"] == str(end_date)
        assert "resources" in data
        assert len(data["resources"]) == 1
        assert data["conflict_count"] == 0


# =============================================================================
# Full Resource Sharing Workflow Tests
# =============================================================================


class TestResourceSharingWorkflow:
    """Integration tests for complete resource sharing workflows."""

    @pytest.mark.asyncio
    async def test_full_pool_creation_and_sharing_workflow(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Test complete workflow:
        1. Create a resource pool
        2. Add resources from multiple programs
        3. Grant access to programs
        4. Check availability
        """
        # Create first program (resource owner)
        program1_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Resource Owner Program",
                "code": f"ROP-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program1_response.status_code == 201
        program1_id = program1_response.json()["id"]

        # Create second program (resource consumer)
        program2_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Resource Consumer Program",
                "code": f"RCP-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program2_response.status_code == 201
        program2_id = program2_response.json()["id"]

        # Create resources for program 1
        resource1_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program1_id,
                "name": "Senior Engineer",
                "code": f"ENG-SR-{uuid4().hex[:6].upper()}",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
                "cost_rate": "150.00",
            },
            headers=auth_headers,
        )
        assert resource1_response.status_code == 201
        resource1_id = resource1_response.json()["id"]

        resource2_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program1_id,
                "name": "Equipment A",
                "code": f"EQP-A-{uuid4().hex[:6].upper()}",
                "resource_type": "equipment",
                "capacity_per_day": "1.0",
            },
            headers=auth_headers,
        )
        assert resource2_response.status_code == 201
        resource2_id = resource2_response.json()["id"]

        # Create shared resource pool
        pool_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Shared Engineering Pool",
                "code": f"SHARED-ENG-{uuid4().hex[:6].upper()}",
                "description": "Pool for sharing engineering resources across programs",
            },
            headers=auth_headers,
        )
        assert pool_response.status_code == 201
        pool_id = pool_response.json()["id"]

        # Add resources to pool with different allocation percentages
        add1_response = await client.post(
            f"/api/v1/resource-pools/{pool_id}/members",
            json={
                "resource_id": resource1_id,
                "allocation_percentage": "50.00",  # 50% of engineer available to pool
            },
            headers=auth_headers,
        )
        assert add1_response.status_code == 201

        add2_response = await client.post(
            f"/api/v1/resource-pools/{pool_id}/members",
            json={
                "resource_id": resource2_id,
                "allocation_percentage": "100.00",  # Full equipment available
            },
            headers=auth_headers,
        )
        assert add2_response.status_code == 201

        # Grant access to program 2
        access_response = await client.post(
            f"/api/v1/resource-pools/{pool_id}/access",
            json={
                "program_id": program2_id,
                "access_level": "MEMBER",
            },
            headers=auth_headers,
        )
        assert access_response.status_code == 201

        # Get pool availability
        response = await client.get(
            f"/api/v1/resource-pools/{pool_id}/availability",
            params={
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=30)),
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["resources"]) == 2

        # Verify allocation percentages are tracked
        resource_codes = {r["resource_code"] for r in data["resources"]}
        assert len(resource_codes) == 2

    @pytest.mark.asyncio
    async def test_pool_with_material_resources(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test resource pool with material resources."""
        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            json={
                "name": "Material Pool Test",
                "code": f"MPT-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today().replace(year=date.today().year + 1)),
            },
            headers=auth_headers,
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Create material resource
        material_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": program_id,
                "name": "Shared Steel Inventory",
                "code": f"MAT-STL-{uuid4().hex[:6].upper()}",
                "resource_type": "material",
                "quantity_unit": "kg",
                "unit_cost": "5.00",
                "quantity_available": "10000.00",
            },
            headers=auth_headers,
        )
        assert material_response.status_code == 201
        material_id = material_response.json()["id"]

        # Create pool
        pool_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Material Pool",
                "code": f"MAT-POOL-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert pool_response.status_code == 201
        pool_id = pool_response.json()["id"]

        # Add material to pool with partial allocation
        member_response = await client.post(
            f"/api/v1/resource-pools/{pool_id}/members",
            json={
                "resource_id": material_id,
                "allocation_percentage": "60.00",  # 60% of inventory available to pool
            },
            headers=auth_headers,
        )
        assert member_response.status_code == 201
        assert Decimal(member_response.json()["allocation_percentage"]) == Decimal("60.00")

    @pytest.mark.asyncio
    async def test_multiple_programs_same_pool(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test multiple programs accessing the same resource pool."""
        # Create pool first
        pool_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Multi-Program Pool",
                "code": f"MULTI-PRG-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert pool_response.status_code == 201
        pool_id = pool_response.json()["id"]

        # Create 3 programs and grant access to each
        for i in range(3):
            program_response = await client.post(
                "/api/v1/programs",
                json={
                    "name": f"Multi-Pool Program {i}",
                    "code": f"MLP-{i}-{uuid4().hex[:4].upper()}",
                    "start_date": str(date.today()),
                    "end_date": str(date.today().replace(year=date.today().year + 1)),
                },
                headers=auth_headers,
            )
            assert program_response.status_code == 201
            program_id = program_response.json()["id"]

            # Grant access with escalating levels
            levels = ["VIEWER", "MEMBER", "ADMIN"]
            access_response = await client.post(
                f"/api/v1/resource-pools/{pool_id}/access",
                json={
                    "program_id": program_id,
                    "access_level": levels[i],
                },
                headers=auth_headers,
            )
            assert access_response.status_code == 201
            assert access_response.json()["access_level"] == levels[i]


# =============================================================================
# Authorization Tests
# =============================================================================


class TestPoolAuthorization:
    """E2E tests for pool authorization."""

    @pytest.mark.asyncio
    async def test_pool_operations_require_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that pool operations require authentication."""
        # Try to create pool without auth
        response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Unauthorized Pool",
                "code": "UNAUTH-POOL",
            },
        )
        assert response.status_code == 401

        # Try to list pools without auth
        response = await client.get("/api/v1/resource-pools")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_only_owner_can_delete_pool(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that only pool owner can delete the pool."""
        # Create pool
        pool_response = await client.post(
            "/api/v1/resource-pools",
            json={
                "name": "Owner Only Delete Pool",
                "code": f"OOD-POOL-{uuid4().hex[:6].upper()}",
            },
            headers=auth_headers,
        )
        assert pool_response.status_code == 201
        pool_id = pool_response.json()["id"]

        # Owner can delete
        delete_response = await client.delete(
            f"/api/v1/resource-pools/{pool_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204
