"""Unit tests for ResourceCostService."""

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.services.resource_cost import (
    ActivityCostSummary,
    EVMSSyncResult,
    ProgramCostSummary,
    ResourceCostService,
    WBSCostSummary,
)


class TestResourceCostServiceRounding:
    """Tests for decimal rounding in ResourceCostService."""

    def test_round_up(self):
        """Test rounding up at midpoint."""
        assert ResourceCostService._round(Decimal("10.125")) == Decimal("10.13")
        assert ResourceCostService._round(Decimal("10.005")) == Decimal("10.01")

    def test_round_down(self):
        """Test rounding down below midpoint."""
        assert ResourceCostService._round(Decimal("10.124")) == Decimal("10.12")
        assert ResourceCostService._round(Decimal("10.004")) == Decimal("10.00")

    def test_round_exact(self):
        """Test exact values don't change."""
        assert ResourceCostService._round(Decimal("10.00")) == Decimal("10.00")
        assert ResourceCostService._round(Decimal("0.00")) == Decimal("0.00")

    def test_round_negative(self):
        """Test rounding negative values (ROUND_HALF_UP rounds away from zero)."""
        assert ResourceCostService._round(Decimal("-10.125")) == Decimal("-10.13")
        assert ResourceCostService._round(Decimal("-10.124")) == Decimal("-10.12")


class TestLaborCostCalculation:
    """Tests for labor resource cost calculations."""

    def test_labor_cost_basic(self):
        """Test basic labor cost calculation."""
        hours = Decimal("40")
        rate = Decimal("150.00")
        expected = Decimal("6000.00")

        actual = hours * rate
        assert ResourceCostService._round(actual) == expected

    def test_labor_cost_fractional_hours(self):
        """Test labor cost with fractional hours."""
        hours = Decimal("37.5")
        rate = Decimal("125.00")
        expected = Decimal("4687.50")

        actual = hours * rate
        assert ResourceCostService._round(actual) == expected

    def test_labor_cost_fractional_rate(self):
        """Test labor cost with fractional rate."""
        hours = Decimal("8")
        rate = Decimal("87.53")
        expected = Decimal("700.24")

        actual = hours * rate
        assert ResourceCostService._round(actual) == expected

    def test_labor_cost_zero_hours(self):
        """Test labor cost with zero hours."""
        hours = Decimal("0")
        rate = Decimal("150.00")
        expected = Decimal("0.00")

        actual = hours * rate
        assert ResourceCostService._round(actual) == expected

    def test_labor_cost_zero_rate(self):
        """Test labor cost with zero rate."""
        hours = Decimal("40")
        rate = Decimal("0")
        expected = Decimal("0.00")

        actual = hours * rate
        assert ResourceCostService._round(actual) == expected


class TestMaterialCostCalculation:
    """Tests for material resource cost calculations."""

    def test_material_cost_basic(self):
        """Test basic material cost calculation."""
        quantity = Decimal("100")
        unit_cost = Decimal("25.50")
        expected = Decimal("2550.00")

        actual = quantity * unit_cost
        assert ResourceCostService._round(actual) == expected

    def test_material_cost_fractional_quantity(self):
        """Test material cost with fractional quantity."""
        quantity = Decimal("12.5")
        unit_cost = Decimal("10.00")
        expected = Decimal("125.00")

        actual = quantity * unit_cost
        assert ResourceCostService._round(actual) == expected

    def test_material_cost_small_unit_cost(self):
        """Test material cost with small unit cost."""
        quantity = Decimal("1000")
        unit_cost = Decimal("0.15")
        expected = Decimal("150.00")

        actual = quantity * unit_cost
        assert ResourceCostService._round(actual) == expected


class TestCostVarianceCalculation:
    """Tests for cost variance calculations."""

    def test_under_budget(self):
        """Test cost variance when under budget."""
        planned = Decimal("10000.00")
        actual = Decimal("9500.00")
        variance = planned - actual
        assert variance == Decimal("500.00")

    def test_over_budget(self):
        """Test cost variance when over budget."""
        planned = Decimal("10000.00")
        actual = Decimal("10500.00")
        variance = planned - actual
        assert variance == Decimal("-500.00")

    def test_on_budget(self):
        """Test cost variance when exactly on budget."""
        planned = Decimal("10000.00")
        actual = Decimal("10000.00")
        variance = planned - actual
        assert variance == Decimal("0.00")


