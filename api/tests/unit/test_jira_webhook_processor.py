"""Unit tests for Jira Webhook Processor."""

import hashlib
import hmac
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.services.jira_webhook_processor import (
    WEBHOOK_EVENT_ISSUE_CREATED,
    WEBHOOK_EVENT_ISSUE_DELETED,
    WEBHOOK_EVENT_ISSUE_UPDATED,
    BatchWebhookResult,
    JiraWebhookProcessor,
    WebhookResult,
)


def _make_processor(
    integration_repo=None,
    mapping_repo=None,
    activity_repo=None,
    wbs_repo=None,
    sync_log_repo=None,
) -> JiraWebhookProcessor:
    """Create a JiraWebhookProcessor with mock repositories."""
    return JiraWebhookProcessor(
        integration_repo=integration_repo or AsyncMock(),
        mapping_repo=mapping_repo or AsyncMock(),
        activity_repo=activity_repo or AsyncMock(),
        wbs_repo=wbs_repo or AsyncMock(),
        sync_log_repo=sync_log_repo or AsyncMock(),
    )


def _make_payload(
    event: str = WEBHOOK_EVENT_ISSUE_UPDATED,
    issue_key: str = "PROJ-123",
    project_key: str = "PROJ",
    summary: str = "Test Issue",
    status_name: str = "In Progress",
    changelog: dict | None = None,
) -> MagicMock:
    """Create a mock JiraWebhookPayload."""
    payload = MagicMock()
    payload.webhookEvent = event
    payload.changelog = changelog

    issue = {
        "key": issue_key,
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "status": {"name": status_name},
        },
    }
    payload.issue = issue
    return payload


def _make_integration(
    integration_id=None,
    project_key: str = "PROJ",
    sync_enabled: bool = True,
) -> MagicMock:
    """Create a mock JiraIntegration."""
    integration = MagicMock()
    integration.id = integration_id or uuid4()
    integration.project_key = project_key
    integration.sync_enabled = sync_enabled
    return integration


def _make_mapping(
    entity_type: str = "activity",
    activity_id=None,
    wbs_id=None,
    sync_direction: str = "bidirectional",
    jira_issue_key: str = "PROJ-123",
) -> MagicMock:
    """Create a mock JiraMapping."""
    mapping = MagicMock()
    mapping.id = uuid4()
    mapping.entity_type = entity_type
    mapping.activity_id = activity_id or uuid4()
    mapping.wbs_id = wbs_id
    mapping.sync_direction = sync_direction
    mapping.jira_issue_key = jira_issue_key
    return mapping


class TestVerifySignature:
    """Tests for JiraWebhookProcessor.verify_signature()."""

    def test_verify_signature_valid(self):
        """Should return True for valid HMAC-SHA256 signature."""
        # Arrange
        processor = _make_processor()
        secret = "my-webhook-secret"
        payload = b'{"event":"test"}'
        expected_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

        # Act
        result = processor.verify_signature(payload, f"sha256={expected_sig}", secret)

        # Assert
        assert result is True

    def test_verify_signature_invalid(self):
        """Should return False for mismatched signature."""
        # Arrange
        processor = _make_processor()
        payload = b'{"event":"test"}'

        # Act
        result = processor.verify_signature(payload, "sha256=invalidsig", "secret")

        # Assert
        assert result is False

    def test_verify_signature_empty_secret(self):
        """Should return False when secret is empty."""
        # Arrange
        processor = _make_processor()
        payload = b'{"event":"test"}'

        # Act
        result = processor.verify_signature(payload, "sha256=abc", "")

        # Assert
        assert result is False

    def test_verify_signature_empty_signature(self):
        """Should return False when signature is empty."""
        # Arrange
        processor = _make_processor()

        # Act
        result = processor.verify_signature(b"payload", "", "secret")

        # Assert
        assert result is False


