"""Repository for VarianceExplanation model."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.variance_explanation import VarianceExplanation
from src.repositories.base import BaseRepository


class VarianceExplanationRepository(BaseRepository[VarianceExplanation]):
    """
    Repository for variance explanation CRUD operations.

    Provides methods for managing variance explanations per DFARS requirements.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__(VarianceExplanation, session)

    async def get_by_program(
        self,
        program_id: UUID,
        variance_type: str | None = None,
        include_deleted: bool = False,
    ) -> list[VarianceExplanation]:
        """
        Get all variance explanations for a program.

        Args:
            program_id: Program ID
            variance_type: Optional filter for 'schedule' or 'cost'
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of variance explanations
        """
        query = select(VarianceExplanation).where(VarianceExplanation.program_id == program_id)

        if variance_type:
            query = query.where(VarianceExplanation.variance_type == variance_type)

        query = self._apply_soft_delete_filter(query, include_deleted)
        query = query.order_by(VarianceExplanation.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_period(
        self,
        period_id: UUID,
        include_deleted: bool = False,
    ) -> list[VarianceExplanation]:
        """
        Get variance explanations for a specific period.

        Args:
            period_id: EVMS Period ID
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of variance explanations for the period
        """
        query = select(VarianceExplanation).where(VarianceExplanation.period_id == period_id)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = query.order_by(VarianceExplanation.variance_percent.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_wbs(
        self,
        wbs_id: UUID,
        include_deleted: bool = False,
    ) -> list[VarianceExplanation]:
        """
        Get variance explanations for a specific WBS element.

        Args:
            wbs_id: WBS Element ID
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of variance explanations for the WBS element
        """
        query = select(VarianceExplanation).where(VarianceExplanation.wbs_id == wbs_id)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = query.order_by(VarianceExplanation.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_significant_variances(
        self,
        program_id: UUID,
        threshold_percent: Decimal = Decimal("10"),
        include_deleted: bool = False,
    ) -> list[VarianceExplanation]:
        """
        Get variance explanations for significant variances (above threshold).

        Args:
            program_id: Program ID
            threshold_percent: Minimum variance percent to include
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of variance explanations exceeding threshold
        """
        query = select(VarianceExplanation).where(
            VarianceExplanation.program_id == program_id,
            VarianceExplanation.variance_percent >= threshold_percent,
        )
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = query.order_by(VarianceExplanation.variance_percent.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())
