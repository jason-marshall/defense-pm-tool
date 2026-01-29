"""Unit tests for ResourceLoadingService.

Tests the resource loading calculation logic including:
- Assignment date range resolution (assignment → planned → early dates)
- Daily loading calculation with calendar awareness
- Overallocation detection
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.resource import ResourceLoadingDay
from src.services.resource_loading import ResourceLoadingService


class TestGetAssignmentDateRange:
    """Tests for get_assignment_date_range method."""

    def test_explicit_assignment_dates_take_priority(self) -> None:
        """Should use explicit assignment dates when set."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_assignment = MagicMock()
        mock_assignment.start_date = date(2024, 1, 15)
        mock_assignment.finish_date = date(2024, 1, 25)
        mock_assignment.activity = MagicMock()
        mock_assignment.activity.planned_start = date(2024, 1, 1)
        mock_assignment.activity.planned_finish = date(2024, 1, 31)
        mock_assignment.activity.early_start = date(2024, 1, 5)
        mock_assignment.activity.early_finish = date(2024, 2, 5)

        # Act
        start, finish = service.get_assignment_date_range(mock_assignment)

        # Assert
        assert start == date(2024, 1, 15)
        assert finish == date(2024, 1, 25)

    def test_falls_back_to_planned_dates(self) -> None:
        """Should use activity planned dates when assignment dates not set."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_assignment = MagicMock()
        mock_assignment.start_date = None
        mock_assignment.finish_date = None
        mock_assignment.activity = MagicMock()
        mock_assignment.activity.planned_start = date(2024, 1, 1)
        mock_assignment.activity.planned_finish = date(2024, 1, 31)
        mock_assignment.activity.early_start = date(2024, 1, 5)
        mock_assignment.activity.early_finish = date(2024, 2, 5)

        # Act
        start, finish = service.get_assignment_date_range(mock_assignment)

        # Assert
        assert start == date(2024, 1, 1)
        assert finish == date(2024, 1, 31)

    def test_falls_back_to_early_dates(self) -> None:
        """Should use activity early dates when planned dates not set."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_assignment = MagicMock()
        mock_assignment.start_date = None
        mock_assignment.finish_date = None
        mock_assignment.activity = MagicMock()
        mock_assignment.activity.planned_start = None
        mock_assignment.activity.planned_finish = None
        mock_assignment.activity.early_start = date(2024, 1, 5)
        mock_assignment.activity.early_finish = date(2024, 2, 5)

        # Act
        start, finish = service.get_assignment_date_range(mock_assignment)

        # Assert
        assert start == date(2024, 1, 5)
        assert finish == date(2024, 2, 5)

    def test_mixed_date_sources(self) -> None:
        """Should allow mixing date sources between start and finish."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_assignment = MagicMock()
        mock_assignment.start_date = date(2024, 1, 10)  # Explicit start
        mock_assignment.finish_date = None  # No explicit finish
        mock_assignment.activity = MagicMock()
        mock_assignment.activity.planned_start = date(2024, 1, 1)
        mock_assignment.activity.planned_finish = date(2024, 1, 31)  # Use this
        mock_assignment.activity.early_start = date(2024, 1, 5)
        mock_assignment.activity.early_finish = date(2024, 2, 5)

        # Act
        start, finish = service.get_assignment_date_range(mock_assignment)

        # Assert
        assert start == date(2024, 1, 10)  # Explicit
        assert finish == date(2024, 1, 31)  # Planned

    def test_no_activity_returns_assignment_dates(self) -> None:
        """Should return assignment dates when no activity attached."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_assignment = MagicMock()
        mock_assignment.start_date = date(2024, 1, 1)
        mock_assignment.finish_date = date(2024, 1, 10)
        mock_assignment.activity = None

        # Act
        start, finish = service.get_assignment_date_range(mock_assignment)

        # Assert
        assert start == date(2024, 1, 1)
        assert finish == date(2024, 1, 10)

    def test_no_dates_available(self) -> None:
        """Should return None for both when no dates available."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_assignment = MagicMock()
        mock_assignment.start_date = None
        mock_assignment.finish_date = None
        mock_assignment.activity = MagicMock()
        mock_assignment.activity.planned_start = None
        mock_assignment.activity.planned_finish = None
        mock_assignment.activity.early_start = None
        mock_assignment.activity.early_finish = None

        # Act
        start, finish = service.get_assignment_date_range(mock_assignment)

        # Assert
        assert start is None
        assert finish is None


class TestIsAssignmentActiveOnDate:
    """Tests for _is_assignment_active_on_date method."""

    def test_active_within_range(self) -> None:
        """Should return True for dates within assignment range."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_assignment = MagicMock()
        mock_assignment.start_date = date(2024, 1, 1)
        mock_assignment.finish_date = date(2024, 1, 10)
        mock_assignment.activity = None

        # Act & Assert
        assert service._is_assignment_active_on_date(mock_assignment, date(2024, 1, 1))
        assert service._is_assignment_active_on_date(mock_assignment, date(2024, 1, 5))
        assert service._is_assignment_active_on_date(mock_assignment, date(2024, 1, 10))

    def test_inactive_before_start(self) -> None:
        """Should return False for dates before start."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_assignment = MagicMock()
        mock_assignment.start_date = date(2024, 1, 10)
        mock_assignment.finish_date = date(2024, 1, 20)
        mock_assignment.activity = None

        # Act & Assert
        assert not service._is_assignment_active_on_date(mock_assignment, date(2024, 1, 9))
        assert not service._is_assignment_active_on_date(mock_assignment, date(2024, 1, 1))

    def test_inactive_after_finish(self) -> None:
        """Should return False for dates after finish."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_assignment = MagicMock()
        mock_assignment.start_date = date(2024, 1, 1)
        mock_assignment.finish_date = date(2024, 1, 10)
        mock_assignment.activity = None

        # Act & Assert
        assert not service._is_assignment_active_on_date(mock_assignment, date(2024, 1, 11))
        assert not service._is_assignment_active_on_date(mock_assignment, date(2024, 1, 20))

    def test_no_start_date_assumes_active_from_beginning(self) -> None:
        """Should assume active from beginning when no start date."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_assignment = MagicMock()
        mock_assignment.start_date = None
        mock_assignment.finish_date = date(2024, 1, 10)
        mock_assignment.activity = None

        # Act & Assert
        assert service._is_assignment_active_on_date(mock_assignment, date(2024, 1, 1))
        assert service._is_assignment_active_on_date(mock_assignment, date(2023, 1, 1))

    def test_no_finish_date_assumes_active_indefinitely(self) -> None:
        """Should assume active indefinitely when no finish date."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_assignment = MagicMock()
        mock_assignment.start_date = date(2024, 1, 1)
        mock_assignment.finish_date = None
        mock_assignment.activity = None

        # Act & Assert
        assert service._is_assignment_active_on_date(mock_assignment, date(2024, 1, 10))
        assert service._is_assignment_active_on_date(mock_assignment, date(2025, 12, 31))


