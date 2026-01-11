"""Repository for WBS Element model."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.wbs import WBSElement
from src.repositories.base import BaseRepository


class WBSElementRepository(BaseRepository[WBSElement]):
    """Repository for WBS Element CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with WBSElement model."""
        super().__init__(WBSElement, session)

    async def get_by_program(
        self,
        program_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[WBSElement]:
        """Get all WBS elements for a program."""
        result = await self.session.execute(
            select(WBSElement)
            .where(WBSElement.program_id == program_id)
            .offset(skip)
            .limit(limit)
            .order_by(WBSElement.path)
        )
        return list(result.scalars().all())

    async def get_root_elements(self, program_id: UUID) -> list[WBSElement]:
        """Get root-level WBS elements (no parent)."""
        result = await self.session.execute(
            select(WBSElement)
            .where(
                WBSElement.program_id == program_id,
                WBSElement.parent_id.is_(None),
            )
            .order_by(WBSElement.wbs_code)
        )
        return list(result.scalars().all())

    async def get_children(self, parent_id: UUID) -> list[WBSElement]:
        """Get direct children of a WBS element."""
        result = await self.session.execute(
            select(WBSElement)
            .where(WBSElement.parent_id == parent_id)
            .order_by(WBSElement.wbs_code)
        )
        return list(result.scalars().all())

    async def get_with_children(self, id: UUID) -> WBSElement | None:
        """Get a WBS element with its children loaded."""
        result = await self.session.execute(
            select(WBSElement).where(WBSElement.id == id).options(selectinload(WBSElement.children))
        )
        return result.scalar_one_or_none()

    async def get_tree(self, program_id: UUID) -> list[WBSElement]:
        """Get full WBS tree for a program with children loaded."""
        result = await self.session.execute(
            select(WBSElement)
            .where(
                WBSElement.program_id == program_id,
                WBSElement.parent_id.is_(None),
            )
            .options(selectinload(WBSElement.children, recursion_depth=10))
            .order_by(WBSElement.wbs_code)
        )
        return list(result.scalars().all())

    async def get_by_code(
        self,
        program_id: UUID,
        code: str,
    ) -> WBSElement | None:
        """Get a WBS element by its code within a program."""
        result = await self.session.execute(
            select(WBSElement).where(
                WBSElement.program_id == program_id,
                WBSElement.wbs_code == code,
            )
        )
        return result.scalar_one_or_none()

    async def get_descendants(self, element_id: UUID) -> list[WBSElement]:
        """Get all descendants of a WBS element using path prefix match."""
        parent = await self.get_by_id(element_id)
        if not parent:
            return []

        result = await self.session.execute(
            select(WBSElement)
            .where(WBSElement.path.like(f"{parent.path}.%"))
            .order_by(WBSElement.path)
        )
        return list(result.scalars().all())
