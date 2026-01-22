"""Pydantic schemas for Activity and CPM schedule management.

This module provides schemas for:
- Activity creation (ActivityCreate)
- Activity updates (ActivityUpdate)
- Activity API responses (ActivityResponse)
- CPM calculation results (ScheduleResult)
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.core.validation import detect_sql_injection, sanitize_text
from src.models.enums import ConstraintType, EVMethod
from src.schemas.common import PaginatedResponse
from src.schemas.wbs import WBSBriefResponse


class ActivityBase(BaseModel):
    """
    Base schema with common activity fields.

    Provides field definitions shared across Create/Update/Response schemas.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Activity name/description",
        examples=["Design Review Meeting"],
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Detailed description of the activity",
        examples=["Conduct preliminary design review with stakeholders"],
    )


class ActivityCreate(ActivityBase):
    """
    Schema for creating a new activity.

    Validates milestone/duration consistency:
    - Milestones must have duration=0
    - Non-milestones must have duration >= 0

    Constraint dates are required for certain constraint types.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "program_id": "550e8400-e29b-41d4-a716-446655440000",
                "wbs_id": "660e8400-e29b-41d4-a716-446655440001",
                "code": "A001",
                "name": "Design Review Meeting",
                "description": "Conduct preliminary design review",
                "duration": 5,
                "is_milestone": False,
                "constraint_type": "asap",
                "constraint_date": None,
                "budgeted_cost": "25000.00",
            }
        }
    )

    program_id: UUID = Field(
        ...,
        description="ID of the parent program",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    wbs_id: UUID = Field(
        ...,
        description="ID of the parent WBS element",
        examples=["660e8400-e29b-41d4-a716-446655440001"],
    )
    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Unique activity code within program (auto-generated if not provided)",
        examples=["A001", "TASK-100"],
    )
    duration: int = Field(
        default=0,
        ge=0,
        description="Duration in working days (0 for milestones)",
        examples=[5, 10, 0],
    )
    is_milestone: bool = Field(
        default=False,
        description="Whether this is a milestone (duration forced to 0)",
        examples=[True, False],
    )
    constraint_type: ConstraintType = Field(
        default=ConstraintType.ASAP,
        description="Scheduling constraint type",
        examples=["asap", "snet", "fnlt"],
    )
    constraint_date: date | None = Field(
        default=None,
        description="Date for constraint (required for SNET, SNLT, FNET, FNLT)",
        examples=["2026-03-15"],
    )
    planned_start: date | None = Field(
        default=None,
        description="Baseline planned start date",
        examples=["2026-02-01"],
    )
    planned_finish: date | None = Field(
        default=None,
        description="Baseline planned finish date",
        examples=["2026-02-05"],
    )
    budgeted_cost: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="Budgeted cost (BCWS at completion)",
        examples=["25000.00"],
    )
    ev_method: EVMethod = Field(
        default=EVMethod.PERCENT_COMPLETE,
        description="Earned value calculation method",
        examples=["percent_complete", "0/100", "50/50", "loe"],
    )
    milestones_json: list[dict[str, object]] | None = Field(
        default=None,
        description="Milestones for milestone-weight EV method",
        examples=[[{"name": "Design", "weight": 0.25, "is_complete": False}]],
    )

    @field_validator("name", "description", mode="after")
    @classmethod
    def sanitize_text_fields(cls, v: str | None) -> str | None:
        """Sanitize text fields to prevent XSS and SQL injection."""
        if v is None:
            return None
        v = sanitize_text(v)
        if v and detect_sql_injection(v):
            raise ValueError("Invalid characters detected in input")
        return v

    @field_validator("code", mode="after")
    @classmethod
    def validate_code_format(cls, v: str | None) -> str | None:
        """Validate and sanitize code field."""
        if v is None:
            return None
        v = sanitize_text(v) or ""
        if not v:
            return None
        if not all(c.isalnum() or c in "_-." for c in v):
            raise ValueError(
                "Code must contain only letters, numbers, underscores, hyphens, and periods"
            )
        return v.upper()

    @model_validator(mode="after")
    def validate_milestone_duration(self) -> "ActivityCreate":
        """
        Force duration to 0 for milestones.

        Milestones are zero-duration events marking key project points.
        """
        if self.is_milestone:
            self.duration = 0
        return self

    @model_validator(mode="after")
    def validate_constraint_date(self) -> "ActivityCreate":
        """
        Validate constraint_date is provided for date-based constraints.

        SNET, SNLT, FNET, FNLT require a constraint date.
        ASAP and ALAP do not use constraint_date.
        """
        requires_date = self.constraint_type in (
            ConstraintType.SNET,
            ConstraintType.SNLT,
            ConstraintType.FNET,
            ConstraintType.FNLT,
        )
        if requires_date and self.constraint_date is None:
            raise ValueError(
                f"constraint_date is required for constraint type {self.constraint_type.value}"
            )
        return self


class ActivityUpdate(BaseModel):
    """
    Schema for updating activity details.

    All fields are optional - only provided fields are updated.
    Validates duration >= 0 and milestone/duration consistency.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Design Review Meeting - Updated",
                "duration": 7,
                "percent_complete": "50.00",
                "actual_start": "2026-02-01",
            }
        }
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Activity name",
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Detailed description",
    )
    duration: int | None = Field(
        default=None,
        ge=0,
        description="Duration in working days",
    )
    is_milestone: bool | None = Field(
        default=None,
        description="Whether this is a milestone",
    )
    constraint_type: ConstraintType | None = Field(
        default=None,
        description="Scheduling constraint type",
    )
    constraint_date: date | None = Field(
        default=None,
        description="Date for constraint",
    )
    planned_start: date | None = Field(
        default=None,
        description="Baseline planned start date",
    )
    planned_finish: date | None = Field(
        default=None,
        description="Baseline planned finish date",
    )
    actual_start: date | None = Field(
        default=None,
        description="Actual start date",
    )
    actual_finish: date | None = Field(
        default=None,
        description="Actual finish date",
    )
    percent_complete: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Progress percentage (0-100)",
    )
    budgeted_cost: Decimal | None = Field(
        default=None,
        ge=0,
        description="Budgeted cost",
    )
    actual_cost: Decimal | None = Field(
        default=None,
        ge=0,
        description="Actual cost incurred",
    )
    ev_method: EVMethod | None = Field(
        default=None,
        description="Earned value calculation method",
    )
    milestones_json: list[dict[str, object]] | None = Field(
        default=None,
        description="Milestones for milestone-weight EV method",
    )

    @field_validator("name", "description", mode="after")
    @classmethod
    def sanitize_text_fields(cls, v: str | None) -> str | None:
        """Sanitize text fields to prevent XSS and SQL injection."""
        if v is None:
            return None
        v = sanitize_text(v)
        if v and detect_sql_injection(v):
            raise ValueError("Invalid characters detected in input")
        return v

    @model_validator(mode="after")
    def validate_milestone_duration(self) -> "ActivityUpdate":
        """Force duration to 0 if is_milestone is set to True."""
        if self.is_milestone is True:
            self.duration = 0
        return self

    @field_validator("percent_complete")
    @classmethod
    def validate_percent_complete(cls, v: Decimal | None) -> Decimal | None:
        """Ensure percent_complete is between 0 and 100."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError("percent_complete must be between 0 and 100")
        return v


class ActivityProgressUpdate(BaseModel):
    """
    Schema for updating activity progress only.

    Simplified schema for status updates during execution.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "percent_complete": "75.00",
                "actual_start": "2026-02-01",
                "actual_cost": "18500.00",
            }
        }
    )

    percent_complete: Decimal = Field(
        ...,
        ge=0,
        le=100,
        description="Progress percentage (0-100)",
        examples=["75.00"],
    )
    actual_start: date | None = Field(
        default=None,
        description="Actual start date (set when work begins)",
    )
    actual_finish: date | None = Field(
        default=None,
        description="Actual finish date (set when complete)",
    )
    actual_cost: Decimal | None = Field(
        default=None,
        ge=0,
        description="Actual cost incurred to date",
    )


