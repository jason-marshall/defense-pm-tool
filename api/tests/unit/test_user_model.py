"""Unit tests for User model properties and methods."""

from uuid import uuid4

from src.models.enums import UserRole
from src.models.user import User


class TestUserProperties:
    """Tests for User model properties."""

    def test_repr(self) -> None:
        """Should return formatted string representation."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed",
            role=UserRole.ANALYST,
        )
        repr_str = repr(user)
        assert "User" in repr_str
        assert "test@example.com" in repr_str
        assert "analyst" in repr_str

    def test_has_role_admin(self) -> None:
        """Admin should have all role permissions."""
        user = User(
            id=uuid4(),
            email="admin@example.com",
            full_name="Admin",
            hashed_password="hashed",
            role=UserRole.ADMIN,
        )
        assert user.has_role(UserRole.VIEWER) is True
        assert user.has_role(UserRole.ANALYST) is True
        assert user.has_role(UserRole.SCHEDULER) is True
        assert user.has_role(UserRole.PROGRAM_MANAGER) is True
        assert user.has_role(UserRole.ADMIN) is True

    def test_has_role_viewer(self) -> None:
        """Viewer should only have viewer permissions."""
        user = User(
            id=uuid4(),
            email="viewer@example.com",
            full_name="Viewer",
            hashed_password="hashed",
            role=UserRole.VIEWER,
        )
        assert user.has_role(UserRole.VIEWER) is True
        assert user.has_role(UserRole.ANALYST) is False
        assert user.has_role(UserRole.ADMIN) is False

    def test_is_admin_true(self) -> None:
        """Should return True for admin users."""
        user = User(
            id=uuid4(),
            email="admin@example.com",
            full_name="Admin",
            hashed_password="hashed",
            role=UserRole.ADMIN,
        )
        assert user.is_admin is True

    def test_is_admin_false(self) -> None:
        """Should return False for non-admin users."""
        user = User(
            id=uuid4(),
            email="user@example.com",
            full_name="User",
            hashed_password="hashed",
            role=UserRole.SCHEDULER,
        )
        assert user.is_admin is False

    def test_can_manage_programs_true(self) -> None:
        """Program managers and admins can manage programs."""
        pm = User(
            id=uuid4(),
            email="pm@example.com",
            full_name="PM",
            hashed_password="hashed",
            role=UserRole.PROGRAM_MANAGER,
        )
        admin = User(
            id=uuid4(),
            email="admin@example.com",
            full_name="Admin",
            hashed_password="hashed",
            role=UserRole.ADMIN,
        )
        assert pm.can_manage_programs is True
        assert admin.can_manage_programs is True

    def test_can_manage_programs_false(self) -> None:
        """Lower roles cannot manage programs."""
        scheduler = User(
            id=uuid4(),
            email="scheduler@example.com",
            full_name="Scheduler",
            hashed_password="hashed",
            role=UserRole.SCHEDULER,
        )
        viewer = User(
            id=uuid4(),
            email="viewer@example.com",
            full_name="Viewer",
            hashed_password="hashed",
            role=UserRole.VIEWER,
        )
        assert scheduler.can_manage_programs is False
        assert viewer.can_manage_programs is False

    def test_can_edit_schedule_true(self) -> None:
        """Scheduler and above can edit schedules."""
        scheduler = User(
            id=uuid4(),
            email="scheduler@example.com",
            full_name="Scheduler",
            hashed_password="hashed",
            role=UserRole.SCHEDULER,
        )
        pm = User(
            id=uuid4(),
            email="pm@example.com",
            full_name="PM",
            hashed_password="hashed",
            role=UserRole.PROGRAM_MANAGER,
        )
        assert scheduler.can_edit_schedule is True
        assert pm.can_edit_schedule is True

    def test_can_edit_schedule_false(self) -> None:
        """Analyst and viewer cannot edit schedules."""
        analyst = User(
            id=uuid4(),
            email="analyst@example.com",
            full_name="Analyst",
            hashed_password="hashed",
            role=UserRole.ANALYST,
        )
        viewer = User(
            id=uuid4(),
            email="viewer@example.com",
            full_name="Viewer",
            hashed_password="hashed",
            role=UserRole.VIEWER,
        )
        assert analyst.can_edit_schedule is False
        assert viewer.can_edit_schedule is False
