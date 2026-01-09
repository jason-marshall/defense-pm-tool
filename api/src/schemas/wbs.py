"""Pydantic schemas for Work Breakdown Structure (WBS) management.

This module provides schemas for:
- WBS element creation (WBSCreate)
- WBS element updates (WBSUpdate)
- WBS API responses (WBSResponse, WBSTreeResponse)
"""

from datetime import datetime
from decimal import Decimal
from typing import ForwardRef
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WBSBase(BaseModel):
    """
    Base schema with common WBS element fields.

    Provides field definitions shared across Create/Update/Response schemas.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name of the WBS element",
        examples=["Program Management"],
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Detailed description of the WBS element",
        examples=["Overall program management and coordination activities"],
    )


class WBSCreate(WBSBase):
    """
    Schema for creating a new WBS element.

    Supports hierarchical creation with optional parent.
    wbs_code is optional - auto-generated if not provided.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "program_id": "550e8400-e29b-41d4-a716-446655440000",
                "parent_id": None,
                "name": "Program Management",
                "wbs_code": "1.0",
                "description": "Overall program management activities",
                "is_control_account": True,
                "budget_at_completion": "500000.00",
            }
        }
    )

    program_id: UUID = Field(
        ...,
        description="ID of the parent program",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    parent_id: UUID | None = Field(
        default=None,
        description="ID of parent WBS element (null for root elements)",
        examples=["660e8400-e29b-41d4-a716-446655440001"],
    )
    wbs_code: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="WBS code (e.g., '1.2.3'). Auto-generated if not provided.",
        examples=["1.0", "1.1", "1.1.1"],
    )
    is_control_account: bool = Field(
        default=False,
        description="Whether this is an EVMS control account",
        examples=[True, False],
    )
    budget_at_completion: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="Allocated budget (BAC) for this element",
        examples=["500000.00"],
    )

    @field_validator("wbs_code")
    @classmethod
    def validate_wbs_code(cls, v: str | None) -> str | None:
        """Validate WBS code format if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            # WBS codes typically use dots as separators
            # Allow alphanumeric and dots
            valid_chars = set("0123456789.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-")
            if not all(c in valid_chars for c in v):
                raise ValueError("WBS code contains invalid characters")
        return v


class WBSUpdate(BaseModel):
    """
    Schema for updating WBS element details.

    All fields are optional - only provided fields are updated.
    Note: parent_id and program_id cannot be changed after creation.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Program Management Office",
                "description": "Updated PMO description",
                "is_control_account": True,
                "budget_at_completion": "600000.00",
            }
        }
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Display name of the WBS element",
        examples=["Program Management Office"],
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Detailed description",
    )
    is_control_account: bool | None = Field(
        default=None,
        description="Whether this is an EVMS control account",
    )
    budget_at_completion: Decimal | None = Field(
        default=None,
        ge=0,
        description="Allocated budget (BAC)",
    )