class ScheduleResult(BaseModel):
    """
    Schema for CPM schedule calculation results.

    Contains the calculated dates and float values
    from forward and backward pass calculations.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "activity_id": "770e8400-e29b-41d4-a716-446655440003",
                "early_start": 0,
                "early_finish": 5,
                "late_start": 2,
                "late_finish": 7,
                "total_float": 2,
                "free_float": 0,
                "is_critical": False,
            }
        }
    )

    activity_id: UUID = Field(
        ...,
        description="ID of the activity",
    )
    early_start: int = Field(
        ...,
        description="Early start (days from project start)",
        examples=[0, 5, 10],
    )
    early_finish: int = Field(
        ...,
        description="Early finish (days from project start)",
        examples=[5, 10, 15],
    )
    late_start: int = Field(
        ...,
        description="Late start (days from project start)",
        examples=[2, 7, 12],
    )
    late_finish: int = Field(
        ...,
        description="Late finish (days from project start)",
        examples=[7, 12, 17],
    )
    total_float: int = Field(
        ...,
        description="Total float in days (LS - ES)",
        examples=[0, 2, 5],
    )
    free_float: int = Field(
        ...,
        description="Free float in days",
        examples=[0, 1, 3],
    )
    is_critical: bool = Field(
        ...,
        description="True if on critical path (total_float = 0)",
        examples=[True, False],
    )


class ActivityResponse(BaseModel):
    """
    Schema for activity data in API responses.

    Includes all activity fields plus calculated CPM dates
    and nested WBS element information.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440003",
                "program_id": "550e8400-e29b-41d4-a716-446655440000",
                "wbs_id": "660e8400-e29b-41d4-a716-446655440001",
                "code": "A001",
                "name": "Design Review Meeting",
                "description": "Conduct preliminary design review",
                "duration": 5,
                "is_milestone": False,
                "constraint_type": "asap",
                "constraint_date": None,
                "planned_start": "2026-02-01",
                "planned_finish": "2026-02-05",
                "actual_start": "2026-02-01",
                "actual_finish": None,
                "early_start": "2026-02-01",
                "early_finish": "2026-02-05",
                "late_start": "2026-02-03",
                "late_finish": "2026-02-07",
                "total_float": 2,
                "free_float": 0,
                "is_critical": False,
                "percent_complete": "50.00",
                "budgeted_cost": "25000.00",
                "actual_cost": "12500.00",
                "created_at": "2026-01-08T12:00:00Z",
                "updated_at": "2026-01-08T12:00:00Z",
            }
        },
    )

    id: UUID = Field(
        ...,
        description="Unique activity identifier",
        examples=["770e8400-e29b-41d4-a716-446655440003"],
    )
    program_id: UUID = Field(
        ...,
        description="ID of the parent program",
    )
    wbs_id: UUID = Field(
        ...,
        description="ID of the parent WBS element",
    )
    code: str = Field(
        ...,
        description="Unique activity code within program",
        examples=["A001"],
    )
    wbs_element: WBSBriefResponse | None = Field(
        default=None,
        description="Parent WBS element details",
    )
    name: str = Field(
        ...,
        description="Activity name",
        examples=["Design Review Meeting"],
    )
    description: str | None = Field(
        default=None,
        description="Detailed description",
    )
    duration: int = Field(
        ...,
        description="Duration in working days",
        examples=[5],
    )
    is_milestone: bool = Field(
        ...,
        description="Whether this is a milestone",
    )
    constraint_type: ConstraintType = Field(
        ...,
        description="Scheduling constraint type",
    )
    constraint_date: date | None = Field(
        default=None,
        description="Date for constraint",
    )
    # Planned dates (baseline)
    planned_start: date | None = Field(
        default=None,
        description="Baseline planned start date",
    )
    planned_finish: date | None = Field(
        default=None,
        description="Baseline planned finish date",
    )
    # Actual dates (execution)
    actual_start: date | None = Field(
        default=None,
        description="Actual start date",
    )
    actual_finish: date | None = Field(
        default=None,
        description="Actual finish date",
    )
    # CPM calculated dates (forward pass)
    early_start: date | None = Field(
        default=None,
        description="Early start from CPM forward pass",
    )
    early_finish: date | None = Field(
        default=None,
        description="Early finish from CPM forward pass",
    )
    # CPM calculated dates (backward pass)
    late_start: date | None = Field(
        default=None,
        description="Late start from CPM backward pass",
    )
    late_finish: date | None = Field(
        default=None,
        description="Late finish from CPM backward pass",
    )
    # Float values
    total_float: int | None = Field(
        default=None,
        description="Total float in days (LS - ES)",
    )
    free_float: int | None = Field(
        default=None,
        description="Free float in days",
    )
    # Critical path flag
    is_critical: bool = Field(
        default=False,
        description="True if on critical path",
    )
    # Progress and cost
    percent_complete: Decimal = Field(
        default=Decimal("0.00"),
        description="Progress percentage (0-100)",
    )
    budgeted_cost: Decimal = Field(
        default=Decimal("0.00"),
        description="Budgeted cost (BCWS at completion)",
    )
    actual_cost: Decimal = Field(
        default=Decimal("0.00"),
        description="Actual cost incurred (ACWP)",
    )
    # EV Method configuration
    ev_method: str = Field(
        default=EVMethod.PERCENT_COMPLETE.value,
        description="Earned value calculation method",
    )
    milestones_json: list[dict[str, object]] | None = Field(
        default=None,
        description="Milestones for milestone-weight EV method",
    )
    # Timestamps
    created_at: datetime = Field(
        ...,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
    )

    @property
    def earned_value(self) -> Decimal:
        """Calculate earned value (BCWP) based on percent complete."""
        return self.budgeted_cost * self.percent_complete / Decimal("100.00")

    @property
    def is_started(self) -> bool:
        """Check if activity has started."""
        return self.actual_start is not None

    @property
    def is_completed(self) -> bool:
        """Check if activity is completed."""
        return self.percent_complete >= Decimal("100.00") or self.actual_finish is not None

    @property
    def is_in_progress(self) -> bool:
        """Check if activity is in progress."""
        return self.is_started and not self.is_completed


