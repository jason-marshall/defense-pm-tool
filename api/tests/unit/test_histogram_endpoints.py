"""Unit tests for histogram API endpoints."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.v1.endpoints.histogram import (
    _convert_histogram_to_response,
    get_program_histogram,
    get_resource_histogram,
)
from src.models.enums import ResourceType
from src.services.resource_histogram import (
    HistogramDataPoint,
    ProgramHistogramSummary,
    ResourceHistogram,
)


def _make_histogram_data_point(
    d: date = date(2025, 1, 6),
    available: Decimal = Decimal("8"),
    assigned: Decimal = Decimal("4"),
    utilization: Decimal = Decimal("50"),
    overallocated: bool = False,
) -> HistogramDataPoint:
    """Helper to build a HistogramDataPoint."""
    return HistogramDataPoint(
        date=d,
        available_hours=available,
        assigned_hours=assigned,
        utilization_percent=utilization,
        is_overallocated=overallocated,
    )


def _make_resource_histogram(
    resource_id=None,
    data_points=None,
    start_date=date(2025, 1, 6),
    end_date=date(2025, 1, 10),
) -> ResourceHistogram:
    """Helper to build a ResourceHistogram dataclass."""
    rid = resource_id or uuid4()
    points = [_make_histogram_data_point(d=start_date)] if data_points is None else data_points
    return ResourceHistogram(
        resource_id=rid,
        resource_code="ENG-001",
        resource_name="Test Engineer",
        resource_type=ResourceType.LABOR,
        start_date=start_date,
        end_date=end_date,
        data_points=points,
        peak_utilization=Decimal("100"),
        peak_date=start_date,
        average_utilization=Decimal("50"),
        overallocated_days=0,
        total_available_hours=Decimal("40"),
        total_assigned_hours=Decimal("20"),
    )


# ---------------------------------------------------------------------------
# Tests for _convert_histogram_to_response helper
# ---------------------------------------------------------------------------


class TestConvertHistogramToResponse:
    """Tests for the _convert_histogram_to_response helper."""

    def test_converts_single_data_point(self):
        """Should convert a histogram with one data point to the response schema."""
        histogram = _make_resource_histogram()

        result = _convert_histogram_to_response(histogram)

        assert result.resource_id == histogram.resource_id
        assert result.resource_code == "ENG-001"
        assert result.resource_name == "Test Engineer"
        assert result.resource_type == ResourceType.LABOR
        assert result.start_date == histogram.start_date
        assert result.end_date == histogram.end_date
        assert len(result.data_points) == 1
        assert result.peak_utilization == Decimal("100")
        assert result.average_utilization == Decimal("50")
        assert result.overallocated_days == 0
        assert result.total_available_hours == Decimal("40")
        assert result.total_assigned_hours == Decimal("20")

    def test_converts_multiple_data_points(self):
        """Should convert all data points in the histogram."""
        points = [
            _make_histogram_data_point(d=date(2025, 1, 6)),
            _make_histogram_data_point(
                d=date(2025, 1, 7), assigned=Decimal("10"), overallocated=True
            ),
            _make_histogram_data_point(
                d=date(2025, 1, 8), assigned=Decimal("0"), utilization=Decimal("0")
            ),
        ]
        histogram = _make_resource_histogram(data_points=points)

        result = _convert_histogram_to_response(histogram)

        assert len(result.data_points) == 3
        assert result.data_points[0].date == date(2025, 1, 6)
        assert result.data_points[1].is_overallocated is True
        assert result.data_points[2].assigned_hours == Decimal("0")

    def test_converts_empty_data_points(self):
        """Should handle histogram with no data points."""
        histogram = _make_resource_histogram(data_points=[])

        result = _convert_histogram_to_response(histogram)

        assert len(result.data_points) == 0
        assert result.resource_id == histogram.resource_id


# ---------------------------------------------------------------------------
# Tests for get_resource_histogram endpoint
# ---------------------------------------------------------------------------


class TestGetResourceHistogram:
    """Tests for get_resource_histogram endpoint."""

    @pytest.mark.asyncio
    async def test_success_daily_granularity(self):
        """Should return histogram data for a valid resource with daily granularity."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        resource_id = uuid4()
        start = date(2025, 1, 6)
        end = date(2025, 1, 10)

        mock_resource = MagicMock()
        mock_resource.id = resource_id

        histogram = _make_resource_histogram(
            resource_id=resource_id, start_date=start, end_date=end
        )

        with patch("src.api.v1.endpoints.histogram.ResourceRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_repo_cls.return_value = mock_repo

            with patch("src.api.v1.endpoints.histogram.ResourceHistogramService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.get_resource_histogram = AsyncMock(return_value=histogram)
                mock_svc_cls.return_value = mock_svc

                result = await get_resource_histogram(
                    resource_id=resource_id,
                    db=mock_db,
                    current_user=mock_user,
                    start_date=start,
                    end_date=end,
                    granularity="daily",
                )

                assert result.resource_id == resource_id
                assert result.resource_code == "ENG-001"
                mock_repo.get_by_id.assert_called_once_with(resource_id)
                mock_svc.get_resource_histogram.assert_called_once_with(
                    resource_id, start, end, "daily"
                )

    @pytest.mark.asyncio
    async def test_success_weekly_granularity(self):
        """Should pass weekly granularity to the service."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        resource_id = uuid4()
        start = date(2025, 1, 6)
        end = date(2025, 1, 31)

        histogram = _make_resource_histogram(
            resource_id=resource_id, start_date=start, end_date=end
        )

        with patch("src.api.v1.endpoints.histogram.ResourceRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=MagicMock())
            mock_repo_cls.return_value = mock_repo

            with patch("src.api.v1.endpoints.histogram.ResourceHistogramService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.get_resource_histogram = AsyncMock(return_value=histogram)
                mock_svc_cls.return_value = mock_svc

                result = await get_resource_histogram(
                    resource_id=resource_id,
                    db=mock_db,
                    current_user=mock_user,
                    start_date=start,
                    end_date=end,
                    granularity="weekly",
                )

                assert result.resource_id == resource_id
                mock_svc.get_resource_histogram.assert_called_once_with(
                    resource_id, start, end, "weekly"
                )

    @pytest.mark.asyncio
    async def test_resource_not_found_in_repo(self):
        """Should raise 404 when resource does not exist in the repository."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        resource_id = uuid4()

        with patch("src.api.v1.endpoints.histogram.ResourceRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_resource_histogram(
                    resource_id=resource_id,
                    db=mock_db,
                    current_user=mock_user,
                    start_date=date(2025, 1, 6),
                    end_date=date(2025, 1, 10),
                    granularity="daily",
                )

            assert exc_info.value.status_code == 404
            assert "Resource not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_service_returns_none(self):
        """Should raise 404 when the histogram service returns None."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        resource_id = uuid4()

        with patch("src.api.v1.endpoints.histogram.ResourceRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=MagicMock())
            mock_repo_cls.return_value = mock_repo

            with patch("src.api.v1.endpoints.histogram.ResourceHistogramService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.get_resource_histogram = AsyncMock(return_value=None)
                mock_svc_cls.return_value = mock_svc

                with pytest.raises(HTTPException) as exc_info:
                    await get_resource_histogram(
                        resource_id=resource_id,
                        db=mock_db,
                        current_user=mock_user,
                        start_date=date(2025, 1, 6),
                        end_date=date(2025, 1, 10),
                        granularity="daily",
                    )

                assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_date_range(self):
        """Should raise 400 when end_date is before start_date."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        resource_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await get_resource_histogram(
                resource_id=resource_id,
                db=mock_db,
                current_user=mock_user,
                start_date=date(2025, 1, 10),
                end_date=date(2025, 1, 6),
                granularity="daily",
            )

        assert exc_info.value.status_code == 400
        assert "end_date must be after start_date" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_same_start_and_end_date(self):
        """Should succeed when start_date equals end_date (single day)."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        resource_id = uuid4()
        single_day = date(2025, 3, 15)

        histogram = _make_resource_histogram(
            resource_id=resource_id,
            start_date=single_day,
            end_date=single_day,
        )

        with patch("src.api.v1.endpoints.histogram.ResourceRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=MagicMock())
            mock_repo_cls.return_value = mock_repo

            with patch("src.api.v1.endpoints.histogram.ResourceHistogramService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.get_resource_histogram = AsyncMock(return_value=histogram)
                mock_svc_cls.return_value = mock_svc

                result = await get_resource_histogram(
                    resource_id=resource_id,
                    db=mock_db,
                    current_user=mock_user,
                    start_date=single_day,
                    end_date=single_day,
                    granularity="daily",
                )

                assert result.start_date == single_day
                assert result.end_date == single_day


# ---------------------------------------------------------------------------
# Tests for get_program_histogram endpoint
# ---------------------------------------------------------------------------


class TestGetProgramHistogram:
    """Tests for get_program_histogram endpoint."""

    @pytest.mark.asyncio
    async def test_success_with_dates(self):
        """Should return program histogram when program exists and dates given."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        program_id = uuid4()
        start = date(2025, 1, 6)
        end = date(2025, 1, 31)

        mock_program = MagicMock()
        mock_program.id = program_id

        resource_id = uuid4()
        histogram = _make_resource_histogram(
            resource_id=resource_id, start_date=start, end_date=end
        )

        summary = ProgramHistogramSummary(
            program_id=program_id,
            start_date=start,
            end_date=end,
            resource_count=1,
            total_overallocated_days=2,
            resources_with_overallocation=1,
        )

        with patch("src.api.v1.endpoints.histogram.ProgramRepository") as mock_prog_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.histogram.ResourceHistogramService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.get_program_histogram = AsyncMock(return_value=(summary, [histogram]))
                mock_svc_cls.return_value = mock_svc

                result = await get_program_histogram(
                    program_id=program_id,
                    db=mock_db,
                    current_user=mock_user,
                    start_date=start,
                    end_date=end,
                    resource_ids=None,
                )

                assert result.summary.program_id == program_id
                assert result.summary.resource_count == 1
                assert result.summary.total_overallocated_days == 2
                assert result.summary.resources_with_overallocation == 1
                assert len(result.histograms) == 1
                assert result.histograms[0].resource_id == resource_id

                mock_prog_repo.get_by_id.assert_called_once_with(program_id)
                mock_svc.get_program_histogram.assert_called_once_with(program_id, start, end, None)

    @pytest.mark.asyncio
    async def test_success_without_dates(self):
        """Should accept None for start_date and end_date (defaults to program dates)."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        program_id = uuid4()

        mock_program = MagicMock()
        mock_program.id = program_id

        summary = ProgramHistogramSummary(
            program_id=program_id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),
            resource_count=0,
            total_overallocated_days=0,
            resources_with_overallocation=0,
        )

        with patch("src.api.v1.endpoints.histogram.ProgramRepository") as mock_prog_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.histogram.ResourceHistogramService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.get_program_histogram = AsyncMock(return_value=(summary, []))
                mock_svc_cls.return_value = mock_svc

                result = await get_program_histogram(
                    program_id=program_id,
                    db=mock_db,
                    current_user=mock_user,
                    start_date=None,
                    end_date=None,
                    resource_ids=None,
                )

                assert result.summary.resource_count == 0
                assert len(result.histograms) == 0
                mock_svc.get_program_histogram.assert_called_once_with(program_id, None, None, None)

    @pytest.mark.asyncio
    async def test_program_not_found(self):
        """Should raise 404 when program does not exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        program_id = uuid4()

        with patch("src.api.v1.endpoints.histogram.ProgramRepository") as mock_prog_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_cls.return_value = mock_prog_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_program_histogram(
                    program_id=program_id,
                    db=mock_db,
                    current_user=mock_user,
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 1, 31),
                    resource_ids=None,
                )

            assert exc_info.value.status_code == 404
            assert "Program not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_date_range(self):
        """Should raise 400 when end_date is before start_date."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        program_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await get_program_histogram(
                program_id=program_id,
                db=mock_db,
                current_user=mock_user,
                start_date=date(2025, 2, 28),
                end_date=date(2025, 1, 1),
                resource_ids=None,
            )

        assert exc_info.value.status_code == 400
        assert "end_date must be after start_date" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_no_date_validation_when_only_start_given(self):
        """Should not raise when only start_date is given (end_date is None)."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        program_id = uuid4()

        mock_program = MagicMock()
        mock_program.id = program_id

        summary = ProgramHistogramSummary(
            program_id=program_id,
            start_date=date(2025, 3, 1),
            end_date=date(2025, 6, 30),
            resource_count=0,
            total_overallocated_days=0,
            resources_with_overallocation=0,
        )

        with patch("src.api.v1.endpoints.histogram.ProgramRepository") as mock_prog_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.histogram.ResourceHistogramService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.get_program_histogram = AsyncMock(return_value=(summary, []))
                mock_svc_cls.return_value = mock_svc

                # Should not raise -- end_date is None so date validation is skipped
                result = await get_program_histogram(
                    program_id=program_id,
                    db=mock_db,
                    current_user=mock_user,
                    start_date=date(2025, 3, 1),
                    end_date=None,
                    resource_ids=None,
                )

                assert result.summary.program_id == program_id

    @pytest.mark.asyncio
    async def test_with_resource_ids_filter(self):
        """Should pass resource_ids filter to the service."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        program_id = uuid4()
        r1 = uuid4()
        r2 = uuid4()
        start = date(2025, 1, 6)
        end = date(2025, 1, 10)

        mock_program = MagicMock()
        mock_program.id = program_id

        histogram1 = _make_resource_histogram(resource_id=r1, start_date=start, end_date=end)
        histogram2 = _make_resource_histogram(resource_id=r2, start_date=start, end_date=end)

        summary = ProgramHistogramSummary(
            program_id=program_id,
            start_date=start,
            end_date=end,
            resource_count=2,
            total_overallocated_days=0,
            resources_with_overallocation=0,
        )

        with patch("src.api.v1.endpoints.histogram.ProgramRepository") as mock_prog_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.histogram.ResourceHistogramService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.get_program_histogram = AsyncMock(
                    return_value=(summary, [histogram1, histogram2])
                )
                mock_svc_cls.return_value = mock_svc

                result = await get_program_histogram(
                    program_id=program_id,
                    db=mock_db,
                    current_user=mock_user,
                    start_date=start,
                    end_date=end,
                    resource_ids=[r1, r2],
                )

                assert len(result.histograms) == 2
                mock_svc.get_program_histogram.assert_called_once_with(
                    program_id, start, end, [r1, r2]
                )

    @pytest.mark.asyncio
    async def test_multiple_histograms_converted(self):
        """Should convert all resource histograms from the service."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        program_id = uuid4()
        start = date(2025, 2, 1)
        end = date(2025, 2, 28)

        mock_program = MagicMock()
        mock_program.id = program_id

        histograms = [
            _make_resource_histogram(resource_id=uuid4(), start_date=start, end_date=end)
            for _ in range(3)
        ]

        summary = ProgramHistogramSummary(
            program_id=program_id,
            start_date=start,
            end_date=end,
            resource_count=3,
            total_overallocated_days=5,
            resources_with_overallocation=2,
        )

        with patch("src.api.v1.endpoints.histogram.ProgramRepository") as mock_prog_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.histogram.ResourceHistogramService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.get_program_histogram = AsyncMock(return_value=(summary, histograms))
                mock_svc_cls.return_value = mock_svc

                result = await get_program_histogram(
                    program_id=program_id,
                    db=mock_db,
                    current_user=mock_user,
                    start_date=start,
                    end_date=end,
                    resource_ids=None,
                )

                assert len(result.histograms) == 3
                assert result.summary.resource_count == 3
                assert result.summary.total_overallocated_days == 5
                assert result.summary.resources_with_overallocation == 2

                # Verify each histogram was converted with correct resource_id
                returned_ids = {h.resource_id for h in result.histograms}
                expected_ids = {h.resource_id for h in histograms}
                assert returned_ids == expected_ids

    @pytest.mark.asyncio
    async def test_summary_dates_match(self):
        """Should propagate summary start_date and end_date into the response."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        program_id = uuid4()
        start = date(2025, 4, 1)
        end = date(2025, 4, 30)

        mock_program = MagicMock()
        mock_program.id = program_id

        summary = ProgramHistogramSummary(
            program_id=program_id,
            start_date=start,
            end_date=end,
            resource_count=0,
            total_overallocated_days=0,
            resources_with_overallocation=0,
        )

        with patch("src.api.v1.endpoints.histogram.ProgramRepository") as mock_prog_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_cls.return_value = mock_prog_repo

            with patch("src.api.v1.endpoints.histogram.ResourceHistogramService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.get_program_histogram = AsyncMock(return_value=(summary, []))
                mock_svc_cls.return_value = mock_svc

                result = await get_program_histogram(
                    program_id=program_id,
                    db=mock_db,
                    current_user=mock_user,
                    start_date=start,
                    end_date=end,
                    resource_ids=None,
                )

                assert result.summary.start_date == start
                assert result.summary.end_date == end
