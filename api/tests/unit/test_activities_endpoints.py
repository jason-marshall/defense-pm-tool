"""Unit tests for activity CRUD endpoints."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.activities import (
    create_activity,
    delete_activity,
    generate_activity_code,
    get_activity,
    list_activities,
    update_activity,
)
from src.core.exceptions import AuthorizationError, NotFoundError
from src.models.enums import ConstraintType, EVMethod

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, is_admin: bool = False, user_id=None):
    """Create a mock user."""
    user = MagicMock()
    user.id = user_id or uuid4()
    user.is_admin = is_admin
    return user


def _make_program(owner_id):
    """Create a mock program owned by the given user id."""
    program = MagicMock()
    program.id = uuid4()
    program.owner_id = owner_id
    return program


def _make_activity(program_id, *, code="A-001", name="Design Review"):
    """Create a mock activity object with all fields needed by ActivityResponse."""
    now = datetime.now(UTC)
    activity = MagicMock()
    activity.id = uuid4()
    activity.program_id = program_id
    activity.wbs_id = uuid4()
    activity.code = code
    activity.name = name
    activity.description = None
    activity.duration = 5
    activity.is_milestone = False
    activity.constraint_type = ConstraintType.ASAP
    activity.constraint_date = None
    activity.planned_start = None
    activity.planned_finish = None
    activity.actual_start = None
    activity.actual_finish = None
    activity.early_start = None
    activity.early_finish = None
    activity.late_start = None
    activity.late_finish = None
    activity.total_float = None
    activity.free_float = None
    activity.is_critical = False
    activity.percent_complete = Decimal("0.00")
    activity.budgeted_cost = Decimal("25000.00")
    activity.actual_cost = Decimal("0.00")
    activity.ev_method = EVMethod.PERCENT_COMPLETE.value
    activity.milestones_json = None
    activity.wbs_element = None
    activity.created_at = now
    activity.updated_at = now
    return activity


def _make_wbs_element(program_id):
    """Create a mock WBS element belonging to the given program."""
    wbs = MagicMock()
    wbs.id = uuid4()
    wbs.program_id = program_id
    return wbs


# ---------------------------------------------------------------------------
# generate_activity_code (pure function, no mocks needed)
# ---------------------------------------------------------------------------


class TestGenerateActivityCode:
    """Tests for the generate_activity_code helper function."""

    def test_empty_codes_returns_first(self):
        """Should return A-001 when no existing codes."""
        assert generate_activity_code([]) == "A-001"

    def test_increments_from_existing(self):
        """Should increment from the highest existing number."""
        assert generate_activity_code(["A-001", "A-002", "A-003"]) == "A-004"

    def test_custom_prefix(self):
        """Should use provided prefix."""
        assert generate_activity_code([], prefix="TSK") == "TSK-001"

    def test_ignores_non_numeric_codes(self):
        """Should skip codes that don't end with a number."""
        assert generate_activity_code(["A-001", "SPECIAL", "A-003"]) == "A-004"

    def test_all_non_numeric_fallback(self):
        """Should return prefix-001 when all codes are non-numeric."""
        assert generate_activity_code(["FOO", "BAR"]) == "A-001"


# ---------------------------------------------------------------------------
# list_activities
# ---------------------------------------------------------------------------


