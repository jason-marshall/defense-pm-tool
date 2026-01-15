"""Pydantic schemas for Monte Carlo simulations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DistributionParamsSchema(BaseModel):
    """Schema for distribution parameters."""

    distribution: str = Field(
        default="triangular",
        description="Distribution type (triangular, pert, normal, uniform)",
    )
    min_value: float | None = Field(
        None,
        alias="min",
        description="Minimum value (for triangular, pert, uniform)",
    )
    max_value: float | None = Field(
        None,
        alias="max",
        description="Maximum value (for triangular, pert, uniform)",
    )
    mode: float | None = Field(
        None,
        description="Most likely value (for triangular, pert)",
    )
    mean: float | None = Field(
        None,
        description="Mean value (for normal distribution)",
    )
    std: float | None = Field(
        None,
        description="Standard deviation (for normal distribution)",
    )

    model_config = {"populate_by_name": True}

    @field_validator("distribution")
    @classmethod
    def validate_distribution(cls, v: str) -> str:
        """Validate distribution type."""
        valid = {"triangular", "pert", "normal", "uniform"}
        if v.lower() not in valid:
            raise ValueError(f"Distribution must be one of: {', '.join(valid)}")
        return v.lower()


class SimulationConfigBase(BaseModel):
    """Base schema for simulation config."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    iterations: int = Field(default=1000, ge=100, le=100000)


class SimulationConfigCreate(SimulationConfigBase):
    """Schema for creating a simulation config."""

    program_id: UUID
    scenario_id: UUID | None = None
    activity_distributions: dict[str, DistributionParamsSchema] = Field(
        default_factory=dict,
        description="Activity duration distributions keyed by activity ID",
    )
    cost_distributions: dict[str, DistributionParamsSchema] | None = Field(
        None,
        description="Cost distributions keyed by activity ID (optional)",
    )

    @field_validator("activity_distributions")
    @classmethod
    def validate_activity_distributions(
        cls, v: dict[str, DistributionParamsSchema]
    ) -> dict[str, DistributionParamsSchema]:
        """Ensure at least one activity has distribution defined."""
        if not v:
            raise ValueError("At least one activity distribution must be defined")
        return v


class SimulationConfigUpdate(BaseModel):
    """Schema for updating a simulation config."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    iterations: int | None = Field(None, ge=100, le=100000)
    activity_distributions: dict[str, DistributionParamsSchema] | None = None
    cost_distributions: dict[str, DistributionParamsSchema] | None = None


class SimulationConfigResponse(SimulationConfigBase):
    """Schema for simulation config response."""

    id: UUID
    program_id: UUID
    scenario_id: UUID | None
    activity_distributions: dict[str, Any]
    cost_distributions: dict[str, Any] | None
    created_by_id: UUID
    created_at: datetime

    activity_count: int = Field(
        default=0,
        description="Number of activities with distributions",
    )

    model_config = {"from_attributes": True}


class SimulationResultBase(BaseModel):
    """Base schema for simulation results."""

    status: str
    iterations_completed: int


class SimulationRunRequest(BaseModel):
    """Schema for running a simulation."""

    seed: int | None = Field(
        None,
        description="Random seed for reproducibility",
    )
    include_activity_stats: bool = Field(
        default=False,
        description="Include per-activity statistics",
    )


class DurationResultsSchema(BaseModel):
    """Schema for duration simulation results."""

    p10: float = Field(description="10th percentile")
    p50: float = Field(description="50th percentile (median)")
    p80: float = Field(description="80th percentile")
    p90: float = Field(description="90th percentile")
    mean: float = Field(description="Mean value")
    std: float = Field(description="Standard deviation")
    min: float = Field(description="Minimum value")
    max: float = Field(description="Maximum value")


class HistogramSchema(BaseModel):
    """Schema for histogram data."""

    bins: list[float] = Field(description="Histogram bin edges")
    counts: list[int] = Field(description="Count in each bin")


class SimulationResultResponse(SimulationResultBase):
    """Schema for simulation result response."""

    id: UUID
    config_id: UUID
    started_at: datetime | None
    completed_at: datetime | None

    duration_results: DurationResultsSchema | None = None
    cost_results: DurationResultsSchema | None = None

    duration_histogram: HistogramSchema | None = None
    cost_histogram: HistogramSchema | None = None

    activity_stats: dict[str, dict[str, float]] | None = None

    error_message: str | None = None
    random_seed: int | None = None

    duration_seconds: float | None = Field(
        None,
        description="Simulation execution time in seconds",
    )
    progress_percent: float = Field(
        default=0.0,
        description="Progress percentage (0-100)",
    )

    model_config = {"from_attributes": True}


class SimulationSummaryResponse(BaseModel):
    """Schema for simulation summary (list view)."""

    id: UUID
    config_id: UUID
    config_name: str
    status: str
    iterations_completed: int
    total_iterations: int
    progress_percent: float
    duration_p50: float | None = None
    duration_p90: float | None = None
    cost_p50: float | None = None
    created_at: datetime
    completed_at: datetime | None


class QuickSimulationRequest(BaseModel):
    """Schema for quick simulation without saving config."""

    program_id: UUID
    activity_distributions: dict[str, DistributionParamsSchema]
    cost_distributions: dict[str, DistributionParamsSchema] | None = None
    iterations: int = Field(default=1000, ge=100, le=10000)
    seed: int | None = None
