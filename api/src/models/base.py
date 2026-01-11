"""Base SQLAlchemy model with common fields and utilities."""

from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, event, func, inspect
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Provides common functionality:
    - Auto-generated table names from class names (snake_case + plural)
    - UUID primary key with auto-generation
    - Timestamp columns (created_at, updated_at)
    - Soft delete support (deleted_at)
    - Utility methods for serialization
    """

    # Type annotation map for custom types
    type_annotation_map: ClassVar[dict[type, Any]] = {
        UUID: PGUUID(as_uuid=True),
    }

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """
        Auto-generate table name from class name.

        Converts CamelCase to snake_case and adds 's' for plural.
        Examples:
            User -> users
            WBSElement -> wbs_elements
            Activity -> activities
        """
        name = cls.__name__
        # Convert CamelCase to snake_case
        result = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append("_")
            result.append(char.lower())
        snake_name = "".join(result)

        # Handle special plural cases
        if snake_name.endswith("y"):
            return snake_name[:-1] + "ies"
        elif snake_name.endswith("s"):
            return snake_name + "es"
        else:
            return snake_name + "s"

    # Primary key - UUID for global uniqueness and security
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique identifier (UUID v4)",
    )

    # Timestamp columns for auditing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when record was last updated",
    )

    # Soft delete support - records are marked as deleted rather than removed
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
        comment="Timestamp when record was soft-deleted (null = active)",
    )

    @property
    def is_deleted(self) -> bool:
        """Check if the record has been soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark the record as deleted without removing from database."""
        self.deleted_at = datetime.now()

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None

    def to_dict(
        self,
        exclude: set[str] | None = None,
        include_relationships: bool = False,
    ) -> dict[str, Any]:
        """
        Convert model to dictionary.

        Args:
            exclude: Set of column names to exclude
            include_relationships: Whether to include relationship data

        Returns:
            Dictionary representation of the model
        """
        exclude = exclude or set()
        result = {}

        # Get column values
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # Convert UUID to string for JSON serialization
                if isinstance(value, UUID):
                    value = str(value)
                # Convert datetime to ISO format
                elif isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value

        # Optionally include relationships
        if include_relationships:
            mapper = inspect(self.__class__)
            for rel in mapper.relationships:
                if rel.key not in exclude:
                    related = getattr(self, rel.key)
                    if related is not None:
                        if hasattr(related, "__iter__"):
                            result[rel.key] = [item.to_dict(exclude=exclude) for item in related]
                        else:
                            result[rel.key] = related.to_dict(exclude=exclude)

        return result

    def __repr__(self) -> str:
        """Generate a debug-friendly string representation."""
        class_name = self.__class__.__name__
        pk = self.id
        return f"<{class_name}(id={pk})>"


class SoftDeleteMixin:
    """
    Mixin for models that need soft delete functionality.

    Provides helper methods for filtering soft-deleted records.
    Use with Base class that already has deleted_at column.
    """

    @classmethod
    def active_filter(cls) -> Any:
        """Return SQLAlchemy filter for active (non-deleted) records."""
        return cls.deleted_at.is_(None)

    @classmethod
    def deleted_filter(cls) -> Any:
        """Return SQLAlchemy filter for deleted records."""
        return cls.deleted_at.isnot(None)


# Event listener to automatically update updated_at on changes
@event.listens_for(Base, "before_update", propagate=True)
def receive_before_update(mapper: Any, connection: Any, target: Base) -> None:
    """Automatically update the updated_at timestamp before any update."""
    target.updated_at = datetime.now()
