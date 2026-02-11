"""Integration tests for Resource Pools API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_pool(
    client: AsyncClient,
    headers: dict[str, str],
    name: str = "Shared Engineers",
    code: str = "POOL-001",
) -> dict:
    """Create a resource pool and return its JSON."""
    resp = await client.post(
        "/api/v1/resource-pools",
        json={"name": name, "code": code, "description": "Test pool"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_resource(
    client: AsyncClient,
    headers: dict[str, str],
    program_id: str,
    code: str = "RES-001",
) -> dict:
    """Create a resource and return its JSON."""
    resp = await client.post(
        "/api/v1/resources",
        json={
            "program_id": program_id,
            "name": f"Resource {code}",
            "code": code,
            "resource_type": "labor",
            "capacity_per_day": "8.0",
            "cost_rate": "100.00",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ===========================================================================
# Auth
# ===========================================================================


class TestResourcePoolsAuth:
    """Tests for authentication requirements on resource pool endpoints."""

    async def test_create_pool_requires_auth(self, client: AsyncClient):
        """Should return 401 when creating pool without auth."""
        response = await client.post(
            "/api/v1/resource-pools",
            json={"name": "x", "code": "X-001"},
        )
        assert response.status_code == 401

    async def test_list_pools_requires_auth(self, client: AsyncClient):
        """Should return 401 when listing pools without auth."""
        response = await client.get("/api/v1/resource-pools")
        assert response.status_code == 401

    async def test_get_pool_requires_auth(self, client: AsyncClient):
        """Should return 401 when getting pool without auth."""
        response = await client.get("/api/v1/resource-pools/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 401

    async def test_delete_pool_requires_auth(self, client: AsyncClient):
        """Should return 401 when deleting pool without auth."""
        response = await client.delete(
            "/api/v1/resource-pools/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401

    async def test_add_member_requires_auth(self, client: AsyncClient):
        """Should return 401 when adding member without auth."""
        response = await client.post(
            "/api/v1/resource-pools/00000000-0000-0000-0000-000000000000/members",
            json={"resource_id": "00000000-0000-0000-0000-000000000001"},
        )
        assert response.status_code == 401


# ===========================================================================
# CRUD
# ===========================================================================


class TestResourcePoolCRUD:
    """Tests for resource pool create / read / update / delete."""

    async def test_create_pool(self, client: AsyncClient, auth_headers: dict[str, str]):
        """Should create a pool and return 201."""
        pool = await _create_pool(client, auth_headers)
        assert pool["name"] == "Shared Engineers"
        assert pool["code"] == "POOL-001"
        assert pool["is_active"] is True

    async def test_list_pools(self, client: AsyncClient, auth_headers: dict[str, str]):
        """Should list pools owned by the current user."""
        await _create_pool(client, auth_headers, code="LIST-001")
        resp = await client.get("/api/v1/resource-pools", headers=auth_headers)
        assert resp.status_code == 200
        pools = resp.json()
        assert isinstance(pools, list)
        assert any(p["code"] == "LIST-001" for p in pools)

    async def test_get_pool_by_id(self, client: AsyncClient, auth_headers: dict[str, str]):
        """Should return a pool by ID."""
        pool = await _create_pool(client, auth_headers, code="GET-001")
        resp = await client.get(f"/api/v1/resource-pools/{pool['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == "GET-001"

    async def test_get_pool_not_found(self, client: AsyncClient, auth_headers: dict[str, str]):
        """Should return 404 for nonexistent pool."""
        resp = await client.get(
            "/api/v1/resource-pools/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_pool(self, client: AsyncClient, auth_headers: dict[str, str]):
        """Should update pool name/description."""
        pool = await _create_pool(client, auth_headers, code="UPD-001")
        resp = await client.patch(
            f"/api/v1/resource-pools/{pool['id']}",
            json={"name": "Renamed Pool"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Pool"

    async def test_update_pool_not_found(self, client: AsyncClient, auth_headers: dict[str, str]):
        """Should return 404 when updating nonexistent pool."""
        resp = await client.patch(
            "/api/v1/resource-pools/00000000-0000-0000-0000-000000000000",
            json={"name": "x"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_delete_pool(self, client: AsyncClient, auth_headers: dict[str, str]):
        """Should soft-delete a pool."""
        pool = await _create_pool(client, auth_headers, code="DEL-001")
        resp = await client.delete(f"/api/v1/resource-pools/{pool['id']}", headers=auth_headers)
        assert resp.status_code == 204

        # Subsequent GET should return 404
        resp2 = await client.get(f"/api/v1/resource-pools/{pool['id']}", headers=auth_headers)
        assert resp2.status_code == 404

    async def test_delete_pool_not_found(self, client: AsyncClient, auth_headers: dict[str, str]):
        """Should return 404 when deleting nonexistent pool."""
        resp = await client.delete(
            "/api/v1/resource-pools/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ===========================================================================
# Pool Members
# ===========================================================================


class TestPoolMembers:
    """Tests for pool member add / list / remove."""

    async def test_add_member(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should add a resource to a pool."""
        pool = await _create_pool(client, auth_headers, code="MEM-001")
        resource = await _create_resource(client, auth_headers, test_program["id"], code="MR-001")
        resp = await client.post(
            f"/api/v1/resource-pools/{pool['id']}/members",
            json={
                "resource_id": resource["id"],
                "allocation_percentage": "80.00",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        member = resp.json()
        assert member["resource_id"] == resource["id"]

    async def test_list_members(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should list members of a pool."""
        pool = await _create_pool(client, auth_headers, code="LM-001")
        resource = await _create_resource(client, auth_headers, test_program["id"], code="LMR-001")
        await client.post(
            f"/api/v1/resource-pools/{pool['id']}/members",
            json={"resource_id": resource["id"]},
            headers=auth_headers,
        )
        resp = await client.get(
            f"/api/v1/resource-pools/{pool['id']}/members",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        members = resp.json()
        assert isinstance(members, list)
        assert len(members) == 1

    async def test_remove_member(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should remove a member from a pool."""
        pool = await _create_pool(client, auth_headers, code="RM-001")
        resource = await _create_resource(client, auth_headers, test_program["id"], code="RMR-001")
        add_resp = await client.post(
            f"/api/v1/resource-pools/{pool['id']}/members",
            json={"resource_id": resource["id"]},
            headers=auth_headers,
        )
        member_id = add_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/resource-pools/{pool['id']}/members/{member_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    async def test_add_member_pool_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Should return 404 when adding member to nonexistent pool."""
        resp = await client.post(
            "/api/v1/resource-pools/00000000-0000-0000-0000-000000000000/members",
            json={"resource_id": "00000000-0000-0000-0000-000000000001"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_list_members_pool_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Should return 404 when listing members of nonexistent pool."""
        resp = await client.get(
            "/api/v1/resource-pools/00000000-0000-0000-0000-000000000000/members",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_remove_member_not_found(self, client: AsyncClient, auth_headers: dict[str, str]):
        """Should return 404 when removing nonexistent member."""
        pool = await _create_pool(client, auth_headers, code="RNF-001")
        resp = await client.delete(
            f"/api/v1/resource-pools/{pool['id']}/members/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ===========================================================================
# Pool Access
# ===========================================================================


class TestPoolAccess:
    """Tests for granting / revoking pool access to programs."""

    async def test_grant_access(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should grant a program access to a pool."""
        pool = await _create_pool(client, auth_headers, code="ACC-001")
        resp = await client.post(
            f"/api/v1/resource-pools/{pool['id']}/access",
            json={
                "program_id": test_program["id"],
                "access_level": "VIEWER",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        access = resp.json()
        assert access["program_id"] == test_program["id"]

    async def test_grant_access_pool_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should return 404 when granting access to nonexistent pool."""
        resp = await client.post(
            "/api/v1/resource-pools/00000000-0000-0000-0000-000000000000/access",
            json={
                "program_id": test_program["id"],
                "access_level": "VIEWER",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ===========================================================================
# Pool Availability & Conflict Check
# ===========================================================================


class TestPoolAvailability:
    """Tests for availability and conflict checking endpoints."""

    async def test_availability_pool_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Should return 404 for nonexistent pool availability."""
        resp = await client.get(
            "/api/v1/resource-pools/00000000-0000-0000-0000-000000000000/availability",
            params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_conflict_check_requires_auth(self, client: AsyncClient):
        """Should return 401 for conflict check without auth."""
        resp = await client.post(
            "/api/v1/resource-pools/check-conflict",
            json={
                "resource_id": "00000000-0000-0000-0000-000000000000",
                "program_id": "00000000-0000-0000-0000-000000000001",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        )
        assert resp.status_code == 401

    async def test_conflict_check_resource_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Should return 404 for conflict check with nonexistent resource."""
        resp = await client.post(
            "/api/v1/resource-pools/check-conflict",
            json={
                "resource_id": "00000000-0000-0000-0000-000000000000",
                "program_id": "00000000-0000-0000-0000-000000000001",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_availability_with_pool(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should return availability data for a pool with members."""
        pool = await _create_pool(client, auth_headers, code="AVAIL-001")
        resource = await _create_resource(client, auth_headers, test_program["id"], code="AVR-001")
        await client.post(
            f"/api/v1/resource-pools/{pool['id']}/members",
            json={"resource_id": resource["id"]},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/resource-pools/{pool['id']}/availability",
            params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pool_id"] == pool["id"]
        assert "resources" in data
        assert "conflicts" in data