class TestListActivities:
    """Tests for list_activities endpoint."""

    @pytest.mark.asyncio
    async def test_list_activities_success(self):
        """Should return paginated activities for owned program."""
        mock_db = AsyncMock()
        user = _make_user()
        program = _make_program(user.id)
        activity1 = _make_activity(program.id, code="A-001", name="Task 1")
        activity2 = _make_activity(program.id, code="A-002", name="Task 2")

        with (
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ActivityResponse") as MockResponse,
            patch("src.api.v1.endpoints.activities.ActivityListResponse") as MockListResponse,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=[activity1, activity2])
            mock_act_repo.count = AsyncMock(return_value=2)
            MockActivityRepo.return_value = mock_act_repo

            resp1 = MagicMock()
            resp2 = MagicMock()
            MockResponse.model_validate.side_effect = [resp1, resp2]

            mock_result = MagicMock()
            mock_result.total = 2
            mock_result.items = [resp1, resp2]
            MockListResponse.return_value = mock_result

            result = await list_activities(
                db=mock_db,
                current_user=user,
                program_id=program.id,
                page=1,
                page_size=50,
            )

            assert result.total == 2
            assert len(result.items) == 2
            mock_act_repo.get_by_program.assert_called_once_with(program.id, skip=0, limit=50)

    @pytest.mark.asyncio
    async def test_list_activities_pagination(self):
        """Should apply correct skip offset for page 2."""
        mock_db = AsyncMock()
        user = _make_user()
        program = _make_program(user.id)

        with (
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ActivityListResponse") as MockListResponse,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=[])
            mock_act_repo.count = AsyncMock(return_value=60)
            MockActivityRepo.return_value = mock_act_repo

            mock_result = MagicMock()
            mock_result.total = 60
            mock_result.page = 2
            mock_result.page_size = 25
            mock_result.items = []
            MockListResponse.return_value = mock_result

            result = await list_activities(
                db=mock_db,
                current_user=user,
                program_id=program.id,
                page=2,
                page_size=25,
            )

            mock_act_repo.get_by_program.assert_called_once_with(program.id, skip=25, limit=25)
            assert result.total == 60
            assert result.page == 2
            assert result.page_size == 25

    @pytest.mark.asyncio
    async def test_list_activities_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        user = _make_user()

        with patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            MockProgramRepo.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await list_activities(
                    db=mock_db,
                    current_user=user,
                    program_id=uuid4(),
                    page=1,
                    page_size=50,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_activities_not_authorized(self):
        """Should raise AuthorizationError when user is not owner and not admin."""
        mock_db = AsyncMock()
        user = _make_user(is_admin=False)
        other_owner = uuid4()
        program = _make_program(other_owner)

        with patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await list_activities(
                    db=mock_db,
                    current_user=user,
                    program_id=program.id,
                    page=1,
                    page_size=50,
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_list_activities_admin_can_view_any_program(self):
        """Admin should be able to list activities from any program."""
        mock_db = AsyncMock()
        admin = _make_user(is_admin=True)
        other_owner = uuid4()
        program = _make_program(other_owner)

        with (
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ActivityListResponse") as MockListResponse,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=[])
            mock_act_repo.count = AsyncMock(return_value=0)
            MockActivityRepo.return_value = mock_act_repo

            mock_result = MagicMock()
            mock_result.total = 0
            mock_result.items = []
            MockListResponse.return_value = mock_result

            result = await list_activities(
                db=mock_db,
                current_user=admin,
                program_id=program.id,
                page=1,
                page_size=50,
            )

            assert result.total == 0

    @pytest.mark.asyncio
    async def test_list_activities_empty(self):
        """Should return empty list when program has no activities."""
        mock_db = AsyncMock()
        user = _make_user()
        program = _make_program(user.id)

        with (
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ActivityListResponse") as MockListResponse,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=[])
            mock_act_repo.count = AsyncMock(return_value=0)
            MockActivityRepo.return_value = mock_act_repo

            mock_result = MagicMock()
            mock_result.total = 0
            mock_result.items = []
            MockListResponse.return_value = mock_result

            result = await list_activities(
                db=mock_db,
                current_user=user,
                program_id=program.id,
                page=1,
                page_size=50,
            )

            assert result.total == 0
            assert len(result.items) == 0


# ---------------------------------------------------------------------------
# get_activity
# ---------------------------------------------------------------------------


class TestGetActivity:
    """Tests for get_activity endpoint."""

    @pytest.mark.asyncio
    async def test_get_activity_success(self):
        """Should return activity when user owns the program."""
        mock_db = AsyncMock()
        user = _make_user()
        program = _make_program(user.id)
        activity = _make_activity(program.id)

        with (
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.ActivityResponse") as MockResponse,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_resp = MagicMock()
            mock_resp.id = activity.id
            mock_resp.name = activity.name
            MockResponse.model_validate.return_value = mock_resp

            result = await get_activity(
                activity_id=activity.id,
                db=mock_db,
                current_user=user,
            )

            assert result.id == activity.id
            assert result.name == activity.name
            MockResponse.model_validate.assert_called_once_with(activity)

    @pytest.mark.asyncio
    async def test_get_activity_not_found(self):
        """Should raise NotFoundError when activity does not exist."""
        mock_db = AsyncMock()
        user = _make_user()

        with patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo:
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=None)
            MockActivityRepo.return_value = mock_act_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_activity(
                    activity_id=uuid4(),
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "ACTIVITY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_activity_program_not_found(self):
        """Should raise NotFoundError when activity's program does not exist."""
        mock_db = AsyncMock()
        user = _make_user()
        activity = _make_activity(uuid4())

        with (
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            MockProgramRepo.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_activity(
                    activity_id=activity.id,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_activity_not_authorized(self):
        """Should raise AuthorizationError when user does not own program."""
        mock_db = AsyncMock()
        user = _make_user(is_admin=False)
        other_owner = uuid4()
        program = _make_program(other_owner)
        activity = _make_activity(program.id)

        with (
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await get_activity(
                    activity_id=activity.id,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_get_activity_admin_can_view_any(self):
        """Admin should be able to view activity from any program."""
        mock_db = AsyncMock()
        admin = _make_user(is_admin=True)
        other_owner = uuid4()
        program = _make_program(other_owner)
        activity = _make_activity(program.id)

        with (
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.ActivityResponse") as MockResponse,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_resp = MagicMock()
            mock_resp.id = activity.id
            MockResponse.model_validate.return_value = mock_resp

            result = await get_activity(
                activity_id=activity.id,
                db=mock_db,
                current_user=admin,
            )

            assert result.id == activity.id


# ---------------------------------------------------------------------------
# create_activity
# ---------------------------------------------------------------------------


class TestCreateActivity:
    """Tests for create_activity endpoint."""

    @pytest.mark.asyncio
    async def test_create_activity_success_with_code(self):
        """Should create activity with user-supplied code."""
        mock_db = AsyncMock()
        user = _make_user()
        program = _make_program(user.id)
        wbs = _make_wbs_element(program.id)
        created_activity = _make_activity(program.id, code="TSK-001")

        activity_in = MagicMock()
        activity_in.program_id = program.id
        activity_in.wbs_id = wbs.id
        activity_in.model_dump.return_value = {
            "program_id": program.id,
            "wbs_id": wbs.id,
            "code": "TSK-001",
            "name": "Design Review",
            "duration": 5,
        }

        with (
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.WBSElementRepository") as MockWBSRepo,
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ActivityResponse") as MockResponse,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get_by_id = AsyncMock(return_value=wbs)
            MockWBSRepo.return_value = mock_wbs_repo

            mock_act_repo = MagicMock()
            mock_act_repo.create = AsyncMock(return_value=created_activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_resp = MagicMock()
            mock_resp.id = created_activity.id
            mock_resp.code = "TSK-001"
            MockResponse.model_validate.return_value = mock_resp

            result = await create_activity(
                activity_in=activity_in,
                db=mock_db,
                current_user=user,
            )

            assert result.code == "TSK-001"
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(created_activity)

    @pytest.mark.asyncio
    async def test_create_activity_auto_generates_code(self):
        """Should auto-generate code when not provided."""
        mock_db = AsyncMock()
        user = _make_user()
        program = _make_program(user.id)
        wbs = _make_wbs_element(program.id)

        existing1 = MagicMock()
        existing1.code = "A-001"
        existing2 = MagicMock()
        existing2.code = "A-002"

        created_activity = _make_activity(program.id, code="A-003")

        activity_in = MagicMock()
        activity_in.program_id = program.id
        activity_in.wbs_id = wbs.id
        activity_in.model_dump.return_value = {
            "program_id": program.id,
            "wbs_id": wbs.id,
            "code": None,
            "name": "Auto-Code Task",
            "duration": 3,
        }

        with (
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.WBSElementRepository") as MockWBSRepo,
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ActivityResponse") as MockResponse,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get_by_id = AsyncMock(return_value=wbs)
            MockWBSRepo.return_value = mock_wbs_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=[existing1, existing2])
            mock_act_repo.create = AsyncMock(return_value=created_activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_resp = MagicMock()
            MockResponse.model_validate.return_value = mock_resp

            await create_activity(
                activity_in=activity_in,
                db=mock_db,
                current_user=user,
            )

            # The create call should receive code="A-003"
            create_call_data = mock_act_repo.create.call_args[0][0]
            assert create_call_data["code"] == "A-003"

    @pytest.mark.asyncio
    async def test_create_activity_auto_generates_code_empty_string(self):
        """Should auto-generate code when code is empty string (falsy)."""
        mock_db = AsyncMock()
        user = _make_user()
        program = _make_program(user.id)
        wbs = _make_wbs_element(program.id)
        created_activity = _make_activity(program.id, code="A-001")

        activity_in = MagicMock()
        activity_in.program_id = program.id
        activity_in.wbs_id = wbs.id
        activity_in.model_dump.return_value = {
            "program_id": program.id,
            "wbs_id": wbs.id,
            "code": "",
            "name": "First Task",
            "duration": 1,
        }

        with (
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.WBSElementRepository") as MockWBSRepo,
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ActivityResponse") as MockResponse,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get_by_id = AsyncMock(return_value=wbs)
            MockWBSRepo.return_value = mock_wbs_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=[])
            mock_act_repo.create = AsyncMock(return_value=created_activity)
            MockActivityRepo.return_value = mock_act_repo

            MockResponse.model_validate.return_value = MagicMock()

            await create_activity(
                activity_in=activity_in,
                db=mock_db,
                current_user=user,
            )

            create_call_data = mock_act_repo.create.call_args[0][0]
            assert create_call_data["code"] == "A-001"

    @pytest.mark.asyncio
    async def test_create_activity_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        user = _make_user()

        activity_in = MagicMock()
        activity_in.program_id = uuid4()

        with patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            MockProgramRepo.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_activity(
                    activity_in=activity_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_activity_not_authorized(self):
        """Should raise AuthorizationError when user does not own program."""
        mock_db = AsyncMock()
        user = _make_user(is_admin=False)
        other_owner = uuid4()
        program = _make_program(other_owner)

        activity_in = MagicMock()
        activity_in.program_id = program.id

        with patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await create_activity(
                    activity_in=activity_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_create_activity_wbs_not_found(self):
        """Should raise NotFoundError when WBS element does not exist."""
        mock_db = AsyncMock()
        user = _make_user()
        program = _make_program(user.id)

        activity_in = MagicMock()
        activity_in.program_id = program.id
        activity_in.wbs_id = uuid4()

        with (
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.WBSElementRepository") as MockWBSRepo,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get_by_id = AsyncMock(return_value=None)
            MockWBSRepo.return_value = mock_wbs_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_activity(
                    activity_in=activity_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "WBS_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_activity_wbs_program_mismatch(self):
        """Should raise AuthorizationError when WBS belongs to a different program."""
        mock_db = AsyncMock()
        user = _make_user()
        program = _make_program(user.id)
        different_program_id = uuid4()
        wbs = _make_wbs_element(different_program_id)

        activity_in = MagicMock()
        activity_in.program_id = program.id
        activity_in.wbs_id = wbs.id

        with (
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.WBSElementRepository") as MockWBSRepo,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get_by_id = AsyncMock(return_value=wbs)
            MockWBSRepo.return_value = mock_wbs_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await create_activity(
                    activity_in=activity_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "WBS_PROGRAM_MISMATCH"

    @pytest.mark.asyncio
    async def test_create_activity_admin_can_create_in_any_program(self):
        """Admin should be able to create activity in any program."""
        mock_db = AsyncMock()
        admin = _make_user(is_admin=True)
        other_owner = uuid4()
        program = _make_program(other_owner)
        wbs = _make_wbs_element(program.id)
        created_activity = _make_activity(program.id)

        activity_in = MagicMock()
        activity_in.program_id = program.id
        activity_in.wbs_id = wbs.id
        activity_in.model_dump.return_value = {
            "program_id": program.id,
            "wbs_id": wbs.id,
            "code": "ADM-001",
            "name": "Admin Task",
            "duration": 2,
        }

        with (
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.WBSElementRepository") as MockWBSRepo,
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ActivityResponse") as MockResponse,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get_by_id = AsyncMock(return_value=wbs)
            MockWBSRepo.return_value = mock_wbs_repo

            mock_act_repo = MagicMock()
            mock_act_repo.create = AsyncMock(return_value=created_activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_resp = MagicMock()
            MockResponse.model_validate.return_value = mock_resp

            result = await create_activity(
                activity_in=activity_in,
                db=mock_db,
                current_user=admin,
            )

            assert result is mock_resp
            mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# update_activity
# ---------------------------------------------------------------------------


class TestUpdateActivity:
    """Tests for update_activity endpoint."""

    @pytest.mark.asyncio
    async def test_update_activity_success(self):
        """Should update activity fields and return updated response."""
        mock_db = AsyncMock()
        user = _make_user()
        program = _make_program(user.id)
        activity = _make_activity(program.id)
        updated_activity = _make_activity(program.id, name="Updated Name")

        activity_in = MagicMock()
        activity_in.model_dump.return_value = {"name": "Updated Name"}

        with (
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.ActivityResponse") as MockResponse,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            mock_act_repo.update = AsyncMock(return_value=updated_activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_resp = MagicMock()
            mock_resp.name = "Updated Name"
            MockResponse.model_validate.return_value = mock_resp

            result = await update_activity(
                activity_id=activity.id,
                activity_in=activity_in,
                db=mock_db,
                current_user=user,
            )

            assert result.name == "Updated Name"
            mock_act_repo.update.assert_called_once_with(activity, {"name": "Updated Name"})
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(updated_activity)

    @pytest.mark.asyncio
    async def test_update_activity_not_found(self):
        """Should raise NotFoundError when activity does not exist."""
        mock_db = AsyncMock()
        user = _make_user()
        activity_in = MagicMock()

        with patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo:
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=None)
            MockActivityRepo.return_value = mock_act_repo

            with pytest.raises(NotFoundError) as exc_info:
                await update_activity(
                    activity_id=uuid4(),
                    activity_in=activity_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "ACTIVITY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_activity_program_not_found(self):
        """Should raise NotFoundError when activity's program is missing."""
        mock_db = AsyncMock()
        user = _make_user()
        activity = _make_activity(uuid4())
        activity_in = MagicMock()

        with (
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            MockProgramRepo.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await update_activity(
                    activity_id=activity.id,
                    activity_in=activity_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_activity_not_authorized(self):
        """Should raise AuthorizationError when user does not own program."""
        mock_db = AsyncMock()
        user = _make_user(is_admin=False)
        other_owner = uuid4()
        program = _make_program(other_owner)
        activity = _make_activity(program.id)
        activity_in = MagicMock()

        with (
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await update_activity(
                    activity_id=activity.id,
                    activity_in=activity_in,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_update_activity_admin_can_update_any(self):
        """Admin should be able to update activity in any program."""
        mock_db = AsyncMock()
        admin = _make_user(is_admin=True)
        other_owner = uuid4()
        program = _make_program(other_owner)
        activity = _make_activity(program.id)
        updated_activity = _make_activity(program.id, name="Admin Update")

        activity_in = MagicMock()
        activity_in.model_dump.return_value = {"name": "Admin Update"}

        with (
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.ActivityResponse") as MockResponse,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            mock_act_repo.update = AsyncMock(return_value=updated_activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            mock_resp = MagicMock()
            mock_resp.name = "Admin Update"
            MockResponse.model_validate.return_value = mock_resp

            result = await update_activity(
                activity_id=activity.id,
                activity_in=activity_in,
                db=mock_db,
                current_user=admin,
            )

            assert result.name == "Admin Update"

    @pytest.mark.asyncio
    async def test_update_activity_partial_update_exclude_unset(self):
        """Should call model_dump with exclude_unset=True for partial updates."""
        mock_db = AsyncMock()
        user = _make_user()
        program = _make_program(user.id)
        activity = _make_activity(program.id)
        updated_activity = _make_activity(program.id)

        activity_in = MagicMock()
        activity_in.model_dump.return_value = {"duration": 10}

        with (
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.activities.ActivityResponse") as MockResponse,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            mock_act_repo.update = AsyncMock(return_value=updated_activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            MockResponse.model_validate.return_value = MagicMock()

            await update_activity(
                activity_id=activity.id,
                activity_in=activity_in,
                db=mock_db,
                current_user=user,
            )

            activity_in.model_dump.assert_called_once_with(exclude_unset=True)


# ---------------------------------------------------------------------------
# delete_activity
# ---------------------------------------------------------------------------


class TestDeleteActivity:
    """Tests for delete_activity endpoint."""

    @pytest.mark.asyncio
    async def test_delete_activity_success(self):
        """Should soft-delete activity and commit."""
        mock_db = AsyncMock()
        user = _make_user()
        program = _make_program(user.id)
        activity = _make_activity(program.id)

        with (
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            mock_act_repo.delete = AsyncMock(return_value=True)
            MockActivityRepo.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            result = await delete_activity(
                activity_id=activity.id,
                db=mock_db,
                current_user=user,
            )

            assert result is None
            mock_act_repo.delete.assert_called_once_with(activity.id)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_activity_not_found(self):
        """Should raise NotFoundError when activity does not exist."""
        mock_db = AsyncMock()
        user = _make_user()

        with patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo:
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=None)
            MockActivityRepo.return_value = mock_act_repo

            with pytest.raises(NotFoundError) as exc_info:
                await delete_activity(
                    activity_id=uuid4(),
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "ACTIVITY_NOT_FOUND"
            mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_activity_program_not_found(self):
        """Should raise NotFoundError when activity's program is missing."""
        mock_db = AsyncMock()
        user = _make_user()
        activity = _make_activity(uuid4())

        with (
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            MockProgramRepo.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await delete_activity(
                    activity_id=activity.id,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"
            mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_activity_not_authorized(self):
        """Should raise AuthorizationError when user does not own program."""
        mock_db = AsyncMock()
        user = _make_user(is_admin=False)
        other_owner = uuid4()
        program = _make_program(other_owner)
        activity = _make_activity(program.id)

        with (
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            MockActivityRepo.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await delete_activity(
                    activity_id=activity.id,
                    db=mock_db,
                    current_user=user,
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"
            mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_activity_admin_can_delete_any(self):
        """Admin should be able to delete activity from any program."""
        mock_db = AsyncMock()
        admin = _make_user(is_admin=True)
        other_owner = uuid4()
        program = _make_program(other_owner)
        activity = _make_activity(program.id)

        with (
            patch("src.api.v1.endpoints.activities.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.activities.ProgramRepository") as MockProgramRepo,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=activity)
            mock_act_repo.delete = AsyncMock(return_value=True)
            MockActivityRepo.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=program)
            MockProgramRepo.return_value = mock_prog_repo

            result = await delete_activity(
                activity_id=activity.id,
                db=mock_db,
                current_user=admin,
            )

            assert result is None
            mock_act_repo.delete.assert_called_once_with(activity.id)
            mock_db.commit.assert_called_once()
