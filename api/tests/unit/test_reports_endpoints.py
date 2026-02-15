"""Unit tests for report generation endpoints."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.reports import (
    generate_cpr_format1,
    generate_cpr_format1_html,
    generate_cpr_format1_pdf,
    generate_cpr_format3,
    generate_cpr_format3_pdf,
    generate_cpr_format5,
    generate_cpr_format5_pdf,
    get_program_report_summary,
    get_recent_report_generations,
    get_report_audit_history,
    get_report_audit_stats,
)
from src.core.exceptions import AuthorizationError, NotFoundError

# ---------------------------------------------------------------------------
# Helpers to build mock objects
# ---------------------------------------------------------------------------


def _mock_program(owner_id=None):
    """Create a mock program."""
    program = MagicMock()
    program.id = uuid4()
    program.name = "Test Program"
    program.code = "TP-001"
    program.owner_id = owner_id or uuid4()
    return program


def _mock_period():
    """Create a mock EVMS period with period_data."""
    period = MagicMock()
    period.id = uuid4()
    period.period_name = "Jan 2026"
    period.period_start = date(2026, 1, 1)
    period.period_end = date(2026, 1, 31)
    period.status = MagicMock(value="approved")
    period.period_data = [MagicMock()]
    return period


def _mock_user(user_id=None, is_admin=False):
    """Create a mock user."""
    user = MagicMock()
    user.id = user_id or uuid4()
    user.is_admin = is_admin
    return user


def _mock_baseline(program_id=None):
    """Create a mock baseline."""
    baseline = MagicMock()
    baseline.id = uuid4()
    baseline.name = "PMB v1"
    baseline.program_id = program_id or uuid4()
    return baseline


def _mock_audit_entry(report_type="cpr_format_1", file_format="pdf", file_size=12345):
    """Create a mock report audit entry."""
    entry = MagicMock()
    entry.id = uuid4()
    entry.report_type = report_type
    entry.program_id = uuid4()
    entry.generated_by = uuid4()
    entry.generated_at = datetime.now(UTC)
    entry.parameters = {}
    entry.file_path = None
    entry.file_format = file_format
    entry.file_size = file_size
    entry.checksum = "abc123"
    entry.created_at = datetime.now(UTC)
    return entry


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestGenerateCprFormat1:
    """Tests for generate_cpr_format1 endpoint."""

    @pytest.mark.asyncio
    async def test_success_with_period_id(self):
        """Should generate CPR Format 1 report for a specific period."""
        mock_db = AsyncMock()
        program = _mock_program()
        period = _mock_period()
        period_id = period.id

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.reports.WBSElementRepository") as mock_wbs_repo_cls,
            patch("src.api.v1.endpoints.reports.ReportGenerator") as mock_gen_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_with_data = AsyncMock(return_value=period)
            mock_wbs_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])

            mock_gen = MagicMock()
            mock_report = MagicMock()
            mock_gen.generate_cpr_format1.return_value = mock_report
            mock_gen.to_dict.return_value = {"report_type": "cpr_format_1"}
            mock_gen_cls.return_value = mock_gen

            result = await generate_cpr_format1(program.id, mock_db, period_id=period_id)

            assert result == {"report_type": "cpr_format_1"}
            mock_gen.generate_cpr_format1.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_latest_period(self):
        """Should use latest period when period_id is not specified."""
        mock_db = AsyncMock()
        program = _mock_program()
        latest_period = _mock_period()
        period_with_data = _mock_period()

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.reports.WBSElementRepository") as mock_wbs_repo_cls,
            patch("src.api.v1.endpoints.reports.ReportGenerator") as mock_gen_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_latest_period = AsyncMock(
                return_value=latest_period
            )
            mock_period_repo_cls.return_value.get_with_data = AsyncMock(
                return_value=period_with_data
            )
            mock_wbs_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])

            mock_gen = MagicMock()
            mock_gen.generate_cpr_format1.return_value = MagicMock()
            mock_gen.to_dict.return_value = {"report_type": "cpr_format_1"}
            mock_gen_cls.return_value = mock_gen

            result = await generate_cpr_format1(program.id, mock_db, period_id=None)

            assert result["report_type"] == "cpr_format_1"
            mock_period_repo_cls.return_value.get_latest_period.assert_called_once_with(program.id)

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        program_id = uuid4()

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await generate_cpr_format1(program_id, mock_db, period_id=None)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_period_not_found(self):
        """Should raise NotFoundError when specified period does not exist."""
        mock_db = AsyncMock()
        program = _mock_program()
        period_id = uuid4()

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_with_data = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await generate_cpr_format1(program.id, mock_db, period_id=period_id)

            assert exc_info.value.code == "PERIOD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_no_periods_found(self):
        """Should raise NotFoundError when program has no periods."""
        mock_db = AsyncMock()
        program = _mock_program()

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_latest_period = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await generate_cpr_format1(program.id, mock_db, period_id=None)

            assert exc_info.value.code == "NO_PERIODS_FOUND"


class TestGenerateCprFormat1Html:
    """Tests for generate_cpr_format1_html endpoint."""

    @pytest.mark.asyncio
    async def test_success_returns_html_response(self):
        """Should return HTMLResponse with generated content."""
        mock_db = AsyncMock()
        program = _mock_program()
        period = _mock_period()

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.reports.WBSElementRepository") as mock_wbs_repo_cls,
            patch("src.api.v1.endpoints.reports.ReportGenerator") as mock_gen_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_with_data = AsyncMock(return_value=period)
            mock_wbs_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])

            mock_gen = MagicMock()
            mock_gen.generate_cpr_format1.return_value = MagicMock()
            mock_gen.to_html.return_value = "<html><body>CPR Format 1</body></html>"
            mock_gen_cls.return_value = mock_gen

            result = await generate_cpr_format1_html(program.id, mock_db, period_id=period.id)

            assert result.status_code == 200
            assert b"CPR Format 1" in result.body

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await generate_cpr_format1_html(uuid4(), mock_db, period_id=None)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"


class TestGetProgramReportSummary:
    """Tests for get_program_report_summary endpoint."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Should return program report summary with periods and report types."""
        mock_db = AsyncMock()
        program = _mock_program()
        period = _mock_period()

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_by_program = AsyncMock(return_value=[period])

            result = await get_program_report_summary(program.id, mock_db)

            assert result["program_id"] == str(program.id)
            assert result["program_name"] == "Test Program"
            assert len(result["available_periods"]) == 1
            assert len(result["available_reports"]) == 3
            # Verify report types
            report_types = [r["report_type"] for r in result["available_reports"]]
            assert "cpr_format1" in report_types
            assert "cpr_format3" in report_types
            assert "cpr_format5" in report_types

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await get_program_report_summary(uuid4(), mock_db)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_no_periods_returns_empty_list(self):
        """Should return empty periods list when program has no periods."""
        mock_db = AsyncMock()
        program = _mock_program()

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])

            result = await get_program_report_summary(program.id, mock_db)

            assert result["available_periods"] == []
            assert len(result["available_reports"]) == 3


