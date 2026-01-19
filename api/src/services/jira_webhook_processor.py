"""Jira Webhook Processing Service.

Handles incoming webhooks from Jira for real-time updates:
- Issue created → Create/link mapping
- Issue updated → Update activity/WBS
- Issue deleted → Mark mapping as inactive

Usage:
    processor = JiraWebhookProcessor(
        integration_repo=integration_repo,
        mapping_repo=mapping_repo,
        activity_repo=activity_repo,
        wbs_repo=wbs_repo,
        sync_log_repo=sync_log_repo,
    )
    result = await processor.process_webhook(payload)
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import structlog

from src.models.jira_mapping import EntityType, SyncDirection
from src.models.jira_sync_log import SyncStatus, SyncType

if TYPE_CHECKING:
    from uuid import UUID

    from src.models.jira_integration import JiraIntegration
    from src.models.jira_mapping import JiraMapping
    from src.repositories.activity import ActivityRepository
    from src.repositories.jira_integration import JiraIntegrationRepository
    from src.repositories.jira_mapping import JiraMappingRepository
    from src.repositories.jira_sync_log import JiraSyncLogRepository
    from src.repositories.wbs import WBSElementRepository
    from src.schemas.jira_integration import JiraWebhookPayload


logger = structlog.get_logger(__name__)


class WebhookProcessingError(Exception):
    """Base exception for webhook processing errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class WebhookSignatureError(WebhookProcessingError):
    """Webhook signature verification failed."""

    pass


class WebhookConfigError(WebhookProcessingError):
    """Webhook configuration error."""

    pass


class IntegrationNotFoundError(WebhookProcessingError):
    """No matching integration found for webhook."""

    pass


# Jira webhook event types
WEBHOOK_EVENT_ISSUE_CREATED = "jira:issue_created"
WEBHOOK_EVENT_ISSUE_UPDATED = "jira:issue_updated"
WEBHOOK_EVENT_ISSUE_DELETED = "jira:issue_deleted"

# Status to percent complete mapping (reverse of what we send to Jira)
JIRA_STATUS_TO_PERCENT: dict[str, Decimal] = {
    "To Do": Decimal("0"),
    "Open": Decimal("0"),
    "Backlog": Decimal("0"),
    "In Progress": Decimal("50"),
    "In Review": Decimal("75"),
    "Done": Decimal("100"),
    "Closed": Decimal("100"),
    "Resolved": Decimal("100"),
}


@dataclass
class WebhookResult:
    """Result of processing a webhook."""

    success: bool
    event_type: str
    issue_key: str | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    action_taken: str | None = None
    error_message: str | None = None
    duration_ms: int = 0


