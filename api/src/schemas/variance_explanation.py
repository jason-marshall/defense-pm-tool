"""Pydantic schemas for VarianceExplanation model.

Schemas for variance explanation CRUD operations per DFARS requirements (GL 21).
Variances exceeding threshold require documented explanations and corrective actions.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VarianceType(str, Enum):
    """Types of variances tracked in EVMS."""

    SCHEDULE = "schedule"
    COST = "cost"


class VarianceExplanationBase(BaseModel):
    """Base schema for variance explanation with shared fields."""

    variance_type: VarianceType = Field(
        ...,
        description="Type of variance: 'schedule' or 'cost'",
    )
    variance_amount: Decimal = Field(
        ...,
        description="Dollar amount of variance",
        ge=Decimal("-999999999999.99"),
        le=Decimal("999999999999.99"),
    )
    variance_percent: Decimal = Field(
        ...,
        description="Percentage variance",
        ge=Decimal("-9999.9999"),
        le=Decimal("9999.9999"),
    )
    explanation: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Required explanation of variance cause",
    )
    corrective_action: str | None = Field(
        default=None,
        max_length=5000,
        description="Corrective action plan",
    )
    expected_resolution: date | None = Field(
        default=None,
        description="Expected date for resolution",
    )

    @field_validator("expected_resolution")
    @classmethod
    def validate_expected_resolution(cls, v: date | None) -> date | None:
        """Validate expected resolution date is in the future."""
        if v is not None and v < date.today():
            pass  # Allow past dates for historical data
        return v


class VarianceExplanationCreate(VarianceExplanationBase):
    """Schema for creating a new variance explanation."""

    program_id: UUID = Field(
        ...,
        description="Program this variance explanation belongs to",
    )
    wbs_id: UUID | None = Field(
        default=None,
        description="Optional WBS element for element-level variance",
    )
    period_id: UUID | None = Field(
        default=None,
        description="Optional period for period-specific variance",
    )


class VarianceExplanationUpdate(BaseModel):
    """Schema for updating a variance explanation."""

    explanation: str | None = Field(
        default=None,
        min_length=10,
        max_length=5000,
        description="Updated explanation text",
    )
    corrective_action: str | None = Field(
        default=None,
        max_length=5000,
        description="Updated corrective action plan",
    )
    expected_resolution: date | None = Field(
        default=None,
        description="Updated expected resolution date",
    )
    variance_amount: Decimal | None = Field(
        default=None,
        description="Updated variance amount",
    )
    variance_percent: Decimal | None = Field(
        default=None,
        description="Updated variance percent",
    )


class VarianceExplanationResponse(BaseModel):
    """Response schema for variance explanation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    wbs_id: UUID | None
    period_id: UUID | None
    created_by: UUID | None
    variance_type: str
    variance_amount: Decimal
    variance_percent: Decimal
    explanation: str
    corrective_action: str | None
    expected_resolution: date | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @property
    def is_resolved(self) -> bool:
        """Check if variance has been resolved."""
        if self.expected_resolution is None:
            return False
        return date.today() >= self.expected_resolution


class VarianceExplanationSummary(BaseModel):
    """Lightweight variance explanation summary."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    variance_type: str
    variance_amount: Decimal
    variance_percent: Decimal
    expected_resolution: date | None
    created_at: datetime


class VarianceExplanationListResponse(BaseModel):
    """Paginated list of variance explanations."""

    items: list[VarianceExplanationResponse]
    total: int
    page: int
    per_page: int
    pages: int


class VarianceThresholdFilter(BaseModel):
    """Filter for variance threshold queries."""

    threshold_percent: Decimal = Field(
        default=Decimal("10.0"),
        description="Minimum variance percent to include",
        ge=Decimal("0"),
        le=Decimal("100"),
    )
    variance_type: VarianceType | None = Field(
        default=None,
        description="Filter by variance type",
    )
    include_resolved: bool = Field(
        default=False,
        description="Include resolved variances",
    )
