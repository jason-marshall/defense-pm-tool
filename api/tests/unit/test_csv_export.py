"""Unit tests for CSV export functionality."""

import csv
import io
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.import_export import (
    _write_activities_csv,
    _write_resources_csv,
    _write_wbs_csv,
)


def make_mock_activity(**overrides):
    """Create a mock activity with sensible defaults."""
    act = MagicMock()
    act.code = overrides.get("code", "ACT-001")
    act.name = overrides.get("name", "Design Review")
    act.duration = overrides.get("duration", 5)
    act.percent_complete = overrides.get("percent_complete", Decimal("50.00"))
    act.planned_start = overrides.get("planned_start", date(2026, 1, 1))
    act.planned_finish = overrides.get("planned_finish", date(2026, 1, 5))
    act.early_start = overrides.get("early_start", date(2026, 1, 1))
    act.early_finish = overrides.get("early_finish", date(2026, 1, 5))
    act.late_start = overrides.get("late_start", date(2026, 1, 2))
    act.late_finish = overrides.get("late_finish", date(2026, 1, 6))
    act.total_float = overrides.get("total_float", 1)
    act.free_float = overrides.get("free_float", 0)
    act.is_critical = overrides.get("is_critical", False)
    act.is_milestone = overrides.get("is_milestone", False)
    ct = overrides.get("constraint_type")
    act.constraint_type = ct
    act.constraint_date = overrides.get("constraint_date")
    act.budgeted_cost = overrides.get("budgeted_cost", Decimal("10000.00"))
    act.actual_cost = overrides.get("actual_cost", Decimal("5000.00"))
    act.ev_method = overrides.get("ev_method", "percent_complete")
    return act


def make_mock_resource(**overrides):
    """Create a mock resource with sensible defaults."""
    res = MagicMock()
    res.code = overrides.get("code", "ENG-001")
    res.name = overrides.get("name", "Senior Engineer")
    rt = MagicMock()
    rt.value = overrides.get("resource_type_value", "LABOR")
    res.resource_type = rt
    res.capacity_per_day = overrides.get("capacity_per_day", Decimal("8.00"))
    res.cost_rate = overrides.get("cost_rate", Decimal("150.00"))
    res.is_active = overrides.get("is_active", True)
    res.effective_date = overrides.get("effective_date", date(2026, 1, 1))
    return res


def make_mock_wbs(**overrides):
    """Create a mock WBS element with sensible defaults."""
    elem = MagicMock()
    elem.wbs_code = overrides.get("wbs_code", "1.1")
    elem.name = overrides.get("name", "Software Development")
    elem.level = overrides.get("level", 2)
    elem.path = overrides.get("path", "1.1")
    elem.is_control_account = overrides.get("is_control_account", False)
    elem.budget_at_completion = overrides.get(
        "budget_at_completion", Decimal("100000.00")
    )
    elem.description = overrides.get("description", "Software dev phase")
    return elem


def parse_csv_output(output: io.StringIO) -> list[list[str]]:
    """Parse CSV output into list of rows."""
    output.seek(0)
    reader = csv.reader(output)
    return list(reader)


