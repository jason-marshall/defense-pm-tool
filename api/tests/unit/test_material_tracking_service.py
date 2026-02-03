"""Unit tests for MaterialTrackingService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.enums import ResourceType
from src.services.material_tracking import (
    MaterialStatus,
    MaterialTrackingService,
)


class TestGetMaterialStatus:
    """Tests for get_material_status method."""

    @pytest.mark.asyncio
    async def test_get_material_status_success(self):
        """Should return material status with calculated values."""
        mock_db = AsyncMock()
        resource_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "MAT-001"
        mock_resource.name = "Steel"
        mock_resource.quantity_unit = "tons"
        mock_resource.quantity_available = Decimal("100.00")
        mock_resource.unit_cost = Decimal("500.00")
        mock_resource.resource_type = ResourceType.MATERIAL

        mock_assignment1 = MagicMock()
        mock_assignment1.deleted_at = None
        mock_assignment1.quantity_assigned = Decimal("50.00")
        mock_assignment1.quantity_consumed = Decimal("25.00")

        mock_assignment2 = MagicMock()
        mock_assignment2.deleted_at = None
        mock_assignment2.quantity_assigned = Decimal("30.00")
        mock_assignment2.quantity_consumed = Decimal("10.00")

        mock_resource.assignments = [mock_assignment1, mock_assignment2]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resource
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)
        status = await service.get_material_status(resource_id)

        assert status.resource_id == resource_id
        assert status.resource_code == "MAT-001"
        assert status.quantity_available == Decimal("100.00")
        assert status.quantity_assigned == Decimal("80.00")  # 50 + 30
        assert status.quantity_consumed == Decimal("35.00")  # 25 + 10

    @pytest.mark.asyncio
    async def test_get_material_status_not_found(self):
        """Should raise ValueError when resource not found."""
        mock_db = AsyncMock()
        resource_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            await service.get_material_status(resource_id)

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_material_status_wrong_type(self):
        """Should raise ValueError when resource is not MATERIAL type."""
        mock_db = AsyncMock()
        resource_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.resource_type = ResourceType.LABOR

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resource
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            await service.get_material_status(resource_id)

        assert "not a MATERIAL type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_material_status_deleted_assignments_skipped(self):
        """Should skip deleted assignments in calculations."""
        mock_db = AsyncMock()
        resource_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "MAT-002"
        mock_resource.name = "Aluminum"
        mock_resource.quantity_unit = None  # Test default unit
        mock_resource.quantity_available = Decimal("200.00")
        mock_resource.unit_cost = Decimal("100.00")
        mock_resource.resource_type = ResourceType.MATERIAL

        # Active assignment
        mock_assignment1 = MagicMock()
        mock_assignment1.deleted_at = None
        mock_assignment1.quantity_assigned = Decimal("50.00")
        mock_assignment1.quantity_consumed = Decimal("25.00")

        # Deleted assignment - should be skipped
        mock_assignment2 = MagicMock()
        mock_assignment2.deleted_at = MagicMock()  # Not None
        mock_assignment2.quantity_assigned = Decimal("100.00")
        mock_assignment2.quantity_consumed = Decimal("100.00")

        mock_resource.assignments = [mock_assignment1, mock_assignment2]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resource
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)
        status = await service.get_material_status(resource_id)

        # Only active assignment should be counted
        assert status.quantity_assigned == Decimal("50.00")
        assert status.quantity_consumed == Decimal("25.00")
        assert status.quantity_unit == "units"  # Default

    @pytest.mark.asyncio
    async def test_get_material_status_zero_quantity(self):
        """Should handle zero quantity without division error."""
        mock_db = AsyncMock()
        resource_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "MAT-003"
        mock_resource.name = "Copper"
        mock_resource.quantity_unit = "kg"
        mock_resource.quantity_available = Decimal("0")
        mock_resource.unit_cost = None  # Test None unit_cost
        mock_resource.resource_type = ResourceType.MATERIAL
        mock_resource.assignments = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resource
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)
        status = await service.get_material_status(resource_id)

        assert status.percent_consumed == Decimal("0")
        assert status.unit_cost == Decimal("0")


class TestConsumeMaterial:
    """Tests for consume_material method."""

    @pytest.mark.asyncio
    async def test_consume_material_success(self):
        """Should record material consumption."""
        mock_db = AsyncMock()
        assignment_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.resource_type = ResourceType.MATERIAL
        mock_resource.unit_cost = Decimal("100.00")

        mock_assignment = MagicMock()
        mock_assignment.id = assignment_id
        mock_assignment.quantity_assigned = Decimal("50.00")
        mock_assignment.quantity_consumed = Decimal("10.00")
        mock_assignment.actual_cost = Decimal("1000.00")
        mock_assignment.resource = mock_resource

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)
        result = await service.consume_material(assignment_id, Decimal("5.00"))

        assert result.assignment_id == assignment_id
        assert result.quantity_consumed == Decimal("15.00")  # 10 + 5
        assert result.remaining_assigned == Decimal("35.00")  # 50 - 15
        assert result.cost_incurred == Decimal("500.00")  # 5 * 100

    @pytest.mark.asyncio
    async def test_consume_material_not_found(self):
        """Should raise ValueError when assignment not found."""
        mock_db = AsyncMock()
        assignment_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            await service.consume_material(assignment_id, Decimal("5.00"))

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_consume_material_wrong_type(self):
        """Should raise ValueError for non-material resource."""
        mock_db = AsyncMock()
        assignment_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.resource_type = ResourceType.LABOR

        mock_assignment = MagicMock()
        mock_assignment.resource = mock_resource

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            await service.consume_material(assignment_id, Decimal("5.00"))

        assert "material resources" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_consume_material_exceeds_assigned(self):
        """Should raise ValueError when consumption exceeds assignment."""
        mock_db = AsyncMock()
        assignment_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.resource_type = ResourceType.MATERIAL

        mock_assignment = MagicMock()
        mock_assignment.quantity_assigned = Decimal("10.00")
        mock_assignment.quantity_consumed = Decimal("5.00")
        mock_assignment.resource = mock_resource

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            await service.consume_material(assignment_id, Decimal("10.00"))

        assert "exceed assigned" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_consume_material_none_values(self):
        """Should handle None values in assignment."""
        mock_db = AsyncMock()
        assignment_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.resource_type = ResourceType.MATERIAL
        mock_resource.unit_cost = None  # None unit cost

        mock_assignment = MagicMock()
        mock_assignment.id = assignment_id
        mock_assignment.quantity_assigned = Decimal("50.00")
        mock_assignment.quantity_consumed = None  # None consumed
        mock_assignment.actual_cost = Decimal("0")
        mock_assignment.resource = mock_resource

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)
        result = await service.consume_material(assignment_id, Decimal("5.00"))

        assert result.quantity_consumed == Decimal("5.00")
        assert result.cost_incurred == Decimal("0")  # 5 * 0


class TestGetProgramMaterials:
    """Tests for get_program_materials method."""

    @pytest.mark.asyncio
    async def test_get_program_materials_success(self):
        """Should return program materials summary."""
        mock_db = AsyncMock()
        program_id = uuid4()

        material1_id = uuid4()
        material2_id = uuid4()

        mock_material1 = MagicMock()
        mock_material1.id = material1_id

        mock_material2 = MagicMock()
        mock_material2.id = material2_id

        # First call returns materials list
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_material1, mock_material2]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)

        # Mock get_material_status calls
        status1 = MaterialStatus(
            resource_id=material1_id,
            resource_code="MAT-001",
            resource_name="Steel",
            quantity_unit="tons",
            quantity_available=Decimal("100.00"),
            quantity_assigned=Decimal("50.00"),
            quantity_consumed=Decimal("25.00"),
            quantity_remaining=Decimal("75.00"),
            percent_consumed=Decimal("25.00"),
            unit_cost=Decimal("500.00"),
            total_value=Decimal("50000.00"),
            consumed_value=Decimal("12500.00"),
        )

        status2 = MaterialStatus(
            resource_id=material2_id,
            resource_code="MAT-002",
            resource_name="Aluminum",
            quantity_unit="kg",
            quantity_available=Decimal("200.00"),
            quantity_assigned=Decimal("100.00"),
            quantity_consumed=Decimal("50.00"),
            quantity_remaining=Decimal("150.00"),
            percent_consumed=Decimal("25.00"),
            unit_cost=Decimal("100.00"),
            total_value=Decimal("20000.00"),
            consumed_value=Decimal("5000.00"),
        )

        with patch.object(service, "get_material_status") as mock_get_status:
            mock_get_status.side_effect = [status1, status2]

            result = await service.get_program_materials(program_id)

            assert result.program_id == program_id
            assert result.material_count == 2
            assert result.total_value == Decimal("70000.00")
            assert result.consumed_value == Decimal("17500.00")
            assert result.remaining_value == Decimal("52500.00")
            assert len(result.materials) == 2

    @pytest.mark.asyncio
    async def test_get_program_materials_empty(self):
        """Should return empty summary when no materials."""
        mock_db = AsyncMock()
        program_id = uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)
        result = await service.get_program_materials(program_id)

        assert result.material_count == 0
        assert result.total_value == Decimal("0")
        assert result.consumed_value == Decimal("0")
        assert result.remaining_value == Decimal("0")
        assert len(result.materials) == 0


class TestValidateMaterialAssignment:
    """Tests for validate_material_assignment method."""

    @pytest.mark.asyncio
    async def test_validate_assignment_success(self):
        """Should return True when quantity is available."""
        mock_db = AsyncMock()
        resource_id = uuid4()

        service = MaterialTrackingService(mock_db)

        status = MaterialStatus(
            resource_id=resource_id,
            resource_code="MAT-001",
            resource_name="Steel",
            quantity_unit="tons",
            quantity_available=Decimal("100.00"),
            quantity_assigned=Decimal("50.00"),
            quantity_consumed=Decimal("0"),
            quantity_remaining=Decimal("50.00"),
            percent_consumed=Decimal("0"),
            unit_cost=Decimal("500.00"),
            total_value=Decimal("50000.00"),
            consumed_value=Decimal("0"),
        )

        with patch.object(service, "get_material_status", return_value=status):
            result = await service.validate_material_assignment(resource_id, Decimal("25.00"))
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_assignment_exceeds_available(self):
        """Should raise ValueError when quantity exceeds available."""
        mock_db = AsyncMock()
        resource_id = uuid4()

        service = MaterialTrackingService(mock_db)

        status = MaterialStatus(
            resource_id=resource_id,
            resource_code="MAT-001",
            resource_name="Steel",
            quantity_unit="tons",
            quantity_available=Decimal("100.00"),
            quantity_assigned=Decimal("90.00"),
            quantity_consumed=Decimal("80.00"),
            quantity_remaining=Decimal("20.00"),
            percent_consumed=Decimal("80.00"),
            unit_cost=Decimal("500.00"),
            total_value=Decimal("50000.00"),
            consumed_value=Decimal("40000.00"),
        )

        with patch.object(service, "get_material_status", return_value=status):
            with pytest.raises(ValueError) as exc_info:
                await service.validate_material_assignment(resource_id, Decimal("30.00"))

            assert "exceeds available" in str(exc_info.value)


class TestUpdateMaterialInventory:
    """Tests for update_material_inventory method."""

    @pytest.mark.asyncio
    async def test_update_inventory_quantity_only(self):
        """Should update inventory quantity."""
        mock_db = AsyncMock()
        resource_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.resource_type = ResourceType.MATERIAL

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resource
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)

        expected_status = MaterialStatus(
            resource_id=resource_id,
            resource_code="MAT-001",
            resource_name="Steel",
            quantity_unit="tons",
            quantity_available=Decimal("150.00"),
            quantity_assigned=Decimal("0"),
            quantity_consumed=Decimal("0"),
            quantity_remaining=Decimal("150.00"),
            percent_consumed=Decimal("0"),
            unit_cost=Decimal("500.00"),
            total_value=Decimal("75000.00"),
            consumed_value=Decimal("0"),
        )

        with patch.object(service, "get_material_status", return_value=expected_status):
            result = await service.update_material_inventory(resource_id, Decimal("150.00"))

            assert mock_resource.quantity_available == Decimal("150.00")
            assert result.quantity_available == Decimal("150.00")
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_inventory_with_unit_cost(self):
        """Should update inventory with new unit cost."""
        mock_db = AsyncMock()
        resource_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.resource_type = ResourceType.MATERIAL

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resource
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)

        expected_status = MaterialStatus(
            resource_id=resource_id,
            resource_code="MAT-001",
            resource_name="Steel",
            quantity_unit="tons",
            quantity_available=Decimal("200.00"),
            quantity_assigned=Decimal("0"),
            quantity_consumed=Decimal("0"),
            quantity_remaining=Decimal("200.00"),
            percent_consumed=Decimal("0"),
            unit_cost=Decimal("600.00"),
            total_value=Decimal("120000.00"),
            consumed_value=Decimal("0"),
        )

        with patch.object(service, "get_material_status", return_value=expected_status):
            result = await service.update_material_inventory(
                resource_id,
                Decimal("200.00"),
                unit_cost=Decimal("600.00"),
            )

            assert mock_resource.quantity_available == Decimal("200.00")
            assert mock_resource.unit_cost == Decimal("600.00")
            assert result.unit_cost == Decimal("600.00")

    @pytest.mark.asyncio
    async def test_update_inventory_not_found(self):
        """Should raise ValueError when resource not found."""
        mock_db = AsyncMock()
        resource_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            await service.update_material_inventory(resource_id, Decimal("100.00"))

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_inventory_wrong_type(self):
        """Should raise ValueError for non-material resource."""
        mock_db = AsyncMock()
        resource_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.resource_type = ResourceType.EQUIPMENT

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resource
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            await service.update_material_inventory(resource_id, Decimal("100.00"))

        assert "not a MATERIAL type" in str(exc_info.value)


class TestGetMaterialAssignmentStatus:
    """Tests for get_material_assignment_status method."""

    @pytest.mark.asyncio
    async def test_get_assignment_status_success(self):
        """Should return detailed assignment status."""
        mock_db = AsyncMock()
        assignment_id = uuid4()
        resource_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "MAT-001"
        mock_resource.name = "Steel"
        mock_resource.quantity_unit = "tons"
        mock_resource.unit_cost = Decimal("500.00")
        mock_resource.resource_type = ResourceType.MATERIAL

        mock_assignment = MagicMock()
        mock_assignment.id = assignment_id
        mock_assignment.quantity_assigned = Decimal("50.00")
        mock_assignment.quantity_consumed = Decimal("20.00")
        mock_assignment.resource = mock_resource

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)
        result = await service.get_material_assignment_status(assignment_id)

        assert result["assignment_id"] == str(assignment_id)
        assert result["resource_id"] == str(resource_id)
        assert result["resource_code"] == "MAT-001"
        assert result["quantity_assigned"] == Decimal("50.00")
        assert result["quantity_consumed"] == Decimal("20.00")
        assert result["quantity_remaining"] == Decimal("30.00")
        assert result["percent_consumed"] == Decimal("40.00")

    @pytest.mark.asyncio
    async def test_get_assignment_status_not_found(self):
        """Should raise ValueError when assignment not found."""
        mock_db = AsyncMock()
        assignment_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            await service.get_material_assignment_status(assignment_id)

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_assignment_status_wrong_type(self):
        """Should raise ValueError for non-material assignment."""
        mock_db = AsyncMock()
        assignment_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.resource_type = ResourceType.LABOR

        mock_assignment = MagicMock()
        mock_assignment.resource = mock_resource

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            await service.get_material_assignment_status(assignment_id)

        assert "not for a material resource" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_assignment_status_with_none_values(self):
        """Should handle None values in assignment."""
        mock_db = AsyncMock()
        assignment_id = uuid4()
        resource_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "MAT-002"
        mock_resource.name = "Aluminum"
        mock_resource.quantity_unit = None  # Default
        mock_resource.unit_cost = None  # None
        mock_resource.resource_type = ResourceType.MATERIAL

        mock_assignment = MagicMock()
        mock_assignment.id = assignment_id
        mock_assignment.quantity_assigned = None  # None
        mock_assignment.quantity_consumed = None  # None
        mock_assignment.resource = mock_resource

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment
        mock_db.execute.return_value = mock_result

        service = MaterialTrackingService(mock_db)
        result = await service.get_material_assignment_status(assignment_id)

        assert result["quantity_unit"] == "units"  # Default
        assert result["quantity_assigned"] == Decimal("0")
        assert result["quantity_consumed"] == Decimal("0")
        assert result["percent_consumed"] == Decimal("0")  # No division by zero


class TestRoundMethod:
    """Tests for the _round static method."""

    def test_round_to_two_decimals(self):
        """Should round to 2 decimal places."""
        assert MaterialTrackingService._round(Decimal("100.125")) == Decimal("100.13")
        assert MaterialTrackingService._round(Decimal("100.124")) == Decimal("100.12")
        assert MaterialTrackingService._round(Decimal("100.1")) == Decimal("100.10")
