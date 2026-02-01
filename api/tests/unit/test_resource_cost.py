"""Unit tests for resource cost service."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.enums import ResourceType
from src.services.resource_cost import (
    ActivityCostSummary,
    EVMSSyncResult,
    ProgramCostSummary,
    ResourceCostService,
    WBSCostSummary,
)


class TestActivityCostSummary:
    """Tests for ActivityCostSummary dataclass."""

    def test_creation(self):
        """Test creating ActivityCostSummary."""
        summary = ActivityCostSummary(
            activity_id=uuid4(),
            activity_code="A-001",
            activity_name="Test Activity",
            planned_cost=Decimal("1000.00"),
            actual_cost=Decimal("800.00"),
            cost_variance=Decimal("200.00"),
            percent_spent=Decimal("80.00"),
            resource_breakdown=[{"resource_id": "123", "cost": Decimal("800.00")}],
        )
        assert summary.activity_code == "A-001"
        assert summary.planned_cost == Decimal("1000.00")
        assert summary.cost_variance == Decimal("200.00")


class TestWBSCostSummary:
    """Tests for WBSCostSummary dataclass."""

    def test_creation(self):
        """Test creating WBSCostSummary."""
        summary = WBSCostSummary(
            wbs_id=uuid4(),
            wbs_code="1.1",
            wbs_name="Test WBS",
            planned_cost=Decimal("5000.00"),
            actual_cost=Decimal("4500.00"),
            cost_variance=Decimal("500.00"),
            activity_count=5,
        )
        assert summary.wbs_code == "1.1"
        assert summary.activity_count == 5


class TestProgramCostSummary:
    """Tests for ProgramCostSummary dataclass."""

    def test_creation(self):
        """Test creating ProgramCostSummary."""
        summary = ProgramCostSummary(
            program_id=uuid4(),
            total_planned_cost=Decimal("100000.00"),
            total_actual_cost=Decimal("90000.00"),
            total_cost_variance=Decimal("10000.00"),
            labor_cost=Decimal("70000.00"),
            equipment_cost=Decimal("15000.00"),
            material_cost=Decimal("5000.00"),
            resource_count=10,
            activity_count=25,
            wbs_breakdown=[],
        )
        assert summary.labor_cost == Decimal("70000.00")
        assert summary.resource_count == 10


class TestEVMSSyncResult:
    """Tests for EVMSSyncResult dataclass."""

    def test_creation_success(self):
        """Test creating successful EVMSSyncResult."""
        result = EVMSSyncResult(
            period_id=uuid4(),
            acwp_updated=Decimal("50000.00"),
            wbs_elements_updated=15,
            success=True,
            warnings=[],
        )
        assert result.success is True
        assert result.wbs_elements_updated == 15

    def test_creation_with_warnings(self):
        """Test creating EVMSSyncResult with warnings."""
        result = EVMSSyncResult(
            period_id=uuid4(),
            acwp_updated=Decimal("0"),
            wbs_elements_updated=0,
            success=False,
            warnings=["Period not found"],
        )
        assert result.success is False
        assert "Period not found" in result.warnings


class TestResourceCostServiceRound:
    """Tests for ResourceCostService._round method."""

    def test_round_standard(self):
        """Test standard rounding."""
        result = ResourceCostService._round(Decimal("100.456"))
        assert result == Decimal("100.46")

    def test_round_half_up(self):
        """Test round half up behavior."""
        result = ResourceCostService._round(Decimal("100.455"))
        assert result == Decimal("100.46")

    def test_round_down(self):
        """Test rounding down."""
        result = ResourceCostService._round(Decimal("100.454"))
        assert result == Decimal("100.45")


class TestResourceCostServiceCalculateAssignmentCost:
    """Tests for ResourceCostService.calculate_assignment_cost method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance."""
        return ResourceCostService(mock_db)

    @pytest.mark.asyncio
    async def test_assignment_not_found(self, service, mock_db):
        """Test when assignment is not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        planned, actual = await service.calculate_assignment_cost(uuid4())

        assert planned == Decimal("0")
        assert actual == Decimal("0")

    @pytest.mark.asyncio
    async def test_labor_assignment_cost(self, service, mock_db):
        """Test calculating labor assignment cost."""
        resource = MagicMock()
        resource.resource_type = ResourceType.LABOR
        resource.cost_rate = Decimal("50.00")

        assignment = MagicMock()
        assignment.resource = resource
        assignment.planned_hours = Decimal("40")
        assignment.actual_hours = Decimal("35")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment
        mock_db.execute.return_value = mock_result

        planned, actual = await service.calculate_assignment_cost(uuid4())

        assert planned == Decimal("2000.00")  # 40 * 50
        assert actual == Decimal("1750.00")  # 35 * 50

    @pytest.mark.asyncio
    async def test_equipment_assignment_cost(self, service, mock_db):
        """Test calculating equipment assignment cost."""
        resource = MagicMock()
        resource.resource_type = ResourceType.EQUIPMENT
        resource.cost_rate = Decimal("100.00")

        assignment = MagicMock()
        assignment.resource = resource
        assignment.planned_hours = Decimal("20")
        assignment.actual_hours = Decimal("22")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment
        mock_db.execute.return_value = mock_result

        planned, actual = await service.calculate_assignment_cost(uuid4())

        assert planned == Decimal("2000.00")  # 20 * 100
        assert actual == Decimal("2200.00")  # 22 * 100

    @pytest.mark.asyncio
    async def test_material_assignment_cost(self, service, mock_db):
        """Test calculating material assignment cost."""
        resource = MagicMock()
        resource.resource_type = ResourceType.MATERIAL
        resource.unit_cost = Decimal("25.00")

        assignment = MagicMock()
        assignment.resource = resource
        assignment.quantity_assigned = Decimal("100")
        assignment.quantity_consumed = Decimal("80")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment
        mock_db.execute.return_value = mock_result

        planned, actual = await service.calculate_assignment_cost(uuid4())

        assert planned == Decimal("2500.00")  # 100 * 25
        assert actual == Decimal("2000.00")  # 80 * 25

    @pytest.mark.asyncio
    async def test_assignment_with_no_cost_rate(self, service, mock_db):
        """Test assignment when resource has no cost rate."""
        resource = MagicMock()
        resource.resource_type = ResourceType.LABOR
        resource.cost_rate = None

        assignment = MagicMock()
        assignment.resource = resource
        assignment.planned_hours = Decimal("40")
        assignment.actual_hours = Decimal("35")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment
        mock_db.execute.return_value = mock_result

        planned, actual = await service.calculate_assignment_cost(uuid4())

        assert planned == Decimal("0")
        assert actual == Decimal("0")


