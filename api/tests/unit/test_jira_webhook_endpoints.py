"""Unit tests for Jira webhook endpoint functions."""

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.v1.endpoints.jira_webhook import (
    _create_processor,
    receive_jira_webhook,
    receive_jira_webhook_for_integration,
    webhook_health_check,
)

# Module path used for patching symbols inside the endpoint module.
_MOD = "src.api.v1.endpoints.jira_webhook"


@dataclass
class FakeWebhookResult:
    """Lightweight stand-in for WebhookResult to avoid importing the real dataclass."""

    success: bool
    event_type: str
    issue_key: str | None = None
    entity_type: str | None = None
    entity_id: Any = None
    action_taken: str | None = None
    error_message: str | None = None
    duration_ms: int = 0


def _make_request(body: bytes | None = None, json_data: dict | None = None) -> MagicMock:
    """Create a mock Request with configurable body and JSON data."""
    mock_request = MagicMock()
    mock_request.body = AsyncMock(return_value=body or b"{}")
    mock_request.json = AsyncMock(return_value=json_data or {})
    # Required for @limiter.limit decorator (slowapi)
    mock_request.client = MagicMock()
    mock_request.client.host = "127.0.0.1"
    mock_request.scope = {"type": "http", "path": "/api/v1/webhooks/jira"}
    mock_request.url = MagicMock()
    mock_request.url.path = "/api/v1/webhooks/jira"
    return mock_request


def _make_valid_payload(event: str = "jira:issue_updated", issue_key: str = "PROJ-42") -> dict:
    """Return a minimal valid webhook payload dict."""
    return {
        "webhookEvent": event,
        "issue": {"key": issue_key, "id": "10042"},
        "timestamp": 1700000000,
    }


# ---------------------------------------------------------------------------
# Tests for receive_jira_webhook (generic endpoint)
# ---------------------------------------------------------------------------


