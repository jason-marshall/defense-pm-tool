"""WBS (Work Breakdown Structure) model with ltree hierarchy support."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UserDefinedType

if TYPE_CHECKING:
    from src.models.activity import Activity
    from src.models.program import Program

from src.models.base import Base


class LtreeType(UserDefinedType):
    """
    Custom SQLAlchemy type for PostgreSQL ltree.

    The ltree extension provides efficient hierarchical data storage and
    querying. It supports operations like:
    - @> (ancestor of)
    - <@ (descendant of)
    - ~ (matches ltree pattern)
    - ? (matches any pattern in array)

    Example paths: "1", "1.2", "1.2.3"
    """

    cache_ok = True

    def get_col_spec(self) -> str:
        """Return the column type specification."""
        return "LTREE"

    def bind_processor(self, dialect):
        """Process value before binding to database."""

        def process(value):
            return value

        return process

    def result_processor(self, dialect, coltype):
        """Process value after retrieving from database."""

        def process(value):
            return value

        return process


class WBSElement(Base):
    """
    Work Breakdown Structure element with hierarchical relationships.

    WBS elements form a tree structure for organizing work. Uses PostgreSQL
    ltree extension for efficient hierarchy queries. Each element can be
    a control account for EVMS tracking.

    Attributes:
        program_id: FK to parent program
        parent_id: FK to parent WBS element (null for root elements)
        name: Display name of the WBS element
        wbs_code: Unique code within the program (e.g., "1.2.3")
        path: ltree path for hierarchy queries
        level: Depth in the hierarchy (1 = root)
        is_control_account: Whether this is a control account for EVMS
        budget_at_completion: Allocated budget for this element

    Example hierarchy:
        1 - Program Management (path: "1", level: 1)
        1.1 - Planning (path: "1.1", level: 2)
        1.1.1 - Requirements (path: "1.1.1", level: 3)
        1.2 - Execution (path: "1.2", level: 2)
    """

    # Override auto-generated table name
    __tablename__ = "wbs_elements"

    # Foreign keys
    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent program",
    )

    parent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("wbs_elements.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="FK to parent WBS element (null for root)",
    )

    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name of the WBS element",
    )

    wbs_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Unique code within program (e.g., 1.2.3)",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of the WBS element",
    )

    # Hierarchy path using ltree for efficient queries
    # Format: "1.2.3" where numbers are element codes
    path: Mapped[str] = mapped_column(
        LtreeType(),
        nullable=False,
        comment="ltree path for hierarchy queries",
    )

    # Hierarchy level (1 = root, 2 = first children, etc.)
    level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Depth in hierarchy (1 = root)",
    )

    # EVMS control account flag
    is_control_account: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether this is an EVMS control account",
    )

    # Budget at Completion for this WBS element
    budget_at_completion: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Allocated budget (BAC) for this element",
    )

    # Relationships
    program: Mapped["Program"] = relationship(
        "Program",
        back_populates="wbs_elements",
    )

    parent: Mapped["WBSElement | None"] = relationship(
        "WBSElement",
        remote_side="WBSElement.id",
        back_populates="children",
    )

    children: Mapped[list["WBSElement"]] = relationship(
        "WBSElement",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="WBSElement.wbs_code",
    )

    activities: Mapped[list["Activity"]] = relationship(
        "Activity",
        back_populates="wbs_element",
        cascade="all, delete-orphan",
        order_by="Activity.name",
    )

    # Table-level configuration
    __table_args__ = (
        # Unique constraint on program_id + wbs_code
        Index(
            "ix_wbs_elements_program_code",
            "program_id",
            "wbs_code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # GiST index on path for ltree queries
        Index(
            "ix_wbs_elements_path_gist",
            "path",
            postgresql_using="gist",
        ),
        # Index for control accounts lookup
        Index(
            "ix_wbs_elements_control_accounts",
            "program_id",
            "is_control_account",
            postgresql_where=text("is_control_account = true AND deleted_at IS NULL"),
        ),
        # Index for hierarchy level queries
        Index(
            "ix_wbs_elements_program_level",
            "program_id",
            "level",
        ),
        {"comment": "Work Breakdown Structure elements with hierarchy"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<WBSElement(id={self.id}, code={self.wbs_code!r}, "
            f"path={self.path!r}, level={self.level})>"
        )

    @property
    def full_path(self) -> str:
        """Get the full path string."""
        return str(self.path)

    @property
    def is_root(self) -> bool:
        """Check if this is a root element (no parent)."""
        return self.parent_id is None

    @property
    def is_leaf(self) -> bool:
        """Check if this is a leaf element (no children)."""
        return len(self.children) == 0

    def build_path(self) -> str:
        """
        Build ltree path from parent path and wbs_code.

        Call this when creating or moving elements.
        """
        if self.parent is None:
            return self.wbs_code.replace(".", "_")
        parent_path = self.parent.path
        # Convert wbs_code dots to underscores for ltree compatibility
        code_part = self.wbs_code.split(".")[-1]
        return f"{parent_path}.{code_part}"

    def get_ancestors_filter(self):
        """Return SQLAlchemy filter for ancestor elements."""
        # In ltree: '1.2.3' @> path means path is ancestor of '1.2.3'
        return text(f"path @> '{self.path}'::ltree AND path != '{self.path}'::ltree")

    def get_descendants_filter(self):
        """Return SQLAlchemy filter for descendant elements."""
        # In ltree: path <@ '1.2.3' means path is descendant of '1.2.3'
        return text(f"path <@ '{self.path}'::ltree AND path != '{self.path}'::ltree")

    def get_children_filter(self):
        """Return SQLAlchemy filter for direct children only."""
        # In ltree: path ~ '1.2.*{1}' matches direct children
        return text(f"path ~ '{self.path}.*{{1}}'::lquery")
