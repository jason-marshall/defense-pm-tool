"""User model for authentication and authorization."""

from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Index, String, text
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.program import Program


class UserRole(str, Enum):
    """
    User roles for role-based access control (RBAC).

    Roles are hierarchical - higher roles include permissions of lower roles:
    - VIEWER: Read-only access to assigned programs
    - ANALYST: Can view and analyze data, run reports
    - SCHEDULER: Can create/modify activities and dependencies
    - PROGRAM_MANAGER: Full control over assigned programs
    - ADMIN: System-wide administration
    """

    VIEWER = "viewer"
    ANALYST = "analyst"
    SCHEDULER = "scheduler"
    PROGRAM_MANAGER = "program_manager"
    ADMIN = "admin"

    @classmethod
    def get_hierarchy(cls) -> dict["UserRole", int]:
        """Get role hierarchy levels (higher = more permissions)."""
        return {
            cls.VIEWER: 1,
            cls.ANALYST: 2,
            cls.SCHEDULER: 3,
            cls.PROGRAM_MANAGER: 4,
            cls.ADMIN: 5,
        }

    def has_permission(self, required_role: "UserRole") -> bool:
        """Check if this role has at least the permissions of required_role."""
        hierarchy = self.get_hierarchy()
        return hierarchy[self] >= hierarchy[required_role]


class User(Base):
    """
    User model for authentication and authorization.

    Stores user credentials and profile information. Passwords are stored
    as bcrypt hashes and should never be exposed via the API.

    Attributes:
        email: Unique email address (used for login)
        hashed_password: Bcrypt hash of the user's password
        full_name: User's display name
        is_active: Whether the user account is active
        role: User's role for authorization
    """

    # Override auto-generated table name for clarity
    __tablename__ = "users"

    # Email - unique identifier for login
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique email address for login",
    )

    # Password hash - never store plain text passwords!
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hash of user password",
    )

    # Profile information
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User's display name",
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether the user account is active",
    )

    # Role for authorization
    role: Mapped[UserRole] = mapped_column(
        PgEnum(UserRole, name="user_role", create_type=True),
        default=UserRole.VIEWER,
        nullable=False,
        index=True,
        comment="User role for access control",
    )

    # Relationships
    # Programs owned by this user
    owned_programs: Mapped[list["Program"]] = relationship(
        "Program",
        back_populates="owner",
        lazy="selectin",
    )

    # Table-level configuration
    __table_args__ = (
        # Index for active users lookup (common query pattern)
        Index(
            "ix_users_active_role",
            "is_active",
            "role",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # Index for email lookup with case-insensitive search
        Index(
            "ix_users_email_lower",
            text("LOWER(email)"),
            unique=True,
        ),
        {"comment": "User accounts for authentication and authorization"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"<User(id={self.id}, email={self.email}, role={self.role.value})>"

    def has_role(self, required_role: UserRole) -> bool:
        """Check if user has at least the required role permissions."""
        return self.role.has_permission(required_role)

    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == UserRole.ADMIN

    @property
    def can_manage_programs(self) -> bool:
        """Check if user can manage programs."""
        return self.role in (UserRole.PROGRAM_MANAGER, UserRole.ADMIN)

    @property
    def can_edit_schedule(self) -> bool:
        """Check if user can edit schedules."""
        return self.role in (UserRole.SCHEDULER, UserRole.PROGRAM_MANAGER, UserRole.ADMIN)
