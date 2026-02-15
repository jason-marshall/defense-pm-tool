"""Unit tests for Management Reserve endpoint functions."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.management_reserve import (
    get_management_reserve_status,
    get_mr_history,
    get_mr_log_entry,
    get_mr_logs_by_period,
    initialize_mr,
    record_mr_change,
)
from src.core.exceptions import NotFoundError, ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_log(
    *,
    program_id=None,
    period_id=None,
    beginning_mr=Decimal("100000"),
    changes_in=Decimal("0"),
    changes_out=Decimal("5000"),
    ending_mr=Decimal("95000"),
    reason="Test change",
    approved_by=None,
    log_id=None,
    created_at=None,
):
    """Return a MagicMock that looks like a ManagementReserveLog ORM object."""
    log = MagicMock()
    log.id = log_id or uuid4()
    log.program_id = program_id or uuid4()
    log.period_id = period_id
    log.beginning_mr = beginning_mr
    log.changes_in = changes_in
    log.changes_out = changes_out
    log.ending_mr = ending_mr
    log.reason = reason
    log.approved_by = approved_by or uuid4()
    log.created_at = created_at or datetime.now(UTC)
    return log


def _mock_db():
    """Return an AsyncMock database session."""
    db = AsyncMock()
    return db


def _mock_user():
    """Return a MagicMock authenticated user."""
    user = MagicMock()
    user.id = uuid4()
    return user


# ---------------------------------------------------------------------------
# get_management_reserve_status
# ---------------------------------------------------------------------------


class TestGetManagementReserveStatus:
    """Tests for get_management_reserve_status endpoint."""

    @pytest.mark.asyncio
    async def test_success_with_logs(self):
        """Should return calculated MR status when log entries exist."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()
        now = datetime.now(UTC)

        log1 = _make_log(
            program_id=program_id,
            beginning_mr=Decimal("0"),
            changes_in=Decimal("100000"),
            changes_out=Decimal("0"),
            ending_mr=Decimal("100000"),
            created_at=now,
        )
        log2 = _make_log(
            program_id=program_id,
            beginning_mr=Decimal("100000"),
            changes_in=Decimal("0"),
            changes_out=Decimal("5000"),
            ending_mr=Decimal("95000"),
            created_at=now,
        )

        mock_program = MagicMock()
        mock_program.id = program_id

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockMRRepo.return_value.get_by_program = AsyncMock(return_value=[log1, log2])

            result = await get_management_reserve_status(db, user, program_id)

        assert result.program_id == program_id
        assert result.current_balance == Decimal("95000")
        assert result.initial_mr == Decimal("0")
        assert result.total_changes_in == Decimal("100000")
        assert result.total_changes_out == Decimal("5000")
        assert result.change_count == 2
        assert result.last_change_at == now

    @pytest.mark.asyncio
    async def test_success_no_logs(self):
        """Should return zero status when no MR history exists."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()

        mock_program = MagicMock()
        mock_program.id = program_id

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockMRRepo.return_value.get_by_program = AsyncMock(return_value=[])

            result = await get_management_reserve_status(db, user, program_id)

        assert result.program_id == program_id
        assert result.current_balance == Decimal("0")
        assert result.initial_mr == Decimal("0")
        assert result.total_changes_in == Decimal("0")
        assert result.total_changes_out == Decimal("0")
        assert result.change_count == 0
        assert result.last_change_at is None

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()

        with patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await get_management_reserve_status(db, user, program_id)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"


# ---------------------------------------------------------------------------
# record_mr_change
# ---------------------------------------------------------------------------


class TestRecordMRChange:
    """Tests for record_mr_change endpoint."""

    @pytest.mark.asyncio
    async def test_success_change_out(self):
        """Should record an MR release (changes_out) successfully."""
        from src.schemas.management_reserve import ManagementReserveChangeCreate

        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()
        now = datetime.now(UTC)

        change_data = ManagementReserveChangeCreate(
            changes_in=Decimal("0"),
            changes_out=Decimal("5000"),
            reason="Release for over-budget work package",
        )

        mock_program = MagicMock()
        mock_program.id = program_id

        latest_log = _make_log(
            program_id=program_id,
            ending_mr=Decimal("100000"),
        )

        created_log = _make_log(
            program_id=program_id,
            beginning_mr=Decimal("100000"),
            changes_in=Decimal("0"),
            changes_out=Decimal("5000"),
            ending_mr=Decimal("95000"),
            reason="Release for over-budget work package",
            approved_by=user.id,
            created_at=now,
        )

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            mock_repo = MockMRRepo.return_value
            mock_repo.get_latest_for_program = AsyncMock(return_value=latest_log)
            mock_repo.create = AsyncMock(return_value=created_log)

            result = await record_mr_change(db, user, program_id, change_data)

        assert result.ending_mr == Decimal("95000")
        assert result.changes_out == Decimal("5000")
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(created_log)

    @pytest.mark.asyncio
    async def test_success_change_in(self):
        """Should record an MR addition (changes_in) successfully."""
        from src.schemas.management_reserve import ManagementReserveChangeCreate

        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()

        change_data = ManagementReserveChangeCreate(
            changes_in=Decimal("20000"),
            changes_out=Decimal("0"),
            reason="Additional MR from contract modification",
        )

        mock_program = MagicMock()
        latest_log = _make_log(ending_mr=Decimal("50000"))
        created_log = _make_log(
            ending_mr=Decimal("70000"),
            changes_in=Decimal("20000"),
            changes_out=Decimal("0"),
        )

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            mock_repo = MockMRRepo.return_value
            mock_repo.get_latest_for_program = AsyncMock(return_value=latest_log)
            mock_repo.create = AsyncMock(return_value=created_log)

            result = await record_mr_change(db, user, program_id, change_data)

        assert result.ending_mr == Decimal("70000")
        assert result.changes_in == Decimal("20000")

    @pytest.mark.asyncio
    async def test_success_first_change_no_prior_log(self):
        """Should use zero beginning balance when no prior log exists."""
        from src.schemas.management_reserve import ManagementReserveChangeCreate

        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()

        change_data = ManagementReserveChangeCreate(
            changes_in=Decimal("100000"),
            changes_out=Decimal("0"),
            reason="Initial MR setup",
        )

        mock_program = MagicMock()
        created_log = _make_log(
            beginning_mr=Decimal("0"),
            changes_in=Decimal("100000"),
            ending_mr=Decimal("100000"),
        )

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            mock_repo = MockMRRepo.return_value
            mock_repo.get_latest_for_program = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=created_log)

            result = await record_mr_change(db, user, program_id, change_data)

        assert result.beginning_mr == Decimal("0")
        assert result.ending_mr == Decimal("100000")

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        from src.schemas.management_reserve import ManagementReserveChangeCreate

        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()

        change_data = ManagementReserveChangeCreate(
            changes_in=Decimal("5000"),
            changes_out=Decimal("0"),
            reason="Test",
        )

        with patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await record_mr_change(db, user, program_id, change_data)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_zero_changes_validation_error(self):
        """Should raise ValidationError when both changes_in and changes_out are zero."""
        from src.schemas.management_reserve import ManagementReserveChangeCreate

        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()

        change_data = ManagementReserveChangeCreate(
            changes_in=Decimal("0"),
            changes_out=Decimal("0"),
            reason="No actual change",
        )

        mock_program = MagicMock()

        with patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)

            with pytest.raises(ValidationError) as exc_info:
                await record_mr_change(db, user, program_id, change_data)

            assert exc_info.value.code == "NO_MR_CHANGE"

    @pytest.mark.asyncio
    async def test_negative_balance_validation_error(self):
        """Should raise ValidationError when change would cause negative MR balance."""
        from src.schemas.management_reserve import ManagementReserveChangeCreate

        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()

        change_data = ManagementReserveChangeCreate(
            changes_in=Decimal("0"),
            changes_out=Decimal("200000"),
            reason="Over-release attempt",
        )

        mock_program = MagicMock()
        latest_log = _make_log(ending_mr=Decimal("100000"))

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            mock_repo = MockMRRepo.return_value
            mock_repo.get_latest_for_program = AsyncMock(return_value=latest_log)

            with pytest.raises(ValidationError) as exc_info:
                await record_mr_change(db, user, program_id, change_data)

            assert exc_info.value.code == "NEGATIVE_MR_BALANCE"

    @pytest.mark.asyncio
    async def test_period_not_found(self):
        """Should raise NotFoundError when specified period does not exist."""
        from src.schemas.management_reserve import ManagementReserveChangeCreate

        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()
        period_id = uuid4()

        change_data = ManagementReserveChangeCreate(
            period_id=period_id,
            changes_in=Decimal("5000"),
            changes_out=Decimal("0"),
            reason="Linked to period",
        )

        mock_program = MagicMock()

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.management_reserve.EVMSPeriodRepository") as MockPeriodRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockPeriodRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await record_mr_change(db, user, program_id, change_data)

            assert exc_info.value.code == "PERIOD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_period_program_mismatch(self):
        """Should raise ValidationError when period belongs to a different program."""
        from src.schemas.management_reserve import ManagementReserveChangeCreate

        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()
        other_program_id = uuid4()
        period_id = uuid4()

        change_data = ManagementReserveChangeCreate(
            period_id=period_id,
            changes_in=Decimal("5000"),
            changes_out=Decimal("0"),
            reason="Cross-program period",
        )

        mock_program = MagicMock()
        mock_program.id = program_id

        mock_period = MagicMock()
        mock_period.id = period_id
        mock_period.program_id = other_program_id

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.management_reserve.EVMSPeriodRepository") as MockPeriodRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockPeriodRepo.return_value.get = AsyncMock(return_value=mock_period)

            with pytest.raises(ValidationError) as exc_info:
                await record_mr_change(db, user, program_id, change_data)

            assert exc_info.value.code == "PERIOD_PROGRAM_MISMATCH"


# ---------------------------------------------------------------------------
# initialize_mr
# ---------------------------------------------------------------------------


class TestInitializeMR:
    """Tests for initialize_mr endpoint."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Should initialize MR with the given amount."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()
        initial_amount = Decimal("250000")
        now = datetime.now(UTC)

        mock_program = MagicMock()
        mock_program.id = program_id

        created_log = _make_log(
            program_id=program_id,
            beginning_mr=Decimal("0"),
            changes_in=initial_amount,
            changes_out=Decimal("0"),
            ending_mr=initial_amount,
            reason="Initial Management Reserve allocation",
            approved_by=user.id,
            created_at=now,
        )

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            mock_repo = MockMRRepo.return_value
            mock_repo.get_latest_for_program = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=created_log)

            result = await initialize_mr(db, user, program_id, initial_amount=initial_amount)

        assert result.ending_mr == initial_amount
        assert result.beginning_mr == Decimal("0")
        assert result.changes_in == initial_amount
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(created_log)

    @pytest.mark.asyncio
    async def test_success_with_custom_reason(self):
        """Should use provided reason instead of default."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()
        initial_amount = Decimal("500000")
        custom_reason = "Per contract clause 42.b MR allocation"

        mock_program = MagicMock()
        created_log = _make_log(
            ending_mr=initial_amount,
            reason=custom_reason,
        )

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            mock_repo = MockMRRepo.return_value
            mock_repo.get_latest_for_program = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=created_log)

            result = await initialize_mr(
                db,
                user,
                program_id,
                initial_amount=initial_amount,
                reason=custom_reason,
            )

        # Verify create was called with the custom reason
        call_args = mock_repo.create.call_args[0][0]
        assert call_args["reason"] == custom_reason

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()

        with patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await initialize_mr(db, user, program_id, initial_amount=Decimal("100000"))

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_already_initialized(self):
        """Should raise ValidationError when MR is already initialized."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()

        mock_program = MagicMock()
        existing_log = _make_log(ending_mr=Decimal("100000"))

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockMRRepo.return_value.get_latest_for_program = AsyncMock(return_value=existing_log)

            with pytest.raises(ValidationError) as exc_info:
                await initialize_mr(db, user, program_id, initial_amount=Decimal("100000"))

            assert exc_info.value.code == "MR_ALREADY_INITIALIZED"


