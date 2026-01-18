"""Variance Explanation model for CPR Format 5 reporting.

Tracks variance explanations for significant variances per DFARS requirements.
Variances exceeding threshold require written explanation and corrective action plans.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class VarianceExplanation(Base):
    """
    Variance explanation for significant variances.

    Per DFARS, variances exceeding threshold (typically 10%) require:
    - Written explanation of variance cause
    - Corrective action plan
    - Expected resolution date

    Attributes:
        program_id: Program this explanation belongs to
        wbs_id: Optional WBS element for element-level variance
        period_id: Optional period for period-specific variance
        variance_type: 'schedule' or 'cost'
        variance_amount: Dollar amount of variance
        variance_percent: Percentage variance
        explanation: Required explanation text
        corrective_action: Optional corrective action plan
        expected_resolution: Expected date for resolution
        created_by: User who created the explanation
    """

    # Foreign keys
    program_id: Mapped[UUID] = mapped_column(
        ForeignKey("programs.id"),
        nullable=False,
        index=True,
        comment="Program this variance explanation belongs to",
    )

    wbs_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("wbs_elements.id"),
        nullable=True,
        index=True,
        comment="Optional WBS element for element-level variance",
    )

    period_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("evms_periods.id"),
        nullable=True,
        index=True,
        comment="Optional period for period-specific variance",
    )

    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        comment="User who created this explanation",
    )

    # Variance details
    variance_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type of variance: 'schedule' or 'cost'",
    )

    variance_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        comment="Dollar amount of variance",
    )

    variance_percent: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
        comment="Percentage variance",
    )

    # Explanation and corrective action
    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Required explanation of variance cause",
    )

    corrective_action: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Corrective action plan",
    )

    expected_resolution: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Expected resolution date",
    )

    # Relationships
    program = relationship("Program", back_populates="variance_explanations")
    wbs = relationship("WBSElement", back_populates="variance_explanations")
    period = relationship("EVMSPeriod", back_populates="variance_explanations")
    author = relationship("User")

    def __repr__(self) -> str:
        """Generate debug-friendly string representation."""
        return (
            f"<VarianceExplanation(id={self.id}, "
            f"type={self.variance_type}, "
            f"percent={self.variance_percent}%)>"
        )
