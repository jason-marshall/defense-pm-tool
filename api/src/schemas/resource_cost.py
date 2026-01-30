"""Pydantic schemas for resource cost and material tracking."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ActivityCostResponse(BaseModel):
    """Cost breakdown for an activity."""

    activity_id: UUID
    activity_code: str
    activity_name: str
    planned_cost: Decimal
    actual_cost: Decimal
    cost_variance: Decimal
    percent_spent: Decimal
    resource_breakdown: list[dict[str, Any]]


class WBSCostResponse(BaseModel):
    """Cost summary rolled up to WBS level."""

    wbs_id: UUID
    wbs_code: str
    wbs_name: str
    planned_cost: Decimal
    actual_cost: Decimal
    cost_variance: Decimal
    activity_count: int


class ProgramCostSummaryResponse(BaseModel):
    """Comprehensive cost summary for a program."""

    program_id: UUID
    total_planned_cost: Decimal
    total_actual_cost: Decimal
    total_cost_variance: Decimal
    labor_cost: Decimal
    equipment_cost: Decimal
    material_cost: Decimal
    resource_count: int
    activity_count: int
    wbs_breakdown: list[WBSCostResponse]


class EVMSSyncResponse(BaseModel):
    """Result of syncing costs to EVMS."""

    period_id: UUID
    acwp_updated: Decimal
    wbs_elements_updated: int
    success: bool
    warnings: list[str]


class CostEntryCreate(BaseModel):
    """Request to create a cost entry."""

    entry_date: date
    hours_worked: Decimal = Field(default=Decimal("0"), ge=0)
    quantity_used: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None


class CostEntryResponse(BaseModel):
    """Response for a cost entry."""

    id: UUID
    assignment_id: UUID
    entry_date: date
    hours_worked: Decimal
    cost_incurred: Decimal
    quantity_used: Decimal | None
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaterialStatusResponse(BaseModel):
    """Current status of a material resource."""

    resource_id: UUID
    resource_code: str
    resource_name: str
    quantity_unit: str
    quantity_available: Decimal
    quantity_assigned: Decimal
    quantity_consumed: Decimal
    quantity_remaining: Decimal
    percent_consumed: Decimal
    unit_cost: Decimal
    total_value: Decimal
    consumed_value: Decimal


class MaterialConsumptionRequest(BaseModel):
    """Request to consume material."""

    quantity: Decimal = Field(..., gt=0, description="Quantity to consume")


class MaterialConsumptionResponse(BaseModel):
    """Response for material consumption."""

    assignment_id: UUID
    quantity_consumed: Decimal
    remaining_assigned: Decimal
    cost_incurred: Decimal


class ProgramMaterialSummaryResponse(BaseModel):
    """Summary of all materials in a program."""

    program_id: UUID
    material_count: int
    total_value: Decimal
    consumed_value: Decimal
    remaining_value: Decimal
    materials: list[MaterialStatusResponse]