# ---------------------------------------------------------------------------
# get_mr_history
# ---------------------------------------------------------------------------


class TestGetMRHistory:
    """Tests for get_mr_history endpoint."""

    @pytest.mark.asyncio
    async def test_success_with_entries(self):
        """Should return history with entries, total count, and current balance."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()
        now = datetime.now(UTC)

        log1 = _make_log(program_id=program_id, ending_mr=Decimal("100000"))
        log2 = _make_log(program_id=program_id, ending_mr=Decimal("95000"))

        mock_program = MagicMock()
        latest_log = _make_log(ending_mr=Decimal("95000"))

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            mock_repo = MockMRRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[log1, log2])
            mock_repo.get_by_program = AsyncMock(return_value=[log1, log2])
            mock_repo.get_latest_for_program = AsyncMock(return_value=latest_log)

            result = await get_mr_history(db, user, program_id)

        assert result.total == 2
        assert len(result.items) == 2
        assert result.program_id == program_id
        assert result.current_balance == Decimal("95000")

    @pytest.mark.asyncio
    async def test_success_empty_history(self):
        """Should return empty history when no MR logs exist."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()

        mock_program = MagicMock()

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            mock_repo = MockMRRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[])
            mock_repo.get_by_program = AsyncMock(return_value=[])
            mock_repo.get_latest_for_program = AsyncMock(return_value=None)

            result = await get_mr_history(db, user, program_id)

        assert result.total == 0
        assert len(result.items) == 0
        assert result.current_balance == Decimal("0")

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()

        with patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await get_mr_history(db, user, program_id)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_custom_limit_passed_to_repo(self):
        """Should pass the limit parameter to the repository."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()

        mock_program = MagicMock()

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            mock_repo = MockMRRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[])
            mock_repo.get_by_program = AsyncMock(return_value=[])
            mock_repo.get_latest_for_program = AsyncMock(return_value=None)

            await get_mr_history(db, user, program_id, limit=50)

            mock_repo.get_history.assert_called_once_with(program_id, limit=50)


# ---------------------------------------------------------------------------
# get_mr_log_entry
# ---------------------------------------------------------------------------


class TestGetMRLogEntry:
    """Tests for get_mr_log_entry endpoint."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Should return a specific MR log entry by ID."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()
        log_id = uuid4()

        mock_program = MagicMock()
        mock_program.id = program_id

        log_entry = _make_log(
            log_id=log_id,
            program_id=program_id,
            ending_mr=Decimal("95000"),
        )

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockMRRepo.return_value.get = AsyncMock(return_value=log_entry)

            result = await get_mr_log_entry(db, user, program_id, log_id)

        assert result.id == log_id
        assert result.ending_mr == Decimal("95000")

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()
        log_id = uuid4()

        with patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await get_mr_log_entry(db, user, program_id, log_id)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_log_entry_not_found(self):
        """Should raise NotFoundError when log entry does not exist."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()
        log_id = uuid4()

        mock_program = MagicMock()
        mock_program.id = program_id

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockMRRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await get_mr_log_entry(db, user, program_id, log_id)

            assert exc_info.value.code == "MR_LOG_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_log_entry_wrong_program(self):
        """Should raise NotFoundError when log entry belongs to a different program."""
        db = _mock_db()
        user = _mock_user()
        program_id = uuid4()
        other_program_id = uuid4()
        log_id = uuid4()

        mock_program = MagicMock()
        mock_program.id = program_id

        log_entry = _make_log(
            log_id=log_id,
            program_id=other_program_id,
        )

        with (
            patch("src.api.v1.endpoints.management_reserve.ProgramRepository") as MockProgramRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockMRRepo.return_value.get = AsyncMock(return_value=log_entry)

            with pytest.raises(NotFoundError) as exc_info:
                await get_mr_log_entry(db, user, program_id, log_id)

            assert exc_info.value.code == "MR_LOG_NOT_FOUND"


# ---------------------------------------------------------------------------
# get_mr_logs_by_period
# ---------------------------------------------------------------------------


class TestGetMRLogsByPeriod:
    """Tests for get_mr_logs_by_period endpoint."""

    @pytest.mark.asyncio
    async def test_success_with_logs(self):
        """Should return MR logs for the specified period."""
        db = _mock_db()
        user = _mock_user()
        period_id = uuid4()

        mock_period = MagicMock()
        mock_period.id = period_id

        log1 = _make_log(period_id=period_id, ending_mr=Decimal("95000"))
        log2 = _make_log(period_id=period_id, ending_mr=Decimal("90000"))

        with (
            patch("src.api.v1.endpoints.management_reserve.EVMSPeriodRepository") as MockPeriodRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockPeriodRepo.return_value.get = AsyncMock(return_value=mock_period)
            MockMRRepo.return_value.get_by_period = AsyncMock(return_value=[log1, log2])

            result = await get_mr_logs_by_period(db, user, period_id)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_success_empty(self):
        """Should return empty list when no MR logs exist for the period."""
        db = _mock_db()
        user = _mock_user()
        period_id = uuid4()

        mock_period = MagicMock()
        mock_period.id = period_id

        with (
            patch("src.api.v1.endpoints.management_reserve.EVMSPeriodRepository") as MockPeriodRepo,
            patch(
                "src.api.v1.endpoints.management_reserve.ManagementReserveLogRepository"
            ) as MockMRRepo,
        ):
            MockPeriodRepo.return_value.get = AsyncMock(return_value=mock_period)
            MockMRRepo.return_value.get_by_period = AsyncMock(return_value=[])

            result = await get_mr_logs_by_period(db, user, period_id)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_period_not_found(self):
        """Should raise NotFoundError when period does not exist."""
        db = _mock_db()
        user = _mock_user()
        period_id = uuid4()

        with patch(
            "src.api.v1.endpoints.management_reserve.EVMSPeriodRepository"
        ) as MockPeriodRepo:
            MockPeriodRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await get_mr_logs_by_period(db, user, period_id)

            assert exc_info.value.code == "PERIOD_NOT_FOUND"