class TestGenerateCprFormat3:
    """Tests for generate_cpr_format3 endpoint."""

    @pytest.mark.asyncio
    async def test_success_with_baseline_id(self):
        """Should generate CPR Format 3 report for a specific baseline."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)
        baseline = _mock_baseline(program_id=program.id)

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.BaselineRepository") as mock_bl_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.reports.CPRFormat3Generator") as mock_gen_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_bl_repo_cls.return_value.get_by_id = AsyncMock(return_value=baseline)
            mock_period_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])

            mock_gen = MagicMock()
            mock_gen.to_dict.return_value = {"format": "cpr_format_3"}
            mock_gen_cls.return_value = mock_gen

            result = await generate_cpr_format3(program.id, mock_db, user, baseline_id=baseline.id)

            assert result == {"format": "cpr_format_3"}

    @pytest.mark.asyncio
    async def test_success_with_approved_baseline(self):
        """Should fall back to approved baseline when baseline_id not given."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)
        baseline = _mock_baseline(program_id=program.id)

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.BaselineRepository") as mock_bl_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.reports.CPRFormat3Generator") as mock_gen_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_bl_repo_cls.return_value.get_approved_baseline = AsyncMock(return_value=baseline)
            mock_period_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])

            mock_gen = MagicMock()
            mock_gen.to_dict.return_value = {"format": "cpr_format_3"}
            mock_gen_cls.return_value = mock_gen

            result = await generate_cpr_format3(program.id, mock_db, user, baseline_id=None)

            assert result["format"] == "cpr_format_3"
            mock_bl_repo_cls.return_value.get_approved_baseline.assert_called_once()

    @pytest.mark.asyncio
    async def test_authorization_denied(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        mock_db = AsyncMock()
        program = _mock_program()
        user = _mock_user()  # different user_id, not admin

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)

            with pytest.raises(AuthorizationError):
                await generate_cpr_format3(program.id, mock_db, user, baseline_id=None)

    @pytest.mark.asyncio
    async def test_admin_bypasses_authorization(self):
        """Should allow admin user to access any program."""
        mock_db = AsyncMock()
        program = _mock_program()
        user = _mock_user(is_admin=True)  # different owner but admin
        baseline = _mock_baseline(program_id=program.id)

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.BaselineRepository") as mock_bl_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.reports.CPRFormat3Generator") as mock_gen_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_bl_repo_cls.return_value.get_approved_baseline = AsyncMock(return_value=baseline)
            mock_period_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])

            mock_gen = MagicMock()
            mock_gen.to_dict.return_value = {"format": "cpr_format_3"}
            mock_gen_cls.return_value = mock_gen

            result = await generate_cpr_format3(program.id, mock_db, user, baseline_id=None)

            assert result["format"] == "cpr_format_3"

    @pytest.mark.asyncio
    async def test_baseline_not_found(self):
        """Should raise NotFoundError when baseline_id does not exist."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.BaselineRepository") as mock_bl_repo_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_bl_repo_cls.return_value.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await generate_cpr_format3(program.id, mock_db, user, baseline_id=uuid4())

            assert exc_info.value.code == "BASELINE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_baseline_program_mismatch(self):
        """Should raise NotFoundError when baseline belongs to another program."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)
        baseline = _mock_baseline(program_id=uuid4())  # different program

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.BaselineRepository") as mock_bl_repo_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_bl_repo_cls.return_value.get_by_id = AsyncMock(return_value=baseline)

            with pytest.raises(NotFoundError) as exc_info:
                await generate_cpr_format3(program.id, mock_db, user, baseline_id=baseline.id)

            assert exc_info.value.code == "BASELINE_MISMATCH"

    @pytest.mark.asyncio
    async def test_no_baseline_found(self):
        """Should raise NotFoundError when program has no baselines at all."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.BaselineRepository") as mock_bl_repo_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_bl_repo_cls.return_value.get_approved_baseline = AsyncMock(return_value=None)
            mock_bl_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])

            with pytest.raises(NotFoundError) as exc_info:
                await generate_cpr_format3(program.id, mock_db, user, baseline_id=None)

            assert exc_info.value.code == "NO_BASELINE_FOUND"


class TestGenerateCprFormat5:
    """Tests for generate_cpr_format5 endpoint."""

    @pytest.mark.asyncio
    async def test_success_default_params(self):
        """Should generate CPR Format 5 report with default parameters."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)
        period = _mock_period()

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.reports.VarianceExplanationRepository") as mock_ve_repo_cls,
            patch(
                "src.api.v1.endpoints.reports.ManagementReserveLogRepository"
            ) as mock_mr_repo_cls,
            patch("src.api.v1.endpoints.reports.CPRFormat5Generator") as mock_gen_cls,
            patch("src.api.v1.endpoints.reports._format5_to_dict") as mock_to_dict,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_by_program = AsyncMock(return_value=[period])
            mock_ve_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])
            mock_mr_repo_cls.return_value.get_history = AsyncMock(return_value=[])

            mock_report = MagicMock()
            mock_gen_cls.return_value.generate.return_value = mock_report
            mock_to_dict.return_value = {"format": "cpr_format_5"}

            result = await generate_cpr_format5(
                program.id,
                mock_db,
                user,
            )

            assert result == {"format": "cpr_format_5"}
            mock_gen_cls.return_value.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_without_mr_and_explanations(self):
        """Should generate report without MR and variance explanations."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)
        period = _mock_period()

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.reports.VarianceExplanationRepository") as mock_ve_repo_cls,
            patch(
                "src.api.v1.endpoints.reports.ManagementReserveLogRepository"
            ) as mock_mr_repo_cls,
            patch("src.api.v1.endpoints.reports.CPRFormat5Generator") as mock_gen_cls,
            patch("src.api.v1.endpoints.reports._format5_to_dict") as mock_to_dict,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_by_program = AsyncMock(return_value=[period])

            mock_report = MagicMock()
            mock_gen_cls.return_value.generate.return_value = mock_report
            mock_to_dict.return_value = {"format": "cpr_format_5"}

            result = await generate_cpr_format5(
                program.id,
                mock_db,
                user,
                include_mr=False,
                include_explanations=False,
            )

            assert result == {"format": "cpr_format_5"}
            # Should NOT call variance or MR repos
            mock_ve_repo_cls.return_value.get_by_program.assert_not_called()
            mock_mr_repo_cls.return_value.get_history.assert_not_called()

    @pytest.mark.asyncio
    async def test_authorization_denied(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        mock_db = AsyncMock()
        program = _mock_program()
        user = _mock_user()

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)

            with pytest.raises(AuthorizationError):
                await generate_cpr_format5(program.id, mock_db, user)

    @pytest.mark.asyncio
    async def test_no_periods_found(self):
        """Should raise NotFoundError when no periods exist."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])

            with pytest.raises(NotFoundError) as exc_info:
                await generate_cpr_format5(program.id, mock_db, user)

            assert exc_info.value.code == "NO_PERIODS_FOUND"

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        user = _mock_user()

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await generate_cpr_format5(uuid4(), mock_db, user)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"


