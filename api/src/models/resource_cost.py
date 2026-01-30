"""Resource cost entry model for detailed cost tracking."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.resource import ResourceAssignment


class ResourceCostEntry(Base):
    """
    Detailed cost tracking entry for resource assignments.

    Records actual hours worked and costs incurred on specific dates.
    Used for accurate ACWP calculation in EVMS.

    Attributes:
        assignment_id: FK to parent resource assignment
        entry_date: Date of the cost entry
        hours_worked: Hours worked on this date
        cost_incurred: Cost incurred on this date
        quantity_used: Quantity used for MATERIAL type resources
        notes: Optional notes for this entry
    """

    __tablename__ = "resource_cost_entries"

    assignment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resource_assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent resource assignment",
    )

    entry_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Date of the cost entry",
    )

    hours_worked: Mapped[Decimal] = mapped_column(
        Numeric(precision=6, scale=2),
        nullable=False,
        default=Decimal("0"),
        comment="Hours worked on this date",
    )

    cost_incurred: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0"),
        comment="Cost incurred on this date",
    )

    quantity_used: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=True,
        comment="Quantity used for MATERIAL type resources",
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional notes for this entry",
    )

    # Relationships
    assignment: Mapped["ResourceAssignment"] = relationship(
        "ResourceAssignment",
        back_populates="cost_entries",
    )

    # Table-level configuration
    __table_args__ = (
        Index(
            "ix_resource_cost_entries_assignment_date",
            "assignment_id",
            "entry_date",
        ),
        {"comment": "Detailed cost tracking entries for resource assignments"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<ResourceCostEntry(id={self.id}, assignment_id={self.assignment_id}, "
            f"date={self.entry_date}, hours={self.hours_worked}, cost={self.cost_incurred})>"
        )
