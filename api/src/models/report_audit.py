"""Report Audit model for tracking report generation.

Provides audit trail for all report generations per compliance requirements.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class ReportAudit(Base):
    """
    Report generation audit trail.

    Tracks all report generations for compliance:
    - Report type and program
    - Who generated and when
    - Parameters used
    - File details (path, format, size, checksum)

    Attributes:
        report_type: Type of report (e.g., 'cpr_format_1', 'cpr_format_5')
        program_id: Program the report was generated for
        generated_by: User who generated the report
        generated_at: Timestamp of generation
        parameters: JSONB of generation parameters
        file_path: Path to generated file
        file_format: Format of output (json, html, pdf)
        file_size: Size in bytes
        checksum: SHA256 checksum for integrity verification
    """

    # Report identification
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of report: cpr_format_1, cpr_format_3, cpr_format_5, etc.",
    )

    # Foreign keys
    program_id: Mapped[UUID] = mapped_column(
        ForeignKey("programs.id"),
        nullable=False,
        index=True,
        comment="Program the report was generated for",
    )

    generated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        comment="User who generated this report",
    )

    # Generation details
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.now,
        index=True,
        comment="Timestamp when report was generated",
    )

    parameters: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Report generation parameters",
    )

    # File details
    file_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Path to generated file",
    )

    file_format: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Output format: json, html, pdf",
    )

    file_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="File size in bytes",
    )

    checksum: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA256 checksum for integrity verification",
    )

    # Relationships
    program = relationship("Program", back_populates="report_audits")
    generator = relationship("User")

    def __repr__(self) -> str:
        """Generate debug-friendly string representation."""
        return (
            f"<ReportAudit(id={self.id}, "
            f"type={self.report_type}, "
            f"generated_at={self.generated_at})>"
        )
