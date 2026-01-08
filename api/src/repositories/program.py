"""Repository for Program model."""

from sqlalchemy import select
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
            select(Program).where(Program.code == code)
        )
        return result.scalar_one_or_none()

    async def code_exists(self, code: str, exclude_id: str | None = None) -> bool:
        """Check if a program code already exists."""
        query = select(Program).where(Program.code == code)
        if exclude_id:
            query = query.where(Program.id != exclude_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
