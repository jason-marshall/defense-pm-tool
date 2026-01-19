"""Unit tests for Jira Webhook processing.

Tests the JiraWebhookProcessor with mocked repositories.
"""

import hashlib
import hmac
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.schemas.jira_integration import JiraWebhookPayload
from src.services.jira_webhook_processor import (
    JIRA_STATUS_TO_PERCENT,
    BatchWebhookResult,
    IntegrationNotFoundError,
    JiraWebhookProcessor,
    WebhookConfigError,
    WebhookProcessingError,
    WebhookResult,
    WebhookSignatureError,
)


class TestWebhookResult:
    """Tests for WebhookResult dataclass."""

    def test_default_values(self):
        """WebhookResult should have sensible defaults."""
        result = WebhookResult(success=True, event_type="jira:issue_updated")
        assert result.success is True
        assert result.event_type == "jira:issue_updated"
        assert result.issue_key is None
        assert result.entity_type is None
        assert result.entity_id is None
        assert result.action_taken is None
        assert result.error_message is None
        assert result.duration_ms == 0

    def test_with_values(self):
        """WebhookResult should store all values."""
        entity_id = uuid4()
        result = WebhookResult(
            success=True,
            event_type="jira:issue_updated",
            issue_key="PROJ-123",
            entity_type="activity",
            entity_id=entity_id,
            action_taken="updated_progress=50%",
            duration_ms=150,
        )
        assert result.issue_key == "PROJ-123"
        assert result.entity_type == "activity"
        assert result.entity_id == entity_id
        assert result.action_taken == "updated_progress=50%"
        assert result.duration_ms == 150

    def test_failure_result(self):
        """WebhookResult should store failure details."""
        result = WebhookResult(
            success=False,
            event_type="jira:issue_updated",
            error_message="Mapping not found",
        )
        assert result.success is False
        assert result.error_message == "Mapping not found"


class TestBatchWebhookResult:
    """Tests for BatchWebhookResult dataclass."""

    def test_default_values(self):
        """BatchWebhookResult should have sensible defaults."""
        result = BatchWebhookResult(success=True, webhooks_processed=0, webhooks_failed=0)
        assert result.success is True
        assert result.webhooks_processed == 0
        assert result.webhooks_failed == 0
        assert result.results == []
        assert result.errors == []
        assert result.duration_ms == 0

    def test_with_values(self):
        """BatchWebhookResult should store all values."""
        webhook_result = WebhookResult(success=True, event_type="jira:issue_updated")
        result = BatchWebhookResult(
            success=True,
            webhooks_processed=5,
            webhooks_failed=1,
            results=[webhook_result],
            errors=["Error 1"],
            duration_ms=500,
        )
        assert result.webhooks_processed == 5
        assert result.webhooks_failed == 1
        assert len(result.results) == 1
        assert len(result.errors) == 1


class TestWebhookExceptions:
    """Tests for custom webhook exceptions."""

    def test_webhook_processing_error(self):
        """WebhookProcessingError should store message and details."""
        error = WebhookProcessingError("Processing failed", {"reason": "timeout"})
        assert str(error) == "Processing failed"
        assert error.message == "Processing failed"
        assert error.details == {"reason": "timeout"}

    def test_webhook_processing_error_default_details(self):
        """WebhookProcessingError should default to empty details."""
        error = WebhookProcessingError("Error")
        assert error.details == {}

    def test_webhook_signature_error(self):
        """WebhookSignatureError should inherit from WebhookProcessingError."""
        error = WebhookSignatureError("Invalid signature")
        assert isinstance(error, WebhookProcessingError)

    def test_webhook_config_error(self):
        """WebhookConfigError should inherit from WebhookProcessingError."""
        error = WebhookConfigError("Missing config")
        assert isinstance(error, WebhookProcessingError)

    def test_integration_not_found_error(self):
        """IntegrationNotFoundError should inherit from WebhookProcessingError."""
        error = IntegrationNotFoundError("Not found")
        assert isinstance(error, WebhookProcessingError)