class TestGenerateCprFormat1Pdf:
    """Tests for generate_cpr_format1_pdf endpoint."""

    @pytest.mark.asyncio
    async def test_success_returns_pdf_response(self):
        """Should return PDF bytes with correct headers."""
        mock_db = AsyncMock()
        mock_request = MagicMock()
        program = _mock_program()
        period = _mock_period()
        pdf_content = b"%PDF-1.4 fake pdf content"

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.reports.WBSElementRepository") as mock_wbs_repo_cls,
            patch("src.api.v1.endpoints.reports.ReportGenerator") as mock_gen_cls,
            patch("src.api.v1.endpoints.reports.ReportPDFGenerator") as mock_pdf_gen_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditRepository") as mock_audit_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_with_data = AsyncMock(return_value=period)
            mock_wbs_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])

            mock_gen = MagicMock()
            mock_gen.generate_cpr_format1.return_value = MagicMock()
            mock_gen_cls.return_value = mock_gen

            mock_pdf_gen_cls.return_value.generate_format1_pdf.return_value = pdf_content
            mock_audit_cls.return_value.log_generation = AsyncMock()

            result = await generate_cpr_format1_pdf(
                mock_request, program.id, mock_db, period_id=period.id
            )

            assert result.body == pdf_content
            assert result.media_type == "application/pdf"
            mock_db.commit.assert_called_once()
            mock_audit_cls.return_value.log_generation.assert_called_once()

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        mock_request = MagicMock()

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await generate_cpr_format1_pdf(mock_request, uuid4(), mock_db, period_id=None)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_landscape_parameter(self):
        """Should pass landscape parameter to PDFConfig."""
        mock_db = AsyncMock()
        mock_request = MagicMock()
        program = _mock_program()
        period = _mock_period()

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.reports.WBSElementRepository") as mock_wbs_repo_cls,
            patch("src.api.v1.endpoints.reports.ReportGenerator") as mock_gen_cls,
            patch("src.api.v1.endpoints.reports.PDFConfig") as mock_pdf_config_cls,
            patch("src.api.v1.endpoints.reports.ReportPDFGenerator") as mock_pdf_gen_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditRepository") as mock_audit_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_with_data = AsyncMock(return_value=period)
            mock_wbs_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])

            mock_gen = MagicMock()
            mock_gen.generate_cpr_format1.return_value = MagicMock()
            mock_gen_cls.return_value = mock_gen

            mock_pdf_gen_cls.return_value.generate_format1_pdf.return_value = b"pdf"
            mock_audit_cls.return_value.log_generation = AsyncMock()

            await generate_cpr_format1_pdf(
                mock_request, program.id, mock_db, period_id=period.id, landscape=False
            )

            mock_pdf_config_cls.assert_called_once_with(landscape_mode=False)


