"""Management Reserve Log model for CPR Format 5 reporting.

Tracks changes to Management Reserve (MR) across periods.
Per DFARS, MR changes must be documented with reasons.
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class ManagementReserveLog(Base):
    """
    Management Reserve (MR) change log entry.

    Tracks changes to management reserve with:
    - Beginning and ending MR amounts
    - Changes in (MR added) and changes out (MR released)
    - Reason for changes
    - Approval tracking

    Used in CPR Format 5 to show MR history across periods.

    Attributes:
        program_id: Program this MR log belongs to
        period_id: Period when this change occurred
        beginning_mr: MR balance at start of period
        changes_in: Amount added to MR
        changes_out: Amount released from MR to work packages
        ending_mr: MR balance at end of period
        reason: Explanation for MR changes
        approved_by: User who approved the MR change
    """

    # Foreign keys
    program_id: Mapped[UUID] = mapped_column(
        ForeignKey("programs.id"),
        nullable=False,
        index=True,
        comment="Program this MR log belongs to",
    )

    period_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("evms_periods.id"),
        nullable=True,
        index=True,
        comment="Period when this MR change occurred",
    )

    approved_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        comment="User who approved this MR change",
    )

    # MR tracking
    beginning_mr: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        comment="MR balance at start of period",
    )

    changes_in: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0"),
        comment="Amount added to MR",
    )

    changes_out: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0"),
        comment="Amount released from MR to work packages",
    )

    ending_mr: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        comment="MR balance at end of period",
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Explanation for MR changes",
    )

    # Relationships
    program = relationship("Program", back_populates="management_reserve_logs")
    period = relationship("EVMSPeriod", back_populates="management_reserve_logs")
    approver = relationship("User")

    def __repr__(self) -> str:
        """Generate debug-friendly string representation."""
        return (
            f"<ManagementReserveLog(id={self.id}, "
            f"beginning={self.beginning_mr}, "
            f"ending={self.ending_mr})>"
        )
