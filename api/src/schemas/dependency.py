"""Pydantic schemas for Activity Dependency management.

This module provides schemas for:
- Dependency creation (DependencyCreate)
- Dependency updates (DependencyUpdate)
- Dependency API responses (DependencyResponse)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.models.dependency import DependencyType
from src.schemas.activity import ActivityBriefResponse


class DependencyBase(BaseModel):
    """
    Base schema with common dependency fields.

    Provides field definitions shared across Create/Update/Response schemas.
    """

    dependency_type: DependencyType = Field(
        default=DependencyType.FS,
        description="Type of dependency relationship",
        examples=["FS", "SS", "FF", "SF"],
    )
    lag_days: int = Field(
        default=0,
        description="Lag (positive) or lead (negative) in working days",
        examples=[0, 2, -1],
    )


class DependencyCreate(DependencyBase):
    """
    Schema for creating a new dependency.

    Validates that predecessor and successor are different activities.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "predecessor_id": "770e8400-e29b-41d4-a716-446655440003",
                "successor_id": "880e8400-e29b-41d4-a716-446655440004",
                "dependency_type": "FS",
                "lag_days": 0,
            }
        }
    )

    predecessor_id: UUID = Field(
        ...,
        description="ID of the predecessor activity",
        examples=["770e8400-e29b-41d4-a716-446655440003"],
    )
    successor_id: UUID = Field(
        ...,
        description="ID of the successor activity",
        examples=["880e8400-e29b-41d4-a716-446655440004"],
    )

    @model_validator(mode="after")
    def validate_different_activities(self) -> "DependencyCreate":
        """
        Validate that predecessor and successor are different activities.

        An activity cannot depend on itself - this would create an
        immediate circular dependency.
        """
        if self.predecessor_id == self.successor_id:
            raise ValueError("An activity cannot depend on itself")
        return self


