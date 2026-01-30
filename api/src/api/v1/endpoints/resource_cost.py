"""API endpoints for resource cost and material tracking."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import get_current_user, get_db
from src.core.exceptions import NotFoundError, ValidationError
from src.models.user import User
from src.schemas.resource_cost import (
    ActivityCostResponse,
    CostEntryCreate,
    CostEntryResponse,
    EVMSSyncResponse,
    MaterialConsumptionRequest,
    MaterialConsumptionResponse,
    MaterialStatusResponse,
    ProgramCostSummaryResponse,
    ProgramMaterialSummaryResponse,
    WBSCostResponse,
)
from src.services.material_tracking import MaterialTrackingService
from src.services.resource_cost import ResourceCostService

router = APIRouter(prefix="/cost", tags=["Resource Cost"])


@router.get("/activities/{activity_id}", response_model=ActivityCostResponse)
async def get_activity_cost(
    activity_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityCostResponse:
    """
    Get cost breakdown for an activity.

    Returns planned and actual costs with resource-level breakdown.
    """
    service = ResourceCostService(db)
    try:
        summary = await service.calculate_activity_cost(activity_id)
        return ActivityCostResponse(
            activity_id=summary.activity_id,
            activity_code=summary.activity_code,
            activity_name=summary.activity_name,
            planned_cost=summary.planned_cost,
            actual_cost=summary.actual_cost,
            cost_variance=summary.cost_variance,
            percent_spent=summary.percent_spent,
            resource_breakdown=summary.resource_breakdown,
        )
    except ValueError as e:
        raise NotFoundError(str(e), "ACTIVITY_NOT_FOUND") from e


@router.get("/wbs/{wbs_id}", response_model=WBSCostResponse)
async def get_wbs_cost(
    wbs_id: UUID,
    include_children: bool = Query(True, description="Include child WBS elements"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WBSCostResponse:
    """
    Get cost rolled up to WBS level.
    """
    service = ResourceCostService(db)
    try:
        summary = await service.calculate_wbs_cost(wbs_id, include_children)
        return WBSCostResponse(
            wbs_id=summary.wbs_id,
            wbs_code=summary.wbs_code,
            wbs_name=summary.wbs_name,
            planned_cost=summary.planned_cost,
            actual_cost=summary.actual_cost,
            cost_variance=summary.cost_variance,
            activity_count=summary.activity_count,
        )
    except ValueError as e:
        raise NotFoundError(str(e), "WBS_NOT_FOUND") from e


@router.get("/programs/{program_id}", response_model=ProgramCostSummaryResponse)
async def get_program_cost_summary(
    program_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgramCostSummaryResponse:
    """
    Get comprehensive cost summary for a program.

    Includes breakdown by resource type and WBS.
    """
    service = ResourceCostService(db)
    summary = await service.calculate_program_cost(program_id)
    return ProgramCostSummaryResponse(
        program_id=summary.program_id,
        total_planned_cost=summary.total_planned_cost,
        total_actual_cost=summary.total_actual_cost,
        total_cost_variance=summary.total_cost_variance,
        labor_cost=summary.labor_cost,
        equipment_cost=summary.equipment_cost,
        material_cost=summary.material_cost,
        resource_count=summary.resource_count,
        activity_count=summary.activity_count,
        wbs_breakdown=[
            WBSCostResponse(
                wbs_id=w.wbs_id,
                wbs_code=w.wbs_code,
                wbs_name=w.wbs_name,
                planned_cost=w.planned_cost,
                actual_cost=w.actual_cost,
                cost_variance=w.cost_variance,
                activity_count=w.activity_count,
            )
            for w in summary.wbs_breakdown
        ],
    )


@router.post("/programs/{program_id}/evms-sync", response_model=EVMSSyncResponse)
async def sync_costs_to_evms(
    program_id: UUID,
    period_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EVMSSyncResponse:
    """
    Sync resource actual costs to EVMS ACWP.

    Updates the specified EVMS period with calculated ACWP from
    resource assignments.
    """
    service = ResourceCostService(db)
    result = await service.sync_evms_acwp(program_id, period_id)
    return EVMSSyncResponse(
        period_id=result.period_id,
        acwp_updated=result.acwp_updated,
        wbs_elements_updated=result.wbs_elements_updated,
        success=result.success,
        warnings=result.warnings,
    )


@router.post("/assignments/{assignment_id}/entries", response_model=CostEntryResponse)
async def record_cost_entry(
    assignment_id: UUID,
    entry: CostEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostEntryResponse:
    """
    Record a cost entry for an assignment.

    Used to track actual hours worked or materials consumed on specific dates.
    """
    service = ResourceCostService(db)
    try:
        result = await service.record_cost_entry(
            assignment_id=assignment_id,
            entry_date=entry.entry_date,
            hours_worked=entry.hours_worked,
            quantity_used=entry.quantity_used,
            notes=entry.notes,
        )
        return CostEntryResponse.model_validate(result)
    except ValueError as e:
        raise ValidationError(str(e), "INVALID_COST_ENTRY") from e


# Material tracking endpoints
material_router = APIRouter(prefix="/materials", tags=["Material Tracking"])


@material_router.get("/resources/{resource_id}", response_model=MaterialStatusResponse)
async def get_material_status(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MaterialStatusResponse:
    """
    Get current status of a material resource.
    """
    service = MaterialTrackingService(db)
    try:
        status = await service.get_material_status(resource_id)
        return MaterialStatusResponse(
            resource_id=status.resource_id,
            resource_code=status.resource_code,
            resource_name=status.resource_name,
            quantity_unit=status.quantity_unit,
            quantity_available=status.quantity_available,
            quantity_assigned=status.quantity_assigned,
            quantity_consumed=status.quantity_consumed,
            quantity_remaining=status.quantity_remaining,
            percent_consumed=status.percent_consumed,
            unit_cost=status.unit_cost,
            total_value=status.total_value,
            consumed_value=status.consumed_value,
        )
    except ValueError as e:
        raise NotFoundError(str(e), "RESOURCE_NOT_FOUND") from e


@material_router.post(
    "/assignments/{assignment_id}/consume", response_model=MaterialConsumptionResponse
)
async def consume_material(
    assignment_id: UUID,
    request: MaterialConsumptionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MaterialConsumptionResponse:
    """
    Record material consumption for an assignment.
    """
    service = MaterialTrackingService(db)
    try:
        result = await service.consume_material(assignment_id, request.quantity)
        return MaterialConsumptionResponse(
            assignment_id=result.assignment_id,
            quantity_consumed=result.quantity_consumed,
            remaining_assigned=result.remaining_assigned,
            cost_incurred=result.cost_incurred,
        )
    except ValueError as e:
        raise ValidationError(str(e), "INVALID_CONSUMPTION") from e


@material_router.get("/programs/{program_id}", response_model=ProgramMaterialSummaryResponse)
async def get_program_materials(
    program_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgramMaterialSummaryResponse:
    """
    Get summary of all materials in a program.
    """
    service = MaterialTrackingService(db)
    summary = await service.get_program_materials(program_id)
    return ProgramMaterialSummaryResponse(
        program_id=summary.program_id,
        material_count=summary.material_count,
        total_value=summary.total_value,
        consumed_value=summary.consumed_value,
        remaining_value=summary.remaining_value,
        materials=[
            MaterialStatusResponse(
                resource_id=m.resource_id,
                resource_code=m.resource_code,
                resource_name=m.resource_name,
                quantity_unit=m.quantity_unit,
                quantity_available=m.quantity_available,
                quantity_assigned=m.quantity_assigned,
                quantity_consumed=m.quantity_consumed,
                quantity_remaining=m.quantity_remaining,
                percent_consumed=m.percent_consumed,
                unit_cost=m.unit_cost,
                total_value=m.total_value,
                consumed_value=m.consumed_value,
            )
            for m in summary.materials
        ],
    )
