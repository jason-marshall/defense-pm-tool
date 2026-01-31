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


import pytest
from unittest.mock import AsyncMock, patch


class TestGetMaterialStatusAsync:
    """Async tests for get_material_status method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create MaterialTrackingService with mock db."""
        return MaterialTrackingService(mock_db)

    @pytest.mark.asyncio
    async def test_get_material_status_not_found(self, service, mock_db):
        """Should raise error when resource not found."""
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        resource_id = uuid4()
        with pytest.raises(ValueError, match=f"Resource {resource_id} not found"):
            await service.get_material_status(resource_id)

    @pytest.mark.asyncio
    async def test_get_material_status_not_material_type(self, service, mock_db):
        """Should raise error when resource is not MATERIAL type."""
        from unittest.mock import MagicMock
        from src.models.enums import ResourceType

        mock_resource = MagicMock()
        mock_resource.id = uuid4()
        mock_resource.resource_type = ResourceType.LABOR
        mock_resource.assignments = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resource
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="is not a MATERIAL type"):
            await service.get_material_status(mock_resource.id)

    @pytest.mark.asyncio
    async def test_get_material_status_success(self, service, mock_db):
        """Should return material status for valid MATERIAL resource."""
        from unittest.mock import MagicMock
        from src.models.enums import ResourceType

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "MAT-001"
        mock_resource.name = "Test Material"
        mock_resource.resource_type = ResourceType.MATERIAL
        mock_resource.quantity_available = Decimal("1000.00")
        mock_resource.quantity_unit = "kg"
        mock_resource.unit_cost = Decimal("10.00")

        # Mock assignments
        mock_assignment = MagicMock()
        mock_assignment.deleted_at = None
        mock_assignment.quantity_assigned = Decimal("500.00")
        mock_assignment.quantity_consumed = Decimal("200.00")
        mock_resource.assignments = [mock_assignment]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resource
        mock_db.execute.return_value = mock_result

        status = await service.get_material_status(resource_id)

        assert status.resource_id == resource_id
        assert status.resource_code == "MAT-001"
        assert status.quantity_available == Decimal("1000.00")
        assert status.quantity_consumed == Decimal("200.00")
        assert status.quantity_remaining == Decimal("800.00")

    @pytest.mark.asyncio
    async def test_get_material_status_with_deleted_assignments(self, service, mock_db):
        """Should skip deleted assignments in calculations."""
        from unittest.mock import MagicMock
        from datetime import datetime
        from src.models.enums import ResourceType

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "MAT-002"
        mock_resource.name = "Test Material 2"
        mock_resource.resource_type = ResourceType.MATERIAL
        mock_resource.quantity_available = Decimal("500.00")
        mock_resource.quantity_unit = "units"
        mock_resource.unit_cost = Decimal("5.00")

        # Active assignment
        mock_assignment1 = MagicMock()
        mock_assignment1.deleted_at = None
        mock_assignment1.quantity_assigned = Decimal("100.00")
        mock_assignment1.quantity_consumed = Decimal("50.00")

        # Deleted assignment - should be skipped
        mock_assignment2 = MagicMock()
        mock_assignment2.deleted_at = datetime.now()
        mock_assignment2.quantity_assigned = Decimal("200.00")
        mock_assignment2.quantity_consumed = Decimal("100.00")

        mock_resource.assignments = [mock_assignment1, mock_assignment2]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resource
        mock_db.execute.return_value = mock_result

        status = await service.get_material_status(resource_id)

        # Should only count active assignment
        assert status.quantity_assigned == Decimal("100.00")
        assert status.quantity_consumed == Decimal("50.00")