class TestWriteActivitiesCSV:
    """Tests for activities CSV export."""

    @pytest.mark.asyncio
    async def test_writes_header_row(self):
        """Should write column headers."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()

        with patch(
            "src.api.v1.endpoints.import_export.ActivityRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(return_value=[])
            await _write_activities_csv(writer, uuid4(), mock_db)

        rows = parse_csv_output(output)
        assert rows[0][0] == "Code"
        assert "Name" in rows[0]
        assert "Duration (days)" in rows[0]
        assert "Budgeted Cost" in rows[0]

    @pytest.mark.asyncio
    async def test_writes_activity_data(self):
        """Should write activity data rows."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()
        activity = make_mock_activity()

        with patch(
            "src.api.v1.endpoints.import_export.ActivityRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(
                return_value=[activity]
            )
            await _write_activities_csv(writer, uuid4(), mock_db)

        rows = parse_csv_output(output)
        assert len(rows) == 2  # Header + 1 data row
        assert rows[1][0] == "ACT-001"
        assert rows[1][1] == "Design Review"
        assert rows[1][2] == "5"

    @pytest.mark.asyncio
    async def test_handles_none_fields(self):
        """Should handle None values gracefully."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()
        activity = make_mock_activity(
            percent_complete=None,
            planned_start=None,
            planned_finish=None,
            early_start=None,
            early_finish=None,
            late_start=None,
            late_finish=None,
            total_float=None,
            free_float=None,
            constraint_type=None,
            constraint_date=None,
            budgeted_cost=None,
            actual_cost=None,
            ev_method=None,
        )

        with patch(
            "src.api.v1.endpoints.import_export.ActivityRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(
                return_value=[activity]
            )
            await _write_activities_csv(writer, uuid4(), mock_db)

        rows = parse_csv_output(output)
        data_row = rows[1]
        # None fields should be empty strings
        assert data_row[3] == ""  # percent_complete
        assert data_row[4] == ""  # planned_start

    @pytest.mark.asyncio
    async def test_multiple_activities(self):
        """Should write multiple activities."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()
        activities = [
            make_mock_activity(code="ACT-001", name="Task A"),
            make_mock_activity(code="ACT-002", name="Task B"),
            make_mock_activity(code="ACT-003", name="Task C"),
        ]

        with patch(
            "src.api.v1.endpoints.import_export.ActivityRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(
                return_value=activities
            )
            await _write_activities_csv(writer, uuid4(), mock_db)

        rows = parse_csv_output(output)
        assert len(rows) == 4  # Header + 3 data rows

    @pytest.mark.asyncio
    async def test_include_header_label(self):
        """Should include section label when include_header_label is True."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()

        with patch(
            "src.api.v1.endpoints.import_export.ActivityRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(return_value=[])
            await _write_activities_csv(
                writer, uuid4(), mock_db, include_header_label=True
            )

        rows = parse_csv_output(output)
        assert rows[0][0] == "## Activities"


class TestWriteResourcesCSV:
    """Tests for resources CSV export."""

    @pytest.mark.asyncio
    async def test_writes_header_row(self):
        """Should write resource column headers."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()

        with patch(
            "src.api.v1.endpoints.import_export.ResourceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(
                return_value=([], 0)
            )
            await _write_resources_csv(writer, uuid4(), mock_db)

        rows = parse_csv_output(output)
        assert rows[0][0] == "Code"
        assert "Name" in rows[0]
        assert "Type" in rows[0]
        assert "Cost Rate" in rows[0]

    @pytest.mark.asyncio
    async def test_writes_resource_data(self):
        """Should write resource data rows."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()
        resource = make_mock_resource()

        with patch(
            "src.api.v1.endpoints.import_export.ResourceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(
                return_value=([resource], 1)
            )
            await _write_resources_csv(writer, uuid4(), mock_db)

        rows = parse_csv_output(output)
        assert len(rows) == 2
        assert rows[1][0] == "ENG-001"
        assert rows[1][1] == "Senior Engineer"
        assert rows[1][2] == "LABOR"

    @pytest.mark.asyncio
    async def test_handles_none_cost_rate(self):
        """Should handle None cost rate."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()
        resource = make_mock_resource(cost_rate=None, effective_date=None)

        with patch(
            "src.api.v1.endpoints.import_export.ResourceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(
                return_value=([resource], 1)
            )
            await _write_resources_csv(writer, uuid4(), mock_db)

        rows = parse_csv_output(output)
        assert rows[1][4] == ""  # cost_rate
        assert rows[1][6] == ""  # effective_date

    @pytest.mark.asyncio
    async def test_include_header_label(self):
        """Should include section label when requested."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()

        with patch(
            "src.api.v1.endpoints.import_export.ResourceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(
                return_value=([], 0)
            )
            await _write_resources_csv(
                writer, uuid4(), mock_db, include_header_label=True
            )

        rows = parse_csv_output(output)
        assert rows[0][0] == "## Resources"


class TestWriteWBSCSV:
    """Tests for WBS CSV export."""

    @pytest.mark.asyncio
    async def test_writes_header_row(self):
        """Should write WBS column headers."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()

        with patch(
            "src.api.v1.endpoints.import_export.WBSElementRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(return_value=[])
            await _write_wbs_csv(writer, uuid4(), mock_db)

        rows = parse_csv_output(output)
        assert rows[0][0] == "WBS Code"
        assert "Name" in rows[0]
        assert "Level" in rows[0]

    @pytest.mark.asyncio
    async def test_writes_wbs_data(self):
        """Should write WBS element data rows."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()
        wbs = make_mock_wbs()

        with patch(
            "src.api.v1.endpoints.import_export.WBSElementRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(
                return_value=[wbs]
            )
            await _write_wbs_csv(writer, uuid4(), mock_db)

        rows = parse_csv_output(output)
        assert len(rows) == 2
        assert rows[1][0] == "1.1"
        assert rows[1][1] == "Software Development"
        assert rows[1][2] == "2"

    @pytest.mark.asyncio
    async def test_handles_none_budget(self):
        """Should handle None budget at completion."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()
        wbs = make_mock_wbs(budget_at_completion=None, description=None)

        with patch(
            "src.api.v1.endpoints.import_export.WBSElementRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(
                return_value=[wbs]
            )
            await _write_wbs_csv(writer, uuid4(), mock_db)

        rows = parse_csv_output(output)
        assert rows[1][5] == ""  # budget_at_completion
        assert rows[1][6] == ""  # description

    @pytest.mark.asyncio
    async def test_control_account_flag(self):
        """Should include control account flag."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()
        wbs = make_mock_wbs(is_control_account=True)

        with patch(
            "src.api.v1.endpoints.import_export.WBSElementRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(
                return_value=[wbs]
            )
            await _write_wbs_csv(writer, uuid4(), mock_db)

        rows = parse_csv_output(output)
        assert rows[1][4] == "True"

    @pytest.mark.asyncio
    async def test_include_header_label(self):
        """Should include section label when requested."""
        output = io.StringIO()
        writer = csv.writer(output)
        mock_db = AsyncMock()

        with patch(
            "src.api.v1.endpoints.import_export.WBSElementRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(return_value=[])
            await _write_wbs_csv(
                writer, uuid4(), mock_db, include_header_label=True
            )

        rows = parse_csv_output(output)
        assert rows[0][0] == "## WBS Elements"
