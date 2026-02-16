"""Integration tests for Jira Webhook API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def webhook_context(client: AsyncClient) -> dict:
    """Create user, program, WBS, activity, integration, and mapping for webhook tests."""
    email = f"webhook_{uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "TestPass123!",
            "full_name": "Webhook Tester",
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
            "name": "Webhook Test Program",
            "code": f"WH-{uuid4().hex[:6]}",
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
        json={"program_id": program_id, "name": "Webhook WP", "wbs_code": "1.1"},
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
            "name": "Webhook Activity",
            "code": "WH-001",
            "duration": 10,
        },
        headers=headers,
    )
    assert act_resp.status_code == 201
    activity = act_resp.json()

    # Create integration
    int_resp = await client.post(
        "/api/v1/jira/integrations",
        json={
            "program_id": program_id,
            "jira_url": "https://webhook-test.atlassian.net",
            "project_key": "WH",
            "email": "webhook@example.com",
            "api_token": "webhook-test-token",
        },
    )
    assert int_resp.status_code == 201
    integration = int_resp.json()

    # Create mapping
    map_resp = await client.post(
        f"/api/v1/jira/integrations/{integration['id']}/mappings",
        json={
            "entity_type": "activity",
            "activity_id": activity["id"],
            "jira_issue_key": "WH-100",
            "sync_direction": "bidirectional",
        },
    )
    assert map_resp.status_code == 201
    mapping = map_resp.json()

    return {
        "headers": headers,
        "program_id": program_id,
        "wbs_id": wbs["id"],
        "activity_id": activity["id"],
        "integration_id": integration["id"],
        "mapping_id": mapping["id"],
    }


class TestWebhookHealthCheck:
    """Tests for GET /api/v1/webhooks/jira/health."""

    async def test_health_check(self, client: AsyncClient) -> None:
        """Should return healthy status."""
        resp = await client.get("/api/v1/webhooks/jira/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "jira-webhook-receiver"

    async def test_health_check_fields(self, client: AsyncClient) -> None:
        """Should include signature verification status."""
        resp = await client.get("/api/v1/webhooks/jira/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "signature_verification" in data


class TestGenericWebhook:
    """Tests for POST /api/v1/webhooks/jira."""

    async def test_issue_created_event(
        self, client: AsyncClient, webhook_context: dict
    ) -> None:
        """Should process issue_created event."""
        resp = await client.post(
            "/api/v1/webhooks/jira",
            json={
                "webhookEvent": "jira:issue_created",
                "issue": {
                    "key": "WH-100",
                    "fields": {
                        "summary": "New Issue",
                        "status": {"name": "To Do"},
                    },
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert data["event_type"] == "jira:issue_created"

    async def test_issue_updated_event(
        self, client: AsyncClient, webhook_context: dict
    ) -> None:
        """Should process issue_updated event."""
        resp = await client.post(
            "/api/v1/webhooks/jira",
            json={
                "webhookEvent": "jira:issue_updated",
                "issue": {
                    "key": "WH-100",
                    "fields": {
                        "summary": "Updated Issue",
                        "status": {"name": "In Progress"},
                    },
                },
                "changelog": {
                    "items": [
                        {
                            "field": "status",
                            "fromString": "To Do",
                            "toString": "In Progress",
                        }
                    ]
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_type"] == "jira:issue_updated"

    async def test_issue_deleted_event(
        self, client: AsyncClient, webhook_context: dict
    ) -> None:
        """Should process issue_deleted event."""
        resp = await client.post(
            "/api/v1/webhooks/jira",
            json={
                "webhookEvent": "jira:issue_deleted",
                "issue": {
                    "key": "WH-100",
                    "fields": {"summary": "Deleted Issue"},
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_type"] == "jira:issue_deleted"

    async def test_unknown_event(
        self, client: AsyncClient
    ) -> None:
        """Should handle unknown event gracefully."""
        resp = await client.post(
            "/api/v1/webhooks/jira",
            json={
                "webhookEvent": "jira:unknown_event",
                "issue": {"key": "TEST-1"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_type"] == "jira:unknown_event"

    async def test_invalid_payload(
        self, client: AsyncClient
    ) -> None:
        """Should return 400 for invalid payload."""
        resp = await client.post(
            "/api/v1/webhooks/jira",
            json={"invalid": "data"},
        )
        assert resp.status_code == 400

    async def test_no_matching_mapping(
        self, client: AsyncClient
    ) -> None:
        """Should handle event with no matching mapping."""
        resp = await client.post(
            "/api/v1/webhooks/jira",
            json={
                "webhookEvent": "jira:issue_created",
                "issue": {
                    "key": "NOMATCH-999",
                    "fields": {"summary": "Unmapped Issue"},
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should succeed but with no action
        assert "success" in data


class TestIntegrationSpecificWebhook:
    """Tests for POST /api/v1/webhooks/jira/{integration_id}."""

    async def test_webhook_for_integration(
        self, client: AsyncClient, webhook_context: dict
    ) -> None:
        """Should process webhook for specific integration."""
        resp = await client.post(
            f"/api/v1/webhooks/jira/{webhook_context['integration_id']}",
            json={
                "webhookEvent": "jira:issue_updated",
                "issue": {
                    "key": "WH-100",
                    "fields": {
                        "summary": "Updated",
                        "status": {"name": "Done"},
                    },
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data

    async def test_integration_not_found(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 for nonexistent integration."""
        resp = await client.post(
            f"/api/v1/webhooks/jira/{uuid4()}",
            json={
                "webhookEvent": "jira:issue_created",
                "issue": {"key": "TEST-1"},
            },
        )
        assert resp.status_code == 404

    async def test_invalid_payload_for_integration(
        self, client: AsyncClient, webhook_context: dict
    ) -> None:
        """Should return 400 for invalid payload."""
        resp = await client.post(
            f"/api/v1/webhooks/jira/{webhook_context['integration_id']}",
            json={"bad": "payload"},
        )
        assert resp.status_code == 400
