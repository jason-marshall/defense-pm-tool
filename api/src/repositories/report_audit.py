"""Repository for ReportAudit model."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.report_audit import ReportAudit
from src.repositories.base import BaseRepository


class ReportAuditRepository(BaseRepository[ReportAudit]):
    """
    Repository for report audit trail CRUD operations.

    Provides methods for tracking report generation per compliance requirements.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__(ReportAudit, session)

    async def get_by_program(
        self,
        program_id: UUID,
        report_type: str | None = None,
        include_deleted: bool = False,
    ) -> list[ReportAudit]:
        """
        Get all report audit entries for a program.

        Args:
            program_id: Program ID
            report_type: Optional filter for report type
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of report audit entries
        """
        query = select(ReportAudit).where(ReportAudit.program_id == program_id)

        if report_type:
            query = query.where(ReportAudit.report_type == report_type)

        query = self._apply_soft_delete_filter(query, include_deleted)
        query = query.order_by(ReportAudit.generated_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_type(
        self,
        report_type: str,
        include_deleted: bool = False,
    ) -> list[ReportAudit]:
        """
        Get all audit entries for a specific report type.

        Args:
            report_type: Report type (e.g., 'cpr_format_5')
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of report audit entries
        """
        query = select(ReportAudit).where(ReportAudit.report_type == report_type)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = query.order_by(ReportAudit.generated_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def log_generation(
        self,
        report_type: str,
        program_id: UUID,
        generated_by: UUID | None = None,
        parameters: dict[str, Any] | None = None,
        file_path: str | None = None,
        file_format: str | None = None,
        file_size: int | None = None,
        checksum: str | None = None,
    ) -> ReportAudit:
        """
        Log a report generation event.

        Args:
            report_type: Type of report generated
            program_id: Program the report was generated for
            generated_by: User who generated the report
            parameters: Report generation parameters
            file_path: Path to generated file
            file_format: Format of output file
            file_size: Size of generated file in bytes
            checksum: SHA256 checksum of generated file

        Returns:
            Created ReportAudit entry
        """
        data = {
            "report_type": report_type,
            "program_id": program_id,
            "generated_by": generated_by,
            "generated_at": datetime.now(UTC),
            "parameters": parameters,
            "file_path": file_path,
            "file_format": file_format,
            "file_size": file_size,
            "checksum": checksum,
        }

        return await self.create(data)

    async def get_recent(
        self,
        program_id: UUID,
        limit: int = 10,
        include_deleted: bool = False,
    ) -> list[ReportAudit]:
        """
        Get recent report generations for a program.

        Args:
            program_id: Program ID
            limit: Maximum number of entries to return
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of recent report audit entries
        """
        query = select(ReportAudit).where(ReportAudit.program_id == program_id)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = query.order_by(ReportAudit.generated_at.desc())
        query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())
