"""Repository for EVMS Period models."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.evms_period import EVMSPeriod, EVMSPeriodData, PeriodStatus
from src.repositories.base import BaseRepository


class EVMSPeriodRepository(BaseRepository[EVMSPeriod]):
    """Repository for EVMS Period CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with EVMSPeriod model."""
        super().__init__(EVMSPeriod, session)

    async def get_by_program(
        self,
        program_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        status: PeriodStatus | None = None,
    ) -> list[EVMSPeriod]:
        """Get all EVMS periods for a program."""
        query = (
            select(EVMSPeriod)
            .where(EVMSPeriod.program_id == program_id)
            .where(EVMSPeriod.deleted_at.is_(None))
        )

        if status:
            query = query.where(EVMSPeriod.status == status)

        query = query.order_by(EVMSPeriod.period_start.desc())
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_period(self, program_id: UUID) -> EVMSPeriod | None:
        """Get the most recent EVMS period for a program."""
        result = await self.session.execute(
            select(EVMSPeriod)
            .where(EVMSPeriod.program_id == program_id)
            .where(EVMSPeriod.deleted_at.is_(None))
            .order_by(EVMSPeriod.period_end.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_with_data(self, period_id: UUID) -> EVMSPeriod | None:
        """Get an EVMS period with all its period data loaded."""
        result = await self.session.execute(
            select(EVMSPeriod)
            .where(EVMSPeriod.id == period_id)
            .where(EVMSPeriod.deleted_at.is_(None))
            .options(selectinload(EVMSPeriod.period_data))
        )
        return result.scalar_one_or_none()

    async def get_by_date_range(
        self,
        program_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[EVMSPeriod]:
        """Get periods that overlap with the given date range."""
        result = await self.session.execute(
            select(EVMSPeriod)
            .where(EVMSPeriod.program_id == program_id)
            .where(EVMSPeriod.deleted_at.is_(None))
            .where(EVMSPeriod.period_start <= end_date)
            .where(EVMSPeriod.period_end >= start_date)
            .order_by(EVMSPeriod.period_start)
        )
        return list(result.scalars().all())

    async def period_exists(
        self,
        program_id: UUID,
        period_start: date,
        period_end: date,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if a period with the same dates already exists."""
        query = (
            select(func.count())
            .select_from(EVMSPeriod)
            .where(EVMSPeriod.program_id == program_id)
            .where(EVMSPeriod.period_start == period_start)
            .where(EVMSPeriod.period_end == period_end)
            .where(EVMSPeriod.deleted_at.is_(None))
        )

        if exclude_id:
            query = query.where(EVMSPeriod.id != exclude_id)

        result = await self.session.execute(query)
        count: int = result.scalar_one()
        return count > 0

    async def update_cumulative_totals(self, period_id: UUID) -> EVMSPeriod | None:
        """Update cumulative totals from period data."""
        period = await self.get_with_data(period_id)
        if not period:
            return None

        # Sum up all period data
        total_bcws = Decimal("0.00")
        total_bcwp = Decimal("0.00")
        total_acwp = Decimal("0.00")

        for data in period.period_data:
            total_bcws += data.cumulative_bcws
            total_bcwp += data.cumulative_bcwp
            total_acwp += data.cumulative_acwp

        period.cumulative_bcws = total_bcws
        period.cumulative_bcwp = total_bcwp
        period.cumulative_acwp = total_acwp

        await self.session.flush()
        return period


class EVMSPeriodDataRepository(BaseRepository[EVMSPeriodData]):
    """Repository for EVMS Period Data CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with EVMSPeriodData model."""
        super().__init__(EVMSPeriodData, session)

    async def get_by_period(
        self,
        period_id: UUID,
        *,
        skip: int = 0,
        limit: int = 1000,
    ) -> list[EVMSPeriodData]:
        """Get all EVMS data for a period."""
        result = await self.session.execute(
            select(EVMSPeriodData)
            .where(EVMSPeriodData.period_id == period_id)
            .where(EVMSPeriodData.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_wbs(
        self,
        wbs_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EVMSPeriodData]:
        """Get all EVMS data for a WBS element across periods."""
        result = await self.session.execute(
            select(EVMSPeriodData)
            .where(EVMSPeriodData.wbs_id == wbs_id)
            .where(EVMSPeriodData.deleted_at.is_(None))
            .order_by(EVMSPeriodData.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_period_and_wbs(
        self,
        period_id: UUID,
        wbs_id: UUID,
    ) -> EVMSPeriodData | None:
        """Get EVMS data for a specific period and WBS element."""
        result = await self.session.execute(
            select(EVMSPeriodData)
            .where(EVMSPeriodData.period_id == period_id)
            .where(EVMSPeriodData.wbs_id == wbs_id)
            .where(EVMSPeriodData.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def data_exists(
        self,
        period_id: UUID,
        wbs_id: UUID,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if data for this period/WBS combination already exists."""
        query = (
            select(func.count())
            .select_from(EVMSPeriodData)
            .where(EVMSPeriodData.period_id == period_id)
            .where(EVMSPeriodData.wbs_id == wbs_id)
            .where(EVMSPeriodData.deleted_at.is_(None))
        )

        if exclude_id:
            query = query.where(EVMSPeriodData.id != exclude_id)

        result = await self.session.execute(query)
        count: int = result.scalar_one()
        return count > 0

    async def get_previous_period_data(
        self,
        program_id: UUID,
        wbs_id: UUID,
        before_date: date,
    ) -> EVMSPeriodData | None:
        """Get the most recent period data for a WBS before a given date."""
        result = await self.session.execute(
            select(EVMSPeriodData)
            .join(EVMSPeriod)
            .where(EVMSPeriod.program_id == program_id)
            .where(EVMSPeriodData.wbs_id == wbs_id)
            .where(EVMSPeriod.period_end < before_date)
            .where(EVMSPeriodData.deleted_at.is_(None))
            .order_by(EVMSPeriod.period_end.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def bulk_create_for_period(
        self,
        period_id: UUID,
        data_items: list[dict[str, object]],
    ) -> list[EVMSPeriodData]:
        """Create multiple period data records."""
        records = []
        for item in data_items:
            item["period_id"] = period_id
            record = EVMSPeriodData(**item)
            record.calculate_metrics()
            self.session.add(record)
            records.append(record)

        await self.session.flush()
        for record in records:
            await self.session.refresh(record)

        return records
