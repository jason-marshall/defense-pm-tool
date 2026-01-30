"""Resource models for resource management with capacity and calendar support."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import ResourceType

if TYPE_CHECKING:
    from src.models.activity import Activity
    from src.models.program import Program
    from src.models.resource_cost import ResourceCostEntry


class Resource(Base):
    """
    Represents a resource that can be assigned to activities.

    Resources can be of type LABOR, EQUIPMENT, or MATERIAL.
    Labor and Equipment resources are time-based and support leveling.
    Material resources are quantity-based.

    Attributes:
        program_id: FK to parent program
        name: Resource name/description
        code: Unique resource code within program
        resource_type: Classification (LABOR, EQUIPMENT, MATERIAL)
        capacity_per_day: Available hours per day (0-24)
        cost_rate: Hourly cost rate
        effective_date: Date when resource becomes available
        is_active: Whether resource is currently active
    """

    __tablename__ = "resources"

    # Foreign key to Program
    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent program",
    )

    # Resource identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Resource name/description",
    )

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Unique resource code within program",
    )

    # Resource type
    resource_type: Mapped[ResourceType] = mapped_column(
        PgEnum(ResourceType, name="resource_type", create_type=True),
        default=ResourceType.LABOR,
        nullable=False,
        index=True,
        comment="Resource classification (LABOR, EQUIPMENT, MATERIAL)",
    )

    # Capacity and cost
    capacity_per_day: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=False,
        default=Decimal("8.00"),
        comment="Available hours per day (0-24)",
    )

    cost_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=True,
        comment="Hourly cost rate",
    )

    # Material quantity fields (for MATERIAL type)
    quantity_unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Unit of measurement for materials (e.g., 'units', 'kg', 'meters')",
    )

    unit_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=True,
        comment="Cost per unit for MATERIAL type resources",
    )

    quantity_available: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=True,
        comment="Total available quantity for MATERIAL type",
    )

    # Availability
    effective_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
        comment="Date when resource becomes available",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether resource is currently active",
    )

    # Relationships
    program: Mapped["Program"] = relationship(
        "Program",
        back_populates="resources",
    )

    assignments: Mapped[list["ResourceAssignment"]] = relationship(
        "ResourceAssignment",
        back_populates="resource",
        cascade="all, delete-orphan",
    )

    calendar_entries: Mapped[list["ResourceCalendar"]] = relationship(
        "ResourceCalendar",
        back_populates="resource",
        cascade="all, delete-orphan",
    )

    # Table-level configuration
    __table_args__ = (
        # Unique constraint: resource code must be unique within a program
        UniqueConstraint(
            "program_id",
            "code",
            name="uq_resources_program_code",
        ),
        # Check constraint for capacity range
        CheckConstraint(
            "capacity_per_day >= 0 AND capacity_per_day <= 24",
            name="ck_resources_capacity",
        ),
        # Check constraint for non-negative cost rate
        CheckConstraint(
            "cost_rate IS NULL OR cost_rate >= 0",
            name="ck_resources_cost_rate",
        ),
        # Index for active resources by type
        Index(
            "ix_resources_active_type",
            "program_id",
            "resource_type",
            "is_active",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"comment": "Resources for assignment to activities"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<Resource(id={self.id}, code={self.code!r}, name={self.name!r}, "
            f"type={self.resource_type.value}, capacity={self.capacity_per_day})>"
        )


class ResourceAssignment(Base):
    """
    Represents an assignment of a resource to an activity.

    Assignments specify how much of a resource is allocated to an activity
    and for what period. Units represent allocation percentage where
    1.0 = 100% allocation.

    Attributes:
        activity_id: FK to assigned activity
        resource_id: FK to assigned resource
        units: Allocation units (0-10, where 1.0 = 100%)
        start_date: Assignment start date (defaults to activity start)
        finish_date: Assignment finish date (defaults to activity finish)
    """

    __tablename__ = "resource_assignments"

    # Foreign keys
    activity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to assigned activity",
    )

    resource_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to assigned resource",
    )

    # Allocation
    units: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=False,
        default=Decimal("1.00"),
        comment="Allocation units (0-10, where 1.0 = 100%)",
    )

    # Date range
    start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
        comment="Assignment start date (defaults to activity start)",
    )

    finish_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
        comment="Assignment finish date (defaults to activity finish)",
    )

    # Time-based cost tracking (for LABOR/EQUIPMENT)
    planned_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=True,
        comment="Planned hours for this assignment",
    )

    actual_hours: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0"),
        comment="Actual hours worked",
    )

    planned_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=True,
        comment="Planned cost (planned_hours * cost_rate)",
    )

    actual_cost: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0"),
        comment="Actual cost incurred",
    )

    # Quantity tracking (for MATERIAL type)
    quantity_assigned: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=True,
        comment="Quantity assigned for MATERIAL type",
    )

    quantity_consumed: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0"),
        comment="Quantity consumed for MATERIAL type",
    )

    # Relationships
    activity: Mapped["Activity"] = relationship(
        "Activity",
        back_populates="resource_assignments",
    )

    resource: Mapped["Resource"] = relationship(
        "Resource",
        back_populates="assignments",
    )

    cost_entries: Mapped[list["ResourceCostEntry"]] = relationship(
        "ResourceCostEntry",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )

    # Table-level configuration
    __table_args__ = (
        # Unique constraint: one assignment per activity-resource pair
        UniqueConstraint(
            "activity_id",
            "resource_id",
            name="uq_resource_assignments_activity_resource",
        ),
        # Check constraint for units range
        CheckConstraint(
            "units >= 0 AND units <= 10",
            name="ck_resource_assignments_units",
        ),
        # Check constraint for valid date range
        CheckConstraint(
            "start_date IS NULL OR finish_date IS NULL OR finish_date >= start_date",
            name="ck_resource_assignments_dates",
        ),
        # Index for resource utilization queries
        Index(
            "ix_resource_assignments_resource_dates",
            "resource_id",
            "start_date",
            "finish_date",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"comment": "Resource assignments to activities"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<ResourceAssignment(id={self.id}, activity_id={self.activity_id}, "
            f"resource_id={self.resource_id}, units={self.units})>"
        )


class ResourceCalendar(Base):
    """
    Represents a calendar entry for a resource on a specific date.

    Calendar entries define resource availability on specific dates,
    allowing for holidays, vacations, and variable work hours.

    Attributes:
        resource_id: FK to resource
        calendar_date: Calendar date
        available_hours: Available hours on this date (0-24)
        is_working_day: Whether this is a working day
    """

    __tablename__ = "resource_calendars"

    # Foreign key to Resource
    resource_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to resource",
    )

    # Calendar data
    calendar_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Calendar date",
    )

    available_hours: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=False,
        default=Decimal("8.00"),
        comment="Available hours on this date (0-24)",
    )

    is_working_day: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this is a working day",
    )

    # Relationships
    resource: Mapped["Resource"] = relationship(
        "Resource",
        back_populates="calendar_entries",
    )

    # Table-level configuration
    __table_args__ = (
        # Unique constraint: one entry per resource-date pair
        UniqueConstraint(
            "resource_id",
            "calendar_date",
            name="uq_resource_calendars_resource_date",
        ),
        # Check constraint for hours range
        CheckConstraint(
            "available_hours >= 0 AND available_hours <= 24",
            name="ck_resource_calendars_hours",
        ),
        # Index for date range queries
        Index(
            "ix_resource_calendars_date_range",
            "resource_id",
            "calendar_date",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"comment": "Resource calendar entries for availability"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<ResourceCalendar(id={self.id}, resource_id={self.resource_id}, "
            f"date={self.calendar_date}, hours={self.available_hours})>"
        )
