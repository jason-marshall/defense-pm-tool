"""Scenario models for what-if analysis and planning.

Scenarios allow users to explore schedule/cost variations without
modifying the actual program data. Changes are stored as deltas
that can be applied or discarded.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.baseline import Baseline
    from src.models.program import Program
    from src.models.user import User


class ScenarioStatus(str):
    """Status values for scenarios."""

    DRAFT = "draft"
    ACTIVE = "active"
    PROMOTED = "promoted"
    ARCHIVED = "archived"


class ChangeType(str):
    """Types of changes in a scenario."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class EntityType(str):
    """Entity types that can be changed in a scenario."""

    ACTIVITY = "activity"
    DEPENDENCY = "dependency"
    WBS = "wbs"


class Scenario(Base):
    """
    Represents a what-if scenario for program planning.

    Scenarios allow exploring alternative schedules and costs without
    modifying actual program data. Changes are tracked as deltas and
    can be promoted to become the new baseline or discarded.

    Key features:
    - Branching: Scenarios can branch from baselines or other scenarios
    - Delta tracking: Only changes are stored, not full copies
    - CPM caching: Results are cached for performance
    - Promotion: Scenarios can become new baselines

    Attributes:
        program_id: FK to parent program
        baseline_id: Optional FK to reference baseline
        parent_scenario_id: Optional FK for scenario branching
        name: Scenario name
        description: Detailed description
        status: Current status (draft, active, promoted, archived)
        is_active: Whether scenario is actively being used
        changes_json: JSON array of delta changes
        results_cache: Cached CPM calculation results
        created_by_id: User who created the scenario
        promoted_at: When promoted to baseline
        promoted_baseline_id: FK to resulting baseline
    """

    __tablename__ = "scenarios"

    # Foreign key to Program
    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent program",
    )

    # Optional reference baseline
    baseline_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("baselines.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to reference baseline (if branched from baseline)",
    )

    # Optional parent scenario (for branching)
    parent_scenario_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to parent scenario (if branched from scenario)",
    )

    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Scenario name",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description",
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ScenarioStatus.DRAFT,
        comment="Scenario status (draft, active, promoted, archived)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether scenario is actively being used",
    )

    # Changes stored as JSON array of deltas
    changes_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON array of delta changes",
    )

    # Cached CPM results
    results_cache: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Cached CPM calculation results",
    )

    # Creator tracking
    created_by_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="User who created the scenario",
    )

    # Promotion tracking
    promoted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When promoted to baseline",
    )

    promoted_baseline_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("baselines.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to resulting baseline (if promoted)",
    )

    # Relationships
    program: Mapped["Program"] = relationship(
        "Program",
        foreign_keys=[program_id],
    )

    baseline: Mapped["Baseline | None"] = relationship(
        "Baseline",
        foreign_keys=[baseline_id],
    )

    parent_scenario: Mapped["Scenario | None"] = relationship(
        "Scenario",
        remote_side="Scenario.id",
        foreign_keys=[parent_scenario_id],
        backref="child_scenarios",
    )

    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )

    promoted_baseline: Mapped["Baseline | None"] = relationship(
        "Baseline",
        foreign_keys=[promoted_baseline_id],
    )

    # Relationship to changes
    changes: Mapped[list["ScenarioChange"]] = relationship(
        "ScenarioChange",
        back_populates="scenario",
        cascade="all, delete-orphan",
        order_by="ScenarioChange.created_at",
    )

    # Table-level configuration
    __table_args__ = (
        # Index for finding active scenarios
        Index(
            "ix_scenarios_active",
            "program_id",
            "is_active",
            postgresql_where="is_active = true AND deleted_at IS NULL",
        ),
        # Index for status queries
        Index(
            "ix_scenarios_status",
            "program_id",
            "status",
        ),
        {"comment": "What-if scenarios for program planning"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<Scenario(id={self.id}, name={self.name!r}, "
            f"status={self.status}, is_active={self.is_active})>"
        )

    @property
    def is_draft(self) -> bool:
        """Check if scenario is in draft status."""
        return self.status == ScenarioStatus.DRAFT

    @property
    def is_promoted(self) -> bool:
        """Check if scenario has been promoted to baseline."""
        return self.status == ScenarioStatus.PROMOTED

    @property
    def change_count(self) -> int:
        """Count of changes in this scenario."""
        if self.changes_json:
            return len(self.changes_json.get("changes", []))
        return len(self.changes) if self.changes else 0

    @property
    def has_cached_results(self) -> bool:
        """Check if scenario has cached CPM results."""
        return self.results_cache is not None

    def invalidate_cache(self) -> None:
        """Invalidate cached results (call after changes)."""
        self.results_cache = None


class ScenarioChange(Base):
    """
    Represents a single change within a scenario.

    Changes track modifications to activities, dependencies, or WBS
    elements. Each change records the entity, field, and old/new values.

    Attributes:
        scenario_id: FK to parent scenario
        entity_type: Type of entity (activity, dependency, wbs)
        entity_id: ID of the entity being changed
        entity_code: Code/identifier of the entity (for display)
        change_type: Type of change (create, update, delete)
        field_name: Name of field being changed (for updates)
        old_value: Previous value (JSON for complex fields)
        new_value: New value (JSON for complex fields)
    """

    __tablename__ = "scenario_changes"

    # Foreign key to Scenario
    scenario_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent scenario",
    )

    # Entity identification
    entity_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Entity type (activity, dependency, wbs)",
    )

    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="ID of entity being changed",
    )

    entity_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Code/identifier of entity (for display)",
    )

    # Change details
    change_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Change type (create, update, delete)",
    )

    field_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Field name being changed (for updates)",
    )

    old_value: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Previous value",
    )

    new_value: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="New value",
    )

    # Relationship back to scenario
    scenario: Mapped["Scenario"] = relationship(
        "Scenario",
        back_populates="changes",
    )

    # Table-level configuration
    __table_args__ = (
        # Index for finding changes by entity
        Index(
            "ix_scenario_changes_entity",
            "scenario_id",
            "entity_type",
            "entity_id",
        ),
        {"comment": "Individual changes within scenarios"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<ScenarioChange(id={self.id}, scenario_id={self.scenario_id}, "
            f"entity_type={self.entity_type}, change_type={self.change_type})>"
        )

    @property
    def is_create(self) -> bool:
        """Check if this is a create change."""
        return self.change_type == ChangeType.CREATE

    @property
    def is_update(self) -> bool:
        """Check if this is an update change."""
        return self.change_type == ChangeType.UPDATE

    @property
    def is_delete(self) -> bool:
        """Check if this is a delete change."""
        return self.change_type == ChangeType.DELETE
