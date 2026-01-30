"""Unit tests for ResourceCostService."""

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

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