class TestJiraStatusMapping:
    """Tests for Jira status to percent mapping."""

    def test_standard_statuses_mapped(self):
        """Standard Jira statuses should be mapped."""
        assert JIRA_STATUS_TO_PERCENT["To Do"] == Decimal("0")
        assert JIRA_STATUS_TO_PERCENT["In Progress"] == Decimal("50")
        assert JIRA_STATUS_TO_PERCENT["Done"] == Decimal("100")

    def test_all_statuses_have_valid_percentages(self):
        """All mapped statuses should have valid percentages."""
        for _status, percent in JIRA_STATUS_TO_PERCENT.items():
            assert Decimal("0") <= percent <= Decimal("100")


class TestJiraWebhookProcessorInit:
    """Tests for JiraWebhookProcessor initialization."""

    def test_init_stores_dependencies(self):
        """Processor should store all dependencies."""
        mock_integration_repo = MagicMock()
        mock_mapping_repo = MagicMock()
        mock_activity_repo = MagicMock()
        mock_wbs_repo = MagicMock()
        mock_sync_log_repo = MagicMock()

        processor = JiraWebhookProcessor(
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            activity_repo=mock_activity_repo,
            wbs_repo=mock_wbs_repo,
            sync_log_repo=mock_sync_log_repo,
        )

        assert processor.integration_repo is mock_integration_repo
        assert processor.mapping_repo is mock_mapping_repo
        assert processor.activity_repo is mock_activity_repo
        assert processor.wbs_repo is mock_wbs_repo
        assert processor.sync_log_repo is mock_sync_log_repo


class TestJiraWebhookProcessorVerifySignature:
    """Tests for verify_signature method."""

    @pytest.fixture
    def processor(self):
        """Create a JiraWebhookProcessor with mocked dependencies."""
        return JiraWebhookProcessor(
            integration_repo=AsyncMock(),
            mapping_repo=AsyncMock(),
            activity_repo=AsyncMock(),
            wbs_repo=AsyncMock(),
            sync_log_repo=AsyncMock(),
        )

    def test_valid_signature(self, processor):
        """Should return True for valid signature."""
        payload = b'{"test": "data"}'
        secret = "my-webhook-secret"
        expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        signature = f"sha256={expected}"

        result = processor.verify_signature(payload, signature, secret)
        assert result is True

    def test_invalid_signature(self, processor):
        """Should return False for invalid signature."""
        payload = b'{"test": "data"}'
        secret = "my-webhook-secret"
        signature = "sha256=invalid_signature"

        result = processor.verify_signature(payload, signature, secret)
        assert result is False

    def test_missing_signature(self, processor):
        """Should return False for missing signature."""
        payload = b'{"test": "data"}'
        secret = "my-webhook-secret"

        result = processor.verify_signature(payload, "", secret)
        assert result is False

    def test_missing_secret(self, processor):
        """Should return False for missing secret."""
        payload = b'{"test": "data"}'
        signature = "sha256=something"

        result = processor.verify_signature(payload, signature, "")
        assert result is False

    def test_signature_without_prefix(self, processor):
        """Should handle signature without sha256= prefix."""
        payload = b'{"test": "data"}'
        secret = "my-webhook-secret"
        expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

        result = processor.verify_signature(payload, expected, secret)
        assert result is True


