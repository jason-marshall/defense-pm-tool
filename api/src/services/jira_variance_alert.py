"""Variance Alert to Jira Issue creation service.

Automatically creates Jira issues when variance explanations are added
for significant variances, enabling tracking and corrective action management.

Usage:
    service = VarianceAlertService(
        jira_client=client,
        integration_repo=integration_repo,
        mapping_repo=mapping_repo,
        sync_log_repo=sync_log_repo,
    )
    result = await service.create_variance_issue(
        integration_id=integration_id,
        variance=variance_explanation,
    )
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import structlog

from src.models.jira_sync_log import SyncStatus, SyncType
from src.services.jira_client import JiraClient, JiraSyncError

if TYPE_CHECKING:
    from uuid import UUID

    from src.models.jira_integration import JiraIntegration
    from src.models.jira_mapping import JiraMapping
    from src.models.variance_explanation import VarianceExplanation
    from src.repositories.jira_integration import JiraIntegrationRepository
    from src.repositories.jira_mapping import JiraMappingRepository
    from src.repositories.jira_sync_log import JiraSyncLogRepository


logger = structlog.get_logger(__name__)


class VarianceAlertError(Exception):
    """Base exception for variance alert operations."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class IntegrationNotFoundError(VarianceAlertError):
    """Jira integration not found."""

    pass


class SyncDisabledError(VarianceAlertError):
    """Sync is disabled for this integration."""

    pass


# Priority mappings based on variance percent severity
VARIANCE_PRIORITY_THRESHOLDS = [
    (Decimal("25.0"), "Highest"),  # >= 25% = Highest priority
    (Decimal("20.0"), "High"),  # >= 20% = High priority
    (Decimal("15.0"), "Medium"),  # >= 15% = Medium priority
    (Decimal("10.0"), "Low"),  # >= 10% = Low priority
    (Decimal("0.0"), "Lowest"),  # < 10% = Lowest priority
]

# Issue type mappings
VARIANCE_ISSUE_TYPES = {
    "cost": "Bug",  # Cost variances as bugs (budget issues)
    "schedule": "Task",  # Schedule variances as tasks
}


@dataclass
class VarianceIssueResult:
    """Result of creating a variance issue."""

    success: bool
    jira_issue_key: str | None = None
    jira_issue_id: str | None = None
    mapping_id: UUID | None = None
    error_message: str | None = None
    duration_ms: int = 0


@dataclass
class BatchCreateResult:
    """Result of batch variance issue creation."""

    success: bool
    issues_created: int
    issues_failed: int
    errors: list[str] = field(default_factory=list)
    created_issues: list[VarianceIssueResult] = field(default_factory=list)
    duration_ms: int = 0


