"""Unit tests for Dependency schemas."""

from datetime import UTC, datetime
from uuid import uuid4

from src.models.enums import DependencyType
from src.schemas.dependency import DependencyCreate, DependencyResponse, DependencyUpdate

# Helpers
NOW = datetime.now(UTC)


class TestDependencyCreate:
    """Tests for DependencyCreate schema."""

    def test_create_fs_dependency(self):
        """Test creating finish-to-start dependency."""
        dep = DependencyCreate(
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
        )
        assert dep.dependency_type == DependencyType.FS
        assert dep.lag == 0  # Default lag

    def test_create_ss_dependency(self):
        """Test creating start-to-start dependency."""
        dep = DependencyCreate(
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.SS,
        )
        assert dep.dependency_type == DependencyType.SS

    def test_create_ff_dependency(self):
        """Test creating finish-to-finish dependency."""
        dep = DependencyCreate(
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FF,
        )
        assert dep.dependency_type == DependencyType.FF

    def test_create_sf_dependency(self):
        """Test creating start-to-finish dependency."""
        dep = DependencyCreate(
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.SF,
        )
        assert dep.dependency_type == DependencyType.SF

    def test_create_dependency_with_positive_lag(self):
        """Test creating dependency with positive lag."""
        dep = DependencyCreate(
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=5,
        )
        assert dep.lag == 5

    def test_create_dependency_with_negative_lag(self):
        """Test creating dependency with negative lag (lead)."""
        dep = DependencyCreate(
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=-3,
        )
        assert dep.lag == -3


class TestDependencyUpdate:
    """Tests for DependencyUpdate schema."""

    def test_update_lag(self):
        """Test updating lag."""
        update = DependencyUpdate(lag=10)
        assert update.lag == 10

    def test_update_dependency_type(self):
        """Test updating dependency type."""
        update = DependencyUpdate(dependency_type=DependencyType.SS)
        assert update.dependency_type == DependencyType.SS

    def test_update_partial(self):
        """Test partial update."""
        update = DependencyUpdate(lag=5)
        assert update.lag == 5


class TestDependencyResponseProperties:
    """Tests for DependencyResponse computed properties."""

    def test_has_lag_true(self) -> None:
        """Should return True for non-zero lag."""
        dep = DependencyResponse(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=5,
            created_at=NOW,
            updated_at=NOW,
        )
        assert dep.has_lag is True

    def test_has_lag_false(self) -> None:
        """Should return False for zero lag."""
        dep = DependencyResponse(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=0,
            created_at=NOW,
            updated_at=NOW,
        )
        assert dep.has_lag is False

    def test_has_lead_true(self) -> None:
        """Should return True for negative lag."""
        dep = DependencyResponse(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=-3,
            created_at=NOW,
            updated_at=NOW,
        )
        assert dep.has_lead is True

    def test_has_lead_false(self) -> None:
        """Should return False for non-negative lag."""
        dep = DependencyResponse(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FS,
            lag=0,
            created_at=NOW,
            updated_at=NOW,
        )
        assert dep.has_lead is False

    def test_dependency_description_fs_no_lag(self) -> None:
        """Should describe FS dependency without lag."""
        pred_id = uuid4()
        succ_id = uuid4()
        dep = DependencyResponse(
            id=uuid4(),
            predecessor_id=pred_id,
            successor_id=succ_id,
            dependency_type=DependencyType.FS,
            lag=0,
            created_at=NOW,
            updated_at=NOW,
        )
        desc = dep.dependency_description
        assert "finishes before" in desc
        assert str(pred_id) in desc
        assert str(succ_id) in desc

    def test_dependency_description_with_lag(self) -> None:
        """Should include lag in description."""
        dep = DependencyResponse(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.SS,
            lag=5,
            created_at=NOW,
            updated_at=NOW,
        )
        desc = dep.dependency_description
        assert "starts before" in desc
        assert "5 day lag" in desc

    def test_dependency_description_with_lead(self) -> None:
        """Should include lead in description."""
        dep = DependencyResponse(
            id=uuid4(),
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            dependency_type=DependencyType.FF,
            lag=-2,
            created_at=NOW,
            updated_at=NOW,
        )
        desc = dep.dependency_description
        assert "finishes before" in desc
        assert "2 day lead" in desc