class TestJiraWebhookProcessorStatusToPercent:
    """Tests for _status_to_percent method."""

    @pytest.fixture
    def processor(self):
        """Create a JiraWebhookProcessor with mocked dependencies."""
        return JiraWebhookProcessor(
            integration_repo=AsyncMock(),
            mapping_repo=AsyncMock(),
            activity_repo=AsyncMock(),
            wbs_repo=AsyncMock(),
            sync_log_repo=AsyncMock(),
        )

    def test_known_status_to_do(self, processor):
        """Should map 'To Do' to 0%."""
        assert processor._status_to_percent("To Do") == Decimal("0")

    def test_known_status_in_progress(self, processor):
        """Should map 'In Progress' to 50%."""
        assert processor._status_to_percent("In Progress") == Decimal("50")

    def test_known_status_done(self, processor):
        """Should map 'Done' to 100%."""
        assert processor._status_to_percent("Done") == Decimal("100")

    def test_case_insensitive_matching(self, processor):
        """Should match statuses case-insensitively."""
        assert processor._status_to_percent("TO DO") == Decimal("0")
        assert processor._status_to_percent("in progress") == Decimal("50")
        assert processor._status_to_percent("DONE") == Decimal("100")

    def test_pattern_matching_done(self, processor):
        """Should recognize 'done' pattern in status."""
        assert processor._status_to_percent("Marked as Done") == Decimal("100")
        assert processor._status_to_percent("Complete") == Decimal("100")

    def test_pattern_matching_in_progress(self, processor):
        """Should recognize 'progress' pattern in status."""
        assert processor._status_to_percent("Work In Progress") == Decimal("50")
        assert processor._status_to_percent("Active Development") == Decimal("50")

    def test_pattern_matching_todo(self, processor):
        """Should recognize 'todo' pattern in status."""
        assert processor._status_to_percent("New Task") == Decimal("0")
        assert processor._status_to_percent("Open Issue") == Decimal("0")

    def test_unknown_status_returns_none(self, processor):
        """Should return None for completely unknown status."""
        result = processor._status_to_percent("Custom Status XYZ")
        assert result is None


class TestJiraWebhookProcessorExtractDescription:
    """Tests for _extract_description_text method."""

    @pytest.fixture
    def processor(self):
        """Create a JiraWebhookProcessor with mocked dependencies."""
        return JiraWebhookProcessor(
            integration_repo=AsyncMock(),
            mapping_repo=AsyncMock(),
            activity_repo=AsyncMock(),
            wbs_repo=AsyncMock(),
            sync_log_repo=AsyncMock(),
        )

    def test_string_description(self, processor):
        """Should return string description as-is."""
        result = processor._extract_description_text("Simple description")
        assert result == "Simple description"

    def test_adf_description(self, processor):
        """Should extract text from ADF format."""
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Hello "}],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "World"}],
                },
            ],
        }
        result = processor._extract_description_text(adf)
        assert result == "Hello \nWorld"

    def test_empty_adf(self, processor):
        """Should return None for empty ADF."""
        adf = {"type": "doc", "content": []}
        result = processor._extract_description_text(adf)
        assert result is None

    def test_non_text_content(self, processor):
        """Should handle ADF with non-text content."""
        adf = {
            "type": "doc",
            "content": [
                {"type": "rule"},  # Horizontal rule
            ],
        }
        result = processor._extract_description_text(adf)
        assert result is None

    def test_none_description(self, processor):
        """Should return None for None description."""
        result = processor._extract_description_text(None)
        assert result is None