class VarianceAlertService:
    """
    Service for creating Jira issues from variance alerts.

    Handles:
    - Automatic issue creation from variance explanations
    - Priority assignment based on variance severity
    - Epic linking through WBS mappings
    - Label management for filtering
    - Audit logging for compliance

    Attributes:
        jira_client: Jira API client
        integration_repo: Repository for Jira integrations
        mapping_repo: Repository for entity mappings
        sync_log_repo: Repository for sync audit logs
    """

    def __init__(
        self,
        jira_client: JiraClient,
        integration_repo: JiraIntegrationRepository,
        mapping_repo: JiraMappingRepository,
        sync_log_repo: JiraSyncLogRepository,
    ) -> None:
        """Initialize variance alert service.

        Args:
            jira_client: Jira API client instance
            integration_repo: Repository for Jira integrations
            mapping_repo: Repository for entity mappings
            sync_log_repo: Repository for sync audit logs
        """
        self.jira_client = jira_client
        self.integration_repo = integration_repo
        self.mapping_repo = mapping_repo
        self.sync_log_repo = sync_log_repo

    async def create_variance_issue(
        self,
        integration_id: UUID,
        variance: VarianceExplanation,
        wbs_name: str | None = None,
    ) -> VarianceIssueResult:
        """Create a Jira issue for a variance explanation.

        Creates a Jira issue with:
        - Summary describing the variance
        - Description with full variance details
        - Priority based on variance severity
        - Labels for categorization
        - Link to parent Epic (if WBS has mapping)

        Args:
            integration_id: Jira integration UUID
            variance: Variance explanation to create issue for
            wbs_name: Optional WBS element name for context

        Returns:
            VarianceIssueResult with issue details

        Raises:
            IntegrationNotFoundError: If integration doesn't exist
            SyncDisabledError: If sync is disabled
            VarianceAlertError: If issue creation fails
        """
        start_time = time.time()

        try:
            # Validate integration
            integration = await self._get_integration(integration_id)

            # Determine issue type based on variance type
            issue_type = VARIANCE_ISSUE_TYPES.get(variance.variance_type, "Task")

            # Build issue summary
            summary = self._build_issue_summary(variance, wbs_name)

            # Build issue description
            description = self._build_issue_description(variance, wbs_name)

            # Determine priority based on severity
            priority = self._get_priority_for_variance(variance.variance_percent)

            # Get parent Epic if WBS has mapping
            epic_key = None
            if variance.wbs_id:
                epic_key = await self._get_wbs_epic_key(integration_id, variance.wbs_id)

            # Build labels
            labels = self._build_labels(variance)

            # Create issue in Jira
            issue = await self.jira_client.create_issue(
                project_key=integration.project_key,
                summary=summary,
                issue_type=issue_type,
                description=description,
                epic_key=epic_key,
                labels=labels,
                custom_fields={"priority": {"name": priority}} if priority else None,
            )

            # Create mapping record for tracking
            mapping = await self._create_variance_mapping(
                integration_id=integration_id,
                variance_id=variance.id,
                jira_issue_key=issue.key,
                jira_issue_id=issue.id,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Log success
            await self._log_sync(
                integration_id=integration_id,
                sync_type=SyncType.PUSH.value,
                status=SyncStatus.SUCCESS.value,
                items_synced=1,
                duration_ms=duration_ms,
            )

            logger.info(
                "variance_issue_created",
                variance_id=str(variance.id),
                jira_key=issue.key,
                variance_type=variance.variance_type,
                variance_percent=str(variance.variance_percent),
                priority=priority,
            )

            return VarianceIssueResult(
                success=True,
                jira_issue_key=issue.key,
                jira_issue_id=issue.id,
                mapping_id=mapping.id if mapping else None,
                duration_ms=duration_ms,
            )

        except (IntegrationNotFoundError, SyncDisabledError):
            raise
        except JiraSyncError as e:
            duration_ms = int((time.time() - start_time) * 1000)

            await self._log_sync(
                integration_id=integration_id,
                sync_type=SyncType.PUSH.value,
                status=SyncStatus.FAILED.value,
                items_synced=0,
                error_message=str(e),
                duration_ms=duration_ms,
            )

            logger.warning(
                "variance_issue_creation_failed",
                variance_id=str(variance.id),
                error=str(e),
            )

            return VarianceIssueResult(
                success=False,
                error_message=str(e),
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            await self._log_sync(
                integration_id=integration_id,
                sync_type=SyncType.PUSH.value,
                status=SyncStatus.FAILED.value,
                items_synced=0,
                error_message=str(e),
                duration_ms=duration_ms,
            )

            logger.error(
                "variance_issue_creation_error",
                variance_id=str(variance.id),
                error=str(e),
            )

            raise VarianceAlertError(f"Failed to create variance issue: {e}") from e

    async def create_variance_issues_batch(
        self,
        integration_id: UUID,
        variances: list[tuple[VarianceExplanation, str | None]],
    ) -> BatchCreateResult:
        """Create Jira issues for multiple variance explanations.

        Args:
            integration_id: Jira integration UUID
            variances: List of (variance, wbs_name) tuples

        Returns:
            BatchCreateResult with creation statistics
        """
        start_time = time.time()
        result = BatchCreateResult(success=True, issues_created=0, issues_failed=0)

        try:
            # Validate integration once
            await self._get_integration(integration_id)

            for variance, wbs_name in variances:
                issue_result = await self.create_variance_issue(
                    integration_id=integration_id,
                    variance=variance,
                    wbs_name=wbs_name,
                )

                if issue_result.success:
                    result.issues_created += 1
                    result.created_issues.append(issue_result)
                else:
                    result.issues_failed += 1
                    if issue_result.error_message:
                        result.errors.append(
                            f"Variance {variance.id}: {issue_result.error_message}"
                        )

            result.duration_ms = int((time.time() - start_time) * 1000)

            if result.issues_failed > 0 and result.issues_created > 0:
                result.success = True  # Partial success
            elif result.issues_failed > 0:
                result.success = False

            return result

        except (IntegrationNotFoundError, SyncDisabledError):
            raise
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            result.duration_ms = int((time.time() - start_time) * 1000)
            raise VarianceAlertError(f"Batch creation failed: {e}") from e

    async def should_create_issue(
        self,
        variance: VarianceExplanation,
        threshold_percent: Decimal = Decimal("10.0"),
    ) -> bool:
        """Determine if a variance should trigger issue creation.

        Issues are created when:
        - Variance percent exceeds threshold
        - Variance has corrective action defined
        - Or variance has expected resolution date

        Args:
            variance: Variance explanation to evaluate
            threshold_percent: Minimum variance percent threshold

        Returns:
            True if issue should be created
        """
        # Check if variance exceeds threshold
        if abs(variance.variance_percent) >= threshold_percent:
            return True

        # Check if corrective action is defined (indicates significant issue)
        if variance.corrective_action:
            return True

        # Check if resolution date is set (indicates planned follow-up)
        return bool(variance.expected_resolution)

    async def _get_integration(self, integration_id: UUID) -> JiraIntegration:
        """Get and validate Jira integration."""
        integration = await self.integration_repo.get_by_id(integration_id)
        if not integration:
            raise IntegrationNotFoundError(
                f"Integration {integration_id} not found",
                {"integration_id": str(integration_id)},
            )

        if not integration.sync_enabled:
            raise SyncDisabledError(
                f"Sync is disabled for integration {integration_id}",
                {"integration_id": str(integration_id)},
            )

        return integration

    def _build_issue_summary(
        self,
        variance: VarianceExplanation,
        wbs_name: str | None = None,
    ) -> str:
        """Build issue summary from variance details.

        Format: "[VARIANCE] {type} variance of {percent}% - {wbs_name or 'Program Level'}"
        """
        variance_type = variance.variance_type.upper()
        percent = abs(variance.variance_percent)
        direction = "over" if variance.variance_amount > 0 else "under"

        if wbs_name:
            return f"[VARIANCE] {variance_type} {direction} {percent}% - {wbs_name}"
        return f"[VARIANCE] {variance_type} {direction} {percent}% - Program Level"

    def _build_issue_description(
        self,
        variance: VarianceExplanation,
        wbs_name: str | None = None,
    ) -> str:
        """Build detailed issue description from variance.

        Includes:
        - Variance details (type, amount, percent)
        - Explanation text
        - Corrective action (if provided)
        - Expected resolution date
        - Source attribution
        """
        lines = [
            "h2. Variance Details",
            "",
            f"*Variance Type:* {variance.variance_type.upper()}",
            f"*Variance Amount:* ${variance.variance_amount:,.2f}",
            f"*Variance Percent:* {variance.variance_percent:.2f}%",
        ]

        if wbs_name:
            lines.append(f"*WBS Element:* {wbs_name}")

        lines.extend(
            [
                "",
                "h2. Explanation",
                "",
                variance.explanation,
            ]
        )

        if variance.corrective_action:
            lines.extend(
                [
                    "",
                    "h2. Corrective Action Plan",
                    "",
                    variance.corrective_action,
                ]
            )

        if variance.expected_resolution:
            lines.extend(
                [
                    "",
                    f"*Expected Resolution Date:* {variance.expected_resolution}",
                ]
            )

        lines.extend(
            [
                "",
                "----",
                "_Created automatically from Defense PM Tool variance alert._",
            ]
        )

        return "\n".join(lines)

    def _get_priority_for_variance(self, variance_percent: Decimal) -> str:
        """Determine Jira priority based on variance severity.

        Args:
            variance_percent: The variance percentage (absolute value used)

        Returns:
            Jira priority name
        """
        abs_percent = abs(variance_percent)

        for threshold, priority in VARIANCE_PRIORITY_THRESHOLDS:
            if abs_percent >= threshold:
                return priority

        return "Lowest"

    def _build_labels(self, variance: VarianceExplanation) -> list[str]:
        """Build labels for the Jira issue.

        Labels include:
        - defense-pm-tool (source)
        - variance-alert (type)
        - variance type (cost/schedule)
        - severity level
        """
        labels = [
            "defense-pm-tool",
            "variance-alert",
            f"variance-{variance.variance_type}",
        ]

        # Add severity label
        abs_percent = abs(variance.variance_percent)
        if abs_percent >= Decimal("25.0"):
            labels.append("severity-critical")
        elif abs_percent >= Decimal("20.0"):
            labels.append("severity-high")
        elif abs_percent >= Decimal("15.0"):
            labels.append("severity-medium")
        else:
            labels.append("severity-low")

        return labels

    async def _get_wbs_epic_key(
        self,
        integration_id: UUID,
        wbs_id: UUID,
    ) -> str | None:
        """Get the Jira Epic key for a WBS element."""
        wbs_mapping = await self.mapping_repo.get_by_wbs(integration_id, wbs_id)
        if wbs_mapping:
            return wbs_mapping.jira_issue_key
        return None

    async def _create_variance_mapping(
        self,
        integration_id: UUID,
        variance_id: UUID,
        jira_issue_key: str,
        jira_issue_id: str,
    ) -> JiraMapping | None:
        """Create a mapping record for the variance issue.

        Note: This uses a custom entity type for variance mappings since
        the JiraMapping model doesn't have a variance_id field. We store
        the variance ID as metadata in the mapping.
        """
        # For now, we don't create a mapping since the model doesn't support
        # variance_id. In a future update, we could extend the model.
        # This is a placeholder for future implementation.
        logger.debug(
            "variance_mapping_skipped",
            integration_id=str(integration_id),
            variance_id=str(variance_id),
            jira_key=jira_issue_key,
            jira_id=jira_issue_id,
        )
        return None

    async def _log_sync(
        self,
        integration_id: UUID,
        sync_type: str,
        status: str,
        items_synced: int,
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Log sync operation to audit trail."""
        log_data: dict[str, Any] = {
            "integration_id": integration_id,
            "sync_type": sync_type,
            "status": status,
            "items_synced": items_synced,
            "error_message": error_message,
            "duration_ms": duration_ms,
        }

        await self.sync_log_repo.create(log_data)
