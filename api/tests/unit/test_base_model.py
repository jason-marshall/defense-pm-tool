"""Unit tests for base model functionality."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, SoftDeleteMixin


class SampleModel(Base):
    """Sample model for unit tests."""

    __tablename__ = "sample_models"

    name: Mapped[str] = mapped_column(String(100))


class SampleSoftDeleteModel(Base, SoftDeleteMixin):
    """Sample model with soft delete mixin."""

    __tablename__ = "sample_soft_deletes"

    name: Mapped[str] = mapped_column(String(100))


class TestBaseModel:
    """Tests for Base model functionality."""

    def test_id_can_be_set(self) -> None:
        """ID can be set manually."""
        test_id = uuid4()
        model = SampleModel(id=test_id, name="test")
        assert model.id == test_id
        assert isinstance(model.id, UUID)

    def test_manual_ids_are_unique(self) -> None:
        """Manually set IDs should be different."""
        id1, id2 = uuid4(), uuid4()
        model1 = SampleModel(id=id1, name="test1")
        model2 = SampleModel(id=id2, name="test2")
        assert model1.id != model2.id

    def test_is_deleted_property_false(self) -> None:
        """is_deleted should be False when deleted_at is None."""
        model = SampleModel(name="test")
        model.deleted_at = None
        assert model.is_deleted is False

    def test_is_deleted_property_true(self) -> None:
        """is_deleted should be True when deleted_at is set."""
        model = SampleModel(name="test")
        model.deleted_at = datetime.now()
        assert model.is_deleted is True

    def test_soft_delete_sets_deleted_at(self) -> None:
        """soft_delete should set deleted_at timestamp."""
        model = SampleModel(name="test")
        assert model.deleted_at is None
        model.soft_delete()
        assert model.deleted_at is not None
        assert isinstance(model.deleted_at, datetime)

    def test_restore_clears_deleted_at(self) -> None:
        """restore should clear deleted_at timestamp."""
        model = SampleModel(name="test")
        model.soft_delete()
        assert model.deleted_at is not None
        model.restore()
        assert model.deleted_at is None

    def test_repr(self) -> None:
        """__repr__ should include class name and ID."""
        model = SampleModel(name="test")
        repr_str = repr(model)
        assert "SampleModel" in repr_str
        assert str(model.id) in repr_str


class TestTableNameGeneration:
    """Tests for automatic table name generation."""

    def test_simple_name(self) -> None:
        """Simple names should be pluralized."""

        class User(Base):
            __abstract__ = True

        assert User.__tablename__ == "users"

    def test_camel_case_name(self) -> None:
        """CamelCase names should be converted to snake_case and pluralized."""

        class UserProfile(Base):
            __abstract__ = True

        assert UserProfile.__tablename__ == "user_profiles"

    def test_name_ending_in_y(self) -> None:
        """Names ending in 'y' should become 'ies'."""

        class Activity(Base):
            __abstract__ = True

        assert Activity.__tablename__ == "activities"

    def test_name_ending_in_s(self) -> None:
        """Names ending in 's' should become 'ses'."""

        class Status(Base):
            __abstract__ = True

        assert Status.__tablename__ == "statuses"

    def test_multi_word_camel_case(self) -> None:
        """Multi-word CamelCase should be properly converted."""

        class WBSElement(Base):
            __abstract__ = True

        assert WBSElement.__tablename__ == "w_b_s_elements"


class TestToDict:
    """Tests for to_dict serialization."""

    def test_to_dict_basic(self) -> None:
        """to_dict should return dict with column values."""
        test_id = uuid4()
        model = SampleModel(id=test_id, name="test_name")
        result = model.to_dict()

        assert isinstance(result, dict)
        assert "name" in result
        assert result["name"] == "test_name"
        assert "id" in result
        # UUID should be converted to string
        assert isinstance(result["id"], str)
        assert result["id"] == str(test_id)

    def test_to_dict_exclude(self) -> None:
        """to_dict should exclude specified columns."""
        model = SampleModel(name="test")
        result = model.to_dict(exclude={"id", "name"})

        assert "id" not in result
        assert "name" not in result

    def test_to_dict_datetime_serialization(self) -> None:
        """to_dict should convert datetime to ISO format."""
        model = SampleModel(name="test")
        model.created_at = datetime(2026, 1, 15, 12, 0, 0)
        result = model.to_dict()

        assert "created_at" in result
        # Should be ISO format string
        assert isinstance(result["created_at"], str)
        assert "2026-01-15" in result["created_at"]


class TestSoftDeleteMixin:
    """Tests for SoftDeleteMixin."""

    def test_active_filter(self) -> None:
        """active_filter should return filter for non-deleted records."""
        filter_expr = SampleSoftDeleteModel.active_filter()
        # Verify it creates a valid SQLAlchemy expression
        assert filter_expr is not None

    def test_deleted_filter(self) -> None:
        """deleted_filter should return filter for deleted records."""
        filter_expr = SampleSoftDeleteModel.deleted_filter()
        # Verify it creates a valid SQLAlchemy expression
        assert filter_expr is not None
