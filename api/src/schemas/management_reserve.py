"""Pydantic schemas for Management Reserve tracking.

Schemas for MR change logging per EVMS Guideline 28.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ManagementReserveBase(BaseModel):
    """Base schema for Management Reserve data."""

    reason: str | None = Field(
        default=None,
        max_length=1000,
        description="Explanation for MR changes",
    )


class ManagementReserveChangeCreate(ManagementReserveBase):
    """Schema for recording an MR change."""

    period_id: UUID | None = Field(
        default=None,
        description="Period when this change occurred",
    )
    changes_in: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Amount added to MR",
    )
    changes_out: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Amount released from MR to work packages",
    )


class ManagementReserveLogResponse(BaseModel):
    """Response schema for an MR log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    period_id: UUID | None
    beginning_mr: Decimal
    changes_in: Decimal
    changes_out: Decimal
    ending_mr: Decimal
    reason: str | None
    approved_by: UUID | None
    created_at: datetime


class ManagementReserveLogSummary(BaseModel):
    """Lightweight summary for MR listing."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    period_id: UUID | None
    beginning_mr: Decimal
    ending_mr: Decimal
    net_change: Decimal = Field(description="changes_in - changes_out")
    created_at: datetime


class ManagementReserveStatus(BaseModel):
    """Current MR status for a program."""

    program_id: UUID
    current_balance: Decimal = Field(description="Current MR balance")
    initial_mr: Decimal = Field(description="Initial MR amount")
    total_changes_in: Decimal = Field(description="Total added to MR")
    total_changes_out: Decimal = Field(description="Total released from MR")
    change_count: int = Field(description="Number of MR changes recorded")
    last_change_at: datetime | None = Field(
        default=None,
        description="Timestamp of most recent MR change",
    )


class ManagementReserveHistoryResponse(BaseModel):
    """Response schema for MR history."""

    items: list[ManagementReserveLogResponse]
    total: int
    program_id: UUID
    current_balance: Decimal
