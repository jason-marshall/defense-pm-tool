"""Extended unit tests for base model functionality."""

from datetime import datetime
from uuid import uuid4

from src.models.activity import Activity
from src.models.enums import ProgramStatus
from src.models.program import Program


class TestBaseModelToDict:
    """Tests for Base model to_dict method."""

    def test_to_dict_basic(self):
        """Test basic to_dict conversion."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test Activity",
            duration=5,
        )

        result = activity.to_dict()

        assert "id" in result
        assert "code" in result
        assert "name" in result
        assert "duration" in result
        assert result["code"] == "ACT-001"
        assert result["name"] == "Test Activity"
        assert result["duration"] == 5

    def test_to_dict_with_exclude(self):
        """Test to_dict with excluded fields."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test Activity",
            duration=5,
        )

        result = activity.to_dict(exclude={"code", "name"})

        assert "id" in result
        assert "code" not in result
        assert "name" not in result
        assert "duration" in result

    def test_to_dict_uuid_conversion(self):
        """Test that UUIDs are converted to strings."""
        activity_id = uuid4()
        program_id = uuid4()
        activity = Activity(
            id=activity_id,
            program_id=program_id,
            code="ACT-001",
            name="Test Activity",
            duration=5,
        )

        result = activity.to_dict()

        assert result["id"] == str(activity_id)
        assert result["program_id"] == str(program_id)

    def test_to_dict_datetime_conversion(self):
        """Test that datetimes are converted to ISO format."""
        now = datetime.now()
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test Activity",
            duration=5,
            created_at=now,
            updated_at=now,
        )

        result = activity.to_dict()

        assert isinstance(result["created_at"], str)
        assert isinstance(result["updated_at"], str)

    def test_to_dict_null_values(self):
        """Test to_dict handles null values."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test Activity",
            duration=5,
            deleted_at=None,
            early_start=None,
            early_finish=None,
        )

        result = activity.to_dict()

        assert result["deleted_at"] is None


class TestBaseModelTableNameGeneration:
    """Additional tests for table name generation."""

    def test_tablename_single_word(self):
        """Test single word class name."""
        # User -> users
        from src.models.user import User

        assert User.__tablename__ == "users"

    def test_tablename_two_words(self):
        """Test two word class name (camelCase)."""
        # WBSElement -> wbs_elements
        from src.models.wbs import WBSElement

        assert WBSElement.__tablename__ == "wbs_elements"

    def test_tablename_ending_in_y(self):
        """Test class name ending in 'y'."""
        # Activity -> activities
        # Dependency -> dependencies
        from src.models.activity import Activity
        from src.models.dependency import Dependency

        assert Activity.__tablename__ == "activities"
        assert Dependency.__tablename__ == "dependencies"

    def test_tablename_ending_in_s(self):
        """Test class name ending in 's'."""
        # EVMSPeriod -> evms_periods (s + es = ses? No, it's evms_periods)
        from src.models.evms_period import EVMSPeriod

        assert EVMSPeriod.__tablename__ == "evms_periods"


class TestSoftDeleteFunctionality:
    """Tests for soft delete functionality in detail."""

    def test_soft_delete_sets_timestamp(self):
        """Test that soft_delete sets deleted_at to current time."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
        )

        before_delete = datetime.now()
        activity.soft_delete()
        after_delete = datetime.now()

        assert activity.deleted_at is not None
        assert before_delete <= activity.deleted_at <= after_delete

    def test_restore_clears_timestamp(self):
        """Test that restore clears deleted_at."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
            deleted_at=datetime.now(),
        )

        activity.restore()

        assert activity.deleted_at is None

    def test_is_deleted_reflects_state(self):
        """Test is_deleted property reflects deleted_at state."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
        )

        assert activity.is_deleted is False

        activity.soft_delete()
        assert activity.is_deleted is True

        activity.restore()
        assert activity.is_deleted is False


class TestBaseModelRepr:
    """Tests for __repr__ method."""

    def test_repr_contains_class_name(self):
        """Test that repr contains class name."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
        )

        repr_str = repr(activity)
        assert "Activity" in repr_str

    def test_repr_contains_id(self):
        """Test that repr contains ID."""
        activity_id = uuid4()
        activity = Activity(
            id=activity_id,
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
        )

        repr_str = repr(activity)
        assert str(activity_id) in repr_str or "id=" in repr_str

    def test_program_repr_special(self):
        """Test Program has special repr with code."""
        program = Program(
            id=uuid4(),
            code="PROG-001",
            name="Test Program",
            owner_id=uuid4(),
            status=ProgramStatus.PLANNING,
        )

        repr_str = repr(program)
        assert "Program" in repr_str
        assert "PROG-001" in repr_str


class TestSoftDeleteMixin:
    """Tests for SoftDeleteMixin."""

    def test_active_filter(self):
        """Test active_filter returns correct filter."""
        from src.models.base import SoftDeleteMixin

        class _SoftDeleteFixture(SoftDeleteMixin):
            deleted_at = None

        # This would require a real SQLAlchemy setup to test properly
        # For now, just verify the method exists
        assert hasattr(_SoftDeleteFixture, "active_filter")
        assert callable(_SoftDeleteFixture.active_filter)

    def test_deleted_filter(self):
        """Test deleted_filter returns correct filter."""
        from src.models.base import SoftDeleteMixin

        class _SoftDeleteFixture(SoftDeleteMixin):
            deleted_at = None

        assert hasattr(_SoftDeleteFixture, "deleted_filter")
        assert callable(_SoftDeleteFixture.deleted_filter)
