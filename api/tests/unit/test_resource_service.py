"""Unit tests for ResourceService."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.resource import (
    ResourceLoadingDay,
    ResourceService,
    ResourceSummaryStats,
)

# =============================================================================
# ResourceLoadingDay Tests
# =============================================================================


class TestResourceLoadingDay:
    """Tests for ResourceLoadingDay dataclass."""

    def test_loading_day_normal_utilization(self) -> None:
        """Test loading day with normal utilization."""
        day = ResourceLoadingDay(
            date=date(2024, 1, 15),
            available_hours=Decimal("8.0"),
            assigned_hours=Decimal("4.0"),
        )

        assert day.utilization == Decimal("50.00")
        assert day.is_overallocated is False

    def test_loading_day_full_utilization(self) -> None:
        """Test loading day at 100% utilization."""
        day = ResourceLoadingDay(
            date=date(2024, 1, 15),
            available_hours=Decimal("8.0"),
            assigned_hours=Decimal("8.0"),
        )

        assert day.utilization == Decimal("100.00")
        assert day.is_overallocated is False

    def test_loading_day_overallocated(self) -> None:
        """Test loading day with overallocation."""
        day = ResourceLoadingDay(
            date=date(2024, 1, 15),
            available_hours=Decimal("8.0"),
            assigned_hours=Decimal("12.0"),
        )

        assert day.utilization == Decimal("150.00")
        assert day.is_overallocated is True

    def test_loading_day_zero_available(self) -> None:
        """Test loading day with zero available hours."""
        day = ResourceLoadingDay(
            date=date(2024, 1, 15),
            available_hours=Decimal("0"),
            assigned_hours=Decimal("0"),
        )

        assert day.utilization == Decimal("0")
        assert day.is_overallocated is False

    def test_loading_day_zero_available_with_assignment(self) -> None:
        """Test loading day with zero available but assigned hours."""
        day = ResourceLoadingDay(
            date=date(2024, 1, 15),
            available_hours=Decimal("0"),
            assigned_hours=Decimal("4.0"),
        )

        assert day.utilization == Decimal("100")
        assert day.is_overallocated is True

    def test_loading_day_partial_hours(self) -> None:
        """Test loading day with fractional hours."""
        day = ResourceLoadingDay(
            date=date(2024, 1, 15),
            available_hours=Decimal("8.0"),
            assigned_hours=Decimal("2.5"),
        )

        assert day.utilization == Decimal("31.25")
        assert day.is_overallocated is False


# =============================================================================
# ResourceSummaryStats Tests
# =============================================================================


class TestResourceSummaryStats:
    """Tests for ResourceSummaryStats dataclass."""

    def test_summary_stats_creation(self) -> None:
        """Test creating summary stats."""
        stats = ResourceSummaryStats(
            total_resources=10,
            labor_count=5,
            equipment_count=3,
            material_count=2,
            active_count=8,
            inactive_count=2,
        )

        assert stats.total_resources == 10
        assert stats.labor_count == 5
        assert stats.equipment_count == 3
        assert stats.material_count == 2
        assert stats.active_count == 8
        assert stats.inactive_count == 2

    def test_summary_stats_model_dump(self) -> None:
        """Test model_dump for caching."""
        stats = ResourceSummaryStats(
            total_resources=10,
            labor_count=5,
            equipment_count=3,
            material_count=2,
            active_count=8,
            inactive_count=2,
        )

        dumped = stats.model_dump()

        assert dumped == {
            "total_resources": 10,
            "labor_count": 5,
            "equipment_count": 3,
            "material_count": 2,
            "active_count": 8,
            "inactive_count": 2,
        }

    def test_summary_stats_from_dict(self) -> None:
        """Test creating from dictionary (cache retrieval)."""
        data = {
            "total_resources": 15,
            "labor_count": 7,
            "equipment_count": 5,
            "material_count": 3,
            "active_count": 12,
            "inactive_count": 3,
        }

        stats = ResourceSummaryStats.from_dict(data)

        assert stats.total_resources == 15
        assert stats.labor_count == 7
        assert stats.equipment_count == 5
        assert stats.material_count == 3
        assert stats.active_count == 12
        assert stats.inactive_count == 3


# =============================================================================
# ResourceService Assignment Active Tests
# =============================================================================


class TestResourceServiceAssignmentActive:
    """Tests for _assignment_active_on_date method."""

    @pytest.fixture
    def service(self) -> ResourceService:
        """Create service with mock session."""
        mock_session = MagicMock()
        return ResourceService(mock_session)

    def test_assignment_no_dates_always_active(self, service: ResourceService) -> None:
        """Test assignment with no start/finish dates is always active."""
        assignment = MagicMock()
        assignment.start_date = None
        assignment.finish_date = None

        # Active on any date
        assert service._assignment_active_on_date(assignment, date(2024, 1, 1)) is True
        assert service._assignment_active_on_date(assignment, date(2024, 6, 15)) is True
        assert service._assignment_active_on_date(assignment, date(2024, 12, 31)) is True

    def test_assignment_with_start_date_only(self, service: ResourceService) -> None:
        """Test assignment with only start date."""
        assignment = MagicMock()
        assignment.start_date = date(2024, 3, 1)
        assignment.finish_date = None

        # Not active before start
        assert service._assignment_active_on_date(assignment, date(2024, 2, 28)) is False

        # Active on and after start
        assert service._assignment_active_on_date(assignment, date(2024, 3, 1)) is True
        assert service._assignment_active_on_date(assignment, date(2024, 12, 31)) is True

    def test_assignment_with_finish_date_only(self, service: ResourceService) -> None:
        """Test assignment with only finish date."""
        assignment = MagicMock()
        assignment.start_date = None
        assignment.finish_date = date(2024, 6, 30)

        # Active before and on finish
        assert service._assignment_active_on_date(assignment, date(2024, 1, 1)) is True
        assert service._assignment_active_on_date(assignment, date(2024, 6, 30)) is True

        # Not active after finish
        assert service._assignment_active_on_date(assignment, date(2024, 7, 1)) is False

    def test_assignment_with_date_range(self, service: ResourceService) -> None:
        """Test assignment with both start and finish dates."""
        assignment = MagicMock()
        assignment.start_date = date(2024, 3, 1)
        assignment.finish_date = date(2024, 6, 30)

        # Not active before start
        assert service._assignment_active_on_date(assignment, date(2024, 2, 28)) is False

        # Active within range
        assert service._assignment_active_on_date(assignment, date(2024, 3, 1)) is True
        assert service._assignment_active_on_date(assignment, date(2024, 4, 15)) is True
        assert service._assignment_active_on_date(assignment, date(2024, 6, 30)) is True

        # Not active after finish
        assert service._assignment_active_on_date(assignment, date(2024, 7, 1)) is False

    def test_assignment_single_day(self, service: ResourceService) -> None:
        """Test assignment active for single day."""
        assignment = MagicMock()
        assignment.start_date = date(2024, 5, 15)
        assignment.finish_date = date(2024, 5, 15)

        # Only active on that exact day
        assert service._assignment_active_on_date(assignment, date(2024, 5, 14)) is False
        assert service._assignment_active_on_date(assignment, date(2024, 5, 15)) is True
        assert service._assignment_active_on_date(assignment, date(2024, 5, 16)) is False


# =============================================================================
# ResourceService Loading Calculation Tests
# =============================================================================


class TestResourceServiceLoading:
    """Tests for resource loading calculations."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_session: MagicMock) -> ResourceService:
        """Create service with mocked repositories."""
        return ResourceService(mock_session)

    @pytest.mark.asyncio
    async def test_get_resource_loading_no_resource(self, service: ResourceService) -> None:
        """Test loading calculation when resource doesn't exist."""
        resource_id = uuid4()

        with patch.object(service._resource_repo, "get_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            loading = await service.get_resource_loading(
                resource_id, date(2024, 1, 1), date(2024, 1, 5)
            )

            assert loading == {}

    @pytest.mark.asyncio
    async def test_get_resource_loading_with_calendar(self, service: ResourceService) -> None:
        """Test loading with calendar entries."""
        resource_id = uuid4()

        # Mock resource
        mock_resource = MagicMock()
        mock_resource.capacity_per_day = Decimal("8.0")

        # Mock calendar entry
        mock_calendar = MagicMock()
        mock_calendar.calendar_date = date(2024, 1, 15)
        mock_calendar.available_hours = Decimal("6.0")
        mock_calendar.is_working_day = True

        with (
            patch.object(
                service._resource_repo, "get_by_id", new_callable=AsyncMock
            ) as mock_get_resource,
            patch.object(
                service._calendar_repo, "get_for_date_range", new_callable=AsyncMock
            ) as mock_get_calendar,
            patch.object(
                service._assignment_repo, "get_by_resource", new_callable=AsyncMock
            ) as mock_get_assignments,
        ):
            mock_get_resource.return_value = mock_resource
            mock_get_calendar.return_value = [mock_calendar]
            mock_get_assignments.return_value = []

            loading = await service.get_resource_loading(
                resource_id, date(2024, 1, 15), date(2024, 1, 15)
            )

            assert len(loading) == 1
            assert loading[date(2024, 1, 15)].available_hours == Decimal("6.0")
            assert loading[date(2024, 1, 15)].assigned_hours == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_overallocated_dates(self, service: ResourceService) -> None:
        """Test finding overallocated dates."""
        resource_id = uuid4()

        # Create loading with one overallocated day
        loading = {
            date(2024, 1, 15): ResourceLoadingDay(
                date=date(2024, 1, 15),
                available_hours=Decimal("8.0"),
                assigned_hours=Decimal("4.0"),
            ),
            date(2024, 1, 16): ResourceLoadingDay(
                date=date(2024, 1, 16),
                available_hours=Decimal("8.0"),
                assigned_hours=Decimal("12.0"),  # Overallocated
            ),
            date(2024, 1, 17): ResourceLoadingDay(
                date=date(2024, 1, 17),
                available_hours=Decimal("8.0"),
                assigned_hours=Decimal("8.0"),
            ),
        }

        with patch.object(service, "get_resource_loading", new_callable=AsyncMock) as mock_loading:
            mock_loading.return_value = loading

            overallocated = await service.get_overallocated_dates(
                resource_id, date(2024, 1, 15), date(2024, 1, 17)
            )

            assert len(overallocated) == 1
            assert date(2024, 1, 16) in overallocated


