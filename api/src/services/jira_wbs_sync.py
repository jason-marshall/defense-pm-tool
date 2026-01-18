"""WBS to Jira Epic synchronization service.

Provides bidirectional sync between WBS elements (levels 1-2) and Jira Epics.
Supports:
- Push WBS elements to Jira as Epics
- Pull Epic updates from Jira
- Conflict resolution (last-write-wins)
- Comprehensive audit logging

Usage:
    service = WBSSyncService(
        jira_client=client,
        integration_repo=integration_repo,
        mapping_repo=mapping_repo,
        sync_log_repo=sync_log_repo,
        wbs_repo=wbs_repo,
    )
    result = await service.sync_wbs_to_jira(integration_id, wbs_ids)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from src.models.jira_mapping import EntityType, SyncDirection
from src.models.jira_sync_log import SyncStatus, SyncType
from src.services.jira_client import JiraClient, JiraSyncError

if TYPE_CHECKING:
    from uuid import UUID

    from src.models.jira_integration import JiraIntegration
    from src.models.jira_mapping import JiraMapping
    from src.models.wbs import WBSElement
    from src.repositories.jira_integration import JiraIntegrationRepository
    from src.repositories.jira_mapping import JiraMappingRepository
    from src.repositories.jira_sync_log import JiraSyncLogRepository
    from src.repositories.wbs import WBSElementRepository


logger = structlog.get_logger(__name__)


class WBSSyncError(Exception):
    """Base exception for WBS sync operations."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class IntegrationNotFoundError(WBSSyncError):
    """Jira integration not found."""

    pass


class SyncDisabledError(WBSSyncError):
    """Sync is disabled for this integration."""

    pass


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
class WBSSyncItem:
    """Represents a WBS element to sync with its mapping status."""

    wbs: WBSElement
    mapping: JiraMapping | None
    action: str  # "create", "update", "skip"
    jira_key: str | None = None
    error: str | None = None


