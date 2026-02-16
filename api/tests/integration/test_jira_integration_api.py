"""Integration tests for Jira Integration API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def jira_context(client: AsyncClient) -> dict:
    """Create user, program, WBS, and activity for Jira testing."""
    email = f"jira_{uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "TestPass123!",
            "full_name": "Jira Tester",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TestPass123!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create program
    prog_resp = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={
            "name": "Jira Test Program",
            "code": f"JR-{uuid4().hex[:6]}",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "budget_at_completion": "500000.00",
        },
    )
    assert prog_resp.status_code == 201
    program = prog_resp.json()
    program_id = program["id"]

    # Create WBS
    wbs_resp = await client.post(
        "/api/v1/wbs",
        json={"program_id": program_id, "name": "Jira WP", "wbs_code": "1.1"},
        headers=headers,
    )
    assert wbs_resp.status_code == 201
    wbs = wbs_resp.json()

    # Create activity
    act_resp = await client.post(
        "/api/v1/activities",
        json={
            "program_id": program_id,
            "wbs_id": wbs["id"],
            "name": "Jira Linked Activity",
            "code": "JLA-001",
            "duration": 10,
        },
        headers=headers,
    )
    assert act_resp.status_code == 201
    activity = act_resp.json()

    return {
        "headers": headers,
        "program_id": program_id,
        "wbs_id": wbs["id"],
        "activity_id": activity["id"],
    }


@pytest_asyncio.fixture
async def jira_integration(client: AsyncClient, jira_context: dict) -> dict:
    """Create a Jira integration record."""
    resp = await client.post(
        "/api/v1/jira/integrations",
        json={
            "program_id": jira_context["program_id"],
            "jira_url": "https://test.atlassian.net",
            "project_key": "TEST",
            "email": "jira@example.com",
            "api_token": "test-api-token-12345",
        },
    )
    assert resp.status_code == 201, f"Integration creation failed: {resp.text}"
    return {**jira_context, "integration": resp.json()}


class TestJiraIntegrationCRUD:
    """Tests for Jira integration CRUD endpoints."""

    async def test_create_integration(
        self, client: AsyncClient, jira_context: dict
    ) -> None:
        """Should create Jira integration."""
        resp = await client.post(
            "/api/v1/jira/integrations",
            json={
                "program_id": jira_context["program_id"],
                "jira_url": "https://test.atlassian.net",
                "project_key": "TEST",
                "email": "jira@example.com",
                "api_token": "test-api-token-12345",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["program_id"] == jira_context["program_id"]
        assert data["project_key"] == "TEST"
        assert data["sync_enabled"] is True

    async def test_get_integration(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should get integration by ID."""
        integration_id = jira_integration["integration"]["id"]
        resp = await client.get(
            f"/api/v1/jira/integrations/{integration_id}",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == integration_id

    async def test_get_integration_by_program(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should get integration by program ID."""
        resp = await client.get(
            f"/api/v1/jira/programs/{jira_integration['program_id']}/integration",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["program_id"] == jira_integration["program_id"]

    async def test_update_integration(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should update integration settings."""
        integration_id = jira_integration["integration"]["id"]
        resp = await client.patch(
            f"/api/v1/jira/integrations/{integration_id}",
            json={"sync_enabled": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sync_enabled"] is False

    async def test_delete_integration(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should delete integration."""
        integration_id = jira_integration["integration"]["id"]
        resp = await client.delete(
            f"/api/v1/jira/integrations/{integration_id}",
        )
        assert resp.status_code == 204

        # Verify deleted
        resp = await client.get(
            f"/api/v1/jira/integrations/{integration_id}",
        )
        assert resp.status_code == 404

    async def test_duplicate_integration(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should return 409 for duplicate program integration."""
        resp = await client.post(
            "/api/v1/jira/integrations",
            json={
                "program_id": jira_integration["program_id"],
                "jira_url": "https://other.atlassian.net",
                "project_key": "OTHER",
                "email": "other@example.com",
                "api_token": "other-token",
            },
        )
        assert resp.status_code == 409

    async def test_get_integration_not_found(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 for nonexistent integration."""
        resp = await client.get(
            f"/api/v1/jira/integrations/{uuid4()}",
        )
        assert resp.status_code == 404

    async def test_get_program_integration_not_found(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 when program has no integration."""
        resp = await client.get(
            f"/api/v1/jira/programs/{uuid4()}/integration",
        )
        assert resp.status_code == 404

    async def test_update_not_found(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 when updating nonexistent integration."""
        resp = await client.patch(
            f"/api/v1/jira/integrations/{uuid4()}",
            json={"sync_enabled": False},
        )
        assert resp.status_code == 404

    async def test_delete_not_found(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 when deleting nonexistent integration."""
        resp = await client.delete(
            f"/api/v1/jira/integrations/{uuid4()}",
        )
        assert resp.status_code == 404

    async def test_create_program_not_found(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 when program doesn't exist."""
        resp = await client.post(
            "/api/v1/jira/integrations",
            json={
                "program_id": str(uuid4()),
                "jira_url": "https://test.atlassian.net",
                "project_key": "TEST",
                "email": "jira@example.com",
                "api_token": "test-token",
            },
        )
        assert resp.status_code == 404


class TestJiraConnectionTest:
    """Tests for POST /api/v1/jira/integrations/{id}/test."""

    async def test_connection_not_found(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 for nonexistent integration."""
        resp = await client.post(
            f"/api/v1/jira/integrations/{uuid4()}/test",
        )
        assert resp.status_code == 404

    async def test_connection_failure(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should return failure when connection fails (no real Jira)."""
        integration_id = jira_integration["integration"]["id"]
        resp = await client.post(
            f"/api/v1/jira/integrations/{integration_id}/test",
        )
        assert resp.status_code == 200
        data = resp.json()
        # Connection will fail since we're not connected to a real Jira
        assert data["success"] is False
        assert "message" in data


class TestJiraMappings:
    """Tests for Jira mapping endpoints."""

    async def test_create_wbs_mapping(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should create WBS-to-Epic mapping."""
        integration_id = jira_integration["integration"]["id"]
        resp = await client.post(
            f"/api/v1/jira/integrations/{integration_id}/mappings",
            json={
                "entity_type": "wbs",
                "wbs_id": jira_integration["wbs_id"],
                "jira_issue_key": "TEST-1",
                "sync_direction": "bidirectional",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["entity_type"] == "wbs"
        assert data["jira_issue_key"] == "TEST-1"

    async def test_create_activity_mapping(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should create Activity-to-Issue mapping."""
        integration_id = jira_integration["integration"]["id"]
        resp = await client.post(
            f"/api/v1/jira/integrations/{integration_id}/mappings",
            json={
                "entity_type": "activity",
                "activity_id": jira_integration["activity_id"],
                "jira_issue_key": "TEST-2",
                "sync_direction": "to_jira",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["entity_type"] == "activity"

    async def test_list_mappings(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should list mappings for integration."""
        integration_id = jira_integration["integration"]["id"]
        # Create a mapping first
        await client.post(
            f"/api/v1/jira/integrations/{integration_id}/mappings",
            json={
                "entity_type": "wbs",
                "wbs_id": jira_integration["wbs_id"],
                "jira_issue_key": "TEST-10",
                "sync_direction": "bidirectional",
            },
        )

        resp = await client.get(
            f"/api/v1/jira/integrations/{integration_id}/mappings",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    async def test_list_mappings_filter_by_type(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should filter mappings by entity type."""
        integration_id = jira_integration["integration"]["id"]
        # Create mappings of both types
        await client.post(
            f"/api/v1/jira/integrations/{integration_id}/mappings",
            json={
                "entity_type": "wbs",
                "wbs_id": jira_integration["wbs_id"],
                "jira_issue_key": "TEST-20",
                "sync_direction": "bidirectional",
            },
        )
        await client.post(
            f"/api/v1/jira/integrations/{integration_id}/mappings",
            json={
                "entity_type": "activity",
                "activity_id": jira_integration["activity_id"],
                "jira_issue_key": "TEST-21",
                "sync_direction": "to_jira",
            },
        )

        resp = await client.get(
            f"/api/v1/jira/integrations/{integration_id}/mappings",
            params={"entity_type": "wbs"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for mapping in data:
            assert mapping["entity_type"] == "wbs"

    async def test_delete_mapping(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should delete a mapping."""
        integration_id = jira_integration["integration"]["id"]
        create_resp = await client.post(
            f"/api/v1/jira/integrations/{integration_id}/mappings",
            json={
                "entity_type": "wbs",
                "wbs_id": jira_integration["wbs_id"],
                "jira_issue_key": "TEST-30",
                "sync_direction": "bidirectional",
            },
        )
        mapping_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/jira/mappings/{mapping_id}",
        )
        assert resp.status_code == 204

    async def test_delete_mapping_not_found(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 for nonexistent mapping."""
        resp = await client.delete(
            f"/api/v1/jira/mappings/{uuid4()}",
        )
        assert resp.status_code == 404

    async def test_create_mapping_integration_not_found(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 for nonexistent integration."""
        resp = await client.post(
            f"/api/v1/jira/integrations/{uuid4()}/mappings",
            json={
                "entity_type": "wbs",
                "wbs_id": str(uuid4()),
                "jira_issue_key": "TEST-99",
                "sync_direction": "bidirectional",
            },
        )
        assert resp.status_code == 404

    async def test_create_mapping_missing_entity(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should return 400 when entity ID missing for type."""
        integration_id = jira_integration["integration"]["id"]
        resp = await client.post(
            f"/api/v1/jira/integrations/{integration_id}/mappings",
            json={
                "entity_type": "wbs",
                # Missing wbs_id
                "jira_issue_key": "TEST-40",
                "sync_direction": "bidirectional",
            },
        )
        assert resp.status_code == 400

    async def test_create_mapping_entity_not_found(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should return 404 when referenced entity doesn't exist."""
        integration_id = jira_integration["integration"]["id"]
        resp = await client.post(
            f"/api/v1/jira/integrations/{integration_id}/mappings",
            json={
                "entity_type": "wbs",
                "wbs_id": str(uuid4()),
                "jira_issue_key": "TEST-50",
                "sync_direction": "bidirectional",
            },
        )
        assert resp.status_code == 404


class TestJiraSyncLogs:
    """Tests for sync log endpoints."""

    async def test_list_logs_empty(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should return empty log list for new integration."""
        integration_id = jira_integration["integration"]["id"]
        resp = await client.get(
            f"/api/v1/jira/integrations/{integration_id}/logs",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    async def test_list_logs_pagination(
        self, client: AsyncClient, jira_integration: dict
    ) -> None:
        """Should support pagination parameters."""
        integration_id = jira_integration["integration"]["id"]
        resp = await client.get(
            f"/api/v1/jira/integrations/{integration_id}/logs",
            params={"page": 1, "per_page": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["per_page"] == 5


class TestJiraSyncEndpoints:
    """Tests for sync operation endpoints."""

    async def test_sync_wbs_integration_not_found(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 when integration doesn't exist."""
        resp = await client.post(
            f"/api/v1/jira/integrations/{uuid4()}/sync/wbs",
            json={"entity_ids": [str(uuid4())]},
        )
        assert resp.status_code == 404

    async def test_sync_activities_integration_not_found(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 when integration doesn't exist."""
        resp = await client.post(
            f"/api/v1/jira/integrations/{uuid4()}/sync/activities",
            json={"entity_ids": [str(uuid4())]},
        )
        assert resp.status_code == 404