class TestPercentSpentCalculation:
    """Tests for percent spent calculations."""

    def test_percent_spent_half(self):
        """Test 50% spent."""
        planned = Decimal("1000.00")
        actual = Decimal("500.00")
        percent = (actual / planned) * 100
        assert ResourceCostService._round(percent) == Decimal("50.00")

    def test_percent_spent_over_100(self):
        """Test over 100% spent."""
        planned = Decimal("1000.00")
        actual = Decimal("1200.00")
        percent = (actual / planned) * 100
        assert ResourceCostService._round(percent) == Decimal("120.00")

    def test_percent_spent_zero_planned(self):
        """Test percent spent with zero planned (avoid division by zero)."""
        planned = Decimal("0")
        actual = Decimal("500.00")
        # Should return 0 when planned is 0
        percent = (actual / planned * 100) if planned > 0 else Decimal("0")
        assert percent == Decimal("0")


class TestDataclasses:
    """Tests for dataclass structures."""

    def test_activity_cost_summary(self):
        """Test ActivityCostSummary dataclass."""
        summary = ActivityCostSummary(
            activity_id=uuid4(),
            activity_code="ACT-001",
            activity_name="Design Phase",
            planned_cost=Decimal("10000.00"),
            actual_cost=Decimal("8500.00"),
            cost_variance=Decimal("1500.00"),
            percent_spent=Decimal("85.00"),
            resource_breakdown=[],
        )

        assert summary.activity_code == "ACT-001"
        assert summary.planned_cost == Decimal("10000.00")
        assert summary.cost_variance == Decimal("1500.00")

    def test_wbs_cost_summary(self):
        """Test WBSCostSummary dataclass."""
        summary = WBSCostSummary(
            wbs_id=uuid4(),
            wbs_code="1.1",
            wbs_name="Engineering",
            planned_cost=Decimal("50000.00"),
            actual_cost=Decimal("45000.00"),
            cost_variance=Decimal("5000.00"),
            activity_count=10,
        )

        assert summary.wbs_code == "1.1"
        assert summary.activity_count == 10

    def test_program_cost_summary(self):
        """Test ProgramCostSummary dataclass."""
        summary = ProgramCostSummary(
            program_id=uuid4(),
            total_planned_cost=Decimal("100000.00"),
            total_actual_cost=Decimal("85000.00"),
            total_cost_variance=Decimal("15000.00"),
            labor_cost=Decimal("60000.00"),
            equipment_cost=Decimal("15000.00"),
            material_cost=Decimal("10000.00"),
            resource_count=15,
            activity_count=50,
            wbs_breakdown=[],
        )

        assert summary.labor_cost == Decimal("60000.00")
        assert summary.resource_count == 15

    def test_evms_sync_result_success(self):
        """Test EVMSSyncResult for successful sync."""
        result = EVMSSyncResult(
            period_id=uuid4(),
            acwp_updated=Decimal("85000.00"),
            wbs_elements_updated=25,
            success=True,
            warnings=[],
        )

        assert result.success is True
        assert result.wbs_elements_updated == 25
        assert len(result.warnings) == 0

    def test_evms_sync_result_failure(self):
        """Test EVMSSyncResult for failed sync."""
        result = EVMSSyncResult(
            period_id=uuid4(),
            acwp_updated=Decimal("0"),
            wbs_elements_updated=0,
            success=False,
            warnings=["Period not found"],
        )

        assert result.success is False
        assert "Period not found" in result.warnings


class TestResourceCostServiceInit:
    """Tests for ResourceCostService initialization."""

    def test_init_with_db_session(self):
        """Test service initializes with database session."""
        mock_db = MagicMock()
        service = ResourceCostService(mock_db)

        assert service.db == mock_db