class WBSSyncService:
    """
    Service for syncing WBS elements to Jira Epics.

    Handles:
    - WBS level 1-2 → Epic creation
    - Bidirectional updates
    - Conflict resolution (last-write-wins by timestamp)
    - Audit logging for compliance

    Attributes:
        jira_client: Jira API client
        integration_repo: Repository for Jira integrations
        mapping_repo: Repository for entity mappings
        sync_log_repo: Repository for sync audit logs
        wbs_repo: Repository for WBS elements
        max_wbs_level: Maximum WBS level to sync (default 2)
    """

    MAX_WBS_LEVEL = 2  # Only sync levels 1-2 as Epics

    def __init__(
        self,
        jira_client: JiraClient,
        integration_repo: JiraIntegrationRepository,
        mapping_repo: JiraMappingRepository,
        sync_log_repo: JiraSyncLogRepository,
        wbs_repo: WBSElementRepository,
    ) -> None:
        """Initialize WBS sync service.

        Args:
            jira_client: Jira API client instance
            integration_repo: Repository for Jira integrations
            mapping_repo: Repository for entity mappings
            sync_log_repo: Repository for sync audit logs
            wbs_repo: Repository for WBS elements
        """
        self.jira_client = jira_client
        self.integration_repo = integration_repo
        self.mapping_repo = mapping_repo
        self.sync_log_repo = sync_log_repo
        self.wbs_repo = wbs_repo

    async def sync_wbs_to_jira(
        self,
        integration_id: UUID,
        wbs_ids: list[UUID] | None = None,
    ) -> SyncResult:
        """Sync WBS elements to Jira as Epics.

        Creates new Epics for unmapped WBS elements and updates
        existing mappings when WBS data has changed.

        Args:
            integration_id: Jira integration UUID
            wbs_ids: Optional list of specific WBS IDs to sync.
                     If None, syncs all eligible WBS elements.

        Returns:
            SyncResult with sync statistics

        Raises:
            IntegrationNotFoundError: If integration doesn't exist
            SyncDisabledError: If sync is disabled
            WBSSyncError: If sync fails
        """
        start_time = time.time()
        result = SyncResult(success=True, items_synced=0, items_failed=0)

        try:
            # Validate integration
            integration = await self._get_integration(integration_id)

            # Get WBS elements to sync
            wbs_elements = await self._get_syncable_wbs(integration.program_id, wbs_ids)

            if not wbs_elements:
                logger.info(
                    "wbs_sync_no_elements",
                    integration_id=str(integration_id),
                )
                return result

            # Prepare sync items with mapping status
            sync_items = await self._prepare_sync_items(integration_id, wbs_elements)

            # Process each item
            for item in sync_items:
                try:
                    if item.action == "create":
                        new_mapping = await self._create_epic(integration, item.wbs)
                        result.created_mappings.append(new_mapping.id)
                        result.items_synced += 1
                    elif item.action == "update":
                        updated_mapping = await self._update_epic(
                            integration, item.wbs, item.mapping
                        )
                        if updated_mapping:
                            result.updated_mappings.append(updated_mapping.id)
                        result.items_synced += 1
                    # Skip items are not counted
                except JiraSyncError as e:
                    item.error = str(e)
                    result.errors.append(f"WBS {item.wbs.wbs_code}: {e}")
                    result.items_failed += 1
                    logger.warning(
                        "wbs_sync_item_failed",
                        wbs_id=str(item.wbs.id),
                        wbs_code=item.wbs.wbs_code,
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
                "wbs_sync_completed",
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
                "wbs_sync_failed",
                integration_id=str(integration_id),
                error=str(e),
            )
            raise WBSSyncError(f"WBS sync failed: {e}") from e

    async def pull_from_jira(
        self,
        integration_id: UUID,
        mapping_ids: list[UUID] | None = None,
    ) -> SyncResult:
        """Pull updates from Jira Epics to WBS elements.

        Fetches Epic data from Jira and updates corresponding WBS elements
        when Jira has newer changes (conflict resolution: last-write-wins).

        Args:
            integration_id: Jira integration UUID
            mapping_ids: Optional list of specific mapping IDs to pull.
                        If None, pulls all mapped WBS elements.

        Returns:
            SyncResult with sync statistics

        Raises:
            IntegrationNotFoundError: If integration doesn't exist
            SyncDisabledError: If sync is disabled
            WBSSyncError: If pull fails
        """
        start_time = time.time()
        result = SyncResult(success=True, items_synced=0, items_failed=0)

        try:
            integration = await self._get_integration(integration_id)

            # Get mappings to pull
            mappings = await self._get_mappings_for_pull(integration_id, mapping_ids)

            if not mappings:
                logger.info(
                    "wbs_pull_no_mappings",
                    integration_id=str(integration_id),
                )
                return result

            # Process each mapping
            for mapping in mappings:
                try:
                    updated = await self._pull_epic_to_wbs(integration, mapping)
                    if updated:
                        result.updated_mappings.append(mapping.id)
                    result.items_synced += 1
                except JiraSyncError as e:
                    result.errors.append(f"Epic {mapping.jira_issue_key}: {e}")
                    result.items_failed += 1
                    logger.warning(
                        "wbs_pull_item_failed",
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
                "wbs_pull_completed",
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
                "wbs_pull_failed",
                integration_id=str(integration_id),
                error=str(e),
            )
            raise WBSSyncError(f"WBS pull failed: {e}") from e

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

    async def _get_syncable_wbs(
        self,
        program_id: UUID,
        wbs_ids: list[UUID] | None = None,
    ) -> list[WBSElement]:
        """Get WBS elements eligible for sync (levels 1-2)."""
        all_wbs = await self.wbs_repo.get_by_program(program_id)

        # Filter to levels 1-2
        eligible = [w for w in all_wbs if w.level <= self.MAX_WBS_LEVEL]

        # Filter to specific IDs if provided
        if wbs_ids:
            eligible = [w for w in eligible if w.id in wbs_ids]

        return eligible

    async def _prepare_sync_items(
        self,
        integration_id: UUID,
        wbs_elements: list[WBSElement],
    ) -> list[WBSSyncItem]:
        """Prepare sync items with mapping status and action."""
        items = []

        for wbs in wbs_elements:
            mapping = await self.mapping_repo.get_by_wbs(integration_id, wbs.id)

            if mapping is None:
                # New WBS - create Epic
                items.append(WBSSyncItem(wbs=wbs, mapping=None, action="create"))
            elif mapping.sync_direction in (
                SyncDirection.TO_JIRA.value,
                SyncDirection.BIDIRECTIONAL.value,
            ):
                # Existing mapping - update Epic
                items.append(WBSSyncItem(wbs=wbs, mapping=mapping, action="update"))
            else:
                # From Jira only - skip push
                items.append(WBSSyncItem(wbs=wbs, mapping=mapping, action="skip"))

        return items

    async def _create_epic(
        self,
        integration: JiraIntegration,
        wbs: WBSElement,
    ) -> JiraMapping:
        """Create a Jira Epic for a WBS element.

        Args:
            integration: Jira integration config
            wbs: WBS element to create Epic for

        Returns:
            Created JiraMapping
        """
        epic_name = f"{wbs.wbs_code} - {wbs.name}"
        description = self._build_epic_description(wbs)

        # Create Epic in Jira
        epic = await self.jira_client.create_epic(
            project_key=integration.project_key,
            name=epic_name,
            summary=wbs.name,
            description=description,
            labels=["defense-pm-tool", f"wbs-level-{wbs.level}"],
        )

        # Create mapping record
        mapping_data: dict[str, Any] = {
            "integration_id": integration.id,
            "entity_type": EntityType.WBS.value,
            "wbs_id": wbs.id,
            "jira_issue_key": epic.key,
            "jira_issue_id": epic.id,
            "sync_direction": SyncDirection.BIDIRECTIONAL.value,
            "last_synced_at": datetime.now(UTC),
            "last_jira_updated": epic.updated,
        }

        mapping = await self.mapping_repo.create(mapping_data)

        logger.info(
            "wbs_epic_created",
            wbs_id=str(wbs.id),
            wbs_code=wbs.wbs_code,
            epic_key=epic.key,
        )

        return mapping

    async def _update_epic(
        self,
        integration: JiraIntegration,
        wbs: WBSElement,
        mapping: JiraMapping | None,
    ) -> JiraMapping | None:
        """Update existing Jira Epic from WBS data.

        Args:
            integration: Jira integration config
            wbs: WBS element with updated data
            mapping: Existing mapping to update

        Returns:
            Updated JiraMapping or None if no update needed
        """
        if mapping is None:
            return None

        # Build updated fields
        epic_name = f"{wbs.wbs_code} - {wbs.name}"
        description = self._build_epic_description(wbs)

        # Update Epic in Jira
        await self.jira_client.update_issue(
            issue_key=mapping.jira_issue_key,
            summary=wbs.name,
            description=description,
            custom_fields={
                # Epic Name field (may vary by Jira instance)
                integration.epic_custom_field or "customfield_10011": epic_name,
            },
        )

        # Update mapping record
        mapping.last_synced_at = datetime.now(UTC)
        await self.mapping_repo.update(mapping, {"last_synced_at": mapping.last_synced_at})

        logger.info(
            "wbs_epic_updated",
            wbs_id=str(wbs.id),
            wbs_code=wbs.wbs_code,
            epic_key=mapping.jira_issue_key,
        )

        return mapping

    def _build_epic_description(self, wbs: WBSElement) -> str:
        """Build Epic description from WBS element.

        Includes:
        - WBS code and path
        - Budget information if available
        - Control account status
        - Link back to Defense PM Tool
        """
        lines = [
            f"*WBS Element:* {wbs.wbs_code}",
            f"*Path:* {wbs.path}",
            f"*Level:* {wbs.level}",
        ]

        if wbs.description:
            lines.append(f"\n{wbs.description}")

        if wbs.is_control_account:
            lines.append("\n_This is a Control Account for EVMS tracking._")

        if wbs.budget_at_completion and wbs.budget_at_completion > 0:
            lines.append(f"\n*Budget at Completion:* ${wbs.budget_at_completion:,.2f}")

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
            integration_id, entity_type=EntityType.WBS.value
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

    async def _pull_epic_to_wbs(
        self,
        _integration: JiraIntegration,
        mapping: JiraMapping,
    ) -> bool:
        """Pull Epic data from Jira and update WBS if newer.

        Uses last-write-wins conflict resolution based on timestamps.

        Args:
            _integration: Jira integration config (reserved for future use)
            mapping: WBS-Epic mapping

        Returns:
            True if WBS was updated, False if no update needed
        """
        if mapping.wbs_id is None:
            return False

        # Fetch current Epic from Jira
        epic = await self.jira_client.get_issue(mapping.jira_issue_key)

        # Check if Jira has newer changes (conflict resolution)
        if mapping.last_jira_updated and epic.updated <= mapping.last_jira_updated:
            logger.debug(
                "wbs_pull_skipped_no_changes",
                mapping_id=str(mapping.id),
                jira_key=mapping.jira_issue_key,
            )
            return False

        # Get WBS element
        wbs = await self.wbs_repo.get_by_id(mapping.wbs_id)
        if not wbs:
            logger.warning(
                "wbs_pull_wbs_not_found",
                mapping_id=str(mapping.id),
                wbs_id=str(mapping.wbs_id),
            )
            return False

        # Update WBS from Epic (only name/description for now)
        # More fields could be synced based on requirements
        update_data = {"name": epic.summary}

        # Only update description if Epic has one
        if epic.description:
            # Parse description to extract original WBS description
            # (exclude sync metadata)
            desc_lines = epic.description.split("\n")
            original_desc = []
            for line in desc_lines:
                if line.startswith("---") or line.startswith("_Synced from"):
                    break
                if not line.startswith("*WBS Element:*") and not line.startswith("*Path:*"):
                    original_desc.append(line)
            if original_desc:
                update_data["description"] = "\n".join(original_desc).strip()

        await self.wbs_repo.update(wbs, update_data)

        # Update mapping timestamps
        mapping.last_synced_at = datetime.now(UTC)
        mapping.last_jira_updated = epic.updated
        await self.mapping_repo.update(
            mapping,
            {
                "last_synced_at": mapping.last_synced_at,
                "last_jira_updated": mapping.last_jira_updated,
            },
        )

        logger.info(
            "wbs_pulled_from_jira",
            wbs_id=str(wbs.id),
            wbs_code=wbs.wbs_code,
            epic_key=mapping.jira_issue_key,
        )

        return True

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
