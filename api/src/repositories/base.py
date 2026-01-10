"""Base repository with common CRUD operations and soft delete support."""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import asc, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError
from src.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic repository providing CRUD operations for SQLAlchemy models.

    Features:
    - Soft delete support (sets deleted_at instead of removing)
    - Filter by any column using filters dict
    - Order by any column (prefix with - for descending)
    - Automatic updated_at timestamp on updates
    - Handle IntegrityError for constraint violations
    - All methods properly typed with generics

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(User, session)
    """

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        """
        Initialize repository with model class and database session.

        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session

    def _apply_soft_delete_filter(self, query: Any, include_deleted: bool = False) -> Any:
        """Apply soft delete filter to exclude deleted records."""
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))
        return query

    def _apply_ordering(self, query: Any, order_by: str | None) -> Any:
        """
        Apply ordering to query.

        Args:
            query: SQLAlchemy query
            order_by: Column name, prefix with '-' for descending

        Returns:
            Query with ordering applied
        """
        if order_by:
            if order_by.startswith("-"):
                column_name = order_by[1:]
                direction = desc
            else:
                column_name = order_by
                direction = asc

            if hasattr(self.model, column_name):
                query = query.order_by(direction(getattr(self.model, column_name)))

        return query

    def _apply_filters(self, query: Any, filters: dict[str, Any] | None) -> Any:
        """
        Apply filters to query.

        Args:
            query: SQLAlchemy query
            filters: Dictionary of field:value pairs

        Returns:
            Query with filters applied
        """
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)
        return query

    async def get_by_id(
        self,
        id: UUID,
        include_deleted: bool = False,
    ) -> ModelType | None:
        """
        Get a single record by ID, excluding soft-deleted by default.

        Args:
            id: Record UUID
            include_deleted: Whether to include soft-deleted records

        Returns:
            Model instance or None if not found
        """
        query = select(self.model).where(self.model.id == id)
        query = self._apply_soft_delete_filter(query, include_deleted)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[ModelType], int]:
        """
        Get paginated list with total count.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            filters: Dictionary of field:value pairs to filter by
            order_by: Column name to order by (prefix with '-' for descending)
            include_deleted: Whether to include soft-deleted records

        Returns:
            Tuple of (list of records, total count)
        """
        # Build base query
        query = select(self.model)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = self._apply_filters(query, filters)

        # Get total count before pagination
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Apply ordering and pagination
        query = self._apply_ordering(query, order_by)
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def count(
        self,
        filters: dict[str, Any] | None = None,
        include_deleted: bool = False,
    ) -> int:
        """
        Count records with optional filtering.

        Args:
            filters: Dictionary of field:value pairs to filter by
            include_deleted: Whether to include soft-deleted records

        Returns:
            Number of matching records
        """
        query = select(func.count()).select_from(self.model)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = self._apply_filters(query, filters)

        result = await self.session.execute(query)
        count: int = result.scalar_one()
        return count

    async def create(self, data: dict[str, Any]) -> ModelType:
        """
        Create a new record.

        Args:
            data: Dictionary of field:value pairs

        Returns:
            Created model instance

        Raises:
            ConflictError: If unique constraint is violated
        """
        try:
            db_obj = self.model(**data)
            self.session.add(db_obj)
            await self.session.flush()
            await self.session.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            await self.session.rollback()
            raise ConflictError(
                f"Record violates database constraint: {e.orig}",
                "CONSTRAINT_VIOLATION",
            ) from e

    async def update(
        self,
        db_obj: ModelType,
        data: dict[str, Any],
    ) -> ModelType:
        """
        Update an existing record.

        Args:
            db_obj: Model instance to update
            data: Dictionary of field:value pairs to update

        Returns:
            Updated model instance

        Raises:
            ConflictError: If unique constraint is violated
        """
        try:
            for field, value in data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            # Explicitly update updated_at timestamp
            if hasattr(db_obj, "updated_at"):
                db_obj.updated_at = datetime.now(UTC)

            await self.session.flush()
            await self.session.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            await self.session.rollback()
            raise ConflictError(
                f"Update violates database constraint: {e.orig}",
                "CONSTRAINT_VIOLATION",
            ) from e

    async def update_by_id(
        self,
        id: UUID,
        data: dict[str, Any],
    ) -> ModelType | None:
        """
        Update a record by ID.

        Args:
            id: Record UUID
            data: Dictionary of field:value pairs to update

        Returns:
            Updated model instance or None if not found

        Raises:
            ConflictError: If unique constraint is violated
        """
        db_obj = await self.get_by_id(id)
        if db_obj is None:
            return None
        return await self.update(db_obj, data)

    async def delete(
        self,
        id: UUID,
        soft: bool = True,
    ) -> bool:
        """
        Delete a record (soft delete by default).

        Args:
            id: Record UUID
            soft: If True, sets deleted_at; if False, removes from database

        Returns:
            True if record was deleted, False if not found
        """
        db_obj = await self.get_by_id(id, include_deleted=not soft)
        if db_obj is None:
            return False

        if soft and hasattr(db_obj, "deleted_at"):
            db_obj.deleted_at = datetime.now(UTC)
            await self.session.flush()
        else:
            await self.session.delete(db_obj)
            await self.session.flush()

        return True

    async def hard_delete(self, db_obj: ModelType) -> None:
        """
        Permanently delete a record from database.

        Args:
            db_obj: Model instance to delete
        """
        await self.session.delete(db_obj)
        await self.session.flush()

    async def restore(self, id: UUID) -> ModelType | None:
        """
        Restore a soft-deleted record.

        Args:
            id: Record UUID

        Returns:
            Restored model instance or None if not found
        """
        db_obj = await self.get_by_id(id, include_deleted=True)
        if db_obj is None:
            return None

        if hasattr(db_obj, "deleted_at"):
            db_obj.deleted_at = None
            await self.session.flush()
            await self.session.refresh(db_obj)

        return db_obj

    async def exists(self, id: UUID, include_deleted: bool = False) -> bool:
        """
        Check if a record exists.

        Args:
            id: Record UUID
            include_deleted: Whether to include soft-deleted records

        Returns:
            True if record exists, False otherwise
        """
        query = select(func.count()).select_from(self.model).where(self.model.id == id)
        query = self._apply_soft_delete_filter(query, include_deleted)
        result = await self.session.execute(query)
        count: int = result.scalar_one()
        return count > 0

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[ModelType]:
        """
        Create multiple records efficiently.

        Args:
            items: List of dictionaries with field:value pairs

        Returns:
            List of created model instances

        Raises:
            ConflictError: If any record violates constraints
        """
        if not items:
            return []

        try:
            db_objects = [self.model(**item) for item in items]
            self.session.add_all(db_objects)
            await self.session.flush()

            # Refresh all objects to get generated values
            for db_obj in db_objects:
                await self.session.refresh(db_obj)

            return db_objects
        except IntegrityError as e:
            await self.session.rollback()
            raise ConflictError(
                f"Bulk create violates database constraint: {e.orig}",
                "CONSTRAINT_VIOLATION",
            ) from e

    async def bulk_update(
        self,
        updates: list[tuple[UUID, dict[str, Any]]],
    ) -> int:
        """
        Update multiple records efficiently.

        Args:
            updates: List of (id, data) tuples

        Returns:
            Number of records updated

        Raises:
            ConflictError: If any update violates constraints
        """
        if not updates:
            return 0

        updated_count = 0

        try:
            for record_id, data in updates:
                # Add updated_at timestamp
                if hasattr(self.model, "updated_at"):
                    data["updated_at"] = datetime.now(UTC)

                stmt = update(self.model).where(self.model.id == record_id).values(**data)

                # Add soft delete filter if model supports it
                if hasattr(self.model, "deleted_at"):
                    stmt = stmt.where(self.model.deleted_at.is_(None))

                cursor_result = await self.session.execute(stmt)
                updated_count += cursor_result.rowcount  # type: ignore[attr-defined]

            await self.session.flush()
            return updated_count
        except IntegrityError as e:
            await self.session.rollback()
            raise ConflictError(
                f"Bulk update violates database constraint: {e.orig}",
                "CONSTRAINT_VIOLATION",
            ) from e

    async def bulk_delete(
        self,
        ids: list[UUID],
        soft: bool = True,
    ) -> int:
        """
        Delete multiple records efficiently.

        Args:
            ids: List of record UUIDs
            soft: If True, sets deleted_at; if False, removes from database

        Returns:
            Number of records deleted
        """
        if not ids:
            return 0

        if soft and hasattr(self.model, "deleted_at"):
            stmt = (
                update(self.model)
                .where(self.model.id.in_(ids))
                .where(self.model.deleted_at.is_(None))
                .values(deleted_at=datetime.now(UTC))
            )
            cursor_result = await self.session.execute(stmt)
            await self.session.flush()
            deleted: int = cursor_result.rowcount  # type: ignore[attr-defined]
            return deleted
        else:
            deleted_count = 0
            for record_id in ids:
                if await self.delete(record_id, soft=False):
                    deleted_count += 1
            return deleted_count

    async def find_one(
        self,
        filters: dict[str, Any],
        include_deleted: bool = False,
    ) -> ModelType | None:
        """
        Find a single record matching filters.

        Args:
            filters: Dictionary of field:value pairs
            include_deleted: Whether to include soft-deleted records

        Returns:
            Model instance or None if not found
        """
        query = select(self.model)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = self._apply_filters(query, filters)
        query = query.limit(1)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def find_many(
        self,
        filters: dict[str, Any],
        order_by: str | None = None,
        include_deleted: bool = False,
    ) -> list[ModelType]:
        """
        Find all records matching filters (no pagination).

        Args:
            filters: Dictionary of field:value pairs
            order_by: Column name to order by (prefix with '-' for descending)
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of matching model instances
        """
        query = select(self.model)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = self._apply_filters(query, filters)
        query = self._apply_ordering(query, order_by)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_or_raise(
        self,
        id: UUID,
        include_deleted: bool = False,
    ) -> ModelType:
        """
        Get a record by ID or raise NotFoundError.

        Args:
            id: Record UUID
            include_deleted: Whether to include soft-deleted records

        Returns:
            Model instance

        Raises:
            NotFoundError: If record not found
        """
        db_obj = await self.get_by_id(id, include_deleted)
        if db_obj is None:
            model_name = self.model.__name__
            raise NotFoundError(
                f"{model_name} with id {id} not found",
                f"{model_name.upper()}_NOT_FOUND",
            )
        return db_obj
