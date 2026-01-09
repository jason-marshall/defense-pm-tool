"""Program model representing a defense program/project."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.user import User
    from src.models.wbs import WBSElement


class ProgramStatus(str, Enum):
    """
    Program lifecycle status.

    Tracks the current phase of a program from initial planning
    through completion or hold.
    """

    PLANNING = "planning"  # Initial setup and planning phase
    ACTIVE = "active"  # Program is actively being executed
    COMPLETE = "complete"  # Program has been completed
    ON_HOLD = "on_hold"  # Program is temporarily suspended

    @property
    def is_editable(self) -> bool:
        """Check if program can be edited in this status."""
        return self in (ProgramStatus.PLANNING, ProgramStatus.ACTIVE)

    @property
    def is_active(self) -> bool:
        """Check if program is in an active state."""
        return self in (ProgramStatus.PLANNING, ProgramStatus.ACTIVE)


class Program(Base):
    """
    Represents a defense program or project.

    A program is the top-level container for all project management data,
    including WBS elements, activities, and EVMS metrics. Each program
    has an owner (User) responsible for its management.

    Attributes:
        name: Display name of the program
        description: Detailed description of the program
        contract_number: Associated contract identifier
        start_date: Planned start date
        end_date: Planned end date
        status: Current program status
        owner_id: FK to the User who owns this program
        budget_at_completion: Total authorized budget (BAC)
    """

    # Override auto-generated table name
    __tablename__ = "programs"

    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Display name of the program",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of the program",
    )

    # Contract information
    contract_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
        comment="Associated contract identifier",
    )

    # Schedule dates
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Planned program start date",
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Planned program end date",
    )

    # Program status
    status: Mapped[ProgramStatus] = mapped_column(
        PgEnum(ProgramStatus, name="program_status", create_type=True),
        default=ProgramStatus.PLANNING,
        nullable=False,
        index=True,
        comment="Current program lifecycle status",
    )

    # Owner relationship
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to user who owns this program",
    )

    # Budget at Completion (using Decimal for financial accuracy)
    budget_at_completion: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Total authorized budget (BAC)",
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_programs",
        lazy="joined",
    )

    wbs_elements: Mapped[list["WBSElement"]] = relationship(
        "WBSElement",
        back_populates="program",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="WBSElement.path",
    )

    # Table-level configuration
    __table_args__ = (
        # Index for active programs lookup
        Index(
            "ix_programs_status_active",
            "status",
            "owner_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # Index for date range queries
        Index(
            "ix_programs_dates",
            "start_date",
            "end_date",
        ),
        {"comment": "Defense programs/projects"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<Program(id={self.id}, name={self.name!r}, "
            f"status={self.status.value})>"
        )

    @property
    def duration_days(self) -> int:
        """Calculate program duration in days."""
        return (self.end_date - self.start_date).days

    @property
    def is_editable(self) -> bool:
        """Check if program can be edited."""
        return self.status.is_editable and not self.is_deleted