class TestCalculateAssignmentCostAsync:
    """Async tests for calculate_assignment_cost method."""

    @pytest.fixture
    def service(self):
        """Create service with mocked db."""
        from unittest.mock import AsyncMock

        db = AsyncMock()
        return ResourceCostService(db)

    @pytest.mark.asyncio
    async def test_assignment_not_found_returns_zeros(self, service):
        """Should return zeros when assignment not found."""
        from unittest.mock import AsyncMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute = AsyncMock(return_value=mock_result)

        planned, actual = await service.calculate_assignment_cost(uuid4())

        assert planned == Decimal("0")
        assert actual == Decimal("0")

    @pytest.mark.asyncio
    async def test_labor_resource_cost_calculation(self, service):
        """Should calculate costs for labor resource."""
        from unittest.mock import AsyncMock

        from src.models.enums import ResourceType

        resource = MagicMock()
        resource.resource_type = ResourceType.LABOR
        resource.cost_rate = Decimal("100.00")

        assignment = MagicMock()
        assignment.resource = resource
        assignment.planned_hours = Decimal("40.00")
        assignment.actual_hours = Decimal("35.00")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment
        service.db.execute = AsyncMock(return_value=mock_result)

        planned, actual = await service.calculate_assignment_cost(uuid4())

        assert planned == Decimal("4000.00")
        assert actual == Decimal("3500.00")

    @pytest.mark.asyncio
    async def test_material_resource_cost_calculation(self, service):
        """Should calculate costs for material resource."""
        from unittest.mock import AsyncMock

        from src.models.enums import ResourceType

        resource = MagicMock()
        resource.resource_type = ResourceType.MATERIAL
        resource.unit_cost = Decimal("25.00")

        assignment = MagicMock()
        assignment.resource = resource
        assignment.quantity_assigned = Decimal("100.00")
        assignment.quantity_consumed = Decimal("80.00")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment
        service.db.execute = AsyncMock(return_value=mock_result)

        planned, actual = await service.calculate_assignment_cost(uuid4())

        assert planned == Decimal("2500.00")
        assert actual == Decimal("2000.00")

    @pytest.mark.asyncio
    async def test_equipment_resource_cost_calculation(self, service):
        """Should calculate costs for equipment resource."""
        from unittest.mock import AsyncMock

        from src.models.enums import ResourceType

        resource = MagicMock()
        resource.resource_type = ResourceType.EQUIPMENT
        resource.cost_rate = Decimal("200.00")

        assignment = MagicMock()
        assignment.resource = resource
        assignment.planned_hours = Decimal("20.00")
        assignment.actual_hours = Decimal("18.00")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment
        service.db.execute = AsyncMock(return_value=mock_result)

        planned, actual = await service.calculate_assignment_cost(uuid4())

        assert planned == Decimal("4000.00")
        assert actual == Decimal("3600.00")

    @pytest.mark.asyncio
    async def test_none_cost_rate_returns_zero(self, service):
        """Should handle None cost rate."""
        from unittest.mock import AsyncMock

        from src.models.enums import ResourceType

        resource = MagicMock()
        resource.resource_type = ResourceType.LABOR
        resource.cost_rate = None

        assignment = MagicMock()
        assignment.resource = resource
        assignment.planned_hours = Decimal("40.00")
        assignment.actual_hours = Decimal("35.00")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment
        service.db.execute = AsyncMock(return_value=mock_result)

        planned, actual = await service.calculate_assignment_cost(uuid4())

        assert planned == Decimal("0.00")
        assert actual == Decimal("0.00")


