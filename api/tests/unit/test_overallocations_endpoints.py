"""Unit tests for over-allocation API endpoints."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.overallocations import (
    _period_to_response,
    get_affected_activities,
    get_program_overallocations,
    get_resource_overallocations,
)
from src.services.overallocation import OverallocationPeriod


class TestPeriodToResponse:
    """Tests for _period_to_response helper function."""

    def test_converts_period_to_response(self):
        """Should convert OverallocationPeriod to response schema."""
        resource_id = uuid4()
        period = OverallocationPeriod(
            resource_id=resource_id,
            resource_code="RES-001",
            resource_name="Test Resource",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5),
            peak_assigned=Decimal("12.0"),
            peak_available=Decimal("8.0"),
            peak_excess=Decimal("4.0"),
            affected_activities=[uuid4(), uuid4()],
        )

        response = _period_to_response(period)

        assert response.resource_id == resource_id
        assert response.resource_code == "RES-001"
        assert response.duration_days == 5  # Calculated from dates
        assert response.peak_excess == Decimal("4.0")


class TestGetResourceOverallocations:
    """Tests for get_resource_overallocations endpoint."""

    @pytest.mark.asyncio
    async def test_get_resource_overallocations_success(self):
        """Should return list of overallocation periods."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        resource_id = uuid4()

        mock_period = OverallocationPeriod(
            resource_id=resource_id,
            resource_code="RES-001",
            resource_name="Test Resource",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5),
            peak_assigned=Decimal("12.0"),
            peak_available=Decimal("8.0"),
            peak_excess=Decimal("4.0"),
            affected_activities=[],
        )

        with patch("src.api.v1.endpoints.overallocations.OverallocationService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.detect_resource_overallocations = AsyncMock(return_value=[mock_period])
            mock_service_class.return_value = mock_service

            result = await get_resource_overallocations(
                resource_id=resource_id,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                db=mock_db,
                current_user=mock_user,
            )

            assert len(result) == 1
            assert result[0].resource_id == resource_id

    @pytest.mark.asyncio
    async def test_get_resource_overallocations_empty(self):
        """Should return empty list when no overallocations."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        resource_id = uuid4()

        with patch("src.api.v1.endpoints.overallocations.OverallocationService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.detect_resource_overallocations = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            result = await get_resource_overallocations(
                resource_id=resource_id,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                db=mock_db,
                current_user=mock_user,
            )

            assert len(result) == 0


class TestGetProgramOverallocations:
    """Tests for get_program_overallocations endpoint."""

    @pytest.mark.asyncio
    async def test_get_program_overallocations_success(self):
        """Should return program overallocation report."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        program_id = uuid4()

        mock_period = OverallocationPeriod(
            resource_id=uuid4(),
            resource_code="RES-001",
            resource_name="Test Resource",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5),
            peak_assigned=Decimal("12.0"),
            peak_available=Decimal("8.0"),
            peak_excess=Decimal("4.0"),
            affected_activities=[],
        )

        mock_report = MagicMock()
        mock_report.program_id = program_id
        mock_report.analysis_start = date(2026, 1, 1)
        mock_report.analysis_end = date(2026, 1, 31)
        mock_report.total_overallocations = 1
        mock_report.resources_affected = 1
        mock_report.total_affected_days = 5
        mock_report.has_high_severity = True
        mock_report.critical_path_affected = False
        mock_report.periods = [mock_period]

        with patch("src.api.v1.endpoints.overallocations.OverallocationService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.detect_program_overallocations = AsyncMock(return_value=mock_report)
            mock_service_class.return_value = mock_service

            result = await get_program_overallocations(
                program_id=program_id,
                db=mock_db,
                current_user=mock_user,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
            )

            assert result.program_id == program_id
            assert result.total_overallocations == 1
            assert result.has_high_severity is True
            assert len(result.periods) == 1

    @pytest.mark.asyncio
    async def test_get_program_overallocations_default_dates(self):
        """Should handle default date parameters."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        program_id = uuid4()

        mock_report = MagicMock()
        mock_report.program_id = program_id
        mock_report.analysis_start = date(2026, 1, 1)
        mock_report.analysis_end = date(2026, 12, 31)
        mock_report.total_overallocations = 0
        mock_report.resources_affected = 0
        mock_report.total_affected_days = 0
        mock_report.has_high_severity = False
        mock_report.critical_path_affected = False
        mock_report.periods = []

        with patch("src.api.v1.endpoints.overallocations.OverallocationService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.detect_program_overallocations = AsyncMock(return_value=mock_report)
            mock_service_class.return_value = mock_service

            result = await get_program_overallocations(
                program_id=program_id,
                db=mock_db,
                current_user=mock_user,
                start_date=None,  # Default
                end_date=None,  # Default
            )

            assert result.program_id == program_id
            mock_service.detect_program_overallocations.assert_called_once_with(
                program_id, None, None
            )


class TestGetAffectedActivities:
    """Tests for get_affected_activities endpoint."""

    @pytest.mark.asyncio
    async def test_get_affected_activities_success(self):
        """Should return list of affected activity IDs."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        resource_id = uuid4()
        activity1_id = uuid4()
        activity2_id = uuid4()

        with patch("src.api.v1.endpoints.overallocations.OverallocationService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_affected_activities = AsyncMock(
                return_value=[activity1_id, activity2_id]
            )
            mock_service_class.return_value = mock_service

            result = await get_affected_activities(
                resource_id=resource_id,
                check_date=date(2026, 1, 15),
                db=mock_db,
                current_user=mock_user,
            )

            assert len(result) == 2
            assert activity1_id in result
            assert activity2_id in result

    @pytest.mark.asyncio
    async def test_get_affected_activities_empty(self):
        """Should return empty list when no affected activities."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        resource_id = uuid4()

        with patch("src.api.v1.endpoints.overallocations.OverallocationService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_affected_activities = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            result = await get_affected_activities(
                resource_id=resource_id,
                check_date=date(2026, 1, 15),
                db=mock_db,
                current_user=mock_user,
            )

            assert len(result) == 0
