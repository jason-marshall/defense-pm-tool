"""Unit tests for EVMS period endpoints."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.evms import (
    add_period_data,
    calculate_all_eac_methods,
    create_period,
    delete_period,
    export_scurve,
    get_enhanced_scurve,
    get_evms_summary,
    get_period,
    list_ev_methods,
    list_periods,
    set_activity_ev_method,
    update_period,
    update_period_data,
)
from src.core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.models.evms_period import PeriodStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, user_id=None, is_admin=False):
    """Create a mock user."""
    user = MagicMock()
    user.id = user_id or uuid4()
    user.is_admin = is_admin
    return user


def _make_program(*, owner_id, budget=Decimal("1000000.00"), start_date=None):
    """Create a mock program."""
    prog = MagicMock()
    prog.id = uuid4()
    prog.owner_id = owner_id
    prog.budget_at_completion = budget
    prog.start_date = start_date or date(2026, 1, 1)
    return prog


def _make_period(
    *,
    program_id=None,
    status=PeriodStatus.DRAFT,
    period_start=None,
    period_end=None,
    cumulative_bcws=Decimal("100000.00"),
    cumulative_bcwp=Decimal("90000.00"),
    cumulative_acwp=Decimal("95000.00"),
):
    """Create a mock EVMS period."""
    p = MagicMock()
    p.id = uuid4()
    p.program_id = program_id or uuid4()
    p.status = status
    p.period_start = period_start or date(2026, 1, 1)
    p.period_end = period_end or date(2026, 1, 31)
    p.period_name = "January 2026"
    p.notes = None
    p.cumulative_bcws = cumulative_bcws
    p.cumulative_bcwp = cumulative_bcwp
    p.cumulative_acwp = cumulative_acwp
    now = datetime.now(UTC)
    p.created_at = now
    p.updated_at = now
    p.period_data = []
    return p


def _make_period_data(*, period_id=None, wbs_id=None):
    """Create a mock EVMS period data entry."""
    d = MagicMock()
    d.id = uuid4()
    d.period_id = period_id or uuid4()
    d.wbs_id = wbs_id or uuid4()
    d.bcws = Decimal("50000.00")
    d.bcwp = Decimal("45000.00")
    d.acwp = Decimal("48000.00")
    d.cumulative_bcws = Decimal("150000.00")
    d.cumulative_bcwp = Decimal("135000.00")
    d.cumulative_acwp = Decimal("144000.00")
    d.cv = Decimal("-9000.00")
    d.sv = Decimal("-15000.00")
    d.cpi = Decimal("0.94")
    d.spi = Decimal("0.90")
    now = datetime.now(UTC)
    d.created_at = now
    d.updated_at = now
    return d


# ---------------------------------------------------------------------------
# TestListPeriods
# ---------------------------------------------------------------------------


class TestListPeriods:
    """Tests for list_periods endpoint."""

    @pytest.mark.asyncio
    async def test_list_periods_success(self):
        """Should return paginated periods for a program."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        mock_db = AsyncMock()
        period = _make_period(program_id=program.id)

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.get_by_program = AsyncMock(return_value=[period])
            mock_period_repo_cls.return_value = mock_period_repo

            result = await list_periods(
                program_id=program.id,
                db=mock_db,
                current_user=user,
                status=None,
                skip=0,
                limit=50,
            )

            assert result.total == 1
            assert len(result.items) == 1
            mock_period_repo.get_by_program.assert_called_once_with(
                program.id, skip=0, limit=50, status=None
            )

    @pytest.mark.asyncio
    async def test_list_periods_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        user = _make_user()
        mock_db = AsyncMock()
        program_id = uuid4()

        with patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await list_periods(
                    program_id=program_id,
                    db=mock_db,
                    current_user=user,
                    status=None,
                    skip=0,
                    limit=50,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_periods_auth_denied(self):
        """Should raise AuthorizationError when user is not the owner."""
        user = _make_user()
        program = _make_program(owner_id=uuid4())  # different owner
        mock_db = AsyncMock()

        with patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await list_periods(
                    program_id=program.id,
                    db=mock_db,
                    current_user=user,
                    status=None,
                    skip=0,
                    limit=50,
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_list_periods_with_status_filter(self):
        """Should pass status filter to repository."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.get_by_program = AsyncMock(return_value=[])
            mock_period_repo_cls.return_value = mock_period_repo

            result = await list_periods(
                program_id=program.id,
                db=mock_db,
                current_user=user,
                status=PeriodStatus.APPROVED,
                skip=0,
                limit=50,
            )

            assert result.total == 0
            mock_period_repo.get_by_program.assert_called_once_with(
                program.id, skip=0, limit=50, status=PeriodStatus.APPROVED
            )


# ---------------------------------------------------------------------------
# TestGetPeriod
# ---------------------------------------------------------------------------


class TestGetPeriod:
    """Tests for get_period endpoint."""

    @pytest.mark.asyncio
    async def test_get_period_success(self):
        """Should return period with data."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodWithDataResponse") as mock_response_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_with_data = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_validated = MagicMock()
            mock_response_cls.model_validate.return_value = mock_validated

            result = await get_period(
                period_id=period.id,
                db=mock_db,
                current_user=user,
            )

            assert result == mock_validated
            mock_period_repo.get_with_data.assert_called_once_with(period.id)

    @pytest.mark.asyncio
    async def test_get_period_not_found(self):
        """Should raise NotFoundError when period does not exist."""
        user = _make_user()
        mock_db = AsyncMock()
        period_id = uuid4()

        with patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls:
            mock_period_repo = MagicMock()
            mock_period_repo.get_with_data = AsyncMock(return_value=None)
            mock_period_repo_cls.return_value = mock_period_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_period(period_id=period_id, db=mock_db, current_user=user)

            assert exc_info.value.code == "PERIOD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_period_program_not_found(self):
        """Should raise NotFoundError when period's program does not exist."""
        user = _make_user()
        period = _make_period()
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_with_data = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_period(period_id=period.id, db=mock_db, current_user=user)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_period_auth_denied(self):
        """Should raise AuthorizationError when user has no access."""
        user = _make_user()
        program = _make_program(owner_id=uuid4())
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_with_data = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await get_period(period_id=period.id, db=mock_db, current_user=user)

            assert exc_info.value.code == "NOT_AUTHORIZED"


# ---------------------------------------------------------------------------
# TestCreatePeriod
# ---------------------------------------------------------------------------


class TestCreatePeriod:
    """Tests for create_period endpoint."""

    @pytest.mark.asyncio
    async def test_create_period_success(self):
        """Should create a new EVMS period."""
        from src.schemas.evms_period import EVMSPeriodCreate

        user = _make_user()
        program = _make_program(owner_id=user.id)
        mock_db = AsyncMock()
        new_period = _make_period(program_id=program.id)

        period_in = EVMSPeriodCreate(
            program_id=program.id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            period_name="January 2026",
        )

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.dashboard_cache") as mock_dash_cache,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.period_exists = AsyncMock(return_value=False)
            mock_period_repo.create = AsyncMock(return_value=new_period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_dash_cache.invalidate_on_period_update = AsyncMock()

            result = await create_period(period_in=period_in, db=mock_db, current_user=user)

            assert result is not None
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(new_period)
            mock_dash_cache.invalidate_on_period_update.assert_called_once_with(program.id)

    @pytest.mark.asyncio
    async def test_create_period_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        from src.schemas.evms_period import EVMSPeriodCreate

        user = _make_user()
        mock_db = AsyncMock()
        program_id = uuid4()

        period_in = EVMSPeriodCreate(
            program_id=program_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            period_name="January 2026",
        )

        with patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_period(period_in=period_in, db=mock_db, current_user=user)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_period_auth_denied(self):
        """Should raise AuthorizationError when user is not the owner."""
        from src.schemas.evms_period import EVMSPeriodCreate

        user = _make_user()
        program = _make_program(owner_id=uuid4())
        mock_db = AsyncMock()

        period_in = EVMSPeriodCreate(
            program_id=program.id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            period_name="January 2026",
        )

        with patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await create_period(period_in=period_in, db=mock_db, current_user=user)

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_create_period_invalid_dates(self):
        """Should raise ValidationError when end date is before start date."""

        user = _make_user()
        program = _make_program(owner_id=user.id)
        mock_db = AsyncMock()

        # EVMSPeriodCreate schema validates end >= start, so build raw data
        period_in = MagicMock()
        period_in.program_id = program.id
        period_in.period_start = date(2026, 2, 1)
        period_in.period_end = date(2026, 1, 1)  # end before start

        with patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(ValidationError) as exc_info:
                await create_period(period_in=period_in, db=mock_db, current_user=user)

            assert exc_info.value.code == "INVALID_DATES"

    @pytest.mark.asyncio
    async def test_create_period_duplicate(self):
        """Should raise ConflictError when period dates already exist."""
        from src.schemas.evms_period import EVMSPeriodCreate

        user = _make_user()
        program = _make_program(owner_id=user.id)
        mock_db = AsyncMock()

        period_in = EVMSPeriodCreate(
            program_id=program.id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            period_name="January 2026",
        )

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.period_exists = AsyncMock(return_value=True)
            mock_period_repo_cls.return_value = mock_period_repo

            with pytest.raises(ConflictError) as exc_info:
                await create_period(period_in=period_in, db=mock_db, current_user=user)

            assert exc_info.value.code == "DUPLICATE_PERIOD"


# ---------------------------------------------------------------------------
# TestUpdatePeriod
# ---------------------------------------------------------------------------


class TestUpdatePeriod:
    """Tests for update_period endpoint."""

    @pytest.mark.asyncio
    async def test_update_period_success(self):
        """Should update an EVMS period."""
        from src.schemas.evms_period import EVMSPeriodUpdate

        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()

        period_in = EVMSPeriodUpdate(period_name="January 2026 (Revised)")

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.dashboard_cache") as mock_dash_cache,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo.update = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_dash_cache.invalidate_on_period_update = AsyncMock()

            result = await update_period(
                period_id=period.id,
                period_in=period_in,
                db=mock_db,
                current_user=user,
            )

            assert result is not None
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_period_not_found(self):
        """Should raise NotFoundError when period does not exist."""
        from src.schemas.evms_period import EVMSPeriodUpdate

        user = _make_user()
        mock_db = AsyncMock()
        period_in = EVMSPeriodUpdate(period_name="Updated")

        with patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls:
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=None)
            mock_period_repo_cls.return_value = mock_period_repo

            with pytest.raises(NotFoundError) as exc_info:
                await update_period(
                    period_id=uuid4(),
                    period_in=period_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "PERIOD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_period_auth_denied(self):
        """Should raise AuthorizationError when user has no access."""
        from src.schemas.evms_period import EVMSPeriodUpdate

        user = _make_user()
        program = _make_program(owner_id=uuid4())
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()
        period_in = EVMSPeriodUpdate(period_name="Updated")

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await update_period(
                    period_id=period.id,
                    period_in=period_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_update_period_approved_error(self):
        """Should raise ValidationError when period is approved and user is not admin."""
        from src.schemas.evms_period import EVMSPeriodUpdate

        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id, status=PeriodStatus.APPROVED)
        mock_db = AsyncMock()
        period_in = EVMSPeriodUpdate(period_name="Updated")

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(ValidationError) as exc_info:
                await update_period(
                    period_id=period.id,
                    period_in=period_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "PERIOD_APPROVED"


# ---------------------------------------------------------------------------
# TestDeletePeriod
# ---------------------------------------------------------------------------


class TestDeletePeriod:
    """Tests for delete_period endpoint."""

    @pytest.mark.asyncio
    async def test_delete_period_success(self):
        """Should delete an EVMS period."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.dashboard_cache") as mock_dash_cache,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo.delete = AsyncMock()
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_dash_cache.invalidate_on_period_update = AsyncMock()

            await delete_period(period_id=period.id, db=mock_db, current_user=user)

            mock_period_repo.delete.assert_called_once_with(period.id)
            mock_db.commit.assert_called_once()
            mock_dash_cache.invalidate_on_period_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_period_not_found(self):
        """Should raise NotFoundError when period does not exist."""
        user = _make_user()
        mock_db = AsyncMock()

        with patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls:
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=None)
            mock_period_repo_cls.return_value = mock_period_repo

            with pytest.raises(NotFoundError) as exc_info:
                await delete_period(period_id=uuid4(), db=mock_db, current_user=user)

            assert exc_info.value.code == "PERIOD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_period_auth_denied(self):
        """Should raise AuthorizationError when user has no access."""
        user = _make_user()
        program = _make_program(owner_id=uuid4())
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await delete_period(period_id=period.id, db=mock_db, current_user=user)

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_delete_period_approved_error(self):
        """Should raise ValidationError when deleting an approved period."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id, status=PeriodStatus.APPROVED)
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(ValidationError) as exc_info:
                await delete_period(period_id=period.id, db=mock_db, current_user=user)

            assert exc_info.value.code == "PERIOD_APPROVED"


# ---------------------------------------------------------------------------
# TestAddPeriodData
# ---------------------------------------------------------------------------


class TestAddPeriodData:
    """Tests for add_period_data endpoint."""

    def _make_data_in(self, wbs_id=None):
        """Build an EVMSPeriodDataCreate-like mock."""
        from src.schemas.evms_period import EVMSPeriodDataCreate

        return EVMSPeriodDataCreate(
            wbs_id=wbs_id or uuid4(),
            bcws=Decimal("50000.00"),
            bcwp=Decimal("45000.00"),
            acwp=Decimal("48000.00"),
        )

    @pytest.mark.asyncio
    async def test_add_period_data_success(self):
        """Should add period data for a WBS element."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        wbs = MagicMock()
        wbs.id = uuid4()
        wbs.program_id = program.id
        mock_db = AsyncMock()
        data_in = self._make_data_in(wbs_id=wbs.id)
        created_data = _make_period_data(period_id=period.id, wbs_id=wbs.id)

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.WBSElementRepository") as mock_wbs_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodDataRepository") as mock_data_repo_cls,
            patch("src.api.v1.endpoints.evms.cache_manager") as mock_cache,
            patch("src.api.v1.endpoints.evms.EVMSCalculator") as mock_calc,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo.update_cumulative_totals = AsyncMock()
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get_by_id = AsyncMock(return_value=wbs)
            mock_wbs_repo_cls.return_value = mock_wbs_repo

            mock_data_repo = MagicMock()
            mock_data_repo.data_exists = AsyncMock(return_value=False)
            mock_data_repo.get_previous_period_data = AsyncMock(return_value=None)
            mock_data_repo.create = AsyncMock(return_value=created_data)
            mock_data_repo_cls.return_value = mock_data_repo

            mock_calc.calculate_cpi.return_value = Decimal("0.94")
            mock_calc.calculate_spi.return_value = Decimal("0.90")
            mock_cache.invalidate_evms = AsyncMock()

            result = await add_period_data(
                period_id=period.id,
                data_in=data_in,
                db=mock_db,
                current_user=user,
            )

            assert result is not None
            mock_data_repo.create.assert_called_once()
            mock_period_repo.update_cumulative_totals.assert_called_once_with(period.id)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_period_data_period_not_found(self):
        """Should raise NotFoundError when period does not exist."""
        user = _make_user()
        mock_db = AsyncMock()
        data_in = self._make_data_in()

        with patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls:
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=None)
            mock_period_repo_cls.return_value = mock_period_repo

            with pytest.raises(NotFoundError) as exc_info:
                await add_period_data(
                    period_id=uuid4(),
                    data_in=data_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "PERIOD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_add_period_data_auth_denied(self):
        """Should raise AuthorizationError when user has no access."""
        user = _make_user()
        program = _make_program(owner_id=uuid4())
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()
        data_in = self._make_data_in()

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await add_period_data(
                    period_id=period.id,
                    data_in=data_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_add_period_data_approved_period(self):
        """Should raise ValidationError when period is approved."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id, status=PeriodStatus.APPROVED)
        mock_db = AsyncMock()
        data_in = self._make_data_in()

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(ValidationError) as exc_info:
                await add_period_data(
                    period_id=period.id,
                    data_in=data_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "PERIOD_APPROVED"

    @pytest.mark.asyncio
    async def test_add_period_data_wbs_not_found(self):
        """Should raise NotFoundError when WBS element does not exist."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()
        data_in = self._make_data_in()

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.WBSElementRepository") as mock_wbs_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get_by_id = AsyncMock(return_value=None)
            mock_wbs_repo_cls.return_value = mock_wbs_repo

            with pytest.raises(NotFoundError) as exc_info:
                await add_period_data(
                    period_id=period.id,
                    data_in=data_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "WBS_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_add_period_data_wbs_program_mismatch(self):
        """Should raise ValidationError when WBS is from a different program."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        wbs = MagicMock()
        wbs.id = uuid4()
        wbs.program_id = uuid4()  # different program
        mock_db = AsyncMock()
        data_in = self._make_data_in(wbs_id=wbs.id)

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.WBSElementRepository") as mock_wbs_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get_by_id = AsyncMock(return_value=wbs)
            mock_wbs_repo_cls.return_value = mock_wbs_repo

            with pytest.raises(ValidationError) as exc_info:
                await add_period_data(
                    period_id=period.id,
                    data_in=data_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "WBS_PROGRAM_MISMATCH"

    @pytest.mark.asyncio
    async def test_add_period_data_duplicate(self):
        """Should raise ConflictError when data already exists for this WBS."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        wbs = MagicMock()
        wbs.id = uuid4()
        wbs.program_id = program.id
        mock_db = AsyncMock()
        data_in = self._make_data_in(wbs_id=wbs.id)

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.WBSElementRepository") as mock_wbs_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodDataRepository") as mock_data_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get_by_id = AsyncMock(return_value=wbs)
            mock_wbs_repo_cls.return_value = mock_wbs_repo

            mock_data_repo = MagicMock()
            mock_data_repo.data_exists = AsyncMock(return_value=True)
            mock_data_repo_cls.return_value = mock_data_repo

            with pytest.raises(ConflictError) as exc_info:
                await add_period_data(
                    period_id=period.id,
                    data_in=data_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "DUPLICATE_PERIOD_DATA"

    @pytest.mark.asyncio
    async def test_add_period_data_with_previous_period(self):
        """Should accumulate cumulative values from previous period data."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        wbs = MagicMock()
        wbs.id = uuid4()
        wbs.program_id = program.id
        mock_db = AsyncMock()
        data_in = self._make_data_in(wbs_id=wbs.id)
        created_data = _make_period_data(period_id=period.id, wbs_id=wbs.id)

        prev_data = MagicMock()
        prev_data.cumulative_bcws = Decimal("100000.00")
        prev_data.cumulative_bcwp = Decimal("90000.00")
        prev_data.cumulative_acwp = Decimal("96000.00")

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.WBSElementRepository") as mock_wbs_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodDataRepository") as mock_data_repo_cls,
            patch("src.api.v1.endpoints.evms.cache_manager") as mock_cache,
            patch("src.api.v1.endpoints.evms.EVMSCalculator") as mock_calc,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo.update_cumulative_totals = AsyncMock()
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get_by_id = AsyncMock(return_value=wbs)
            mock_wbs_repo_cls.return_value = mock_wbs_repo

            mock_data_repo = MagicMock()
            mock_data_repo.data_exists = AsyncMock(return_value=False)
            mock_data_repo.get_previous_period_data = AsyncMock(return_value=prev_data)
            mock_data_repo.create = AsyncMock(return_value=created_data)
            mock_data_repo_cls.return_value = mock_data_repo

            mock_calc.calculate_cpi.return_value = Decimal("0.94")
            mock_calc.calculate_spi.return_value = Decimal("0.90")
            mock_cache.invalidate_evms = AsyncMock()

            await add_period_data(
                period_id=period.id,
                data_in=data_in,
                db=mock_db,
                current_user=user,
            )

            # Verify create was called with accumulated cumulative values
            create_call_args = mock_data_repo.create.call_args[0][0]
            assert create_call_args["cumulative_bcws"] == Decimal("150000.00")
            assert create_call_args["cumulative_bcwp"] == Decimal("135000.00")
            assert create_call_args["cumulative_acwp"] == Decimal("144000.00")


# ---------------------------------------------------------------------------
# TestUpdatePeriodData
# ---------------------------------------------------------------------------


class TestUpdatePeriodData:
    """Tests for update_period_data endpoint."""

    @pytest.mark.asyncio
    async def test_update_period_data_success(self):
        """Should update EVMS period data."""
        from src.schemas.evms_period import EVMSPeriodDataUpdate

        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        period_data = _make_period_data(period_id=period.id)
        mock_db = AsyncMock()
        data_in = EVMSPeriodDataUpdate(bcwp=Decimal("50000.00"))

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodDataRepository") as mock_data_repo_cls,
            patch("src.api.v1.endpoints.evms.cache_manager") as mock_cache,
            patch("src.api.v1.endpoints.evms.EVMSCalculator") as mock_calc,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo.update_cumulative_totals = AsyncMock()
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_data_repo = MagicMock()
            mock_data_repo.get_by_id = AsyncMock(return_value=period_data)
            mock_data_repo.get_previous_period_data = AsyncMock(return_value=None)
            mock_data_repo.update = AsyncMock(return_value=period_data)
            mock_data_repo_cls.return_value = mock_data_repo

            mock_calc.calculate_cpi.return_value = Decimal("1.04")
            mock_calc.calculate_spi.return_value = Decimal("1.00")
            mock_cache.invalidate_evms = AsyncMock()

            result = await update_period_data(
                period_id=period.id,
                data_id=period_data.id,
                data_in=data_in,
                db=mock_db,
                current_user=user,
            )

            assert result is not None
            mock_data_repo.update.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_period_data_period_not_found(self):
        """Should raise NotFoundError when period does not exist."""
        from src.schemas.evms_period import EVMSPeriodDataUpdate

        user = _make_user()
        mock_db = AsyncMock()
        data_in = EVMSPeriodDataUpdate(bcwp=Decimal("50000.00"))

        with patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls:
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=None)
            mock_period_repo_cls.return_value = mock_period_repo

            with pytest.raises(NotFoundError) as exc_info:
                await update_period_data(
                    period_id=uuid4(),
                    data_id=uuid4(),
                    data_in=data_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "PERIOD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_period_data_auth_denied(self):
        """Should raise AuthorizationError when user has no access."""
        from src.schemas.evms_period import EVMSPeriodDataUpdate

        user = _make_user()
        program = _make_program(owner_id=uuid4())
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()
        data_in = EVMSPeriodDataUpdate(bcwp=Decimal("50000.00"))

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await update_period_data(
                    period_id=period.id,
                    data_id=uuid4(),
                    data_in=data_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_update_period_data_approved_period(self):
        """Should raise ValidationError when period is approved."""
        from src.schemas.evms_period import EVMSPeriodDataUpdate

        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id, status=PeriodStatus.APPROVED)
        mock_db = AsyncMock()
        data_in = EVMSPeriodDataUpdate(bcwp=Decimal("50000.00"))

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(ValidationError) as exc_info:
                await update_period_data(
                    period_id=period.id,
                    data_id=uuid4(),
                    data_in=data_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "PERIOD_APPROVED"

    @pytest.mark.asyncio
    async def test_update_period_data_data_not_found(self):
        """Should raise NotFoundError when period data does not exist."""
        from src.schemas.evms_period import EVMSPeriodDataUpdate

        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()
        data_in = EVMSPeriodDataUpdate(bcwp=Decimal("50000.00"))

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodDataRepository") as mock_data_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_data_repo = MagicMock()
            mock_data_repo.get_by_id = AsyncMock(return_value=None)
            mock_data_repo_cls.return_value = mock_data_repo

            with pytest.raises(NotFoundError) as exc_info:
                await update_period_data(
                    period_id=period.id,
                    data_id=uuid4(),
                    data_in=data_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "PERIOD_DATA_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_period_data_recalculate_cumulative(self):
        """Should recalculate cumulative values when base values change."""
        from src.schemas.evms_period import EVMSPeriodDataUpdate

        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        period_data = _make_period_data(period_id=period.id)
        mock_db = AsyncMock()

        # Update bcws triggers recalculation
        data_in = EVMSPeriodDataUpdate(bcws=Decimal("60000.00"))

        prev_data = MagicMock()
        prev_data.cumulative_bcws = Decimal("100000.00")
        prev_data.cumulative_bcwp = Decimal("90000.00")
        prev_data.cumulative_acwp = Decimal("96000.00")

        with (
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodDataRepository") as mock_data_repo_cls,
            patch("src.api.v1.endpoints.evms.cache_manager") as mock_cache,
            patch("src.api.v1.endpoints.evms.EVMSCalculator") as mock_calc,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo.update_cumulative_totals = AsyncMock()
            mock_period_repo_cls.return_value = mock_period_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_data_repo = MagicMock()
            mock_data_repo.get_by_id = AsyncMock(return_value=period_data)
            mock_data_repo.get_previous_period_data = AsyncMock(return_value=prev_data)
            mock_data_repo.update = AsyncMock(return_value=period_data)
            mock_data_repo_cls.return_value = mock_data_repo

            mock_calc.calculate_cpi.return_value = Decimal("0.94")
            mock_calc.calculate_spi.return_value = Decimal("0.84")
            mock_cache.invalidate_evms = AsyncMock()

            await update_period_data(
                period_id=period.id,
                data_id=period_data.id,
                data_in=data_in,
                db=mock_db,
                current_user=user,
            )

            # Verify update was called with recalculated cumulative values
            update_call_args = mock_data_repo.update.call_args
            update_dict = update_call_args[0][1]
            # 100000 (prev) + 60000 (new bcws) = 160000
            assert update_dict["cumulative_bcws"] == Decimal("160000.00")


# ---------------------------------------------------------------------------
# TestGetEVMSSummary
# ---------------------------------------------------------------------------


class TestGetEVMSSummary:
    """Tests for get_evms_summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_evms_summary_success(self):
        """Should return EVMS summary for a program."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.cache_manager") as mock_cache,
            patch("src.api.v1.endpoints.evms.EVMSCalculator") as mock_calc,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.get_latest_period = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            mock_calc.calculate_cost_variance.return_value = Decimal("-5000.00")
            mock_calc.calculate_schedule_variance.return_value = Decimal("-10000.00")
            mock_calc.calculate_cpi.return_value = Decimal("0.95")
            mock_calc.calculate_spi.return_value = Decimal("0.90")
            mock_calc.calculate_eac.return_value = Decimal("1052631.58")
            mock_calc.calculate_etc.return_value = Decimal("957631.58")
            mock_calc.calculate_vac.return_value = Decimal("-52631.58")
            mock_calc.calculate_tcpi.return_value = Decimal("1.06")

            result = await get_evms_summary(
                program_id=program.id,
                db=mock_db,
                current_user=user,
            )

            assert result.program_id == program.id
            assert result.bac == program.budget_at_completion

    @pytest.mark.asyncio
    async def test_get_evms_summary_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        user = _make_user()
        mock_db = AsyncMock()

        with patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_evms_summary(program_id=uuid4(), db=mock_db, current_user=user)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_evms_summary_auth_denied(self):
        """Should raise AuthorizationError when user has no access."""
        user = _make_user()
        program = _make_program(owner_id=uuid4())
        mock_db = AsyncMock()

        with patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await get_evms_summary(program_id=program.id, db=mock_db, current_user=user)

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_get_evms_summary_cache_hit(self):
        """Should return cached summary when available."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        mock_db = AsyncMock()

        cached_data = {
            "program_id": str(program.id),
            "as_of_date": "2026-01-31",
            "bac": "1000000.00",
            "bcws": "100000.00",
            "bcwp": "90000.00",
            "acwp": "95000.00",
            "cv": "-5000.00",
            "sv": "-10000.00",
            "cpi": "0.95",
            "spi": "0.90",
            "eac": "1052631.58",
            "etc": "957631.58",
            "vac": "-52631.58",
            "tcpi": "1.06",
            "percent_complete": "9.00",
        }

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.cache_manager") as mock_cache,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_cache.get = AsyncMock(return_value=cached_data)

            result = await get_evms_summary(program_id=program.id, db=mock_db, current_user=user)

            assert result.bac == Decimal("1000000.00")

    @pytest.mark.asyncio
    async def test_get_evms_summary_with_as_of_date(self):
        """Should use date range query when as_of_date is provided."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()
        as_of = date(2026, 1, 31)

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.cache_manager") as mock_cache,
            patch("src.api.v1.endpoints.evms.EVMSCalculator") as mock_calc,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.get_by_date_range = AsyncMock(return_value=[period])
            mock_period_repo_cls.return_value = mock_period_repo

            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            mock_calc.calculate_cost_variance.return_value = Decimal("-5000.00")
            mock_calc.calculate_schedule_variance.return_value = Decimal("-10000.00")
            mock_calc.calculate_cpi.return_value = Decimal("0.95")
            mock_calc.calculate_spi.return_value = Decimal("0.90")
            mock_calc.calculate_eac.return_value = Decimal("1052631.58")
            mock_calc.calculate_etc.return_value = Decimal("957631.58")
            mock_calc.calculate_vac.return_value = Decimal("-52631.58")
            mock_calc.calculate_tcpi.return_value = Decimal("1.06")

            result = await get_evms_summary(
                program_id=program.id,
                db=mock_db,
                current_user=user,
                as_of_date=as_of,
            )

            mock_period_repo.get_by_date_range.assert_called_once_with(
                program.id, program.start_date, as_of
            )
            assert result.as_of_date == as_of

    @pytest.mark.asyncio
    async def test_get_evms_summary_no_period(self):
        """Should return zeroed summary when no periods exist."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.cache_manager") as mock_cache,
            patch("src.api.v1.endpoints.evms.EVMSCalculator") as mock_calc,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.get_latest_period = AsyncMock(return_value=None)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            mock_calc.calculate_cost_variance.return_value = Decimal("0.00")
            mock_calc.calculate_schedule_variance.return_value = Decimal("0.00")
            mock_calc.calculate_cpi.return_value = None
            mock_calc.calculate_spi.return_value = None
            mock_calc.calculate_eac.return_value = None
            mock_calc.calculate_etc.return_value = None
            mock_calc.calculate_vac.return_value = None
            mock_calc.calculate_tcpi.return_value = None

            result = await get_evms_summary(program_id=program.id, db=mock_db, current_user=user)

            assert result.bcws == Decimal("0.00")
            assert result.bcwp == Decimal("0.00")
            assert result.acwp == Decimal("0.00")


# ---------------------------------------------------------------------------
# TestListEVMethods
# ---------------------------------------------------------------------------


class TestListEVMethods:
    """Tests for list_ev_methods endpoint."""

    @pytest.mark.asyncio
    async def test_list_ev_methods_success(self):
        """Should return list of EV method information."""
        with patch("src.api.v1.endpoints.evms.get_ev_method_info") as mock_info:
            mock_info.return_value = [
                {
                    "value": "0/100",
                    "display_name": "0/100 (Discrete)",
                    "description": "0% until complete, then 100%",
                    "recommended_duration": "< 1 month",
                },
                {
                    "value": "50/50",
                    "display_name": "50/50",
                    "description": "50% at start, 100% at finish",
                    "recommended_duration": "1-2 months",
                },
            ]

            result = await list_ev_methods()

            assert len(result) == 2
            assert result[0]["value"] == "0/100"
            assert result[1]["value"] == "50/50"
            mock_info.assert_called_once()


# ---------------------------------------------------------------------------
# TestSetActivityEVMethod
# ---------------------------------------------------------------------------


class TestSetActivityEVMethod:
    """Tests for set_activity_ev_method endpoint."""

    @pytest.mark.asyncio
    async def test_set_ev_method_success(self):
        """Should set EV method on an activity."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        activity = MagicMock()
        activity.id = uuid4()
        activity.program_id = program.id
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            mock_act_repo.update = AsyncMock()
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            result = await set_activity_ev_method(
                activity_id=activity.id,
                db=mock_db,
                current_user=user,
                ev_method="percent_complete",
                milestones=None,
            )

            assert result["activity_id"] == str(activity.id)
            assert result["ev_method"] == "percent_complete"
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_ev_method_activity_not_found(self):
        """Should raise NotFoundError when activity does not exist."""
        user = _make_user()
        mock_db = AsyncMock()

        with patch("src.api.v1.endpoints.evms.ActivityRepository") as mock_act_repo_cls:
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=None)
            mock_act_repo_cls.return_value = mock_act_repo

            with pytest.raises(NotFoundError) as exc_info:
                await set_activity_ev_method(
                    activity_id=uuid4(),
                    db=mock_db,
                    current_user=user,
                    ev_method="percent_complete",
                )

            assert exc_info.value.code == "ACTIVITY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_set_ev_method_auth_denied(self):
        """Should raise AuthorizationError when user has no access."""
        user = _make_user()
        program = _make_program(owner_id=uuid4())
        activity = MagicMock()
        activity.id = uuid4()
        activity.program_id = program.id
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await set_activity_ev_method(
                    activity_id=activity.id,
                    db=mock_db,
                    current_user=user,
                    ev_method="percent_complete",
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_set_ev_method_invalid_method(self):
        """Should raise ValidationError for an invalid EV method value."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        activity = MagicMock()
        activity.id = uuid4()
        activity.program_id = program.id
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(ValidationError) as exc_info:
                await set_activity_ev_method(
                    activity_id=activity.id,
                    db=mock_db,
                    current_user=user,
                    ev_method="not_a_valid_method",
                )

            assert exc_info.value.code == "INVALID_EV_METHOD"

    @pytest.mark.asyncio
    async def test_set_ev_method_milestone_without_milestones(self):
        """Should raise ValidationError for milestone method without milestones."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        activity = MagicMock()
        activity.id = uuid4()
        activity.program_id = program.id
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(ValidationError) as exc_info:
                await set_activity_ev_method(
                    activity_id=activity.id,
                    db=mock_db,
                    current_user=user,
                    ev_method="milestone_weight",
                    milestones=None,
                )

            assert exc_info.value.code == "MILESTONES_REQUIRED"

    @pytest.mark.asyncio
    async def test_set_ev_method_invalid_weights(self):
        """Should raise ValidationError when milestone weights do not sum to 1.0."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        activity = MagicMock()
        activity.id = uuid4()
        activity.program_id = program.id
        mock_db = AsyncMock()

        bad_milestones = [
            {"name": "M1", "weight": 0.3},
            {"name": "M2", "weight": 0.3},
        ]  # sums to 0.6, not 1.0

        with (
            patch("src.api.v1.endpoints.evms.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.validate_milestone_weights") as mock_validate,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_validate.return_value = False

            with pytest.raises(ValidationError) as exc_info:
                await set_activity_ev_method(
                    activity_id=activity.id,
                    db=mock_db,
                    current_user=user,
                    ev_method="milestone_weight",
                    milestones=bad_milestones,
                )

            assert exc_info.value.code == "INVALID_MILESTONE_WEIGHTS"


# ---------------------------------------------------------------------------
# TestCalculateAllEACMethods
# ---------------------------------------------------------------------------


class TestCalculateAllEACMethods:
    """Tests for calculate_all_eac_methods endpoint."""

    @pytest.mark.asyncio
    async def test_calculate_eac_methods_success(self):
        """Should return EAC results for all methods."""
        from src.services.evms import EACMethod, EACResult

        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()

        mock_results = [
            EACResult(
                method=EACMethod.CPI,
                eac=Decimal("1052631.58"),
                etc=Decimal("957631.58"),
                vac=Decimal("-52631.58"),
                description="BAC / CPI",
            ),
        ]

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSCalculator") as mock_calc,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.get_latest_period = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_calc.calculate_all_eac_methods.return_value = mock_results

            result = await calculate_all_eac_methods(
                program_id=program.id,
                db=mock_db,
                current_user=user,
            )

            assert len(result) == 1
            assert result[0]["method"] == "cpi"
            assert result[0]["eac"] == str(Decimal("1052631.58"))

    @pytest.mark.asyncio
    async def test_calculate_eac_methods_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        user = _make_user()
        mock_db = AsyncMock()

        with patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await calculate_all_eac_methods(program_id=uuid4(), db=mock_db, current_user=user)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_calculate_eac_methods_auth_denied(self):
        """Should raise AuthorizationError when user has no access."""
        user = _make_user()
        program = _make_program(owner_id=uuid4())
        mock_db = AsyncMock()

        with patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await calculate_all_eac_methods(
                    program_id=program.id, db=mock_db, current_user=user
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_calculate_eac_methods_specific_period(self):
        """Should use the specified period_id."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()

        from src.services.evms import EACMethod, EACResult

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSCalculator") as mock_calc,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_calc.calculate_all_eac_methods.return_value = [
                EACResult(
                    method=EACMethod.TYPICAL,
                    eac=Decimal("1005000.00"),
                    etc=Decimal("910000.00"),
                    vac=Decimal("-5000.00"),
                    description="ACWP + (BAC - BCWP)",
                ),
            ]

            result = await calculate_all_eac_methods(
                program_id=program.id,
                db=mock_db,
                current_user=user,
                period_id=period.id,
            )

            assert len(result) == 1
            mock_period_repo.get_by_id.assert_called_once_with(period.id)

    @pytest.mark.asyncio
    async def test_calculate_eac_methods_period_not_found(self):
        """Should raise NotFoundError when specified period does not exist."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        mock_db = AsyncMock()
        period_id = uuid4()

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=None)
            mock_period_repo_cls.return_value = mock_period_repo

            with pytest.raises(NotFoundError) as exc_info:
                await calculate_all_eac_methods(
                    program_id=program.id,
                    db=mock_db,
                    current_user=user,
                    period_id=period_id,
                )

            assert exc_info.value.code == "PERIOD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_calculate_eac_methods_period_mismatch(self):
        """Should raise ValidationError when period belongs to different program."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=uuid4())  # different program
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.get_by_id = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            with pytest.raises(ValidationError) as exc_info:
                await calculate_all_eac_methods(
                    program_id=program.id,
                    db=mock_db,
                    current_user=user,
                    period_id=period.id,
                )

            assert exc_info.value.code == "PERIOD_PROGRAM_MISMATCH"

    @pytest.mark.asyncio
    async def test_calculate_eac_methods_zero_bac(self):
        """Should raise ValidationError when program BAC is zero."""
        user = _make_user()
        program = _make_program(owner_id=user.id, budget=Decimal("0"))
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.get_latest_period = AsyncMock(return_value=period)
            mock_period_repo_cls.return_value = mock_period_repo

            with pytest.raises(ValidationError) as exc_info:
                await calculate_all_eac_methods(
                    program_id=program.id, db=mock_db, current_user=user
                )

            assert exc_info.value.code == "ZERO_BAC"


# ---------------------------------------------------------------------------
# TestGetEnhancedSCurve
# ---------------------------------------------------------------------------


class TestGetEnhancedSCurve:
    """Tests for get_enhanced_scurve endpoint."""

    @pytest.mark.asyncio
    async def test_get_enhanced_scurve_success(self):
        """Should return enhanced S-curve data."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()

        # Build a mock EnhancedSCurveResponse
        mock_scurve_result = MagicMock()
        mock_scurve_result.program_id = program.id
        mock_scurve_result.bac = Decimal("1000000.00")
        mock_scurve_result.current_period = 1
        mock_scurve_result.percent_complete = Decimal("9.00")
        mock_scurve_result.simulation_available = False
        mock_scurve_result.data_points = []
        mock_scurve_result.eac_range = None
        mock_scurve_result.completion_range = None

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.dashboard_cache") as mock_dash_cache,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.repositories.simulation.SimulationConfigRepository") as mock_sim_cfg_cls,
            patch("src.repositories.simulation.SimulationResultRepository") as mock_sim_res_cls,
            patch("src.services.scurve_enhanced.EnhancedSCurveService") as mock_svc_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_dash_cache.get_scurve = AsyncMock(return_value=None)
            mock_dash_cache.set_scurve = AsyncMock()

            mock_period_repo = MagicMock()
            mock_period_repo.get_by_program = AsyncMock(return_value=[period])
            mock_period_repo_cls.return_value = mock_period_repo

            mock_sim_cfg = MagicMock()
            mock_sim_cfg.get_by_program = AsyncMock(return_value=[])
            mock_sim_cfg_cls.return_value = mock_sim_cfg

            mock_sim_res_cls.return_value = MagicMock()

            mock_svc = MagicMock()
            mock_svc.generate.return_value = mock_scurve_result
            mock_svc_cls.return_value = mock_svc

            result = await get_enhanced_scurve(
                program_id=program.id,
                db=mock_db,
                current_user=user,
            )

            assert result["program_id"] == str(program.id)
            assert result["from_cache"] is False
            mock_dash_cache.set_scurve.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_enhanced_scurve_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        user = _make_user()
        mock_db = AsyncMock()

        with patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_enhanced_scurve(program_id=uuid4(), db=mock_db, current_user=user)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_enhanced_scurve_auth_denied(self):
        """Should raise AuthorizationError when user has no access."""
        user = _make_user()
        program = _make_program(owner_id=uuid4())
        mock_db = AsyncMock()

        with patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await get_enhanced_scurve(program_id=program.id, db=mock_db, current_user=user)

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_get_enhanced_scurve_cache_hit(self):
        """Should return cached data when available."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        mock_db = AsyncMock()

        cached = {
            "program_id": str(program.id),
            "bac": "1000000.00",
            "data_points": [],
        }

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.dashboard_cache") as mock_dash_cache,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_dash_cache.get_scurve = AsyncMock(return_value=cached)

            result = await get_enhanced_scurve(program_id=program.id, db=mock_db, current_user=user)

            assert result["from_cache"] is True

    @pytest.mark.asyncio
    async def test_get_enhanced_scurve_with_simulation(self):
        """Should include simulation data when available."""
        user = _make_user()
        program = _make_program(owner_id=user.id)
        period = _make_period(program_id=program.id)
        mock_db = AsyncMock()

        mock_scurve_result = MagicMock()
        mock_scurve_result.program_id = program.id
        mock_scurve_result.bac = Decimal("1000000.00")
        mock_scurve_result.current_period = 1
        mock_scurve_result.percent_complete = Decimal("9.00")
        mock_scurve_result.simulation_available = True
        mock_scurve_result.data_points = []

        mock_eac_range = MagicMock()
        mock_eac_range.p10 = Decimal("950000.00")
        mock_eac_range.p50 = Decimal("1050000.00")
        mock_eac_range.p90 = Decimal("1150000.00")
        mock_eac_range.method = "simulation"
        mock_scurve_result.eac_range = mock_eac_range

        mock_completion_range = MagicMock()
        mock_completion_range.p10_days = 180
        mock_completion_range.p50_days = 210
        mock_completion_range.p90_days = 240
        mock_completion_range.p10_date = date(2026, 7, 1)
        mock_completion_range.p50_date = date(2026, 8, 1)
        mock_completion_range.p90_date = date(2026, 9, 1)
        mock_scurve_result.completion_range = mock_completion_range

        with (
            patch("src.api.v1.endpoints.evms.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.evms.dashboard_cache") as mock_dash_cache,
            patch("src.api.v1.endpoints.evms.EVMSPeriodRepository") as mock_period_repo_cls,
            patch("src.repositories.simulation.SimulationConfigRepository") as mock_sim_cfg_cls,
            patch("src.repositories.simulation.SimulationResultRepository") as mock_sim_res_cls,
            patch(
                "src.services.scurve_enhanced.build_simulation_metrics_from_result"
            ) as mock_build_metrics,
            patch("src.services.scurve_enhanced.EnhancedSCurveService") as mock_svc_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_dash_cache.get_scurve = AsyncMock(return_value=None)
            mock_dash_cache.set_scurve = AsyncMock()

            mock_period_repo = MagicMock()
            mock_period_repo.get_by_program = AsyncMock(return_value=[period])
            mock_period_repo_cls.return_value = mock_period_repo

            mock_config = MagicMock()
            mock_config.id = uuid4()
            mock_sim_cfg = MagicMock()
            mock_sim_cfg.get_by_program = AsyncMock(return_value=[mock_config])
            mock_sim_cfg_cls.return_value = mock_sim_cfg

            mock_sim_result = MagicMock()
            mock_sim_res = MagicMock()
            mock_sim_res.get_completed_by_config = AsyncMock(return_value=mock_sim_result)
            mock_sim_res_cls.return_value = mock_sim_res

            mock_build_metrics.return_value = MagicMock()

            mock_svc = MagicMock()
            mock_svc.generate.return_value = mock_scurve_result
            mock_svc_cls.return_value = mock_svc

            result = await get_enhanced_scurve(
                program_id=program.id,
                db=mock_db,
                current_user=user,
            )

            assert result["simulation_available"] is True
            assert "eac_range" in result
            assert result["eac_range"]["p50"] == str(Decimal("1050000.00"))
            assert "completion_range" in result
            assert result["completion_range"]["p50_days"] == 210


# ---------------------------------------------------------------------------
# TestExportSCurve
# ---------------------------------------------------------------------------


class TestExportSCurve:
    """Tests for export_scurve endpoint."""

    @pytest.mark.asyncio
    async def test_export_scurve_png_success(self):
        """Should export S-curve as PNG."""
        user = _make_user()
        program_id = uuid4()
        mock_db = AsyncMock()

        scurve_data = {
            "program_id": str(program_id),
            "data_points": [],
            "from_cache": False,
        }

        with (
            patch(
                "src.api.v1.endpoints.evms.get_enhanced_scurve",
                new_callable=AsyncMock,
            ) as mock_get_scurve,
            patch("src.services.scurve_export.scurve_exporter") as mock_exporter,
            patch("src.services.scurve_export.SCurveExportConfig"),
        ):
            mock_get_scurve.return_value = scurve_data
            mock_exporter.export_png.return_value = b"\x89PNG_fake_bytes"

            result = await export_scurve(
                program_id=program_id,
                db=mock_db,
                current_user=user,
                format="png",
            )

            assert result.media_type == "image/png"
            assert result.body == b"\x89PNG_fake_bytes"
            mock_exporter.export_png.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_scurve_svg_success(self):
        """Should export S-curve as SVG."""
        user = _make_user()
        program_id = uuid4()
        mock_db = AsyncMock()

        scurve_data = {
            "program_id": str(program_id),
            "data_points": [],
            "from_cache": False,
        }

        with (
            patch(
                "src.api.v1.endpoints.evms.get_enhanced_scurve",
                new_callable=AsyncMock,
            ) as mock_get_scurve,
            patch("src.services.scurve_export.scurve_exporter") as mock_exporter,
            patch("src.services.scurve_export.SCurveExportConfig"),
        ):
            mock_get_scurve.return_value = scurve_data
            mock_exporter.export_svg.return_value = b"<svg>fake</svg>"

            result = await export_scurve(
                program_id=program_id,
                db=mock_db,
                current_user=user,
                format="svg",
            )

            assert result.media_type == "image/svg+xml"
            assert result.body == b"<svg>fake</svg>"
            mock_exporter.export_svg.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_scurve_invalid_format(self):
        """Should raise ValidationError for unsupported export format."""
        user = _make_user()
        program_id = uuid4()
        mock_db = AsyncMock()

        with pytest.raises(ValidationError) as exc_info:
            await export_scurve(
                program_id=program_id,
                db=mock_db,
                current_user=user,
                format="pdf",
            )

        assert exc_info.value.code == "INVALID_FORMAT"