class TestReceiveJiraWebhook:
    """Tests for the generic receive_jira_webhook endpoint."""

    @pytest.mark.asyncio
    async def test_webhook_success_issue_updated(self):
        """Should process an issue-updated webhook and return success dict."""
        payload_dict = _make_valid_payload("jira:issue_updated", "PROJ-10")
        mock_request = _make_request(body=b"{}", json_data=payload_dict)
        mock_db = AsyncMock()

        fake_result = FakeWebhookResult(
            success=True,
            event_type="jira:issue_updated",
            issue_key="PROJ-10",
            action_taken="updated_activity",
            duration_ms=42,
        )

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = None
            mock_processor = MagicMock()
            mock_processor.process_webhook = AsyncMock(return_value=fake_result)
            mock_cp.return_value = mock_processor

            result = await receive_jira_webhook(mock_request, mock_db)

        assert result["success"] is True
        assert result["event_type"] == "jira:issue_updated"
        assert result["issue_key"] == "PROJ-10"
        assert result["action"] == "updated_activity"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_success_issue_created(self):
        """Should handle issue-created events."""
        payload_dict = _make_valid_payload("jira:issue_created", "PROJ-99")
        mock_request = _make_request(body=b"{}", json_data=payload_dict)
        mock_db = AsyncMock()

        fake_result = FakeWebhookResult(
            success=True,
            event_type="jira:issue_created",
            issue_key="PROJ-99",
            action_taken="created_mapping",
        )

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = None
            mock_processor = MagicMock()
            mock_processor.process_webhook = AsyncMock(return_value=fake_result)
            mock_cp.return_value = mock_processor

            result = await receive_jira_webhook(mock_request, mock_db)

        assert result["success"] is True
        assert result["event_type"] == "jira:issue_created"
        assert result["issue_key"] == "PROJ-99"

    @pytest.mark.asyncio
    async def test_webhook_success_issue_deleted(self):
        """Should handle issue-deleted events."""
        payload_dict = _make_valid_payload("jira:issue_deleted", "PROJ-7")
        mock_request = _make_request(body=b"{}", json_data=payload_dict)
        mock_db = AsyncMock()

        fake_result = FakeWebhookResult(
            success=True,
            event_type="jira:issue_deleted",
            issue_key="PROJ-7",
            action_taken="deactivated_mapping",
        )

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = None
            mock_processor = MagicMock()
            mock_processor.process_webhook = AsyncMock(return_value=fake_result)
            mock_cp.return_value = mock_processor

            result = await receive_jira_webhook(mock_request, mock_db)

        assert result["success"] is True
        assert result["action"] == "deactivated_mapping"

    @pytest.mark.asyncio
    async def test_webhook_invalid_payload_returns_400(self):
        """Should raise HTTPException 400 when JSON cannot be parsed into schema."""
        mock_request = _make_request(body=b"bad", json_data={"not_valid": True})
        mock_db = AsyncMock()

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = None

            with pytest.raises(HTTPException) as exc_info:
                await receive_jira_webhook(mock_request, mock_db)

            assert exc_info.value.status_code == 400
            assert "Invalid webhook payload" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_webhook_signature_valid(self):
        """Should proceed when signature verification passes."""
        payload_dict = _make_valid_payload()
        mock_request = _make_request(
            body=b'{"webhookEvent":"jira:issue_updated"}',
            json_data=payload_dict,
        )
        mock_db = AsyncMock()

        fake_result = FakeWebhookResult(
            success=True,
            event_type="jira:issue_updated",
            issue_key="PROJ-42",
            action_taken="updated_activity",
        )

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = "super-secret"
            mock_processor = MagicMock()
            mock_processor.verify_signature = MagicMock(return_value=True)
            mock_processor.process_webhook = AsyncMock(return_value=fake_result)
            mock_cp.return_value = mock_processor

            result = await receive_jira_webhook(
                mock_request,
                mock_db,
                x_hub_signature="sha256=abc",
            )

        assert result["success"] is True
        mock_processor.verify_signature.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_signature_invalid_returns_401(self):
        """Should raise HTTPException 401 when signature verification fails."""
        mock_request = _make_request(body=b"payload")
        mock_db = AsyncMock()

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = "my-secret"
            mock_processor = MagicMock()
            mock_processor.verify_signature = MagicMock(return_value=False)
            mock_cp.return_value = mock_processor

            with pytest.raises(HTTPException) as exc_info:
                await receive_jira_webhook(
                    mock_request,
                    mock_db,
                    x_hub_signature="sha256=wrong",
                )

            assert exc_info.value.status_code == 401
            assert "Invalid webhook signature" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_webhook_signature_missing_header_uses_empty_string(self):
        """Should use empty string when X-Hub-Signature header is absent."""
        mock_request = _make_request(body=b"payload")
        mock_db = AsyncMock()

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = "secret-configured"
            mock_processor = MagicMock()
            mock_processor.verify_signature = MagicMock(return_value=False)
            mock_cp.return_value = mock_processor

            with pytest.raises(HTTPException) as exc_info:
                await receive_jira_webhook(mock_request, mock_db)

            # verify_signature should have been called with "" for the signature
            mock_processor.verify_signature.assert_called_once_with(
                b"payload", "", "secret-configured"
            )
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_webhook_processing_error_returns_200_with_failure(self):
        """Should return 200 with success=False when processor raises exception."""
        payload_dict = _make_valid_payload("jira:issue_updated", "PROJ-5")
        mock_request = _make_request(body=b"{}", json_data=payload_dict)
        mock_db = AsyncMock()

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = None
            mock_processor = MagicMock()
            mock_processor.process_webhook = AsyncMock(
                side_effect=RuntimeError("Jira API connection timeout")
            )
            mock_cp.return_value = mock_processor

            result = await receive_jira_webhook(mock_request, mock_db)

        assert result["success"] is False
        assert "Processing error" in result["message"]
        assert "Jira API connection timeout" in result["message"]
        assert result["event_type"] == "jira:issue_updated"
        assert result["issue_key"] == "PROJ-5"
        assert result["action"] is None

    @pytest.mark.asyncio
    async def test_webhook_processing_error_no_issue_in_payload(self):
        """Should handle processing error when payload has no issue key."""
        payload_dict = {"webhookEvent": "jira:issue_updated", "issue": None}
        mock_request = _make_request(body=b"{}", json_data=payload_dict)
        mock_db = AsyncMock()

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = None
            mock_processor = MagicMock()
            mock_processor.process_webhook = AsyncMock(side_effect=ValueError("No mapping found"))
            mock_cp.return_value = mock_processor

            result = await receive_jira_webhook(mock_request, mock_db)

        assert result["success"] is False
        assert result["issue_key"] is None

    @pytest.mark.asyncio
    async def test_webhook_processor_result_failure(self):
        """Should return error message from processor when result.success is False."""
        payload_dict = _make_valid_payload("jira:issue_updated", "PROJ-11")
        mock_request = _make_request(body=b"{}", json_data=payload_dict)
        mock_db = AsyncMock()

        fake_result = FakeWebhookResult(
            success=False,
            event_type="jira:issue_updated",
            issue_key="PROJ-11",
            error_message="No matching mapping found",
        )

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = None
            mock_processor = MagicMock()
            mock_processor.process_webhook = AsyncMock(return_value=fake_result)
            mock_cp.return_value = mock_processor

            result = await receive_jira_webhook(mock_request, mock_db)

        assert result["success"] is False
        assert result["message"] == "No matching mapping found"

    @pytest.mark.asyncio
    async def test_webhook_commit_not_called_on_processing_error(self):
        """Should not commit when the processor raises an exception."""
        payload_dict = _make_valid_payload("jira:issue_updated", "PROJ-3")
        mock_request = _make_request(body=b"{}", json_data=payload_dict)
        mock_db = AsyncMock()

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = None
            mock_processor = MagicMock()
            mock_processor.process_webhook = AsyncMock(side_effect=RuntimeError("Unexpected error"))
            mock_cp.return_value = mock_processor

            await receive_jira_webhook(mock_request, mock_db)

        mock_db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Tests for receive_jira_webhook_for_integration (integration-scoped endpoint)
