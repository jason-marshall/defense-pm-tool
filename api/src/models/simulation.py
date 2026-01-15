"""Simulation models for Monte Carlo analysis.

This module provides models for configuring and storing Monte Carlo
simulation results for schedule and cost risk analysis.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.program import Program
    from src.models.scenario import Scenario
    from src.models.user import User


class SimulationStatus:
    """Status values for simulations."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SimulationConfig(Base):
    """
    Monte Carlo simulation configuration.

    Defines:
    - Which activities have uncertainty
    - Distribution types and parameters
    - Number of iterations

    Example activity_distributions format:
    {
        "activity-uuid-1": {
            "distribution": "triangular",
            "min": 5,
            "mode": 10,
            "max": 20
        },
        "activity-uuid-2": {
            "distribution": "pert",
            "min": 8,
            "mode": 12,
            "max": 18
        }
    }

    Supported distributions:
    - triangular: min, mode, max
    - pert: min, mode, max (beta distribution)
    - normal: mean, std
    - uniform: min, max
    """

    __tablename__ = "simulation_configs"

    # Foreign key to Program
    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent program",
    )

    # Optional scenario to simulate
    scenario_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Optional scenario to simulate (if None, uses current data)",
    )

    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Simulation configuration name",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of simulation purpose",
    )

    # Number of iterations
    iterations: Mapped[int] = mapped_column(
        Integer,
        default=1000,
        nullable=False,
        comment="Number of Monte Carlo iterations",
    )

    # Activity duration uncertainty definitions
    # Format: {activity_id: {distribution: "triangular", min: 5, mode: 10, max: 20}}
    activity_distributions: Mapped[dict[str, dict[str, float | str]]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Activity duration distribution parameters",
    )

    # Cost uncertainty definitions (optional)
    cost_distributions: Mapped[dict[str, dict[str, float | str]] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Cost distribution parameters (optional)",
    )

    # Correlation matrix for correlated risks (optional)
    correlation_matrix: Mapped[dict[str, dict[str, float]] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Correlation coefficients between activities (optional)",
    )

    # Creator tracking
    created_by_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="User who created the simulation config",
    )

    # Relationships
    program: Mapped["Program"] = relationship(
        "Program",
        foreign_keys=[program_id],
    )

    scenario: Mapped["Scenario | None"] = relationship(
        "Scenario",
        foreign_keys=[scenario_id],
    )

    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )

    results: Mapped[list["SimulationResult"]] = relationship(
        "SimulationResult",
        back_populates="config",
        cascade="all, delete-orphan",
        order_by="SimulationResult.created_at.desc()",
    )

    # Table-level configuration
    __table_args__ = (
        Index(
            "ix_simulation_configs_program",
            "program_id",
            "deleted_at",
        ),
        {"comment": "Monte Carlo simulation configurations"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"<SimulationConfig(id={self.id}, name={self.name!r}, iterations={self.iterations})>"

    @property
    def activity_count(self) -> int:
        """Count of activities with uncertainty defined."""
        return len(self.activity_distributions) if self.activity_distributions else 0

    @property
    def has_cost_distributions(self) -> bool:
        """Check if cost distributions are defined."""
        return bool(self.cost_distributions)


class SimulationResult(Base):
    """
    Monte Carlo simulation results.

    Stores:
    - Percentile results (P10, P50, P80, P90)
    - Full distribution statistics
    - Histogram data for visualization
    - Execution metadata

    Duration results format:
    {
        "p10": 120,
        "p50": 145,
        "p80": 165,
        "p90": 180,
        "mean": 147.5,
        "std": 22.3,
        "min": 95,
        "max": 210
    }

    Histogram format:
    {
        "bins": [100, 110, 120, ...],
        "counts": [5, 12, 25, ...]
    }
    """

    __tablename__ = "simulation_results"

    # Foreign key to SimulationConfig
    config_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("simulation_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to simulation configuration",
    )

    # Execution status
    status: Mapped[str] = mapped_column(
        String(20),
        default=SimulationStatus.PENDING,
        nullable=False,
        index=True,
        comment="Simulation status (pending, running, completed, failed)",
    )

    # Execution timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When simulation started",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When simulation completed",
    )

    # Progress tracking
    iterations_completed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of iterations completed so far",
    )

    # Duration results
    duration_results: Mapped[dict[str, float] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Duration distribution: p10, p50, p80, p90, mean, std",
    )

    # Cost results (if cost distributions were provided)
    cost_results: Mapped[dict[str, float] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Cost distribution: p10, p50, p80, p90, mean, std",
    )

    # Histogram data for visualization
    duration_histogram: Mapped[dict[str, list[float]] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Duration histogram (bins and counts)",
    )

    cost_histogram: Mapped[dict[str, list[float]] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Cost histogram (bins and counts)",
    )

    # Activity-level results (critical path frequency, etc.)
    activity_results: Mapped[dict[str, dict[str, float]] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Per-activity statistics (criticality index, etc.)",
    )

    # Error information (if failed)
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if simulation failed",
    )

    # Seed used for reproducibility
    random_seed: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Random seed used (for reproducibility)",
    )

    # Relationships
    config: Mapped["SimulationConfig"] = relationship(
        "SimulationConfig",
        back_populates="results",
    )

    # Table-level configuration
    __table_args__ = (
        Index(
            "ix_simulation_results_config_status",
            "config_id",
            "status",
        ),
        {"comment": "Monte Carlo simulation results"},
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"<SimulationResult(id={self.id}, config_id={self.config_id}, "
            f"status={self.status}, iterations={self.iterations_completed})>"
        )

    @property
    def is_complete(self) -> bool:
        """Check if simulation completed successfully."""
        return self.status == SimulationStatus.COMPLETED

    @property
    def is_running(self) -> bool:
        """Check if simulation is currently running."""
        return self.status == SimulationStatus.RUNNING

    @property
    def duration_seconds(self) -> float | None:
        """Calculate simulation duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.config and self.config.iterations > 0:
            return (self.iterations_completed / self.config.iterations) * 100
        return 0.0
