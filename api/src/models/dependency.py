"""Dependency model representing relationships between activities."""

from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.activity import Activity


class DependencyType(str, Enum):
    """
    Types of dependencies between activities.

    FS (Finish-to-Start): Successor starts after predecessor finishes
    SS (Start-to-Start): Successor starts after predecessor starts
    FF (Finish-to-Finish): Successor finishes after predecessor finishes
    SF (Start-to-Finish): Successor finishes after predecessor starts
    """

    FS = "FS"  # Finish-to-Start (most common)
    SS = "SS"  # Start-to-Start
    FF = "FF"  # Finish-to-Finish
    SF = "SF"  # Start-to-Finish (rare)


class Dependency(Base):
    """
    Represents a dependency relationship between two activities.

    Dependencies define the logical relationships between activities
    and are used by the CPM engine to calculate schedule dates.
    """

    __tablename__ = "dependencies"

    # Foreign keys
    predecessor_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
    )
    successor_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Dependency attributes
    dependency_type: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        default=DependencyType.FS.value,
    )
    lag: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Lag in working days (positive=delay, negative=lead)",
    )

    # Relationships
    predecessor: Mapped["Activity"] = relationship(
        "Activity",
        foreign_keys=[predecessor_id],
        back_populates="successor_dependencies",
    )
    successor: Mapped["Activity"] = relationship(
        "Activity",
        foreign_keys=[successor_id],
        back_populates="predecessor_dependencies",
    )

    @property
    def type_enum(self) -> DependencyType:
        """Get the dependency type as enum."""
        return DependencyType(self.dependency_type)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<Dependency(predecessor={self.predecessor_id}, "
            f"successor={self.successor_id}, type={self.dependency_type}, "
            f"lag={self.lag})>"
        )
