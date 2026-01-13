"""Unit tests for schema validation."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from src.schemas.program import ProgramCreate, ProgramUpdate
from src.schemas.wbs import WBSCreate, WBSUpdate
from src.schemas.evms_period import EVMSPeriodCreate, EVMSPeriodDataCreate


class TestProgramSchemas:
    """Tests for Program schema validation."""

    def test_create_program_minimal(self):
        """Test creating program with minimal fields."""
        program = ProgramCreate(
            name="Test Program",
            code="TP-001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        assert program.name == "Test Program"
        assert program.code == "TP-001"

    def test_create_program_with_budget(self):
        """Test creating program with budget."""
        program = ProgramCreate(
            name="Test Program",
            code="TP-001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_at_completion=Decimal("1000000.00"),
        )
        assert program.budget_at_completion == Decimal("1000000.00")

    def test_create_program_with_contract(self):
        """Test creating program with contract info."""
        program = ProgramCreate(
            name="Test Program",
            code="TP-001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            contract_number="W912DQ-24-C-0001",
        )
        assert program.contract_number == "W912DQ-24-C-0001"

    def test_update_program_partial(self):
        """Test partial update of program."""
        update = ProgramUpdate(name="Updated Program Name")
        assert update.name == "Updated Program Name"

    def test_create_program_with_description(self):
        """Test creating program with description."""
        program = ProgramCreate(
            name="Test Program",
            code="TP-001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            description="A test defense program",
        )
        assert program.description == "A test defense program"


class TestWBSSchemas:
    """Tests for WBS schema validation."""

    def test_create_wbs_minimal(self):
        """Test creating WBS with minimal fields."""
        wbs = WBSCreate(
            program_id=uuid4(),
            wbs_code="1.0",
            name="Program Management",
        )
        assert wbs.wbs_code == "1.0"
        assert wbs.name == "Program Management"

    def test_create_wbs_with_parent(self):
        """Test creating WBS with parent."""
        parent_id = uuid4()
        wbs = WBSCreate(
            program_id=uuid4(),
            wbs_code="1.1",
            name="Systems Engineering",
            parent_id=parent_id,
        )
        assert wbs.parent_id == parent_id

    def test_create_wbs_control_account(self):
        """Test creating control account WBS."""
        wbs = WBSCreate(
            program_id=uuid4(),
            wbs_code="1.1.1",
            name="Design",
            is_control_account=True,
            budget_at_completion=Decimal("500000.00"),
        )
        assert wbs.is_control_account is True
        assert wbs.budget_at_completion == Decimal("500000.00")

    def test_update_wbs_partial(self):
        """Test partial WBS update."""
        update = WBSUpdate(name="Updated WBS Name")
        assert update.name == "Updated WBS Name"

    def test_create_wbs_with_description(self):
        """Test creating WBS with description."""
        wbs = WBSCreate(
            program_id=uuid4(),
            wbs_code="1.0",
            name="Program Management",
            description="Overall program management",
        )
        assert wbs.description == "Overall program management"


class TestEVMSPeriodSchemas:
    """Tests for EVMS Period schema validation."""

    def test_create_period_minimal(self):
        """Test creating period with minimal fields."""
        period = EVMSPeriodCreate(
            program_id=uuid4(),
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            period_name="January 2024",
        )
        assert period.period_name == "January 2024"

    def test_create_period_dates(self):
        """Test period date fields."""
        period = EVMSPeriodCreate(
            program_id=uuid4(),
            period_start=date(2024, 2, 1),
            period_end=date(2024, 2, 29),
            period_name="February 2024",
        )
        assert period.period_start == date(2024, 2, 1)
        assert period.period_end == date(2024, 2, 29)

    def test_create_period_data_minimal(self):
        """Test creating period data with minimal fields."""
        data = EVMSPeriodDataCreate(
            period_id=uuid4(),
            wbs_id=uuid4(),
            bcws=Decimal("50000.00"),
            bcwp=Decimal("48000.00"),
            acwp=Decimal("45000.00"),
            cumulative_bcws=Decimal("50000.00"),
            cumulative_bcwp=Decimal("48000.00"),
            cumulative_acwp=Decimal("45000.00"),
        )
        assert data.bcws == Decimal("50000.00")
        assert data.bcwp == Decimal("48000.00")
        assert data.acwp == Decimal("45000.00")

    def test_create_period_data_zero_values(self):
        """Test period data with zero values."""
        data = EVMSPeriodDataCreate(
            period_id=uuid4(),
            wbs_id=uuid4(),
            bcws=Decimal("0.00"),
            bcwp=Decimal("0.00"),
            acwp=Decimal("0.00"),
            cumulative_bcws=Decimal("0.00"),
            cumulative_bcwp=Decimal("0.00"),
            cumulative_acwp=Decimal("0.00"),
        )
        assert data.bcws == Decimal("0.00")

    def test_create_period_data_large_values(self):
        """Test period data with large values."""
        data = EVMSPeriodDataCreate(
            period_id=uuid4(),
            wbs_id=uuid4(),
            bcws=Decimal("99999999.99"),
            bcwp=Decimal("99999999.99"),
            acwp=Decimal("99999999.99"),
            cumulative_bcws=Decimal("99999999.99"),
            cumulative_bcwp=Decimal("99999999.99"),
            cumulative_acwp=Decimal("99999999.99"),
        )
        assert data.bcws == Decimal("99999999.99")
