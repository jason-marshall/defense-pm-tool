"""Unit tests for OverallocationService.

Tests the over-allocation detection logic including:
- Single and multi-day over-allocation detection
- Period merging for consecutive days
- Affected activity identification
- Critical path impact detection
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.overallocation import (
    OverallocationPeriod,
    OverallocationService,
    ProgramOverallocationReport,
)
from src.services.resource import ResourceLoadingDay


class TestOverallocationPeriod:
    """Tests for OverallocationPeriod dataclass."""

    def test_duration_days_single_day(self) -> None:
        """Should return 1 for single day period."""
        period = OverallocationPeriod(
            resource_id=uuid4(),
            resource_code="ENG-001",
            resource_name="Engineer",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            peak_assigned=Decimal("10.0"),
            peak_available=Decimal("8.0"),
            peak_excess=Decimal("2.0"),
            affected_activities=[],
        )
        assert period.duration_days == 1

    def test_duration_days_multi_day(self) -> None:
        """Should return correct duration for multi-day period."""
        period = OverallocationPeriod(
            resource_id=uuid4(),
            resource_code="ENG-001",
            resource_name="Engineer",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 19),
            peak_assigned=Decimal("12.0"),
            peak_available=Decimal("8.0"),
            peak_excess=Decimal("4.0"),
            affected_activities=[],
        )
        assert period.duration_days == 5

    def test_severity_low(self) -> None:
        """Should classify as low severity when excess <= 2 hours."""
        period = OverallocationPeriod(
            resource_id=uuid4(),
            resource_code="ENG-001",
            resource_name="Engineer",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            peak_assigned=Decimal("10.0"),
            peak_available=Decimal("8.0"),
            peak_excess=Decimal("2.0"),
            affected_activities=[],
        )
        assert period.severity == "low"

    def test_severity_medium(self) -> None:
        """Should classify as medium severity when 2 < excess <= 4 hours."""
        period = OverallocationPeriod(
            resource_id=uuid4(),
            resource_code="ENG-001",
            resource_name="Engineer",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            peak_assigned=Decimal("11.0"),
            peak_available=Decimal("8.0"),
            peak_excess=Decimal("3.0"),
            affected_activities=[],
        )
        assert period.severity == "medium"

    def test_severity_high(self) -> None:
        """Should classify as high severity when excess > 4 hours."""
        period = OverallocationPeriod(
            resource_id=uuid4(),
            resource_code="ENG-001",
            resource_name="Engineer",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            peak_assigned=Decimal("14.0"),
            peak_available=Decimal("8.0"),
            peak_excess=Decimal("6.0"),
            affected_activities=[],
        )
        assert period.severity == "high"


class TestProgramOverallocationReport:
    """Tests for ProgramOverallocationReport dataclass."""

    def test_has_high_severity_true(self) -> None:
        """Should return True when any period has high severity."""
        periods = [
            OverallocationPeriod(
                resource_id=uuid4(),
                resource_code="ENG-001",
                resource_name="Engineer",
                start_date=date(2024, 1, 15),
                end_date=date(2024, 1, 15),
                peak_assigned=Decimal("14.0"),
                peak_available=Decimal("8.0"),
                peak_excess=Decimal("6.0"),  # High severity
                affected_activities=[],
            ),
        ]
        report = ProgramOverallocationReport(
            program_id=uuid4(),
            analysis_start=date(2024, 1, 1),
            analysis_end=date(2024, 1, 31),
            total_overallocations=1,
            resources_affected=1,
            periods=periods,
            critical_path_affected=False,
        )
        assert report.has_high_severity is True

    def test_has_high_severity_false(self) -> None:
        """Should return False when no period has high severity."""
        periods = [
            OverallocationPeriod(
                resource_id=uuid4(),
                resource_code="ENG-001",
                resource_name="Engineer",
                start_date=date(2024, 1, 15),
                end_date=date(2024, 1, 15),
                peak_assigned=Decimal("10.0"),
                peak_available=Decimal("8.0"),
                peak_excess=Decimal("2.0"),  # Low severity
                affected_activities=[],
            ),
        ]
        report = ProgramOverallocationReport(
            program_id=uuid4(),
            analysis_start=date(2024, 1, 1),
            analysis_end=date(2024, 1, 31),
            total_overallocations=1,
            resources_affected=1,
            periods=periods,
            critical_path_affected=False,
        )
        assert report.has_high_severity is False

    def test_total_affected_days(self) -> None:
        """Should sum duration of all periods."""
        periods = [
            OverallocationPeriod(
                resource_id=uuid4(),
                resource_code="ENG-001",
                resource_name="Engineer 1",
                start_date=date(2024, 1, 15),
                end_date=date(2024, 1, 17),  # 3 days
                peak_assigned=Decimal("10.0"),
                peak_available=Decimal("8.0"),
                peak_excess=Decimal("2.0"),
                affected_activities=[],
            ),
            OverallocationPeriod(
                resource_id=uuid4(),
                resource_code="ENG-002",
                resource_name="Engineer 2",
                start_date=date(2024, 1, 20),
                end_date=date(2024, 1, 21),  # 2 days
                peak_assigned=Decimal("12.0"),
                peak_available=Decimal("8.0"),
                peak_excess=Decimal("4.0"),
                affected_activities=[],
            ),
        ]
        report = ProgramOverallocationReport(
            program_id=uuid4(),
            analysis_start=date(2024, 1, 1),
            analysis_end=date(2024, 1, 31),
            total_overallocations=2,
            resources_affected=2,
            periods=periods,
            critical_path_affected=False,
        )
        assert report.total_affected_days == 5


class TestDetectResourceOverallocations:
    """Tests for detect_resource_overallocations method."""

    @pytest.mark.asyncio
    async def test_detect_single_day_overallocation(self) -> None:
        """Should detect single day over-allocation."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "ENG-001"
        mock_resource.name = "Test Engineer"

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)

        # Mock loading service to return over-allocation on Jan 15
        with patch.object(
            service._loading_service,
            "calculate_daily_loading",
            new_callable=AsyncMock,
        ) as mock_loading:
            mock_loading.return_value = {
                date(2024, 1, 15): ResourceLoadingDay(
                    date=date(2024, 1, 15),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("10.0"),  # Over-allocated
                ),
                date(2024, 1, 16): ResourceLoadingDay(
                    date=date(2024, 1, 16),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("6.0"),  # Not over-allocated
                ),
            }

            with patch.object(
                service,
                "get_affected_activities",
                new_callable=AsyncMock,
            ) as mock_affected:
                mock_affected.return_value = [uuid4()]

                result = await service.detect_resource_overallocations(
                    resource_id, date(2024, 1, 15), date(2024, 1, 16)
                )

        assert len(result) == 1
        assert result[0].start_date == date(2024, 1, 15)
        assert result[0].end_date == date(2024, 1, 15)
        assert result[0].peak_excess == Decimal("2.0")

    @pytest.mark.asyncio
    async def test_detect_multi_day_overallocation(self) -> None:
        """Should detect and merge consecutive over-allocated days."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "ENG-001"
        mock_resource.name = "Test Engineer"

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)

        # Mock loading service to return over-allocation on Jan 15-17
        with patch.object(
            service._loading_service,
            "calculate_daily_loading",
            new_callable=AsyncMock,
        ) as mock_loading:
            mock_loading.return_value = {
                date(2024, 1, 15): ResourceLoadingDay(
                    date=date(2024, 1, 15),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("10.0"),
                ),
                date(2024, 1, 16): ResourceLoadingDay(
                    date=date(2024, 1, 16),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("12.0"),  # Higher excess
                ),
                date(2024, 1, 17): ResourceLoadingDay(
                    date=date(2024, 1, 17),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("9.0"),
                ),
            }

            with patch.object(
                service,
                "get_affected_activities",
                new_callable=AsyncMock,
            ) as mock_affected:
                mock_affected.return_value = [uuid4()]

                result = await service.detect_resource_overallocations(
                    resource_id, date(2024, 1, 15), date(2024, 1, 17)
                )

        assert len(result) == 1
        assert result[0].start_date == date(2024, 1, 15)
        assert result[0].end_date == date(2024, 1, 17)
        assert result[0].peak_excess == Decimal("4.0")  # From Jan 16
        assert result[0].duration_days == 3

    @pytest.mark.asyncio
    async def test_no_overallocation_when_under_capacity(self) -> None:
        """Should return empty list when no over-allocation."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "ENG-001"
        mock_resource.name = "Test Engineer"

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)

        with patch.object(
            service._loading_service,
            "calculate_daily_loading",
            new_callable=AsyncMock,
        ) as mock_loading:
            mock_loading.return_value = {
                date(2024, 1, 15): ResourceLoadingDay(
                    date=date(2024, 1, 15),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("6.0"),  # Under capacity
                ),
                date(2024, 1, 16): ResourceLoadingDay(
                    date=date(2024, 1, 16),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("8.0"),  # Exactly at capacity
                ),
            }

            result = await service.detect_resource_overallocations(
                resource_id, date(2024, 1, 15), date(2024, 1, 16)
            )

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_nonexistent_resource_returns_empty(self) -> None:
        """Should return empty list for nonexistent resource."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=None)

        result = await service.detect_resource_overallocations(
            uuid4(), date(2024, 1, 15), date(2024, 1, 16)
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_detect_separate_periods(self) -> None:
        """Should detect multiple separate over-allocation periods."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "ENG-001"
        mock_resource.name = "Test Engineer"

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_id = AsyncMock(return_value=mock_resource)

        # Over-allocation on Jan 15 and Jan 18 (not consecutive)
        with patch.object(
            service._loading_service,
            "calculate_daily_loading",
            new_callable=AsyncMock,
        ) as mock_loading:
            mock_loading.return_value = {
                date(2024, 1, 15): ResourceLoadingDay(
                    date=date(2024, 1, 15),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("10.0"),  # Over-allocated
                ),
                date(2024, 1, 16): ResourceLoadingDay(
                    date=date(2024, 1, 16),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("6.0"),  # Not over-allocated
                ),
                date(2024, 1, 17): ResourceLoadingDay(
                    date=date(2024, 1, 17),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("7.0"),  # Not over-allocated
                ),
                date(2024, 1, 18): ResourceLoadingDay(
                    date=date(2024, 1, 18),
                    available_hours=Decimal("8.0"),
                    assigned_hours=Decimal("12.0"),  # Over-allocated
                ),
            }

            with patch.object(
                service,
                "get_affected_activities",
                new_callable=AsyncMock,
            ) as mock_affected:
                mock_affected.return_value = [uuid4()]

                result = await service.detect_resource_overallocations(
                    resource_id, date(2024, 1, 15), date(2024, 1, 18)
                )

        assert len(result) == 2
        assert result[0].start_date == date(2024, 1, 15)
        assert result[0].end_date == date(2024, 1, 15)
        assert result[1].start_date == date(2024, 1, 18)
        assert result[1].end_date == date(2024, 1, 18)