# =============================================================================
# ResourceService Summary Tests
# =============================================================================


class TestResourceServiceSummary:
    """Tests for program resource summary."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock session."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_get_program_resource_summary_no_cache(self, mock_session: MagicMock) -> None:
        """Test summary calculation without cache."""
        service = ResourceService(mock_session, cache=None)
        program_id = uuid4()

        with patch.object(
            service._resource_repo, "count_by_program", new_callable=AsyncMock
        ) as mock_count:
            # Set up return values for each call
            mock_count.side_effect = [10, 5, 3, 2, 8, 2]

            summary = await service.get_program_resource_summary(program_id)

            assert summary.total_resources == 10
            assert summary.labor_count == 5
            assert summary.equipment_count == 3
            assert summary.material_count == 2
            assert summary.active_count == 8
            assert summary.inactive_count == 2

    @pytest.mark.asyncio
    async def test_get_program_resource_summary_with_cache_hit(
        self, mock_session: MagicMock
    ) -> None:
        """Test summary retrieval from cache."""
        mock_cache = MagicMock()
        mock_cache.is_available = True
        mock_cache.get = AsyncMock(
            return_value={
                "total_resources": 15,
                "labor_count": 7,
                "equipment_count": 5,
                "material_count": 3,
                "active_count": 12,
                "inactive_count": 3,
            }
        )

        service = ResourceService(mock_session, cache=mock_cache)
        program_id = uuid4()

        summary = await service.get_program_resource_summary(program_id)

        assert summary.total_resources == 15
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_program_resource_summary_cache_miss(self, mock_session: MagicMock) -> None:
        """Test summary calculation on cache miss."""
        mock_cache = MagicMock()
        mock_cache.is_available = True
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        service = ResourceService(mock_session, cache=mock_cache)
        program_id = uuid4()

        with patch.object(
            service._resource_repo, "count_by_program", new_callable=AsyncMock
        ) as mock_count:
            mock_count.side_effect = [10, 5, 3, 2, 8, 2]

            summary = await service.get_program_resource_summary(program_id)

            assert summary.total_resources == 10
            mock_cache.set.assert_called_once()


# =============================================================================
# ResourceService Calendar Generation Tests
# =============================================================================


class TestResourceServiceCalendarGeneration:
    """Tests for default calendar generation."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_session: MagicMock) -> ResourceService:
        """Create service."""
        return ResourceService(mock_session)

    @pytest.mark.asyncio
    async def test_generate_default_calendar_weekdays_only(self, service: ResourceService) -> None:
        """Test generating calendar excluding weekends."""
        resource_id = uuid4()

        # Monday to Friday (Jan 15-19, 2024)
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 19)

        mock_entries = [MagicMock() for _ in range(5)]

        with (
            patch.object(
                service._calendar_repo, "delete_range", new_callable=AsyncMock
            ) as mock_delete,
            patch.object(
                service._calendar_repo, "bulk_create_entries", new_callable=AsyncMock
            ) as mock_create,
        ):
            mock_create.return_value = mock_entries

            entries = await service.generate_default_calendar(
                resource_id, start_date, end_date, include_weekends=False
            )

            assert len(entries) == 5
            mock_delete.assert_called_once_with(resource_id, start_date, end_date)

            # Verify entries data
            create_call_args = mock_create.call_args[0][0]
            assert len(create_call_args) == 5
            # All should be working days with 8 hours
            for entry_data in create_call_args:
                assert entry_data["available_hours"] == Decimal("8.0")
                assert entry_data["is_working_day"] is True

    @pytest.mark.asyncio
    async def test_generate_default_calendar_with_weekends(self, service: ResourceService) -> None:
        """Test generating calendar including weekends."""
        resource_id = uuid4()

        # Full week including weekend (Jan 15-21, 2024)
        start_date = date(2024, 1, 15)  # Monday
        end_date = date(2024, 1, 21)  # Sunday

        mock_entries = [MagicMock() for _ in range(7)]

        with (
            patch.object(service._calendar_repo, "delete_range", new_callable=AsyncMock),
            patch.object(
                service._calendar_repo, "bulk_create_entries", new_callable=AsyncMock
            ) as mock_create,
        ):
            mock_create.return_value = mock_entries

            entries = await service.generate_default_calendar(
                resource_id, start_date, end_date, include_weekends=True
            )

            assert len(entries) == 7

            # Verify all 7 days are working days
            create_call_args = mock_create.call_args[0][0]
            assert len(create_call_args) == 7
            for entry_data in create_call_args:
                assert entry_data["is_working_day"] is True

    @pytest.mark.asyncio
    async def test_generate_default_calendar_custom_hours(self, service: ResourceService) -> None:
        """Test generating calendar with custom hours."""
        resource_id = uuid4()

        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        mock_entries = [MagicMock()]

        with (
            patch.object(service._calendar_repo, "delete_range", new_callable=AsyncMock),
            patch.object(
                service._calendar_repo, "bulk_create_entries", new_callable=AsyncMock
            ) as mock_create,
        ):
            mock_create.return_value = mock_entries

            await service.generate_default_calendar(
                resource_id,
                start_date,
                end_date,
                hours_per_day=Decimal("10.0"),
            )

            create_call_args = mock_create.call_args[0][0]
            assert create_call_args[0]["available_hours"] == Decimal("10.0")

    @pytest.mark.asyncio
    async def test_generate_default_calendar_marks_weekends_non_working(
        self, service: ResourceService
    ) -> None:
        """Test calendar marks weekends as non-working when include_weekends=False."""
        resource_id = uuid4()

        # Full week including weekend (Jan 15-21, 2024) - Mon to Sun
        start_date = date(2024, 1, 15)  # Monday
        end_date = date(2024, 1, 21)  # Sunday

        # All 7 entries expected, but weekends marked non-working
        mock_entries = [MagicMock() for _ in range(7)]

        with (
            patch.object(service._calendar_repo, "delete_range", new_callable=AsyncMock),
            patch.object(
                service._calendar_repo, "bulk_create_entries", new_callable=AsyncMock
            ) as mock_create,
        ):
            mock_create.return_value = mock_entries

            entries = await service.generate_default_calendar(
                resource_id, start_date, end_date, include_weekends=False
            )

            # Should get all 7 entries
            assert len(entries) == 7

            # Verify entries - weekdays are working, weekends are not
            create_call_args = mock_create.call_args[0][0]
            assert len(create_call_args) == 7

            for entry_data in create_call_args:
                day_of_week = entry_data["calendar_date"].weekday()
                if day_of_week < 5:  # Weekday
                    assert entry_data["is_working_day"] is True
                    assert entry_data["available_hours"] == Decimal("8.0")
                else:  # Weekend
                    assert entry_data["is_working_day"] is False
                    assert entry_data["available_hours"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_generate_default_calendar_weekend_only_range(
        self, service: ResourceService
    ) -> None:
        """Test calendar when date range is weekend only."""
        resource_id = uuid4()

        # Saturday and Sunday only (Jan 20-21, 2024)
        start_date = date(2024, 1, 20)  # Saturday
        end_date = date(2024, 1, 21)  # Sunday

        mock_entries = [MagicMock() for _ in range(2)]

        with (
            patch.object(service._calendar_repo, "delete_range", new_callable=AsyncMock),
            patch.object(
                service._calendar_repo, "bulk_create_entries", new_callable=AsyncMock
            ) as mock_create,
        ):
            mock_create.return_value = mock_entries

            entries = await service.generate_default_calendar(
                resource_id, start_date, end_date, include_weekends=False
            )

            # Both days should be created as non-working
            create_call_args = mock_create.call_args[0][0]
            assert len(create_call_args) == 2
            for entry_data in create_call_args:
                assert entry_data["is_working_day"] is False
                assert entry_data["available_hours"] == Decimal("0")
