"""Resource pool models for cross-program resource sharing."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.program import Program
    from src.models.resource import Resource
    from src.models.user import User


class PoolAccessLevel(str, Enum):
    """Access level for programs to resource pools."""

    OWNER = "OWNER"  # Full control, can delete pool
    ADMIN = "ADMIN"  # Can manage members and access
    MEMBER = "MEMBER"  # Can use resources from pool
    VIEWER = "VIEWER"  # Read-only access


class ResourcePool(Base):
    """
    Represents a shared pool of resources across programs.

    Resource pools allow organizations to share resources between programs,
    enabling better resource utilization and cross-program planning.

    Attributes:
        name: Pool name/description
        code: Unique pool code
        description: Detailed description
        owner_id: FK to user who owns the pool
        is_active: Whether pool is currently active
    """

    __tablename__ = "resource_pools"

    # Pool identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Pool name/description",
    )

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique pool code",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of the pool",
    )

    # Ownership
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to user who owns the pool",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether pool is currently active",
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner_id],
        lazy="joined",
    )

    members: Mapped[list["ResourcePoolMember"]] = relationship(
        "ResourcePoolMember",
        back_populates="pool",
        cascade="all, delete-orphan",
    )

    access_grants: Mapped[list["ResourcePoolAccess"]] = relationship(
        "ResourcePoolAccess",
        back_populates="pool",
        cascade="all, delete-orphan",
    )

    # Table-level configuration
    __table_args__ = (
        UniqueConstraint("code", name="uq_resource_pools_code"),
        Index(
            "ix_resource_pools_active",
            "is_active",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"comment": "Shared resource pools across programs"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<ResourcePool(id={self.id}, code={self.code!r}, name={self.name!r}, "
            f"active={self.is_active})>"
        )


class ResourcePoolMember(Base):
    """
    Represents a resource that belongs to a pool.

    Pool members define which resources are shared through a pool
    and what percentage of their capacity is available.

    Attributes:
        pool_id: FK to parent pool
        resource_id: FK to the shared resource
        allocation_percentage: Percentage of resource available to pool (0-100)
        is_active: Whether membership is active
    """

    __tablename__ = "resource_pool_members"

    # Foreign keys
    pool_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resource_pools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent pool",
    )

    resource_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to the shared resource",
    )

    # Allocation
    allocation_percentage: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=False,
        default=Decimal("100.00"),
        comment="Percentage of resource available to pool (0-100)",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether membership is active",
    )

    # Relationships
    pool: Mapped["ResourcePool"] = relationship(
        "ResourcePool",
        back_populates="members",
    )

    resource: Mapped["Resource"] = relationship(
        "Resource",
        lazy="joined",
    )

    # Table-level configuration
    __table_args__ = (
        UniqueConstraint(
            "pool_id",
            "resource_id",
            name="uq_resource_pool_members_pool_resource",
        ),
        CheckConstraint(
            "allocation_percentage >= 0 AND allocation_percentage <= 100",
            name="ck_resource_pool_members_allocation",
        ),
        Index(
            "ix_resource_pool_members_active",
            "pool_id",
            "is_active",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"comment": "Resources belonging to pools"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<ResourcePoolMember(id={self.id}, pool_id={self.pool_id}, "
            f"resource_id={self.resource_id}, allocation={self.allocation_percentage}%)>"
        )


class ResourcePoolAccess(Base):
    """
    Represents program access to a resource pool.

    Pool access controls which programs can use resources from a pool
    and at what access level.

    Attributes:
        pool_id: FK to the pool
        program_id: FK to the program with access
        access_level: Level of access granted
        granted_by: FK to user who granted access
        granted_at: When access was granted
    """

    __tablename__ = "resource_pool_access"

    # Foreign keys
    pool_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resource_pools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to the pool",
    )

    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to the program with access",
    )

    # Access control
    access_level: Mapped[PoolAccessLevel] = mapped_column(
        PgEnum(PoolAccessLevel, name="pool_access_level", create_type=False),
        nullable=False,
        default=PoolAccessLevel.VIEWER,
        comment="Level of access granted",
    )

    # Grant tracking
    granted_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to user who granted access",
    )

    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="When access was granted",
    )

    # Relationships
    pool: Mapped["ResourcePool"] = relationship(
        "ResourcePool",
        back_populates="access_grants",
    )

    program: Mapped["Program"] = relationship(
        "Program",
        lazy="joined",
    )

    granter: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[granted_by],
        lazy="joined",
    )

    # Table-level configuration
    __table_args__ = (
        UniqueConstraint(
            "pool_id",
            "program_id",
            name="uq_resource_pool_access_pool_program",
        ),
        Index(
            "ix_resource_pool_access_by_level",
            "pool_id",
            "access_level",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"comment": "Program access to resource pools"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<ResourcePoolAccess(id={self.id}, pool_id={self.pool_id}, "
            f"program_id={self.program_id}, level={self.access_level.value})>"
        )
