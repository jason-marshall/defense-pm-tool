"""EVMS Period models for time-phased earned value tracking."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.program import Program
    from src.models.wbs import WBSElement


class PeriodStatus(str, Enum):
    """Status of an EVMS reporting period."""

    DRAFT = "draft"  # Period is being prepared
    SUBMITTED = "submitted"  # Period has been submitted for review
    APPROVED = "approved"  # Period has been approved
    REJECTED = "rejected"  # Period was rejected, needs revision


class EVMSPeriod(Base):
    """
    Represents an EVMS reporting period for a program.

    EVMS data is typically reported on a monthly basis. Each period captures
    the planned value, earned value, and actual cost data for all control
    accounts in a program.

    Attributes:
        program_id: FK to the parent program
        period_start: Start date of the reporting period
        period_end: End date of the reporting period
        period_name: Human-readable name (e.g., "January 2026")
        status: Current status of the period
        notes: Optional notes about the period
    """

    __tablename__ = "evms_periods"

    # Program relationship
    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent program",
    )

    # Period dates
    period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Start date of reporting period",
    )

    period_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="End date of reporting period",
    )

    # Period identification
    period_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable period name (e.g., 'January 2026')",
    )

    # Status
    status: Mapped[PeriodStatus] = mapped_column(
        PgEnum(PeriodStatus, name="period_status", create_type=True),
        default=PeriodStatus.DRAFT,
        nullable=False,
        index=True,
        comment="Current period status",
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional notes about this period",
    )

    # Cumulative totals (calculated and stored for performance)
    cumulative_bcws: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Cumulative Budgeted Cost of Work Scheduled",
    )

    cumulative_bcwp: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Cumulative Budgeted Cost of Work Performed",
    )

    cumulative_acwp: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Cumulative Actual Cost of Work Performed",
    )

    # Relationships
    program: Mapped["Program"] = relationship(
        "Program",
        lazy="joined",
    )

    period_data: Mapped[list["EVMSPeriodData"]] = relationship(
        "EVMSPeriodData",
        back_populates="period",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        # Ensure unique periods per program
        UniqueConstraint(
            "program_id",
            "period_start",
            "period_end",
            name="uq_evms_periods_program_dates",
        ),
        # Index for period lookups
        Index(
            "ix_evms_periods_program_status",
            "program_id",
            "status",
        ),
        {"comment": "EVMS reporting periods"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<EVMSPeriod(id={self.id}, program_id={self.program_id}, "
            f"period={self.period_name}, status={self.status.value})>"
        )

    @property
    def cost_variance(self) -> Decimal:
        """Calculate Cost Variance (CV = BCWP - ACWP)."""
        return self.cumulative_bcwp - self.cumulative_acwp

    @property
    def schedule_variance(self) -> Decimal:
        """Calculate Schedule Variance (SV = BCWP - BCWS)."""
        return self.cumulative_bcwp - self.cumulative_bcws

    @property
    def cpi(self) -> Decimal | None:
        """Calculate Cost Performance Index (CPI = BCWP / ACWP)."""
        if self.cumulative_acwp == 0:
            return None
        return (self.cumulative_bcwp / self.cumulative_acwp).quantize(Decimal("0.01"))

    @property
    def spi(self) -> Decimal | None:
        """Calculate Schedule Performance Index (SPI = BCWP / BCWS)."""
        if self.cumulative_bcws == 0:
            return None
        return (self.cumulative_bcwp / self.cumulative_bcws).quantize(Decimal("0.01"))


class EVMSPeriodData(Base):
    """
    EVMS data for a specific WBS element within a reporting period.

    Stores the time-phased EVMS values for each control account or
    WBS element during a specific reporting period.

    Attributes:
        period_id: FK to the parent EVMS period
        wbs_id: FK to the WBS element
        bcws: Budgeted Cost of Work Scheduled for this period
        bcwp: Budgeted Cost of Work Performed for this period
        acwp: Actual Cost of Work Performed for this period
    """

    __tablename__ = "evms_period_data"

    # Period relationship
    period_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("evms_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent EVMS period",
    )

    # WBS relationship
    wbs_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("wbs_elements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to WBS element",
    )

    # Period values (incremental for this period)
    bcws: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Budgeted Cost of Work Scheduled (period)",
    )

    bcwp: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Budgeted Cost of Work Performed (period)",
    )

    acwp: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Actual Cost of Work Performed (period)",
    )

    # Cumulative values (running totals through this period)
    cumulative_bcws: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Cumulative BCWS through this period",
    )

    cumulative_bcwp: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Cumulative BCWP through this period",
    )

    cumulative_acwp: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Cumulative ACWP through this period",
    )

    # Calculated metrics (stored for query performance)
    cv: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Cost Variance (BCWP - ACWP)",
    )

    sv: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Schedule Variance (BCWP - BCWS)",
    )

    cpi: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=True,
        comment="Cost Performance Index",
    )

    spi: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=True,
        comment="Schedule Performance Index",
    )

    # Relationships
    period: Mapped["EVMSPeriod"] = relationship(
        "EVMSPeriod",
        back_populates="period_data",
        lazy="joined",
    )

    wbs: Mapped["WBSElement"] = relationship(
        "WBSElement",
        lazy="joined",
    )

    __table_args__ = (
        # Ensure unique WBS per period
        UniqueConstraint(
            "period_id",
            "wbs_id",
            name="uq_evms_period_data_period_wbs",
        ),
        # Index for WBS lookups across periods
        Index(
            "ix_evms_period_data_wbs",
            "wbs_id",
            "period_id",
        ),
        {"comment": "EVMS data per WBS element per period"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<EVMSPeriodData(id={self.id}, period_id={self.period_id}, "
            f"wbs_id={self.wbs_id}, bcwp={self.bcwp})>"
        )

    def calculate_metrics(self) -> None:
        """Calculate derived metrics from base values."""
        self.cv = self.cumulative_bcwp - self.cumulative_acwp
        self.sv = self.cumulative_bcwp - self.cumulative_bcws

        if self.cumulative_acwp > 0:
            self.cpi = (self.cumulative_bcwp / self.cumulative_acwp).quantize(Decimal("0.01"))
        else:
            self.cpi = None

        if self.cumulative_bcws > 0:
            self.spi = (self.cumulative_bcwp / self.cumulative_bcws).quantize(Decimal("0.01"))
        else:
            self.spi = None