@dataclass
class BatchWebhookResult:
    """Result of batch webhook processing."""

    success: bool
    webhooks_processed: int
    webhooks_failed: int
    results: list[WebhookResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


class JiraWebhookProcessor:
    """
    Service for processing Jira webhooks.

    Handles real-time updates from Jira:
    - Issue updates propagate to linked activities/WBS
    - Status changes update percent complete
    - Deletions mark mappings as inactive

    Attributes:
        integration_repo: Repository for Jira integrations
        mapping_repo: Repository for entity mappings
        activity_repo: Repository for activities
        wbs_repo: Repository for WBS elements
        sync_log_repo: Repository for sync audit logs
    """

    def __init__(
        self,
        integration_repo: JiraIntegrationRepository,
        mapping_repo: JiraMappingRepository,
        activity_repo: ActivityRepository,
        wbs_repo: WBSElementRepository,
        sync_log_repo: JiraSyncLogRepository,
    ) -> None:
        """Initialize webhook processor.

        Args:
            integration_repo: Repository for Jira integrations
            mapping_repo: Repository for entity mappings
            activity_repo: Repository for activities
            wbs_repo: Repository for WBS elements
            sync_log_repo: Repository for sync audit logs
        """
        self.integration_repo = integration_repo
        self.mapping_repo = mapping_repo
        self.activity_repo = activity_repo
        self.wbs_repo = wbs_repo
        self.sync_log_repo = sync_log_repo

    def verify_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        """Verify webhook signature for security.

        Jira Cloud uses HMAC-SHA256 signatures.

        Args:
            payload: Raw webhook payload bytes
            signature: Signature from X-Hub-Signature header
            secret: Webhook secret configured in Jira

        Returns:
            True if signature is valid
        """
        if not signature or not secret:
            return False

        # Jira uses sha256=<signature> format
        if signature.startswith("sha256="):
            signature = signature[7:]

        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    async def process_webhook(
        self,
        payload: JiraWebhookPayload,
        integration_id: UUID | None = None,
    ) -> WebhookResult:
        """Process a single webhook event.

        Args:
            payload: Parsed webhook payload
            integration_id: Optional integration ID (if known)

        Returns:
            WebhookResult with processing details
        """
        start_time = time.time()
        event_type = payload.webhookEvent

        try:
            # Validate and extract webhook context
            validation = await self._validate_webhook(
                payload, integration_id, event_type, start_time
            )
            if isinstance(validation, WebhookResult):
                return validation

            # Unpack validated context
            issue, issue_key, integration, mapping = validation

            # Route to appropriate handler
            result = await self._route_webhook_event(
                event_type, integration, mapping, issue, payload, issue_key
            )

            result.duration_ms = int((time.time() - start_time) * 1000)

            # Log the sync operation
            await self._log_sync(
                integration_id=integration.id,
                mapping_id=mapping.id,
                sync_type=SyncType.WEBHOOK.value,
                status=SyncStatus.SUCCESS.value if result.success else SyncStatus.FAILED.value,
                items_synced=1 if result.success else 0,
                error_message=result.error_message,
                duration_ms=result.duration_ms,
            )

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "webhook_processing_error",
                event=event_type,
                error=str(e),
            )
            return WebhookResult(
                success=False,
                event_type=event_type,
                error_message=str(e),
                duration_ms=duration_ms,
            )

    async def _validate_webhook(  # noqa: PLR0911
        self,
        payload: JiraWebhookPayload,
        integration_id: UUID | None,
        event_type: str,
        start_time: float,
    ) -> WebhookResult | tuple[dict[str, Any], str, JiraIntegration, JiraMapping]:
        """Validate webhook payload and find matching context.

        Returns:
            WebhookResult if validation fails (early exit reason), or
            tuple of (issue, issue_key, integration, mapping) if valid.
        """
        # Extract issue information
        issue = payload.issue
        if not issue:
            return WebhookResult(
                success=False,
                event_type=event_type,
                error_message="No issue data in webhook payload",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        issue_key = issue.get("key")
        project_key = issue.get("fields", {}).get("project", {}).get("key")

        if not issue_key or not project_key:
            return WebhookResult(
                success=False,
                event_type=event_type,
                error_message="Missing issue key or project key",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Find matching integration
        integration = await self._find_integration(
            integration_id=integration_id,
            project_key=project_key,
        )

        if not integration:
            logger.debug(
                "webhook_no_matching_integration",
                project_key=project_key,
                issue_key=issue_key,
            )
            return WebhookResult(
                success=True,
                event_type=event_type,
                issue_key=issue_key,
                action_taken="ignored_no_integration",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Check if sync is enabled
        if not integration.sync_enabled:
            return WebhookResult(
                success=True,
                event_type=event_type,
                issue_key=issue_key,
                action_taken="ignored_sync_disabled",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Find mapping for this issue
        mapping = await self.mapping_repo.get_by_jira_key(
            integration_id=integration.id,
            jira_issue_key=issue_key,
        )

        if not mapping:
            logger.debug(
                "webhook_no_mapping",
                issue_key=issue_key,
                webhook_event=event_type,
            )
            return WebhookResult(
                success=True,
                event_type=event_type,
                issue_key=issue_key,
                action_taken="ignored_no_mapping",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Check sync direction allows from_jira updates
        if mapping.sync_direction == SyncDirection.TO_JIRA.value:
            return WebhookResult(
                success=True,
                event_type=event_type,
                issue_key=issue_key,
                entity_type=mapping.entity_type,
                action_taken="ignored_sync_direction",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # All validations passed - return validated context
        return (issue, issue_key, integration, mapping)

    async def _route_webhook_event(
        self,
        event_type: str,
        integration: JiraIntegration,
        mapping: JiraMapping,
        issue: dict[str, Any],
        payload: JiraWebhookPayload,
        issue_key: str,
    ) -> WebhookResult:
        """Route webhook event to appropriate handler."""
        if event_type == WEBHOOK_EVENT_ISSUE_CREATED:
            return await self._handle_issue_created(integration, mapping, issue, payload)
        elif event_type == WEBHOOK_EVENT_ISSUE_UPDATED:
            return await self._handle_issue_updated(integration, mapping, issue, payload)
        elif event_type == WEBHOOK_EVENT_ISSUE_DELETED:
            return await self._handle_issue_deleted(integration, mapping, issue, payload)
        else:
            return WebhookResult(
                success=True,
                event_type=event_type,
                issue_key=issue_key,
                action_taken="ignored_unsupported_event",
            )

    async def _find_integration(
        self,
        integration_id: UUID | None = None,
        project_key: str | None = None,
    ) -> JiraIntegration | None:
        """Find matching integration for webhook.

        Args:
            integration_id: Direct integration ID (if known)
            project_key: Jira project key to search by

        Returns:
            JiraIntegration or None
        """
        if integration_id:
            return await self.integration_repo.get(integration_id)

        if project_key:
            # Search active integrations for matching project key
            integrations = await self.integration_repo.get_active_integrations()
            for integration in integrations:
                if integration.project_key == project_key:
                    return integration

        return None

    async def _handle_issue_created(
        self,
        integration: JiraIntegration,
        mapping: JiraMapping,
        issue: dict[str, Any],
        payload: JiraWebhookPayload,
    ) -> WebhookResult:
        """Handle jira:issue_created event.

        For created events, we typically just update the mapping's
        last_jira_updated timestamp since the issue was created externally.
        """
        issue_key = issue.get("key", "")

        # Update mapping timestamp
        await self.mapping_repo.update(
            mapping,
            {"last_jira_updated": datetime.now(UTC)},
        )

        logger.info(
            "webhook_issue_created_processed",
            issue_key=issue_key,
            entity_type=mapping.entity_type,
            integration_id=str(integration.id),
            webhook_event=payload.webhookEvent,
        )

        return WebhookResult(
            success=True,
            event_type=WEBHOOK_EVENT_ISSUE_CREATED,
            issue_key=issue_key,
            entity_type=mapping.entity_type,
            entity_id=mapping.activity_id or mapping.wbs_id,
            action_taken="mapping_updated",
        )

    async def _handle_issue_updated(
        self,
        integration: JiraIntegration,
        mapping: JiraMapping,
        issue: dict[str, Any],
        payload: JiraWebhookPayload,
    ) -> WebhookResult:
        """Handle jira:issue_updated event.

        Updates the linked entity based on issue changes:
        - Status changes → Update percent complete (for activities)
        - Summary changes → Update name
        - Description changes → Update description (for WBS)
        """
        issue_key = issue.get("key", "")
        fields = issue.get("fields", {})
        changelog = payload.changelog

        logger.debug(
            "webhook_issue_update_processing",
            issue_key=issue_key,
            integration_id=str(integration.id),
        )

        # Update mapping timestamp
        await self.mapping_repo.update(
            mapping,
            {"last_jira_updated": datetime.now(UTC)},
        )

        # Determine what changed
        status_changed = False
        new_status = None

        if changelog and changelog.get("items"):
            for item in changelog["items"]:
                if item.get("field") == "status":
                    status_changed = True
                    new_status = item.get("toString")
                    break

        # If no changelog, get current status from fields
        if not status_changed:
            status_obj = fields.get("status", {})
            new_status = status_obj.get("name")

        # Handle based on entity type
        if mapping.entity_type == EntityType.ACTIVITY.value:
            return await self._update_activity_from_issue(
                mapping=mapping,
                issue_key=issue_key,
                fields=fields,
                status_changed=status_changed,
                new_status=new_status,
            )
        elif mapping.entity_type == EntityType.WBS.value:
            return await self._update_wbs_from_issue(
                mapping=mapping,
                issue_key=issue_key,
                fields=fields,
            )

        return WebhookResult(
            success=True,
            event_type=WEBHOOK_EVENT_ISSUE_UPDATED,
            issue_key=issue_key,
            entity_type=mapping.entity_type,
            action_taken="no_update_needed",
        )

    async def _update_activity_from_issue(
        self,
        mapping: JiraMapping,
        issue_key: str,
        fields: dict[str, Any],
        status_changed: bool,
        new_status: str | None,
    ) -> WebhookResult:
        """Update activity from Jira issue changes.

        Args:
            mapping: Entity mapping
            issue_key: Jira issue key
            fields: Issue fields
            status_changed: Whether status was changed
            new_status: New status name (if changed)

        Returns:
            WebhookResult
        """
        if not mapping.activity_id:
            return WebhookResult(
                success=False,
                event_type=WEBHOOK_EVENT_ISSUE_UPDATED,
                issue_key=issue_key,
                entity_type=EntityType.ACTIVITY.value,
                error_message="Mapping has no activity_id",
            )

        activity = await self.activity_repo.get(mapping.activity_id)
        if not activity:
            return WebhookResult(
                success=False,
                event_type=WEBHOOK_EVENT_ISSUE_UPDATED,
                issue_key=issue_key,
                entity_type=EntityType.ACTIVITY.value,
                error_message=f"Activity {mapping.activity_id} not found",
            )

        update_data: dict[str, Any] = {}
        action_parts: list[str] = []

        # Update name from summary
        summary = fields.get("summary")
        if summary and summary != activity.name:
            update_data["name"] = summary
            action_parts.append("name")

        # Update percent complete from status
        if status_changed and new_status:
            new_percent = self._status_to_percent(new_status)
            if new_percent is not None and new_percent != activity.percent_complete:
                update_data["percent_complete"] = new_percent
                action_parts.append(f"progress={new_percent}%")

        if update_data:
            await self.activity_repo.update(activity, update_data)
            action = f"updated_{'+'.join(action_parts)}"
        else:
            action = "no_changes"

        logger.info(
            "webhook_activity_updated",
            issue_key=issue_key,
            activity_id=str(mapping.activity_id),
            changes=action_parts,
        )

        return WebhookResult(
            success=True,
            event_type=WEBHOOK_EVENT_ISSUE_UPDATED,
            issue_key=issue_key,
            entity_type=EntityType.ACTIVITY.value,
            entity_id=mapping.activity_id,
            action_taken=action,
        )

    async def _update_wbs_from_issue(
        self,
        mapping: JiraMapping,
        issue_key: str,
        fields: dict[str, Any],
    ) -> WebhookResult:
        """Update WBS element from Jira issue (Epic) changes.

        Args:
            mapping: Entity mapping
            issue_key: Jira issue key
            fields: Issue fields

        Returns:
            WebhookResult
        """
        if not mapping.wbs_id:
            return WebhookResult(
                success=False,
                event_type=WEBHOOK_EVENT_ISSUE_UPDATED,
                issue_key=issue_key,
                entity_type=EntityType.WBS.value,
                error_message="Mapping has no wbs_id",
            )

        wbs = await self.wbs_repo.get(mapping.wbs_id)
        if not wbs:
            return WebhookResult(
                success=False,
                event_type=WEBHOOK_EVENT_ISSUE_UPDATED,
                issue_key=issue_key,
                entity_type=EntityType.WBS.value,
                error_message=f"WBS {mapping.wbs_id} not found",
            )

        update_data: dict[str, Any] = {}
        action_parts: list[str] = []

        # Update name from summary
        summary = fields.get("summary")
        if summary and summary != wbs.name:
            update_data["name"] = summary
            action_parts.append("name")

        # Update description
        description = fields.get("description")
        if description:
            # Jira description can be complex (ADF format), extract text
            desc_text = self._extract_description_text(description)
            if desc_text and desc_text != wbs.description:
                update_data["description"] = desc_text
                action_parts.append("description")

        if update_data:
            await self.wbs_repo.update(wbs, update_data)
            action = f"updated_{'+'.join(action_parts)}"
        else:
            action = "no_changes"

        logger.info(
            "webhook_wbs_updated",
            issue_key=issue_key,
            wbs_id=str(mapping.wbs_id),
            changes=action_parts,
        )

        return WebhookResult(
            success=True,
            event_type=WEBHOOK_EVENT_ISSUE_UPDATED,
            issue_key=issue_key,
            entity_type=EntityType.WBS.value,
            entity_id=mapping.wbs_id,
            action_taken=action,
        )

    async def _handle_issue_deleted(
        self,
        integration: JiraIntegration,
        mapping: JiraMapping,
        issue: dict[str, Any],
        payload: JiraWebhookPayload,
    ) -> WebhookResult:
        """Handle jira:issue_deleted event.

        Soft-deletes the mapping to preserve audit trail.
        Does not delete the linked entity.
        """
        issue_key = issue.get("key", "")

        # Soft delete the mapping
        await self.mapping_repo.delete(mapping.id)

        logger.info(
            "webhook_issue_deleted_processed",
            issue_key=issue_key,
            entity_type=mapping.entity_type,
            entity_id=str(mapping.activity_id or mapping.wbs_id),
            integration_id=str(integration.id),
            webhook_event=payload.webhookEvent,
        )

        return WebhookResult(
            success=True,
            event_type=WEBHOOK_EVENT_ISSUE_DELETED,
            issue_key=issue_key,
            entity_type=mapping.entity_type,
            entity_id=mapping.activity_id or mapping.wbs_id,
            action_taken="mapping_deleted",
        )

    def _status_to_percent(self, status: str) -> Decimal | None:
        """Convert Jira status to percent complete.

        Args:
            status: Jira status name

        Returns:
            Decimal percent complete, or None if unknown status
        """
        # Check direct mapping
        if status in JIRA_STATUS_TO_PERCENT:
            return JIRA_STATUS_TO_PERCENT[status]

        # Check case-insensitive
        status_lower = status.lower()
        for jira_status, percent in JIRA_STATUS_TO_PERCENT.items():
            if jira_status.lower() == status_lower:
                return percent

        # Common patterns
        if "done" in status_lower or "complete" in status_lower or "closed" in status_lower:
            return Decimal("100")
        if "progress" in status_lower or "active" in status_lower:
            return Decimal("50")
        if "todo" in status_lower or "open" in status_lower or "new" in status_lower:
            return Decimal("0")

        logger.warning(
            "webhook_unknown_status",
            status=status,
        )
        return None

    def _extract_description_text(self, description: Any) -> str | None:
        """Extract plain text from Jira description.

        Jira Cloud uses Atlassian Document Format (ADF) for descriptions.
        This extracts the text content.

        Args:
            description: Description field (string or ADF dict)

        Returns:
            Plain text description or None
        """
        if isinstance(description, str):
            return description

        if isinstance(description, dict):
            # ADF format - extract text from content
            content = description.get("content", [])
            texts = []
            for block in content:
                if block.get("type") == "paragraph":
                    for item in block.get("content", []):
                        if item.get("type") == "text":
                            texts.append(item.get("text", ""))
            return "\n".join(texts) if texts else None

        return None

    async def _log_sync(
        self,
        integration_id: UUID,
        mapping_id: UUID | None,
        sync_type: str,
        status: str,
        items_synced: int,
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Log sync operation to audit trail."""
        log_data: dict[str, Any] = {
            "integration_id": integration_id,
            "mapping_id": mapping_id,
            "sync_type": sync_type,
            "status": status,
            "items_synced": items_synced,
            "error_message": error_message,
            "duration_ms": duration_ms,
        }

        await self.sync_log_repo.create(log_data)