class TestResourceCostServiceCalculateActivityCost:
    """Tests for ResourceCostService.calculate_activity_cost method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance."""
        return ResourceCostService(mock_db)

    @pytest.mark.asyncio
    async def test_activity_not_found(self, service, mock_db):
        """Test when activity is not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Activity .* not found"):
            await service.calculate_activity_cost(uuid4())

    @pytest.mark.asyncio
    async def test_activity_with_no_assignments(self, service, mock_db):
        """Test activity with no assignments."""
        activity = MagicMock()
        activity.id = uuid4()
        activity.code = "A-001"
        activity.name = "Test Activity"
        activity.resource_assignments = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = activity
        mock_db.execute.return_value = mock_result

        result = await service.calculate_activity_cost(activity.id)

        assert result.planned_cost == Decimal("0")
        assert result.actual_cost == Decimal("0")
        assert result.percent_spent == Decimal("0")

    @pytest.mark.asyncio
    async def test_activity_with_labor_assignment(self, service, mock_db):
        """Test activity with labor assignment."""
        resource = MagicMock()
        resource.id = uuid4()
        resource.code = "R-001"
        resource.name = "Engineer"
        resource.resource_type = ResourceType.LABOR
        resource.cost_rate = Decimal("75.00")

        assignment = MagicMock()
        assignment.deleted_at = None
        assignment.resource = resource
        assignment.planned_hours = Decimal("40")
        assignment.actual_hours = Decimal("30")

        activity = MagicMock()
        activity.id = uuid4()
        activity.code = "A-001"
        activity.name = "Test Activity"
        activity.resource_assignments = [assignment]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = activity
        mock_db.execute.return_value = mock_result

        result = await service.calculate_activity_cost(activity.id)

        assert result.planned_cost == Decimal("3000.00")  # 40 * 75
        assert result.actual_cost == Decimal("2250.00")  # 30 * 75
        assert result.cost_variance == Decimal("750.00")

    @pytest.mark.asyncio
    async def test_activity_with_material_assignment(self, service, mock_db):
        """Test activity with material assignment."""
        resource = MagicMock()
        resource.id = uuid4()
        resource.code = "M-001"
        resource.name = "Concrete"
        resource.resource_type = ResourceType.MATERIAL
        resource.unit_cost = Decimal("150.00")

        assignment = MagicMock()
        assignment.deleted_at = None
        assignment.resource = resource
        assignment.quantity_assigned = Decimal("100")
        assignment.quantity_consumed = Decimal("85")

        activity = MagicMock()
        activity.id = uuid4()
        activity.code = "A-001"
        activity.name = "Test Activity"
        activity.resource_assignments = [assignment]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = activity
        mock_db.execute.return_value = mock_result

        result = await service.calculate_activity_cost(activity.id)

        assert result.planned_cost == Decimal("15000.00")  # 100 * 150
        assert result.actual_cost == Decimal("12750.00")  # 85 * 150

    @pytest.mark.asyncio
    async def test_activity_with_deleted_assignment(self, service, mock_db):
        """Test activity with deleted assignment is skipped."""
        resource = MagicMock()
        resource.id = uuid4()
        resource.resource_type = ResourceType.LABOR
        resource.cost_rate = Decimal("50.00")

        assignment = MagicMock()
        assignment.deleted_at = "2026-01-01"  # Deleted
        assignment.resource = resource
        assignment.planned_hours = Decimal("40")
        assignment.actual_hours = Decimal("30")

        activity = MagicMock()
        activity.id = uuid4()
        activity.code = "A-001"
        activity.name = "Test Activity"
        activity.resource_assignments = [assignment]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = activity
        mock_db.execute.return_value = mock_result

        result = await service.calculate_activity_cost(activity.id)

        assert result.planned_cost == Decimal("0")
        assert result.actual_cost == Decimal("0")


class TestResourceCostServiceCalculateWBSCost:
    """Tests for ResourceCostService.calculate_wbs_cost method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance."""
        return ResourceCostService(mock_db)

    @pytest.mark.asyncio
    async def test_wbs_not_found(self, service, mock_db):
        """Test when WBS is not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="WBS .* not found"):
            await service.calculate_wbs_cost(uuid4())

    @pytest.mark.asyncio
    async def test_wbs_without_children(self, service, mock_db):
        """Test WBS calculation without including children."""
        wbs = MagicMock()
        wbs.id = uuid4()
        wbs.wbs_code = "1.1"
        wbs.name = "Test WBS"

        # First call returns WBS
        mock_wbs_result = MagicMock()
        mock_wbs_result.scalar_one_or_none.return_value = wbs

        # Second call returns no activities
        mock_activity_result = MagicMock()
        mock_activity_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_wbs_result, mock_activity_result]

        result = await service.calculate_wbs_cost(wbs.id, include_children=False)

        assert result.wbs_code == "1.1"
        assert result.planned_cost == Decimal("0")
        assert result.activity_count == 0