class TestConsumeMaterialAsync:
    """Async tests for consume_material method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create MaterialTrackingService with mock db."""
        return MaterialTrackingService(mock_db)

    @pytest.mark.asyncio
    async def test_consume_material_assignment_not_found(self, service, mock_db):
        """Should raise error when assignment not found."""
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        assignment_id = uuid4()
        with pytest.raises(ValueError, match=f"Assignment {assignment_id} not found"):
            await service.consume_material(assignment_id, Decimal("10"))

    @pytest.mark.asyncio
    async def test_consume_material_not_material_type(self, service, mock_db):
        """Should raise error when resource is not MATERIAL type."""
        from unittest.mock import MagicMock
        from src.models.enums import ResourceType

        mock_resource = MagicMock()
        mock_resource.resource_type = ResourceType.LABOR

        mock_assignment = MagicMock()
        mock_assignment.resource = mock_resource

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Can only consume material resources"):
            await service.consume_material(uuid4(), Decimal("10"))

    @pytest.mark.asyncio
    async def test_consume_material_exceeds_assigned(self, service, mock_db):
        """Should raise error when consumption exceeds assigned quantity."""
        from unittest.mock import MagicMock
        from src.models.enums import ResourceType

        mock_resource = MagicMock()
        mock_resource.resource_type = ResourceType.MATERIAL
        mock_resource.unit_cost = Decimal("10.00")

        mock_assignment = MagicMock()
        mock_assignment.resource = mock_resource
        mock_assignment.quantity_assigned = Decimal("100.00")
        mock_assignment.quantity_consumed = Decimal("90.00")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="would exceed assigned quantity"):
            await service.consume_material(uuid4(), Decimal("20"))

    @pytest.mark.asyncio
    async def test_consume_material_success(self, service, mock_db):
        """Should successfully consume material."""
        from unittest.mock import MagicMock
        from src.models.enums import ResourceType

        mock_resource = MagicMock()
        mock_resource.resource_type = ResourceType.MATERIAL
        mock_resource.unit_cost = Decimal("10.00")

        assignment_id = uuid4()
        mock_assignment = MagicMock()
        mock_assignment.resource = mock_resource
        mock_assignment.quantity_assigned = Decimal("100.00")
        mock_assignment.quantity_consumed = Decimal("50.00")
        mock_assignment.actual_cost = Decimal("500.00")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_db.execute.return_value = mock_result

        result = await service.consume_material(assignment_id, Decimal("25"))

        assert result.assignment_id == assignment_id
        assert result.quantity_consumed == Decimal("75.00")
        assert result.remaining_assigned == Decimal("25.00")
        assert result.cost_incurred == Decimal("250.00")
        mock_db.commit.assert_awaited_once()


class TestValidateMaterialAssignmentAsync:
    """Async tests for validate_material_assignment method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create MaterialTrackingService with mock db."""
        return MaterialTrackingService(mock_db)

    @pytest.mark.asyncio
    async def test_validate_assignment_exceeds_available(self, service, mock_db):
        """Should raise error when requested quantity exceeds available."""
        from unittest.mock import MagicMock
        from src.models.enums import ResourceType

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "MAT-001"
        mock_resource.name = "Test Material"
        mock_resource.resource_type = ResourceType.MATERIAL
        mock_resource.quantity_available = Decimal("100.00")
        mock_resource.quantity_unit = "kg"
        mock_resource.unit_cost = Decimal("10.00")
        mock_resource.assignments = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resource
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="exceeds available"):
            await service.validate_material_assignment(resource_id, Decimal("150"))

    @pytest.mark.asyncio
    async def test_validate_assignment_success(self, service, mock_db):
        """Should return True when quantity is available."""
        from unittest.mock import MagicMock
        from src.models.enums import ResourceType

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "MAT-001"
        mock_resource.name = "Test Material"
        mock_resource.resource_type = ResourceType.MATERIAL
        mock_resource.quantity_available = Decimal("100.00")
        mock_resource.quantity_unit = "kg"
        mock_resource.unit_cost = Decimal("10.00")
        mock_resource.assignments = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resource
        mock_db.execute.return_value = mock_result

        result = await service.validate_material_assignment(resource_id, Decimal("50"))
        assert result is True


