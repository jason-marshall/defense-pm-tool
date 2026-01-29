"""Unit tests for ResourceHistogramService.

Tests histogram generation, aggregation, and statistics calculation.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.enums import ResourceType
from src.services.resource_histogram import (
    HistogramDataPoint,
    ProgramHistogramSummary,
    ResourceHistogram,
    ResourceHistogramService,
)


class TestHistogramDataPoint:
    """Tests for HistogramDataPoint dataclass."""

    def test_create_data_point(self) -> None:
        """Should create data point with all fields."""
        point = HistogramDataPoint(
            date=date(2024, 1, 15),
            available_hours=Decimal("8.0"),
            assigned_hours=Decimal("6.0"),
            utilization_percent=Decimal("75.0"),
            is_overallocated=False,
        )

        assert point.date == date(2024, 1, 15)
        assert point.available_hours == Decimal("8.0")
        assert point.assigned_hours == Decimal("6.0")
        assert point.utilization_percent == Decimal("75.0")
        assert point.is_overallocated is False

    def test_overallocated_point(self) -> None:
        """Should represent over-allocated day."""
        point = HistogramDataPoint(
            date=date(2024, 1, 15),
            available_hours=Decimal("8.0"),
            assigned_hours=Decimal("12.0"),
            utilization_percent=Decimal("150.0"),
            is_overallocated=True,
        )

        assert point.is_overallocated is True
        assert point.utilization_percent > Decimal("100")


class TestResourceHistogram:
    """Tests for ResourceHistogram dataclass."""

    def test_create_histogram(self) -> None:
        """Should create histogram with all fields."""
        resource_id = uuid4()
        histogram = ResourceHistogram(
            resource_id=resource_id,
            resource_code="ENG-001",
            resource_name="Engineer 1",
            resource_type=ResourceType.LABOR,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            data_points=[],
            peak_utilization=Decimal("85.0"),
            peak_date=date(2024, 1, 15),
            average_utilization=Decimal("60.0"),
            overallocated_days=2,
            total_available_hours=Decimal("160.0"),
            total_assigned_hours=Decimal("96.0"),
        )

        assert histogram.resource_id == resource_id
        assert histogram.resource_code == "ENG-001"
        assert histogram.peak_utilization == Decimal("85.0")
        assert histogram.overallocated_days == 2


class TestProgramHistogramSummary:
    """Tests for ProgramHistogramSummary dataclass."""

    def test_create_summary(self) -> None:
        """Should create program summary."""
        program_id = uuid4()
        summary = ProgramHistogramSummary(
            program_id=program_id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            resource_count=5,
            total_overallocated_days=12,
            resources_with_overallocation=2,
        )

        assert summary.program_id == program_id
        assert summary.resource_count == 5
        assert summary.total_overallocated_days == 12
        assert summary.resources_with_overallocation == 2


class TestGetResourceHistogram:
    """Tests for get_resource_histogram method."""

    @pytest.mark.asyncio
    async def test_single_resource_histogram(self) -> None:
        """Should generate histogram for single resource."""
        mock_session = MagicMock()
        service = ResourceHistogramService(mock_session)

        resource_id = uuid4()

        # Mock resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "ENG-001"
        mock_resource.name = "Engineer 1"
        mock_resource.resource_type = ResourceType.LABOR
        mock_resource.capacity_per_day = Decimal("8.0")
        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)

        # Mock loading service - 5 days of data
        mock_loading = {}
        for i in range(5):
            day = date(2024, 1, 15) + timedelta(days=i)
            mock_day = MagicMock()
            mock_day.available_hours = Decimal("8.0")
            mock_day.assigned_hours = Decimal("6.0")
            mock_day.is_overallocated = False
            mock_loading[day] = mock_day

        service._loading_service = MagicMock()
        service._loading_service.calculate_daily_loading = AsyncMock(return_value=mock_loading)

        # Act
        result = await service.get_resource_histogram(
            resource_id, date(2024, 1, 15), date(2024, 1, 19)
        )

        # Assert
        assert result is not None
        assert result.resource_id == resource_id
        assert result.resource_code == "ENG-001"
        assert len(result.data_points) == 5
        assert result.average_utilization == Decimal("75.0")

    @pytest.mark.asyncio
    async def test_histogram_with_overallocation(self) -> None:
        """Should correctly identify over-allocated days."""
        mock_session = MagicMock()
        service = ResourceHistogramService(mock_session)

        resource_id = uuid4()

        # Mock resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "ENG-001"
        mock_resource.name = "Engineer 1"
        mock_resource.resource_type = ResourceType.LABOR
        mock_resource.capacity_per_day = Decimal("8.0")
        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)

        # Mock loading with 2 overallocated days
        mock_loading = {}
        for i in range(5):
            day = date(2024, 1, 15) + timedelta(days=i)
            mock_day = MagicMock()
            mock_day.available_hours = Decimal("8.0")
            if i < 2:  # First 2 days overallocated
                mock_day.assigned_hours = Decimal("12.0")
                mock_day.is_overallocated = True
            else:
                mock_day.assigned_hours = Decimal("6.0")
                mock_day.is_overallocated = False
            mock_loading[day] = mock_day

        service._loading_service = MagicMock()
        service._loading_service.calculate_daily_loading = AsyncMock(return_value=mock_loading)

        # Act
        result = await service.get_resource_histogram(
            resource_id, date(2024, 1, 15), date(2024, 1, 19)
        )

        # Assert
        assert result is not None
        assert result.overallocated_days == 2
        assert result.peak_utilization == Decimal("150.0")

    @pytest.mark.asyncio
    async def test_resource_not_found(self) -> None:
        """Should return None if resource not found."""
        mock_session = MagicMock()
        service = ResourceHistogramService(mock_session)

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=None)

        result = await service.get_resource_histogram(uuid4(), date(2024, 1, 1), date(2024, 1, 31))

        assert result is None


class TestWeeklyAggregation:
    """Tests for weekly aggregation."""

    def test_aggregate_to_weekly(self) -> None:
        """Should aggregate daily data to weekly."""
        mock_session = MagicMock()
        service = ResourceHistogramService(mock_session)

        # Create 14 days of data (2 full weeks starting Monday)
        daily_data = []
        # Start from Monday 2024-01-15
        for i in range(14):
            day = date(2024, 1, 15) + timedelta(days=i)
            daily_data.append(
                HistogramDataPoint(
                    date=day,
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("6.0"),
                    utilization_percent=Decimal("75.0"),
                    is_overallocated=False,
                )
            )

        # Act
        weekly_data = service._aggregate_to_weekly(daily_data)

        # Assert
        assert len(weekly_data) == 2
        # Each week should have summed hours
        assert weekly_data[0].available_hours == Decimal("56.0")  # 7 * 8
        assert weekly_data[0].assigned_hours == Decimal("42.0")  # 7 * 6

    def test_aggregate_partial_week(self) -> None:
        """Should handle partial weeks."""
        mock_session = MagicMock()
        service = ResourceHistogramService(mock_session)

        # Create 10 days (1 full week + 3 days)
        daily_data = []
        for i in range(10):
            day = date(2024, 1, 15) + timedelta(days=i)
            daily_data.append(
                HistogramDataPoint(
                    date=day,
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("6.0"),
                    utilization_percent=Decimal("75.0"),
                    is_overallocated=False,
                )
            )

        # Act
        weekly_data = service._aggregate_to_weekly(daily_data)

        # Assert
        assert len(weekly_data) == 2

    def test_aggregate_with_overallocation(self) -> None:
        """Should mark week as overallocated if any day is."""
        mock_session = MagicMock()
        service = ResourceHistogramService(mock_session)

        # Create 7 days with 1 overallocated
        daily_data = []
        for i in range(7):
            day = date(2024, 1, 15) + timedelta(days=i)
            is_over = i == 3  # Only day 4 is overallocated
            daily_data.append(
                HistogramDataPoint(
                    date=day,
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("10.0") if is_over else Decimal("6.0"),
                    utilization_percent=Decimal("125.0") if is_over else Decimal("75.0"),
                    is_overallocated=is_over,
                )
            )

        # Act
        weekly_data = service._aggregate_to_weekly(daily_data)

        # Assert
        assert len(weekly_data) == 1
        assert weekly_data[0].is_overallocated is True


class TestStatisticsCalculation:
    """Tests for statistics calculation."""

    def test_calculate_statistics(self) -> None:
        """Should calculate correct statistics."""
        mock_session = MagicMock()
        service = ResourceHistogramService(mock_session)

        data_points = [
            HistogramDataPoint(
                date=date(2024, 1, 15),
                available_hours=Decimal("8.0"),
                assigned_hours=Decimal("4.0"),
                utilization_percent=Decimal("50.0"),
                is_overallocated=False,
            ),
            HistogramDataPoint(
                date=date(2024, 1, 16),
                available_hours=Decimal("8.0"),
                assigned_hours=Decimal("8.0"),
                utilization_percent=Decimal("100.0"),
                is_overallocated=False,
            ),
            HistogramDataPoint(
                date=date(2024, 1, 17),
                available_hours=Decimal("8.0"),
                assigned_hours=Decimal("10.0"),
                utilization_percent=Decimal("125.0"),
                is_overallocated=True,
            ),
        ]

        # Act
        stats = service._calculate_statistics(data_points)

        # Assert
        assert stats["peak_utilization"] == Decimal("125.0")
        assert stats["peak_date"] == date(2024, 1, 17)
        assert stats["average_utilization"] == Decimal("275.0") / 3
        assert stats["overallocated_days"] == 1
        assert stats["total_available_hours"] == Decimal("24.0")
        assert stats["total_assigned_hours"] == Decimal("22.0")

    def test_empty_data_points(self) -> None:
        """Should handle empty data points."""
        mock_session = MagicMock()
        service = ResourceHistogramService(mock_session)

        stats = service._calculate_statistics([])

        assert stats["peak_utilization"] == Decimal("0")
        assert stats["peak_date"] is None
        assert stats["average_utilization"] == Decimal("0")
        assert stats["overallocated_days"] == 0


class TestGetProgramHistogram:
    """Tests for get_program_histogram method."""

    @pytest.mark.asyncio
    async def test_program_histogram(self) -> None:
        """Should generate histograms for all resources in program."""
        mock_session = MagicMock()
        service = ResourceHistogramService(mock_session)

        program_id = uuid4()
        resource1_id = uuid4()
        resource2_id = uuid4()

        # Mock program
        mock_program = MagicMock()
        mock_program.start_date = date(2024, 1, 1)
        mock_program.end_date = date(2024, 12, 31)
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        # Mock resources
        mock_resource1 = MagicMock()
        mock_resource1.id = resource1_id
        mock_resource1.code = "ENG-001"
        mock_resource1.name = "Engineer 1"
        mock_resource1.resource_type = ResourceType.LABOR
        mock_resource1.capacity_per_day = Decimal("8.0")

        mock_resource2 = MagicMock()
        mock_resource2.id = resource2_id
        mock_resource2.code = "ENG-002"
        mock_resource2.name = "Engineer 2"
        mock_resource2.resource_type = ResourceType.LABOR
        mock_resource2.capacity_per_day = Decimal("8.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_program = AsyncMock(
            return_value=([mock_resource1, mock_resource2], 2)
        )
        service._resource_repo.get_by_id = AsyncMock(
            side_effect=lambda id: mock_resource1 if id == resource1_id else mock_resource2
        )

        # Mock loading service
        service._loading_service = MagicMock()
        service._loading_service.calculate_daily_loading = AsyncMock(return_value={})

        # Act
        summary, histograms = await service.get_program_histogram(
            program_id, date(2024, 1, 1), date(2024, 1, 5)
        )

        # Assert
        assert summary.program_id == program_id
        assert summary.resource_count == 2
        assert len(histograms) == 2

    @pytest.mark.asyncio
    async def test_program_not_found(self) -> None:
        """Should return empty result if program not found."""
        mock_session = MagicMock()
        service = ResourceHistogramService(mock_session)

        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=None)

        summary, histograms = await service.get_program_histogram(
            uuid4(), date(2024, 1, 1), date(2024, 1, 31)
        )

        assert summary.resource_count == 0
        assert len(histograms) == 0

    @pytest.mark.asyncio
    async def test_filter_by_resource_ids(self) -> None:
        """Should filter to specified resources."""
        mock_session = MagicMock()
        service = ResourceHistogramService(mock_session)

        program_id = uuid4()
        resource1_id = uuid4()
        resource2_id = uuid4()

        # Mock program
        mock_program = MagicMock()
        mock_program.start_date = date(2024, 1, 1)
        mock_program.end_date = date(2024, 12, 31)
        service._program_repo = MagicMock()
        service._program_repo.get_by_id = AsyncMock(return_value=mock_program)

        # Mock resources - return 2, but we'll filter to 1
        mock_resource1 = MagicMock()
        mock_resource1.id = resource1_id
        mock_resource1.code = "ENG-001"
        mock_resource1.name = "Engineer 1"
        mock_resource1.resource_type = ResourceType.LABOR
        mock_resource1.capacity_per_day = Decimal("8.0")

        mock_resource2 = MagicMock()
        mock_resource2.id = resource2_id
        mock_resource2.code = "ENG-002"
        mock_resource2.name = "Engineer 2"
        mock_resource2.resource_type = ResourceType.LABOR
        mock_resource2.capacity_per_day = Decimal("8.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_program = AsyncMock(
            return_value=([mock_resource1, mock_resource2], 2)
        )
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource1)

        # Mock loading service
        service._loading_service = MagicMock()
        service._loading_service.calculate_daily_loading = AsyncMock(return_value={})

        # Act - filter to only resource1
        summary, histograms = await service.get_program_histogram(
            program_id,
            date(2024, 1, 1),
            date(2024, 1, 5),
            resource_ids=[resource1_id],
        )

        # Assert - should only have 1 histogram
        assert summary.resource_count == 1
        assert len(histograms) == 1
        assert histograms[0].resource_id == resource1_id
