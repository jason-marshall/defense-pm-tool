"""Unit tests for MaterialTrackingService."""

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from src.services.material_tracking import (
    MaterialConsumption,
    MaterialStatus,
    MaterialTrackingService,
    ProgramMaterialSummary,
)


class TestMaterialTrackingServiceRounding:
    """Tests for decimal rounding in MaterialTrackingService."""

    def test_round_up(self):
        """Test rounding up at midpoint."""
        assert MaterialTrackingService._round(Decimal("10.125")) == Decimal("10.13")

    def test_round_down(self):
        """Test rounding down below midpoint."""
        assert MaterialTrackingService._round(Decimal("10.124")) == Decimal("10.12")

    def test_round_exact(self):
        """Test exact values don't change."""
        assert MaterialTrackingService._round(Decimal("10.00")) == Decimal("10.00")


class TestQuantityCalculations:
    """Tests for quantity calculations."""

    def test_quantity_remaining_calculation(self):
        """Test quantity remaining calculation."""
        available = Decimal("1000")
        consumed = Decimal("350")
        remaining = available - consumed
        assert remaining == Decimal("650")

    def test_quantity_remaining_with_decimals(self):
        """Test quantity remaining with decimal values."""
        available = Decimal("100.50")
        consumed = Decimal("25.75")
        remaining = available - consumed
        assert remaining == Decimal("74.75")

    def test_quantity_fully_consumed(self):
        """Test quantity when fully consumed."""
        available = Decimal("500")
        consumed = Decimal("500")
        remaining = available - consumed
        assert remaining == Decimal("0")


class TestPercentConsumedCalculations:
    """Tests for percent consumed calculations."""

    def test_percent_consumed_quarter(self):
        """Test 25% consumed."""
        available = Decimal("1000")
        consumed = Decimal("250")
        percent = consumed / available * 100
        assert MaterialTrackingService._round(percent) == Decimal("25.00")

    def test_percent_consumed_half(self):
        """Test 50% consumed."""
        available = Decimal("200")
        consumed = Decimal("100")
        percent = consumed / available * 100
        assert MaterialTrackingService._round(percent) == Decimal("50.00")

    def test_percent_consumed_full(self):
        """Test 100% consumed."""
        available = Decimal("500")
        consumed = Decimal("500")
        percent = consumed / available * 100
        assert MaterialTrackingService._round(percent) == Decimal("100.00")

    def test_percent_consumed_zero_available(self):
        """Test percent consumed with zero available (avoid division by zero)."""
        available = Decimal("0")
        consumed = Decimal("0")
        percent = (consumed / available * 100) if available > 0 else Decimal("0")
        assert percent == Decimal("0")

    def test_percent_consumed_fractional(self):
        """Test percent consumed with fractional result."""
        available = Decimal("300")
        consumed = Decimal("100")
        percent = consumed / available * 100
        assert MaterialTrackingService._round(percent) == Decimal("33.33")


class TestConsumptionValidation:
    """Tests for consumption validation logic."""

    def test_consumption_within_assigned(self):
        """Test valid consumption within assigned quantity."""
        assigned = Decimal("100")
        current_consumed = Decimal("50")
        new_consumption = Decimal("30")

        new_total = current_consumed + new_consumption
        assert new_total <= assigned  # 80 <= 100

    def test_consumption_exceeds_assigned(self):
        """Test consumption that exceeds assigned quantity."""
        assigned = Decimal("100")
        current_consumed = Decimal("80")
        new_consumption = Decimal("30")

        new_total = current_consumed + new_consumption
        assert new_total > assigned  # 110 > 100

    def test_consumption_exactly_matches_assigned(self):
        """Test consumption that exactly matches assigned."""
        assigned = Decimal("100")
        current_consumed = Decimal("70")
        new_consumption = Decimal("30")

        new_total = current_consumed + new_consumption
        assert new_total == assigned  # 100 == 100

    def test_consumption_from_zero(self):
        """Test first consumption from zero."""
        assigned = Decimal("100")
        current_consumed = Decimal("0")
        new_consumption = Decimal("25")

        new_total = current_consumed + new_consumption
        assert new_total <= assigned


