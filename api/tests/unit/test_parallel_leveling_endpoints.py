"""Unit tests for parallel resource leveling endpoints."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.v1.endpoints.parallel_leveling import (
    _convert_parallel_result_to_response,
    _determine_recommendation,
    compare_leveling_algorithms,
    preview_parallel_leveling,
    run_parallel_leveling,
)
from src.services.resource_leveling import ActivityShift, LevelingResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_activity_shift(**overrides) -> ActivityShift:
    """Create a test ActivityShift dataclass instance."""
    defaults = {
        "activity_id": uuid4(),
        "activity_code": "ACT-001",
        "original_start": date(2026, 1, 1),
        "original_finish": date(2026, 1, 10),
        "new_start": date(2026, 1, 5),
        "new_finish": date(2026, 1, 14),
        "delay_days": 4,
        "reason": "Resource overallocation",
    }
    defaults.update(overrides)
    return ActivityShift(**defaults)


def _make_parallel_result(**overrides):
    """Create a mock ParallelLevelingResult dataclass."""
    from src.services.parallel_leveling import ParallelLevelingResult

    defaults = {
        "program_id": uuid4(),
        "success": True,
        "iterations_used": 5,
        "activities_shifted": 2,
        "shifts": [_make_activity_shift()],
        "remaining_overallocations": 0,
        "new_project_finish": date(2026, 6, 15),
        "original_project_finish": date(2026, 6, 1),
        "schedule_extension_days": 14,
        "warnings": [],
        "conflicts_resolved": 3,
        "resources_processed": 2,
    }
    defaults.update(overrides)
    return ParallelLevelingResult(**defaults)


def _make_serial_result(**overrides) -> LevelingResult:
    """Create a test LevelingResult dataclass instance."""
    defaults = {
        "program_id": uuid4(),
        "success": True,
        "iterations_used": 8,
        "activities_shifted": 4,
        "shifts": [_make_activity_shift()],
        "remaining_overallocations": 0,
        "new_project_finish": date(2026, 6, 20),
        "original_project_finish": date(2026, 6, 1),
        "schedule_extension_days": 19,
        "warnings": [],
    }
    defaults.update(overrides)
    return LevelingResult(**defaults)


# ---------------------------------------------------------------------------
# TestRunParallelLeveling
# ---------------------------------------------------------------------------


class TestRunParallelLeveling:
    """Tests for the run_parallel_leveling endpoint."""

    @pytest.mark.asyncio
    async def test_run_parallel_leveling_success(self):
        """Should run parallel leveling and return result for valid program."""
        from src.schemas.leveling import LevelingOptionsRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        parallel_result = _make_parallel_result(program_id=program_id)

        options = LevelingOptionsRequest(
            preserve_critical_path=True,
            max_iterations=50,
            target_resources=None,
            level_within_float=True,
        )

        with patch("src.api.v1.endpoints.parallel_leveling.ProgramRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_repo_class.return_value = mock_repo

            with patch(
                "src.api.v1.endpoints.parallel_leveling.ParallelLevelingService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.level_program = AsyncMock(return_value=parallel_result)
                mock_service_class.return_value = mock_service

                result = await run_parallel_leveling(program_id, options, mock_db, mock_user)

                assert result.program_id == program_id
                assert result.success is True
                assert result.conflicts_resolved == 3
                assert result.resources_processed == 2
                mock_repo.get_by_id.assert_called_once_with(program_id)
                mock_service.level_program.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_parallel_leveling_program_not_found(self):
        """Should raise HTTPException 404 when program does not exist."""
        from src.schemas.leveling import LevelingOptionsRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        options = LevelingOptionsRequest()

        with patch("src.api.v1.endpoints.parallel_leveling.ProgramRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await run_parallel_leveling(program_id, options, mock_db, mock_user)

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Program not found"

    @pytest.mark.asyncio
    async def test_run_parallel_leveling_passes_options(self):
        """Should pass leveling options correctly to the service."""
        from src.schemas.leveling import LevelingOptionsRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        target_resource_ids = [uuid4(), uuid4()]
        parallel_result = _make_parallel_result(program_id=program_id)

        options = LevelingOptionsRequest(
            preserve_critical_path=False,
            max_iterations=200,
            target_resources=target_resource_ids,
            level_within_float=False,
        )

        with patch("src.api.v1.endpoints.parallel_leveling.ProgramRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_repo_class.return_value = mock_repo

            with patch(
                "src.api.v1.endpoints.parallel_leveling.ParallelLevelingService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.level_program = AsyncMock(return_value=parallel_result)
                mock_service_class.return_value = mock_service

                await run_parallel_leveling(program_id, options, mock_db, mock_user)

                call_args = mock_service.level_program.call_args
                leveling_opts = call_args[0][1]
                assert leveling_opts.preserve_critical_path is False
                assert leveling_opts.max_iterations == 200
                assert leveling_opts.target_resources == target_resource_ids
                assert leveling_opts.level_within_float is False

    @pytest.mark.asyncio
    async def test_run_parallel_leveling_with_shifts(self):
        """Should correctly convert shifts in response."""
        from src.schemas.leveling import LevelingOptionsRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        shift1_id = uuid4()
        shift2_id = uuid4()
        shifts = [
            _make_activity_shift(
                activity_id=shift1_id,
                activity_code="ACT-001",
                delay_days=3,
            ),
            _make_activity_shift(
                activity_id=shift2_id,
                activity_code="ACT-002",
                delay_days=7,
            ),
        ]
        parallel_result = _make_parallel_result(
            program_id=program_id,
            activities_shifted=2,
            shifts=shifts,
        )

        options = LevelingOptionsRequest()

        with patch("src.api.v1.endpoints.parallel_leveling.ProgramRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_repo_class.return_value = mock_repo

            with patch(
                "src.api.v1.endpoints.parallel_leveling.ParallelLevelingService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.level_program = AsyncMock(return_value=parallel_result)
                mock_service_class.return_value = mock_service

                result = await run_parallel_leveling(program_id, options, mock_db, mock_user)

                assert len(result.shifts) == 2
                assert result.shifts[0].activity_id == shift1_id
                assert result.shifts[0].activity_code == "ACT-001"
                assert result.shifts[0].delay_days == 3
                assert result.shifts[1].activity_id == shift2_id
                assert result.shifts[1].delay_days == 7


# ---------------------------------------------------------------------------
# TestPreviewParallelLeveling
# ---------------------------------------------------------------------------


class TestPreviewParallelLeveling:
    """Tests for the preview_parallel_leveling endpoint."""

    @pytest.mark.asyncio
    async def test_preview_parallel_leveling_success(self):
        """Should preview leveling with default parameters."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        parallel_result = _make_parallel_result(program_id=program_id)

        with patch("src.api.v1.endpoints.parallel_leveling.ProgramRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_repo_class.return_value = mock_repo

            with patch(
                "src.api.v1.endpoints.parallel_leveling.ParallelLevelingService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.level_program = AsyncMock(return_value=parallel_result)
                mock_service_class.return_value = mock_service

                result = await preview_parallel_leveling(program_id, mock_db, mock_user)

                assert result.program_id == program_id
                assert result.success is True
                mock_repo.get_by_id.assert_called_once_with(program_id)

    @pytest.mark.asyncio
    async def test_preview_parallel_leveling_program_not_found(self):
        """Should raise HTTPException 404 when program not found."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()

        with patch("src.api.v1.endpoints.parallel_leveling.ProgramRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await preview_parallel_leveling(program_id, mock_db, mock_user)

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Program not found"

    @pytest.mark.asyncio
    async def test_preview_parallel_leveling_with_custom_options(self):
        """Should pass custom query parameters to the service."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id
        target_ids = [uuid4()]

        parallel_result = _make_parallel_result(program_id=program_id)

        with patch("src.api.v1.endpoints.parallel_leveling.ProgramRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_repo_class.return_value = mock_repo

            with patch(
                "src.api.v1.endpoints.parallel_leveling.ParallelLevelingService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.level_program = AsyncMock(return_value=parallel_result)
                mock_service_class.return_value = mock_service

                await preview_parallel_leveling(
                    program_id,
                    mock_db,
                    mock_user,
                    preserve_critical_path=False,
                    level_within_float=False,
                    max_iterations=500,
                    target_resources=target_ids,
                )

                call_args = mock_service.level_program.call_args
                leveling_opts = call_args[0][1]
                assert leveling_opts.preserve_critical_path is False
                assert leveling_opts.level_within_float is False
                assert leveling_opts.max_iterations == 500
                assert leveling_opts.target_resources == target_ids


# ---------------------------------------------------------------------------
# TestCompareLevelingAlgorithms
# ---------------------------------------------------------------------------


class TestCompareLevelingAlgorithms:
    """Tests for the compare_leveling_algorithms endpoint."""

    @pytest.mark.asyncio
    async def test_compare_leveling_success(self):
        """Should return comparison of serial and parallel results."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        serial_result = _make_serial_result(
            program_id=program_id,
            success=True,
            iterations_used=8,
            activities_shifted=4,
            schedule_extension_days=19,
            remaining_overallocations=0,
        )
        parallel_result = _make_parallel_result(
            program_id=program_id,
            success=True,
            iterations_used=5,
            activities_shifted=2,
            schedule_extension_days=14,
            remaining_overallocations=0,
        )

        with patch("src.api.v1.endpoints.parallel_leveling.ProgramRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_repo_class.return_value = mock_repo

            with patch(
                "src.api.v1.endpoints.parallel_leveling.ResourceLevelingService"
            ) as mock_serial_class:
                mock_serial_svc = MagicMock()
                mock_serial_svc.level_program = AsyncMock(return_value=serial_result)
                mock_serial_class.return_value = mock_serial_svc

                with patch(
                    "src.api.v1.endpoints.parallel_leveling.ParallelLevelingService"
                ) as mock_parallel_class:
                    mock_parallel_svc = MagicMock()
                    mock_parallel_svc.level_program = AsyncMock(return_value=parallel_result)
                    mock_parallel_class.return_value = mock_parallel_svc

                    result = await compare_leveling_algorithms(program_id, mock_db, mock_user)

                    assert result.serial.success is True
                    assert result.serial.iterations == 8
                    assert result.serial.activities_shifted == 4
                    assert result.serial.schedule_extension_days == 19

                    assert result.parallel.success is True
                    assert result.parallel.iterations == 5
                    assert result.parallel.activities_shifted == 2
                    assert result.parallel.schedule_extension_days == 14

                    assert result.recommendation == "parallel"
                    assert result.improvement["extension_days_saved"] == 5
                    assert result.improvement["fewer_shifts"] == 2
                    assert result.improvement["fewer_iterations"] == 3

    @pytest.mark.asyncio
    async def test_compare_leveling_program_not_found(self):
        """Should raise HTTPException 404 when program not found."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()

        with patch("src.api.v1.endpoints.parallel_leveling.ProgramRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await compare_leveling_algorithms(program_id, mock_db, mock_user)

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Program not found"

    @pytest.mark.asyncio
    async def test_compare_leveling_with_custom_options(self):
        """Should pass custom options to both services."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        serial_result = _make_serial_result(program_id=program_id)
        parallel_result = _make_parallel_result(program_id=program_id)

        with patch("src.api.v1.endpoints.parallel_leveling.ProgramRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_repo_class.return_value = mock_repo

            with patch(
                "src.api.v1.endpoints.parallel_leveling.ResourceLevelingService"
            ) as mock_serial_class:
                mock_serial_svc = MagicMock()
                mock_serial_svc.level_program = AsyncMock(return_value=serial_result)
                mock_serial_class.return_value = mock_serial_svc

                with patch(
                    "src.api.v1.endpoints.parallel_leveling.ParallelLevelingService"
                ) as mock_parallel_class:
                    mock_parallel_svc = MagicMock()
                    mock_parallel_svc.level_program = AsyncMock(return_value=parallel_result)
                    mock_parallel_class.return_value = mock_parallel_svc

                    await compare_leveling_algorithms(
                        program_id,
                        mock_db,
                        mock_user,
                        preserve_critical_path=False,
                        level_within_float=False,
                        max_iterations=250,
                    )

                    serial_call = mock_serial_svc.level_program.call_args
                    serial_opts = serial_call[0][1]
                    assert serial_opts.preserve_critical_path is False
                    assert serial_opts.level_within_float is False
                    assert serial_opts.max_iterations == 250

                    parallel_call = mock_parallel_svc.level_program.call_args
                    parallel_opts = parallel_call[0][1]
                    assert parallel_opts.preserve_critical_path is False
                    assert parallel_opts.level_within_float is False
                    assert parallel_opts.max_iterations == 250

    @pytest.mark.asyncio
    async def test_compare_leveling_serial_wins(self):
        """Should recommend serial when it produces shorter schedule."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        serial_result = _make_serial_result(
            program_id=program_id,
            success=True,
            schedule_extension_days=5,
            activities_shifted=2,
        )
        parallel_result = _make_parallel_result(
            program_id=program_id,
            success=True,
            schedule_extension_days=10,
            activities_shifted=3,
        )

        with patch("src.api.v1.endpoints.parallel_leveling.ProgramRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_repo_class.return_value = mock_repo

            with patch(
                "src.api.v1.endpoints.parallel_leveling.ResourceLevelingService"
            ) as mock_serial_class:
                mock_serial_svc = MagicMock()
                mock_serial_svc.level_program = AsyncMock(return_value=serial_result)
                mock_serial_class.return_value = mock_serial_svc

                with patch(
                    "src.api.v1.endpoints.parallel_leveling.ParallelLevelingService"
                ) as mock_parallel_class:
                    mock_parallel_svc = MagicMock()
                    mock_parallel_svc.level_program = AsyncMock(return_value=parallel_result)
                    mock_parallel_class.return_value = mock_parallel_svc

                    result = await compare_leveling_algorithms(program_id, mock_db, mock_user)

                    assert result.recommendation == "serial"


# ---------------------------------------------------------------------------
# TestDetermineRecommendation
# ---------------------------------------------------------------------------


class TestDetermineRecommendation:
    """Tests for the _determine_recommendation helper function."""

    def test_both_successful_parallel_shorter(self):
        """Should recommend parallel when both succeed and parallel is shorter."""
        serial = _make_serial_result(success=True, schedule_extension_days=10, activities_shifted=3)
        parallel = _make_parallel_result(
            success=True, schedule_extension_days=5, activities_shifted=2
        )
        assert _determine_recommendation(serial, parallel) == "parallel"

    def test_both_successful_serial_shorter(self):
        """Should recommend serial when both succeed and serial is shorter."""
        serial = _make_serial_result(success=True, schedule_extension_days=5, activities_shifted=3)
        parallel = _make_parallel_result(
            success=True, schedule_extension_days=10, activities_shifted=2
        )
        assert _determine_recommendation(serial, parallel) == "serial"

    def test_both_successful_tie_fewer_shifts_parallel(self):
        """Should recommend parallel on tie when parallel has fewer shifts."""
        serial = _make_serial_result(success=True, schedule_extension_days=10, activities_shifted=5)
        parallel = _make_parallel_result(
            success=True, schedule_extension_days=10, activities_shifted=3
        )
        assert _determine_recommendation(serial, parallel) == "parallel"

    def test_both_successful_tie_fewer_shifts_serial(self):
        """Should recommend serial on tie when serial has fewer shifts."""
        serial = _make_serial_result(success=True, schedule_extension_days=10, activities_shifted=2)
        parallel = _make_parallel_result(
            success=True, schedule_extension_days=10, activities_shifted=5
        )
        assert _determine_recommendation(serial, parallel) == "serial"

    def test_only_parallel_succeeds(self):
        """Should recommend parallel when only parallel succeeds."""
        serial = _make_serial_result(success=False, remaining_overallocations=3)
        parallel = _make_parallel_result(success=True, remaining_overallocations=0)
        assert _determine_recommendation(serial, parallel) == "parallel"

    def test_only_serial_succeeds(self):
        """Should recommend serial when only serial succeeds."""
        serial = _make_serial_result(success=True, remaining_overallocations=0)
        parallel = _make_parallel_result(success=False, remaining_overallocations=2)
        assert _determine_recommendation(serial, parallel) == "serial"

    def test_both_failed_parallel_fewer_conflicts(self):
        """Should recommend parallel when both fail but parallel has fewer conflicts."""
        serial = _make_serial_result(
            success=False, remaining_overallocations=5, schedule_extension_days=10
        )
        parallel = _make_parallel_result(
            success=False, remaining_overallocations=2, schedule_extension_days=10
        )
        assert _determine_recommendation(serial, parallel) == "parallel"

    def test_both_failed_serial_fewer_conflicts(self):
        """Should recommend serial when both fail but serial has fewer conflicts."""
        serial = _make_serial_result(
            success=False, remaining_overallocations=1, schedule_extension_days=10
        )
        parallel = _make_parallel_result(
            success=False, remaining_overallocations=4, schedule_extension_days=10
        )
        assert _determine_recommendation(serial, parallel) == "serial"

    def test_both_failed_same_conflicts_parallel_shorter(self):
        """Should recommend parallel when both fail with same conflicts and parallel is shorter."""
        serial = _make_serial_result(
            success=False, remaining_overallocations=3, schedule_extension_days=15
        )
        parallel = _make_parallel_result(
            success=False, remaining_overallocations=3, schedule_extension_days=10
        )
        assert _determine_recommendation(serial, parallel) == "parallel"

    def test_both_failed_same_conflicts_serial_shorter(self):
        """Should recommend serial when both fail with same conflicts and serial is shorter."""
        serial = _make_serial_result(
            success=False, remaining_overallocations=3, schedule_extension_days=8
        )
        parallel = _make_parallel_result(
            success=False, remaining_overallocations=3, schedule_extension_days=12
        )
        assert _determine_recommendation(serial, parallel) == "serial"


# ---------------------------------------------------------------------------
# TestConvertParallelResultToResponse
# ---------------------------------------------------------------------------


class TestConvertParallelResultToResponse:
    """Tests for the _convert_parallel_result_to_response helper."""

    def test_converts_basic_result(self):
        """Should convert ParallelLevelingResult to response schema."""
        program_id = uuid4()
        result = _make_parallel_result(
            program_id=program_id,
            success=True,
            iterations_used=10,
            activities_shifted=3,
            remaining_overallocations=0,
            schedule_extension_days=7,
            conflicts_resolved=5,
            resources_processed=4,
            warnings=["Warning 1"],
        )

        response = _convert_parallel_result_to_response(result)

        assert response.program_id == program_id
        assert response.success is True
        assert response.iterations_used == 10
        assert response.activities_shifted == 3
        assert response.remaining_overallocations == 0
        assert response.schedule_extension_days == 7
        assert response.conflicts_resolved == 5
        assert response.resources_processed == 4
        assert response.warnings == ["Warning 1"]

    def test_converts_shifts_correctly(self):
        """Should convert all activity shifts with correct field mapping."""
        shift_id = uuid4()
        shift = _make_activity_shift(
            activity_id=shift_id,
            activity_code="TSK-042",
            original_start=date(2026, 3, 1),
            original_finish=date(2026, 3, 10),
            new_start=date(2026, 3, 5),
            new_finish=date(2026, 3, 14),
            delay_days=4,
            reason="Resource R-1 overallocated",
        )
        result = _make_parallel_result(shifts=[shift])

        response = _convert_parallel_result_to_response(result)

        assert len(response.shifts) == 1
        s = response.shifts[0]
        assert s.activity_id == shift_id
        assert s.activity_code == "TSK-042"
        assert s.original_start == date(2026, 3, 1)
        assert s.original_finish == date(2026, 3, 10)
        assert s.new_start == date(2026, 3, 5)
        assert s.new_finish == date(2026, 3, 14)
        assert s.delay_days == 4
        assert s.reason == "Resource R-1 overallocated"

    def test_converts_empty_shifts(self):
        """Should handle result with no shifts (no activities delayed)."""
        result = _make_parallel_result(
            shifts=[],
            activities_shifted=0,
            success=True,
        )

        response = _convert_parallel_result_to_response(result)

        assert len(response.shifts) == 0
        assert response.activities_shifted == 0
        assert response.success is True