class WBSMoveRequest(BaseModel):
    """
    Schema for moving a WBS element to a new parent.

    Moving updates the path and level for the element and all descendants.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "new_parent_id": "770e8400-e29b-41d4-a716-446655440002",
            }
        }
    )

    new_parent_id: UUID | None = Field(
        ...,
        description="ID of new parent element (null to make root)",
        examples=["770e8400-e29b-41d4-a716-446655440002"],
    )


class WBSResponse(BaseModel):
    """
    Schema for WBS element data in API responses.

    Includes all fields plus hierarchy information.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "program_id": "550e8400-e29b-41d4-a716-446655440000",
                "parent_id": None,
                "name": "Program Management",
                "wbs_code": "1.0",
                "description": "Overall program management activities",
                "path": "1_0",
                "level": 1,
                "is_control_account": True,
                "budget_at_completion": "500000.00",
                "created_at": "2026-01-08T12:00:00Z",
                "updated_at": "2026-01-08T12:00:00Z",
            }
        }
    )

    id: UUID = Field(
        ...,
        description="Unique WBS element identifier",
        examples=["660e8400-e29b-41d4-a716-446655440001"],
    )
    program_id: UUID = Field(
        ...,
        description="ID of the parent program",
    )
    parent_id: UUID | None = Field(
        default=None,
        description="ID of parent WBS element",
    )
    name: str = Field(
        ...,
        description="Display name of the WBS element",
        examples=["Program Management"],
    )
    wbs_code: str = Field(
        ...,
        description="WBS code (e.g., '1.2.3')",
        examples=["1.0", "1.1", "1.1.1"],
    )
    description: str | None = Field(
        default=None,
        description="Detailed description",
    )
    path: str = Field(
        ...,
        description="ltree path for hierarchy queries",
        examples=["1_0", "1_0.1", "1_0.1.2"],
    )
    level: int = Field(
        ...,
        ge=1,
        description="Depth in hierarchy (1 = root)",
        examples=[1, 2, 3],
    )
    is_control_account: bool = Field(
        ...,
        description="Whether this is an EVMS control account",
    )
    budget_at_completion: Decimal = Field(
        ...,
        description="Allocated budget (BAC)",
        examples=["500000.00"],
    )
    created_at: datetime = Field(
        ...,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
    )


class WBSBriefResponse(BaseModel):
    """
    Brief WBS response for embedding in other responses.

    Contains only essential identification fields.
    Used when including WBS info in activity responses.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "Program Management",
                "wbs_code": "1.0",
            }
        }
    )

    id: UUID = Field(
        ...,
        description="Unique WBS element identifier",
    )
    name: str = Field(
        ...,
        description="Display name",
    )
    wbs_code: str = Field(
        ...,
        description="WBS code",
    )


class WBSWithChildrenResponse(WBSResponse):
    """
    WBS element response with direct children included.

    Used for flat list with one level of children.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    children: list["WBSBriefResponse"] = Field(
        default_factory=list,
        description="Direct child WBS elements",
    )


class WBSTreeResponse(BaseModel):
    """
    Full hierarchical WBS tree structure.

    Recursively includes all descendants for tree rendering.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "Program Management",
                "wbs_code": "1.0",
                "level": 1,
                "is_control_account": True,
                "budget_at_completion": "500000.00",
                "children": [
                    {
                        "id": "770e8400-e29b-41d4-a716-446655440002",
                        "name": "Planning",
                        "wbs_code": "1.1",
                        "level": 2,
                        "is_control_account": False,
                        "budget_at_completion": "100000.00",
                        "children": [],
                    }
                ],
            }
        }
    )

    id: UUID = Field(
        ...,
        description="Unique WBS element identifier",
    )
    name: str = Field(
        ...,
        description="Display name",
    )
    wbs_code: str = Field(
        ...,
        description="WBS code",
    )
    description: str | None = Field(
        default=None,
        description="Detailed description",
    )
    level: int = Field(
        ...,
        description="Depth in hierarchy",
    )
    is_control_account: bool = Field(
        ...,
        description="Whether this is an EVMS control account",
    )
    budget_at_completion: Decimal = Field(
        ...,
        description="Allocated budget",
    )
    children: list["WBSTreeResponse"] = Field(
        default_factory=list,
        description="Child WBS elements (recursive)",
    )


# Update forward references for recursive types
WBSTreeResponse.model_rebuild()
WBSWithChildrenResponse.model_rebuild()


class WBSSummaryResponse(WBSResponse):
    """
    Extended WBS response with summary statistics.

    Includes activity counts and rollup metrics.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    activity_count: int = Field(
        default=0,
        description="Number of activities in this WBS element",
        examples=[15],
    )
    child_count: int = Field(
        default=0,
        description="Number of direct children",
        examples=[3],
    )
    total_actual_cost: Decimal = Field(
        default=Decimal("0.00"),
        description="Sum of actual costs from activities",
        examples=["125000.00"],
    )
    percent_complete: Decimal = Field(
        default=Decimal("0.00"),
        description="Weighted completion percentage",
        examples=["45.50"],
    )
