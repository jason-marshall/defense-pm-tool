"""Pydantic schemas for ReportAudit model.

Schemas for report generation audit trail per compliance requirements.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportType(str, Enum):
    """Types of reports that can be generated."""

    CPR_FORMAT_1 = "cpr_format_1"
    CPR_FORMAT_3 = "cpr_format_3"
    CPR_FORMAT_5 = "cpr_format_5"


class ReportFormat(str, Enum):
    """Output formats for reports."""

    JSON = "json"
    HTML = "html"
    PDF = "pdf"


class ReportAuditCreate(BaseModel):
    """Schema for creating a report audit entry (internal use)."""

    report_type: str = Field(
        ...,
        description="Type of report: cpr_format_1, cpr_format_3, cpr_format_5",
    )
    program_id: UUID = Field(
        ...,
        description="Program the report was generated for",
    )
    generated_by: UUID | None = Field(
        default=None,
        description="User who generated the report",
    )
    parameters: dict[str, Any] | None = Field(
        default=None,
        description="Report generation parameters",
    )
    file_path: str | None = Field(
        default=None,
        max_length=500,
        description="Path to generated file",
    )
    file_format: str | None = Field(
        default=None,
        max_length=20,
        description="Output format: json, html, pdf",
    )
    file_size: int | None = Field(
        default=None,
        ge=0,
        description="File size in bytes",
    )
    checksum: str | None = Field(
        default=None,
        max_length=64,
        description="SHA256 checksum for integrity verification",
    )


class ReportAuditResponse(BaseModel):
    """Response schema for report audit entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_type: str
    program_id: UUID
    generated_by: UUID | None
    generated_at: datetime
    parameters: dict[str, Any] | None
    file_path: str | None
    file_format: str | None
    file_size: int | None
    checksum: str | None
    created_at: datetime


class ReportAuditSummary(BaseModel):
    """Lightweight summary for audit listing."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_type: str
    generated_at: datetime
    generated_by: UUID | None
    file_format: str | None
    file_size: int | None


class ReportAuditListResponse(BaseModel):
    """Paginated list of report audit entries."""

    items: list[ReportAuditResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ReportAuditStats(BaseModel):
    """Statistics about report generations."""

    total_reports: int = Field(..., description="Total number of reports generated")
    by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Count of reports by type",
    )
    by_format: dict[str, int] = Field(
        default_factory=dict,
        description="Count of reports by output format",
    )
    total_size_bytes: int = Field(
        default=0,
        description="Total size of all generated reports in bytes",
    )
    last_generated: datetime | None = Field(
        default=None,
        description="Timestamp of most recent report generation",
    )
