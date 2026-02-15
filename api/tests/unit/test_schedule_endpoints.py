"""Unit tests for schedule and CPM calculation endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.schedule import (
    calculate_schedule,
    get_critical_path,
    get_project_duration,
)
from src.core.exceptions import AuthorizationError, NotFoundError
from src.services.cpm import ScheduleResult as CPMScheduleResult


def _make_mock_user(*, is_admin: bool = False, user_id=None):
    """Create a mock user with given properties."""
    mock_user = MagicMock()
    mock_user.id = user_id or uuid4()
    mock_user.is_admin = is_admin
    return mock_user


def _make_mock_program(owner_id):
    """Create a mock program owned by the given user ID."""
    mock_program = MagicMock()
    mock_program.id = uuid4()
    mock_program.owner_id = owner_id
    return mock_program


def _make_mock_activity(activity_id=None, duration=5):
    """Create a mock activity with sensible defaults."""
    mock_activity = MagicMock()
    mock_activity.id = activity_id or uuid4()
    mock_activity.duration = duration
    mock_activity.total_float = None
    mock_activity.free_float = None
    mock_activity.is_critical = None
    return mock_activity


def _make_mock_dependency(predecessor_id, successor_id, dep_type="FS", lag=0):
    """Create a mock dependency."""
    mock_dep = MagicMock()
    mock_dep.predecessor_id = predecessor_id
    mock_dep.successor_id = successor_id
    mock_dep.dependency_type = dep_type
    mock_dep.lag = lag
    return mock_dep


def _make_cpm_result(
    activity_id,
    *,
    early_start=0,
    early_finish=5,
    late_start=0,
    late_finish=5,
    total_float=0,
    free_float=0,
):
    """Create a CPM ScheduleResult dataclass instance."""
    return CPMScheduleResult(
        activity_id=activity_id,
        early_start=early_start,
        early_finish=early_finish,
        late_start=late_start,
        late_finish=late_finish,
        total_float=total_float,
        free_float=free_float,
    )


# ---------------------------------------------------------------------------
# calculate_schedule
# ---------------------------------------------------------------------------


class TestCalculateSchedule:
    """Tests for calculate_schedule endpoint."""

    @pytest.mark.asyncio
    async def test_calculate_schedule_success(self):
        """Should calculate schedule and return results for all activities."""
        mock_db = AsyncMock()
        owner_id = uuid4()
        mock_user = _make_mock_user(user_id=owner_id)
        program_id = uuid4()

        mock_program = _make_mock_program(owner_id)
        act1 = _make_mock_activity(duration=5)
        act2 = _make_mock_activity(duration=3)
        dep = _make_mock_dependency(act1.id, act2.id)

        cpm_result_1 = _make_cpm_result(
            act1.id,
            early_start=0,
            early_finish=5,
            late_start=0,
            late_finish=5,
            total_float=0,
            free_float=0,
        )
        cpm_result_2 = _make_cpm_result(
            act2.id,
            early_start=5,
            early_finish=8,
            late_start=5,
            late_finish=8,
            total_float=0,
            free_float=0,
        )

        with (
            patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.schedule.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.schedule.DependencyRepository") as MockDepRepo,
            patch("src.api.v1.endpoints.schedule.CPMEngine") as MockCPMEngine,
            patch("src.api.v1.endpoints.schedule.cache_manager") as mock_cache,
            patch("src.api.v1.endpoints.schedule.compute_activities_hash", return_value="abc123"),
        ):
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[act1, act2])
            MockDepRepo.return_value.get_by_program = AsyncMock(return_value=[dep])
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            mock_engine = MagicMock()
            mock_engine.calculate.return_value = {
                act1.id: cpm_result_1,
                act2.id: cpm_result_2,
            }
            MockCPMEngine.return_value = mock_engine

            result = await calculate_schedule(program_id, mock_db, mock_user)

            assert len(result) == 2
            activity_ids = {r.activity_id for r in result}
            assert act1.id in activity_ids
            assert act2.id in activity_ids
            mock_db.commit.assert_called_once()
            mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_schedule_returns_cached_results(self):
        """Should return cached results when available and not force_recalculate."""
        mock_db = AsyncMock()
        owner_id = uuid4()
        mock_user = _make_mock_user(user_id=owner_id)
        program_id = uuid4()
        mock_program = _make_mock_program(owner_id)
        act1 = _make_mock_activity(duration=5)
        dep = _make_mock_dependency(act1.id, uuid4())

        cached_data = [
            {
                "activity_id": str(act1.id),
                "early_start": 0,
                "early_finish": 5,
                "late_start": 0,
                "late_finish": 5,
                "total_float": 0,
                "free_float": 0,
                "is_critical": True,
            }
        ]

        with (
            patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.schedule.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.schedule.DependencyRepository") as MockDepRepo,
            patch("src.api.v1.endpoints.schedule.CPMEngine") as MockCPMEngine,
            patch("src.api.v1.endpoints.schedule.cache_manager") as mock_cache,
            patch("src.api.v1.endpoints.schedule.compute_activities_hash", return_value="abc123"),
        ):
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[act1])
            MockDepRepo.return_value.get_by_program = AsyncMock(return_value=[dep])
            mock_cache.get = AsyncMock(return_value=cached_data)

            result = await calculate_schedule(program_id, mock_db, mock_user)

            assert len(result) == 1
            assert result[0].activity_id == act1.id
            assert result[0].is_critical is True
            MockCPMEngine.assert_not_called()
            mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_calculate_schedule_force_recalculate_ignores_cache(self):
        """Should recalculate when force_recalculate=True even if cache exists."""
        mock_db = AsyncMock()
        owner_id = uuid4()
        mock_user = _make_mock_user(user_id=owner_id)
        program_id = uuid4()
        mock_program = _make_mock_program(owner_id)
        act1 = _make_mock_activity(duration=10)

        cpm_result = _make_cpm_result(
            act1.id,
            early_start=0,
            early_finish=10,
            late_start=0,
            late_finish=10,
            total_float=0,
            free_float=0,
        )

        with (
            patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.schedule.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.schedule.DependencyRepository") as MockDepRepo,
            patch("src.api.v1.endpoints.schedule.CPMEngine") as MockCPMEngine,
            patch("src.api.v1.endpoints.schedule.cache_manager") as mock_cache,
            patch("src.api.v1.endpoints.schedule.compute_activities_hash", return_value="abc123"),
        ):
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[act1])
            MockDepRepo.return_value.get_by_program = AsyncMock(return_value=[])
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            mock_engine = MagicMock()
            mock_engine.calculate.return_value = {act1.id: cpm_result}
            MockCPMEngine.return_value = mock_engine

            result = await calculate_schedule(
                program_id,
                mock_db,
                mock_user,
                force_recalculate=True,
            )

            assert len(result) == 1
            # cache.get should NOT be called when force_recalculate=True
            mock_cache.get.assert_not_called()
            MockCPMEngine.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_schedule_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program_id = uuid4()

        with patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await calculate_schedule(program_id, mock_db, mock_user)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_calculate_schedule_not_authorized(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)
        program_id = uuid4()

        other_owner_id = uuid4()
        mock_program = _make_mock_program(other_owner_id)

        with patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)

            with pytest.raises(AuthorizationError) as exc_info:
                await calculate_schedule(program_id, mock_db, mock_user)

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_calculate_schedule_admin_bypasses_ownership(self):
        """Should allow admin user to calculate schedule for any program."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=True)
        program_id = uuid4()

        other_owner_id = uuid4()
        mock_program = _make_mock_program(other_owner_id)
        act1 = _make_mock_activity(duration=4)

        cpm_result = _make_cpm_result(
            act1.id,
            early_start=0,
            early_finish=4,
            late_start=0,
            late_finish=4,
            total_float=0,
            free_float=0,
        )

        with (
            patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.schedule.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.schedule.DependencyRepository") as MockDepRepo,
            patch("src.api.v1.endpoints.schedule.CPMEngine") as MockCPMEngine,
            patch("src.api.v1.endpoints.schedule.cache_manager") as mock_cache,
            patch("src.api.v1.endpoints.schedule.compute_activities_hash", return_value="def456"),
        ):
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[act1])
            MockDepRepo.return_value.get_by_program = AsyncMock(return_value=[])
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            mock_engine = MagicMock()
            mock_engine.calculate.return_value = {act1.id: cpm_result}
            MockCPMEngine.return_value = mock_engine

            result = await calculate_schedule(program_id, mock_db, mock_user)

            assert len(result) == 1
            assert result[0].activity_id == act1.id

    @pytest.mark.asyncio
    async def test_calculate_schedule_no_activities_returns_empty(self):
        """Should return empty list when program has no activities."""
        mock_db = AsyncMock()
        owner_id = uuid4()
        mock_user = _make_mock_user(user_id=owner_id)
        program_id = uuid4()
        mock_program = _make_mock_program(owner_id)

        with (
            patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.schedule.ActivityRepository") as MockActivityRepo,
        ):
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[])

            result = await calculate_schedule(program_id, mock_db, mock_user)

            assert result == []
            mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_calculate_schedule_updates_activity_float_values(self):
        """Should update activity models with calculated float values."""
        mock_db = AsyncMock()
        owner_id = uuid4()
        mock_user = _make_mock_user(user_id=owner_id)
        program_id = uuid4()
        mock_program = _make_mock_program(owner_id)

        act1 = _make_mock_activity(duration=5)
        act2 = _make_mock_activity(duration=3)

        cpm_result_1 = _make_cpm_result(act1.id, total_float=0, free_float=0)
        cpm_result_2 = _make_cpm_result(
            act2.id,
            early_start=0,
            early_finish=3,
            late_start=2,
            late_finish=5,
            total_float=2,
            free_float=1,
        )

        with (
            patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.schedule.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.schedule.DependencyRepository") as MockDepRepo,
            patch("src.api.v1.endpoints.schedule.CPMEngine") as MockCPMEngine,
            patch("src.api.v1.endpoints.schedule.cache_manager") as mock_cache,
            patch("src.api.v1.endpoints.schedule.compute_activities_hash", return_value="hash1"),
        ):
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[act1, act2])
            MockDepRepo.return_value.get_by_program = AsyncMock(return_value=[])
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            mock_engine = MagicMock()
            mock_engine.calculate.return_value = {
                act1.id: cpm_result_1,
                act2.id: cpm_result_2,
            }
            MockCPMEngine.return_value = mock_engine

            await calculate_schedule(program_id, mock_db, mock_user)

            # Verify activity objects were updated with CPM results
            assert act1.total_float == 0
            assert act1.free_float == 0
            assert act1.is_critical is True
            assert act2.total_float == 2
            assert act2.free_float == 1
            assert act2.is_critical is False


