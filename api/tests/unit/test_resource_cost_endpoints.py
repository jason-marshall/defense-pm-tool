"""Unit tests for resource cost API endpoints."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.resource_cost import (
    consume_material,
    get_activity_cost,
    get_material_status,
    get_program_cost_summary,
    get_program_materials,
    get_wbs_cost,
    record_cost_entry,
    sync_costs_to_evms,
)


class TestGetActivityCost:
    """Tests for get_activity_cost endpoint."""

    @pytest.mark.asyncio
    async def test_get_activity_cost_success(self):
        """Should return activity cost breakdown."""
        activity_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        mock_summary = MagicMock()
        mock_summary.activity_id = activity_id
        mock_summary.activity_code = "ACT-001"
        mock_summary.activity_name = "Test Activity"
        mock_summary.planned_cost = Decimal("1000.00")
        mock_summary.actual_cost = Decimal("800.00")
        mock_summary.cost_variance = Decimal("200.00")
        mock_summary.percent_spent = Decimal("80.00")
        mock_summary.resource_breakdown = []

        with patch("src.api.v1.endpoints.resource_cost.ResourceCostService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.calculate_activity_cost = AsyncMock(return_value=mock_summary)
            mock_service_class.return_value = mock_service

            result = await get_activity_cost(activity_id, mock_db, mock_user)

            assert result.activity_id == activity_id
            assert result.activity_code == "ACT-001"
            assert result.planned_cost == Decimal("1000.00")

    @pytest.mark.asyncio
    async def test_get_activity_cost_not_found(self):
        """Should raise NotFoundError when activity not found."""
        from src.core.exceptions import NotFoundError

        activity_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        with patch("src.api.v1.endpoints.resource_cost.ResourceCostService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.calculate_activity_cost = AsyncMock(
                side_effect=ValueError("Activity not found")
            )
            mock_service_class.return_value = mock_service

            with pytest.raises(NotFoundError) as exc_info:
                await get_activity_cost(activity_id, mock_db, mock_user)

            assert exc_info.value.code == "ACTIVITY_NOT_FOUND"


class TestGetWBSCost:
    """Tests for get_wbs_cost endpoint."""

    @pytest.mark.asyncio
    async def test_get_wbs_cost_success(self):
        """Should return WBS cost breakdown."""
        wbs_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        mock_summary = MagicMock()
        mock_summary.wbs_id = wbs_id
        mock_summary.wbs_code = "WBS-001"
        mock_summary.wbs_name = "Test WBS"
        mock_summary.planned_cost = Decimal("5000.00")
        mock_summary.actual_cost = Decimal("4500.00")
        mock_summary.cost_variance = Decimal("500.00")
        mock_summary.activity_count = 5

        with patch("src.api.v1.endpoints.resource_cost.ResourceCostService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.calculate_wbs_cost = AsyncMock(return_value=mock_summary)
            mock_service_class.return_value = mock_service

            result = await get_wbs_cost(wbs_id, True, mock_db, mock_user)

            assert result.wbs_id == wbs_id
            assert result.wbs_code == "WBS-001"
            assert result.activity_count == 5

    @pytest.mark.asyncio
    async def test_get_wbs_cost_not_found(self):
        """Should raise NotFoundError when WBS not found."""
        from src.core.exceptions import NotFoundError

        wbs_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        with patch("src.api.v1.endpoints.resource_cost.ResourceCostService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.calculate_wbs_cost = AsyncMock(side_effect=ValueError("WBS not found"))
            mock_service_class.return_value = mock_service

            with pytest.raises(NotFoundError) as exc_info:
                await get_wbs_cost(wbs_id, True, mock_db, mock_user)

            assert exc_info.value.code == "WBS_NOT_FOUND"


class TestGetProgramCostSummary:
    """Tests for get_program_cost_summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_program_cost_summary_success(self):
        """Should return program cost summary."""
        program_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        mock_summary = MagicMock()
        mock_summary.program_id = program_id
        mock_summary.total_planned_cost = Decimal("100000.00")
        mock_summary.total_actual_cost = Decimal("95000.00")
        mock_summary.total_cost_variance = Decimal("5000.00")
        mock_summary.labor_cost = Decimal("60000.00")
        mock_summary.equipment_cost = Decimal("20000.00")
        mock_summary.material_cost = Decimal("15000.00")
        mock_summary.resource_count = 10
        mock_summary.activity_count = 25
        mock_summary.wbs_breakdown = []

        with patch("src.api.v1.endpoints.resource_cost.ResourceCostService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.calculate_program_cost = AsyncMock(return_value=mock_summary)
            mock_service_class.return_value = mock_service

            result = await get_program_cost_summary(program_id, mock_db, mock_user)

            assert result.program_id == program_id
            assert result.total_planned_cost == Decimal("100000.00")
            assert result.resource_count == 10


class TestSyncCostsToEVMS:
    """Tests for sync_costs_to_evms endpoint."""

    @pytest.mark.asyncio
    async def test_sync_costs_to_evms_success(self):
        """Should sync costs to EVMS successfully."""
        program_id = uuid4()
        period_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        mock_result = MagicMock()
        mock_result.period_id = period_id
        mock_result.acwp_updated = Decimal("50000.00")
        mock_result.wbs_elements_updated = 5
        mock_result.success = True
        mock_result.warnings = []

        with patch("src.api.v1.endpoints.resource_cost.ResourceCostService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.sync_evms_acwp = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            result = await sync_costs_to_evms(program_id, period_id, mock_db, mock_user)

            assert result.period_id == period_id
            assert result.success is True
            assert result.wbs_elements_updated == 5


class TestRecordCostEntry:
    """Tests for record_cost_entry endpoint."""

    @pytest.mark.asyncio
    async def test_record_cost_entry_success(self):
        """Should record cost entry successfully."""
        from src.schemas.resource_cost import CostEntryCreate

        assignment_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        entry = CostEntryCreate(
            entry_date=date(2026, 1, 15),
            hours_worked=Decimal("8.0"),
            quantity_used=None,
            notes="Test entry",
        )

        mock_result = MagicMock()
        mock_result.id = uuid4()
        mock_result.assignment_id = assignment_id
        mock_result.entry_date = date(2026, 1, 15)
        mock_result.hours_worked = Decimal("8.0")
        mock_result.quantity_used = None
        mock_result.calculated_cost = Decimal("400.00")
        mock_result.notes = "Test entry"

        with patch("src.api.v1.endpoints.resource_cost.ResourceCostService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.record_cost_entry = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            with patch(
                "src.schemas.resource_cost.CostEntryResponse.model_validate"
            ) as mock_validate:
                mock_validate.return_value = MagicMock(
                    id=mock_result.id,
                    assignment_id=assignment_id,
                    entry_date=date(2026, 1, 15),
                )

                result = await record_cost_entry(assignment_id, entry, mock_db, mock_user)

                assert result.assignment_id == assignment_id

    @pytest.mark.asyncio
    async def test_record_cost_entry_invalid(self):
        """Should raise ValidationError for invalid entry."""
        from src.core.exceptions import ValidationError
        from src.schemas.resource_cost import CostEntryCreate

        assignment_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        entry = CostEntryCreate(
            entry_date=date(2026, 1, 15),
            hours_worked=Decimal("8.0"),
        )

        with patch("src.api.v1.endpoints.resource_cost.ResourceCostService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.record_cost_entry = AsyncMock(side_effect=ValueError("Invalid entry"))
            mock_service_class.return_value = mock_service

            with pytest.raises(ValidationError) as exc_info:
                await record_cost_entry(assignment_id, entry, mock_db, mock_user)

            assert exc_info.value.code == "INVALID_COST_ENTRY"


class TestGetMaterialStatus:
    """Tests for get_material_status endpoint."""

    @pytest.mark.asyncio
    async def test_get_material_status_success(self):
        """Should return material status."""
        resource_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        mock_status = MagicMock()
        mock_status.resource_id = resource_id
        mock_status.resource_code = "MAT-001"
        mock_status.resource_name = "Steel"
        mock_status.quantity_unit = "tons"
        mock_status.quantity_available = Decimal("100.00")
        mock_status.quantity_assigned = Decimal("80.00")
        mock_status.quantity_consumed = Decimal("50.00")
        mock_status.quantity_remaining = Decimal("30.00")
        mock_status.percent_consumed = Decimal("62.5")
        mock_status.unit_cost = Decimal("500.00")
        mock_status.total_value = Decimal("50000.00")
        mock_status.consumed_value = Decimal("25000.00")

        with patch(
            "src.api.v1.endpoints.resource_cost.MaterialTrackingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_material_status = AsyncMock(return_value=mock_status)
            mock_service_class.return_value = mock_service

            result = await get_material_status(resource_id, mock_db, mock_user)

            assert result.resource_id == resource_id
            assert result.resource_code == "MAT-001"
            assert result.quantity_consumed == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_get_material_status_not_found(self):
        """Should raise NotFoundError when resource not found."""
        from src.core.exceptions import NotFoundError

        resource_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        with patch(
            "src.api.v1.endpoints.resource_cost.MaterialTrackingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_material_status = AsyncMock(
                side_effect=ValueError("Resource not found")
            )
            mock_service_class.return_value = mock_service

            with pytest.raises(NotFoundError) as exc_info:
                await get_material_status(resource_id, mock_db, mock_user)

            assert exc_info.value.code == "RESOURCE_NOT_FOUND"


class TestConsumeMaterial:
    """Tests for consume_material endpoint."""

    @pytest.mark.asyncio
    async def test_consume_material_success(self):
        """Should consume material successfully."""
        from src.schemas.resource_cost import MaterialConsumptionRequest

        assignment_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        request = MaterialConsumptionRequest(quantity=Decimal("10.0"))

        mock_result = MagicMock()
        mock_result.assignment_id = assignment_id
        mock_result.quantity_consumed = Decimal("10.0")
        mock_result.remaining_assigned = Decimal("20.0")
        mock_result.cost_incurred = Decimal("5000.00")

        with patch(
            "src.api.v1.endpoints.resource_cost.MaterialTrackingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.consume_material = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            result = await consume_material(assignment_id, request, mock_db, mock_user)

            assert result.assignment_id == assignment_id
            assert result.quantity_consumed == Decimal("10.0")

    @pytest.mark.asyncio
    async def test_consume_material_invalid(self):
        """Should raise ValidationError for invalid consumption."""
        from src.core.exceptions import ValidationError
        from src.schemas.resource_cost import MaterialConsumptionRequest

        assignment_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        request = MaterialConsumptionRequest(quantity=Decimal("1000.0"))  # Too much

        with patch(
            "src.api.v1.endpoints.resource_cost.MaterialTrackingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.consume_material = AsyncMock(
                side_effect=ValueError("Insufficient quantity")
            )
            mock_service_class.return_value = mock_service

            with pytest.raises(ValidationError) as exc_info:
                await consume_material(assignment_id, request, mock_db, mock_user)

            assert exc_info.value.code == "INVALID_CONSUMPTION"


class TestGetProgramMaterials:
    """Tests for get_program_materials endpoint."""

    @pytest.mark.asyncio
    async def test_get_program_materials_success(self):
        """Should return program materials summary."""
        program_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        mock_material = MagicMock()
        mock_material.resource_id = uuid4()
        mock_material.resource_code = "MAT-001"
        mock_material.resource_name = "Steel"
        mock_material.quantity_unit = "tons"
        mock_material.quantity_available = Decimal("100.00")
        mock_material.quantity_assigned = Decimal("80.00")
        mock_material.quantity_consumed = Decimal("50.00")
        mock_material.quantity_remaining = Decimal("30.00")
        mock_material.percent_consumed = Decimal("62.5")
        mock_material.unit_cost = Decimal("500.00")
        mock_material.total_value = Decimal("50000.00")
        mock_material.consumed_value = Decimal("25000.00")

        mock_summary = MagicMock()
        mock_summary.program_id = program_id
        mock_summary.material_count = 3
        mock_summary.total_value = Decimal("150000.00")
        mock_summary.consumed_value = Decimal("75000.00")
        mock_summary.remaining_value = Decimal("75000.00")
        mock_summary.materials = [mock_material]

        with patch(
            "src.api.v1.endpoints.resource_cost.MaterialTrackingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_program_materials = AsyncMock(return_value=mock_summary)
            mock_service_class.return_value = mock_service

            result = await get_program_materials(program_id, mock_db, mock_user)

            assert result.program_id == program_id
            assert result.material_count == 3
            assert len(result.materials) == 1

    @pytest.mark.asyncio
    async def test_get_program_materials_empty(self):
        """Should return empty materials list."""
        program_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()

        mock_summary = MagicMock()
        mock_summary.program_id = program_id
        mock_summary.material_count = 0
        mock_summary.total_value = Decimal("0.00")
        mock_summary.consumed_value = Decimal("0.00")
        mock_summary.remaining_value = Decimal("0.00")
        mock_summary.materials = []

        with patch(
            "src.api.v1.endpoints.resource_cost.MaterialTrackingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_program_materials = AsyncMock(return_value=mock_summary)
            mock_service_class.return_value = mock_service

            result = await get_program_materials(program_id, mock_db, mock_user)

            assert result.material_count == 0
            assert len(result.materials) == 0
