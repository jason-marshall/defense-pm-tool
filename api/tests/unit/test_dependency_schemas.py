"""Unit tests for Dependency schemas."""

from uuid import uuid4

from src.models.enums import DependencyType
from src.schemas.dependency import DependencyCreate, DependencyUpdate


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