class TestGetLoadingForAssignment:
    """Tests for get_loading_for_assignment method."""

    def test_calculates_hours_per_day(self) -> None:
        """Should calculate assigned hours based on units and capacity."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        mock_assignment = MagicMock()
        mock_assignment.start_date = date(2024, 1, 1)
        mock_assignment.finish_date = date(2024, 1, 3)
        mock_assignment.units = Decimal("1.0")  # 100% allocation
        mock_assignment.activity = None

        # Act
        loading = service.get_loading_for_assignment(
            mock_assignment,
            mock_resource,
            date(2024, 1, 1),
            date(2024, 1, 3),
        )

        # Assert
        assert len(loading) == 3
        assert loading[date(2024, 1, 1)] == Decimal("8.00")
        assert loading[date(2024, 1, 2)] == Decimal("8.00")
        assert loading[date(2024, 1, 3)] == Decimal("8.00")

    def test_partial_allocation(self) -> None:
        """Should calculate hours for partial allocation."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        mock_assignment = MagicMock()
        mock_assignment.start_date = date(2024, 1, 1)
        mock_assignment.finish_date = date(2024, 1, 1)
        mock_assignment.units = Decimal("0.5")  # 50% allocation
        mock_assignment.activity = None

        # Act
        loading = service.get_loading_for_assignment(
            mock_assignment,
            mock_resource,
            date(2024, 1, 1),
            date(2024, 1, 1),
        )

        # Assert
        assert loading[date(2024, 1, 1)] == Decimal("4.00")

    def test_zero_for_inactive_dates(self) -> None:
        """Should return zero for dates outside assignment range."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        mock_assignment = MagicMock()
        mock_assignment.start_date = date(2024, 1, 5)
        mock_assignment.finish_date = date(2024, 1, 10)
        mock_assignment.units = Decimal("1.0")
        mock_assignment.activity = None

        # Act
        loading = service.get_loading_for_assignment(
            mock_assignment,
            mock_resource,
            date(2024, 1, 1),
            date(2024, 1, 15),
        )

        # Assert
        # Before assignment
        assert loading[date(2024, 1, 1)] == Decimal("0")
        assert loading[date(2024, 1, 4)] == Decimal("0")
        # During assignment
        assert loading[date(2024, 1, 5)] == Decimal("8.00")
        assert loading[date(2024, 1, 10)] == Decimal("8.00")
        # After assignment
        assert loading[date(2024, 1, 11)] == Decimal("0")
        assert loading[date(2024, 1, 15)] == Decimal("0")


class TestCalculateDailyLoading:
    """Tests for calculate_daily_loading method."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_nonexistent_resource(self) -> None:
        """Should return empty dict when resource not found."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)
        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=None)

        # Act
        result = await service.calculate_daily_loading(
            uuid4(),
            date(2024, 1, 1),
            date(2024, 1, 5),
        )

        # Assert
        assert result == {}

    @pytest.mark.asyncio
    async def test_uses_calendar_availability(self) -> None:
        """Should use calendar entries for availability when present."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.capacity_per_day = Decimal("8.0")

        # Calendar entry for Jan 2 - only 4 hours
        mock_calendar_entry = MagicMock()
        mock_calendar_entry.calendar_date = date(2024, 1, 2)
        mock_calendar_entry.available_hours = Decimal("4.0")
        mock_calendar_entry.is_working_day = True

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._calendar_repo = MagicMock()
        service._calendar_repo.get_for_date_range = AsyncMock(return_value=[mock_calendar_entry])
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(return_value=[])

        # Act
        result = await service.calculate_daily_loading(
            resource_id,
            date(2024, 1, 1),
            date(2024, 1, 3),
        )

        # Assert
        assert result[date(2024, 1, 1)].available_hours == Decimal("8.0")  # Default
        assert result[date(2024, 1, 2)].available_hours == Decimal("4.0")  # Calendar
        assert result[date(2024, 1, 3)].available_hours == Decimal("8.0")  # Default

    @pytest.mark.asyncio
    async def test_weekends_have_zero_availability(self) -> None:
        """Should have zero availability on weekends without calendar entry."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.capacity_per_day = Decimal("8.0")

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._calendar_repo = MagicMock()
        service._calendar_repo.get_for_date_range = AsyncMock(return_value=[])
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(return_value=[])

        # Act - Jan 6, 2024 is Saturday, Jan 7 is Sunday
        result = await service.calculate_daily_loading(
            resource_id,
            date(2024, 1, 5),  # Friday
            date(2024, 1, 8),  # Monday
        )

        # Assert
        assert result[date(2024, 1, 5)].available_hours == Decimal("8.0")  # Friday
        assert result[date(2024, 1, 6)].available_hours == Decimal("0")  # Saturday
        assert result[date(2024, 1, 7)].available_hours == Decimal("0")  # Sunday
        assert result[date(2024, 1, 8)].available_hours == Decimal("8.0")  # Monday

    @pytest.mark.asyncio
    async def test_aggregates_multiple_assignments(self) -> None:
        """Should sum hours from multiple overlapping assignments."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.capacity_per_day = Decimal("8.0")

        # Two assignments, both active on Jan 2
        mock_assignment1 = MagicMock()
        mock_assignment1.start_date = date(2024, 1, 1)
        mock_assignment1.finish_date = date(2024, 1, 3)
        mock_assignment1.units = Decimal("0.5")  # 50%
        mock_assignment1.activity = None

        mock_assignment2 = MagicMock()
        mock_assignment2.start_date = date(2024, 1, 2)
        mock_assignment2.finish_date = date(2024, 1, 4)
        mock_assignment2.units = Decimal("0.75")  # 75%
        mock_assignment2.activity = None

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._calendar_repo = MagicMock()
        service._calendar_repo.get_for_date_range = AsyncMock(return_value=[])
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[mock_assignment1, mock_assignment2]
        )

        # Act
        result = await service.calculate_daily_loading(
            resource_id,
            date(2024, 1, 1),
            date(2024, 1, 4),
        )

        # Assert
        # Jan 1: only assignment1 (0.5 * 8 = 4)
        assert result[date(2024, 1, 1)].assigned_hours == Decimal("4.00")
        # Jan 2: both (0.5 * 8 + 0.75 * 8 = 10)
        assert result[date(2024, 1, 2)].assigned_hours == Decimal("10.00")
        # Jan 3: both
        assert result[date(2024, 1, 3)].assigned_hours == Decimal("10.00")
        # Jan 4: only assignment2 (0.75 * 8 = 6)
        assert result[date(2024, 1, 4)].assigned_hours == Decimal("6.00")

    @pytest.mark.asyncio
    async def test_detects_overallocation(self) -> None:
        """Should mark days as overallocated when assigned exceeds available."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.capacity_per_day = Decimal("8.0")

        # Assignment for 150% allocation
        mock_assignment = MagicMock()
        mock_assignment.start_date = date(2024, 1, 1)
        mock_assignment.finish_date = date(2024, 1, 1)
        mock_assignment.units = Decimal("1.5")  # 150%
        mock_assignment.activity = None

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)
        service._calendar_repo = MagicMock()
        service._calendar_repo.get_for_date_range = AsyncMock(return_value=[])
        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[mock_assignment]
        )

        # Act
        result = await service.calculate_daily_loading(
            resource_id,
            date(2024, 1, 1),
            date(2024, 1, 1),
        )

        # Assert
        day = result[date(2024, 1, 1)]
        assert day.assigned_hours == Decimal("12.00")  # 1.5 * 8
        assert day.available_hours == Decimal("8.0")
        assert day.is_overallocated is True


class TestGetOverallocatedDates:
    """Tests for get_overallocated_dates method."""

    @pytest.mark.asyncio
    async def test_returns_only_overallocated_dates(self) -> None:
        """Should return list of dates where resource is overallocated."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        # Mock calculate_daily_loading to return mixed results
        resource_id = uuid4()

        with patch.object(
            service,
            "calculate_daily_loading",
            new_callable=AsyncMock,
        ) as mock_calc:
            mock_calc.return_value = {
                date(2024, 1, 1): ResourceLoadingDay(
                    date=date(2024, 1, 1),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("4.0"),  # Not overallocated
                ),
                date(2024, 1, 2): ResourceLoadingDay(
                    date=date(2024, 1, 2),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("10.0"),  # Overallocated
                ),
                date(2024, 1, 3): ResourceLoadingDay(
                    date=date(2024, 1, 3),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("8.0"),  # Exactly at capacity
                ),
            }

            # Act
            result = await service.get_overallocated_dates(
                resource_id,
                date(2024, 1, 1),
                date(2024, 1, 3),
            )

            # Assert
            assert len(result) == 1
            assert date(2024, 1, 2) in result


