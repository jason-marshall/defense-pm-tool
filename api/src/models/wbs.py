"""WBS (Work Breakdown Structure) model."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.activity import Activity
    from src.models.program import Program


class WBSElement(Base):
    """
    Represents a Work Breakdown Structure element.

    WBS elements form a hierarchical structure for organizing work.
    Uses a path-based approach for efficient hierarchy queries.
    """

    __tablename__ = "wbs_elements"

    # Foreign keys
    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("wbs_elements.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Basic information
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Hierarchy path (e.g., "1.2.3" for efficient queries)
    path: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    level: Mapped[int] = mapped_column(nullable=False, default=1)

    # Budget allocation
    budgeted_cost: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # Relationships
    program: Mapped["Program"] = relationship("Program", back_populates="wbs_elements")
    parent: Mapped["WBSElement | None"] = relationship(
        "WBSElement",
        remote_side="WBSElement.id",
        back_populates="children",
    )
    children: Mapped[list["WBSElement"]] = relationship(
        "WBSElement",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    activities: Mapped[list["Activity"]] = relationship(
        "Activity",
        back_populates="wbs_element",
    )

    @property
    def full_code(self) -> str:
        """Get the full WBS code including parent codes."""
        return self.path

    @property
    def is_leaf(self) -> bool:
        """Check if this is a leaf element (no children)."""
        return len(self.children) == 0

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<WBSElement(id={self.id}, code={self.code}, path={self.path})>"
