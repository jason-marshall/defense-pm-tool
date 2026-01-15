"""Pydantic schemas for Scenario model."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScenarioStatus(str, Enum):
    """Status values for scenarios."""

    DRAFT = "draft"
    ACTIVE = "active"
    PROMOTED = "promoted"
    ARCHIVED = "archived"


class ChangeType(str, Enum):
    """Types of changes in a scenario."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class EntityType(str, Enum):
    """Entity types that can be changed in a scenario."""

    ACTIVITY = "activity"
    DEPENDENCY = "dependency"
    WBS = "wbs"


class ScenarioBase(BaseModel):
    """Base schema for Scenario with shared fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Scenario name")
    description: str | None = Field(
        default=None, max_length=5000, description="Scenario description"
    )


class ScenarioCreate(ScenarioBase):
    """Schema for creating a new scenario."""

    program_id: UUID = Field(..., description="Program ID")
    baseline_id: UUID | None = Field(default=None, description="Reference baseline ID (optional)")
    parent_scenario_id: UUID | None = Field(
        default=None, description="Parent scenario ID for branching (optional)"
    )


class ScenarioUpdate(BaseModel):
    """Schema for updating scenario metadata."""

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Updated name")
    description: str | None = Field(
        default=None, max_length=5000, description="Updated description"
    )
    status: ScenarioStatus | None = Field(default=None, description="Updated status")
    is_active: bool | None = Field(default=None, description="Updated active flag")


class ScenarioChangeCreate(BaseModel):
    """Schema for creating a change within a scenario."""

    entity_type: EntityType = Field(..., description="Entity type")
    entity_id: UUID = Field(..., description="Entity ID being changed")
    entity_code: str | None = Field(
        default=None, max_length=100, description="Entity code for display"
    )
    change_type: ChangeType = Field(..., description="Type of change")
    field_name: str | None = Field(
        default=None, max_length=100, description="Field being changed (for updates)"
    )
    old_value: Any | None = Field(default=None, description="Previous value")
    new_value: Any | None = Field(default=None, description="New value")


class ScenarioChangeResponse(BaseModel):
    """Schema for scenario change response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scenario_id: UUID
    entity_type: str
    entity_id: UUID
    entity_code: str | None
    change_type: str
    field_name: str | None
    old_value: Any | None
    new_value: Any | None
    created_at: datetime


class ScenarioSummary(BaseModel):
    """Lightweight scenario response without change details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    baseline_id: UUID | None
    parent_scenario_id: UUID | None
    name: str
    description: str | None
    status: str
    is_active: bool
    change_count: int = Field(default=0, description="Number of changes")
    has_cached_results: bool = Field(default=False)
    created_at: datetime
    created_by_id: UUID
    promoted_at: datetime | None
    promoted_baseline_id: UUID | None


class ScenarioResponse(ScenarioSummary):
    """Full scenario response with change details."""

    changes: list[ScenarioChangeResponse] = Field(
        default_factory=list, description="List of changes in this scenario"
    )
    results_cache: dict[str, Any] | None = Field(default=None, description="Cached CPM results")
    updated_at: datetime | None = None


class ScenarioListResponse(BaseModel):
    """Paginated list of scenarios."""

    items: list[ScenarioSummary]
    total: int
    page: int
    per_page: int
    pages: int


class ScenarioPromoteRequest(BaseModel):
    """Request to promote scenario to baseline."""

    baseline_name: str = Field(
        ..., min_length=1, max_length=255, description="Name for new baseline"
    )
    baseline_description: str | None = Field(
        default=None, max_length=5000, description="Description for new baseline"
    )


class ScenarioApplyChangesRequest(BaseModel):
    """Request to apply scenario changes to actual program data."""

    confirm: bool = Field(default=False, description="Confirm applying changes (required)")


class ScenarioCPMResult(BaseModel):
    """CPM calculation results for a scenario."""

    scenario_id: UUID
    calculated_at: datetime
    project_duration: int | None
    project_finish: str | None  # ISO date string
    critical_path_count: int
    critical_path_ids: list[UUID]
    activity_results: dict[str, Any] = Field(
        default_factory=dict, description="CPM results by activity ID"
    )


class ScenarioDiffSummary(BaseModel):
    """Summary of differences between scenario and current state."""

    scenario_id: UUID
    scenario_name: str

    # Activity changes
    activities_created: int = 0
    activities_updated: int = 0
    activities_deleted: int = 0

    # Dependency changes
    dependencies_created: int = 0
    dependencies_updated: int = 0
    dependencies_deleted: int = 0

    # WBS changes
    wbs_created: int = 0
    wbs_updated: int = 0
    wbs_deleted: int = 0

    # Impact summary
    total_changes: int = 0
    schedule_impact_days: int | None = None
    cost_impact: str | None = None  # Decimal as string