class TestJiraWebhookProcessorProcessWebhook:
    """Tests for process_webhook method."""

    @pytest.fixture
    def processor(self):
        """Create a JiraWebhookProcessor with mocked dependencies."""
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_activity_repo = AsyncMock()
        mock_wbs_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()

        return JiraWebhookProcessor(
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            activity_repo=mock_activity_repo,
            wbs_repo=mock_wbs_repo,
            sync_log_repo=mock_sync_log_repo,
        )

    @pytest.mark.asyncio
    async def test_no_issue_data(self, processor):
        """Should return failure for payload without issue data."""
        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=None,
        )

        result = await processor.process_webhook(payload)

        assert result.success is False
        assert "No issue data" in result.error_message

    @pytest.mark.asyncio
    async def test_missing_issue_key(self, processor):
        """Should return failure for missing issue key."""
        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue={"fields": {"project": {"key": "PROJ"}}},
        )

        result = await processor.process_webhook(payload)

        assert result.success is False
        assert "Missing issue key" in result.error_message

    @pytest.mark.asyncio
    async def test_no_matching_integration(self, processor):
        """Should ignore webhook when no integration matches."""
        processor.integration_repo.get_active_integrations.return_value = []

        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue={
                "key": "PROJ-123",
                "fields": {"project": {"key": "PROJ"}},
            },
        )

        result = await processor.process_webhook(payload)

        assert result.success is True
        assert result.action_taken == "ignored_no_integration"

    @pytest.mark.asyncio
    async def test_sync_disabled(self, processor):
        """Should ignore webhook when sync is disabled."""
        mock_integration = MagicMock()
        mock_integration.sync_enabled = False
        mock_integration.project_key = "PROJ"
        processor.integration_repo.get_active_integrations.return_value = [mock_integration]

        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue={
                "key": "PROJ-123",
                "fields": {"project": {"key": "PROJ"}},
            },
        )

        result = await processor.process_webhook(payload)

        assert result.success is True
        assert result.action_taken == "ignored_sync_disabled"

    @pytest.mark.asyncio
    async def test_no_mapping_found(self, processor):
        """Should ignore webhook when no mapping exists."""
        mock_integration = MagicMock()
        mock_integration.id = uuid4()
        mock_integration.sync_enabled = True
        mock_integration.project_key = "PROJ"
        processor.integration_repo.get_active_integrations.return_value = [mock_integration]
        processor.mapping_repo.get_by_jira_key.return_value = None

        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue={
                "key": "PROJ-123",
                "fields": {"project": {"key": "PROJ"}},
            },
        )

        result = await processor.process_webhook(payload)

        assert result.success is True
        assert result.action_taken == "ignored_no_mapping"

    @pytest.mark.asyncio
    async def test_to_jira_only_sync_direction(self, processor):
        """Should ignore webhook for to_jira only mappings."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.project_key = "PROJ"
        processor.integration_repo.get_active_integrations.return_value = [mock_integration]

        mock_mapping = MagicMock()
        mock_mapping.sync_direction = "to_jira"
        mock_mapping.entity_type = "activity"
        processor.mapping_repo.get_by_jira_key.return_value = mock_mapping

        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue={
                "key": "PROJ-123",
                "fields": {"project": {"key": "PROJ"}},
            },
        )

        result = await processor.process_webhook(payload)

        assert result.success is True
        assert result.action_taken == "ignored_sync_direction"

    @pytest.mark.asyncio
    async def test_unsupported_event(self, processor):
        """Should ignore unsupported webhook events."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.project_key = "PROJ"
        processor.integration_repo.get_active_integrations.return_value = [mock_integration]

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        mock_mapping.sync_direction = "bidirectional"
        mock_mapping.entity_type = "activity"
        processor.mapping_repo.get_by_jira_key.return_value = mock_mapping

        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_commented",  # Unsupported event
            issue={
                "key": "PROJ-123",
                "fields": {"project": {"key": "PROJ"}},
            },
        )

        result = await processor.process_webhook(payload)

        assert result.success is True
        assert result.action_taken == "ignored_unsupported_event"