class TestCalculateActivityCostAsync:
    """Async tests for calculate_activity_cost method."""

    @pytest.fixture
    def service(self):
        """Create service with mocked db."""
        from unittest.mock import AsyncMock

        db = AsyncMock()
        return ResourceCostService(db)

    @pytest.mark.asyncio
    async def test_activity_not_found_raises_error(self, service):
        """Should raise ValueError when activity not found."""
        from unittest.mock import AsyncMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError) as exc_info:
            await service.calculate_activity_cost(uuid4())
        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_activity_with_no_assignments(self, service):
        """Should handle activity with no assignments."""
        from unittest.mock import AsyncMock

        activity = MagicMock()
        activity.id = uuid4()
        activity.code = "A-001"
        activity.name = "Test Activity"
        activity.resource_assignments = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = activity
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.calculate_activity_cost(activity.id)

        assert result.planned_cost == Decimal("0.00")
        assert result.actual_cost == Decimal("0.00")
        assert result.resource_breakdown == []

    @pytest.mark.asyncio
    async def test_skips_deleted_assignments(self, service):
        """Should skip deleted assignments."""
        from unittest.mock import AsyncMock

        from src.models.enums import ResourceType

        resource = MagicMock()
        resource.id = uuid4()
        resource.code = "R-001"
        resource.name = "Resource"
        resource.resource_type = ResourceType.LABOR
        resource.cost_rate = Decimal("100.00")

        deleted_assignment = MagicMock()
        deleted_assignment.deleted_at = "2026-01-01"
        deleted_assignment.resource = resource

        activity = MagicMock()
        activity.id = uuid4()
        activity.code = "A-001"
        activity.name = "Test"
        activity.resource_assignments = [deleted_assignment]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = activity
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.calculate_activity_cost(activity.id)

        assert result.planned_cost == Decimal("0.00")
        assert len(result.resource_breakdown) == 0

    @pytest.mark.asyncio
    async def test_calculates_correct_totals(self, service):
        """Should calculate correct cost totals."""
        from unittest.mock import AsyncMock

        from src.models.enums import ResourceType

        resource = MagicMock()
        resource.id = uuid4()
        resource.code = "ENG-001"
        resource.name = "Engineer"
        resource.resource_type = ResourceType.LABOR
        resource.cost_rate = Decimal("100.00")

        assignment = MagicMock()
        assignment.deleted_at = None
        assignment.resource = resource
        assignment.planned_hours = Decimal("80.00")
        assignment.actual_hours = Decimal("70.00")

        activity = MagicMock()
        activity.id = uuid4()
        activity.code = "A-001"
        activity.name = "Design"
        activity.resource_assignments = [assignment]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = activity
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.calculate_activity_cost(activity.id)

        assert result.planned_cost == Decimal("8000.00")
        assert result.actual_cost == Decimal("7000.00")
        assert result.cost_variance == Decimal("1000.00")
        assert result.percent_spent == Decimal("87.50")
        assert len(result.resource_breakdown) == 1


class TestCalculateWBSCostAsync:
    """Async tests for calculate_wbs_cost method."""

    @pytest.fixture
    def service(self):
        """Create service with mocked db."""
        from unittest.mock import AsyncMock

        db = AsyncMock()
        return ResourceCostService(db)

    @pytest.mark.asyncio
    async def test_wbs_not_found_raises_error(self, service):
        """Should raise ValueError when WBS not found."""
        from unittest.mock import AsyncMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError) as exc_info:
            await service.calculate_wbs_cost(uuid4())
        assert "not found" in str(exc_info.value)


class TestGetResourceCostSummaryAsync:
    """Async tests for get_resource_cost_summary method."""

    @pytest.fixture
    def service(self):
        """Create service with mocked db."""
        from unittest.mock import AsyncMock

        db = AsyncMock()
        return ResourceCostService(db)

    @pytest.mark.asyncio
    async def test_no_assignments_returns_zeros(self, service):
        """Should return zeros for resource with no assignments."""
        from unittest.mock import AsyncMock

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        service.db.execute = AsyncMock(return_value=mock_result)

        resource_id = uuid4()
        result = await service.get_resource_cost_summary(resource_id)

        assert result["resource_id"] == str(resource_id)
        assert result["assignment_count"] == 0
        assert result["total_planned_hours"] == Decimal("0.00")
        assert result["total_actual_hours"] == Decimal("0.00")
        assert result["cost_variance"] == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_sums_multiple_assignments(self, service):
        """Should sum up values from multiple assignments."""
        from unittest.mock import AsyncMock

        assignment1 = MagicMock()
        assignment1.planned_hours = Decimal("40.00")
        assignment1.actual_hours = Decimal("35.00")
        assignment1.planned_cost = Decimal("4000.00")
        assignment1.actual_cost = Decimal("3500.00")

        assignment2 = MagicMock()
        assignment2.planned_hours = Decimal("20.00")
        assignment2.actual_hours = Decimal("22.00")
        assignment2.planned_cost = Decimal("2000.00")
        assignment2.actual_cost = Decimal("2200.00")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [assignment1, assignment2]
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_resource_cost_summary(uuid4())

        assert result["assignment_count"] == 2
        assert result["total_planned_hours"] == Decimal("60.00")
        assert result["total_actual_hours"] == Decimal("57.00")
        assert result["total_planned_cost"] == Decimal("6000.00")
        assert result["total_actual_cost"] == Decimal("5700.00")
        assert result["cost_variance"] == Decimal("300.00")


