"""Jira Webhook API endpoints.

Receives webhooks from Jira for real-time updates:
- Issue created/updated/deleted events
- Status change propagation
- Bidirectional sync support

Security:
- Signature verification using webhook secret
- Rate limiting recommended at infrastructure level
"""

from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Header, HTTPException, Request, status

from src.config import settings
from src.core.deps import DbSession
from src.core.rate_limit import RATE_LIMIT_WEBHOOK, limiter
from src.repositories.activity import ActivityRepository
from src.repositories.jira_integration import JiraIntegrationRepository
from src.repositories.jira_mapping import JiraMappingRepository
from src.repositories.jira_sync_log import JiraSyncLogRepository
from src.repositories.wbs import WBSElementRepository
from src.schemas.jira_integration import JiraWebhookPayload
from src.services.jira_webhook_processor import (
    JiraWebhookProcessor,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


class WebhookResponse:
    """Response model for webhook processing."""

    def __init__(
        self,
        success: bool,
        message: str,
        event_type: str | None = None,
        issue_key: str | None = None,
        action: str | None = None,
    ):
        self.success = success
        self.message = message
        self.event_type = event_type
        self.issue_key = issue_key
        self.action = action

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "success": self.success,
            "message": self.message,
            "event_type": self.event_type,
            "issue_key": self.issue_key,
            "action": self.action,
        }