class TestJiraWebhookProcessorHandleIssueUpdated:
    """Tests for _handle_issue_updated method."""

    @pytest.fixture
    def processor(self):
        """Create a JiraWebhookProcessor with mocked dependencies."""
        return JiraWebhookProcessor(
            integration_repo=AsyncMock(),
            mapping_repo=AsyncMock(),
            activity_repo=AsyncMock(),
            wbs_repo=AsyncMock(),
            sync_log_repo=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_update_activity_status(self, processor):
        """Should update activity percent complete from status change."""
        integration = MagicMock()
        activity_id = uuid4()

        mapping = MagicMock()
        mapping.entity_type = "activity"
        mapping.activity_id = activity_id
        mapping.wbs_id = None

        activity = MagicMock()
        activity.name = "Original Name"
        activity.percent_complete = Decimal("0")
        processor.activity_repo.get.return_value = activity

        issue = {
            "key": "PROJ-123",
            "fields": {
                "summary": "Original Name",
                "status": {"name": "Done"},
            },
        }

        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=issue,
            changelog={"items": [{"field": "status", "fromString": "To Do", "toString": "Done"}]},
        )

        result = await processor._handle_issue_updated(integration, mapping, issue, payload)

        assert result.success is True
        assert "progress=100%" in result.action_taken
        processor.activity_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_activity_name(self, processor):
        """Should update activity name from summary change."""
        integration = MagicMock()
        activity_id = uuid4()

        mapping = MagicMock()
        mapping.entity_type = "activity"
        mapping.activity_id = activity_id
        mapping.wbs_id = None

        activity = MagicMock()
        activity.name = "Original Name"
        activity.percent_complete = Decimal("50")
        processor.activity_repo.get.return_value = activity

        issue = {
            "key": "PROJ-123",
            "fields": {
                "summary": "New Name",
                "status": {"name": "In Progress"},
            },
        }

        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=issue,
            changelog=None,
        )

        result = await processor._handle_issue_updated(integration, mapping, issue, payload)

        assert result.success is True
        assert "name" in result.action_taken
        processor.activity_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_activity_not_found(self, processor):
        """Should return failure when activity not found."""
        integration = MagicMock()
        activity_id = uuid4()

        mapping = MagicMock()
        mapping.entity_type = "activity"
        mapping.activity_id = activity_id
        mapping.wbs_id = None

        processor.activity_repo.get.return_value = None

        issue = {
            "key": "PROJ-123",
            "fields": {"summary": "Test", "status": {"name": "Done"}},
        }

        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=issue,
        )

        result = await processor._handle_issue_updated(integration, mapping, issue, payload)

        assert result.success is False
        assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_update_wbs_name(self, processor):
        """Should update WBS name from summary change."""
        integration = MagicMock()
        wbs_id = uuid4()

        mapping = MagicMock()
        mapping.entity_type = "wbs"
        mapping.wbs_id = wbs_id
        mapping.activity_id = None

        wbs = MagicMock()
        wbs.name = "Original WBS Name"
        wbs.description = None
        processor.wbs_repo.get.return_value = wbs

        issue = {
            "key": "PROJ-123",
            "fields": {
                "summary": "New WBS Name",
                "description": None,
            },
        }

        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=issue,
        )

        result = await processor._handle_issue_updated(integration, mapping, issue, payload)

        assert result.success is True
        assert "name" in result.action_taken
        processor.wbs_repo.update.assert_called_once()


class TestJiraWebhookProcessorHandleIssueDeleted:
    """Tests for _handle_issue_deleted method."""

    @pytest.fixture
    def processor(self):
        """Create a JiraWebhookProcessor with mocked dependencies."""
        return JiraWebhookProcessor(
            integration_repo=AsyncMock(),
            mapping_repo=AsyncMock(),
            activity_repo=AsyncMock(),
            wbs_repo=AsyncMock(),
            sync_log_repo=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_soft_deletes_mapping(self, processor):
        """Should soft-delete the mapping when issue is deleted."""
        integration = MagicMock()
        integration.id = uuid4()

        mapping = MagicMock()
        mapping.id = uuid4()
        mapping.entity_type = "activity"
        mapping.activity_id = uuid4()
        mapping.wbs_id = None

        issue = {"key": "PROJ-123"}

        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_deleted",
            issue=issue,
        )

        result = await processor._handle_issue_deleted(integration, mapping, issue, payload)

        assert result.success is True
        assert result.action_taken == "mapping_deleted"
        processor.mapping_repo.delete.assert_called_once_with(mapping.id)


