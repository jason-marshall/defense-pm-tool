"""Unit tests for ReportAudit model, repository, and schemas."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.report_audit import ReportAudit
from src.repositories.report_audit import ReportAuditRepository
from src.schemas.report_audit import (
    ReportAuditCreate,
    ReportAuditListResponse,
    ReportAuditResponse,
    ReportAuditStats,
    ReportAuditSummary,
    ReportFormat,
    ReportType,
)

# =============================================================================
# Schema Tests
# =============================================================================


class TestReportType:
    """Tests for ReportType enum."""

    def test_cpr_format_1(self):
        """Should have cpr_format_1 type."""
        assert ReportType.CPR_FORMAT_1.value == "cpr_format_1"

    def test_cpr_format_3(self):
        """Should have cpr_format_3 type."""
        assert ReportType.CPR_FORMAT_3.value == "cpr_format_3"

    def test_cpr_format_5(self):
        """Should have cpr_format_5 type."""
        assert ReportType.CPR_FORMAT_5.value == "cpr_format_5"


class TestReportFormat:
    """Tests for ReportFormat enum."""

    def test_json_format(self):
        """Should have json format."""
        assert ReportFormat.JSON.value == "json"

    def test_html_format(self):
        """Should have html format."""
        assert ReportFormat.HTML.value == "html"

    def test_pdf_format(self):
        """Should have pdf format."""
        assert ReportFormat.PDF.value == "pdf"


class TestReportAuditCreate:
    """Tests for ReportAuditCreate schema."""

    def test_valid_create_minimal(self):
        """Should create with minimal required fields."""
        data = ReportAuditCreate(
            report_type="cpr_format_1",
            program_id=uuid4(),
        )
        assert data.report_type == "cpr_format_1"
        assert data.generated_by is None
        assert data.parameters is None

    def test_valid_create_all_fields(self):
        """Should create with all fields."""
        program_id = uuid4()
        user_id = uuid4()
        data = ReportAuditCreate(
            report_type="cpr_format_5",
            program_id=program_id,
            generated_by=user_id,
            parameters={"periods_to_include": 12, "variance_threshold": "10"},
            file_path="/reports/cpr_format5_ABC123.pdf",
            file_format="pdf",
            file_size=45678,
            checksum="abc123def456",
        )
        assert data.report_type == "cpr_format_5"
        assert data.program_id == program_id
        assert data.generated_by == user_id
        assert data.parameters is not None
        assert data.file_format == "pdf"
        assert data.file_size == 45678


class TestReportAuditResponse:
    """Tests for ReportAuditResponse schema."""

    def test_from_attributes(self):
        """Should create from model attributes."""
        now = datetime.now()
        data = ReportAuditResponse(
            id=uuid4(),
            report_type="cpr_format_1",
            program_id=uuid4(),
            generated_by=uuid4(),
            generated_at=now,
            parameters=None,
            file_path=None,
            file_format="json",
            file_size=1234,
            checksum=None,
            created_at=now,
        )
        assert data.report_type == "cpr_format_1"
        assert data.file_format == "json"
        assert data.file_size == 1234

    def test_with_all_fields(self):
        """Should include all optional fields."""
        now = datetime.now()
        data = ReportAuditResponse(
            id=uuid4(),
            report_type="cpr_format_5",
            program_id=uuid4(),
            generated_by=uuid4(),
            generated_at=now,
            parameters={"periods": 12},
            file_path="/reports/test.pdf",
            file_format="pdf",
            file_size=56789,
            checksum="abc123",
            created_at=now,
        )
        assert data.file_path == "/reports/test.pdf"
        assert data.checksum == "abc123"


class TestReportAuditSummary:
    """Tests for ReportAuditSummary schema."""

    def test_summary_fields(self):
        """Should contain only summary fields."""
        now = datetime.now()
        data = ReportAuditSummary(
            id=uuid4(),
            report_type="cpr_format_3",
            generated_at=now,
            generated_by=uuid4(),
            file_format="pdf",
            file_size=12345,
        )
        assert data.report_type == "cpr_format_3"
        assert data.file_size == 12345


class TestReportAuditListResponse:
    """Tests for ReportAuditListResponse schema."""

    def test_empty_list(self):
        """Should handle empty list."""
        data = ReportAuditListResponse(
            items=[],
            total=0,
            page=1,
            per_page=20,
            pages=1,
        )
        assert len(data.items) == 0
        assert data.total == 0

    def test_with_items(self):
        """Should contain list of responses."""
        now = datetime.now()
        item = ReportAuditResponse(
            id=uuid4(),
            report_type="cpr_format_1",
            program_id=uuid4(),
            generated_by=None,
            generated_at=now,
            parameters=None,
            file_path=None,
            file_format="html",
            file_size=5000,
            checksum=None,
            created_at=now,
        )
        data = ReportAuditListResponse(
            items=[item],
            total=1,
            page=1,
            per_page=20,
            pages=1,
        )
        assert len(data.items) == 1
        assert data.total == 1


class TestReportAuditStats:
    """Tests for ReportAuditStats schema."""

    def test_default_values(self):
        """Should have correct default values."""
        data = ReportAuditStats(
            total_reports=0,
        )
        assert data.total_reports == 0
        assert data.by_type == {}
        assert data.by_format == {}
        assert data.total_size_bytes == 0
        assert data.last_generated is None

    def test_with_values(self):
        """Should accept all values."""
        now = datetime.now()
        data = ReportAuditStats(
            total_reports=10,
            by_type={"cpr_format_1": 5, "cpr_format_5": 5},
            by_format={"pdf": 7, "json": 3},
            total_size_bytes=500000,
            last_generated=now,
        )
        assert data.total_reports == 10
        assert data.by_type["cpr_format_1"] == 5
        assert data.by_format["pdf"] == 7
        assert data.total_size_bytes == 500000
        assert data.last_generated == now


# =============================================================================
# Repository Tests
# =============================================================================


class TestReportAuditRepositoryGetByProgram:
    """Tests for get_by_program method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ReportAuditRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_program_returns_list(self, repo, mock_session):
        """Should return list of audit entries for a program."""
        program_id = uuid4()
        audit = ReportAudit(
            id=uuid4(),
            report_type="cpr_format_1",
            program_id=program_id,
            generated_at=datetime.now(),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [audit]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_program(program_id)

        assert result == [audit]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_program_with_type_filter(self, repo, mock_session):
        """Should filter by report type."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_by_program(program_id, report_type="cpr_format_5")

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_program_empty_result(self, repo, mock_session):
        """Should return empty list when no entries."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_program(program_id)

        assert result == []


class TestReportAuditRepositoryGetByType:
    """Tests for get_by_type method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ReportAuditRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_type_returns_list(self, repo, mock_session):
        """Should return entries for a report type."""
        audit = ReportAudit(
            id=uuid4(),
            report_type="cpr_format_5",
            program_id=uuid4(),
            generated_at=datetime.now(),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [audit]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_type("cpr_format_5")

        assert result == [audit]


class TestReportAuditRepositoryLogGeneration:
    """Tests for log_generation method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ReportAuditRepository(mock_session)

    @pytest.mark.asyncio
    async def test_log_generation_minimal(self, repo, mock_session):
        """Should log generation with minimal fields."""
        program_id = uuid4()

        # Mock the create method
        mock_audit = ReportAudit(
            id=uuid4(),
            report_type="cpr_format_1",
            program_id=program_id,
            generated_at=datetime.now(),
        )
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.add = MagicMock()

        # Patch the create method to return our mock
        with pytest.MonkeyPatch().context() as m:
            m.setattr(repo, "create", AsyncMock(return_value=mock_audit))
            result = await repo.log_generation(
                report_type="cpr_format_1",
                program_id=program_id,
            )

        assert result.report_type == "cpr_format_1"

    @pytest.mark.asyncio
    async def test_log_generation_all_fields(self, repo, mock_session):
        """Should log generation with all fields."""
        program_id = uuid4()
        user_id = uuid4()

        mock_audit = ReportAudit(
            id=uuid4(),
            report_type="cpr_format_5",
            program_id=program_id,
            generated_by=user_id,
            generated_at=datetime.now(),
            parameters={"periods": 12},
            file_path="/reports/test.pdf",
            file_format="pdf",
            file_size=45678,
            checksum="abc123",
        )

        with pytest.MonkeyPatch().context() as m:
            m.setattr(repo, "create", AsyncMock(return_value=mock_audit))
            result = await repo.log_generation(
                report_type="cpr_format_5",
                program_id=program_id,
                generated_by=user_id,
                parameters={"periods": 12},
                file_path="/reports/test.pdf",
                file_format="pdf",
                file_size=45678,
                checksum="abc123",
            )

        assert result.file_format == "pdf"
        assert result.file_size == 45678


class TestReportAuditRepositoryGetRecent:
    """Tests for get_recent method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ReportAuditRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_recent_default_limit(self, repo, mock_session):
        """Should return recent entries with default limit."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_recent(program_id)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_custom_limit(self, repo, mock_session):
        """Should respect custom limit."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_recent(program_id, limit=5)

        mock_session.execute.assert_called_once()


# =============================================================================
# Model Tests
# =============================================================================


class TestReportAuditModel:
    """Tests for ReportAudit model."""

    def test_create_model(self):
        """Should create model instance."""
        audit = ReportAudit(
            id=uuid4(),
            report_type="cpr_format_1",
            program_id=uuid4(),
            generated_at=datetime.now(),
        )
        assert audit.report_type == "cpr_format_1"

    def test_model_with_all_fields(self):
        """Should create model with all fields."""
        audit = ReportAudit(
            id=uuid4(),
            report_type="cpr_format_5",
            program_id=uuid4(),
            generated_by=uuid4(),
            generated_at=datetime.now(),
            parameters={"periods": 12, "threshold": 10},
            file_path="/reports/test.pdf",
            file_format="pdf",
            file_size=123456,
            checksum="abc123def456789",
        )
        assert audit.report_type == "cpr_format_5"
        assert audit.file_format == "pdf"
        assert audit.file_size == 123456
        assert audit.checksum == "abc123def456789"

    def test_model_repr(self):
        """Should have informative repr."""
        now = datetime.now()
        audit = ReportAudit(
            id=uuid4(),
            report_type="cpr_format_3",
            program_id=uuid4(),
            generated_at=now,
        )
        repr_str = repr(audit)
        assert "ReportAudit" in repr_str
        assert "cpr_format_3" in repr_str


# =============================================================================
# Checksum Tests
# =============================================================================


class TestChecksumFunction:
    """Tests for checksum computation."""

    def test_compute_checksum(self):
        """Should compute correct SHA256 checksum."""
        import hashlib

        data = b"test data for checksum"
        expected = hashlib.sha256(data).hexdigest()

        # Import the function from reports endpoint
        from src.api.v1.endpoints.reports import _compute_checksum

        result = _compute_checksum(data)
        assert result == expected

    def test_checksum_consistency(self):
        """Should produce consistent checksums."""
        from src.api.v1.endpoints.reports import _compute_checksum

        data = b"consistent data"
        result1 = _compute_checksum(data)
        result2 = _compute_checksum(data)

        assert result1 == result2

    def test_checksum_different_data(self):
        """Should produce different checksums for different data."""
        from src.api.v1.endpoints.reports import _compute_checksum

        data1 = b"data one"
        data2 = b"data two"

        result1 = _compute_checksum(data1)
        result2 = _compute_checksum(data2)

        assert result1 != result2
