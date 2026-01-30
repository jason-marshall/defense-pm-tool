"""Resource cost calculation service for EVMS integration."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.activity import Activity
from src.models.enums import ResourceType
from src.models.evms_period import EVMSPeriod, EVMSPeriodData
from src.models.resource import Resource, ResourceAssignment
from src.models.resource_cost import ResourceCostEntry
from src.models.wbs import WBSElement


@dataclass
class ActivityCostSummary:
    """Cost summary for a single activity."""

    activity_id: UUID
    activity_code: str
    activity_name: str
    planned_cost: Decimal
    actual_cost: Decimal
    cost_variance: Decimal
    percent_spent: Decimal
    resource_breakdown: list[dict[str, Any]]


@dataclass
class WBSCostSummary:
    """Cost summary rolled up to WBS level."""

    wbs_id: UUID
    wbs_code: str
    wbs_name: str
    planned_cost: Decimal
    actual_cost: Decimal
    cost_variance: Decimal
    activity_count: int


@dataclass
class ProgramCostSummary:
    """Cost summary for entire program."""

    program_id: UUID
    total_planned_cost: Decimal
    total_actual_cost: Decimal
    total_cost_variance: Decimal
    labor_cost: Decimal
    equipment_cost: Decimal
    material_cost: Decimal
    resource_count: int
    activity_count: int
    wbs_breakdown: list[WBSCostSummary]


@dataclass
class EVMSSyncResult:
    """Result of syncing costs to EVMS."""

    period_id: UUID
    acwp_updated: Decimal
    wbs_elements_updated: int
    success: bool
    warnings: list[str]


class ResourceCostService:
    """
    Service for calculating resource costs and integrating with EVMS.

    Responsibilities:
    - Calculate planned and actual costs for assignments
    - Roll up costs to activity, WBS, and program levels
    - Sync actual costs to EVMS ACWP
    - Track material consumption costs
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _round(value: Decimal) -> Decimal:
        """Round to 2 decimal places."""
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    async def calculate_assignment_cost(
        self,
        assignment_id: UUID,
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate planned and actual cost for a single assignment.

        Returns:
            Tuple of (planned_cost, actual_cost)
        """
        query = (
            select(ResourceAssignment)
            .options(selectinload(ResourceAssignment.resource))
            .where(ResourceAssignment.id == assignment_id)
            .where(ResourceAssignment.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        assignment = result.scalar_one_or_none()

        if not assignment:
            return Decimal("0"), Decimal("0")

        resource = assignment.resource

        if resource.resource_type == ResourceType.MATERIAL:
            # Material: cost based on quantity
            unit_cost = resource.unit_cost or Decimal("0")
            planned = (assignment.quantity_assigned or Decimal("0")) * unit_cost
            actual = assignment.quantity_consumed * unit_cost
        else:
            # Labor/Equipment: cost based on hours
            cost_rate = resource.cost_rate or Decimal("0")
            planned = (assignment.planned_hours or Decimal("0")) * cost_rate
            actual = assignment.actual_hours * cost_rate

        return self._round(planned), self._round(actual)

    async def calculate_activity_cost(
        self,
        activity_id: UUID,
    ) -> ActivityCostSummary:
        """
        Calculate total costs for an activity from all assignments.
        """
        query = (
            select(Activity)
            .options(
                selectinload(Activity.resource_assignments).selectinload(
                    ResourceAssignment.resource
                )
            )
            .where(Activity.id == activity_id)
            .where(Activity.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        activity = result.scalar_one_or_none()

        if not activity:
            raise ValueError(f"Activity {activity_id} not found")

        planned_total = Decimal("0")
        actual_total = Decimal("0")
        resource_breakdown = []

        for assignment in activity.resource_assignments:
            if assignment.deleted_at:
                continue

            resource = assignment.resource

            if resource.resource_type == ResourceType.MATERIAL:
                unit_cost = resource.unit_cost or Decimal("0")
                planned = (assignment.quantity_assigned or Decimal("0")) * unit_cost
                actual = assignment.quantity_consumed * unit_cost
            else:
                cost_rate = resource.cost_rate or Decimal("0")
                planned = (assignment.planned_hours or Decimal("0")) * cost_rate
                actual = assignment.actual_hours * cost_rate

            planned_total += planned
            actual_total += actual

            resource_breakdown.append(
                {
                    "resource_id": str(resource.id),
                    "resource_code": resource.code,
                    "resource_name": resource.name,
                    "resource_type": resource.resource_type.value,
                    "planned_cost": self._round(planned),
                    "actual_cost": self._round(actual),
                }
            )

        planned_total = self._round(planned_total)
        actual_total = self._round(actual_total)
        variance = planned_total - actual_total
        percent_spent = (actual_total / planned_total * 100) if planned_total > 0 else Decimal("0")

        return ActivityCostSummary(
            activity_id=activity.id,
            activity_code=activity.code,
            activity_name=activity.name,
            planned_cost=planned_total,
            actual_cost=actual_total,
            cost_variance=self._round(variance),
            percent_spent=self._round(percent_spent),
            resource_breakdown=resource_breakdown,
        )

    async def calculate_wbs_cost(
        self,
        wbs_id: UUID,
        include_children: bool = True,
    ) -> WBSCostSummary:
        """
        Calculate costs rolled up to WBS level.
        """
        # Get WBS element
        wbs_query = select(WBSElement).where(WBSElement.id == wbs_id)
        result = await self.db.execute(wbs_query)
        wbs = result.scalar_one_or_none()

        if not wbs:
            raise ValueError(f"WBS {wbs_id} not found")

        # Get activities for this WBS (and children if requested)
        if include_children:
            # Use ltree to get all descendants
            activity_query = (
                select(Activity)
                .join(WBSElement)
                .where(WBSElement.path.descendant_of(wbs.path))
                .where(Activity.deleted_at.is_(None))
            )
        else:
            activity_query = (
                select(Activity)
                .where(Activity.wbs_id == wbs_id)
                .where(Activity.deleted_at.is_(None))
            )

        result = await self.db.execute(activity_query)
        activities = result.scalars().all()

        planned_total = Decimal("0")
        actual_total = Decimal("0")

        for activity in activities:
            cost_summary = await self.calculate_activity_cost(activity.id)
            planned_total += cost_summary.planned_cost
            actual_total += cost_summary.actual_cost

        return WBSCostSummary(
            wbs_id=wbs.id,
            wbs_code=wbs.wbs_code,
            wbs_name=wbs.name,
            planned_cost=self._round(planned_total),
            actual_cost=self._round(actual_total),
            cost_variance=self._round(planned_total - actual_total),
            activity_count=len(activities),
        )

    async def calculate_program_cost(
        self,
        program_id: UUID,
    ) -> ProgramCostSummary:
        """
        Calculate cost summary for entire program.
        """
        # Get all assignments for program with resources
        query = (
            select(ResourceAssignment)
            .join(Resource)
            .where(Resource.program_id == program_id)
            .where(ResourceAssignment.deleted_at.is_(None))
            .options(selectinload(ResourceAssignment.resource))
        )
        result = await self.db.execute(query)
        assignments = result.scalars().all()

        totals: dict[str, Decimal] = {
            "planned": Decimal("0"),
            "actual": Decimal("0"),
            "labor": Decimal("0"),
            "equipment": Decimal("0"),
            "material": Decimal("0"),
        }
        resource_ids: set[UUID] = set()
        activity_ids: set[UUID] = set()

        for assignment in assignments:
            resource = assignment.resource
            resource_ids.add(resource.id)
            activity_ids.add(assignment.activity_id)

            if resource.resource_type == ResourceType.MATERIAL:
                unit_cost = resource.unit_cost or Decimal("0")
                planned = (assignment.quantity_assigned or Decimal("0")) * unit_cost
                actual = assignment.quantity_consumed * unit_cost
                totals["material"] += actual
            else:
                cost_rate = resource.cost_rate or Decimal("0")
                planned = (assignment.planned_hours or Decimal("0")) * cost_rate
                actual = assignment.actual_hours * cost_rate

                if resource.resource_type == ResourceType.LABOR:
                    totals["labor"] += actual
                else:
                    totals["equipment"] += actual

            totals["planned"] += planned
            totals["actual"] += actual

        # Get WBS breakdown (top-level only)
        wbs_query = (
            select(WBSElement)
            .where(WBSElement.program_id == program_id)
            .where(WBSElement.level == 1)
            .where(WBSElement.deleted_at.is_(None))
        )
        result = await self.db.execute(wbs_query)
        top_wbs = result.scalars().all()

        wbs_breakdown = []
        for wbs in top_wbs:
            wbs_summary = await self.calculate_wbs_cost(wbs.id, include_children=True)
            wbs_breakdown.append(wbs_summary)

        return ProgramCostSummary(
            program_id=program_id,
            total_planned_cost=self._round(totals["planned"]),
            total_actual_cost=self._round(totals["actual"]),
            total_cost_variance=self._round(totals["planned"] - totals["actual"]),
            labor_cost=self._round(totals["labor"]),
            equipment_cost=self._round(totals["equipment"]),
            material_cost=self._round(totals["material"]),
            resource_count=len(resource_ids),
            activity_count=len(activity_ids),
            wbs_breakdown=wbs_breakdown,
        )

    async def sync_evms_acwp(
        self,
        program_id: UUID,
        period_id: UUID,
    ) -> EVMSSyncResult:
        """
        Sync actual costs to EVMS period ACWP.

        Updates EVMSPeriodData.acwp for each WBS element based on
        resource assignment actual costs.
        """
        warnings: list[str] = []

        # Get period
        period_query = (
            select(EVMSPeriod)
            .where(EVMSPeriod.id == period_id)
            .where(EVMSPeriod.program_id == program_id)
        )
        result = await self.db.execute(period_query)
        period = result.scalar_one_or_none()

        if not period:
            return EVMSSyncResult(
                period_id=period_id,
                acwp_updated=Decimal("0"),
                wbs_elements_updated=0,
                success=False,
                warnings=["Period not found"],
            )

        # Get WBS elements with period data
        period_data_query = select(EVMSPeriodData).where(EVMSPeriodData.period_id == period_id)
        result = await self.db.execute(period_data_query)
        period_data_list = cast("list[EVMSPeriodData]", list(result.scalars().all()))
        period_data_records: dict[UUID, EVMSPeriodData] = {pd.wbs_id: pd for pd in period_data_list}

        # Calculate actual costs per WBS
        wbs_query = (
            select(WBSElement)
            .where(WBSElement.program_id == program_id)
            .where(WBSElement.deleted_at.is_(None))
        )
        result = await self.db.execute(wbs_query)
        wbs_elements = result.scalars().all()

        total_acwp = Decimal("0")
        updated_count = 0

        for wbs in wbs_elements:
            wbs_cost = await self.calculate_wbs_cost(wbs.id, include_children=False)

            if wbs.id in period_data_records:
                pd = period_data_records[wbs.id]
                pd.acwp = wbs_cost.actual_cost
                updated_count += 1
            else:
                # Create new period data if not exists
                new_pd = EVMSPeriodData(
                    period_id=period_id,
                    wbs_id=wbs.id,
                    bcws=Decimal("0"),
                    bcwp=Decimal("0"),
                    acwp=wbs_cost.actual_cost,
                )
                self.db.add(new_pd)
                updated_count += 1

            total_acwp += wbs_cost.actual_cost

        # Update period cumulative ACWP
        period.cumulative_acwp = total_acwp

        await self.db.commit()

        return EVMSSyncResult(
            period_id=period_id,
            acwp_updated=self._round(total_acwp),
            wbs_elements_updated=updated_count,
            success=True,
            warnings=warnings,
        )

    async def record_cost_entry(
        self,
        assignment_id: UUID,
        entry_date: date,
        hours_worked: Decimal = Decimal("0"),
        quantity_used: Decimal | None = None,
        notes: str | None = None,
    ) -> ResourceCostEntry:
        """
        Record a cost entry for an assignment.

        Automatically calculates cost based on resource cost rate.
        Updates assignment totals.
        """
        # Get assignment with resource
        query = (
            select(ResourceAssignment)
            .options(selectinload(ResourceAssignment.resource))
            .where(ResourceAssignment.id == assignment_id)
        )
        result = await self.db.execute(query)
        assignment = result.scalar_one_or_none()

        if not assignment:
            raise ValueError(f"Assignment {assignment_id} not found")

        resource = assignment.resource

        # Calculate cost
        if resource.resource_type == ResourceType.MATERIAL:
            cost = (quantity_used or Decimal("0")) * (resource.unit_cost or Decimal("0"))
        else:
            cost = hours_worked * (resource.cost_rate or Decimal("0"))

        # Create entry
        entry = ResourceCostEntry(
            assignment_id=assignment_id,
            entry_date=entry_date,
            hours_worked=hours_worked,
            cost_incurred=self._round(cost),
            quantity_used=quantity_used,
            notes=notes,
        )
        self.db.add(entry)

        # Update assignment totals
        assignment.actual_hours += hours_worked
        assignment.actual_cost += cost
        if quantity_used:
            assignment.quantity_consumed += quantity_used

        await self.db.commit()
        await self.db.refresh(entry)

        return entry

    async def get_assignment_cost_entries(
        self,
        assignment_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[ResourceCostEntry]:
        """
        Get cost entries for an assignment within optional date range.
        """
        query = (
            select(ResourceCostEntry)
            .where(ResourceCostEntry.assignment_id == assignment_id)
            .where(ResourceCostEntry.deleted_at.is_(None))
        )

        if start_date:
            query = query.where(ResourceCostEntry.entry_date >= start_date)
        if end_date:
            query = query.where(ResourceCostEntry.entry_date <= end_date)

        query = query.order_by(ResourceCostEntry.entry_date)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_resource_cost_summary(
        self,
        resource_id: UUID,
    ) -> dict[str, Any]:
        """
        Get cost summary for a resource across all assignments.
        """
        query = (
            select(ResourceAssignment)
            .options(selectinload(ResourceAssignment.resource))
            .where(ResourceAssignment.resource_id == resource_id)
            .where(ResourceAssignment.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        assignments = result.scalars().all()

        total_planned_hours = Decimal("0")
        total_actual_hours = Decimal("0")
        total_planned_cost = Decimal("0")
        total_actual_cost = Decimal("0")

        for assignment in assignments:
            total_planned_hours += assignment.planned_hours or Decimal("0")
            total_actual_hours += assignment.actual_hours
            total_planned_cost += assignment.planned_cost or Decimal("0")
            total_actual_cost += assignment.actual_cost

        return {
            "resource_id": str(resource_id),
            "assignment_count": len(assignments),
            "total_planned_hours": self._round(total_planned_hours),
            "total_actual_hours": self._round(total_actual_hours),
            "total_planned_cost": self._round(total_planned_cost),
            "total_actual_cost": self._round(total_actual_cost),
            "cost_variance": self._round(total_planned_cost - total_actual_cost),
        }