# ---------------------------------------------------------------------------


class TestReceiveJiraWebhookForIntegration:
    """Tests for the integration-specific webhook endpoint."""

    @pytest.mark.asyncio
    async def test_integration_webhook_success(self):
        """Should process webhook for a valid integration ID."""
        integration_id = uuid4()
        payload_dict = _make_valid_payload("jira:issue_updated", "PROJ-20")
        mock_request = _make_request(body=b"{}", json_data=payload_dict)
        mock_db = AsyncMock()

        fake_result = FakeWebhookResult(
            success=True,
            event_type="jira:issue_updated",
            issue_key="PROJ-20",
            action_taken="updated_activity",
            duration_ms=15,
        )

        mock_integration = MagicMock()
        mock_integration.id = integration_id

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}.JiraIntegrationRepository") as mock_repo_cls,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = None
            mock_repo = MagicMock()
            mock_repo.get = AsyncMock(return_value=mock_integration)
            mock_repo_cls.return_value = mock_repo

            mock_processor = MagicMock()
            mock_processor.process_webhook = AsyncMock(return_value=fake_result)
            mock_cp.return_value = mock_processor

            result = await receive_jira_webhook_for_integration(
                mock_request, mock_db, integration_id
            )

        assert result["success"] is True
        assert result["issue_key"] == "PROJ-20"
        mock_processor.process_webhook.assert_called_once()
        # Verify integration_id was passed to process_webhook
        call_kwargs = mock_processor.process_webhook.call_args
        assert call_kwargs.kwargs.get("integration_id") == integration_id
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_integration_not_found_returns_404(self):
        """Should raise HTTPException 404 when integration does not exist."""
        integration_id = uuid4()
        mock_request = _make_request(body=b"{}")
        mock_db = AsyncMock()

        with (
            patch(f"{_MOD}.JiraIntegrationRepository") as mock_repo_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await receive_jira_webhook_for_integration(mock_request, mock_db, integration_id)

            assert exc_info.value.status_code == 404
            assert str(integration_id) in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_integration_webhook_signature_invalid(self):
        """Should raise 401 when signature verification fails for integration endpoint."""
        integration_id = uuid4()
        mock_request = _make_request(body=b"payload-body")
        mock_db = AsyncMock()

        mock_integration = MagicMock()
        mock_integration.id = integration_id

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}.JiraIntegrationRepository") as mock_repo_cls,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = "integration-secret"
            mock_repo = MagicMock()
            mock_repo.get = AsyncMock(return_value=mock_integration)
            mock_repo_cls.return_value = mock_repo

            mock_processor = MagicMock()
            mock_processor.verify_signature = MagicMock(return_value=False)
            mock_cp.return_value = mock_processor

            with pytest.raises(HTTPException) as exc_info:
                await receive_jira_webhook_for_integration(
                    mock_request,
                    mock_db,
                    integration_id,
                    x_hub_signature="sha256=bad",
                )

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_integration_webhook_invalid_payload(self):
        """Should raise 400 for invalid payload on integration-specific endpoint."""
        integration_id = uuid4()
        mock_request = _make_request(body=b"{}", json_data={"garbage": True})
        mock_db = AsyncMock()

        mock_integration = MagicMock()
        mock_integration.id = integration_id

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}.JiraIntegrationRepository") as mock_repo_cls,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = None
            mock_repo = MagicMock()
            mock_repo.get = AsyncMock(return_value=mock_integration)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await receive_jira_webhook_for_integration(mock_request, mock_db, integration_id)

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_integration_webhook_processing_error(self):
        """Should return 200 with success=False on processing exception."""
        integration_id = uuid4()
        payload_dict = _make_valid_payload("jira:issue_updated", "PROJ-88")
        mock_request = _make_request(body=b"{}", json_data=payload_dict)
        mock_db = AsyncMock()

        mock_integration = MagicMock()
        mock_integration.id = integration_id

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}.JiraIntegrationRepository") as mock_repo_cls,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = None
            mock_repo = MagicMock()
            mock_repo.get = AsyncMock(return_value=mock_integration)
            mock_repo_cls.return_value = mock_repo

            mock_processor = MagicMock()
            mock_processor.process_webhook = AsyncMock(side_effect=RuntimeError("DB timeout"))
            mock_cp.return_value = mock_processor

            result = await receive_jira_webhook_for_integration(
                mock_request, mock_db, integration_id
            )

        assert result["success"] is False
        assert "DB timeout" in result["message"]
        assert result["issue_key"] == "PROJ-88"

    @pytest.mark.asyncio
    async def test_integration_webhook_commit_not_called_on_error(self):
        """Should not commit the session when processing raises an exception."""
        integration_id = uuid4()
        payload_dict = _make_valid_payload("jira:issue_updated", "PROJ-50")
        mock_request = _make_request(body=b"{}", json_data=payload_dict)
        mock_db = AsyncMock()

        mock_integration = MagicMock()
        mock_integration.id = integration_id

        with (
            patch(f"{_MOD}.settings") as mock_settings,
            patch(f"{_MOD}.JiraIntegrationRepository") as mock_repo_cls,
            patch(f"{_MOD}._create_processor") as mock_cp,
            patch(f"{_MOD}.logger"),
        ):
            mock_settings.jira_webhook_secret = None
            mock_repo = MagicMock()
            mock_repo.get = AsyncMock(return_value=mock_integration)
            mock_repo_cls.return_value = mock_repo

            mock_processor = MagicMock()
            mock_processor.process_webhook = AsyncMock(side_effect=RuntimeError("fail"))
            mock_cp.return_value = mock_processor

            await receive_jira_webhook_for_integration(mock_request, mock_db, integration_id)

        mock_db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Tests for webhook_health_check