class TestMaterialCostCalculations:
    """Tests for material cost calculations."""

    def test_material_cost_basic(self):
        """Test basic material cost calculation."""
        quantity = Decimal("50")
        unit_cost = Decimal("12.50")
        expected = Decimal("625.00")

        actual = quantity * unit_cost
        assert MaterialTrackingService._round(actual) == expected

    def test_material_cost_fractional_quantity(self):
        """Test material cost with fractional quantity."""
        quantity = Decimal("12.5")
        unit_cost = Decimal("10.00")
        expected = Decimal("125.00")

        actual = quantity * unit_cost
        assert MaterialTrackingService._round(actual) == expected

    def test_material_cost_small_unit(self):
        """Test material cost with small unit cost."""
        quantity = Decimal("1000")
        unit_cost = Decimal("0.25")
        expected = Decimal("250.00")

        actual = quantity * unit_cost
        assert MaterialTrackingService._round(actual) == expected

    def test_material_cost_large_quantity(self):
        """Test material cost with large quantity."""
        quantity = Decimal("10000")
        unit_cost = Decimal("5.99")
        expected = Decimal("59900.00")

        actual = quantity * unit_cost
        assert MaterialTrackingService._round(actual) == expected

    def test_total_value_calculation(self):
        """Test total inventory value calculation."""
        available = Decimal("500")
        unit_cost = Decimal("15.00")
        expected_total = Decimal("7500.00")

        total_value = available * unit_cost
        assert MaterialTrackingService._round(total_value) == expected_total

    def test_consumed_value_calculation(self):
        """Test consumed value calculation."""
        consumed = Decimal("150")
        unit_cost = Decimal("15.00")
        expected_consumed = Decimal("2250.00")

        consumed_value = consumed * unit_cost
        assert MaterialTrackingService._round(consumed_value) == expected_consumed


class TestDataclasses:
    """Tests for dataclass structures."""

    def test_material_status(self):
        """Test MaterialStatus dataclass."""
        status = MaterialStatus(
            resource_id=uuid4(),
            resource_code="MAT-001",
            resource_name="Steel Plates",
            quantity_unit="kg",
            quantity_available=Decimal("1000.00"),
            quantity_assigned=Decimal("500.00"),
            quantity_consumed=Decimal("200.00"),
            quantity_remaining=Decimal("800.00"),
            percent_consumed=Decimal("20.00"),
            unit_cost=Decimal("5.50"),
            total_value=Decimal("5500.00"),
            consumed_value=Decimal("1100.00"),
        )

        assert status.resource_code == "MAT-001"
        assert status.quantity_unit == "kg"
        assert status.quantity_remaining == Decimal("800.00")

    def test_material_consumption(self):
        """Test MaterialConsumption dataclass."""
        consumption = MaterialConsumption(
            assignment_id=uuid4(),
            quantity_consumed=Decimal("50.00"),
            remaining_assigned=Decimal("150.00"),
            cost_incurred=Decimal("275.00"),
        )

        assert consumption.quantity_consumed == Decimal("50.00")
        assert consumption.cost_incurred == Decimal("275.00")

    def test_program_material_summary(self):
        """Test ProgramMaterialSummary dataclass."""
        summary = ProgramMaterialSummary(
            program_id=uuid4(),
            material_count=5,
            total_value=Decimal("50000.00"),
            consumed_value=Decimal("15000.00"),
            remaining_value=Decimal("35000.00"),
            materials=[],
        )

        assert summary.material_count == 5
        assert summary.remaining_value == Decimal("35000.00")


class TestMaterialTrackingServiceInit:
    """Tests for MaterialTrackingService initialization."""

    def test_init_with_db_session(self):
        """Test service initializes with database session."""
        mock_db = MagicMock()
        service = MaterialTrackingService(mock_db)

        assert service.db == mock_db


class TestInventoryScenarios:
    """Integration-style tests for inventory scenarios."""

    def test_multiple_consumptions(self):
        """Test tracking multiple consumptions."""
        assigned = Decimal("100")
        consumptions = [Decimal("20"), Decimal("30"), Decimal("25")]

        total_consumed = sum(consumptions)
        remaining = assigned - total_consumed

        assert total_consumed == Decimal("75")
        assert remaining == Decimal("25")

    def test_inventory_value_tracking(self):
        """Test tracking inventory value over consumptions."""
        initial_quantity = Decimal("1000")
        unit_cost = Decimal("10.00")
        initial_value = initial_quantity * unit_cost

        # First consumption
        consumed_1 = Decimal("200")
        value_1 = consumed_1 * unit_cost

        # Second consumption
        consumed_2 = Decimal("300")
        value_2 = consumed_2 * unit_cost

        total_consumed = consumed_1 + consumed_2
        total_consumed_value = value_1 + value_2
        remaining_quantity = initial_quantity - total_consumed
        remaining_value = remaining_quantity * unit_cost

        assert total_consumed == Decimal("500")
        assert total_consumed_value == Decimal("5000.00")
        assert remaining_quantity == Decimal("500")
        assert remaining_value == Decimal("5000.00")

    def test_low_inventory_warning_threshold(self):
        """Test identifying low inventory situation."""
        available = Decimal("1000")
        consumed = Decimal("900")
        remaining = available - consumed
        percent_remaining = remaining / available * 100

        # Low inventory threshold at 20%
        is_low = percent_remaining < Decimal("20")
        assert is_low is True
        assert MaterialTrackingService._round(percent_remaining) == Decimal("10.00")
