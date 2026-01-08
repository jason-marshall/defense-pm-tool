"""Program model representing a defense program/project."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.activity import Activity
    from src.models.wbs import WBSElement


class Program(Base):
    """
    Represents a defense program or project.

    A program is the top-level container for all project management data,
    including WBS elements, activities, and EVMS metrics.
    """

    __tablename__ = "programs"

    # Basic information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Schedule dates
    planned_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    planned_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Budget (using Decimal for financial accuracy)
    budget_at_completion: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # Contract information
    contract_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    wbs_elements: Mapped[list["WBSElement"]] = relationship(
        "WBSElement",
        back_populates="program",
        cascade="all, delete-orphan",
    )
    activities: Mapped[list["Activity"]] = relationship(
        "Activity",
        back_populates="program",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Program(id={self.id}, code={self.code}, name={self.name})>"