# ---------------------------------------------------------------------------


class TestWebhookHealthCheck:
    """Tests for the webhook health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self):
        """Should return healthy status with no webhook secret configured."""
        with patch(f"{_MOD}.settings") as mock_settings:
            mock_settings.jira_webhook_secret = None

            result = await webhook_health_check()

        assert result["status"] == "healthy"
        assert result["service"] == "jira-webhook-receiver"
        assert result["signature_verification"] is False

    @pytest.mark.asyncio
    async def test_health_check_with_signature_verification_enabled(self):
        """Should report signature_verification=True when secret is configured."""
        with patch(f"{_MOD}.settings") as mock_settings:
            mock_settings.jira_webhook_secret = "configured-secret"

            result = await webhook_health_check()

        assert result["status"] == "healthy"
        assert result["signature_verification"] is True


# ---------------------------------------------------------------------------
# Tests for _create_processor helper
# ---------------------------------------------------------------------------


class TestCreateProcessor:
    """Tests for the _create_processor factory function."""

    def test_create_processor_returns_processor_instance(self):
        """Should construct a JiraWebhookProcessor with all required repos."""
        mock_db = AsyncMock()

        with patch(f"{_MOD}.JiraWebhookProcessor") as mock_proc_cls:
            mock_proc_cls.return_value = MagicMock()
            processor = _create_processor(mock_db)

        mock_proc_cls.assert_called_once()
        call_kwargs = mock_proc_cls.call_args.kwargs
        assert "integration_repo" in call_kwargs
        assert "mapping_repo" in call_kwargs
        assert "activity_repo" in call_kwargs
        assert "wbs_repo" in call_kwargs
        assert "sync_log_repo" in call_kwargs

    def test_create_processor_passes_db_to_repos(self):
        """Should instantiate each repository with the provided db session."""
        mock_db = AsyncMock()

        with (
            patch(f"{_MOD}.JiraIntegrationRepository") as mock_int_repo,
            patch(f"{_MOD}.JiraMappingRepository") as mock_map_repo,
            patch(f"{_MOD}.ActivityRepository") as mock_act_repo,
            patch(f"{_MOD}.WBSElementRepository") as mock_wbs_repo,
            patch(f"{_MOD}.JiraSyncLogRepository") as mock_sync_repo,
            patch(f"{_MOD}.JiraWebhookProcessor"),
        ):
            _create_processor(mock_db)

        mock_int_repo.assert_called_once_with(mock_db)
        mock_map_repo.assert_called_once_with(mock_db)
        mock_act_repo.assert_called_once_with(mock_db)
        mock_wbs_repo.assert_called_once_with(mock_db)
        mock_sync_repo.assert_called_once_with(mock_db)


# ---------------------------------------------------------------------------
# Tests for WebhookResponse helper class
# ---------------------------------------------------------------------------


class TestWebhookResponse:
    """Tests for the WebhookResponse helper class."""

    def test_to_dict_full(self):
        """Should convert all fields to a dictionary."""
        from src.api.v1.endpoints.jira_webhook import WebhookResponse

        resp = WebhookResponse(
            success=True,
            message="Done",
            event_type="jira:issue_updated",
            issue_key="PROJ-1",
            action="updated_activity",
        )
        d = resp.to_dict()
        assert d == {
            "success": True,
            "message": "Done",
            "event_type": "jira:issue_updated",
            "issue_key": "PROJ-1",
            "action": "updated_activity",
        }

    def test_to_dict_defaults(self):
        """Should include None defaults when optional fields are omitted."""
        from src.api.v1.endpoints.jira_webhook import WebhookResponse

        resp = WebhookResponse(success=False, message="Error")
        d = resp.to_dict()
        assert d["success"] is False
        assert d["event_type"] is None
        assert d["issue_key"] is None
        assert d["action"] is None
