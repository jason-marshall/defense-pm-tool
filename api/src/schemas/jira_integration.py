"""Pydantic schemas for Jira integration API."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SyncDirection(str, Enum):
    """Sync direction for mappings."""

    TO_JIRA = "to_jira"
    FROM_JIRA = "from_jira"
    BIDIRECTIONAL = "bidirectional"


class EntityType(str, Enum):
    """Type of mapped entity."""

    WBS = "wbs"
    ACTIVITY = "activity"


class SyncType(str, Enum):
    """Type of sync operation."""

    PUSH = "push"
    PULL = "pull"
    WEBHOOK = "webhook"
    FULL = "full"


class SyncStatus(str, Enum):
    """Status of sync operation."""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


# Integration schemas


class JiraIntegrationCreate(BaseModel):
    """Schema for creating a Jira integration connection."""

    program_id: UUID = Field(..., description="Program ID to connect")
    jira_url: HttpUrl = Field(
        ..., description="Jira Cloud URL (e.g., https://company.atlassian.net)"
    )
    project_key: str = Field(
        ..., min_length=1, max_length=20, description="Target Jira project key"
    )
    email: str = Field(..., description="User email for Jira authentication")
    api_token: str = Field(..., description="Jira API token (will be encrypted)")
    epic_custom_field: str | None = Field(default=None, description="Custom field ID for Epic Name")


class JiraIntegrationUpdate(BaseModel):
    """Schema for updating Jira integration settings."""

    sync_enabled: bool | None = Field(default=None, description="Enable/disable sync")
    epic_custom_field: str | None = Field(default=None, description="Custom field ID for Epic Name")


class JiraIntegrationResponse(BaseModel):
    """Response schema for Jira integration."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    jira_url: str
    project_key: str
    email: str
    sync_enabled: bool
    sync_status: str
    last_sync_at: datetime | None
    epic_custom_field: str | None
    created_at: datetime
    updated_at: datetime | None


# Mapping schemas


class JiraMappingCreate(BaseModel):
    """Schema for creating a manual mapping."""

    entity_type: EntityType = Field(..., description="Type of entity to map")
    wbs_id: UUID | None = Field(default=None, description="WBS element ID (if type is wbs)")
    activity_id: UUID | None = Field(default=None, description="Activity ID (if type is activity)")
    jira_issue_key: str = Field(..., description="Jira issue key (e.g., PROJ-123)")
    sync_direction: SyncDirection = Field(
        default=SyncDirection.BIDIRECTIONAL, description="Sync direction"
    )


class JiraMappingResponse(BaseModel):
    """Response schema for Jira mapping."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    integration_id: UUID
    entity_type: str
    wbs_id: UUID | None
    activity_id: UUID | None
    jira_issue_key: str
    jira_issue_id: str | None
    sync_direction: str
    last_synced_at: datetime | None
    last_jira_updated: datetime | None
    created_at: datetime


class JiraMappingBrief(BaseModel):
    """Brief mapping info for list responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    jira_issue_key: str
    last_synced_at: datetime | None


# Sync request/response schemas


class JiraSyncRequest(BaseModel):
    """Request schema for triggering a sync operation."""

    entity_type: EntityType | None = Field(
        default=None, description="Limit sync to entity type (wbs or activity)"
    )
    entity_ids: list[UUID] | None = Field(
        default=None, description="Specific entity IDs to sync (if not provided, syncs all)"
    )
    sync_direction: SyncDirection = Field(
        default=SyncDirection.TO_JIRA, description="Direction of sync"
    )
    include_progress: bool = Field(
        default=True, description="Include progress/status sync for activities"
    )


class SyncResultItem(BaseModel):
    """Individual item sync result."""

    entity_id: UUID
    entity_type: str
    jira_issue_key: str | None
    success: bool
    error_message: str | None = None


class JiraSyncResponse(BaseModel):
    """Response schema for sync operation."""

    success: bool
    sync_type: str
    items_synced: int
    items_failed: int
    duration_ms: int
    errors: list[str] = Field(default_factory=list)
    results: list[SyncResultItem] = Field(default_factory=list)


# Sync log schemas


class JiraSyncLogResponse(BaseModel):
    """Response schema for sync log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    integration_id: UUID
    mapping_id: UUID | None
    sync_type: str
    status: str
    items_synced: int
    error_message: str | None
    duration_ms: int | None
    created_at: datetime


class JiraSyncLogListResponse(BaseModel):
    """Paginated list of sync logs."""

    items: list[JiraSyncLogResponse]
    total: int
    page: int
    per_page: int


# Progress sync schemas


class ActivityProgressSyncRequest(BaseModel):
    """Request schema for syncing activity progress to Jira."""

    activity_ids: list[UUID] | None = Field(
        default=None, description="Specific activity IDs (if not provided, syncs all mapped)"
    )


class ActivityProgressSyncResult(BaseModel):
    """Result of activity progress sync."""

    activity_id: UUID
    activity_code: str
    jira_issue_key: str
    percent_complete: Decimal
    jira_status: str
    success: bool
    message: str | None = None


class ActivityProgressSyncResponse(BaseModel):
    """Response for progress sync operation."""

    success: bool
    synced_count: int
    failed_count: int
    results: list[ActivityProgressSyncResult]


# Status mapping schemas


class JiraStatusMapping(BaseModel):
    """Mapping between percent complete and Jira status."""

    min_percent: Decimal = Field(..., ge=0, le=100)
    max_percent: Decimal = Field(..., ge=0, le=100)
    jira_status: str
    jira_transition_id: str | None = None


class JiraStatusMappingConfig(BaseModel):
    """Configuration for Jira status mappings."""

    mappings: list[JiraStatusMapping] = Field(
        default_factory=lambda: [
            JiraStatusMapping(
                min_percent=Decimal("0"),
                max_percent=Decimal("0"),
                jira_status="To Do",
            ),
            JiraStatusMapping(
                min_percent=Decimal("1"),
                max_percent=Decimal("99"),
                jira_status="In Progress",
            ),
            JiraStatusMapping(
                min_percent=Decimal("100"),
                max_percent=Decimal("100"),
                jira_status="Done",
            ),
        ]
    )


# Webhook schemas


class JiraWebhookPayload(BaseModel):
    """Schema for Jira webhook payload."""

    webhookEvent: str
    issue: dict[str, Any] | None = None
    changelog: dict[str, Any] | None = None
    user: dict[str, Any] | None = None
    timestamp: int | None = None


# Connection test


class JiraConnectionTestResponse(BaseModel):
    """Response for connection test."""

    success: bool
    message: str
    project_name: str | None = None
    issue_types: list[str] | None = None