class TestAffectedActivitiesIdentification:
    """Tests for get_affected_activities method."""

    @pytest.mark.asyncio
    async def test_affected_activities_identification(self) -> None:
        """Should identify activities contributing to over-allocation."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        resource_id = uuid4()
        activity1_id = uuid4()
        activity2_id = uuid4()

        # Mock assignments
        mock_assignment1 = MagicMock()
        mock_assignment1.activity_id = activity1_id
        mock_assignment1.start_date = date(2024, 1, 10)
        mock_assignment1.finish_date = date(2024, 1, 20)
        mock_assignment1.activity = None

        mock_assignment2 = MagicMock()
        mock_assignment2.activity_id = activity2_id
        mock_assignment2.start_date = date(2024, 1, 15)
        mock_assignment2.finish_date = date(2024, 1, 25)
        mock_assignment2.activity = None

        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[mock_assignment1, mock_assignment2]
        )

        # Mock the loading service's get_assignment_date_range
        def mock_date_range(assignment):
            return assignment.start_date, assignment.finish_date

        service._loading_service.get_assignment_date_range = mock_date_range

        result = await service.get_affected_activities(
            resource_id, date(2024, 1, 15), date(2024, 1, 18)
        )

        # Both activities should be affected (both have assignments in the range)
        assert len(result) == 2
        assert activity1_id in result
        assert activity2_id in result

    @pytest.mark.asyncio
    async def test_affected_activities_filters_by_date(self) -> None:
        """Should only include activities active on the specified date."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        resource_id = uuid4()
        activity1_id = uuid4()
        activity2_id = uuid4()

        # Assignment 1 ends before the check date
        mock_assignment1 = MagicMock()
        mock_assignment1.activity_id = activity1_id
        mock_assignment1.start_date = date(2024, 1, 1)
        mock_assignment1.finish_date = date(2024, 1, 10)
        mock_assignment1.activity = None

        # Assignment 2 is active on the check date
        mock_assignment2 = MagicMock()
        mock_assignment2.activity_id = activity2_id
        mock_assignment2.start_date = date(2024, 1, 15)
        mock_assignment2.finish_date = date(2024, 1, 25)
        mock_assignment2.activity = None

        service._assignment_repo = MagicMock()
        service._assignment_repo.get_assignments_with_activities = AsyncMock(
            return_value=[mock_assignment1, mock_assignment2]
        )

        def mock_date_range(assignment):
            return assignment.start_date, assignment.finish_date

        service._loading_service.get_assignment_date_range = mock_date_range

        result = await service.get_affected_activities(resource_id, date(2024, 1, 15))

        # Only activity2 should be affected
        assert len(result) == 1
        assert activity2_id in result


