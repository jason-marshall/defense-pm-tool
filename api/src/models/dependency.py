"""Dependency model representing relationships between activities."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import DependencyType

if TYPE_CHECKING:
    from src.models.activity import Activity


class Dependency(Base):
    """
    Represents a dependency relationship between two activities.

    Dependencies define the logical relationships between activities
    and are used by the CPM engine to calculate schedule dates.
    Each dependency has a type (FS, SS, FF, SF) and optional lag/lead.

    Attributes:
        predecessor_id: FK to the activity that must occur first
        successor_id: FK to the activity that depends on predecessor
        dependency_type: Type of dependency relationship
        lag_days: Delay in days (positive) or lead (negative)

    Example:
        # Activity B starts 2 days after Activity A finishes
        dep = Dependency(
            predecessor_id=activity_a.id,
            successor_id=activity_b.id,
            dependency_type=DependencyType.FS,
            lag_days=2
        )
    """

    __tablename__ = "dependencies"

    # Foreign keys to activities
    predecessor_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to predecessor activity",
    )

    successor_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to successor activity",
    )

    # Dependency type using PostgreSQL enum
    dependency_type: Mapped[DependencyType] = mapped_column(
        PgEnum(DependencyType, name="dependency_type", create_type=True),
        default=DependencyType.FS,
        nullable=False,
        comment="Type of dependency (FS, SS, FF, SF)",
    )

    # Lag/lead in working days
    lag_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Lag (positive) or lead (negative) in working days",
    )

    # Relationships
    predecessor: Mapped["Activity"] = relationship(
        "Activity",
        foreign_keys=[predecessor_id],
        back_populates="successor_links",
    )

    successor: Mapped["Activity"] = relationship(
        "Activity",
        foreign_keys=[successor_id],
        back_populates="predecessor_links",
    )

    # Table-level configuration
    __table_args__ = (
        # Unique constraint: only one dependency between any two activities
        UniqueConstraint(
            "predecessor_id",
            "successor_id",
            name="uq_dependencies_predecessor_successor",
        ),
        # Index for finding all dependencies for an activity
        Index(
            "ix_dependencies_activities",
            "predecessor_id",
            "successor_id",
        ),
        # Partial index for active dependencies only
        Index(
            "ix_dependencies_active",
            "predecessor_id",
            "successor_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"comment": "Activity dependencies for CPM scheduling"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<Dependency(id={self.id}, "
            f"pred={self.predecessor_id}, succ={self.successor_id}, "
            f"type={self.dependency_type.value}, lag={self.lag_days})>"
        )

    @property
    def has_lag(self) -> bool:
        """Check if dependency has non-zero lag."""
        return self.lag_days != 0

    @property
    def has_lead(self) -> bool:
        """Check if dependency has lead time (negative lag)."""
        return self.lag_days < 0

    def calculate_successor_constraint(
        self,
        predecessor_es: int,
        predecessor_ef: int,
    ) -> int:
        """
        Calculate the constraint date for successor based on dependency type.

        Args:
            predecessor_es: Predecessor's early start (in days from project start)
            predecessor_ef: Predecessor's early finish (in days from project start)

        Returns:
            The earliest date (in days) the successor can start or finish
            depending on the dependency type.

        Note:
            For FS/SS types, returns constraint for successor's ES
            For FF/SF types, returns constraint for successor's EF
        """
        match self.dependency_type:
            case DependencyType.FS:
                # Successor ES = Predecessor EF + lag
                return predecessor_ef + self.lag_days
            case DependencyType.SS:
                # Successor ES = Predecessor ES + lag
                return predecessor_es + self.lag_days
            case DependencyType.FF:
                # Successor EF = Predecessor EF + lag
                return predecessor_ef + self.lag_days
            case DependencyType.SF:
                # Successor EF = Predecessor ES + lag
                return predecessor_es + self.lag_days
