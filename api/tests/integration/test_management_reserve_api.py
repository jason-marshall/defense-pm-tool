"""Integration tests for Management Reserve API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def mr_context(client: AsyncClient) -> dict:
    """Create user and program for MR testing."""
    email = f"mr_test_{uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "TestPass123!",
            "full_name": "MR Tester",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TestPass123!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    prog_resp = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={
            "name": "MR Test Program",
            "code": f"MR-{uuid4().hex[:6]}",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "budget_at_completion": "1000000.00",
        },
    )
    assert prog_resp.status_code == 201
    program = prog_resp.json()

    return {"headers": headers, "program_id": program["id"]}


@pytest_asyncio.fixture
async def initialized_mr(client: AsyncClient, mr_context: dict) -> dict:
    """Create a program with initialized MR balance."""
    resp = await client.post(
        f"/api/v1/mr/{mr_context['program_id']}/initialize",
        params={"initial_amount": "50000.00", "reason": "Initial MR allocation"},
        headers=mr_context["headers"],
    )
    assert resp.status_code == 201
    return {**mr_context, "mr_log": resp.json()}


class TestMRInitialization:
    """Tests for POST /api/v1/mr/{program_id}/initialize."""

    async def test_initialize_mr_success(
        self, client: AsyncClient, mr_context: dict
    ) -> None:
        """Should initialize MR with valid amount."""
        resp = await client.post(
            f"/api/v1/mr/{mr_context['program_id']}/initialize",
            params={"initial_amount": "50000.00"},
            headers=mr_context["headers"],
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["changes_in"] == "50000.00"
        assert data["ending_mr"] == "50000.00"

    async def test_initialize_mr_program_not_found(
        self, client: AsyncClient, mr_context: dict
    ) -> None:
        """Should return 404 for nonexistent program."""
        resp = await client.post(
            f"/api/v1/mr/{uuid4()}/initialize",
            params={"initial_amount": "50000.00"},
            headers=mr_context["headers"],
        )
        assert resp.status_code == 404

    async def test_initialize_mr_already_initialized(
        self, client: AsyncClient, initialized_mr: dict
    ) -> None:
        """Should return 400 when MR already initialized."""
        resp = await client.post(
            f"/api/v1/mr/{initialized_mr['program_id']}/initialize",
            params={"initial_amount": "10000.00"},
            headers=initialized_mr["headers"],
        )
        assert resp.status_code == 422

    async def test_initialize_mr_unauthenticated(
        self, client: AsyncClient, mr_context: dict
    ) -> None:
        """Should return 401 without auth."""
        resp = await client.post(
            f"/api/v1/mr/{mr_context['program_id']}/initialize",
            params={"initial_amount": "50000.00"},
        )
        assert resp.status_code == 401


class TestMRStatus:
    """Tests for GET /api/v1/mr/{program_id}."""

    async def test_get_status_empty(
        self, client: AsyncClient, mr_context: dict
    ) -> None:
        """Should return zero status when no MR initialized."""
        resp = await client.get(
            f"/api/v1/mr/{mr_context['program_id']}",
            headers=mr_context["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_balance"] == "0"
        assert data["change_count"] == 0

    async def test_get_status_after_initialization(
        self, client: AsyncClient, initialized_mr: dict
    ) -> None:
        """Should return correct balance after initialization."""
        resp = await client.get(
            f"/api/v1/mr/{initialized_mr['program_id']}",
            headers=initialized_mr["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_balance"] == "50000.00"
        assert data["change_count"] == 1

    async def test_get_status_program_not_found(
        self, client: AsyncClient, mr_context: dict
    ) -> None:
        """Should return 404 for nonexistent program."""
        resp = await client.get(
            f"/api/v1/mr/{uuid4()}",
            headers=mr_context["headers"],
        )
        assert resp.status_code == 404


class TestMRChanges:
    """Tests for POST /api/v1/mr/{program_id}/change."""

    async def test_record_increase(
        self, client: AsyncClient, initialized_mr: dict
    ) -> None:
        """Should record MR increase."""
        resp = await client.post(
            f"/api/v1/mr/{initialized_mr['program_id']}/change",
            json={
                "changes_in": "10000.00",
                "changes_out": "0",
                "reason": "Additional MR allocation",
            },
            headers=initialized_mr["headers"],
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["ending_mr"] == "60000.00"

    async def test_record_decrease(
        self, client: AsyncClient, initialized_mr: dict
    ) -> None:
        """Should record MR decrease."""
        resp = await client.post(
            f"/api/v1/mr/{initialized_mr['program_id']}/change",
            json={
                "changes_in": "0",
                "changes_out": "5000.00",
                "reason": "MR release to WP",
            },
            headers=initialized_mr["headers"],
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["ending_mr"] == "45000.00"

    async def test_negative_balance_error(
        self, client: AsyncClient, initialized_mr: dict
    ) -> None:
        """Should reject change resulting in negative balance."""
        resp = await client.post(
            f"/api/v1/mr/{initialized_mr['program_id']}/change",
            json={
                "changes_in": "0",
                "changes_out": "999999.00",
                "reason": "Exceeds balance",
            },
            headers=initialized_mr["headers"],
        )
        assert resp.status_code == 422

    async def test_zero_change_error(
        self, client: AsyncClient, initialized_mr: dict
    ) -> None:
        """Should reject zero changes."""
        resp = await client.post(
            f"/api/v1/mr/{initialized_mr['program_id']}/change",
            json={
                "changes_in": "0",
                "changes_out": "0",
                "reason": "No change",
            },
            headers=initialized_mr["headers"],
        )
        assert resp.status_code == 422

    async def test_change_program_not_found(
        self, client: AsyncClient, initialized_mr: dict
    ) -> None:
        """Should return 404 for nonexistent program."""
        resp = await client.post(
            f"/api/v1/mr/{uuid4()}/change",
            json={
                "changes_in": "1000.00",
                "changes_out": "0",
                "reason": "Test",
            },
            headers=initialized_mr["headers"],
        )
        assert resp.status_code == 404


class TestMRHistory:
    """Tests for GET /api/v1/mr/{program_id}/history."""

    async def test_get_history(
        self, client: AsyncClient, initialized_mr: dict
    ) -> None:
        """Should return history with entries."""
        resp = await client.get(
            f"/api/v1/mr/{initialized_mr['program_id']}/history",
            headers=initialized_mr["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    async def test_get_history_custom_limit(
        self, client: AsyncClient, initialized_mr: dict
    ) -> None:
        """Should respect custom limit."""
        resp = await client.get(
            f"/api/v1/mr/{initialized_mr['program_id']}/history",
            params={"limit": 1},
            headers=initialized_mr["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 1

    async def test_get_log_entry_by_id(
        self, client: AsyncClient, initialized_mr: dict
    ) -> None:
        """Should return specific log entry."""
        log_id = initialized_mr["mr_log"]["id"]
        resp = await client.get(
            f"/api/v1/mr/{initialized_mr['program_id']}/log/{log_id}",
            headers=initialized_mr["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == log_id

    async def test_get_log_entry_not_found(
        self, client: AsyncClient, initialized_mr: dict
    ) -> None:
        """Should return 404 for nonexistent log entry."""
        resp = await client.get(
            f"/api/v1/mr/{initialized_mr['program_id']}/log/{uuid4()}",
            headers=initialized_mr["headers"],
        )
        assert resp.status_code == 404

    async def test_history_program_not_found(
        self, client: AsyncClient, mr_context: dict
    ) -> None:
        """Should return 404 for nonexistent program."""
        resp = await client.get(
            f"/api/v1/mr/{uuid4()}/history",
            headers=mr_context["headers"],
        )
        assert resp.status_code == 404