@router.post(
    "/jira",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Webhook processed successfully"},
        400: {"description": "Invalid webhook payload"},
        401: {"description": "Invalid webhook signature"},
        500: {"description": "Internal processing error"},
    },
)
@limiter.limit(RATE_LIMIT_WEBHOOK)
async def receive_jira_webhook(
    request: Request,
    db: DbSession,
    x_hub_signature: Annotated[str | None, Header(alias="X-Hub-Signature")] = None,
    x_atlassian_webhook_identifier: Annotated[
        str | None, Header(alias="X-Atlassian-Webhook-Identifier")
    ] = None,
) -> dict[str, Any]:
    """
    Receive and process Jira webhooks.

    This endpoint handles incoming webhooks from Jira Cloud for real-time
    synchronization. It processes the following events:
    - jira:issue_created - New issues linked to mappings
    - jira:issue_updated - Updates to linked issues (status, summary, etc.)
    - jira:issue_deleted - Soft-deletes mappings for deleted issues

    Headers:
    - X-Hub-Signature: HMAC-SHA256 signature for verification (optional based on config)
    - X-Atlassian-Webhook-Identifier: Unique webhook ID from Jira

    Note: For security, configure a webhook secret in Jira and set
    JIRA_WEBHOOK_SECRET in environment to enable signature verification.
    """
    # Get raw body for signature verification
    raw_body = await request.body()

    # Verify signature if secret is configured
    webhook_secret = getattr(settings, "jira_webhook_secret", None)
    if webhook_secret:
        processor = _create_processor(db)
        if not processor.verify_signature(raw_body, x_hub_signature or "", webhook_secret):
            logger.warning(
                "webhook_signature_invalid",
                webhook_id=x_atlassian_webhook_identifier,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    # Parse payload
    try:
        payload_dict = await request.json()
        payload = JiraWebhookPayload(**payload_dict)
    except Exception as e:
        logger.error(
            "webhook_parse_error",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid webhook payload: {e}",
        ) from e

    logger.info(
        "webhook_received",
        event=payload.webhookEvent,
        webhook_id=x_atlassian_webhook_identifier,
        issue_key=payload.issue.get("key") if payload.issue else None,
    )

    # Process the webhook
    processor = _create_processor(db)

    try:
        result = await processor.process_webhook(payload)
        await db.commit()

        logger.info(
            "webhook_processed",
            event=payload.webhookEvent,
            success=result.success,
            action=result.action_taken,
            issue_key=result.issue_key,
            duration_ms=result.duration_ms,
        )

        return {
            "success": result.success,
            "message": "Webhook processed successfully" if result.success else result.error_message,
            "event_type": result.event_type,
            "issue_key": result.issue_key,
            "action": result.action_taken,
        }

    except Exception as e:
        logger.error(
            "webhook_processing_error",
            event=payload.webhookEvent,
            error=str(e),
        )
        # Return 200 to prevent Jira from retrying for unrecoverable errors
        # but indicate failure in response body
        return {
            "success": False,
            "message": f"Processing error: {e}",
            "event_type": payload.webhookEvent,
            "issue_key": payload.issue.get("key") if payload.issue else None,
            "action": None,
        }


@router.post(
    "/jira/{integration_id}",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Webhook processed successfully"},
        400: {"description": "Invalid webhook payload"},
        401: {"description": "Invalid webhook signature"},
        404: {"description": "Integration not found"},
        500: {"description": "Internal processing error"},
    },
)
async def receive_jira_webhook_for_integration(
    request: Request,
    db: DbSession,
    integration_id: UUID,
    x_hub_signature: Annotated[str | None, Header(alias="X-Hub-Signature")] = None,
    x_atlassian_webhook_identifier: Annotated[
        str | None, Header(alias="X-Atlassian-Webhook-Identifier")
    ] = None,
) -> dict[str, Any]:
    """
    Receive Jira webhooks for a specific integration.

    This endpoint is an alternative that includes the integration ID in the URL,
    useful when you have integration-specific webhook URLs configured in Jira.

    Args:
        integration_id: UUID of the Jira integration
    """
    # Get raw body for signature verification
    raw_body = await request.body()

    # Verify integration exists
    integration_repo = JiraIntegrationRepository(db)
    integration = await integration_repo.get(integration_id)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration {integration_id} not found",
        )

    # Verify signature if configured
    # Could use per-integration secrets in the future
    webhook_secret = getattr(settings, "jira_webhook_secret", None)
    if webhook_secret:
        processor = _create_processor(db)
        if not processor.verify_signature(raw_body, x_hub_signature or "", webhook_secret):
            logger.warning(
                "webhook_signature_invalid",
                integration_id=str(integration_id),
                webhook_id=x_atlassian_webhook_identifier,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    # Parse payload
    try:
        payload_dict = await request.json()
        payload = JiraWebhookPayload(**payload_dict)
    except Exception as e:
        logger.error(
            "webhook_parse_error",
            integration_id=str(integration_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid webhook payload: {e}",
        ) from e

    logger.info(
        "webhook_received",
        event=payload.webhookEvent,
        integration_id=str(integration_id),
        webhook_id=x_atlassian_webhook_identifier,
        issue_key=payload.issue.get("key") if payload.issue else None,
    )

    # Process the webhook with known integration
    processor = _create_processor(db)

    try:
        result = await processor.process_webhook(payload, integration_id=integration_id)
        await db.commit()

        logger.info(
            "webhook_processed",
            event=payload.webhookEvent,
            integration_id=str(integration_id),
            success=result.success,
            action=result.action_taken,
            issue_key=result.issue_key,
            duration_ms=result.duration_ms,
        )

        return {
            "success": result.success,
            "message": "Webhook processed successfully" if result.success else result.error_message,
            "event_type": result.event_type,
            "issue_key": result.issue_key,
            "action": result.action_taken,
        }

    except Exception as e:
        logger.error(
            "webhook_processing_error",
            event=payload.webhookEvent,
            integration_id=str(integration_id),
            error=str(e),
        )
        return {
            "success": False,
            "message": f"Processing error: {e}",
            "event_type": payload.webhookEvent,
            "issue_key": payload.issue.get("key") if payload.issue else None,
            "action": None,
        }


@router.get(
    "/jira/health",
    status_code=status.HTTP_200_OK,
)
async def webhook_health_check() -> dict[str, Any]:
    """
    Health check endpoint for webhook receiver.

    Use this endpoint to verify the webhook receiver is operational.
    Jira can also use this for connectivity testing.
    """
    return {
        "status": "healthy",
        "service": "jira-webhook-receiver",
        "signature_verification": bool(getattr(settings, "jira_webhook_secret", None)),
    }


def _create_processor(db: DbSession) -> JiraWebhookProcessor:
    """Create a JiraWebhookProcessor with all dependencies.

    Args:
        db: Database session

    Returns:
        Configured JiraWebhookProcessor instance
    """
    return JiraWebhookProcessor(
        integration_repo=JiraIntegrationRepository(db),
        mapping_repo=JiraMappingRepository(db),
        activity_repo=ActivityRepository(db),
        wbs_repo=WBSElementRepository(db),
        sync_log_repo=JiraSyncLogRepository(db),
    )
