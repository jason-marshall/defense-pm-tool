"""Material quantity tracking service."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.enums import ResourceType
from src.models.resource import Resource, ResourceAssignment


@dataclass
class MaterialStatus:
    """Status of a material resource."""

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


@dataclass
class MaterialConsumption:
    """Record of material consumption."""

    assignment_id: UUID
    quantity_consumed: Decimal
    remaining_assigned: Decimal
    cost_incurred: Decimal


@dataclass
class ProgramMaterialSummary:
    """Summary of all materials in a program."""

    program_id: UUID
    material_count: int
    total_value: Decimal
    consumed_value: Decimal
    remaining_value: Decimal
    materials: list[MaterialStatus]


class MaterialTrackingService:
    """
    Service for tracking material resource quantities.

    Handles:
    - Material quantity assignment
    - Consumption tracking
    - Inventory status
    - Cost calculations for materials
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _round(value: Decimal) -> Decimal:
        """Round to 2 decimal places."""
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    async def get_material_status(
        self,
        resource_id: UUID,
    ) -> MaterialStatus:
        """
        Get current status of a material resource.
        """
        query = (
            select(Resource)
            .options(selectinload(Resource.assignments))
            .where(Resource.id == resource_id)
            .where(Resource.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        resource = result.scalar_one_or_none()

        if not resource:
            raise ValueError(f"Resource {resource_id} not found")

        if resource.resource_type != ResourceType.MATERIAL:
            raise ValueError(f"Resource {resource_id} is not a MATERIAL type")

        # Calculate totals from assignments
        total_assigned = Decimal("0")
        total_consumed = Decimal("0")

        for assignment in resource.assignments:
            if assignment.deleted_at:
                continue
            total_assigned += assignment.quantity_assigned or Decimal("0")
            total_consumed += assignment.quantity_consumed or Decimal("0")

        quantity_available = resource.quantity_available or Decimal("0")
        quantity_remaining = quantity_available - total_consumed
        unit_cost = resource.unit_cost or Decimal("0")

        percent_consumed = (
            (total_consumed / quantity_available * 100) if quantity_available > 0 else Decimal("0")
        )

        return MaterialStatus(
            resource_id=resource.id,
            resource_code=resource.code,
            resource_name=resource.name,
            quantity_unit=resource.quantity_unit or "units",
            quantity_available=self._round(quantity_available),
            quantity_assigned=self._round(total_assigned),
            quantity_consumed=self._round(total_consumed),
            quantity_remaining=self._round(quantity_remaining),
            percent_consumed=self._round(percent_consumed),
            unit_cost=self._round(unit_cost),
            total_value=self._round(quantity_available * unit_cost),
            consumed_value=self._round(total_consumed * unit_cost),
        )

    async def consume_material(
        self,
        assignment_id: UUID,
        quantity: Decimal,
    ) -> MaterialConsumption:
        """
        Record material consumption for an assignment.

        Validates that consumption doesn't exceed assignment.
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
            raise ValueError(f"Assignment {assignment_id} not found")

        resource = assignment.resource
        if resource.resource_type != ResourceType.MATERIAL:
            raise ValueError("Can only consume material resources")

        # Validate quantity
        assigned = assignment.quantity_assigned or Decimal("0")
        current_consumed = assignment.quantity_consumed or Decimal("0")
        new_total = current_consumed + quantity

        if new_total > assigned:
            raise ValueError(
                f"Consumption ({new_total}) would exceed assigned quantity ({assigned})"
            )

        # Update assignment
        assignment.quantity_consumed = new_total

        # Calculate cost
        unit_cost = resource.unit_cost or Decimal("0")
        cost_incurred = quantity * unit_cost
        assignment.actual_cost += cost_incurred

        await self.db.commit()

        return MaterialConsumption(
            assignment_id=assignment_id,
            quantity_consumed=self._round(new_total),
            remaining_assigned=self._round(assigned - new_total),
            cost_incurred=self._round(cost_incurred),
        )

    async def get_program_materials(
        self,
        program_id: UUID,
    ) -> ProgramMaterialSummary:
        """
        Get summary of all materials in a program.
        """
        query = (
            select(Resource)
            .where(Resource.program_id == program_id)
            .where(Resource.resource_type == ResourceType.MATERIAL)
            .where(Resource.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        materials = result.scalars().all()

        material_statuses = []
        total_value = Decimal("0")
        consumed_value = Decimal("0")

        for material in materials:
            status = await self.get_material_status(material.id)
            material_statuses.append(status)
            total_value += status.total_value
            consumed_value += status.consumed_value

        return ProgramMaterialSummary(
            program_id=program_id,
            material_count=len(materials),
            total_value=self._round(total_value),
            consumed_value=self._round(consumed_value),
            remaining_value=self._round(total_value - consumed_value),
            materials=material_statuses,
        )

    async def validate_material_assignment(
        self,
        resource_id: UUID,
        quantity: Decimal,
    ) -> bool:
        """
        Validate that a material assignment quantity is available.

        Returns True if quantity is available, raises error if not.
        """
        status = await self.get_material_status(resource_id)

        if quantity > status.quantity_remaining:
            raise ValueError(
                f"Requested quantity ({quantity}) exceeds available "
                f"({status.quantity_remaining} {status.quantity_unit})"
            )

        return True

    async def update_material_inventory(
        self,
        resource_id: UUID,
        quantity_available: Decimal,
        unit_cost: Decimal | None = None,
    ) -> MaterialStatus:
        """
        Update material inventory levels.

        Args:
            resource_id: Material resource ID
            quantity_available: New available quantity
            unit_cost: Optional new unit cost

        Returns:
            Updated material status
        """
        query = (
            select(Resource).where(Resource.id == resource_id).where(Resource.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        resource = result.scalar_one_or_none()

        if not resource:
            raise ValueError(f"Resource {resource_id} not found")

        if resource.resource_type != ResourceType.MATERIAL:
            raise ValueError(f"Resource {resource_id} is not a MATERIAL type")

        resource.quantity_available = quantity_available
        if unit_cost is not None:
            resource.unit_cost = unit_cost

        await self.db.commit()

        return await self.get_material_status(resource_id)

    async def get_material_assignment_status(
        self,
        assignment_id: UUID,
    ) -> dict[str, Any]:
        """
        Get detailed status of a material assignment.
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
            raise ValueError(f"Assignment {assignment_id} not found")

        resource = assignment.resource
        if resource.resource_type != ResourceType.MATERIAL:
            raise ValueError("Assignment is not for a material resource")

        assigned = assignment.quantity_assigned or Decimal("0")
        consumed = assignment.quantity_consumed or Decimal("0")
        remaining = assigned - consumed
        unit_cost = resource.unit_cost or Decimal("0")

        return {
            "assignment_id": str(assignment_id),
            "resource_id": str(resource.id),
            "resource_code": resource.code,
            "resource_name": resource.name,
            "quantity_unit": resource.quantity_unit or "units",
            "quantity_assigned": self._round(assigned),
            "quantity_consumed": self._round(consumed),
            "quantity_remaining": self._round(remaining),
            "percent_consumed": self._round(
                (consumed / assigned * 100) if assigned > 0 else Decimal("0")
            ),
            "unit_cost": self._round(unit_cost),
            "assigned_value": self._round(assigned * unit_cost),
            "consumed_value": self._round(consumed * unit_cost),
        }
