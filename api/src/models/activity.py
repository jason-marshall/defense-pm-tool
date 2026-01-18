"""Activity model for schedule management with CPM support."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import ConstraintType, EVMethod

if TYPE_CHECKING:
    from src.models.dependency import Dependency
    from src.models.program import Program
    from src.models.wbs import WBSElement


class Activity(Base):
    """
    Represents a schedulable activity within a WBS element.

    Activities are the fundamental units of work in CPM scheduling.
    They have durations, dependencies, and calculated dates from
    forward/backward pass calculations.

    CPM Fields:
    - early_start, early_finish: Earliest possible dates (forward pass)
    - late_start, late_finish: Latest possible dates (backward pass)
    - total_float: Time activity can slip without delaying project
    - free_float: Time activity can slip without delaying successors
    - is_critical: True if on critical path (total_float = 0)

    Attributes:
        program_id: FK to parent program (for direct program queries)
        wbs_id: FK to parent WBS element
        code: Unique activity code within program (e.g., "A001")
        name: Activity name/description
        duration: Duration in working days
        planned_start/finish: Baseline planned dates
        actual_start/finish: Actual execution dates
        constraint_type: Scheduling constraint
        constraint_date: Date for constraint (if applicable)
        percent_complete: Progress percentage (0-100)
        is_milestone: Whether this is a zero-duration milestone
    """

    # Override auto-generated table name
    __tablename__ = "activities"

    # Foreign key to Program (for direct program queries)
    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent program",
    )

    # Foreign key to WBS element
    wbs_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("wbs_elements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent WBS element",
    )

    # Unique activity code within program (e.g., "A001", "TASK-100")
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Unique activity code within program",
    )

    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Activity name/description",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description",
    )

    # Duration in working days (0 for milestones)
    duration: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Duration in working days",
    )

    # Planned baseline dates
    planned_start: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
        comment="Baseline planned start date",
    )

    planned_finish: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
        comment="Baseline planned finish date",
    )

    # Actual execution dates
    actual_start: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
        comment="Actual start date",
    )

    actual_finish: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
        comment="Actual finish date",
    )

    # CPM calculated dates (from forward pass)
    early_start: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Early start from CPM forward pass",
    )

    early_finish: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Early finish from CPM forward pass",
    )

    # CPM calculated dates (from backward pass)
    late_start: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Late start from CPM backward pass",
    )

    late_finish: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Late finish from CPM backward pass",
    )

    # Float/slack values
    total_float: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Total float in days (LS - ES)",
    )

    free_float: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Free float in days",
    )

    # Critical path flag
    is_critical: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="True if on critical path (total_float = 0)",
    )

    # Scheduling constraints
    constraint_type: Mapped[ConstraintType] = mapped_column(
        PgEnum(ConstraintType, name="constraint_type", create_type=True),
        default=ConstraintType.ASAP,
        nullable=False,
        comment="Scheduling constraint type",
    )

    constraint_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Date for scheduling constraint",
    )

    # Progress tracking
    percent_complete: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Progress percentage (0-100)",
    )

    # Milestone flag (zero duration)
    is_milestone: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="True if this is a milestone (duration=0)",
    )

    # EVMS cost tracking
    budgeted_cost: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Budgeted cost (BCWS at completion)",
    )

    actual_cost: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Actual cost incurred (ACWP)",
    )

    # EV Method configuration
    ev_method: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=EVMethod.PERCENT_COMPLETE.value,
        comment="Earned value calculation method",
    )

    # Milestones for milestone-weight method (stored as JSON)
    milestones_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Milestone definitions for weighted EV method",
    )

    # Relationships
    program: Mapped["Program"] = relationship(
        "Program",
        back_populates="activities",
    )

    wbs_element: Mapped["WBSElement"] = relationship(
        "WBSElement",
        back_populates="activities",
    )

    # Dependencies where this activity is the successor (predecessors)
    predecessor_links: Mapped[list["Dependency"]] = relationship(
        "Dependency",
        foreign_keys="Dependency.successor_id",
        back_populates="successor",
        cascade="all, delete-orphan",
    )

    # Dependencies where this activity is the predecessor (successors)
    successor_links: Mapped[list["Dependency"]] = relationship(
        "Dependency",
        foreign_keys="Dependency.predecessor_id",
        back_populates="predecessor",
        cascade="all, delete-orphan",
    )

    # Table-level configuration
    __table_args__ = (
        # Unique constraint: activity code must be unique within a program
        UniqueConstraint(
            "program_id",
            "code",
            name="uq_activities_program_code",
        ),
        # Check constraint for percent_complete range
        CheckConstraint(
            "percent_complete >= 0 AND percent_complete <= 100",
            name="ck_activities_percent_complete",
        ),
        # Check constraint for non-negative duration
        CheckConstraint(
            "duration >= 0",
            name="ck_activities_duration",
        ),
        # Note: program_id index is created by index=True on the column
        # Index for critical path queries
        Index(
            "ix_activities_critical",
            "program_id",
            "is_critical",
            postgresql_where=text("is_critical = true AND deleted_at IS NULL"),
        ),
        # Index for milestone lookup
        Index(
            "ix_activities_milestones",
            "wbs_id",
            "is_milestone",
            postgresql_where=text("is_milestone = true AND deleted_at IS NULL"),
        ),
        # Index for date range queries
        Index(
            "ix_activities_dates",
            "early_start",
            "early_finish",
        ),
        # Index for incomplete activities
        Index(
            "ix_activities_incomplete",
            "wbs_id",
            "percent_complete",
            postgresql_where=text("percent_complete < 100 AND deleted_at IS NULL"),
        ),
        {"comment": "Schedule activities with CPM support"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<Activity(id={self.id}, code={self.code!r}, name={self.name!r}, "
            f"duration={self.duration}, is_critical={self.is_critical})>"
        )

    @property
    def is_started(self) -> bool:
        """Check if activity has started."""
        return self.actual_start is not None

    @property
    def is_completed(self) -> bool:
        """Check if activity is completed."""
        return self.percent_complete >= Decimal("100.00") or self.actual_finish is not None

    @property
    def is_in_progress(self) -> bool:
        """Check if activity is in progress."""
        return self.is_started and not self.is_completed

    @property
    def remaining_duration(self) -> int:
        """Calculate remaining duration based on percent complete."""
        if self.is_completed:
            return 0
        remaining_pct = (Decimal("100.00") - self.percent_complete) / Decimal("100.00")
        return int(self.duration * float(remaining_pct))

    @property
    def earned_value(self) -> Decimal:
        """Calculate earned value (BCWP) based on percent complete."""
        return self.budgeted_cost * self.percent_complete / Decimal("100.00")

    def calculate_float(self) -> None:
        """
        Calculate total and free float from CPM dates.

        Call this after forward and backward passes are complete.
        """
        if self.late_start is not None and self.early_start is not None:
            self.total_float = (self.late_start - self.early_start).days
            self.is_critical = self.total_float == 0
