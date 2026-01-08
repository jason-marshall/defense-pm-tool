"""Activity model representing a schedulable task."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.dependency import Dependency
    from src.models.program import Program
    from src.models.wbs import WBSElement


class Activity(Base):
    """
    Represents a schedulable activity within a program.

    Activities are the fundamental units of work in CPM scheduling.
    They have durations, dependencies, and are assigned to WBS elements.
    """

    __tablename__ = "activities"

    # Foreign keys
    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
    )
    wbs_element_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("wbs_elements.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Basic information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Duration (in working days)
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remaining_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Schedule dates (calculated by CPM engine)
    early_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    early_finish: Mapped[date | None] = mapped_column(Date, nullable=True)
    late_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    late_finish: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Actual dates
    actual_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_finish: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Float/slack (calculated by CPM engine)
    total_float: Mapped[int | None] = mapped_column(Integer, nullable=True)
    free_float: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Progress
    percent_complete: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # EVMS values (using Decimal for financial accuracy)
    budgeted_cost: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
    )
    actual_cost: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # Relationships
    program: Mapped["Program"] = relationship("Program", back_populates="activities")
    wbs_element: Mapped["WBSElement | None"] = relationship(
        "WBSElement",
        back_populates="activities",
    )
    predecessor_dependencies: Mapped[list["Dependency"]] = relationship(
        "Dependency",
        foreign_keys="Dependency.successor_id",
        back_populates="successor",
        cascade="all, delete-orphan",
    )
    successor_dependencies: Mapped[list["Dependency"]] = relationship(
        "Dependency",
        foreign_keys="Dependency.predecessor_id",
        back_populates="predecessor",
        cascade="all, delete-orphan",
    )

    @property
    def is_critical(self) -> bool:
        """Check if activity is on the critical path (zero total float)."""
        return self.total_float == 0

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Activity(id={self.id}, code={self.code}, name={self.name})>"
