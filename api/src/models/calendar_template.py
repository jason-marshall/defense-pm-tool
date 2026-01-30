"""Calendar template models for reusable work patterns.

Calendar templates allow users to define standard work patterns
(e.g., "5-day work week", "7-day operations", "Shift schedule")
that can be applied to multiple resources.
"""

from __future__ import annotations

from datetime import date  # noqa: TC003 - Required at runtime for SQLAlchemy
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 - Required at runtime for SQLAlchemy

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.program import Program
    from src.models.resource import Resource


class CalendarTemplate(Base):
    """Reusable calendar template defining work patterns.

    Templates define standard working hours and days that can be
    applied to multiple resources. Each program can have multiple
    templates, with one marked as the default.

    Attributes:
        program_id: UUID of the owning program
        name: Human-readable template name (e.g., "Standard 5-Day Week")
        description: Optional detailed description
        hours_per_day: Standard working hours per day (default 8.0)
        working_days: Array of working day numbers (1=Monday, 7=Sunday)
        is_default: Whether this is the default template for the program
        holidays: List of holidays defined in this template
        resources: Resources using this template

    Example:
        Standard 5-day week:
            hours_per_day = 8.0
            working_days = [1, 2, 3, 4, 5]  # Mon-Fri

        24/7 Operations:
            hours_per_day = 24.0
            working_days = [1, 2, 3, 4, 5, 6, 7]  # All days
    """

    __tablename__ = "resource_calendar_templates"

    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    hours_per_day: Mapped[Decimal] = mapped_column(
        Numeric(precision=4, scale=2),
        nullable=False,
        default=Decimal("8.0"),
    )

    # Working days as array of integers (1=Monday, 7=Sunday per ISO 8601)
    working_days: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        default=[1, 2, 3, 4, 5],  # Monday-Friday
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Relationships
    program: Mapped[Program] = relationship(back_populates="calendar_templates")
    holidays: Mapped[list[CalendarTemplateHoliday]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    resources: Mapped[list[Resource]] = relationship(
        back_populates="calendar_template",
        foreign_keys="Resource.calendar_template_id",
    )

    def is_working_day(self, check_date: date) -> bool:
        """Check if a date is a working day according to this template.

        Args:
            check_date: The date to check

        Returns:
            True if the date is a working day (not a weekend or holiday)
        """
        # Check if day of week is in working_days (ISO: Monday=1, Sunday=7)
        # Python's weekday() returns Monday=0, Sunday=6, so we add 1
        day_of_week = check_date.weekday() + 1
        if day_of_week not in self.working_days:
            return False

        # Check if it's a holiday
        for holiday in self.holidays:
            if holiday.recurring_yearly:
                # Check month and day only
                if (
                    check_date.month == holiday.holiday_date.month
                    and check_date.day == holiday.holiday_date.day
                ):
                    return False
            elif check_date == holiday.holiday_date:
                return False

        return True

    def get_available_hours(self, check_date: date) -> Decimal:
        """Get available working hours for a specific date.

        Args:
            check_date: The date to get hours for

        Returns:
            Available hours (0 if not a working day, hours_per_day otherwise)
        """
        if self.is_working_day(check_date):
            return self.hours_per_day
        return Decimal("0")


class CalendarTemplateHoliday(Base):
    """Holiday entry within a calendar template.

    Holidays can be one-time (specific date) or recurring yearly
    (same month/day each year).

    Attributes:
        template_id: UUID of the parent template
        holiday_date: The date of the holiday
        name: Holiday name (e.g., "Christmas Day")
        recurring_yearly: If True, repeats every year on same month/day
    """

    __tablename__ = "calendar_template_holidays"

    template_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resource_calendar_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    holiday_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    recurring_yearly: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Relationships
    template: Mapped[CalendarTemplate] = relationship(back_populates="holidays")