class ActivityBriefResponse(BaseModel):
    """
    Brief activity response for embedding in other responses.

    Contains only essential identification fields.
    Used in dependency responses.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440003",
                "code": "A001",
                "name": "Design Review Meeting",
                "is_milestone": False,
                "is_critical": False,
            }
        },
    )

    id: UUID = Field(
        ...,
        description="Unique activity identifier",
    )
    code: str = Field(
        ...,
        description="Unique activity code within program",
    )
    name: str = Field(
        ...,
        description="Activity name",
    )
    is_milestone: bool = Field(
        ...,
        description="Whether this is a milestone",
    )
    is_critical: bool = Field(
        default=False,
        description="True if on critical path",
    )


class CriticalPathResponse(BaseModel):
    """
    Schema for critical path analysis results.

    Returns the list of activities on the critical path
    and overall project duration.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_duration": 120,
                "critical_activities": [
                    {
                        "id": "770e8400-e29b-41d4-a716-446655440003",
                        "code": "A001",
                        "name": "Design Review",
                        "is_milestone": False,
                        "is_critical": True,
                    }
                ],
                "total_activities": 50,
                "critical_count": 12,
            }
        }
    )

    project_duration: int = Field(
        ...,
        description="Total project duration in working days",
        examples=[120],
    )
    critical_activities: list[ActivityBriefResponse] = Field(
        ...,
        description="Activities on the critical path",
    )
    total_activities: int = Field(
        ...,
        description="Total number of activities",
        examples=[50],
    )
    critical_count: int = Field(
        ...,
        description="Number of critical activities",
        examples=[12],
    )


# Type alias for paginated activity lists
ActivityListResponse = PaginatedResponse[ActivityResponse]
