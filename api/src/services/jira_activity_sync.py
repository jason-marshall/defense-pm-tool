"""Activity to Jira Issue synchronization service.

Provides bidirectional sync between Activities and Jira Issues (Tasks/Stories).
Supports:
- Push Activities to Jira as Issues
- Link to parent Epic (from WBS mapping)
- Sync progress and status
- Pull Issue updates from Jira
- Comprehensive audit logging

Usage:
    service = ActivitySyncService(
        jira_client=client,
        integration_repo=integration_repo,
        mapping_repo=mapping_repo,
        sync_log_repo=sync_log_repo,
        activity_repo=activity_repo,
    )
    result = await service.sync_activities_to_jira(integration_id, activity_ids)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import structlog

from src.models.jira_mapping import EntityType, SyncDirection
from src.models.jira_sync_log import SyncStatus, SyncType
from src.services.jira_client import JiraClient, JiraSyncError

if TYPE_CHECKING:
    from uuid import UUID

    from src.models.activity import Activity
    from src.models.jira_integration import JiraIntegration
    from src.models.jira_mapping import JiraMapping
    from src.repositories.activity import ActivityRepository
    from src.repositories.jira_integration import JiraIntegrationRepository
    from src.repositories.jira_mapping import JiraMappingRepository
    from src.repositories.jira_sync_log import JiraSyncLogRepository


logger = structlog.get_logger(__name__)


class ActivitySyncError(Exception):
    """Base exception for Activity sync operations."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class IntegrationNotFoundError(ActivitySyncError):
    """Jira integration not found."""

    pass


class SyncDisabledError(ActivitySyncError):
    """Sync is disabled for this integration."""

    pass


class ParentEpicNotFoundError(ActivitySyncError):
    """Parent WBS element has no Epic mapping."""

    pass


# Jira status mappings based on percent_complete
JIRA_STATUS_MAPPINGS = {
    "not_started": "To Do",
    "in_progress": "In Progress",
    "completed": "Done",
}


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    items_synced: int
    items_failed: int
    errors: list[str] = field(default_factory=list)
    created_mappings: list[UUID] = field(default_factory=list)
    updated_mappings: list[UUID] = field(default_factory=list)
    duration_ms: int = 0


@dataclass
class ActivitySyncItem:
    """Represents an Activity to sync with its mapping status."""

    activity: Activity
    mapping: JiraMapping | None
    parent_epic_key: str | None
    action: str  # "create", "update", "skip"
    jira_key: str | None = None
    error: str | None = None