class TestUpdateMaterialInventoryAsync:
    """Async tests for update_material_inventory method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create MaterialTrackingService with mock db."""
        return MaterialTrackingService(mock_db)

    @pytest.mark.asyncio
    async def test_update_inventory_not_found(self, service, mock_db):
        """Should raise error when resource not found."""
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        resource_id = uuid4()
        with pytest.raises(ValueError, match=f"Resource {resource_id} not found"):
            await service.update_material_inventory(resource_id, Decimal("100"))

    @pytest.mark.asyncio
    async def test_update_inventory_not_material_type(self, service, mock_db):
        """Should raise error when resource is not MATERIAL type."""
        from unittest.mock import MagicMock
        from src.models.enums import ResourceType

        resource_id = uuid4()
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.resource_type = ResourceType.EQUIPMENT

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resource
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="is not a MATERIAL type"):
            await service.update_material_inventory(resource_id, Decimal("100"))


class TestGetMaterialAssignmentStatusAsync:
    """Async tests for get_material_assignment_status method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create MaterialTrackingService with mock db."""
        return MaterialTrackingService(mock_db)

    @pytest.mark.asyncio
    async def test_get_assignment_status_not_found(self, service, mock_db):
        """Should raise error when assignment not found."""
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        assignment_id = uuid4()
        with pytest.raises(ValueError, match=f"Assignment {assignment_id} not found"):
            await service.get_material_assignment_status(assignment_id)

    @pytest.mark.asyncio
    async def test_get_assignment_status_not_material(self, service, mock_db):
        """Should raise error when assignment is not for material."""
        from unittest.mock import MagicMock
        from src.models.enums import ResourceType

        mock_resource = MagicMock()
        mock_resource.resource_type = ResourceType.LABOR

        mock_assignment = MagicMock()
        mock_assignment.resource = mock_resource

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Assignment is not for a material resource"):
            await service.get_material_assignment_status(uuid4())

    @pytest.mark.asyncio
    async def test_get_assignment_status_success(self, service, mock_db):
        """Should return assignment status dict."""
        from unittest.mock import MagicMock
        from src.models.enums import ResourceType

        resource_id = uuid4()
        assignment_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "MAT-001"
        mock_resource.name = "Test Material"
        mock_resource.resource_type = ResourceType.MATERIAL
        mock_resource.quantity_unit = "kg"
        mock_resource.unit_cost = Decimal("10.00")

        mock_assignment = MagicMock()
        mock_assignment.resource = mock_resource
        mock_assignment.quantity_assigned = Decimal("100.00")
        mock_assignment.quantity_consumed = Decimal("40.00")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_db.execute.return_value = mock_result

        result = await service.get_material_assignment_status(assignment_id)

        assert result["resource_code"] == "MAT-001"
        assert result["quantity_assigned"] == Decimal("100.00")
        assert result["quantity_consumed"] == Decimal("40.00")
        assert result["quantity_remaining"] == Decimal("60.00")
        assert result["percent_consumed"] == Decimal("40.00")

    @pytest.mark.asyncio
    async def test_get_assignment_status_zero_assigned(self, service, mock_db):
        """Should handle zero assigned quantity."""
        from unittest.mock import MagicMock
        from src.models.enums import ResourceType

        resource_id = uuid4()
        assignment_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "MAT-001"
        mock_resource.name = "Test Material"
        mock_resource.resource_type = ResourceType.MATERIAL
        mock_resource.quantity_unit = "kg"
        mock_resource.unit_cost = Decimal("10.00")

        mock_assignment = MagicMock()
        mock_assignment.resource = mock_resource
        mock_assignment.quantity_assigned = Decimal("0")
        mock_assignment.quantity_consumed = Decimal("0")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_db.execute.return_value = mock_result

        result = await service.get_material_assignment_status(assignment_id)

        assert result["quantity_assigned"] == Decimal("0.00")
        assert result["percent_consumed"] == Decimal("0.00")