class TestJiraWebhookProcessorHandleIssueCreated:
    """Tests for _handle_issue_created method."""

    @pytest.fixture
    def processor(self):
        """Create a JiraWebhookProcessor with mocked dependencies."""
        return JiraWebhookProcessor(
            integration_repo=AsyncMock(),
            mapping_repo=AsyncMock(),
            activity_repo=AsyncMock(),
            wbs_repo=AsyncMock(),
            sync_log_repo=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_updates_mapping_timestamp(self, processor):
        """Should update mapping timestamp for created event."""
        integration = MagicMock()
        integration.id = uuid4()

        mapping = MagicMock()
        mapping.entity_type = "activity"
        mapping.activity_id = uuid4()
        mapping.wbs_id = None

        issue = {"key": "PROJ-123"}

        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_created",
            issue=issue,
        )

        result = await processor._handle_issue_created(integration, mapping, issue, payload)

        assert result.success is True
        assert result.action_taken == "mapping_updated"
        processor.mapping_repo.update.assert_called_once()


class TestJiraWebhookProcessorFindIntegration:
    """Tests for _find_integration method."""

    @pytest.fixture
    def processor(self):
        """Create a JiraWebhookProcessor with mocked dependencies."""
        return JiraWebhookProcessor(
            integration_repo=AsyncMock(),
            mapping_repo=AsyncMock(),
            activity_repo=AsyncMock(),
            wbs_repo=AsyncMock(),
            sync_log_repo=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_find_by_integration_id(self, processor):
        """Should find integration by direct ID."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        processor.integration_repo.get.return_value = mock_integration

        result = await processor._find_integration(integration_id=integration_id)

        assert result is mock_integration
        processor.integration_repo.get.assert_called_once_with(integration_id)

    @pytest.mark.asyncio
    async def test_find_by_project_key(self, processor):
        """Should find integration by project key."""
        mock_integration = MagicMock()
        mock_integration.project_key = "PROJ"
        processor.integration_repo.get_active_integrations.return_value = [mock_integration]

        result = await processor._find_integration(project_key="PROJ")

        assert result is mock_integration

    @pytest.mark.asyncio
    async def test_not_found_by_project_key(self, processor):
        """Should return None when project key doesn't match."""
        mock_integration = MagicMock()
        mock_integration.project_key = "OTHER"
        processor.integration_repo.get_active_integrations.return_value = [mock_integration]

        result = await processor._find_integration(project_key="PROJ")

        assert result is None

    @pytest.mark.asyncio
    async def test_no_parameters(self, processor):
        """Should return None when no parameters provided."""
        result = await processor._find_integration()

        assert result is None


class TestJiraWebhookProcessorLogSync:
    """Tests for _log_sync method."""

    @pytest.fixture
    def processor(self):
        """Create a JiraWebhookProcessor with mocked dependencies."""
        return JiraWebhookProcessor(
            integration_repo=AsyncMock(),
            mapping_repo=AsyncMock(),
            activity_repo=AsyncMock(),
            wbs_repo=AsyncMock(),
            sync_log_repo=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_creates_sync_log_entry(self, processor):
        """Should create sync log with all parameters."""
        integration_id = uuid4()
        mapping_id = uuid4()

        await processor._log_sync(
            integration_id=integration_id,
            mapping_id=mapping_id,
            sync_type="webhook",
            status="success",
            items_synced=1,
            error_message=None,
            duration_ms=150,
        )

        processor.sync_log_repo.create.assert_called_once()
        call_args = processor.sync_log_repo.create.call_args[0][0]
        assert call_args["integration_id"] == integration_id
        assert call_args["mapping_id"] == mapping_id
        assert call_args["sync_type"] == "webhook"
        assert call_args["status"] == "success"
        assert call_args["items_synced"] == 1
        assert call_args["duration_ms"] == 150

    @pytest.mark.asyncio
    async def test_creates_sync_log_with_error(self, processor):
        """Should include error message in sync log."""
        integration_id = uuid4()

        await processor._log_sync(
            integration_id=integration_id,
            mapping_id=None,
            sync_type="webhook",
            status="failed",
            items_synced=0,
            error_message="Processing failed",
            duration_ms=50,
        )

        call_args = processor.sync_log_repo.create.call_args[0][0]
        assert call_args["status"] == "failed"
        assert call_args["error_message"] == "Processing failed"
