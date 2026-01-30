"""Pydantic schemas for resource pools and cross-program availability."""

from __future__ import annotations

from datetime import date, datetime  # noqa: TC003 - Required at runtime for Pydantic
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID  # noqa: TC003 - Required at runtime for Pydantic

from pydantic import BaseModel, ConfigDict, Field

from src.models.resource_pool import PoolAccessLevel

# =============================================================================
# Resource Pool Schemas
# =============================================================================


class ResourcePoolCreate(BaseModel):
    """Schema for creating a resource pool."""

    name: Annotated[str, Field(min_length=1, max_length=100, description="Pool name")]
    code: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            pattern=r"^[A-Z0-9\-_]+$",
            description="Unique pool code",
        ),
    ]
    description: str | None = Field(default=None, description="Pool description")


class ResourcePoolUpdate(BaseModel):
    """Schema for updating a resource pool."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class ResourcePoolResponse(BaseModel):
    """Response schema for a resource pool."""

    id: UUID
    name: str
    code: str
    description: str | None
    owner_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Pool Member Schemas
# =============================================================================


class PoolMemberCreate(BaseModel):
    """Schema for adding a resource to a pool."""

    resource_id: UUID = Field(..., description="Resource to add to pool")
    allocation_percentage: Annotated[
        Decimal,
        Field(
            default=Decimal("100.00"),
            ge=Decimal("0"),
            le=Decimal("100"),
            description="Percentage of resource available to pool (0-100)",
        ),
    ] = Decimal("100.00")


class PoolMemberResponse(BaseModel):
    """Response schema for a pool member."""

    id: UUID
    pool_id: UUID
    resource_id: UUID
    allocation_percentage: Decimal
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Pool Access Schemas
# =============================================================================


class PoolAccessCreate(BaseModel):
    """Schema for granting pool access to a program."""

    program_id: UUID = Field(..., description="Program to grant access")
    access_level: PoolAccessLevel = Field(
        default=PoolAccessLevel.VIEWER,
        description="Access level for the program",
    )


class PoolAccessResponse(BaseModel):
    """Response schema for pool access grant."""

    id: UUID
    pool_id: UUID
    program_id: UUID
    access_level: PoolAccessLevel
    granted_by: UUID | None
    granted_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Availability Schemas
# =============================================================================


class PoolAvailabilityResponse(BaseModel):
    """Response schema for pool availability check."""

    pool_id: UUID
    pool_name: str
    date_range_start: date
    date_range_end: date
    resources: list[dict[str, Any]]
    conflict_count: int
    conflicts: list[dict[str, Any]]


class ConflictCheckRequest(BaseModel):
    """Request schema for checking assignment conflicts."""

    resource_id: UUID = Field(..., description="Resource to check")
    program_id: UUID = Field(..., description="Program making the assignment")
    start_date: date = Field(..., description="Assignment start date")
    end_date: date = Field(..., description="Assignment end date")
    units: Annotated[
        Decimal,
        Field(
            default=Decimal("1.00"),
            ge=Decimal("0"),
            le=Decimal("10"),
            description="Allocation units",
        ),
    ] = Decimal("1.00")


class ConflictCheckResponse(BaseModel):
    """Response schema for conflict check."""

    has_conflicts: bool
    conflict_count: int
    conflicts: list[dict[str, Any]]