class TestCriticalPathImpactDetection:
    """Tests for check_critical_path_impact method."""

    @pytest.mark.asyncio
    async def test_critical_path_impact_detection(self) -> None:
        """Should detect when critical path activities are affected."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        activity_id = uuid4()
        periods = [
            OverallocationPeriod(
                resource_id=uuid4(),
                resource_code="ENG-001",
                resource_name="Engineer",
                start_date=date(2024, 1, 15),
                end_date=date(2024, 1, 17),
                peak_assigned=Decimal("10.0"),
                peak_available=Decimal("8.0"),
                peak_excess=Decimal("2.0"),
                affected_activities=[activity_id],
            ),
        ]

        # Mock critical activity
        mock_activity = MagicMock()
        mock_activity.is_critical = True

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_id = AsyncMock(return_value=mock_activity)

        result = await service.check_critical_path_impact(uuid4(), periods)

        assert result is True

    @pytest.mark.asyncio
    async def test_no_critical_path_impact(self) -> None:
        """Should return False when no critical activities affected."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        activity_id = uuid4()
        periods = [
            OverallocationPeriod(
                resource_id=uuid4(),
                resource_code="ENG-001",
                resource_name="Engineer",
                start_date=date(2024, 1, 15),
                end_date=date(2024, 1, 17),
                peak_assigned=Decimal("10.0"),
                peak_available=Decimal("8.0"),
                peak_excess=Decimal("2.0"),
                affected_activities=[activity_id],
            ),
        ]

        # Mock non-critical activity
        mock_activity = MagicMock()
        mock_activity.is_critical = False

        service._activity_repo = MagicMock()
        service._activity_repo.get_by_id = AsyncMock(return_value=mock_activity)

        result = await service.check_critical_path_impact(uuid4(), periods)

        assert result is False

    @pytest.mark.asyncio
    async def test_empty_periods_returns_false(self) -> None:
        """Should return False when no over-allocation periods."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        result = await service.check_critical_path_impact(uuid4(), [])

        assert result is False


class TestMergeAdjacentPeriods:
    """Tests for _merge_adjacent_periods method."""

    def test_merge_adjacent_periods(self) -> None:
        """Should merge consecutive periods for same resource."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        resource_id = uuid4()
        activity_id = uuid4()

        periods = [
            OverallocationPeriod(
                resource_id=resource_id,
                resource_code="ENG-001",
                resource_name="Engineer",
                start_date=date(2024, 1, 15),
                end_date=date(2024, 1, 16),
                peak_assigned=Decimal("10.0"),
                peak_available=Decimal("8.0"),
                peak_excess=Decimal("2.0"),
                affected_activities=[activity_id],
            ),
            OverallocationPeriod(
                resource_id=resource_id,
                resource_code="ENG-001",
                resource_name="Engineer",
                start_date=date(2024, 1, 17),
                end_date=date(2024, 1, 18),
                peak_assigned=Decimal("12.0"),
                peak_available=Decimal("8.0"),
                peak_excess=Decimal("4.0"),
                affected_activities=[activity_id],
            ),
        ]

        result = service._merge_adjacent_periods(periods)

        assert len(result) == 1
        assert result[0].start_date == date(2024, 1, 15)
        assert result[0].end_date == date(2024, 1, 18)
        assert result[0].peak_excess == Decimal("4.0")

    def test_no_merge_for_different_resources(self) -> None:
        """Should not merge periods for different resources."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        resource1_id = uuid4()
        resource2_id = uuid4()

        periods = [
            OverallocationPeriod(
                resource_id=resource1_id,
                resource_code="ENG-001",
                resource_name="Engineer 1",
                start_date=date(2024, 1, 15),
                end_date=date(2024, 1, 16),
                peak_assigned=Decimal("10.0"),
                peak_available=Decimal("8.0"),
                peak_excess=Decimal("2.0"),
                affected_activities=[],
            ),
            OverallocationPeriod(
                resource_id=resource2_id,
                resource_code="ENG-002",
                resource_name="Engineer 2",
                start_date=date(2024, 1, 17),
                end_date=date(2024, 1, 18),
                peak_assigned=Decimal("12.0"),
                peak_available=Decimal("8.0"),
                peak_excess=Decimal("4.0"),
                affected_activities=[],
            ),
        ]

        result = service._merge_adjacent_periods(periods)

        assert len(result) == 2

    def test_no_merge_for_non_adjacent_periods(self) -> None:
        """Should not merge non-adjacent periods."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        resource_id = uuid4()

        periods = [
            OverallocationPeriod(
                resource_id=resource_id,
                resource_code="ENG-001",
                resource_name="Engineer",
                start_date=date(2024, 1, 15),
                end_date=date(2024, 1, 16),
                peak_assigned=Decimal("10.0"),
                peak_available=Decimal("8.0"),
                peak_excess=Decimal("2.0"),
                affected_activities=[],
            ),
            OverallocationPeriod(
                resource_id=resource_id,
                resource_code="ENG-001",
                resource_name="Engineer",
                start_date=date(2024, 1, 20),  # Gap of 3 days
                end_date=date(2024, 1, 21),
                peak_assigned=Decimal("12.0"),
                peak_available=Decimal("8.0"),
                peak_excess=Decimal("4.0"),
                affected_activities=[],
            ),
        ]

        result = service._merge_adjacent_periods(periods)

        assert len(result) == 2

    def test_empty_periods_returns_empty(self) -> None:
        """Should return empty list for empty input."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        result = service._merge_adjacent_periods([])

        assert result == []


class TestCalculatePeakExcess:
    """Tests for _calculate_peak_excess method."""

    def test_calculate_peak_excess(self) -> None:
        """Should find date with maximum over-allocation."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        loading = {
            date(2024, 1, 15): ResourceLoadingDay(
                date=date(2024, 1, 15),
                available_hours=Decimal("8.0"),
                assigned_hours=Decimal("10.0"),  # 2 hours excess
            ),
            date(2024, 1, 16): ResourceLoadingDay(
                date=date(2024, 1, 16),
                available_hours=Decimal("8.0"),
                assigned_hours=Decimal("12.0"),  # 4 hours excess (peak)
            ),
            date(2024, 1, 17): ResourceLoadingDay(
                date=date(2024, 1, 17),
                available_hours=Decimal("8.0"),
                assigned_hours=Decimal("9.0"),  # 1 hour excess
            ),
        }

        peak_date, peak_excess = service._calculate_peak_excess(loading)

        assert peak_date == date(2024, 1, 16)
        assert peak_excess == Decimal("4.0")

    def test_no_overallocation_returns_none(self) -> None:
        """Should return (None, 0) when no over-allocation."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        loading = {
            date(2024, 1, 15): ResourceLoadingDay(
                date=date(2024, 1, 15),
                available_hours=Decimal("8.0"),
                assigned_hours=Decimal("6.0"),
            ),
            date(2024, 1, 16): ResourceLoadingDay(
                date=date(2024, 1, 16),
                available_hours=Decimal("8.0"),
                assigned_hours=Decimal("8.0"),
            ),
        }

        peak_date, peak_excess = service._calculate_peak_excess(loading)

        assert peak_date is None
        assert peak_excess == Decimal("0")


class TestDetectProgramOverallocations:
    """Tests for detect_program_overallocations method."""

    @pytest.mark.asyncio
    async def test_detect_program_overallocations(self) -> None:
        """Should analyze all resources in program."""
        mock_session = MagicMock()
        service = OverallocationService(mock_session)

        program_id = uuid4()
        resource1_id = uuid4()
        resource2_id = uuid4()

        # Mock program
        mock_program = MagicMock()
        mock_program.start_date = date(2024, 1, 1)
        mock_program.end_date = date(2024, 12, 31)

        # Mock resources
        mock_resource1 = MagicMock()
        mock_resource1.id = resource1_id
        mock_resource2 = MagicMock()
        mock_resource2.id = resource2_id

        service._resource_repo = MagicMock()
        service._resource_repo.get_by_program = AsyncMock(
            return_value=([mock_resource1, mock_resource2], 2)
        )

        # Mock period for resource1 only
        mock_period = OverallocationPeriod(
            resource_id=resource1_id,
            resource_code="ENG-001",
            resource_name="Engineer",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 17),
            peak_assigned=Decimal("10.0"),
            peak_available=Decimal("8.0"),
            peak_excess=Decimal("2.0"),
            affected_activities=[],
        )

        with patch.object(
            service,
            "detect_resource_overallocations",
            new_callable=AsyncMock,
        ) as mock_detect:
            # Return period for resource1, empty for resource2
            mock_detect.side_effect = [
                [mock_period],  # resource1
                [],  # resource2
            ]

            with patch.object(
                service,
                "check_critical_path_impact",
                new_callable=AsyncMock,
            ) as mock_critical:
                mock_critical.return_value = False

                with patch("src.services.overallocation.ProgramRepository") as mock_prog_repo_class:
                    mock_prog_repo = MagicMock()
                    mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
                    mock_prog_repo_class.return_value = mock_prog_repo

                    result = await service.detect_program_overallocations(
                        program_id, date(2024, 1, 1), date(2024, 1, 31)
                    )

        assert result.total_overallocations == 1
        assert result.resources_affected == 1
        assert len(result.periods) == 1
        assert result.critical_path_affected is False
