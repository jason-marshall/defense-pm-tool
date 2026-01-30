"""Service for cross-program resource availability."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.resource import Resource, ResourceAssignment
from src.models.resource_pool import ResourcePool, ResourcePoolMember


@dataclass
class CrossProgramConflict:
    """Conflict between programs for a shared resource."""

    resource_id: UUID
    resource_name: str
    conflict_date: date
    programs_involved: list[dict[str, Any]]  # [{program_id, program_name, assigned_hours}]
    total_assigned: Decimal
    available_hours: Decimal
    overallocation: Decimal


@dataclass
class PoolAvailability:
    """Availability of resources in a pool."""

    pool_id: UUID
    pool_name: str
    date_range_start: date
    date_range_end: date
    resources: list[dict[str, Any]]  # Resource availability summaries
    conflicts: list[CrossProgramConflict]


class CrossProgramAvailabilityService:
    """
    Service for managing cross-program resource availability.

    Handles:
    - Checking resource availability across multiple programs
    - Detecting conflicts when multiple programs use shared resources
    - Allocation percentage-based availability calculations
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_pool_availability(
        self,
        pool_id: UUID,
        start_date: date,
        end_date: date,
    ) -> PoolAvailability:
        """
        Get availability of all resources in a pool across all programs.
        """
        # Get pool with members
        pool_query = (
            select(ResourcePool)
            .options(selectinload(ResourcePool.members).selectinload(ResourcePoolMember.resource))
            .where(ResourcePool.id == pool_id)
            .where(ResourcePool.deleted_at.is_(None))
        )
        result = await self.db.execute(pool_query)
        pool = result.scalar_one_or_none()

        if not pool:
            raise ValueError(f"Pool {pool_id} not found")

        resources = []
        all_conflicts: list[CrossProgramConflict] = []

        for member in pool.members:
            if not member.is_active:
                continue

            resource = member.resource

            # Get all assignments for this resource across all programs
            assignments = await self._get_cross_program_assignments(
                resource.id,
                start_date,
                end_date,
            )

            # Calculate daily availability and detect conflicts
            resource_conflicts = await self._detect_conflicts(
                resource,
                assignments,
                start_date,
                end_date,
                member.allocation_percentage,
            )

            resources.append(
                {
                    "resource_id": str(resource.id),
                    "resource_code": resource.code,
                    "resource_name": resource.name,
                    "allocation_percentage": float(member.allocation_percentage),
                    "is_active": member.is_active,
                    "conflict_count": len(resource_conflicts),
                }
            )

            all_conflicts.extend(resource_conflicts)

        return PoolAvailability(
            pool_id=pool.id,
            pool_name=pool.name,
            date_range_start=start_date,
            date_range_end=end_date,
            resources=resources,
            conflicts=all_conflicts,
        )

    async def check_resource_conflict(
        self,
        resource_id: UUID,
        program_id: UUID,
        assignment_start: date,
        assignment_end: date,
        units: Decimal,
    ) -> list[CrossProgramConflict]:
        """
        Check if assigning a resource would cause cross-program conflicts.

        Used before creating an assignment to preview conflicts.
        """
        # Get resource
        resource_query = select(Resource).where(Resource.id == resource_id)
        result = await self.db.execute(resource_query)
        resource = result.scalar_one_or_none()

        if not resource:
            raise ValueError(f"Resource {resource_id} not found")

        # Get existing assignments
        assignments = await self._get_cross_program_assignments(
            resource_id,
            assignment_start,
            assignment_end,
        )

        # Add proposed assignment
        proposed = {
            "program_id": program_id,
            "start_date": assignment_start,
            "end_date": assignment_end,
            "units": units,
        }

        # Check for conflicts
        conflicts = []
        current = assignment_start

        while current <= assignment_end:
            # Get all assignments active on this date
            daily_assignments = [
                a
                for a in assignments
                if a["start_date"] and a["end_date"] and a["start_date"] <= current <= a["end_date"]
            ]
            daily_assignments.append(proposed)

            # Calculate total allocation
            total_hours = sum(
                (Decimal(str(a["units"])) * resource.capacity_per_day for a in daily_assignments),
                Decimal("0"),
            )

            available = resource.capacity_per_day

            if total_hours > available:
                conflicts.append(
                    CrossProgramConflict(
                        resource_id=resource.id,
                        resource_name=resource.name,
                        conflict_date=current,
                        programs_involved=[
                            {
                                "program_id": str(a["program_id"]),
                                "assigned_hours": float(
                                    Decimal(str(a["units"])) * resource.capacity_per_day
                                ),
                            }
                            for a in daily_assignments
                        ],
                        total_assigned=total_hours,
                        available_hours=available,
                        overallocation=total_hours - available,
                    )
                )

            current += timedelta(days=1)

        return conflicts

    async def _get_cross_program_assignments(
        self,
        resource_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Get all assignments for a resource across all programs."""
        query = (
            select(ResourceAssignment)
            .options(selectinload(ResourceAssignment.activity))
            .where(ResourceAssignment.resource_id == resource_id)
            .where(ResourceAssignment.deleted_at.is_(None))
            .where(
                (ResourceAssignment.start_date <= end_date)
                | (ResourceAssignment.start_date.is_(None))
            )
            .where(
                (ResourceAssignment.finish_date >= start_date)
                | (ResourceAssignment.finish_date.is_(None))
            )
        )
        result = await self.db.execute(query)
        assignments = result.scalars().all()

        return [
            {
                "program_id": a.activity.program_id if a.activity else None,
                "activity_id": a.activity_id,
                "start_date": a.start_date or (a.activity.early_start if a.activity else None),
                "end_date": a.finish_date or (a.activity.early_finish if a.activity else None),
                "units": a.units,
            }
            for a in assignments
        ]

    async def _detect_conflicts(
        self,
        resource: Resource,
        assignments: list[dict[str, Any]],
        start_date: date,
        end_date: date,
        allocation_percentage: Decimal = Decimal("100.00"),
    ) -> list[CrossProgramConflict]:
        """Detect all conflicts for a resource in date range."""
        conflicts = []
        current = start_date

        # Adjust available capacity by allocation percentage
        pool_available = resource.capacity_per_day * (allocation_percentage / Decimal("100"))

        while current <= end_date:
            # Get assignments active on this date
            daily = [
                a
                for a in assignments
                if a["start_date"] and a["end_date"] and a["start_date"] <= current <= a["end_date"]
            ]

            if len(daily) <= 1:
                current += timedelta(days=1)
                continue

            # Check for overallocation
            total = sum(
                (Decimal(str(a["units"])) * resource.capacity_per_day for a in daily),
                Decimal("0"),
            )

            if total > pool_available:
                conflicts.append(
                    CrossProgramConflict(
                        resource_id=resource.id,
                        resource_name=resource.name,
                        conflict_date=current,
                        programs_involved=[
                            {
                                "program_id": str(a["program_id"]),
                                "assigned_hours": float(
                                    Decimal(str(a["units"])) * resource.capacity_per_day
                                ),
                            }
                            for a in daily
                        ],
                        total_assigned=total,
                        available_hours=pool_available,
                        overallocation=total - pool_available,
                    )
                )

            current += timedelta(days=1)

        return conflicts