# ---------------------------------------------------------------------------
# get_critical_path
# ---------------------------------------------------------------------------


class TestGetCriticalPath:
    """Tests for get_critical_path endpoint."""

    @pytest.mark.asyncio
    async def test_get_critical_path_success(self):
        """Should return critical path activities and project duration."""
        mock_db = AsyncMock()
        owner_id = uuid4()
        mock_user = _make_mock_user(user_id=owner_id)
        program_id = uuid4()
        mock_program = _make_mock_program(owner_id)

        # Two critical activities, one non-critical
        crit1 = _make_mock_activity(duration=10)
        crit1.code = "A001"
        crit1.name = "Design"
        crit1.is_milestone = False
        crit1.is_critical = True

        crit2 = _make_mock_activity(duration=15)
        crit2.code = "A002"
        crit2.name = "Build"
        crit2.is_milestone = False
        crit2.is_critical = True

        non_crit = _make_mock_activity(duration=5)
        non_crit.code = "A003"
        non_crit.name = "Documentation"
        non_crit.is_milestone = False
        non_crit.is_critical = False

        all_activities = [crit1, crit2, non_crit]
        critical_activities = [crit1, crit2]

        with (
            patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.schedule.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.schedule.ActivityBriefResponse") as MockBriefResp,
        ):
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=all_activities)
            MockActivityRepo.return_value.get_critical_path = AsyncMock(
                return_value=critical_activities,
            )

            # model_validate returns objects with the right fields
            brief1 = MagicMock()
            brief1.id = crit1.id
            brief1.code = "A001"
            brief1.name = "Design"
            brief2 = MagicMock()
            brief2.id = crit2.id
            brief2.code = "A002"
            brief2.name = "Build"
            MockBriefResp.model_validate.side_effect = [brief1, brief2]

            result = await get_critical_path(program_id, mock_db, mock_user)

            assert result.project_duration == 25  # 10 + 15
            assert result.total_activities == 3
            assert result.critical_count == 2
            assert len(result.critical_activities) == 2

    @pytest.mark.asyncio
    async def test_get_critical_path_no_critical_activities(self):
        """Should return zero duration when no critical activities exist."""
        mock_db = AsyncMock()
        owner_id = uuid4()
        mock_user = _make_mock_user(user_id=owner_id)
        program_id = uuid4()
        mock_program = _make_mock_program(owner_id)

        act1 = _make_mock_activity(duration=5)

        with (
            patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.schedule.ActivityRepository") as MockActivityRepo,
        ):
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[act1])
            MockActivityRepo.return_value.get_critical_path = AsyncMock(return_value=[])

            result = await get_critical_path(program_id, mock_db, mock_user)

            assert result.project_duration == 0
            assert result.total_activities == 1
            assert result.critical_count == 0
            assert result.critical_activities == []

    @pytest.mark.asyncio
    async def test_get_critical_path_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program_id = uuid4()

        with patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await get_critical_path(program_id, mock_db, mock_user)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_critical_path_not_authorized(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)
        program_id = uuid4()

        other_owner_id = uuid4()
        mock_program = _make_mock_program(other_owner_id)

        with patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)

            with pytest.raises(AuthorizationError) as exc_info:
                await get_critical_path(program_id, mock_db, mock_user)

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_get_critical_path_admin_bypasses_ownership(self):
        """Should allow admin to view critical path for any program."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=True)
        program_id = uuid4()

        other_owner_id = uuid4()
        mock_program = _make_mock_program(other_owner_id)

        with (
            patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.schedule.ActivityRepository") as MockActivityRepo,
        ):
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[])
            MockActivityRepo.return_value.get_critical_path = AsyncMock(return_value=[])

            result = await get_critical_path(program_id, mock_db, mock_user)

            assert result.project_duration == 0
            assert result.total_activities == 0
            assert result.critical_count == 0


# ---------------------------------------------------------------------------
# get_project_duration
# ---------------------------------------------------------------------------


class TestGetProjectDuration:
    """Tests for get_project_duration endpoint."""

    @pytest.mark.asyncio
    async def test_get_project_duration_success(self):
        """Should return project duration from CPM calculation."""
        mock_db = AsyncMock()
        owner_id = uuid4()
        mock_user = _make_mock_user(user_id=owner_id)
        program_id = uuid4()
        mock_program = _make_mock_program(owner_id)

        act1 = _make_mock_activity(duration=10)
        act2 = _make_mock_activity(duration=5)

        with (
            patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.schedule.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.schedule.DependencyRepository") as MockDepRepo,
            patch("src.api.v1.endpoints.schedule.CPMEngine") as MockCPMEngine,
        ):
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[act1, act2])
            MockDepRepo.return_value.get_by_program = AsyncMock(return_value=[])

            mock_engine = MagicMock()
            mock_engine.calculate.return_value = {}
            mock_engine.get_project_duration.return_value = 15
            MockCPMEngine.return_value = mock_engine

            result = await get_project_duration(program_id, mock_db, mock_user)

            assert result == {"duration": 15}
            mock_engine.calculate.assert_called_once()
            mock_engine.get_project_duration.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_project_duration_no_activities(self):
        """Should return zero duration when program has no activities."""
        mock_db = AsyncMock()
        owner_id = uuid4()
        mock_user = _make_mock_user(user_id=owner_id)
        program_id = uuid4()
        mock_program = _make_mock_program(owner_id)

        with (
            patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.schedule.ActivityRepository") as MockActivityRepo,
        ):
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[])

            result = await get_project_duration(program_id, mock_db, mock_user)

            assert result == {"duration": 0}

    @pytest.mark.asyncio
    async def test_get_project_duration_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program_id = uuid4()

        with patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await get_project_duration(program_id, mock_db, mock_user)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_project_duration_not_authorized(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)
        program_id = uuid4()

        other_owner_id = uuid4()
        mock_program = _make_mock_program(other_owner_id)

        with patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)

            with pytest.raises(AuthorizationError) as exc_info:
                await get_project_duration(program_id, mock_db, mock_user)

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_get_project_duration_admin_bypasses_ownership(self):
        """Should allow admin to get duration for any program."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=True)
        program_id = uuid4()

        other_owner_id = uuid4()
        mock_program = _make_mock_program(other_owner_id)
        act1 = _make_mock_activity(duration=20)

        with (
            patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.schedule.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.schedule.DependencyRepository") as MockDepRepo,
            patch("src.api.v1.endpoints.schedule.CPMEngine") as MockCPMEngine,
        ):
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[act1])
            MockDepRepo.return_value.get_by_program = AsyncMock(return_value=[])

            mock_engine = MagicMock()
            mock_engine.calculate.return_value = {}
            mock_engine.get_project_duration.return_value = 20
            MockCPMEngine.return_value = mock_engine

            result = await get_project_duration(program_id, mock_db, mock_user)

            assert result == {"duration": 20}

    @pytest.mark.asyncio
    async def test_get_project_duration_with_dependencies(self):
        """Should pass dependencies to CPMEngine for duration calculation."""
        mock_db = AsyncMock()
        owner_id = uuid4()
        mock_user = _make_mock_user(user_id=owner_id)
        program_id = uuid4()
        mock_program = _make_mock_program(owner_id)

        act1 = _make_mock_activity(duration=5)
        act2 = _make_mock_activity(duration=3)
        dep = _make_mock_dependency(act1.id, act2.id, dep_type="FS", lag=2)

        with (
            patch("src.api.v1.endpoints.schedule.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.schedule.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.schedule.DependencyRepository") as MockDepRepo,
            patch("src.api.v1.endpoints.schedule.CPMEngine") as MockCPMEngine,
        ):
            MockProgramRepo.return_value.get_by_id = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[act1, act2])
            MockDepRepo.return_value.get_by_program = AsyncMock(return_value=[dep])

            mock_engine = MagicMock()
            mock_engine.calculate.return_value = {}
            mock_engine.get_project_duration.return_value = 10
            MockCPMEngine.return_value = mock_engine

            result = await get_project_duration(program_id, mock_db, mock_user)

            assert result == {"duration": 10}
            # Verify CPMEngine was created with both activities and dependencies
            MockCPMEngine.assert_called_once_with([act1, act2], [dep])