class TestGenerateCprFormat3Pdf:
    """Tests for generate_cpr_format3_pdf endpoint."""

    @pytest.mark.asyncio
    async def test_success_returns_pdf_response(self):
        """Should return PDF bytes with audit trail logged."""
        mock_db = AsyncMock()
        mock_request = MagicMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)
        baseline = _mock_baseline(program_id=program.id)
        pdf_content = b"%PDF-format3"

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.BaselineRepository") as mock_bl_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.reports.CPRFormat3Generator") as mock_gen_cls,
            patch("src.api.v1.endpoints.reports.ReportPDFGenerator") as mock_pdf_gen_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditRepository") as mock_audit_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_bl_repo_cls.return_value.get_approved_baseline = AsyncMock(return_value=baseline)
            mock_period_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])

            mock_gen_cls.return_value.generate.return_value = MagicMock()
            mock_pdf_gen_cls.return_value.generate_format3_pdf.return_value = pdf_content
            mock_audit_cls.return_value.log_generation = AsyncMock()

            result = await generate_cpr_format3_pdf(mock_request, program.id, mock_db, user)

            assert result.body == pdf_content
            assert result.media_type == "application/pdf"
            mock_audit_cls.return_value.log_generation.assert_called_once()
            # Verify generated_by is the current user
            call_kwargs = mock_audit_cls.return_value.log_generation.call_args[1]
            assert call_kwargs["generated_by"] == user_id
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_authorization_denied(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        mock_db = AsyncMock()
        mock_request = MagicMock()
        program = _mock_program()
        user = _mock_user()

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)

            with pytest.raises(AuthorizationError):
                await generate_cpr_format3_pdf(mock_request, program.id, mock_db, user)