class TestRecordCostEntryAsync:
    """Async tests for record_cost_entry method."""

    @pytest.fixture
    def service(self):
        """Create service with mocked db."""
        from unittest.mock import AsyncMock

        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()
        return ResourceCostService(db)

    @pytest.mark.asyncio
    async def test_assignment_not_found_raises_error(self, service):
        """Should raise ValueError when assignment not found."""
        from datetime import date as dt_date
        from unittest.mock import AsyncMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError) as exc_info:
            await service.record_cost_entry(
                assignment_id=uuid4(),
                entry_date=dt_date(2026, 1, 15),
                hours_worked=Decimal("8.00"),
            )
        assert "not found" in str(exc_info.value)


class TestGetAssignmentCostEntriesAsync:
    """Async tests for get_assignment_cost_entries method."""

    @pytest.fixture
    def service(self):
        """Create service with mocked db."""
        from unittest.mock import AsyncMock

        db = AsyncMock()
        return ResourceCostService(db)

    @pytest.mark.asyncio
    async def test_returns_entries_list(self, service):
        """Should return list of cost entries."""
        from unittest.mock import AsyncMock

        mock_entry1 = MagicMock()
        mock_entry2 = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_entry1, mock_entry2]
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_assignment_cost_entries(uuid4())

        assert len(result) == 2


class TestCalculateProgramCostAsync:
    """Async tests for calculate_program_cost method."""

    @pytest.fixture
    def service(self):
        """Create service with mocked db."""
        from unittest.mock import AsyncMock

        db = AsyncMock()
        return ResourceCostService(db)

    @pytest.mark.asyncio
    async def test_program_cost_with_material_assignments(self, service):
        """Should calculate program cost including material resources."""
        from unittest.mock import AsyncMock

        from src.models.enums import ResourceType

        # Create material resource assignment
        material_resource = MagicMock()
        material_resource.id = uuid4()
        material_resource.resource_type = ResourceType.MATERIAL
        material_resource.unit_cost = Decimal("50.00")

        material_assignment = MagicMock()
        material_assignment.activity_id = uuid4()
        material_assignment.quantity_assigned = Decimal("100.00")
        material_assignment.quantity_consumed = Decimal("80.00")
        material_assignment.resource = material_resource

        # Mock assignments query
        assignments_mock = MagicMock()
        assignments_mock.scalars.return_value.all.return_value = [material_assignment]

        # Mock WBS query (empty)
        wbs_mock = MagicMock()
        wbs_mock.scalars.return_value.all.return_value = []

        service.db.execute = AsyncMock(side_effect=[assignments_mock, wbs_mock])

        result = await service.calculate_program_cost(uuid4())

        # Material cost: 80 * 50 = 4000
        assert result.material_cost == Decimal("4000.00")
        assert result.total_actual_cost == Decimal("4000.00")

    @pytest.mark.asyncio
    async def test_program_cost_with_wbs_breakdown(self, service):
        """Should include WBS breakdown with top-level elements."""
        from unittest.mock import AsyncMock, patch

        # Mock assignments (empty for simplicity)
        assignments_mock = MagicMock()
        assignments_mock.scalars.return_value.all.return_value = []

        # Mock WBS elements
        wbs1 = MagicMock()
        wbs1.id = uuid4()
        wbs2 = MagicMock()
        wbs2.id = uuid4()

        wbs_mock = MagicMock()
        wbs_mock.scalars.return_value.all.return_value = [wbs1, wbs2]

        service.db.execute = AsyncMock(side_effect=[assignments_mock, wbs_mock])

        # Mock WBS cost calculations
        wbs_cost1 = WBSCostSummary(
            wbs_id=wbs1.id,
            wbs_code="1.0",
            wbs_name="Engineering",
            planned_cost=Decimal("10000.00"),
            actual_cost=Decimal("8000.00"),
            cost_variance=Decimal("2000.00"),
            activity_count=5,
        )
        wbs_cost2 = WBSCostSummary(
            wbs_id=wbs2.id,
            wbs_code="2.0",
            wbs_name="Manufacturing",
            planned_cost=Decimal("20000.00"),
            actual_cost=Decimal("18000.00"),
            cost_variance=Decimal("2000.00"),
            activity_count=10,
        )

        with patch.object(service, "calculate_wbs_cost") as mock_wbs_cost:
            mock_wbs_cost.side_effect = [wbs_cost1, wbs_cost2]

            result = await service.calculate_program_cost(uuid4())

            assert len(result.wbs_breakdown) == 2
            mock_wbs_cost.assert_any_call(wbs1.id, include_children=True)
            mock_wbs_cost.assert_any_call(wbs2.id, include_children=True)