class TestResourceCostServiceCalculateProgramCost:
    """Tests for ResourceCostService.calculate_program_cost method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance."""
        return ResourceCostService(mock_db)

    @pytest.mark.asyncio
    async def test_program_with_no_assignments(self, service, mock_db):
        """Test program with no assignments."""
        # First call returns no assignments
        mock_assignment_result = MagicMock()
        mock_assignment_result.scalars.return_value.all.return_value = []

        # Second call returns no WBS elements
        mock_wbs_result = MagicMock()
        mock_wbs_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_assignment_result, mock_wbs_result]

        program_id = uuid4()
        result = await service.calculate_program_cost(program_id)

        assert result.program_id == program_id
        assert result.total_planned_cost == Decimal("0")
        assert result.resource_count == 0

    @pytest.mark.asyncio
    async def test_program_with_labor_and_equipment(self, service, mock_db):
        """Test program with labor and equipment assignments."""
        labor_resource = MagicMock()
        labor_resource.id = uuid4()
        labor_resource.resource_type = ResourceType.LABOR
        labor_resource.cost_rate = Decimal("50.00")

        equipment_resource = MagicMock()
        equipment_resource.id = uuid4()
        equipment_resource.resource_type = ResourceType.EQUIPMENT
        equipment_resource.cost_rate = Decimal("100.00")

        labor_assignment = MagicMock()
        labor_assignment.resource = labor_resource
        labor_assignment.activity_id = uuid4()
        labor_assignment.planned_hours = Decimal("40")
        labor_assignment.actual_hours = Decimal("35")

        equipment_assignment = MagicMock()
        equipment_assignment.resource = equipment_resource
        equipment_assignment.activity_id = uuid4()
        equipment_assignment.planned_hours = Decimal("20")
        equipment_assignment.actual_hours = Decimal("25")

        # First call returns assignments
        mock_assignment_result = MagicMock()
        mock_assignment_result.scalars.return_value.all.return_value = [
            labor_assignment,
            equipment_assignment,
        ]

        # Second call returns no WBS elements
        mock_wbs_result = MagicMock()
        mock_wbs_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_assignment_result, mock_wbs_result]

        result = await service.calculate_program_cost(uuid4())

        # Labor: 40 * 50 = 2000 planned, 35 * 50 = 1750 actual
        # Equipment: 20 * 100 = 2000 planned, 25 * 100 = 2500 actual
        assert result.total_planned_cost == Decimal("4000.00")
        assert result.total_actual_cost == Decimal("4250.00")
        assert result.labor_cost == Decimal("1750.00")
        assert result.equipment_cost == Decimal("2500.00")