class TestGenerateCprFormat5Pdf:
    """Tests for generate_cpr_format5_pdf endpoint."""

    @pytest.mark.asyncio
    async def test_success_returns_pdf_response(self):
        """Should return PDF bytes for Format 5."""
        mock_db = AsyncMock()
        mock_request = MagicMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)
        period = _mock_period()
        pdf_content = b"%PDF-format5-content"

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.reports.VarianceExplanationRepository") as mock_ve_repo_cls,
            patch(
                "src.api.v1.endpoints.reports.ManagementReserveLogRepository"
            ) as mock_mr_repo_cls,
            patch("src.api.v1.endpoints.reports.CPRFormat5Generator") as mock_gen_cls,
            patch("src.api.v1.endpoints.reports.ReportPDFGenerator") as mock_pdf_gen_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditRepository") as mock_audit_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_by_program = AsyncMock(return_value=[period])
            mock_ve_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])
            mock_mr_repo_cls.return_value.get_history = AsyncMock(return_value=[])

            mock_gen_cls.return_value.generate.return_value = MagicMock()
            mock_pdf_gen_cls.return_value.generate_format5_pdf.return_value = pdf_content
            mock_audit_cls.return_value.log_generation = AsyncMock()

            result = await generate_cpr_format5_pdf(mock_request, program.id, mock_db, user)

            assert result.body == pdf_content
            assert result.media_type == "application/pdf"
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_authorization_denied(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        mock_db = AsyncMock()
        mock_request = MagicMock()
        program = _mock_program()
        user = _mock_user()

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)

            with pytest.raises(AuthorizationError):
                await generate_cpr_format5_pdf(mock_request, program.id, mock_db, user)

    @pytest.mark.asyncio
    async def test_no_periods_found(self):
        """Should raise NotFoundError when no periods exist for the program."""
        mock_db = AsyncMock()
        mock_request = MagicMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])

            with pytest.raises(NotFoundError) as exc_info:
                await generate_cpr_format5_pdf(mock_request, program.id, mock_db, user)

            assert exc_info.value.code == "NO_PERIODS_FOUND"

    @pytest.mark.asyncio
    async def test_with_manager_etc(self):
        """Should pass manager_etc to generator for independent EAC method."""
        mock_db = AsyncMock()
        mock_request = MagicMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)
        period = _mock_period()
        manager_etc_val = Decimal("50000.00")

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.reports.VarianceExplanationRepository") as mock_ve_repo_cls,
            patch(
                "src.api.v1.endpoints.reports.ManagementReserveLogRepository"
            ) as mock_mr_repo_cls,
            patch("src.api.v1.endpoints.reports.CPRFormat5Generator") as mock_gen_cls,
            patch("src.api.v1.endpoints.reports.ReportPDFGenerator") as mock_pdf_gen_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditRepository") as mock_audit_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_period_repo_cls.return_value.get_by_program = AsyncMock(return_value=[period])
            mock_ve_repo_cls.return_value.get_by_program = AsyncMock(return_value=[])
            mock_mr_repo_cls.return_value.get_history = AsyncMock(return_value=[])

            mock_gen_cls.return_value.generate.return_value = MagicMock()
            mock_pdf_gen_cls.return_value.generate_format5_pdf.return_value = b"pdf"
            mock_audit_cls.return_value.log_generation = AsyncMock()

            await generate_cpr_format5_pdf(
                mock_request,
                program.id,
                mock_db,
                user,
                manager_etc=manager_etc_val,
            )

            # Verify manager_etc was passed to generator constructor
            call_kwargs = mock_gen_cls.call_args[1]
            assert call_kwargs["manager_etc"] == manager_etc_val


