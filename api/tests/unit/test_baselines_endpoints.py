"""Unit tests for Baseline management endpoints."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.baselines import (
    approve_baseline,
    compare_baseline,
    create_baseline,
    delete_baseline,
    get_approved_baseline,
    get_baseline,
    list_baselines,
    unapprove_baseline,
    update_baseline,
)


def _make_mock_baseline(**overrides):
    """Create a mock baseline with sensible defaults."""
    now = datetime.now(UTC)
    defaults = {
        "id": uuid4(),
        "program_id": uuid4(),
        "name": "Baseline v1",
        "version": 1,
        "description": "Test baseline",
        "is_approved": False,
        "approved_at": None,
        "approved_by_id": None,
        "total_bac": Decimal("100000.00"),
        "scheduled_finish": date(2026, 12, 31),
        "activity_count": 10,
        "wbs_count": 5,
        "created_at": now,
        "updated_at": now,
        "created_by_id": uuid4(),
        "schedule_snapshot": {"activities": [], "dependencies": []},
        "cost_snapshot": {"total_bac": "100000.00"},
        "wbs_snapshot": {"wbs_elements": []},
    }
    defaults.update(overrides)
    mock = MagicMock()
    for key, value in defaults.items():
        setattr(mock, key, value)
    return mock


class TestListBaselines:
    """Tests for list_baselines endpoint."""

    @pytest.mark.asyncio
    async def test_list_baselines_success(self):
        """Should return paginated baselines for a program."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        baseline1 = _make_mock_baseline(program_id=program_id, version=2, name="BL v2")
        baseline2 = _make_mock_baseline(program_id=program_id, version=1, name="BL v1")

        with (
            patch("src.api.v1.endpoints.baselines.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineSummary") as mock_summary_cls,
            patch("src.api.v1.endpoints.baselines.BaselineListResponse") as mock_list_resp_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_bl_repo = MagicMock()
            mock_bl_repo.get_by_program = AsyncMock(return_value=[baseline1, baseline2])
            mock_bl_repo.count_by_program = AsyncMock(return_value=2)
            mock_bl_repo_cls.return_value = mock_bl_repo

            summary1 = MagicMock()
            summary2 = MagicMock()
            mock_summary_cls.model_validate.side_effect = [summary1, summary2]

            mock_result = MagicMock()
            mock_result.total = 2
            mock_result.page = 1
            mock_result.per_page = 20
            mock_result.items = [summary1, summary2]
            mock_list_resp_cls.return_value = mock_result

            result = await list_baselines(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
                page=1,
                per_page=20,
            )

            assert result.total == 2
            assert result.page == 1
            assert result.per_page == 20
            assert len(result.items) == 2
            mock_bl_repo.get_by_program.assert_called_once_with(program_id, skip=0, limit=20)

    @pytest.mark.asyncio
    async def test_list_baselines_pagination(self):
        """Should calculate correct skip offset for page 3."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()

        with (
            patch("src.api.v1.endpoints.baselines.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_bl_repo = MagicMock()
            mock_bl_repo.get_by_program = AsyncMock(return_value=[])
            mock_bl_repo.count_by_program = AsyncMock(return_value=50)
            mock_bl_repo_cls.return_value = mock_bl_repo

            result = await list_baselines(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
                page=3,
                per_page=10,
            )

            # page=3, per_page=10 => skip=(3-1)*10=20
            mock_bl_repo.get_by_program.assert_called_once_with(program_id, skip=20, limit=10)
            assert result.pages == 5  # 50 / 10 = 5

    @pytest.mark.asyncio
    async def test_list_baselines_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        from src.core.exceptions import NotFoundError

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()

        with patch("src.api.v1.endpoints.baselines.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await list_baselines(
                    db=mock_db,
                    current_user=mock_user,
                    program_id=program_id,
                    page=1,
                    per_page=20,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_baselines_empty(self):
        """Should return empty list with correct page count when no baselines."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()

        with (
            patch("src.api.v1.endpoints.baselines.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_bl_repo = MagicMock()
            mock_bl_repo.get_by_program = AsyncMock(return_value=[])
            mock_bl_repo.count_by_program = AsyncMock(return_value=0)
            mock_bl_repo_cls.return_value = mock_bl_repo

            result = await list_baselines(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
                page=1,
                per_page=20,
            )

            assert result.total == 0
            assert result.pages == 1  # 0 total => pages=1 (not 0)
            assert len(result.items) == 0


class TestCreateBaseline:
    """Tests for create_baseline endpoint."""

    @pytest.mark.asyncio
    async def test_create_baseline_success(self):
        """Should create a baseline snapshot successfully."""
        from src.schemas.baseline import BaselineCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        baseline = _make_mock_baseline(program_id=program_id, created_by_id=mock_user.id)

        data = BaselineCreate(
            program_id=program_id,
            name="PMB v1",
            description="Initial performance measurement baseline",
            include_schedule=True,
            include_cost=True,
            include_wbs=True,
        )

        with (
            patch("src.api.v1.endpoints.baselines.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineResponse") as mock_response_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_bl_repo = MagicMock()
            mock_bl_repo.create_snapshot = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            mock_response = MagicMock()
            mock_response_cls.model_validate.return_value = mock_response

            result = await create_baseline(
                db=mock_db,
                current_user=mock_user,
                baseline_data=data,
            )

            assert result is mock_response
            mock_bl_repo.create_snapshot.assert_called_once_with(
                program_id=program_id,
                name="PMB v1",
                description="Initial performance measurement baseline",
                created_by_id=mock_user.id,
                include_schedule=True,
                include_cost=True,
                include_wbs=True,
            )
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(baseline)

    @pytest.mark.asyncio
    async def test_create_baseline_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        from src.core.exceptions import NotFoundError
        from src.schemas.baseline import BaselineCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        data = BaselineCreate(
            program_id=program_id,
            name="PMB v1",
        )

        with patch("src.api.v1.endpoints.baselines.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    baseline_data=data,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"
            mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_baseline_schedule_only(self):
        """Should create baseline with schedule only (no cost/wbs)."""
        from src.schemas.baseline import BaselineCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()

        baseline = _make_mock_baseline(
            program_id=program_id,
            cost_snapshot=None,
            wbs_snapshot=None,
        )

        data = BaselineCreate(
            program_id=program_id,
            name="Schedule BL",
            include_schedule=True,
            include_cost=False,
            include_wbs=False,
        )

        with (
            patch("src.api.v1.endpoints.baselines.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineResponse") as mock_response_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_bl_repo = MagicMock()
            mock_bl_repo.create_snapshot = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            mock_response_cls.model_validate.return_value = MagicMock()

            await create_baseline(
                db=mock_db,
                current_user=mock_user,
                baseline_data=data,
            )

            mock_bl_repo.create_snapshot.assert_called_once_with(
                program_id=program_id,
                name="Schedule BL",
                description=None,
                created_by_id=mock_user.id,
                include_schedule=True,
                include_cost=False,
                include_wbs=False,
            )


class TestGetBaseline:
    """Tests for get_baseline endpoint."""

    @pytest.mark.asyncio
    async def test_get_baseline_success(self):
        """Should return baseline with full snapshot data."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()
        baseline = _make_mock_baseline(id=baseline_id)

        with patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls:
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            with patch("src.api.v1.endpoints.baselines.BaselineResponse") as mock_response_cls:
                mock_response = MagicMock()
                mock_response.schedule_snapshot = {"activities": []}
                mock_response.cost_snapshot = {"total_bac": "100000.00"}
                mock_response.wbs_snapshot = {"wbs_elements": []}
                mock_response_cls.model_validate.return_value = mock_response

                result = await get_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    baseline_id=baseline_id,
                    include_snapshots=True,
                )

                assert result is mock_response
                assert result.schedule_snapshot is not None
                assert result.cost_snapshot is not None
                assert result.wbs_snapshot is not None

    @pytest.mark.asyncio
    async def test_get_baseline_without_snapshots(self):
        """Should return baseline with snapshot fields set to None when excluded."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()
        baseline = _make_mock_baseline(id=baseline_id)

        with patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls:
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            with patch("src.api.v1.endpoints.baselines.BaselineResponse") as mock_response_cls:
                mock_response = MagicMock()
                mock_response_cls.model_validate.return_value = mock_response

                result = await get_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    baseline_id=baseline_id,
                    include_snapshots=False,
                )

                assert result.schedule_snapshot is None
                assert result.cost_snapshot is None
                assert result.wbs_snapshot is None

    @pytest.mark.asyncio
    async def test_get_baseline_not_found(self):
        """Should raise NotFoundError when baseline does not exist."""
        from src.core.exceptions import NotFoundError

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()

        with patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls:
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=None)
            mock_bl_repo_cls.return_value = mock_bl_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    baseline_id=baseline_id,
                )

            assert exc_info.value.code == "BASELINE_NOT_FOUND"


class TestUpdateBaseline:
    """Tests for update_baseline endpoint."""

    @pytest.mark.asyncio
    async def test_update_baseline_name(self):
        """Should update baseline name successfully."""
        from src.schemas.baseline import BaselineUpdate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()
        baseline = _make_mock_baseline(id=baseline_id, name="Old Name")

        update_data = BaselineUpdate(name="New Name")

        with (
            patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineResponse") as mock_response_cls,
        ):
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            mock_response = MagicMock()
            mock_response_cls.model_validate.return_value = mock_response

            result = await update_baseline(
                db=mock_db,
                current_user=mock_user,
                baseline_id=baseline_id,
                update_data=update_data,
            )

            assert result is mock_response
            assert baseline.name == "New Name"
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(baseline)

    @pytest.mark.asyncio
    async def test_update_baseline_description(self):
        """Should update baseline description successfully."""
        from src.schemas.baseline import BaselineUpdate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()
        baseline = _make_mock_baseline(id=baseline_id, description="Old desc")

        update_data = BaselineUpdate(description="Updated description")

        with (
            patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineResponse") as mock_response_cls,
        ):
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            mock_response_cls.model_validate.return_value = MagicMock()

            await update_baseline(
                db=mock_db,
                current_user=mock_user,
                baseline_id=baseline_id,
                update_data=update_data,
            )

            assert baseline.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_baseline_not_found(self):
        """Should raise NotFoundError when baseline does not exist."""
        from src.core.exceptions import NotFoundError
        from src.schemas.baseline import BaselineUpdate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()
        update_data = BaselineUpdate(name="New Name")

        with patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls:
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=None)
            mock_bl_repo_cls.return_value = mock_bl_repo

            with pytest.raises(NotFoundError) as exc_info:
                await update_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    baseline_id=baseline_id,
                    update_data=update_data,
                )

            assert exc_info.value.code == "BASELINE_NOT_FOUND"
            mock_db.commit.assert_not_called()


class TestDeleteBaseline:
    """Tests for delete_baseline endpoint."""

    @pytest.mark.asyncio
    async def test_delete_baseline_success(self):
        """Should soft delete a non-approved baseline."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()
        baseline = _make_mock_baseline(id=baseline_id, is_approved=False)

        with patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls:
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=baseline)
            mock_bl_repo.delete = AsyncMock()
            mock_bl_repo_cls.return_value = mock_bl_repo

            result = await delete_baseline(
                db=mock_db,
                current_user=mock_user,
                baseline_id=baseline_id,
            )

            assert result is None
            mock_bl_repo.delete.assert_called_once_with(baseline_id)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_baseline_not_found(self):
        """Should raise NotFoundError when baseline does not exist."""
        from src.core.exceptions import NotFoundError

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()

        with patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls:
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=None)
            mock_bl_repo_cls.return_value = mock_bl_repo

            with pytest.raises(NotFoundError) as exc_info:
                await delete_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    baseline_id=baseline_id,
                )

            assert exc_info.value.code == "BASELINE_NOT_FOUND"
            mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_approved_baseline_raises_validation_error(self):
        """Should raise ValidationError when deleting an approved baseline."""
        from src.core.exceptions import ValidationError

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()
        baseline = _make_mock_baseline(id=baseline_id, is_approved=True)

        with patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls:
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            with pytest.raises(ValidationError) as exc_info:
                await delete_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    baseline_id=baseline_id,
                )

            assert exc_info.value.code == "APPROVED_BASELINE_DELETE"
            mock_db.commit.assert_not_called()


class TestApproveBaseline:
    """Tests for approve_baseline endpoint."""

    @pytest.mark.asyncio
    async def test_approve_baseline_success(self):
        """Should approve a baseline as PMB."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()
        now = datetime.now(UTC)
        baseline = _make_mock_baseline(
            id=baseline_id,
            is_approved=True,
            approved_at=now,
            approved_by_id=mock_user.id,
        )

        with (
            patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineResponse") as mock_response_cls,
        ):
            mock_bl_repo = MagicMock()
            mock_bl_repo.approve_baseline = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            mock_response = MagicMock()
            mock_response_cls.model_validate.return_value = mock_response

            result = await approve_baseline(
                db=mock_db,
                current_user=mock_user,
                baseline_id=baseline_id,
                approval_data=None,
            )

            assert result is mock_response
            mock_bl_repo.approve_baseline.assert_called_once_with(baseline_id, mock_user.id)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(baseline)

    @pytest.mark.asyncio
    async def test_approve_baseline_not_found(self):
        """Should raise NotFoundError when baseline does not exist."""
        from src.core.exceptions import NotFoundError

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()

        with patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls:
            mock_bl_repo = MagicMock()
            mock_bl_repo.approve_baseline = AsyncMock(return_value=None)
            mock_bl_repo_cls.return_value = mock_bl_repo

            with pytest.raises(NotFoundError) as exc_info:
                await approve_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    baseline_id=baseline_id,
                    approval_data=None,
                )

            assert exc_info.value.code == "BASELINE_NOT_FOUND"
            mock_db.commit.assert_not_called()


