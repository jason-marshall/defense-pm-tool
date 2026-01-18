"""Unit tests for Management Reserve model, repository, and schemas."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.management_reserve_log import ManagementReserveLog
from src.repositories.management_reserve_log import ManagementReserveLogRepository
from src.schemas.management_reserve import (
    ManagementReserveChangeCreate,
    ManagementReserveHistoryResponse,
    ManagementReserveLogResponse,
    ManagementReserveLogSummary,
    ManagementReserveStatus,
)

# =============================================================================
# Schema Tests
# =============================================================================


class TestManagementReserveChangeCreate:
    """Tests for ManagementReserveChangeCreate schema."""

    def test_valid_change_in(self):
        """Should create change with amount added to MR."""
        data = ManagementReserveChangeCreate(
            changes_in=Decimal("50000.00"),
            changes_out=Decimal("0"),
            reason="Contingency addition for risk mitigation",
        )
        assert data.changes_in == Decimal("50000.00")
        assert data.changes_out == Decimal("0")
        assert "Contingency" in data.reason

    def test_valid_change_out(self):
        """Should create change with amount released from MR."""
        data = ManagementReserveChangeCreate(
            changes_in=Decimal("0"),
            changes_out=Decimal("25000.00"),
            reason="Released to work package WP-123 for scope change",
        )
        assert data.changes_in == Decimal("0")
        assert data.changes_out == Decimal("25000.00")

    def test_valid_both_changes(self):
        """Should create change with both in and out amounts."""
        data = ManagementReserveChangeCreate(
            changes_in=Decimal("10000.00"),
            changes_out=Decimal("5000.00"),
            reason="Reallocation between reserves",
        )
        assert data.changes_in == Decimal("10000.00")
        assert data.changes_out == Decimal("5000.00")

    def test_with_period_id(self):
        """Should accept optional period ID."""
        period_id = uuid4()
        data = ManagementReserveChangeCreate(
            period_id=period_id,
            changes_in=Decimal("10000.00"),
            reason="Quarterly MR adjustment",
        )
        assert data.period_id == period_id

    def test_defaults(self):
        """Should have correct default values."""
        data = ManagementReserveChangeCreate()
        assert data.changes_in == Decimal("0")
        assert data.changes_out == Decimal("0")
        assert data.reason is None
        assert data.period_id is None


class TestManagementReserveLogResponse:
    """Tests for ManagementReserveLogResponse schema."""

    def test_from_attributes(self):
        """Should create from model attributes."""
        now = datetime.now()
        data = ManagementReserveLogResponse(
            id=uuid4(),
            program_id=uuid4(),
            period_id=None,
            beginning_mr=Decimal("100000.00"),
            changes_in=Decimal("0"),
            changes_out=Decimal("15000.00"),
            ending_mr=Decimal("85000.00"),
            reason="Released for engineering change",
            approved_by=uuid4(),
            created_at=now,
        )
        assert data.beginning_mr == Decimal("100000.00")
        assert data.ending_mr == Decimal("85000.00")

    def test_with_all_fields(self):
        """Should include all optional fields."""
        now = datetime.now()
        program_id = uuid4()
        period_id = uuid4()
        approver_id = uuid4()
        data = ManagementReserveLogResponse(
            id=uuid4(),
            program_id=program_id,
            period_id=period_id,
            beginning_mr=Decimal("50000.00"),
            changes_in=Decimal("20000.00"),
            changes_out=Decimal("0"),
            ending_mr=Decimal("70000.00"),
            reason="Budget increase approved",
            approved_by=approver_id,
            created_at=now,
        )
        assert data.program_id == program_id
        assert data.period_id == period_id
        assert data.approved_by == approver_id


class TestManagementReserveLogSummary:
    """Tests for ManagementReserveLogSummary schema."""

    def test_summary_fields(self):
        """Should contain summary fields with net change."""
        now = datetime.now()
        data = ManagementReserveLogSummary(
            id=uuid4(),
            period_id=uuid4(),
            beginning_mr=Decimal("100000.00"),
            ending_mr=Decimal("90000.00"),
            net_change=Decimal("-10000.00"),
            created_at=now,
        )
        assert data.beginning_mr == Decimal("100000.00")
        assert data.ending_mr == Decimal("90000.00")
        assert data.net_change == Decimal("-10000.00")


class TestManagementReserveStatus:
    """Tests for ManagementReserveStatus schema."""

    def test_default_status(self):
        """Should create status with all fields."""
        program_id = uuid4()
        now = datetime.now()
        data = ManagementReserveStatus(
            program_id=program_id,
            current_balance=Decimal("75000.00"),
            initial_mr=Decimal("100000.00"),
            total_changes_in=Decimal("10000.00"),
            total_changes_out=Decimal("35000.00"),
            change_count=5,
            last_change_at=now,
        )
        assert data.current_balance == Decimal("75000.00")
        assert data.initial_mr == Decimal("100000.00")
        assert data.total_changes_in == Decimal("10000.00")
        assert data.total_changes_out == Decimal("35000.00")
        assert data.change_count == 5
        assert data.last_change_at == now

    def test_zero_status(self):
        """Should handle zero MR status."""
        program_id = uuid4()
        data = ManagementReserveStatus(
            program_id=program_id,
            current_balance=Decimal("0"),
            initial_mr=Decimal("0"),
            total_changes_in=Decimal("0"),
            total_changes_out=Decimal("0"),
            change_count=0,
            last_change_at=None,
        )
        assert data.current_balance == Decimal("0")
        assert data.change_count == 0
        assert data.last_change_at is None


class TestManagementReserveHistoryResponse:
    """Tests for ManagementReserveHistoryResponse schema."""

    def test_empty_history(self):
        """Should handle empty history."""
        program_id = uuid4()
        data = ManagementReserveHistoryResponse(
            items=[],
            total=0,
            program_id=program_id,
            current_balance=Decimal("0"),
        )
        assert len(data.items) == 0
        assert data.total == 0

    def test_with_items(self):
        """Should contain list of log entries."""
        now = datetime.now()
        program_id = uuid4()
        item = ManagementReserveLogResponse(
            id=uuid4(),
            program_id=program_id,
            period_id=None,
            beginning_mr=Decimal("0"),
            changes_in=Decimal("100000.00"),
            changes_out=Decimal("0"),
            ending_mr=Decimal("100000.00"),
            reason="Initial MR allocation",
            approved_by=uuid4(),
            created_at=now,
        )
        data = ManagementReserveHistoryResponse(
            items=[item],
            total=1,
            program_id=program_id,
            current_balance=Decimal("100000.00"),
        )
        assert len(data.items) == 1
        assert data.total == 1
        assert data.current_balance == Decimal("100000.00")


# =============================================================================
# Repository Tests
# =============================================================================


class TestManagementReserveLogRepositoryGetByProgram:
    """Tests for get_by_program method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ManagementReserveLogRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_program_returns_list(self, repo, mock_session):
        """Should return list of MR log entries for a program."""
        program_id = uuid4()
        log = ManagementReserveLog(
            id=uuid4(),
            program_id=program_id,
            beginning_mr=Decimal("100000.00"),
            changes_in=Decimal("0"),
            changes_out=Decimal("10000.00"),
            ending_mr=Decimal("90000.00"),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [log]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_program(program_id)

        assert result == [log]
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


class TestManagementReserveLogRepositoryGetByPeriod:
    """Tests for get_by_period method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ManagementReserveLogRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_period_returns_list(self, repo, mock_session):
        """Should return MR log entries for a period."""
        period_id = uuid4()
        log = ManagementReserveLog(
            id=uuid4(),
            program_id=uuid4(),
            period_id=period_id,
            beginning_mr=Decimal("50000.00"),
            changes_in=Decimal("5000.00"),
            changes_out=Decimal("0"),
            ending_mr=Decimal("55000.00"),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [log]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_period(period_id)

        assert result == [log]


class TestManagementReserveLogRepositoryGetLatest:
    """Tests for get_latest_for_program method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ManagementReserveLogRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_latest_returns_most_recent(self, repo, mock_session):
        """Should return the most recent MR log entry."""
        program_id = uuid4()
        log = ManagementReserveLog(
            id=uuid4(),
            program_id=program_id,
            beginning_mr=Decimal("80000.00"),
            changes_in=Decimal("0"),
            changes_out=Decimal("5000.00"),
            ending_mr=Decimal("75000.00"),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = log
        mock_session.execute.return_value = mock_result

        result = await repo.get_latest_for_program(program_id)

        assert result == log
        assert result.ending_mr == Decimal("75000.00")

    @pytest.mark.asyncio
    async def test_get_latest_returns_none_when_empty(self, repo, mock_session):
        """Should return None when no entries exist."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_latest_for_program(program_id)

        assert result is None


class TestManagementReserveLogRepositoryGetHistory:
    """Tests for get_history method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ManagementReserveLogRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_history_default_limit(self, repo, mock_session):
        """Should return recent entries with default limit."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_history(program_id)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_custom_limit(self, repo, mock_session):
        """Should respect custom limit."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_history(program_id, limit=5)

        mock_session.execute.assert_called_once()


# =============================================================================
# Model Tests
# =============================================================================


class TestManagementReserveLogModel:
    """Tests for ManagementReserveLog model."""

    def test_create_model(self):
        """Should create model instance."""
        log = ManagementReserveLog(
            id=uuid4(),
            program_id=uuid4(),
            beginning_mr=Decimal("100000.00"),
            changes_in=Decimal("0"),
            changes_out=Decimal("0"),
            ending_mr=Decimal("100000.00"),
        )
        assert log.beginning_mr == Decimal("100000.00")
        assert log.ending_mr == Decimal("100000.00")

    def test_model_with_all_fields(self):
        """Should create model with all fields."""
        log = ManagementReserveLog(
            id=uuid4(),
            program_id=uuid4(),
            period_id=uuid4(),
            approved_by=uuid4(),
            beginning_mr=Decimal("150000.00"),
            changes_in=Decimal("25000.00"),
            changes_out=Decimal("50000.00"),
            ending_mr=Decimal("125000.00"),
            reason="Quarterly adjustment for risk mitigation",
        )
        assert log.beginning_mr == Decimal("150000.00")
        assert log.changes_in == Decimal("25000.00")
        assert log.changes_out == Decimal("50000.00")
        assert log.ending_mr == Decimal("125000.00")
        assert "Quarterly adjustment" in log.reason

    def test_model_repr(self):
        """Should have informative repr."""
        log = ManagementReserveLog(
            id=uuid4(),
            program_id=uuid4(),
            beginning_mr=Decimal("100000.00"),
            changes_in=Decimal("0"),
            changes_out=Decimal("0"),
            ending_mr=Decimal("100000.00"),
        )
        repr_str = repr(log)
        assert "ManagementReserveLog" in repr_str
        assert "beginning=" in repr_str
        assert "ending=" in repr_str


# =============================================================================
# MR Calculation Tests
# =============================================================================


class TestMRCalculations:
    """Tests for MR balance calculations."""

    def test_initial_mr_balance(self):
        """Should correctly initialize MR balance."""
        log = ManagementReserveLog(
            id=uuid4(),
            program_id=uuid4(),
            beginning_mr=Decimal("0"),
            changes_in=Decimal("100000.00"),
            changes_out=Decimal("0"),
            ending_mr=Decimal("100000.00"),
        )
        assert log.ending_mr == log.beginning_mr + log.changes_in - log.changes_out

    def test_mr_change_out(self):
        """Should correctly calculate MR after release."""
        log = ManagementReserveLog(
            id=uuid4(),
            program_id=uuid4(),
            beginning_mr=Decimal("100000.00"),
            changes_in=Decimal("0"),
            changes_out=Decimal("25000.00"),
            ending_mr=Decimal("75000.00"),
        )
        assert log.ending_mr == log.beginning_mr + log.changes_in - log.changes_out

    def test_mr_change_in(self):
        """Should correctly calculate MR after addition."""
        log = ManagementReserveLog(
            id=uuid4(),
            program_id=uuid4(),
            beginning_mr=Decimal("75000.00"),
            changes_in=Decimal("15000.00"),
            changes_out=Decimal("0"),
            ending_mr=Decimal("90000.00"),
        )
        assert log.ending_mr == log.beginning_mr + log.changes_in - log.changes_out

    def test_mr_both_changes(self):
        """Should correctly calculate MR with both in and out."""
        log = ManagementReserveLog(
            id=uuid4(),
            program_id=uuid4(),
            beginning_mr=Decimal("100000.00"),
            changes_in=Decimal("20000.00"),
            changes_out=Decimal("30000.00"),
            ending_mr=Decimal("90000.00"),
        )
        # Net change: +20000 - 30000 = -10000
        # Ending: 100000 - 10000 = 90000
        assert log.ending_mr == log.beginning_mr + log.changes_in - log.changes_out


# =============================================================================
# Format 5 Integration Tests
# =============================================================================


class TestFormat5Integration:
    """Tests for MR data usage in Format 5 reports."""

    def test_mr_status_for_format5(self):
        """Should provide status suitable for Format 5 reporting."""
        program_id = uuid4()
        status = ManagementReserveStatus(
            program_id=program_id,
            current_balance=Decimal("85000.00"),
            initial_mr=Decimal("100000.00"),
            total_changes_in=Decimal("10000.00"),
            total_changes_out=Decimal("25000.00"),
            change_count=3,
            last_change_at=datetime.now(),
        )
        # Format 5 needs: initial, changes, and current balance
        assert status.initial_mr == Decimal("100000.00")
        assert status.total_changes_in == Decimal("10000.00")
        assert status.total_changes_out == Decimal("25000.00")
        assert status.current_balance == Decimal("85000.00")

    def test_mr_history_for_audit(self):
        """Should provide history suitable for audit trail."""
        now = datetime.now()
        program_id = uuid4()
        logs = [
            ManagementReserveLogResponse(
                id=uuid4(),
                program_id=program_id,
                period_id=None,
                beginning_mr=Decimal("0"),
                changes_in=Decimal("100000.00"),
                changes_out=Decimal("0"),
                ending_mr=Decimal("100000.00"),
                reason="Initial allocation",
                approved_by=uuid4(),
                created_at=now,
            ),
            ManagementReserveLogResponse(
                id=uuid4(),
                program_id=program_id,
                period_id=uuid4(),
                beginning_mr=Decimal("100000.00"),
                changes_in=Decimal("0"),
                changes_out=Decimal("15000.00"),
                ending_mr=Decimal("85000.00"),
                reason="Released for engineering change order",
                approved_by=uuid4(),
                created_at=now,
            ),
        ]
        history = ManagementReserveHistoryResponse(
            items=logs,
            total=2,
            program_id=program_id,
            current_balance=Decimal("85000.00"),
        )
        # Each log entry has reason and approver for audit
        assert all(log.reason is not None for log in history.items)
        assert all(log.approved_by is not None for log in history.items)