class ActivitySyncService:
    """
    Service for syncing Activities to Jira Issues.

    Handles:
    - Activity → Task/Story creation
    - Link to parent Epic (from WBS mapping)
    - Progress and status sync
    - Bidirectional updates
    - Audit logging for compliance

    Attributes:
        jira_client: Jira API client
        integration_repo: Repository for Jira integrations
        mapping_repo: Repository for entity mappings
        sync_log_repo: Repository for sync audit logs
        activity_repo: Repository for activities
    """

    def __init__(
        self,
        jira_client: JiraClient,
        integration_repo: JiraIntegrationRepository,
        mapping_repo: JiraMappingRepository,
        sync_log_repo: JiraSyncLogRepository,
        activity_repo: ActivityRepository,
    ) -> None:
        """Initialize Activity sync service.

        Args:
            jira_client: Jira API client instance
            integration_repo: Repository for Jira integrations
            mapping_repo: Repository for entity mappings
            sync_log_repo: Repository for sync audit logs
            activity_repo: Repository for activities
        """
        self.jira_client = jira_client
        self.integration_repo = integration_repo
        self.mapping_repo = mapping_repo
        self.sync_log_repo = sync_log_repo
        self.activity_repo = activity_repo

    async def sync_activities_to_jira(
        self,
        integration_id: UUID,
        activity_ids: list[UUID] | None = None,
    ) -> SyncResult:
        """Sync Activities to Jira as Issues.

        Creates new Issues for unmapped Activities and updates
        existing mappings when Activity data has changed.

        Args:
            integration_id: Jira integration UUID
            activity_ids: Optional list of specific Activity IDs to sync.
                         If None, syncs all activities for the program.

        Returns:
            SyncResult with sync statistics

        Raises:
            IntegrationNotFoundError: If integration doesn't exist
            SyncDisabledError: If sync is disabled
            ActivitySyncError: If sync fails
        """
        start_time = time.time()
        result = SyncResult(success=True, items_synced=0, items_failed=0)

        try:
            # Validate integration
            integration = await self._get_integration(integration_id)

            # Get activities to sync
            activities = await self._get_syncable_activities(integration.program_id, activity_ids)

            if not activities:
                logger.info(
                    "activity_sync_no_elements",
                    integration_id=str(integration_id),
                )
                return result

            # Prepare sync items with mapping status and parent epic
            sync_items = await self._prepare_sync_items(integration_id, activities)

            # Process each item
            for item in sync_items:
                try:
                    if item.action == "create":
                        new_mapping = await self._create_issue(integration, item)
                        result.created_mappings.append(new_mapping.id)
                        result.items_synced += 1
                    elif item.action == "update":
                        updated_mapping = await self._update_issue(
                            integration, item.activity, item.mapping
                        )
                        if updated_mapping:
                            result.updated_mappings.append(updated_mapping.id)
                        result.items_synced += 1
                    # Skip items are not counted
                except JiraSyncError as e:
                    item.error = str(e)
                    result.errors.append(f"Activity {item.activity.code}: {e}")
                    result.items_failed += 1
                    logger.warning(
                        "activity_sync_item_failed",
                        activity_id=str(item.activity.id),
                        activity_code=item.activity.code,
                        error=str(e),
                    )

            # Determine overall status
            if result.items_failed > 0 and result.items_synced > 0:
                result.success = True  # Partial success
                sync_status = SyncStatus.PARTIAL.value
            elif result.items_failed > 0:
                result.success = False
                sync_status = SyncStatus.FAILED.value
            else:
                sync_status = SyncStatus.SUCCESS.value

            # Calculate duration
            result.duration_ms = int((time.time() - start_time) * 1000)

            # Log sync operation
            await self._log_sync(
                integration_id=integration_id,
                sync_type=SyncType.PUSH.value,
                status=sync_status,
                items_synced=result.items_synced,
                error_message="; ".join(result.errors) if result.errors else None,
                duration_ms=result.duration_ms,
            )

            # Update integration last_sync_at
            if result.items_synced > 0:
                await self._update_integration_sync_time(integration)

            logger.info(
                "activity_sync_completed",
                integration_id=str(integration_id),
                items_synced=result.items_synced,
                items_failed=result.items_failed,
                duration_ms=result.duration_ms,
            )

            return result

        except (IntegrationNotFoundError, SyncDisabledError):
            raise
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            result.duration_ms = int((time.time() - start_time) * 1000)

            await self._log_sync(
                integration_id=integration_id,
                sync_type=SyncType.PUSH.value,
                status=SyncStatus.FAILED.value,
                items_synced=0,
                error_message=str(e),
                duration_ms=result.duration_ms,
            )

            logger.error(
                "activity_sync_failed",
                integration_id=str(integration_id),
                error=str(e),
            )
            raise ActivitySyncError(f"Activity sync failed: {e}") from e

    async def pull_from_jira(
        self,
        integration_id: UUID,
        mapping_ids: list[UUID] | None = None,
    ) -> SyncResult:
        """Pull updates from Jira Issues to Activities.

        Fetches Issue data from Jira and updates corresponding Activities
        when Jira has newer changes (conflict resolution: last-write-wins).

        Args:
            integration_id: Jira integration UUID
            mapping_ids: Optional list of specific mapping IDs to pull.
                        If None, pulls all mapped Activities.

        Returns:
            SyncResult with sync statistics

        Raises:
            IntegrationNotFoundError: If integration doesn't exist
            SyncDisabledError: If sync is disabled
            ActivitySyncError: If pull fails
        """
        start_time = time.time()
        result = SyncResult(success=True, items_synced=0, items_failed=0)

        try:
            integration = await self._get_integration(integration_id)

            # Get mappings to pull
            mappings = await self._get_mappings_for_pull(integration_id, mapping_ids)

            if not mappings:
                logger.info(
                    "activity_pull_no_mappings",
                    integration_id=str(integration_id),
                )
                return result

            # Process each mapping
            for mapping in mappings:
                try:
                    updated = await self._pull_issue_to_activity(mapping)
                    if updated:
                        result.updated_mappings.append(mapping.id)
                    result.items_synced += 1
                except JiraSyncError as e:
                    result.errors.append(f"Issue {mapping.jira_issue_key}: {e}")
                    result.items_failed += 1
                    logger.warning(
                        "activity_pull_item_failed",
                        mapping_id=str(mapping.id),
                        jira_key=mapping.jira_issue_key,
                        error=str(e),
                    )

            # Determine overall status
            if result.items_failed > 0 and result.items_synced > 0:
                sync_status = SyncStatus.PARTIAL.value
            elif result.items_failed > 0:
                result.success = False
                sync_status = SyncStatus.FAILED.value
            else:
                sync_status = SyncStatus.SUCCESS.value

            result.duration_ms = int((time.time() - start_time) * 1000)

            await self._log_sync(
                integration_id=integration_id,
                sync_type=SyncType.PULL.value,
                status=sync_status,
                items_synced=result.items_synced,
                error_message="; ".join(result.errors) if result.errors else None,
                duration_ms=result.duration_ms,
            )

            if result.items_synced > 0:
                await self._update_integration_sync_time(integration)

            logger.info(
                "activity_pull_completed",
                integration_id=str(integration_id),
                items_synced=result.items_synced,
                items_failed=result.items_failed,
                duration_ms=result.duration_ms,
            )

            return result

        except (IntegrationNotFoundError, SyncDisabledError):
            raise
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            result.duration_ms = int((time.time() - start_time) * 1000)

            await self._log_sync(
                integration_id=integration_id,
                sync_type=SyncType.PULL.value,
                status=SyncStatus.FAILED.value,
                items_synced=0,
                error_message=str(e),
                duration_ms=result.duration_ms,
            )

            logger.error(
                "activity_pull_failed",
                integration_id=str(integration_id),
                error=str(e),
            )
            raise ActivitySyncError(f"Activity pull failed: {e}") from e

    async def sync_progress(
        self,
        integration_id: UUID,
        activity_ids: list[UUID] | None = None,
    ) -> SyncResult:
        """Sync activity progress to Jira Issues.

        Updates percent_complete and triggers status transitions in Jira.

        Args:
            integration_id: Jira integration UUID
            activity_ids: Optional list of specific Activity IDs to sync

        Returns:
            SyncResult with sync statistics
        """
        start_time = time.time()
        result = SyncResult(success=True, items_synced=0, items_failed=0)

        try:
            # Validate integration exists and is enabled
            await self._get_integration(integration_id)

            # Get mapped activities
            mappings = await self.mapping_repo.get_by_integration(
                integration_id, entity_type=EntityType.ACTIVITY.value
            )

            if activity_ids:
                mappings = [m for m in mappings if m.activity_id in activity_ids]

            for mapping in mappings:
                if mapping.activity_id is None:
                    continue

                try:
                    activity = await self.activity_repo.get_by_id(mapping.activity_id)
                    if not activity:
                        continue

                    await self._sync_activity_progress(mapping, activity)
                    result.updated_mappings.append(mapping.id)
                    result.items_synced += 1
                except JiraSyncError as e:
                    result.errors.append(f"Issue {mapping.jira_issue_key}: {e}")
                    result.items_failed += 1

            sync_status = (
                SyncStatus.PARTIAL.value
                if result.items_failed > 0 and result.items_synced > 0
                else SyncStatus.SUCCESS.value
                if result.items_failed == 0
                else SyncStatus.FAILED.value
            )

            result.duration_ms = int((time.time() - start_time) * 1000)

            await self._log_sync(
                integration_id=integration_id,
                sync_type=SyncType.PUSH.value,
                status=sync_status,
                items_synced=result.items_synced,
                error_message="; ".join(result.errors) if result.errors else None,
                duration_ms=result.duration_ms,
            )

            return result

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            result.duration_ms = int((time.time() - start_time) * 1000)
            raise ActivitySyncError(f"Progress sync failed: {e}") from e

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

    async def _get_syncable_activities(
        self,
        program_id: UUID,
        activity_ids: list[UUID] | None = None,
    ) -> list[Activity]:
        """Get Activities eligible for sync."""
        all_activities = await self.activity_repo.get_by_program(program_id)

        # Filter to specific IDs if provided
        if activity_ids:
            all_activities = [a for a in all_activities if a.id in activity_ids]

        return all_activities

    async def _prepare_sync_items(
        self,
        integration_id: UUID,
        activities: list[Activity],
    ) -> list[ActivitySyncItem]:
        """Prepare sync items with mapping status and parent epic."""
        items = []

        for activity in activities:
            mapping = await self.mapping_repo.get_by_activity(integration_id, activity.id)

            # Get parent WBS Epic mapping
            parent_epic_key = await self._get_parent_epic_key(integration_id, activity.wbs_id)

            if mapping is None:
                # New Activity - create Issue
                items.append(
                    ActivitySyncItem(
                        activity=activity,
                        mapping=None,
                        parent_epic_key=parent_epic_key,
                        action="create",
                    )
                )
            elif mapping.sync_direction in (
                SyncDirection.TO_JIRA.value,
                SyncDirection.BIDIRECTIONAL.value,
            ):
                # Existing mapping - update Issue
                items.append(
                    ActivitySyncItem(
                        activity=activity,
                        mapping=mapping,
                        parent_epic_key=parent_epic_key,
                        action="update",
                    )
                )
            else:
                # From Jira only - skip push
                items.append(
                    ActivitySyncItem(
                        activity=activity,
                        mapping=mapping,
                        parent_epic_key=parent_epic_key,
                        action="skip",
                    )
                )

        return items

    async def _get_parent_epic_key(
        self,
        integration_id: UUID,
        wbs_id: UUID,
    ) -> str | None:
        """Get the Jira Epic key for the parent WBS element."""
        wbs_mapping = await self.mapping_repo.get_by_wbs(integration_id, wbs_id)
        if wbs_mapping:
            return wbs_mapping.jira_issue_key
        return None

    async def _create_issue(
        self,
        integration: JiraIntegration,
        item: ActivitySyncItem,
    ) -> JiraMapping:
        """Create a Jira Issue for an Activity.

        Args:
            integration: Jira integration config
            item: Activity sync item with parent epic info

        Returns:
            Created JiraMapping
        """
        activity = item.activity
        description = self._build_issue_description(activity)

        # Determine issue type based on activity
        issue_type = "Task"
        if activity.is_milestone:
            issue_type = "Task"  # Could be customized

        # Create Issue in Jira
        issue = await self.jira_client.create_issue(
            project_key=integration.project_key,
            summary=activity.name,
            issue_type=issue_type,
            description=description,
            epic_key=item.parent_epic_key,
            labels=["defense-pm-tool", f"activity-{activity.code}"],
        )

        # Create mapping record
        mapping_data: dict[str, Any] = {
            "integration_id": integration.id,
            "entity_type": EntityType.ACTIVITY.value,
            "activity_id": activity.id,
            "jira_issue_key": issue.key,
            "jira_issue_id": issue.id,
            "sync_direction": SyncDirection.BIDIRECTIONAL.value,
            "last_synced_at": datetime.now(UTC),
            "last_jira_updated": issue.updated,
        }

        mapping = await self.mapping_repo.create(mapping_data)

        logger.info(
            "activity_issue_created",
            activity_id=str(activity.id),
            activity_code=activity.code,
            issue_key=issue.key,
            epic_key=item.parent_epic_key,
        )

        return mapping

    async def _update_issue(
        self,
        _integration: JiraIntegration,
        activity: Activity,
        mapping: JiraMapping | None,
    ) -> JiraMapping | None:
        """Update existing Jira Issue from Activity data.

        Args:
            _integration: Jira integration config (reserved for future use)
            activity: Activity with updated data
            mapping: Existing mapping to update

        Returns:
            Updated JiraMapping or None if no update needed
        """
        if mapping is None:
            return None

        # Build updated fields
        description = self._build_issue_description(activity)

        # Update Issue in Jira
        await self.jira_client.update_issue(
            issue_key=mapping.jira_issue_key,
            summary=activity.name,
            description=description,
        )

        # Update mapping record
        mapping.last_synced_at = datetime.now(UTC)
        await self.mapping_repo.update(mapping, {"last_synced_at": mapping.last_synced_at})

        logger.info(
            "activity_issue_updated",
            activity_id=str(activity.id),
            activity_code=activity.code,
            issue_key=mapping.jira_issue_key,
        )

        return mapping

    def _build_issue_description(self, activity: Activity) -> str:
        """Build Issue description from Activity.

        Includes:
        - Activity code and schedule info
        - Duration and dates
        - Progress status
        - Link back to Defense PM Tool
        """
        lines = [
            f"*Activity Code:* {activity.code}",
            f"*Duration:* {activity.duration} days",
        ]

        if activity.planned_start:
            lines.append(f"*Planned Start:* {activity.planned_start}")
        if activity.planned_finish:
            lines.append(f"*Planned Finish:* {activity.planned_finish}")

        if activity.early_start:
            lines.append(f"*Early Start:* {activity.early_start}")
        if activity.early_finish:
            lines.append(f"*Early Finish:* {activity.early_finish}")

        lines.append(f"\n*Progress:* {activity.percent_complete}%")

        if activity.is_critical:
            lines.append("\n_This activity is on the critical path._")

        if activity.is_milestone:
            lines.append("\n_This is a milestone._")

        if activity.description:
            lines.append(f"\n{activity.description}")

        lines.append("\n---")
        lines.append("_Synced from Defense PM Tool_")

        return "\n".join(lines)

    async def _get_mappings_for_pull(
        self,
        integration_id: UUID,
        mapping_ids: list[UUID] | None = None,
    ) -> list[JiraMapping]:
        """Get mappings eligible for pull from Jira."""
        all_mappings = await self.mapping_repo.get_by_integration(
            integration_id, entity_type=EntityType.ACTIVITY.value
        )

        # Filter to specific IDs if provided
        if mapping_ids:
            all_mappings = [m for m in all_mappings if m.id in mapping_ids]

        # Filter to mappings that allow pull
        pullable = [
            m
            for m in all_mappings
            if m.sync_direction
            in (SyncDirection.FROM_JIRA.value, SyncDirection.BIDIRECTIONAL.value)
        ]

        return pullable

    async def _pull_issue_to_activity(
        self,
        mapping: JiraMapping,
    ) -> bool:
        """Pull Issue data from Jira and update Activity if newer.

        Uses last-write-wins conflict resolution based on timestamps.

        Args:
            mapping: Activity-Issue mapping

        Returns:
            True if Activity was updated, False if no update needed
        """
        if mapping.activity_id is None:
            return False

        # Fetch current Issue from Jira
        issue = await self.jira_client.get_issue(mapping.jira_issue_key)

        # Check if Jira has newer changes (conflict resolution)
        if mapping.last_jira_updated and issue.updated <= mapping.last_jira_updated:
            logger.debug(
                "activity_pull_skipped_no_changes",
                mapping_id=str(mapping.id),
                jira_key=mapping.jira_issue_key,
            )
            return False

        # Get Activity
        activity = await self.activity_repo.get_by_id(mapping.activity_id)
        if not activity:
            logger.warning(
                "activity_pull_activity_not_found",
                mapping_id=str(mapping.id),
                activity_id=str(mapping.activity_id),
            )
            return False

        # Update Activity from Issue
        update_data: dict[str, Any] = {"name": issue.summary}

        # Map Jira status to percent_complete
        jira_status = issue.status.lower()
        if "done" in jira_status or "complete" in jira_status:
            update_data["percent_complete"] = Decimal("100.00")
        elif "progress" in jira_status and activity.percent_complete == Decimal("0.00"):
            # Set to 50% if activity was not started but Jira shows in progress
            update_data["percent_complete"] = Decimal("50.00")

        await self.activity_repo.update(activity, update_data)

        # Update mapping timestamps
        mapping.last_synced_at = datetime.now(UTC)
        mapping.last_jira_updated = issue.updated
        await self.mapping_repo.update(
            mapping,
            {
                "last_synced_at": mapping.last_synced_at,
                "last_jira_updated": mapping.last_jira_updated,
            },
        )

        logger.info(
            "activity_pulled_from_jira",
            activity_id=str(activity.id),
            activity_code=activity.code,
            issue_key=mapping.jira_issue_key,
        )

        return True

    async def _sync_activity_progress(
        self,
        mapping: JiraMapping,
        activity: Activity,
    ) -> None:
        """Sync activity progress to Jira Issue.

        Updates status based on percent_complete:
        - 0%: To Do
        - 1-99%: In Progress
        - 100%: Done
        """
        # Determine target status
        if activity.percent_complete >= Decimal("100.00"):
            target_status = JIRA_STATUS_MAPPINGS["completed"]
        elif activity.percent_complete > Decimal("0.00"):
            target_status = JIRA_STATUS_MAPPINGS["in_progress"]
        else:
            target_status = JIRA_STATUS_MAPPINGS["not_started"]

        # Get current Jira status
        issue = await self.jira_client.get_issue(mapping.jira_issue_key)

        # Transition if needed
        if issue.status.lower() != target_status.lower():
            try:
                await self.jira_client.transition_issue(mapping.jira_issue_key, target_status)
                logger.info(
                    "activity_status_transitioned",
                    issue_key=mapping.jira_issue_key,
                    from_status=issue.status,
                    to_status=target_status,
                )
            except JiraSyncError as e:
                # Log but don't fail - transition might not be available
                logger.warning(
                    "activity_status_transition_failed",
                    issue_key=mapping.jira_issue_key,
                    target_status=target_status,
                    error=str(e),
                )

        # Update mapping
        mapping.last_synced_at = datetime.now(UTC)
        await self.mapping_repo.update(mapping, {"last_synced_at": mapping.last_synced_at})

    async def _log_sync(
        self,
        integration_id: UUID,
        sync_type: str,
        status: str,
        items_synced: int,
        error_message: str | None = None,
        duration_ms: int | None = None,
        mapping_id: UUID | None = None,
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

    async def _update_integration_sync_time(
        self,
        integration: JiraIntegration,
    ) -> None:
        """Update integration's last_sync_at timestamp."""
        await self.integration_repo.update(
            integration,
            {"last_sync_at": datetime.now(UTC)},
        )