class TestUnapproveBaseline:
    """Tests for unapprove_baseline endpoint."""

    @pytest.mark.asyncio
    async def test_unapprove_baseline_success(self):
        """Should unapprove a currently approved baseline."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()
        now = datetime.now(UTC)
        baseline = _make_mock_baseline(
            id=baseline_id,
            is_approved=True,
            approved_at=now,
            approved_by_id=uuid4(),
        )

        with (
            patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineResponse") as mock_response_cls,
        ):
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            mock_response = MagicMock()
            mock_response_cls.model_validate.return_value = mock_response

            result = await unapprove_baseline(
                db=mock_db,
                current_user=mock_user,
                baseline_id=baseline_id,
            )

            assert result is mock_response
            assert baseline.is_approved is False
            assert baseline.approved_at is None
            assert baseline.approved_by_id is None
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(baseline)

    @pytest.mark.asyncio
    async def test_unapprove_baseline_not_found(self):
        """Should raise NotFoundError when baseline does not exist."""
        from src.core.exceptions import NotFoundError

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()

        with patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls:
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=None)
            mock_bl_repo_cls.return_value = mock_bl_repo

            with pytest.raises(NotFoundError) as exc_info:
                await unapprove_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    baseline_id=baseline_id,
                )

            assert exc_info.value.code == "BASELINE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_unapprove_baseline_not_approved(self):
        """Should raise ValidationError when baseline is not currently approved."""
        from src.core.exceptions import ValidationError

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()
        baseline = _make_mock_baseline(id=baseline_id, is_approved=False)

        with patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls:
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            with pytest.raises(ValidationError) as exc_info:
                await unapprove_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    baseline_id=baseline_id,
                )

            assert exc_info.value.code == "BASELINE_NOT_APPROVED"
            mock_db.commit.assert_not_called()


class TestCompareBaseline:
    """Tests for compare_baseline endpoint."""

    @pytest.mark.asyncio
    async def test_compare_baseline_success(self):
        """Should return comparison results with details."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()
        baseline = _make_mock_baseline(
            id=baseline_id,
            schedule_snapshot={"activities": [{"id": "abc"}]},
            cost_snapshot={"total_bac": "100000.00"},
        )

        mock_comparison_result = MagicMock()
        mock_comparison_dict = {
            "baseline_id": str(baseline_id),
            "baseline_name": "Baseline v1",
            "bac_variance": "500.00",
            "schedule_variance_days": -3,
        }

        with (
            patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls,
            patch("src.services.baseline_comparison.BaselineComparisonService") as mock_service_cls,
            patch("src.services.baseline_comparison.comparison_result_to_dict") as mock_to_dict,
        ):
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            mock_service = MagicMock()
            mock_service.compare_to_current = AsyncMock(return_value=mock_comparison_result)
            mock_service_cls.return_value = mock_service

            mock_to_dict.return_value = mock_comparison_dict

            result = await compare_baseline(
                db=mock_db,
                current_user=mock_user,
                baseline_id=baseline_id,
                include_details=True,
            )

            assert result == mock_comparison_dict
            mock_service.compare_to_current.assert_called_once_with(baseline, True)
            mock_to_dict.assert_called_once_with(mock_comparison_result)

    @pytest.mark.asyncio
    async def test_compare_baseline_not_found(self):
        """Should raise NotFoundError when baseline does not exist."""
        from src.core.exceptions import NotFoundError

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()

        with patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls:
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=None)
            mock_bl_repo_cls.return_value = mock_bl_repo

            with pytest.raises(NotFoundError) as exc_info:
                await compare_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    baseline_id=baseline_id,
                )

            assert exc_info.value.code == "BASELINE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_compare_baseline_no_snapshot_data(self):
        """Should raise ValidationError when baseline has no snapshot data."""
        from src.core.exceptions import ValidationError

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()
        baseline = _make_mock_baseline(
            id=baseline_id,
            schedule_snapshot=None,
            cost_snapshot=None,
        )

        with patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls:
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            with pytest.raises(ValidationError) as exc_info:
                await compare_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    baseline_id=baseline_id,
                )

            assert exc_info.value.code == "BASELINE_NO_SNAPSHOT"

    @pytest.mark.asyncio
    async def test_compare_baseline_without_details(self):
        """Should pass include_details=False to the comparison service."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        baseline_id = uuid4()
        baseline = _make_mock_baseline(
            id=baseline_id,
            schedule_snapshot={"activities": []},
        )

        with (
            patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls,
            patch("src.services.baseline_comparison.BaselineComparisonService") as mock_service_cls,
            patch("src.services.baseline_comparison.comparison_result_to_dict") as mock_to_dict,
        ):
            mock_bl_repo = MagicMock()
            mock_bl_repo.get = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            mock_service = MagicMock()
            mock_service.compare_to_current = AsyncMock(return_value=MagicMock())
            mock_service_cls.return_value = mock_service

            mock_to_dict.return_value = {}

            await compare_baseline(
                db=mock_db,
                current_user=mock_user,
                baseline_id=baseline_id,
                include_details=False,
            )

            mock_service.compare_to_current.assert_called_once_with(baseline, False)


class TestGetApprovedBaseline:
    """Tests for get_approved_baseline endpoint."""

    @pytest.mark.asyncio
    async def test_get_approved_baseline_success(self):
        """Should return the approved baseline for a program."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        baseline = _make_mock_baseline(
            program_id=program_id,
            is_approved=True,
            approved_at=datetime.now(UTC),
        )

        with (
            patch("src.api.v1.endpoints.baselines.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineResponse") as mock_response_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_bl_repo = MagicMock()
            mock_bl_repo.get_approved_baseline = AsyncMock(return_value=baseline)
            mock_bl_repo_cls.return_value = mock_bl_repo

            mock_response = MagicMock()
            mock_response_cls.model_validate.return_value = mock_response

            result = await get_approved_baseline(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
            )

            assert result is mock_response
            mock_bl_repo.get_approved_baseline.assert_called_once_with(program_id)

    @pytest.mark.asyncio
    async def test_get_approved_baseline_none_approved(self):
        """Should return None when no baseline is approved."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()

        with (
            patch("src.api.v1.endpoints.baselines.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.baselines.BaselineRepository") as mock_bl_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_bl_repo = MagicMock()
            mock_bl_repo.get_approved_baseline = AsyncMock(return_value=None)
            mock_bl_repo_cls.return_value = mock_bl_repo

            result = await get_approved_baseline(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_get_approved_baseline_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        from src.core.exceptions import NotFoundError

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()

        with patch("src.api.v1.endpoints.baselines.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_approved_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    program_id=program_id,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"