class DependencyUpdate(BaseModel):
    """
    Schema for updating dependency details.

    Only dependency_type and lag_days can be updated.
    Predecessor/successor cannot be changed - delete and recreate instead.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dependency_type": "SS",
                "lag_days": 2,
            }
        }
    )

    dependency_type: DependencyType | None = Field(
        default=None,
        description="Type of dependency relationship",
        examples=["FS", "SS", "FF", "SF"],
    )
    lag_days: int | None = Field(
        default=None,
        description="Lag (positive) or lead (negative) in working days",
        examples=[0, 2, -1],
    )


class DependencyResponse(BaseModel):
    """
    Schema for dependency data in API responses.

    Includes predecessor and successor activity names
    for display purposes.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "990e8400-e29b-41d4-a716-446655440005",
                "predecessor_id": "770e8400-e29b-41d4-a716-446655440003",
                "successor_id": "880e8400-e29b-41d4-a716-446655440004",
                "dependency_type": "FS",
                "lag_days": 0,
                "predecessor": {
                    "id": "770e8400-e29b-41d4-a716-446655440003",
                    "name": "Design Review Meeting",
                    "is_milestone": False,
                    "is_critical": True,
                },
                "successor": {
                    "id": "880e8400-e29b-41d4-a716-446655440004",
                    "name": "Implementation Phase",
                    "is_milestone": False,
                    "is_critical": True,
                },
                "created_at": "2026-01-08T12:00:00Z",
                "updated_at": "2026-01-08T12:00:00Z",
            }
        }
    )

    id: UUID = Field(
        ...,
        description="Unique dependency identifier",
        examples=["990e8400-e29b-41d4-a716-446655440005"],
    )
    predecessor_id: UUID = Field(
        ...,
        description="ID of the predecessor activity",
    )
    successor_id: UUID = Field(
        ...,
        description="ID of the successor activity",
    )
    dependency_type: DependencyType = Field(
        ...,
        description="Type of dependency relationship",
        examples=["FS", "SS", "FF", "SF"],
    )
    lag_days: int = Field(
        ...,
        description="Lag (positive) or lead (negative) in working days",
    )
    # Nested activity information
    predecessor: ActivityBriefResponse | None = Field(
        default=None,
        description="Predecessor activity details",
    )
    successor: ActivityBriefResponse | None = Field(
        default=None,
        description="Successor activity details",
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
    def has_lag(self) -> bool:
        """Check if dependency has non-zero lag."""
        return self.lag_days != 0

    @property
    def has_lead(self) -> bool:
        """Check if dependency has lead time (negative lag)."""
        return self.lag_days < 0

    @property
    def dependency_description(self) -> str:
        """Get human-readable dependency description."""
        pred_name = self.predecessor.name if self.predecessor else str(self.predecessor_id)
        succ_name = self.successor.name if self.successor else str(self.successor_id)

        type_desc = {
            DependencyType.FS: "finishes before",
            DependencyType.SS: "starts before",
            DependencyType.FF: "finishes before",
            DependencyType.SF: "starts before",
        }

        lag_desc = ""
        if self.lag_days > 0:
            lag_desc = f" with {self.lag_days} day lag"
        elif self.lag_days < 0:
            lag_desc = f" with {abs(self.lag_days)} day lead"

        return f"{pred_name} {type_desc[self.dependency_type]} {succ_name}{lag_desc}"


class DependencyBriefResponse(BaseModel):
    """
    Brief dependency response for listing.

    Contains essential fields without nested activity details.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "990e8400-e29b-41d4-a716-446655440005",
                "predecessor_id": "770e8400-e29b-41d4-a716-446655440003",
                "successor_id": "880e8400-e29b-41d4-a716-446655440004",
                "dependency_type": "FS",
                "lag_days": 0,
            }
        }
    )

    id: UUID = Field(
        ...,
        description="Unique dependency identifier",
    )
    predecessor_id: UUID = Field(
        ...,
        description="ID of the predecessor activity",
    )
    successor_id: UUID = Field(
        ...,
        description="ID of the successor activity",
    )
    dependency_type: DependencyType = Field(
        ...,
        description="Type of dependency relationship",
    )
    lag_days: int = Field(
        ...,
        description="Lag/lead in working days",
    )


class BulkDependencyCreate(BaseModel):
    """
    Schema for creating multiple dependencies at once.

    Used for bulk operations like importing schedules.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dependencies": [
                    {
                        "predecessor_id": "770e8400-e29b-41d4-a716-446655440003",
                        "successor_id": "880e8400-e29b-41d4-a716-446655440004",
                        "dependency_type": "FS",
                        "lag_days": 0,
                    },
                    {
                        "predecessor_id": "880e8400-e29b-41d4-a716-446655440004",
                        "successor_id": "990e8400-e29b-41d4-a716-446655440005",
                        "dependency_type": "FS",
                        "lag_days": 2,
                    },
                ]
            }
        }
    )

    dependencies: list[DependencyCreate] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of dependencies to create",
    )


class DependencyValidationResult(BaseModel):
    """
    Schema for dependency validation results.

    Used when checking for circular dependencies or other issues.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_valid": False,
                "has_cycles": True,
                "cycle_path": [
                    "770e8400-e29b-41d4-a716-446655440003",
                    "880e8400-e29b-41d4-a716-446655440004",
                    "990e8400-e29b-41d4-a716-446655440005",
                    "770e8400-e29b-41d4-a716-446655440003",
                ],
                "error_message": "Circular dependency detected",
            }
        }
    )

    is_valid: bool = Field(
        ...,
        description="Whether the dependency configuration is valid",
    )
    has_cycles: bool = Field(
        default=False,
        description="Whether circular dependencies were detected",
    )
    cycle_path: list[UUID] | None = Field(
        default=None,
        description="Activity IDs forming a cycle (if detected)",
    )
    error_message: str | None = Field(
        default=None,
        description="Description of validation error",
    )