class TestProcessWebhook:
    """Tests for JiraWebhookProcessor.process_webhook()."""

    @pytest.mark.asyncio
    async def test_process_webhook_issue_created(self):
        """Should process issue_created event and update mapping."""
        # Arrange
        integration = _make_integration()
        mapping = _make_mapping()
        mapping_repo = AsyncMock()
        mapping_repo.get_by_jira_key = AsyncMock(return_value=mapping)
        mapping_repo.update = AsyncMock()

        integration_repo = AsyncMock()
        integration_repo.get = AsyncMock(return_value=integration)

        sync_log_repo = AsyncMock()
        sync_log_repo.create = AsyncMock()

        processor = _make_processor(
            integration_repo=integration_repo,
            mapping_repo=mapping_repo,
            sync_log_repo=sync_log_repo,
        )

        payload = _make_payload(event=WEBHOOK_EVENT_ISSUE_CREATED)

        # Act
        result = await processor.process_webhook(payload, integration.id)

        # Assert
        assert result.success is True
        assert result.event_type == WEBHOOK_EVENT_ISSUE_CREATED
        assert result.action_taken == "mapping_updated"

    @pytest.mark.asyncio
    async def test_process_webhook_issue_updated(self):
        """Should process issue_updated event."""
        # Arrange
        integration = _make_integration()
        activity = MagicMock()
        activity.name = "Old Name"
        activity.percent_complete = Decimal("0")

        mapping = _make_mapping(entity_type="activity")

        mapping_repo = AsyncMock()
        mapping_repo.get_by_jira_key = AsyncMock(return_value=mapping)
        mapping_repo.update = AsyncMock()

        integration_repo = AsyncMock()
        integration_repo.get = AsyncMock(return_value=integration)

        activity_repo = AsyncMock()
        activity_repo.get = AsyncMock(return_value=activity)
        activity_repo.update = AsyncMock()

        sync_log_repo = AsyncMock()
        sync_log_repo.create = AsyncMock()

        processor = _make_processor(
            integration_repo=integration_repo,
            mapping_repo=mapping_repo,
            activity_repo=activity_repo,
            sync_log_repo=sync_log_repo,
        )

        changelog = {
            "items": [
                {
                    "field": "status",
                    "fromString": "To Do",
                    "toString": "Done",
                }
            ]
        }
        payload = _make_payload(
            event=WEBHOOK_EVENT_ISSUE_UPDATED,
            summary="New Name",
            changelog=changelog,
        )

        # Act
        result = await processor.process_webhook(payload, integration.id)

        # Assert
        assert result.success is True
        assert result.event_type == WEBHOOK_EVENT_ISSUE_UPDATED

    @pytest.mark.asyncio
    async def test_process_webhook_issue_deleted(self):
        """Should soft-delete mapping on issue_deleted event."""
        # Arrange
        integration = _make_integration()
        mapping = _make_mapping()

        mapping_repo = AsyncMock()
        mapping_repo.get_by_jira_key = AsyncMock(return_value=mapping)
        mapping_repo.delete = AsyncMock()

        integration_repo = AsyncMock()
        integration_repo.get = AsyncMock(return_value=integration)

        sync_log_repo = AsyncMock()
        sync_log_repo.create = AsyncMock()

        processor = _make_processor(
            integration_repo=integration_repo,
            mapping_repo=mapping_repo,
            sync_log_repo=sync_log_repo,
        )

        payload = _make_payload(event=WEBHOOK_EVENT_ISSUE_DELETED)

        # Act
        result = await processor.process_webhook(payload, integration.id)

        # Assert
        assert result.success is True
        assert result.event_type == WEBHOOK_EVENT_ISSUE_DELETED
        assert result.action_taken == "mapping_deleted"
        mapping_repo.delete.assert_called_once_with(mapping.id)

    @pytest.mark.asyncio
    async def test_process_webhook_unknown_event(self):
        """Should ignore unsupported webhook event types gracefully."""
        # Arrange
        integration = _make_integration()
        mapping = _make_mapping()

        mapping_repo = AsyncMock()
        mapping_repo.get_by_jira_key = AsyncMock(return_value=mapping)

        integration_repo = AsyncMock()
        integration_repo.get = AsyncMock(return_value=integration)

        sync_log_repo = AsyncMock()
        sync_log_repo.create = AsyncMock()

        processor = _make_processor(
            integration_repo=integration_repo,
            mapping_repo=mapping_repo,
            sync_log_repo=sync_log_repo,
        )

        payload = _make_payload(event="jira:issue_commented")

        # Act
        result = await processor.process_webhook(payload, integration.id)

        # Assert
        assert result.success is True
        assert result.action_taken == "ignored_unsupported_event"

    @pytest.mark.asyncio
    async def test_process_webhook_missing_issue_key(self):
        """Should fail when payload has no issue data."""
        # Arrange
        processor = _make_processor()
        payload = MagicMock()
        payload.webhookEvent = WEBHOOK_EVENT_ISSUE_UPDATED
        payload.issue = None
        payload.changelog = None

        # Act
        result = await processor.process_webhook(payload)

        # Assert
        assert result.success is False
        assert "No issue data" in result.error_message

    @pytest.mark.asyncio
    async def test_process_webhook_no_integration_found(self):
        """Should return success with ignored action when no integration matches."""
        # Arrange
        integration_repo = AsyncMock()
        integration_repo.get = AsyncMock(return_value=None)
        integration_repo.get_active_integrations = AsyncMock(return_value=[])

        processor = _make_processor(integration_repo=integration_repo)
        payload = _make_payload()

        # Act
        result = await processor.process_webhook(payload)

        # Assert
        assert result.success is True
        assert result.action_taken == "ignored_no_integration"

    @pytest.mark.asyncio
    async def test_process_webhook_no_mapping_found(self):
        """Should return success with ignored action when no mapping exists."""
        # Arrange
        integration = _make_integration()

        integration_repo = AsyncMock()
        integration_repo.get = AsyncMock(return_value=integration)

        mapping_repo = AsyncMock()
        mapping_repo.get_by_jira_key = AsyncMock(return_value=None)

        processor = _make_processor(
            integration_repo=integration_repo,
            mapping_repo=mapping_repo,
        )
        payload = _make_payload()

        # Act
        result = await processor.process_webhook(payload, integration.id)

        # Assert
        assert result.success is True
        assert result.action_taken == "ignored_no_mapping"

    @pytest.mark.asyncio
    async def test_handle_issue_updated_status_change(self):
        """Should update activity percent_complete on status change."""
        # Arrange
        integration = _make_integration()
        activity = MagicMock()
        activity.name = "Same Name"
        activity.percent_complete = Decimal("0")

        mapping = _make_mapping(entity_type="activity")

        mapping_repo = AsyncMock()
        mapping_repo.get_by_jira_key = AsyncMock(return_value=mapping)
        mapping_repo.update = AsyncMock()

        integration_repo = AsyncMock()
        integration_repo.get = AsyncMock(return_value=integration)

        activity_repo = AsyncMock()
        activity_repo.get = AsyncMock(return_value=activity)
        activity_repo.update = AsyncMock()

        sync_log_repo = AsyncMock()
        sync_log_repo.create = AsyncMock()

        processor = _make_processor(
            integration_repo=integration_repo,
            mapping_repo=mapping_repo,
            activity_repo=activity_repo,
            sync_log_repo=sync_log_repo,
        )

        changelog = {"items": [{"field": "status", "fromString": "To Do", "toString": "Done"}]}
        payload = _make_payload(
            event=WEBHOOK_EVENT_ISSUE_UPDATED,
            summary="Same Name",
            changelog=changelog,
        )

        # Act
        result = await processor.process_webhook(payload, integration.id)

        # Assert
        assert result.success is True
        # Activity update should have been called with percent_complete = 100
        activity_repo.update.assert_called_once()
        update_data = activity_repo.update.call_args[0][1]
        assert update_data["percent_complete"] == Decimal("100")

    @pytest.mark.asyncio
    async def test_handle_issue_updated_summary_change(self):
        """Should update activity name when summary changes."""
        # Arrange
        integration = _make_integration()
        activity = MagicMock()
        activity.name = "Old Task Name"
        activity.percent_complete = Decimal("50")

        mapping = _make_mapping(entity_type="activity")

        mapping_repo = AsyncMock()
        mapping_repo.get_by_jira_key = AsyncMock(return_value=mapping)
        mapping_repo.update = AsyncMock()

        integration_repo = AsyncMock()
        integration_repo.get = AsyncMock(return_value=integration)

        activity_repo = AsyncMock()
        activity_repo.get = AsyncMock(return_value=activity)
        activity_repo.update = AsyncMock()

        sync_log_repo = AsyncMock()
        sync_log_repo.create = AsyncMock()

        processor = _make_processor(
            integration_repo=integration_repo,
            mapping_repo=mapping_repo,
            activity_repo=activity_repo,
            sync_log_repo=sync_log_repo,
        )

        payload = _make_payload(
            event=WEBHOOK_EVENT_ISSUE_UPDATED,
            summary="New Task Name",
            status_name="In Progress",
        )

        # Act
        result = await processor.process_webhook(payload, integration.id)

        # Assert
        assert result.success is True
        activity_repo.update.assert_called_once()
        update_data = activity_repo.update.call_args[0][1]
        assert update_data["name"] == "New Task Name"