class TestAggregateProgramLoading:
    """Tests for aggregate_program_loading method."""

    @pytest.mark.asyncio
    async def test_returns_loading_for_all_program_resources(self) -> None:
        """Should return loading data for all resources in program."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        program_id = uuid4()
        resource1_id = uuid4()
        resource2_id = uuid4()

        mock_resource1 = MagicMock()
        mock_resource1.id = resource1_id
        mock_resource2 = MagicMock()
        mock_resource2.id = resource2_id

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_program = AsyncMock(
            return_value=([mock_resource1, mock_resource2], 2)
        )

        # Mock calculate_daily_loading
        with patch.object(
            service,
            "calculate_daily_loading",
            new_callable=AsyncMock,
        ) as mock_calc:
            mock_calc.return_value = {
                date(2024, 1, 1): ResourceLoadingDay(
                    date=date(2024, 1, 1),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("4.0"),
                )
            }

            # Act
            result = await service.aggregate_program_loading(
                program_id,
                date(2024, 1, 1),
                date(2024, 1, 1),
            )

            # Assert
            assert len(result) == 2
            assert resource1_id in result
            assert resource2_id in result
            assert mock_calc.call_count == 2


class TestGetProgramOverallocationSummary:
    """Tests for get_program_overallocation_summary method."""

    @pytest.mark.asyncio
    async def test_returns_only_resources_with_overallocations(self) -> None:
        """Should only include resources that have overallocated dates."""
        # Arrange
        mock_session = MagicMock()
        service = ResourceLoadingService(mock_session)

        program_id = uuid4()
        resource1_id = uuid4()  # Has overallocation
        resource2_id = uuid4()  # No overallocation

        # Mock aggregate_program_loading
        with patch.object(
            service,
            "aggregate_program_loading",
            new_callable=AsyncMock,
        ) as mock_agg:
            mock_agg.return_value = {
                resource1_id: {
                    date(2024, 1, 1): ResourceLoadingDay(
                        date=date(2024, 1, 1),
                        available_hours=Decimal("8.0"),
                        assigned_hours=Decimal("10.0"),  # Overallocated
                    ),
                },
                resource2_id: {
                    date(2024, 1, 1): ResourceLoadingDay(
                        date=date(2024, 1, 1),
                        available_hours=Decimal("8.0"),
                        assigned_hours=Decimal("4.0"),  # Not overallocated
                    ),
                },
            }

            # Act
            result = await service.get_program_overallocation_summary(
                program_id,
                date(2024, 1, 1),
                date(2024, 1, 1),
            )

            # Assert
            assert len(result) == 1
            assert resource1_id in result
            assert resource2_id not in result
            assert date(2024, 1, 1) in result[resource1_id]
