"""Repository for Monte Carlo simulation operations."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.simulation import SimulationConfig, SimulationResult, SimulationStatus
from src.repositories.base import BaseRepository


class SimulationConfigRepository(BaseRepository[SimulationConfig]):
    """Repository for SimulationConfig CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(SimulationConfig, session)

    async def get_by_program(
        self,
        program_id: UUID,
        include_results: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SimulationConfig]:
        """
        Get all simulation configs for a program.

        Args:
            program_id: Program ID to filter by
            include_results: Whether to eagerly load results
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of SimulationConfig instances
        """
        query = (
            select(SimulationConfig)
            .where(SimulationConfig.program_id == program_id)
            .where(SimulationConfig.deleted_at.is_(None))
            .order_by(SimulationConfig.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        if include_results:
            query = query.options(selectinload(SimulationConfig.results))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_scenario(
        self,
        scenario_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SimulationConfig]:
        """Get all simulation configs for a scenario."""
        result = await self.session.execute(
            select(SimulationConfig)
            .where(SimulationConfig.scenario_id == scenario_id)
            .where(SimulationConfig.deleted_at.is_(None))
            .order_by(SimulationConfig.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_with_results(self, config_id: UUID) -> SimulationConfig | None:
        """Get a simulation config with its results eagerly loaded."""
        result = await self.session.execute(
            select(SimulationConfig)
            .where(SimulationConfig.id == config_id)
            .where(SimulationConfig.deleted_at.is_(None))
            .options(selectinload(SimulationConfig.results))
        )
        return result.scalar_one_or_none()

    async def create_config(
        self,
        program_id: UUID,
        name: str,
        created_by_id: UUID,
        iterations: int = 1000,
        activity_distributions: dict[str, Any] | None = None,
        cost_distributions: dict[str, Any] | None = None,
        scenario_id: UUID | None = None,
        description: str | None = None,
    ) -> SimulationConfig:
        """
        Create a new simulation configuration.

        Args:
            program_id: Program to associate with
            name: Configuration name
            created_by_id: User creating the config
            iterations: Number of Monte Carlo iterations
            activity_distributions: Activity duration distributions
            cost_distributions: Cost distributions (optional)
            scenario_id: Optional scenario to simulate
            description: Optional description

        Returns:
            Created SimulationConfig instance
        """
        config = SimulationConfig(
            program_id=program_id,
            scenario_id=scenario_id,
            name=name,
            description=description,
            iterations=iterations,
            activity_distributions=activity_distributions or {},
            cost_distributions=cost_distributions,
            created_by_id=created_by_id,
        )

        self.session.add(config)
        await self.session.flush()
        return config


class SimulationResultRepository(BaseRepository[SimulationResult]):
    """Repository for SimulationResult CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(SimulationResult, session)

    async def get_by_config(
        self,
        config_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SimulationResult]:
        """Get all results for a simulation config."""
        result = await self.session.execute(
            select(SimulationResult)
            .where(SimulationResult.config_id == config_id)
            .where(SimulationResult.deleted_at.is_(None))
            .order_by(SimulationResult.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_by_config(self, config_id: UUID) -> SimulationResult | None:
        """Get the most recent result for a config."""
        result = await self.session.execute(
            select(SimulationResult)
            .where(SimulationResult.config_id == config_id)
            .where(SimulationResult.deleted_at.is_(None))
            .order_by(SimulationResult.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_completed_by_config(self, config_id: UUID) -> SimulationResult | None:
        """Get the most recent completed result for a config."""
        result = await self.session.execute(
            select(SimulationResult)
            .where(SimulationResult.config_id == config_id)
            .where(SimulationResult.status == SimulationStatus.COMPLETED)
            .where(SimulationResult.deleted_at.is_(None))
            .order_by(SimulationResult.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_result(
        self,
        config_id: UUID,
        seed: int | None = None,
    ) -> SimulationResult:
        """
        Create a new simulation result record.

        Args:
            config_id: Configuration to run
            seed: Optional random seed

        Returns:
            Created SimulationResult instance (pending status)
        """
        result = SimulationResult(
            config_id=config_id,
            status=SimulationStatus.PENDING,
            random_seed=seed,
        )

        self.session.add(result)
        await self.session.flush()
        return result

    async def mark_running(self, result_id: UUID) -> SimulationResult | None:
        """Mark a simulation as running."""
        result = await self.session.execute(
            select(SimulationResult).where(SimulationResult.id == result_id)
        )
        sim_result = result.scalar_one_or_none()

        if sim_result:
            sim_result.status = SimulationStatus.RUNNING
            sim_result.started_at = datetime.now(UTC)
            await self.session.flush()

        return sim_result

    async def mark_completed(
        self,
        result_id: UUID,
        duration_results: dict[str, float],
        cost_results: dict[str, float] | None,
        duration_histogram: dict[str, list[float]] | None,
        cost_histogram: dict[str, list[float]] | None,
        activity_results: dict[str, dict[str, float]] | None,
        iterations_completed: int,
    ) -> SimulationResult | None:
        """
        Mark a simulation as completed with results.

        Args:
            result_id: Result ID to update
            duration_results: Duration percentiles and stats
            cost_results: Cost percentiles and stats (optional)
            duration_histogram: Duration histogram data
            cost_histogram: Cost histogram data (optional)
            activity_results: Per-activity statistics (optional)
            iterations_completed: Number of iterations completed

        Returns:
            Updated SimulationResult instance
        """
        result = await self.session.execute(
            select(SimulationResult).where(SimulationResult.id == result_id)
        )
        sim_result = result.scalar_one_or_none()

        if sim_result:
            sim_result.status = SimulationStatus.COMPLETED
            sim_result.completed_at = datetime.now(UTC)
            sim_result.iterations_completed = iterations_completed
            sim_result.duration_results = duration_results
            sim_result.cost_results = cost_results
            sim_result.duration_histogram = duration_histogram
            sim_result.cost_histogram = cost_histogram
            sim_result.activity_results = activity_results
            await self.session.flush()

        return sim_result

    async def mark_failed(
        self,
        result_id: UUID,
        error_message: str,
    ) -> SimulationResult | None:
        """Mark a simulation as failed."""
        result = await self.session.execute(
            select(SimulationResult).where(SimulationResult.id == result_id)
        )
        sim_result = result.scalar_one_or_none()

        if sim_result:
            sim_result.status = SimulationStatus.FAILED
            sim_result.completed_at = datetime.now(UTC)
            sim_result.error_message = error_message
            await self.session.flush()

        return sim_result

    async def update_progress(
        self,
        result_id: UUID,
        iterations_completed: int,
    ) -> SimulationResult | None:
        """Update the progress of a running simulation."""
        result = await self.session.execute(
            select(SimulationResult).where(SimulationResult.id == result_id)
        )
        sim_result = result.scalar_one_or_none()

        if sim_result:
            sim_result.iterations_completed = iterations_completed
            await self.session.flush()

        return sim_result