class TestStatusToPercent:
    """Tests for JiraWebhookProcessor._status_to_percent()."""

    def test_status_to_percent_done(self):
        """Should map 'Done' to 100."""
        # Arrange
        processor = _make_processor()

        # Act
        result = processor._status_to_percent("Done")

        # Assert
        assert result == Decimal("100")

    def test_status_to_percent_in_progress(self):
        """Should map 'In Progress' to 50."""
        # Arrange
        processor = _make_processor()

        # Act
        result = processor._status_to_percent("In Progress")

        # Assert
        assert result == Decimal("50")

    def test_status_to_percent_unknown(self):
        """Should return None for unrecognized status."""
        # Arrange
        processor = _make_processor()

        # Act
        result = processor._status_to_percent("Custom Workflow Step")

        # Assert
        assert result is None

    def test_status_to_percent_to_do(self):
        """Should map 'To Do' to 0."""
        # Arrange
        processor = _make_processor()

        # Act
        result = processor._status_to_percent("To Do")

        # Assert
        assert result == Decimal("0")

    def test_status_to_percent_in_review(self):
        """Should map 'In Review' to 75."""
        # Arrange
        processor = _make_processor()

        # Act
        result = processor._status_to_percent("In Review")

        # Assert
        assert result == Decimal("75")

    def test_status_to_percent_case_insensitive(self):
        """Should match case-insensitively."""
        # Arrange
        processor = _make_processor()

        # Act
        result = processor._status_to_percent("done")

        # Assert
        assert result == Decimal("100")

    def test_status_to_percent_pattern_match_complete(self):
        """Should match patterns like 'Completed' via common patterns."""
        # Arrange
        processor = _make_processor()

        # Act
        result = processor._status_to_percent("Completed")

        # Assert
        assert result == Decimal("100")