class TestSyncEvmsAcwpAsync:
    """Async tests for sync_evms_acwp method."""

    @pytest.fixture
    def service(self):
        """Create service with mocked db."""
        from unittest.mock import AsyncMock

        db = AsyncMock()
        db.commit = AsyncMock()
        db.add = MagicMock()
        return ResourceCostService(db)

    @pytest.mark.asyncio
    async def test_sync_period_not_found(self, service):
        """Should return failure when period not found."""
        from unittest.mock import AsyncMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.sync_evms_acwp(uuid4(), uuid4())

        assert result.success is False
        assert "Period not found" in result.warnings

    @pytest.mark.asyncio
    async def test_sync_updates_existing_period_data(self, service):
        """Should update existing EVMSPeriodData records."""
        from unittest.mock import AsyncMock, patch

        period_id = uuid4()
        program_id = uuid4()
        wbs_id = uuid4()

        # Mock period
        mock_period = MagicMock()
        mock_period.id = period_id
        mock_period.cumulative_acwp = Decimal("0")

        period_result = MagicMock()
        period_result.scalar_one_or_none.return_value = mock_period

        # Mock existing period data
        mock_period_data = MagicMock()
        mock_period_data.wbs_id = wbs_id
        mock_period_data.acwp = Decimal("0")

        period_data_mock = MagicMock()
        period_data_mock.scalars.return_value.all.return_value = [mock_period_data]

        # Mock WBS elements
        mock_wbs = MagicMock()
        mock_wbs.id = wbs_id

        wbs_mock = MagicMock()
        wbs_mock.scalars.return_value.all.return_value = [mock_wbs]

        service.db.execute = AsyncMock(side_effect=[period_result, period_data_mock, wbs_mock])

        # Mock WBS cost
        wbs_cost = WBSCostSummary(
            wbs_id=wbs_id,
            wbs_code="1.0",
            wbs_name="Test",
            planned_cost=Decimal("10000.00"),
            actual_cost=Decimal("5000.00"),
            cost_variance=Decimal("5000.00"),
            activity_count=5,
        )

        with patch.object(service, "calculate_wbs_cost", return_value=wbs_cost):
            result = await service.sync_evms_acwp(program_id, period_id)

            assert result.success is True
            assert result.wbs_elements_updated == 1
            assert result.acwp_updated == Decimal("5000.00")
            assert mock_period_data.acwp == Decimal("5000.00")

    @pytest.mark.asyncio
    async def test_sync_creates_new_period_data(self, service):
        """Should create new EVMSPeriodData when not exists."""
        from unittest.mock import AsyncMock, patch

        period_id = uuid4()
        program_id = uuid4()
        wbs_id = uuid4()

        # Mock period
        mock_period = MagicMock()
        mock_period.id = period_id

        period_result = MagicMock()
        period_result.scalar_one_or_none.return_value = mock_period

        # No existing period data
        period_data_mock = MagicMock()
        period_data_mock.scalars.return_value.all.return_value = []

        # Mock WBS element not in period data
        mock_wbs = MagicMock()
        mock_wbs.id = wbs_id

        wbs_mock = MagicMock()
        wbs_mock.scalars.return_value.all.return_value = [mock_wbs]

        service.db.execute = AsyncMock(side_effect=[period_result, period_data_mock, wbs_mock])

        # Mock WBS cost
        wbs_cost = WBSCostSummary(
            wbs_id=wbs_id,
            wbs_code="1.0",
            wbs_name="Test",
            planned_cost=Decimal("10000.00"),
            actual_cost=Decimal("3000.00"),
            cost_variance=Decimal("7000.00"),
            activity_count=3,
        )

        with patch.object(service, "calculate_wbs_cost", return_value=wbs_cost):
            result = await service.sync_evms_acwp(program_id, period_id)

            assert result.success is True
            assert result.wbs_elements_updated == 1
            # Should have called db.add for new period data
            service.db.add.assert_called_once()


