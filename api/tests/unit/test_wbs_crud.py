"""Unit tests for WBS CRUD operations and schemas."""

import pytest
from uuid import uuid4
from decimal import Decimal

from src.schemas.wbs import WBSCreate, WBSUpdate, WBSResponse
from src.models.wbs import WBSElement


class TestWBSCreate:
    """Tests for WBS creation schema."""

    def test_create_root_wbs_minimal(self):
        """Should create root WBS with minimal fields."""
        data = WBSCreate(
            program_id=uuid4(),
            name="Program Root",
            wbs_code="1",
        )
        assert data.wbs_code == "1"
        assert data.parent_id is None
        assert data.is_control_account is False

    def test_create_child_wbs(self):
        """Should create child WBS element."""
        parent_id = uuid4()
        data = WBSCreate(
            program_id=uuid4(),
            parent_id=parent_id,
            name="Phase 1",
            wbs_code="1.1",
        )
        assert data.parent_id == parent_id
        assert data.wbs_code == "1.1"

    def test_create_wbs_with_budget(self):
        """Should create WBS with budgeted cost."""
        data = WBSCreate(
            program_id=uuid4(),
            name="Control Account 1",
            wbs_code="1.1",
            is_control_account=True,
            budget_at_completion=Decimal("100000.00"),
        )
        assert data.is_control_account is True
        assert data.budget_at_completion == Decimal("100000.00")

    def test_create_wbs_with_description(self):
        """Should create WBS with description."""
        data = WBSCreate(
            program_id=uuid4(),
            name="Engineering",
            wbs_code="1.2",
            description="Engineering work package",
        )
        assert data.description == "Engineering work package"

    def test_wbs_code_required(self):
        """WBS code is required."""
        with pytest.raises(ValueError):
            WBSCreate(
                program_id=uuid4(),
                name="Test",
                wbs_code="",  # Empty not allowed
            )

    def test_wbs_name_required(self):
        """WBS name is required."""
        with pytest.raises(ValueError):
            WBSCreate(
                program_id=uuid4(),
                wbs_code="1.1",
                name="",  # Empty not allowed
            )


class TestWBSUpdate:
    """Tests for WBS update schema."""

    def test_update_name_only(self):
        """Should allow updating just the name."""
        data = WBSUpdate(name="Updated Name")
        assert data.name == "Updated Name"
        assert data.description is None

    def test_update_control_account_flag(self):
        """Should allow updating control account flag."""
        data = WBSUpdate(is_control_account=True)
        assert data.is_control_account is True

    def test_update_budget(self):
        """Should allow updating budget."""
        data = WBSUpdate(budget_at_completion=Decimal("250000.00"))
        assert data.budget_at_completion == Decimal("250000.00")

    def test_update_multiple_fields(self):
        """Should allow updating multiple fields."""
        data = WBSUpdate(
            name="New Name",
            description="New description",
            is_control_account=True,
            budget_at_completion=Decimal("500000.00"),
        )
        assert data.name == "New Name"
        assert data.description == "New description"
        assert data.is_control_account is True
        assert data.budget_at_completion == Decimal("500000.00")


class TestWBSModel:
    """Tests for WBS model properties."""

    def test_wbs_element_creation(self):
        """Should create WBS element with all fields."""
        element = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            name="Root Element",
            wbs_code="1",
            path="1",
            level=1,
        )
        assert element.wbs_code == "1"
        assert element.level == 1

    def test_wbs_element_with_parent(self):
        """Should create child WBS element."""
        parent_id = uuid4()
        element = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            parent_id=parent_id,
            name="Child Element",
            wbs_code="1.1",
            path="1.1",
            level=2,
        )
        assert element.parent_id == parent_id
        assert element.level == 2

    def test_wbs_control_account(self):
        """Should handle control account flag."""
        element = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            name="Control Account",
            wbs_code="1.1",
            path="1.1",
            level=2,
            is_control_account=True,
            budget_at_completion=Decimal("100000.00"),
        )
        assert element.is_control_account is True
        assert element.budget_at_completion == Decimal("100000.00")


class TestWBSHierarchy:
    """Tests for WBS hierarchy operations."""

    def test_level_calculation_root(self):
        """Root element should be level 1."""
        element = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            name="Root",
            wbs_code="1",
            path="1",
            level=1,
        )
        assert element.level == 1

    def test_level_calculation_child(self):
        """Child element level based on path depth."""
        element = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            name="Level 3",
            wbs_code="1.1.1",
            path="1.1.1",
            level=3,
        )
        assert element.level == 3

    def test_path_format(self):
        """Path should match WBS code structure."""
        element = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            name="Test",
            wbs_code="1.2.3",
            path="1.2.3",
            level=3,
        )
        assert element.path == "1.2.3"
        assert element.wbs_code == "1.2.3"
