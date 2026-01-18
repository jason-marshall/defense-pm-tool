"""Scenario simulation service for Monte Carlo what-if analysis.

This service applies scenario changes to base activities and runs
Monte Carlo simulations through the CPM network to evaluate the
impact of proposed changes.

Key features:
- Apply scenario changes (duration, cost) to activities
- Run Monte Carlo simulation with modified activities
- Compare baseline vs scenario simulation results
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.models.activity import Activity
from src.models.dependency import Dependency
from src.models.scenario import Scenario, ScenarioChange
from src.services.monte_carlo import DistributionParams, DistributionType
from src.services.monte_carlo_cpm import (
    NetworkMonteCarloEngine,
    NetworkSimulationInput,
    NetworkSimulationOutput,
)


@dataclass
class ModifiedActivity:
    """Activity with scenario changes applied."""

    id: UUID
    duration: int
    budgeted_cost: Decimal
    name: str
    code: str | None = None


@dataclass
class ScenarioComparisonResult:
    """Result of comparing baseline vs scenario simulations."""

    # Duration changes
    p50_delta: float
    p90_delta: float
    mean_delta: float

    # Risk changes
    std_delta: float
    risk_improved: bool

    # Criticality changes (activity_id -> delta %)
    criticality_changes: dict[UUID, float]

    # Summary
    summary: str


class ScenarioSimulationService:
    """
    Service for running Monte Carlo simulations on scenarios.

    Applies scenario changes to base activities before simulation,
    enabling what-if analysis without modifying actual program data.

    Example usage:
        service = ScenarioSimulationService(
            activities=activities,
            dependencies=dependencies,
            scenario=scenario,
            changes=changes,
        )
        output = service.simulate(distributions, iterations=1000)
    """

    def __init__(
        self,
        activities: list[Activity],
        dependencies: list[Dependency],
        scenario: Scenario,
        changes: list[ScenarioChange],
    ) -> None:
        """
        Initialize scenario simulation service.

        Args:
            activities: Base activities from program
            dependencies: Dependencies between activities
            scenario: Scenario being simulated
            changes: List of changes to apply
        """
        self.base_activities = activities
        self.dependencies = dependencies
        self.scenario = scenario
        self.changes = changes
        self._change_map: dict[UUID, list[ScenarioChange]] | None = None

    def apply_changes(self) -> list[ModifiedActivity]:
        """
        Apply scenario changes to create modified activity list.

        Returns:
            List of ModifiedActivity with changes applied
        """
        change_map = self._build_change_map()
        modified_activities: list[ModifiedActivity] = []

        for activity in self.base_activities:
            # Create modified copy with base values
            modified = ModifiedActivity(
                id=activity.id,
                duration=activity.duration or 0,
                budgeted_cost=activity.budgeted_cost or Decimal("0"),
                name=activity.name,
                code=activity.code,
            )

            # Apply changes for this activity
            if activity.id in change_map:
                for change in change_map[activity.id]:
                    self._apply_change(modified, change)

            modified_activities.append(modified)

        return modified_activities

    def _apply_change(
        self,
        activity: ModifiedActivity,
        change: ScenarioChange,
    ) -> None:
        """Apply a single change to an activity."""
        if change.change_type == "delete":
            # Mark for exclusion (set duration to 0)
            activity.duration = 0
            return

        if change.field_name and change.new_value is not None:
            new_val = change.new_value

            # Handle JSON-wrapped values
            if isinstance(new_val, dict) and "value" in new_val:
                new_val = new_val["value"]

            if change.field_name == "duration":
                activity.duration = int(str(new_val))
            elif change.field_name == "budgeted_cost":
                activity.budgeted_cost = Decimal(str(new_val))
            elif change.field_name == "name":
                activity.name = str(new_val)

    def _build_change_map(self) -> dict[UUID, list[ScenarioChange]]:
        """Build map of entity_id -> changes for quick lookup."""
        if self._change_map is not None:
            return self._change_map

        self._change_map = {}
        for change in self.changes:
            if change.entity_type == "activity":
                if change.entity_id not in self._change_map:
                    self._change_map[change.entity_id] = []
                self._change_map[change.entity_id].append(change)

        return self._change_map

    def simulate(
        self,
        distributions: dict[UUID, DistributionParams] | None = None,
        iterations: int = 1000,
        seed: int | None = None,
    ) -> NetworkSimulationOutput:
        """
        Run Monte Carlo simulation on scenario.

        Args:
            distributions: Duration distributions for activities.
                          If None, default triangular +-20% is used.
            iterations: Number of simulation iterations
            seed: Optional random seed for reproducibility

        Returns:
            NetworkSimulationOutput with simulation results
        """
        # Apply scenario changes
        modified_activities = self.apply_changes()

        # Build default distributions if not provided
        if distributions is None:
            distributions = self._build_default_distributions(modified_activities)

        # Update distributions for changed activities
        distributions = self._update_distributions_for_changes(distributions, modified_activities)

        # Run simulation
        engine = NetworkMonteCarloEngine(seed=seed)
        sim_input = NetworkSimulationInput(
            activities=modified_activities,  # type: ignore
            dependencies=self.dependencies,  # type: ignore
            duration_distributions=distributions,
            iterations=iterations,
            seed=seed,
        )

        return engine.simulate(sim_input)

    def _build_default_distributions(
        self,
        activities: list[ModifiedActivity],
    ) -> dict[UUID, DistributionParams]:
        """Build default triangular distributions (+-20% of duration)."""
        distributions: dict[UUID, DistributionParams] = {}

        for activity in activities:
            if activity.duration and activity.duration > 0:
                base = float(activity.duration)
                distributions[activity.id] = DistributionParams(
                    distribution=DistributionType.TRIANGULAR,
                    min_value=base * 0.8,
                    mode=base,
                    max_value=base * 1.2,
                )

        return distributions

    def _update_distributions_for_changes(
        self,
        distributions: dict[UUID, DistributionParams],
        modified_activities: list[ModifiedActivity],
    ) -> dict[UUID, DistributionParams]:
        """Update distributions based on modified activity durations."""
        change_map = self._build_change_map()
        updated = dict(distributions)

        for activity in modified_activities:
            # If activity had duration change, update its distribution
            if activity.id in change_map:
                for change in change_map[activity.id]:
                    if change.field_name == "duration" and activity.duration > 0:
                        base = float(activity.duration)
                        updated[activity.id] = DistributionParams(
                            distribution=DistributionType.TRIANGULAR,
                            min_value=base * 0.8,
                            mode=base,
                            max_value=base * 1.2,
                        )

        return updated


def compare_scenario_simulations(
    baseline_output: NetworkSimulationOutput,
    scenario_output: NetworkSimulationOutput,
) -> ScenarioComparisonResult:
    """
    Compare simulation results between baseline and scenario.

    Args:
        baseline_output: Simulation results without scenario changes
        scenario_output: Simulation results with scenario changes

    Returns:
        ScenarioComparisonResult with comparison metrics
    """
    # Duration deltas
    p50_delta = scenario_output.project_duration_p50 - baseline_output.project_duration_p50
    p90_delta = scenario_output.project_duration_p90 - baseline_output.project_duration_p90
    mean_delta = scenario_output.project_duration_mean - baseline_output.project_duration_mean

    # Risk deltas
    std_delta = scenario_output.project_duration_std - baseline_output.project_duration_std
    risk_improved = std_delta < 0

    # Criticality changes
    all_activity_ids = set(baseline_output.activity_criticality.keys()) | set(
        scenario_output.activity_criticality.keys()
    )
    criticality_changes: dict[UUID, float] = {}
    for act_id in all_activity_ids:
        baseline_crit = baseline_output.activity_criticality.get(act_id, 0)
        scenario_crit = scenario_output.activity_criticality.get(act_id, 0)
        criticality_changes[act_id] = scenario_crit - baseline_crit

    # Build summary
    if mean_delta < 0:
        duration_summary = f"reduces duration by {abs(mean_delta):.1f} days"
    elif mean_delta > 0:
        duration_summary = f"increases duration by {mean_delta:.1f} days"
    else:
        duration_summary = "no change to duration"

    if risk_improved:
        risk_summary = f"reduces risk (std: {abs(std_delta):.1f} days)"
    elif std_delta > 0:
        risk_summary = f"increases risk (std: +{std_delta:.1f} days)"
    else:
        risk_summary = "no change to risk"

    summary = f"Scenario {duration_summary} and {risk_summary}"

    return ScenarioComparisonResult(
        p50_delta=p50_delta,
        p90_delta=p90_delta,
        mean_delta=mean_delta,
        std_delta=std_delta,
        risk_improved=risk_improved,
        criticality_changes=criticality_changes,
        summary=summary,
    )


def build_scenario_distributions(
    activities: list[Any],
    custom_distributions: dict[UUID, dict[str, Any]] | None = None,
    uncertainty_factor: float = 0.2,
) -> dict[UUID, DistributionParams]:
    """
    Build distribution parameters for scenario simulation.

    Args:
        activities: List of activities with id and duration
        custom_distributions: Optional custom distributions by activity ID
        uncertainty_factor: Default uncertainty as fraction of duration (default 20%)

    Returns:
        Dict mapping activity ID to DistributionParams
    """
    distributions: dict[UUID, DistributionParams] = {}

    for activity in activities:
        activity_id = activity.id if hasattr(activity, "id") else activity["id"]
        duration = (
            activity.duration if hasattr(activity, "duration") else activity.get("duration", 0)
        )

        if not duration or duration <= 0:
            continue

        # Check for custom distribution
        if custom_distributions and activity_id in custom_distributions:
            custom = custom_distributions[activity_id]
            distributions[activity_id] = DistributionParams(
                distribution=DistributionType(custom.get("distribution", "triangular")),
                min_value=custom.get("min_value"),
                max_value=custom.get("max_value"),
                mode=custom.get("mode"),
                mean=custom.get("mean"),
                std=custom.get("std"),
            )
        else:
            # Use default triangular distribution
            base = float(duration)
            distributions[activity_id] = DistributionParams(
                distribution=DistributionType.TRIANGULAR,
                min_value=base * (1 - uncertainty_factor),
                mode=base,
                max_value=base * (1 + uncertainty_factor),
            )

    return distributions
