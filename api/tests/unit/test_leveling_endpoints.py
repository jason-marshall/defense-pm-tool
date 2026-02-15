"""Unit tests for resource leveling API endpoints."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.v1.endpoints.leveling import (
    _convert_result_to_response,
    apply_leveling_shifts,
    level_program_resources,
    preview_leveling,
)
from src.services.resource_leveling import ActivityShift, LevelingResult


def _make_leveling_result(
    program_id=None,
    success=True,
    iterations_used=3,
    activities_shifted=2,
    shifts=None,
    remaining_overallocations=0,
    new_project_finish=None,
    original_project_finish=None,
    schedule_extension_days=5,
    warnings=None,
):
    """Helper to build a LevelingResult with sensible defaults."""
    pid = program_id or uuid4()
    orig = original_project_finish or date(2026, 6, 1)
    new = new_project_finish or date(2026, 6, 6)
    return LevelingResult(
        program_id=pid,
        success=success,
        iterations_used=iterations_used,
        activities_shifted=activities_shifted,
        shifts=shifts or [],
        remaining_overallocations=remaining_overallocations,
        new_project_finish=new,
        original_project_finish=orig,
        schedule_extension_days=schedule_extension_days,
        warnings=warnings or [],
    )


def _make_activity_shift(
    activity_id=None,
    activity_code="ACT-001",
    original_start=None,
    original_finish=None,
    new_start=None,
    new_finish=None,
    delay_days=3,
    reason="Resource ENG-01 overallocated",
):
    """Helper to build an ActivityShift with sensible defaults."""
    return ActivityShift(
        activity_id=activity_id or uuid4(),
        activity_code=activity_code,
        original_start=original_start or date(2026, 3, 1),
        original_finish=original_finish or date(2026, 3, 10),
        new_start=new_start or date(2026, 3, 4),
        new_finish=new_finish or date(2026, 3, 13),
        delay_days=delay_days,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Tests for _convert_result_to_response helper
# ---------------------------------------------------------------------------


class TestConvertResultToResponse:
    """Tests for the _convert_result_to_response helper function."""

    def test_converts_empty_result(self):
        """Should convert a result with no shifts."""
        program_id = uuid4()
        result = _make_leveling_result(
            program_id=program_id,
            shifts=[],
            activities_shifted=0,
        )

        response = _convert_result_to_response(result)

        assert response.program_id == program_id
        assert response.success is True
        assert response.shifts == []
        assert response.activities_shifted == 0

    def test_converts_result_with_shifts(self):
        """Should convert all shift dataclasses to response schemas."""
        shift1 = _make_activity_shift(activity_code="ACT-001", delay_days=2)
        shift2 = _make_activity_shift(activity_code="ACT-002", delay_days=5)
        result = _make_leveling_result(shifts=[shift1, shift2], activities_shifted=2)

        response = _convert_result_to_response(result)

        assert len(response.shifts) == 2
        assert response.shifts[0].activity_code == "ACT-001"
        assert response.shifts[0].delay_days == 2
        assert response.shifts[1].activity_code == "ACT-002"
        assert response.shifts[1].delay_days == 5

    def test_preserves_all_fields(self):
        """Should map every LevelingResult field to the response."""
        program_id = uuid4()
        result = _make_leveling_result(
            program_id=program_id,
            success=False,
            iterations_used=50,
            activities_shifted=4,
            remaining_overallocations=2,
            original_project_finish=date(2026, 5, 1),
            new_project_finish=date(2026, 5, 20),
            schedule_extension_days=19,
            warnings=["Cannot delay critical activity DR-001"],
        )

        response = _convert_result_to_response(result)

        assert response.program_id == program_id
        assert response.success is False
        assert response.iterations_used == 50
        assert response.activities_shifted == 4
        assert response.remaining_overallocations == 2
        assert response.original_project_finish == date(2026, 5, 1)
        assert response.new_project_finish == date(2026, 5, 20)
        assert response.schedule_extension_days == 19
        assert response.warnings == ["Cannot delay critical activity DR-001"]


# ---------------------------------------------------------------------------
# Tests for POST /{program_id}/level
# ---------------------------------------------------------------------------


class TestLevelProgramResources:
    """Tests for the level_program_resources endpoint."""

    @pytest.mark.asyncio
    async def test_level_success(self):
        """Should run leveling and return result response."""
        from src.schemas.leveling import LevelingOptionsRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        shift = _make_activity_shift()
        leveling_result = _make_leveling_result(
            program_id=program_id, shifts=[shift], activities_shifted=1
        )

        options = LevelingOptionsRequest(
            preserve_critical_path=True,
            max_iterations=100,
            target_resources=None,
            level_within_float=True,
        )

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.leveling.ResourceLevelingService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.level_program = AsyncMock(return_value=leveling_result)
                mock_svc_cls.return_value = mock_svc

                result = await level_program_resources(program_id, options, mock_db, mock_user)

                assert result.program_id == program_id
                assert result.success is True
                assert len(result.shifts) == 1
                mock_svc.level_program.assert_called_once()

    @pytest.mark.asyncio
    async def test_level_program_not_found(self):
        """Should raise HTTPException 404 when program does not exist."""
        from src.schemas.leveling import LevelingOptionsRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        options = LevelingOptionsRequest()

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(HTTPException) as exc_info:
                await level_program_resources(program_id, options, mock_db, mock_user)

            assert exc_info.value.status_code == 404
            assert "Program not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_level_passes_options_to_service(self):
        """Should forward all options to LevelingOptions and service."""
        from src.schemas.leveling import LevelingOptionsRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        resource_ids = [uuid4(), uuid4()]
        mock_program = MagicMock()
        mock_program.id = program_id

        options = LevelingOptionsRequest(
            preserve_critical_path=False,
            max_iterations=50,
            target_resources=resource_ids,
            level_within_float=False,
        )

        leveling_result = _make_leveling_result(program_id=program_id)

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.leveling.ResourceLevelingService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.level_program = AsyncMock(return_value=leveling_result)
                mock_svc_cls.return_value = mock_svc

                await level_program_resources(program_id, options, mock_db, mock_user)

                call_args = mock_svc.level_program.call_args
                leveling_opts = call_args[0][1]
                assert leveling_opts.preserve_critical_path is False
                assert leveling_opts.max_iterations == 50
                assert leveling_opts.target_resources == resource_ids
                assert leveling_opts.level_within_float is False

    @pytest.mark.asyncio
    async def test_level_with_warnings(self):
        """Should propagate warnings from leveling result."""
        from src.schemas.leveling import LevelingOptionsRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        leveling_result = _make_leveling_result(
            program_id=program_id,
            success=False,
            remaining_overallocations=1,
            warnings=["Cannot delay critical activity DR-001"],
        )

        options = LevelingOptionsRequest()

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.leveling.ResourceLevelingService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.level_program = AsyncMock(return_value=leveling_result)
                mock_svc_cls.return_value = mock_svc

                result = await level_program_resources(program_id, options, mock_db, mock_user)

                assert result.success is False
                assert result.remaining_overallocations == 1
                assert len(result.warnings) == 1
                assert "critical activity" in result.warnings[0]


# ---------------------------------------------------------------------------
# Tests for GET /{program_id}/level/preview
# ---------------------------------------------------------------------------


class TestPreviewLeveling:
    """Tests for the preview_leveling endpoint."""

    @pytest.mark.asyncio
    async def test_preview_success(self):
        """Should preview leveling with default options."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        leveling_result = _make_leveling_result(program_id=program_id)

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.leveling.ResourceLevelingService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.level_program = AsyncMock(return_value=leveling_result)
                mock_svc_cls.return_value = mock_svc

                result = await preview_leveling(program_id, mock_db, mock_user)

                assert result.program_id == program_id
                assert result.success is True
                mock_svc.level_program.assert_called_once()

    @pytest.mark.asyncio
    async def test_preview_program_not_found(self):
        """Should raise HTTPException 404 when program does not exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(HTTPException) as exc_info:
                await preview_leveling(program_id, mock_db, mock_user)

            assert exc_info.value.status_code == 404
            assert "Program not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_preview_custom_options(self):
        """Should forward query params as leveling options."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        resource_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        leveling_result = _make_leveling_result(program_id=program_id)

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.leveling.ResourceLevelingService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.level_program = AsyncMock(return_value=leveling_result)
                mock_svc_cls.return_value = mock_svc

                await preview_leveling(
                    program_id,
                    mock_db,
                    mock_user,
                    preserve_critical_path=False,
                    level_within_float=False,
                    max_iterations=200,
                    target_resources=[resource_id],
                )

                call_args = mock_svc.level_program.call_args
                leveling_opts = call_args[0][1]
                assert leveling_opts.preserve_critical_path is False
                assert leveling_opts.level_within_float is False
                assert leveling_opts.max_iterations == 200
                assert leveling_opts.target_resources == [resource_id]

    @pytest.mark.asyncio
    async def test_preview_returns_shifts(self):
        """Should include shift details in response."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        shift = _make_activity_shift(
            activity_code="DR-100",
            delay_days=7,
            reason="Resource ENG-05 overallocated",
        )
        leveling_result = _make_leveling_result(
            program_id=program_id,
            shifts=[shift],
            activities_shifted=1,
            schedule_extension_days=7,
        )

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.leveling.ResourceLevelingService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.level_program = AsyncMock(return_value=leveling_result)
                mock_svc_cls.return_value = mock_svc

                result = await preview_leveling(program_id, mock_db, mock_user)

                assert result.activities_shifted == 1
                assert result.schedule_extension_days == 7
                assert result.shifts[0].activity_code == "DR-100"
                assert result.shifts[0].delay_days == 7
                assert "ENG-05" in result.shifts[0].reason


# ---------------------------------------------------------------------------
# Tests for POST /{program_id}/level/apply
# ---------------------------------------------------------------------------


class TestApplyLevelingShifts:
    """Tests for the apply_leveling_shifts endpoint."""

    @pytest.mark.asyncio
    async def test_apply_success(self):
        """Should apply requested shifts and return counts."""
        from src.schemas.leveling import LevelingApplyRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        activity_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        shift = _make_activity_shift(
            activity_id=activity_id,
            new_start=date(2026, 3, 5),
            new_finish=date(2026, 3, 14),
        )
        leveling_result = _make_leveling_result(
            program_id=program_id,
            shifts=[shift],
            original_project_finish=date(2026, 6, 1),
        )

        mock_activity = MagicMock()
        mock_activity.id = activity_id
        mock_activity.planned_start = date(2026, 3, 1)
        mock_activity.planned_finish = date(2026, 3, 10)

        request = LevelingApplyRequest(shifts=[activity_id])

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.leveling.ResourceLevelingService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.level_program = AsyncMock(return_value=leveling_result)
                mock_svc_cls.return_value = mock_svc

                with patch("src.api.v1.endpoints.leveling.ActivityRepository") as mock_act_repo_cls:
                    mock_act_repo = MagicMock()
                    mock_act_repo.get_by_id = AsyncMock(return_value=mock_activity)
                    mock_act_repo_cls.return_value = mock_act_repo

                    result = await apply_leveling_shifts(program_id, request, mock_db, mock_user)

                    assert result.applied_count == 1
                    assert result.skipped_count == 0
                    assert mock_activity.planned_start == date(2026, 3, 5)
                    assert mock_activity.planned_finish == date(2026, 3, 14)
                    mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_program_not_found(self):
        """Should raise HTTPException 404 when program does not exist."""
        from src.schemas.leveling import LevelingApplyRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        request = LevelingApplyRequest(shifts=[uuid4()])

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(HTTPException) as exc_info:
                await apply_leveling_shifts(program_id, request, mock_db, mock_user)

            assert exc_info.value.status_code == 404
            assert "Program not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_apply_skips_unmatched_ids(self):
        """Should increment skipped_count for IDs not in leveling result."""
        from src.schemas.leveling import LevelingApplyRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        # Leveling produced no shifts
        leveling_result = _make_leveling_result(
            program_id=program_id,
            shifts=[],
            original_project_finish=date(2026, 6, 1),
        )

        bogus_id = uuid4()
        request = LevelingApplyRequest(shifts=[bogus_id])

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.leveling.ResourceLevelingService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.level_program = AsyncMock(return_value=leveling_result)
                mock_svc_cls.return_value = mock_svc

                with patch("src.api.v1.endpoints.leveling.ActivityRepository") as mock_act_repo_cls:
                    mock_act_repo_cls.return_value = MagicMock()

                    result = await apply_leveling_shifts(program_id, request, mock_db, mock_user)

                    assert result.applied_count == 0
                    assert result.skipped_count == 1
                    mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_multiple_shifts(self):
        """Should apply multiple shifts and accumulate counts."""
        from src.schemas.leveling import LevelingApplyRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        act_id_1 = uuid4()
        act_id_2 = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        shift1 = _make_activity_shift(
            activity_id=act_id_1,
            activity_code="ACT-001",
            new_start=date(2026, 3, 5),
            new_finish=date(2026, 3, 14),
        )
        shift2 = _make_activity_shift(
            activity_id=act_id_2,
            activity_code="ACT-002",
            new_start=date(2026, 3, 8),
            new_finish=date(2026, 3, 17),
        )
        leveling_result = _make_leveling_result(
            program_id=program_id,
            shifts=[shift1, shift2],
            original_project_finish=date(2026, 6, 1),
        )

        mock_activity_1 = MagicMock()
        mock_activity_1.id = act_id_1
        mock_activity_2 = MagicMock()
        mock_activity_2.id = act_id_2

        request = LevelingApplyRequest(shifts=[act_id_1, act_id_2])

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.leveling.ResourceLevelingService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.level_program = AsyncMock(return_value=leveling_result)
                mock_svc_cls.return_value = mock_svc

                with patch("src.api.v1.endpoints.leveling.ActivityRepository") as mock_act_repo_cls:
                    activity_map = {act_id_1: mock_activity_1, act_id_2: mock_activity_2}
                    mock_act_repo = MagicMock()
                    mock_act_repo.get_by_id = AsyncMock(
                        side_effect=lambda aid: activity_map.get(aid)
                    )
                    mock_act_repo_cls.return_value = mock_act_repo

                    result = await apply_leveling_shifts(program_id, request, mock_db, mock_user)

                    assert result.applied_count == 2
                    assert result.skipped_count == 0

    @pytest.mark.asyncio
    async def test_apply_skips_missing_activity(self):
        """Should not crash when activity repo returns None for an ID."""
        from src.schemas.leveling import LevelingApplyRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        act_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        shift = _make_activity_shift(
            activity_id=act_id,
            new_start=date(2026, 3, 5),
            new_finish=date(2026, 3, 14),
        )
        leveling_result = _make_leveling_result(
            program_id=program_id,
            shifts=[shift],
            original_project_finish=date(2026, 6, 1),
        )

        request = LevelingApplyRequest(shifts=[act_id])

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.leveling.ResourceLevelingService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.level_program = AsyncMock(return_value=leveling_result)
                mock_svc_cls.return_value = mock_svc

                with patch("src.api.v1.endpoints.leveling.ActivityRepository") as mock_act_repo_cls:
                    mock_act_repo = MagicMock()
                    # Activity not found in DB
                    mock_act_repo.get_by_id = AsyncMock(return_value=None)
                    mock_act_repo_cls.return_value = mock_act_repo

                    result = await apply_leveling_shifts(program_id, request, mock_db, mock_user)

                    # The shift was in leveling results but activity
                    # is None, so it is not applied and not counted as
                    # skipped (only IDs absent from shifts_to_apply are
                    # skipped).
                    assert result.applied_count == 0
                    assert result.skipped_count == 0
                    mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_empty_request(self):
        """Should handle empty shift list gracefully."""
        from src.schemas.leveling import LevelingApplyRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        leveling_result = _make_leveling_result(
            program_id=program_id,
            shifts=[_make_activity_shift()],
            original_project_finish=date(2026, 6, 1),
        )

        request = LevelingApplyRequest(shifts=[])

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.leveling.ResourceLevelingService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.level_program = AsyncMock(return_value=leveling_result)
                mock_svc_cls.return_value = mock_svc

                with patch("src.api.v1.endpoints.leveling.ActivityRepository") as mock_act_repo_cls:
                    mock_act_repo_cls.return_value = MagicMock()

                    result = await apply_leveling_shifts(program_id, request, mock_db, mock_user)

                    assert result.applied_count == 0
                    assert result.skipped_count == 0
                    mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_new_project_finish_tracks_latest_shift(self):
        """Should set new_project_finish to the latest applied shift finish."""
        from src.schemas.leveling import LevelingApplyRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        act_id_1 = uuid4()
        act_id_2 = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        shift1 = _make_activity_shift(
            activity_id=act_id_1,
            new_start=date(2026, 3, 5),
            new_finish=date(2026, 7, 10),
        )
        shift2 = _make_activity_shift(
            activity_id=act_id_2,
            new_start=date(2026, 3, 8),
            new_finish=date(2026, 8, 15),
        )
        leveling_result = _make_leveling_result(
            program_id=program_id,
            shifts=[shift1, shift2],
            original_project_finish=date(2026, 6, 1),
        )

        mock_act_1 = MagicMock()
        mock_act_1.id = act_id_1
        mock_act_2 = MagicMock()
        mock_act_2.id = act_id_2

        request = LevelingApplyRequest(shifts=[act_id_1, act_id_2])

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.leveling.ResourceLevelingService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.level_program = AsyncMock(return_value=leveling_result)
                mock_svc_cls.return_value = mock_svc

                with patch("src.api.v1.endpoints.leveling.ActivityRepository") as mock_act_repo_cls:
                    mock_act_repo = MagicMock()
                    mock_act_repo.get_by_id = AsyncMock(side_effect=[mock_act_1, mock_act_2])
                    mock_act_repo_cls.return_value = mock_act_repo

                    result = await apply_leveling_shifts(program_id, request, mock_db, mock_user)

                    assert result.new_project_finish == date(2026, 8, 15)

    @pytest.mark.asyncio
    async def test_apply_flushes_after_each_activity(self):
        """Should call db.flush() after updating each activity."""
        from src.schemas.leveling import LevelingApplyRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        act_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        shift = _make_activity_shift(
            activity_id=act_id,
            new_start=date(2026, 3, 5),
            new_finish=date(2026, 3, 14),
        )
        leveling_result = _make_leveling_result(
            program_id=program_id,
            shifts=[shift],
            original_project_finish=date(2026, 6, 1),
        )

        mock_activity = MagicMock()
        mock_activity.id = act_id

        request = LevelingApplyRequest(shifts=[act_id])

        with patch("src.api.v1.endpoints.leveling.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.leveling.ResourceLevelingService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.level_program = AsyncMock(return_value=leveling_result)
                mock_svc_cls.return_value = mock_svc

                with patch("src.api.v1.endpoints.leveling.ActivityRepository") as mock_act_repo_cls:
                    mock_act_repo = MagicMock()
                    mock_act_repo.get_by_id = AsyncMock(return_value=mock_activity)
                    mock_act_repo_cls.return_value = mock_act_repo

                    await apply_leveling_shifts(program_id, request, mock_db, mock_user)

                    mock_db.flush.assert_called_once()
                    mock_db.commit.assert_called_once()
