"""Data access layer - Repository pattern implementation."""

from typing import Generic, TypeVar, Type, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Base


ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[ModelT], session: AsyncSession):
        """Initialize repository."""
        self.model = model
        self.session = session

    async def get(self, id: Any) -> ModelT | None:
        """Get entity by ID."""
        return await self.session.get(self.model, id)

    async def list(
        self, *, skip: int = 0, limit: int = 100
    ) -> list[ModelT]:
        """List entities with pagination."""
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelT:
        """Create new entity."""
        entity = self.model(**kwargs)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: ModelT, **kwargs: Any) -> ModelT:
        """Update existing entity."""
        for key, value in kwargs.items():
            setattr(entity, key, value)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        """Delete entity."""
        await self.session.delete(entity)
        await self.session.commit()