class TestCalculateWbsCostWithActivities:
    """Tests for calculate_wbs_cost with activity loops."""

    @pytest.fixture
    def service(self):
        """Create service with mocked db."""
        from unittest.mock import AsyncMock

        db = AsyncMock()
        return ResourceCostService(db)

    @pytest.mark.asyncio
    async def test_wbs_cost_without_children(self, service):
        """Should calculate WBS cost excluding children."""
        from unittest.mock import AsyncMock, patch

        wbs_id = uuid4()

        # Mock WBS - use include_children=False to avoid ltree query
        mock_wbs = MagicMock()
        mock_wbs.id = wbs_id
        mock_wbs.wbs_code = "1.0"
        mock_wbs.name = "Test WBS"

        wbs_result = MagicMock()
        wbs_result.scalar_one_or_none.return_value = mock_wbs

        # Mock activities
        activity1 = MagicMock()
        activity1.id = uuid4()
        activity2 = MagicMock()
        activity2.id = uuid4()
        activity3 = MagicMock()
        activity3.id = uuid4()

        activities_mock = MagicMock()
        activities_mock.scalars.return_value.all.return_value = [
            activity1,
            activity2,
            activity3,
        ]

        service.db.execute = AsyncMock(side_effect=[wbs_result, activities_mock])

        # Mock activity costs
        cost1 = ActivityCostSummary(
            activity_id=activity1.id,
            activity_code="A-001",
            activity_name="Activity 1",
            planned_cost=Decimal("1000.00"),
            actual_cost=Decimal("800.00"),
            cost_variance=Decimal("200.00"),
            percent_spent=Decimal("80.00"),
            resource_breakdown=[],
        )
        cost2 = ActivityCostSummary(
            activity_id=activity2.id,
            activity_code="A-002",
            activity_name="Activity 2",
            planned_cost=Decimal("2000.00"),
            actual_cost=Decimal("2500.00"),
            cost_variance=Decimal("-500.00"),
            percent_spent=Decimal("125.00"),
            resource_breakdown=[],
        )
        cost3 = ActivityCostSummary(
            activity_id=activity3.id,
            activity_code="A-003",
            activity_name="Activity 3",
            planned_cost=Decimal("500.00"),
            actual_cost=Decimal("400.00"),
            cost_variance=Decimal("100.00"),
            percent_spent=Decimal("80.00"),
            resource_breakdown=[],
        )

        with patch.object(service, "calculate_activity_cost") as mock_activity_cost:
            mock_activity_cost.side_effect = [cost1, cost2, cost3]

            # Use include_children=False to avoid ltree path query
            result = await service.calculate_wbs_cost(wbs_id, include_children=False)

            assert result.planned_cost == Decimal("3500.00")
            assert result.actual_cost == Decimal("3700.00")
            assert result.activity_count == 3
            assert mock_activity_cost.call_count == 3


class TestCostCalculationScenarios:
    """Integration-style tests for cost calculation scenarios."""

    def test_mixed_resource_types_cost(self):
        """Test calculating costs for mixed resource types."""
        # Labor cost
        labor_hours = Decimal("160")
        labor_rate = Decimal("125.00")
        labor_cost = labor_hours * labor_rate  # 20000.00

        # Equipment cost
        equipment_hours = Decimal("40")
        equipment_rate = Decimal("75.00")
        equipment_cost = equipment_hours * equipment_rate  # 3000.00

        # Material cost
        material_qty = Decimal("500")
        material_unit_cost = Decimal("5.00")
        material_cost = material_qty * material_unit_cost  # 2500.00

        total = labor_cost + equipment_cost + material_cost
        assert ResourceCostService._round(total) == Decimal("25500.00")

    def test_cost_rollup_multiple_assignments(self):
        """Test cost rollup from multiple assignments."""
        costs = [
            Decimal("1500.00"),
            Decimal("2300.50"),
            Decimal("800.75"),
            Decimal("1200.25"),
        ]

        total = sum(costs)
        assert ResourceCostService._round(total) == Decimal("5801.50")

    def test_variance_percentage_calculation(self):
        """Test cost variance as percentage of budget."""
        planned = Decimal("100000.00")
        actual = Decimal("92500.00")
        variance = planned - actual
        variance_percent = (variance / planned) * 100

        assert ResourceCostService._round(variance) == Decimal("7500.00")
        assert ResourceCostService._round(variance_percent) == Decimal("7.50")
