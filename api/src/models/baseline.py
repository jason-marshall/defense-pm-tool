"""Baseline model for EVMS baseline management.

Baselines represent immutable snapshots of program schedule and cost data
for performance measurement per EIA-748 standards.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.program import Program
    from src.models.user import User


class Baseline(Base):
    """
    Represents a program baseline snapshot for EVMS.

    Baselines are immutable snapshots of program data used for:
    - Performance Measurement Baseline (PMB) tracking
    - Variance analysis (comparing current state to baseline)
    - Historical audit trail
    - What-if scenario comparisons

    Per EIA-748, baselines should capture:
    - Schedule data (activities, dependencies, CPM results)
    - Cost data (WBS budgets, time-phased BCWS)
    - WBS structure

    Attributes:
        program_id: FK to parent program
        name: Descriptive name for this baseline
        version: Auto-incrementing version number per program
        description: Optional detailed description
        schedule_snapshot: JSON snapshot of activities and dependencies
        cost_snapshot: JSON snapshot of cost data by WBS
        wbs_snapshot: JSON snapshot of WBS hierarchy
        is_approved: Whether this baseline is approved as PMB
        approved_at: Timestamp when approved
        approved_by_id: User who approved the baseline
        created_by_id: User who created the baseline
        total_bac: Total Budget at Completion from snapshot
        scheduled_finish: Scheduled completion date from snapshot
    """

    __tablename__ = "baselines"

    # Foreign key to Program
    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent program",
    )

    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Descriptive name for this baseline",
    )

    # Auto-incrementing version per program
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Version number (auto-incremented per program)",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional detailed description",
    )

    # Schedule snapshot (activities, dependencies, CPM dates)
    schedule_snapshot: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON snapshot of activities and dependencies",
    )

    # Cost snapshot (WBS budgets, time-phased BCWS)
    cost_snapshot: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON snapshot of cost data by WBS",
    )

    # WBS structure snapshot
    wbs_snapshot: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON snapshot of WBS hierarchy",
    )

    # Approval tracking
    is_approved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether this baseline is approved as PMB",
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when approved",
    )

    approved_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who approved the baseline",
    )

    # Creator tracking
    created_by_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="User who created the baseline",
    )

    # Summary metrics (cached from snapshots)
    total_bac: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Total Budget at Completion from snapshot",
    )

    scheduled_finish: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Scheduled completion date from snapshot",
    )

    # Summary counts
    activity_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of activities in snapshot",
    )

    wbs_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of WBS elements in snapshot",
    )

    # Relationships
    program: Mapped["Program"] = relationship(
        "Program",
    )

    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id],
        backref="created_baselines",
    )

    approved_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[approved_by_id],
        backref="approved_baselines",
    )

    # Table-level configuration
    __table_args__ = (
        # Unique constraint: version must be unique per program
        UniqueConstraint(
            "program_id",
            "version",
            name="uq_baselines_program_version",
        ),
        # Index for finding approved baselines
        Index(
            "ix_baselines_approved",
            "program_id",
            "is_approved",
            postgresql_where="is_approved = true AND deleted_at IS NULL",
        ),
        # Index for finding latest baseline per program
        Index(
            "ix_baselines_latest",
            "program_id",
            "version",
        ),
        {"comment": "Program baselines for EVMS performance measurement"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<Baseline(id={self.id}, name={self.name!r}, "
            f"version={self.version}, is_approved={self.is_approved})>"
        )

    @property
    def is_pmb(self) -> bool:
        """Check if this baseline is the Performance Measurement Baseline."""
        return self.is_approved

    @property
    def has_schedule_data(self) -> bool:
        """Check if baseline has schedule snapshot data."""
        return self.schedule_snapshot is not None

    @property
    def has_cost_data(self) -> bool:
        """Check if baseline has cost snapshot data."""
        return self.cost_snapshot is not None

    @property
    def has_wbs_data(self) -> bool:
        """Check if baseline has WBS snapshot data."""
        return self.wbs_snapshot is not None
