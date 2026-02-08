"""Unit tests for ResourceHistogramService."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.resource_histogram import (
    HistogramDataPoint,
    ProgramHistogramSummary,
    ResourceHistogram,
    ResourceHistogramService,
)


def _make_resource(
    resource_id=None,
    code: str = "RES-001",
    name: str = "Engineer A",
    resource_type: str = "LABOR",
    capacity_per_day: Decimal = Decimal("8.0"),
) -> MagicMock:
    """Create a mock Resource model."""
    resource = MagicMock()
    resource.id = resource_id or uuid4()
    resource.code = code
    resource.name = name
    resource.resource_type = resource_type
    resource.capacity_per_day = capacity_per_day
    return resource


def _make_loading_day(
    available_hours: Decimal = Decimal("8.0"),
    assigned_hours: Decimal = Decimal("6.0"),
    is_overallocated: bool = False,
) -> MagicMock:
    """Create a mock ResourceLoadingDay."""
    day = MagicMock()
    day.available_hours = available_hours
    day.assigned_hours = assigned_hours
    day.is_overallocated = is_overallocated
    return day


def _make_program(
    program_id=None,
    start_date: date = date(2026, 1, 1),
    end_date: date = date(2026, 3, 31),
) -> MagicMock:
    """Create a mock Program model."""
    program = MagicMock()
    program.id = program_id or uuid4()
    program.start_date = start_date
    program.end_date = end_date
    return program


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    return AsyncMock()


@pytest.fixture
def mock_cache():
    """Create a mock cache service."""
    return MagicMock()


class TestGetResourceHistogram:
    """Tests for ResourceHistogramService.get_resource_histogram()."""

    @pytest.mark.asyncio
    async def test_get_resource_histogram_returns_none_for_missing(self, mock_session, mock_cache):
        """Should return None if resource not found."""
        # Arrange
        with (
            patch("src.services.resource_histogram.ResourceRepository") as MockResRepo,
            patch("src.services.resource_histogram.ProgramRepository"),
            patch("src.services.resource_histogram.ResourceLoadingService"),
        ):
            repo_instance = MockResRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=None)

            service = ResourceHistogramService(mock_session, mock_cache)
            service._resource_repo = repo_instance

            # Act
            result = await service.get_resource_histogram(
                uuid4(), date(2026, 1, 1), date(2026, 1, 7)
            )

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_get_resource_histogram_returns_histogram(self, mock_session, mock_cache):
        """Should return a ResourceHistogram with data points."""
        # Arrange
        resource = _make_resource()
        start = date(2026, 1, 1)
        end = date(2026, 1, 3)

        loading_data = {
            date(2026, 1, 1): _make_loading_day(Decimal("8"), Decimal("6"), False),
            date(2026, 1, 2): _make_loading_day(Decimal("8"), Decimal("4"), False),
            date(2026, 1, 3): _make_loading_day(Decimal("8"), Decimal("10"), True),
        }

        with (
            patch("src.services.resource_histogram.ResourceRepository") as MockResRepo,
            patch("src.services.resource_histogram.ProgramRepository"),
            patch("src.services.resource_histogram.ResourceLoadingService") as MockLoadingSvc,
        ):
            repo_instance = MockResRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=resource)

            loading_instance = MockLoadingSvc.return_value
            loading_instance.calculate_daily_loading = AsyncMock(return_value=loading_data)

            service = ResourceHistogramService(mock_session, mock_cache)
            service._resource_repo = repo_instance
            service._loading_service = loading_instance

            # Act
            result = await service.get_resource_histogram(resource.id, start, end)

            # Assert
            assert result is not None
            assert isinstance(result, ResourceHistogram)
            assert result.resource_id == resource.id
            assert len(result.data_points) == 3

    @pytest.mark.asyncio
    async def test_histogram_data_points_have_correct_fields(self, mock_session, mock_cache):
        """Should populate data point fields correctly."""
        # Arrange
        resource = _make_resource()
        start = date(2026, 1, 1)
        end = date(2026, 1, 1)

        loading_data = {
            start: _make_loading_day(Decimal("8"), Decimal("6"), False),
        }

        with (
            patch("src.services.resource_histogram.ResourceRepository") as MockResRepo,
            patch("src.services.resource_histogram.ProgramRepository"),
            patch("src.services.resource_histogram.ResourceLoadingService") as MockLoadingSvc,
        ):
            repo_instance = MockResRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=resource)

            loading_instance = MockLoadingSvc.return_value
            loading_instance.calculate_daily_loading = AsyncMock(return_value=loading_data)

            service = ResourceHistogramService(mock_session, mock_cache)
            service._resource_repo = repo_instance
            service._loading_service = loading_instance

            # Act
            result = await service.get_resource_histogram(resource.id, start, end)

            # Assert
            point = result.data_points[0]
            assert point.date == start
            assert point.available_hours == Decimal("8")
            assert point.assigned_hours == Decimal("6")
            assert point.is_overallocated is False
            # Utilization = 6/8 * 100 = 75
            assert point.utilization_percent == Decimal("75")

    @pytest.mark.asyncio
    async def test_overallocation_detection_in_data_points(self, mock_session, mock_cache):
        """Should detect overallocation when assigned > available."""
        # Arrange
        resource = _make_resource()
        start = date(2026, 1, 1)
        end = date(2026, 1, 1)

        loading_data = {
            start: _make_loading_day(Decimal("8"), Decimal("10"), True),
        }

        with (
            patch("src.services.resource_histogram.ResourceRepository") as MockResRepo,
            patch("src.services.resource_histogram.ProgramRepository"),
            patch("src.services.resource_histogram.ResourceLoadingService") as MockLoadingSvc,
        ):
            repo_instance = MockResRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=resource)

            loading_instance = MockLoadingSvc.return_value
            loading_instance.calculate_daily_loading = AsyncMock(return_value=loading_data)

            service = ResourceHistogramService(mock_session, mock_cache)
            service._resource_repo = repo_instance
            service._loading_service = loading_instance

            # Act
            result = await service.get_resource_histogram(resource.id, start, end)

            # Assert
            assert result.data_points[0].is_overallocated is True
            assert result.overallocated_days == 1

    @pytest.mark.asyncio
    async def test_utilization_percent_calculation(self, mock_session, mock_cache):
        """Should calculate utilization as (assigned/available) * 100."""
        # Arrange
        resource = _make_resource()
        start = date(2026, 1, 1)
        end = date(2026, 1, 1)

        loading_data = {
            start: _make_loading_day(Decimal("10"), Decimal("5"), False),
        }

        with (
            patch("src.services.resource_histogram.ResourceRepository") as MockResRepo,
            patch("src.services.resource_histogram.ProgramRepository"),
            patch("src.services.resource_histogram.ResourceLoadingService") as MockLoadingSvc,
        ):
            repo_instance = MockResRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=resource)

            loading_instance = MockLoadingSvc.return_value
            loading_instance.calculate_daily_loading = AsyncMock(return_value=loading_data)

            service = ResourceHistogramService(mock_session, mock_cache)
            service._resource_repo = repo_instance
            service._loading_service = loading_instance

            # Act
            result = await service.get_resource_histogram(resource.id, start, end)

            # Assert
            # 5/10 * 100 = 50%
            assert result.data_points[0].utilization_percent == Decimal("50")

    @pytest.mark.asyncio
    async def test_histogram_granularity_daily(self, mock_session, mock_cache):
        """Should return one data point per day for daily granularity."""
        # Arrange
        resource = _make_resource()
        start = date(2026, 1, 1)
        end = date(2026, 1, 5)

        loading_data = {date(2026, 1, d): _make_loading_day() for d in range(1, 6)}

        with (
            patch("src.services.resource_histogram.ResourceRepository") as MockResRepo,
            patch("src.services.resource_histogram.ProgramRepository"),
            patch("src.services.resource_histogram.ResourceLoadingService") as MockLoadingSvc,
        ):
            repo_instance = MockResRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=resource)

            loading_instance = MockLoadingSvc.return_value
            loading_instance.calculate_daily_loading = AsyncMock(return_value=loading_data)

            service = ResourceHistogramService(mock_session, mock_cache)
            service._resource_repo = repo_instance
            service._loading_service = loading_instance

            # Act
            result = await service.get_resource_histogram(
                resource.id, start, end, granularity="daily"
            )

            # Assert
            assert len(result.data_points) == 5

    @pytest.mark.asyncio
    async def test_histogram_granularity_weekly(self, mock_session, mock_cache):
        """Should aggregate data points into weekly buckets."""
        # Arrange
        resource = _make_resource()
        # Mon Jan 5 to Sun Jan 18 = 14 days = 2 full weeks
        start = date(2026, 1, 5)
        end = date(2026, 1, 18)

        loading_data = {}
        current = start
        while current <= end:
            loading_data[current] = _make_loading_day(Decimal("8"), Decimal("4"), False)
            current += timedelta(days=1)

        with (
            patch("src.services.resource_histogram.ResourceRepository") as MockResRepo,
            patch("src.services.resource_histogram.ProgramRepository"),
            patch("src.services.resource_histogram.ResourceLoadingService") as MockLoadingSvc,
        ):
            repo_instance = MockResRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=resource)

            loading_instance = MockLoadingSvc.return_value
            loading_instance.calculate_daily_loading = AsyncMock(return_value=loading_data)

            service = ResourceHistogramService(mock_session, mock_cache)
            service._resource_repo = repo_instance
            service._loading_service = loading_instance

            # Act
            result = await service.get_resource_histogram(
                resource.id, start, end, granularity="weekly"
            )

            # Assert
            # 14 days = 2 calendar weeks
            assert len(result.data_points) == 2


class TestAggregateToWeekly:
    """Tests for ResourceHistogramService._aggregate_to_weekly()."""

    def test_aggregate_to_weekly_groups_by_week(self, mock_session):
        """Should group daily data into weekly buckets."""
        # Arrange
        service = ResourceHistogramService.__new__(ResourceHistogramService)

        # Mon Jan 5 through Sun Jan 11 = 1 week, Mon Jan 12 through Sat Jan 17 = partial week
        daily_data = []
        for d in range(5, 18):  # Jan 5 to Jan 17
            daily_data.append(
                HistogramDataPoint(
                    date=date(2026, 1, d),
                    available_hours=Decimal("8"),
                    assigned_hours=Decimal("4"),
                    utilization_percent=Decimal("50"),
                    is_overallocated=False,
                )
            )

        # Act
        result = service._aggregate_to_weekly(daily_data)

        # Assert
        # 13 days spanning 2 calendar weeks
        assert len(result) == 2

    def test_aggregate_to_weekly_sums_hours(self, mock_session):
        """Should sum available and assigned hours within each week."""
        # Arrange
        service = ResourceHistogramService.__new__(ResourceHistogramService)

        # 5 days in same week (Mon-Fri Jan 5-9)
        daily_data = [
            HistogramDataPoint(
                date=date(2026, 1, 5 + i),
                available_hours=Decimal("8"),
                assigned_hours=Decimal("6"),
                utilization_percent=Decimal("75"),
                is_overallocated=False,
            )
            for i in range(5)
        ]

        # Act
        result = service._aggregate_to_weekly(daily_data)

        # Assert
        assert len(result) == 1
        assert result[0].available_hours == Decimal("40")  # 5 * 8
        assert result[0].assigned_hours == Decimal("30")  # 5 * 6

    def test_aggregate_to_weekly_empty_data(self, mock_session):
        """Should return empty list for empty input."""
        # Arrange
        service = ResourceHistogramService.__new__(ResourceHistogramService)

        # Act
        result = service._aggregate_to_weekly([])

        # Assert
        assert result == []


class TestCalculateStatistics:
    """Tests for ResourceHistogramService._calculate_statistics()."""

    def test_calculate_statistics_returns_correct_keys(self, mock_session):
        """Should return dict with all expected keys."""
        # Arrange
        service = ResourceHistogramService.__new__(ResourceHistogramService)
        data_points = [
            HistogramDataPoint(
                date=date(2026, 1, 1),
                available_hours=Decimal("8"),
                assigned_hours=Decimal("6"),
                utilization_percent=Decimal("75"),
                is_overallocated=False,
            )
        ]

        # Act
        stats = service._calculate_statistics(data_points)

        # Assert
        expected_keys = {
            "peak_utilization",
            "peak_date",
            "average_utilization",
            "overallocated_days",
            "total_available_hours",
            "total_assigned_hours",
        }
        assert set(stats.keys()) == expected_keys

    def test_calculate_statistics_with_empty_data(self, mock_session):
        """Should return zero values for empty data points."""
        # Arrange
        service = ResourceHistogramService.__new__(ResourceHistogramService)

        # Act
        stats = service._calculate_statistics([])

        # Assert
        assert stats["peak_utilization"] == Decimal("0")
        assert stats["peak_date"] is None
        assert stats["average_utilization"] == Decimal("0")
        assert stats["overallocated_days"] == 0
        assert stats["total_available_hours"] == Decimal("0")
        assert stats["total_assigned_hours"] == Decimal("0")

    def test_calculate_statistics_peak_and_average(self, mock_session):
        """Should compute peak and average utilization correctly."""
        # Arrange
        service = ResourceHistogramService.__new__(ResourceHistogramService)
        data_points = [
            HistogramDataPoint(
                date=date(2026, 1, 1),
                available_hours=Decimal("8"),
                assigned_hours=Decimal("4"),
                utilization_percent=Decimal("50"),
                is_overallocated=False,
            ),
            HistogramDataPoint(
                date=date(2026, 1, 2),
                available_hours=Decimal("8"),
                assigned_hours=Decimal("8"),
                utilization_percent=Decimal("100"),
                is_overallocated=False,
            ),
        ]

        # Act
        stats = service._calculate_statistics(data_points)

        # Assert
        assert stats["peak_utilization"] == Decimal("100")
        assert stats["peak_date"] == date(2026, 1, 2)
        assert stats["average_utilization"] == Decimal("75")  # (50 + 100) / 2


class TestGetProgramHistogram:
    """Tests for ResourceHistogramService.get_program_histogram()."""

    @pytest.mark.asyncio
    async def test_program_histogram_returns_summary_and_list(self, mock_session, mock_cache):
        """Should return a tuple of (summary, list of histograms)."""
        # Arrange
        program = _make_program()
        resource = _make_resource()

        loading_data = {
            date(2026, 1, 1): _make_loading_day(),
        }

        with (
            patch("src.services.resource_histogram.ResourceRepository") as MockResRepo,
            patch("src.services.resource_histogram.ProgramRepository") as MockProgRepo,
            patch("src.services.resource_histogram.ResourceLoadingService") as MockLoadingSvc,
        ):
            res_repo = MockResRepo.return_value
            res_repo.get_by_id = AsyncMock(return_value=resource)
            res_repo.get_by_program = AsyncMock(return_value=([resource], 1))

            prog_repo = MockProgRepo.return_value
            prog_repo.get_by_id = AsyncMock(return_value=program)

            loading_svc = MockLoadingSvc.return_value
            loading_svc.calculate_daily_loading = AsyncMock(return_value=loading_data)

            service = ResourceHistogramService(mock_session, mock_cache)
            service._resource_repo = res_repo
            service._program_repo = prog_repo
            service._loading_service = loading_svc

            # Act
            summary, histograms = await service.get_program_histogram(
                program.id,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 1),
            )

            # Assert
            assert isinstance(summary, ProgramHistogramSummary)
            assert isinstance(histograms, list)
            assert summary.resource_count == 1

    @pytest.mark.asyncio
    async def test_program_histogram_filters_by_resource_ids(self, mock_session, mock_cache):
        """Should only include specified resource IDs when filter provided."""
        # Arrange
        program = _make_program()
        res1 = _make_resource(resource_id=uuid4(), code="R1")
        res2 = _make_resource(resource_id=uuid4(), code="R2")

        loading_data = {
            date(2026, 1, 1): _make_loading_day(),
        }

        with (
            patch("src.services.resource_histogram.ResourceRepository") as MockResRepo,
            patch("src.services.resource_histogram.ProgramRepository") as MockProgRepo,
            patch("src.services.resource_histogram.ResourceLoadingService") as MockLoadingSvc,
        ):
            res_repo = MockResRepo.return_value
            res_repo.get_by_id = AsyncMock(return_value=res1)
            res_repo.get_by_program = AsyncMock(return_value=([res1, res2], 2))

            prog_repo = MockProgRepo.return_value
            prog_repo.get_by_id = AsyncMock(return_value=program)

            loading_svc = MockLoadingSvc.return_value
            loading_svc.calculate_daily_loading = AsyncMock(return_value=loading_data)

            service = ResourceHistogramService(mock_session, mock_cache)
            service._resource_repo = res_repo
            service._program_repo = prog_repo
            service._loading_service = loading_svc

            # Act
            summary, _histograms = await service.get_program_histogram(
                program.id,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 1),
                resource_ids=[res1.id],
            )

            # Assert
            # Only res1 should be included (filtered out res2)
            assert summary.resource_count == 1

    @pytest.mark.asyncio
    async def test_program_histogram_missing_program(self, mock_session, mock_cache):
        """Should return empty summary when program not found."""
        # Arrange
        program_id = uuid4()

        with (
            patch("src.services.resource_histogram.ResourceRepository"),
            patch("src.services.resource_histogram.ProgramRepository") as MockProgRepo,
            patch("src.services.resource_histogram.ResourceLoadingService"),
        ):
            prog_repo = MockProgRepo.return_value
            prog_repo.get_by_id = AsyncMock(return_value=None)

            service = ResourceHistogramService(mock_session, mock_cache)
            service._program_repo = prog_repo

            # Act
            summary, histograms = await service.get_program_histogram(program_id)

            # Assert
            assert summary.resource_count == 0
            assert histograms == []
