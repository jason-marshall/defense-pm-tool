"""Repository for Baseline model with snapshot creation."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from src.models.activity import Activity
from src.models.baseline import Baseline
from src.models.dependency import Dependency
from src.models.wbs import WBSElement
from src.repositories.base import BaseRepository


class BaselineRepository(BaseRepository[Baseline]):
    """Repository for Baseline CRUD operations and snapshot creation."""

    model = Baseline

    async def get_by_program(
        self,
        program_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> list[Baseline]:
        """Get all baselines for a program, ordered by version."""
        query = select(self.model).where(self.model.program_id == program_id)

        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))

        query = query.order_by(self.model.version.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_program(
        self,
        program_id: UUID,
        include_deleted: bool = False,
    ) -> int:
        """Count baselines for a program."""
        query = (
            select(func.count()).select_from(self.model).where(self.model.program_id == program_id)
        )

        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_latest_version(self, program_id: UUID) -> int:
        """Get the latest baseline version number for a program."""
        query = (
            select(func.max(self.model.version))
            .where(self.model.program_id == program_id)
            .where(self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_approved_baseline(self, program_id: UUID) -> Baseline | None:
        """Get the approved (PMB) baseline for a program."""
        query = (
            select(self.model)
            .where(self.model.program_id == program_id)
            .where(self.model.is_approved.is_(True))
            .where(self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_snapshot(
        self,
        program_id: UUID,
        name: str,
        description: str | None,
        created_by_id: UUID,
        include_schedule: bool = True,
        include_cost: bool = True,
        include_wbs: bool = True,
    ) -> Baseline:
        """
        Create a new baseline snapshot from current program data.

        This captures the current state of activities, dependencies,
        WBS elements, and cost data into immutable snapshot fields.

        Args:
            program_id: Program to snapshot
            name: Name for this baseline
            description: Optional description
            created_by_id: User creating the baseline
            include_schedule: Whether to snapshot schedule data
            include_cost: Whether to snapshot cost data
            include_wbs: Whether to snapshot WBS data

        Returns:
            Created Baseline with snapshot data
        """
        # Get next version number
        next_version = (await self.get_latest_version(program_id)) + 1

        # Build snapshots
        schedule_snapshot = None
        cost_snapshot = None
        wbs_snapshot = None
        total_bac = Decimal("0.00")
        scheduled_finish = None
        activity_count = 0
        wbs_count = 0

        if include_schedule:
            (
                schedule_snapshot,
                activity_count,
                scheduled_finish,
            ) = await self._build_schedule_snapshot(program_id)

        if include_wbs or include_cost:
            wbs_snapshot, cost_snapshot, wbs_count, total_bac = await self._build_wbs_cost_snapshot(
                program_id, include_wbs, include_cost
            )

        # Create baseline
        baseline = Baseline(
            program_id=program_id,
            name=name,
            version=next_version,
            description=description,
            schedule_snapshot=schedule_snapshot,
            cost_snapshot=cost_snapshot,
            wbs_snapshot=wbs_snapshot,
            total_bac=total_bac,
            scheduled_finish=scheduled_finish,
            activity_count=activity_count,
            wbs_count=wbs_count,
            created_by_id=created_by_id,
        )

        self.session.add(baseline)
        await self.session.flush()
        return baseline

    async def approve_baseline(
        self,
        baseline_id: UUID,
        approved_by_id: UUID,
    ) -> Baseline | None:
        """
        Approve a baseline as the Performance Measurement Baseline (PMB).

        This unapproves any previously approved baseline for the same program.

        Args:
            baseline_id: Baseline to approve
            approved_by_id: User approving

        Returns:
            The approved baseline, or None if not found
        """
        baseline = await self.get(baseline_id)
        if not baseline:
            return None

        # Unapprove any existing approved baseline for this program
        existing_approved = await self.get_approved_baseline(baseline.program_id)
        if existing_approved and existing_approved.id != baseline_id:
            existing_approved.is_approved = False
            existing_approved.approved_at = None
            existing_approved.approved_by_id = None

        # Approve this baseline
        baseline.is_approved = True
        baseline.approved_at = datetime.now()
        baseline.approved_by_id = approved_by_id

        await self.session.flush()
        return baseline

    async def _build_schedule_snapshot(
        self, program_id: UUID
    ) -> tuple[dict[str, Any] | None, int, Any]:
        """Build schedule snapshot from current activities and dependencies."""
        # Get activities
        activity_query = (
            select(Activity)
            .where(Activity.program_id == program_id)
            .where(Activity.deleted_at.is_(None))
            .order_by(Activity.code)
        )
        activity_result = await self.session.execute(activity_query)
        activities = list(activity_result.scalars().all())

        if not activities:
            return None, 0, None

        # Get dependencies for these activities
        activity_ids = [a.id for a in activities]
        dependency_query = (
            select(Dependency)
            .where(
                Dependency.predecessor_id.in_(activity_ids)
                | Dependency.successor_id.in_(activity_ids)
            )
            .where(Dependency.deleted_at.is_(None))
        )
        dependency_result = await self.session.execute(dependency_query)
        dependencies = list(dependency_result.scalars().all())

        # Build activity snapshots
        activity_snapshots = []
        critical_path_ids = []
        project_finish = None

        for activity in activities:
            activity_snapshots.append(
                {
                    "id": str(activity.id),
                    "code": activity.code,
                    "name": activity.name,
                    "duration": activity.duration,
                    "planned_start": activity.planned_start.isoformat()
                    if activity.planned_start
                    else None,
                    "planned_finish": activity.planned_finish.isoformat()
                    if activity.planned_finish
                    else None,
                    "early_start": activity.early_start.isoformat()
                    if activity.early_start
                    else None,
                    "early_finish": activity.early_finish.isoformat()
                    if activity.early_finish
                    else None,
                    "late_start": activity.late_start.isoformat() if activity.late_start else None,
                    "late_finish": activity.late_finish.isoformat()
                    if activity.late_finish
                    else None,
                    "total_float": activity.total_float,
                    "is_critical": activity.is_critical,
                    "budgeted_cost": str(activity.budgeted_cost),
                    "percent_complete": str(activity.percent_complete),
                    "ev_method": activity.ev_method,
                }
            )

            if activity.is_critical:
                critical_path_ids.append(str(activity.id))

            # Track project finish date
            if activity.early_finish and (
                project_finish is None or activity.early_finish > project_finish
            ):
                project_finish = activity.early_finish

        # Build dependency snapshots
        dependency_snapshots = [
            {
                "predecessor_id": str(dep.predecessor_id),
                "successor_id": str(dep.successor_id),
                "dependency_type": dep.dependency_type,
                "lag": dep.lag,
            }
            for dep in dependencies
        ]

        # Calculate project duration
        project_duration = None
        if project_finish:
            # Find earliest start
            earliest_start = min((a.early_start for a in activities if a.early_start), default=None)
            if earliest_start:
                project_duration = (project_finish - earliest_start).days

        schedule_snapshot = {
            "activities": activity_snapshots,
            "dependencies": dependency_snapshots,
            "critical_path_ids": critical_path_ids,
            "project_duration": project_duration,
            "project_finish": project_finish.isoformat() if project_finish else None,
        }

        return schedule_snapshot, len(activities), project_finish

    async def _build_wbs_cost_snapshot(
        self,
        program_id: UUID,
        include_wbs: bool,
        include_cost: bool,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, int, Decimal]:
        """Build WBS and cost snapshots from current data."""
        # Get WBS elements
        wbs_query = (
            select(WBSElement)
            .where(WBSElement.program_id == program_id)
            .where(WBSElement.deleted_at.is_(None))
            .order_by(WBSElement.path)
        )
        wbs_result = await self.session.execute(wbs_query)
        wbs_elements = list(wbs_result.scalars().all())

        if not wbs_elements:
            return None, None, 0, Decimal("0.00")

        wbs_snapshots = []
        total_bac = Decimal("0.00")

        for wbs in wbs_elements:
            wbs_snapshots.append(
                {
                    "id": str(wbs.id),
                    "wbs_code": wbs.wbs_code,
                    "name": wbs.name,
                    "parent_id": str(wbs.parent_id) if wbs.parent_id else None,
                    "path": str(wbs.path),
                    "budgeted_cost": str(wbs.budget_at_completion),
                }
            )
            total_bac += wbs.budget_at_completion

        wbs_snapshot = {"wbs_elements": wbs_snapshots} if include_wbs else None
        cost_snapshot = (
            {
                "wbs_elements": wbs_snapshots,
                "total_bac": str(total_bac),
                "time_phased_bcws": None,  # To be implemented with EVMS periods
            }
            if include_cost
            else None
        )

        return wbs_snapshot, cost_snapshot, len(wbs_elements), total_bac