class TestExtractDescriptionText:
    """Tests for JiraWebhookProcessor._extract_description_text()."""

    def test_extract_description_text_string(self):
        """Should return the string directly when description is a string."""
        # Arrange
        processor = _make_processor()

        # Act
        result = processor._extract_description_text("Simple text description")

        # Assert
        assert result == "Simple text description"

    def test_extract_description_text_adf_format(self):
        """Should extract text from Atlassian Document Format."""
        # Arrange
        processor = _make_processor()
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Hello"},
                        {"type": "text", "text": " World"},
                    ],
                }
            ],
        }

        # Act
        result = processor._extract_description_text(adf)

        # Assert
        assert result == "Hello\n World"

    def test_extract_description_text_none(self):
        """Should return None for None description."""
        # Arrange
        processor = _make_processor()

        # Act
        result = processor._extract_description_text(None)

        # Assert
        assert result is None

    def test_extract_description_text_empty_adf(self):
        """Should return None for ADF with no text content."""
        # Arrange
        processor = _make_processor()
        adf = {"type": "doc", "version": 1, "content": []}

        # Act
        result = processor._extract_description_text(adf)

        # Assert
        assert result is None


class TestWebhookResultDataclass:
    """Tests for the WebhookResult and BatchWebhookResult dataclasses."""

    def test_webhook_result_dataclass(self):
        """Should construct WebhookResult with required and default fields."""
        # Act
        result = WebhookResult(
            success=True,
            event_type=WEBHOOK_EVENT_ISSUE_CREATED,
            issue_key="PROJ-1",
        )

        # Assert
        assert result.success is True
        assert result.event_type == WEBHOOK_EVENT_ISSUE_CREATED
        assert result.issue_key == "PROJ-1"
        assert result.entity_type is None
        assert result.entity_id is None
        assert result.action_taken is None
        assert result.error_message is None
        assert result.duration_ms == 0

    def test_batch_webhook_result(self):
        """Should construct BatchWebhookResult with defaults."""
        # Act
        batch = BatchWebhookResult(
            success=True,
            webhooks_processed=5,
            webhooks_failed=1,
        )

        # Assert
        assert batch.success is True
        assert batch.webhooks_processed == 5
        assert batch.webhooks_failed == 1
        assert batch.results == []
        assert batch.errors == []
        assert batch.duration_ms == 0