class TestResourceCostServiceSyncEvmsACWP:
    """Tests for ResourceCostService.sync_evms_acwp method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance."""
        return ResourceCostService(mock_db)

    @pytest.mark.asyncio
    async def test_period_not_found(self, service, mock_db):
        """Test when EVMS period is not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.sync_evms_acwp(uuid4(), uuid4())

        assert result.success is False
        assert "Period not found" in result.warnings


class TestResourceCostServiceRecordCostEntry:
    """Tests for ResourceCostService.record_cost_entry method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance."""
        return ResourceCostService(mock_db)

    @pytest.mark.asyncio
    async def test_assignment_not_found(self, service, mock_db):
        """Test when assignment is not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Assignment .* not found"):
            await service.record_cost_entry(uuid4(), date(2026, 1, 15))

    @pytest.mark.asyncio
    async def test_record_labor_entry(self, service, mock_db):
        """Test recording labor cost entry."""
        resource = MagicMock()
        resource.resource_type = ResourceType.LABOR
        resource.cost_rate = Decimal("75.00")

        assignment = MagicMock()
        assignment.resource = resource
        assignment.actual_hours = Decimal("0")
        assignment.actual_cost = Decimal("0")
        assignment.quantity_consumed = Decimal("0")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment
        mock_db.execute.return_value = mock_result

        result = await service.record_cost_entry(
            uuid4(),
            date(2026, 1, 15),
            hours_worked=Decimal("8"),
        )

        # Verify assignment was updated
        assert assignment.actual_hours == Decimal("8")
        assert assignment.actual_cost == Decimal("600.00")  # 8 * 75

    @pytest.mark.asyncio
    async def test_record_material_entry(self, service, mock_db):
        """Test recording material cost entry."""
        resource = MagicMock()
        resource.resource_type = ResourceType.MATERIAL
        resource.unit_cost = Decimal("25.00")

        assignment = MagicMock()
        assignment.resource = resource
        assignment.actual_hours = Decimal("0")
        assignment.actual_cost = Decimal("0")
        assignment.quantity_consumed = Decimal("0")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment
        mock_db.execute.return_value = mock_result

        result = await service.record_cost_entry(
            uuid4(),
            date(2026, 1, 15),
            quantity_used=Decimal("50"),
        )

        # Verify assignment was updated
        assert assignment.quantity_consumed == Decimal("50")


class TestResourceCostServiceGetAssignmentCostEntries:
    """Tests for ResourceCostService.get_assignment_cost_entries method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance."""
        return ResourceCostService(mock_db)

    @pytest.mark.asyncio
    async def test_get_all_entries(self, service, mock_db):
        """Test getting all cost entries for an assignment."""
        entry1 = MagicMock()
        entry1.entry_date = date(2026, 1, 10)
        entry2 = MagicMock()
        entry2.entry_date = date(2026, 1, 15)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [entry1, entry2]
        mock_db.execute.return_value = mock_result

        result = await service.get_assignment_cost_entries(uuid4())

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_entries_with_date_range(self, service, mock_db):
        """Test getting cost entries within date range."""
        entry = MagicMock()
        entry.entry_date = date(2026, 1, 15)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [entry]
        mock_db.execute.return_value = mock_result

        result = await service.get_assignment_cost_entries(
            uuid4(),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        assert len(result) == 1


class TestResourceCostServiceGetResourceCostSummary:
    """Tests for ResourceCostService.get_resource_cost_summary method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance."""
        return ResourceCostService(mock_db)

    @pytest.mark.asyncio
    async def test_resource_with_no_assignments(self, service, mock_db):
        """Test resource with no assignments."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        resource_id = uuid4()
        result = await service.get_resource_cost_summary(resource_id)

        assert result["resource_id"] == str(resource_id)
        assert result["assignment_count"] == 0
        assert result["total_planned_hours"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_resource_with_multiple_assignments(self, service, mock_db):
        """Test resource with multiple assignments."""
        assignment1 = MagicMock()
        assignment1.planned_hours = Decimal("40")
        assignment1.actual_hours = Decimal("35")
        assignment1.planned_cost = Decimal("2000")
        assignment1.actual_cost = Decimal("1750")

        assignment2 = MagicMock()
        assignment2.planned_hours = Decimal("20")
        assignment2.actual_hours = Decimal("25")
        assignment2.planned_cost = Decimal("1000")
        assignment2.actual_cost = Decimal("1250")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [assignment1, assignment2]
        mock_db.execute.return_value = mock_result

        resource_id = uuid4()
        result = await service.get_resource_cost_summary(resource_id)

        assert result["assignment_count"] == 2
        assert result["total_planned_hours"] == Decimal("60.00")
        assert result["total_actual_hours"] == Decimal("60.00")
        assert result["total_planned_cost"] == Decimal("3000.00")
        assert result["total_actual_cost"] == Decimal("3000.00")
