"""Unit tests for dependency schemas."""

from datetime import datetime
from uuid import uuid4

import pytest

from src.models.enums import DependencyType
from src.schemas.dependency import (
    DependencyCreate,
    DependencyResponse,
    DependencyUpdate,
)


class TestDependencyCreate:
    """Tests for DependencyCreate schema."""

    def test_valid_dependency(self):
        """Test valid dependency creation."""
        pred_id = uuid4()
        succ_id = uuid4()

        dep = DependencyCreate(
            predecessor_id=pred_id,
            successor_id=succ_id,
            dependency_type=DependencyType.FS,
            lag=0,
        )

        assert dep.predecessor_id == pred_id
        assert dep.successor_id == succ_id
        assert dep.dependency_type == DependencyType.FS
        assert dep.lag == 0

    def test_dependency_with_lag(self):
        """Test dependency with positive lag."""
        dep = DependencyCreate(
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=5,
        )

        assert dep.lag == 5

    def test_dependency_with_lead(self):
        """Test dependency with negative lag (lead)."""
        dep = DependencyCreate(
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.SS,
            lag=-2,
        )

        assert dep.lag == -2

    def test_self_dependency_raises_error(self):
        """Test that self-dependency raises validation error."""
        same_id = uuid4()

        with pytest.raises(ValueError, match="cannot depend on itself"):
            DependencyCreate(
                predecessor_id=same_id,
                successor_id=same_id,
                dependency_type=DependencyType.FS,
                lag=0,
            )

    def test_dependency_types(self):
        """Test all dependency types are accepted."""
        pred_id = uuid4()
        succ_id = uuid4()

        for dep_type in DependencyType:
            dep = DependencyCreate(
                predecessor_id=pred_id,
                successor_id=succ_id,
                dependency_type=dep_type,
                lag=0,
            )
            assert dep.dependency_type == dep_type


class TestDependencyUpdate:
    """Tests for DependencyUpdate schema."""

    def test_update_dependency_type(self):
        """Test updating dependency type."""
        update = DependencyUpdate(dependency_type=DependencyType.SS)

        assert update.dependency_type == DependencyType.SS
        assert update.lag is None

    def test_update_lag(self):
        """Test updating lag."""
        update = DependencyUpdate(lag=3)

        assert update.dependency_type is None
        assert update.lag == 3

    def test_update_both(self):
        """Test updating both fields."""
        update = DependencyUpdate(
            dependency_type=DependencyType.FF,
            lag=-1,
        )

        assert update.dependency_type == DependencyType.FF
        assert update.lag == -1

    def test_update_empty(self):
        """Test update with no changes."""
        update = DependencyUpdate()

        assert update.dependency_type is None
        assert update.lag is None


class TestDependencyResponse:
    """Tests for DependencyResponse schema properties."""

    def _make_response(self, lag: int) -> DependencyResponse:
        """Create a DependencyResponse with given lag."""
        return DependencyResponse(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=lag,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def test_has_lag_true(self):
        """Test has_lag with positive lag."""
        response = self._make_response(lag=5)
        assert response.has_lag is True

    def test_has_lag_with_negative_lag(self):
        """Test has_lag with negative lag (lead)."""
        response = self._make_response(lag=-2)
        assert response.has_lag is True

    def test_has_lag_false(self):
        """Test has_lag with zero lag."""
        response = self._make_response(lag=0)
        assert response.has_lag is False

    def test_has_lead_true(self):
        """Test has_lead with negative lag."""
        response = self._make_response(lag=-3)
        assert response.has_lead is True

    def test_has_lead_false_positive(self):
        """Test has_lead with positive lag."""
        response = self._make_response(lag=5)
        assert response.has_lead is False

    def test_has_lead_false_zero(self):
        """Test has_lead with zero lag."""
        response = self._make_response(lag=0)
        assert response.has_lead is False