class TestGetReportAuditHistory:
    """Tests for get_report_audit_history endpoint."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Should return paginated audit history."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)
        entries = [_mock_audit_entry() for _ in range(3)]

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditRepository") as mock_audit_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditResponse") as mock_response_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditListResponse") as mock_list_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_audit_cls.return_value.get_by_program = AsyncMock(return_value=entries)
            mock_response_cls.model_validate.side_effect = [MagicMock() for _ in entries]

            mock_result = MagicMock()
            mock_result.total = 3
            mock_result.page = 1
            mock_result.per_page = 20
            mock_result.pages = 1
            mock_list_cls.return_value = mock_result

            result = await get_report_audit_history(
                program.id, mock_db, user, report_type=None, page=1, per_page=20
            )

            assert result.total == 3
            assert result.page == 1
            assert result.per_page == 20
            assert result.pages == 1

    @pytest.mark.asyncio
    async def test_authorization_denied(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        mock_db = AsyncMock()
        program = _mock_program()
        user = _mock_user()

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)

            with pytest.raises(AuthorizationError):
                await get_report_audit_history(
                    program.id, mock_db, user, report_type=None, page=1, per_page=20
                )

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        user = _mock_user()

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await get_report_audit_history(
                    uuid4(), mock_db, user, report_type=None, page=1, per_page=20
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_pagination(self):
        """Should return correct page of results."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)
        # 5 entries, page size 2 -> 3 pages
        entries = [_mock_audit_entry() for _ in range(5)]

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditRepository") as mock_audit_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditResponse") as mock_response_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditListResponse") as mock_list_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_audit_cls.return_value.get_by_program = AsyncMock(return_value=entries)
            mock_page_items = [MagicMock() for _ in range(2)]
            mock_response_cls.model_validate.side_effect = mock_page_items

            mock_result = MagicMock()
            mock_result.total = 5
            mock_result.page = 2
            mock_result.per_page = 2
            mock_result.pages = 3
            mock_result.items = mock_page_items
            mock_list_cls.return_value = mock_result

            result = await get_report_audit_history(
                program.id, mock_db, user, report_type=None, page=2, per_page=2
            )

            assert result.total == 5
            assert result.page == 2
            assert result.per_page == 2
            assert result.pages == 3
            assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_filter_by_report_type(self):
        """Should pass report_type filter to repository."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditRepository") as mock_audit_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_audit_cls.return_value.get_by_program = AsyncMock(return_value=[])

            await get_report_audit_history(
                program.id,
                mock_db,
                user,
                report_type="cpr_format_1",
                page=1,
                per_page=20,
            )

            mock_audit_cls.return_value.get_by_program.assert_called_once_with(
                program.id, report_type="cpr_format_1"
            )


class TestGetReportAuditStats:
    """Tests for get_report_audit_stats endpoint."""

    @pytest.mark.asyncio
    async def test_success_with_entries(self):
        """Should calculate correct statistics from audit entries."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)

        now = datetime.now(UTC)
        entry1 = _mock_audit_entry(report_type="cpr_format_1", file_format="pdf", file_size=1000)
        entry1.generated_at = now
        entry2 = _mock_audit_entry(report_type="cpr_format_1", file_format="json", file_size=500)
        entry2.generated_at = datetime(2025, 1, 1, tzinfo=UTC)
        entry3 = _mock_audit_entry(report_type="cpr_format_5", file_format="pdf", file_size=2000)
        entry3.generated_at = datetime(2025, 6, 1, tzinfo=UTC)

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditRepository") as mock_audit_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_audit_cls.return_value.get_by_program = AsyncMock(
                return_value=[entry1, entry2, entry3]
            )

            result = await get_report_audit_stats(program.id, mock_db, user)

            assert result.total_reports == 3
            assert result.by_type["cpr_format_1"] == 2
            assert result.by_type["cpr_format_5"] == 1
            assert result.by_format["pdf"] == 2
            assert result.by_format["json"] == 1
            assert result.total_size_bytes == 3500
            assert result.last_generated == now

    @pytest.mark.asyncio
    async def test_success_no_entries(self):
        """Should return zeroed stats when no entries exist."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditRepository") as mock_audit_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_audit_cls.return_value.get_by_program = AsyncMock(return_value=[])

            result = await get_report_audit_stats(program.id, mock_db, user)

            assert result.total_reports == 0
            assert result.by_type == {}
            assert result.by_format == {}
            assert result.total_size_bytes == 0
            assert result.last_generated is None

    @pytest.mark.asyncio
    async def test_authorization_denied(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        mock_db = AsyncMock()
        program = _mock_program()
        user = _mock_user()

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)

            with pytest.raises(AuthorizationError):
                await get_report_audit_stats(program.id, mock_db, user)


class TestGetRecentReportGenerations:
    """Tests for get_recent_report_generations endpoint."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Should return recent audit entries."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)
        entries = [_mock_audit_entry() for _ in range(3)]

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditRepository") as mock_audit_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditResponse") as mock_response_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_audit_cls.return_value.get_recent = AsyncMock(return_value=entries)
            mock_responses = [MagicMock() for _ in entries]
            mock_response_cls.model_validate.side_effect = mock_responses

            result = await get_recent_report_generations(program.id, mock_db, user, limit=10)

            assert len(result) == 3
            mock_audit_cls.return_value.get_recent.assert_called_once_with(program.id, limit=10)

    @pytest.mark.asyncio
    async def test_custom_limit(self):
        """Should pass custom limit to repository."""
        mock_db = AsyncMock()
        user_id = uuid4()
        program = _mock_program(owner_id=user_id)
        user = _mock_user(user_id=user_id)

        with (
            patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.reports.ReportAuditRepository") as mock_audit_cls,
        ):
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)
            mock_audit_cls.return_value.get_recent = AsyncMock(return_value=[])

            result = await get_recent_report_generations(program.id, mock_db, user, limit=5)

            assert len(result) == 0
            mock_audit_cls.return_value.get_recent.assert_called_once_with(program.id, limit=5)

    @pytest.mark.asyncio
    async def test_authorization_denied(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        mock_db = AsyncMock()
        program = _mock_program()
        user = _mock_user()

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=program)

            with pytest.raises(AuthorizationError):
                await get_recent_report_generations(program.id, mock_db, user, limit=10)

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        user = _mock_user()

        with patch("src.api.v1.endpoints.reports.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo_cls.return_value.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await get_recent_report_generations(uuid4(), mock_db, user, limit=10)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"
