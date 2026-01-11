"""Repository for Program model."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.program import Program
from src.repositories.base import BaseRepository


class ProgramRepository(BaseRepository[Program]):
    """Repository for Program CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with Program model."""
        super().__init__(Program, session)

    async def get_by_code(self, code: str) -> Program | None:
        """Get a program by its unique code."""
        result = await self.session.execute(
            select(Program).where(Program.code == code).where(Program.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def code_exists(self, code: str, exclude_id: UUID | None = None) -> bool:
        """Check if a program code already exists."""
        query = select(Program).where(Program.code == code).where(Program.deleted_at.is_(None))
        if exclude_id:
            query = query.where(Program.id != exclude_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_by_owner(
        self,
        owner_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Program], int]:
        """
        Get programs owned by a specific user.

        Args:
            owner_id: UUID of the program owner
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of programs, total count)
        """
        base_query = (
            select(Program).where(Program.owner_id == owner_id).where(Program.deleted_at.is_(None))
        )

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await self.session.execute(count_query)
        total: int = count_result.scalar_one()

        # Get paginated results
        query = base_query.order_by(Program.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        programs = list(result.scalars().all())

        return programs, total

    async def user_owns_program(self, program_id: UUID, user_id: UUID) -> bool:
        """
        Check if a user owns a specific program.

        Args:
            program_id: UUID of the program
            user_id: UUID of the user

        Returns:
            True if the user owns the program, False otherwise
        """
        query = (
            select(func.count())
            .select_from(Program)
            .where(Program.id == program_id)
            .where(Program.owner_id == user_id)
            .where(Program.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        count: int = result.scalar_one()
        return count > 0

    async def get_accessible_programs(
        self,
        user_id: UUID,
        is_admin: bool = False,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Program], int]:
        """
        Get programs accessible to a user.

        Admins can see all programs. Regular users only see their own.

        Args:
            user_id: UUID of the user
            is_admin: Whether the user is an admin
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of programs, total count)
        """
        if is_admin:
            return await self.get_all(skip=skip, limit=limit, order_by="-created_at")

        return await self.get_by_owner(user_id, skip=skip, limit=limit)
