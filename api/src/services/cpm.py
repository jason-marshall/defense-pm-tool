"""Critical Path Method (CPM) scheduling engine."""

from dataclasses import dataclass
from uuid import UUID

import networkx as nx

from src.core.exceptions import CircularDependencyError, ScheduleCalculationError
from src.models.activity import Activity
from src.models.dependency import Dependency, DependencyType


@dataclass
class ScheduleResult:
    """Result of CPM calculation for a single activity."""

    activity_id: UUID
    early_start: int  # Days from project start
    early_finish: int
    late_start: int
    late_finish: int
    total_float: int
    free_float: int

    @property
    def is_critical(self) -> bool:
        """Activity is critical if total float is zero."""
        return self.total_float == 0


class CPMEngine:
    """
    Critical Path Method scheduling engine.

    Calculates Early Start (ES), Early Finish (EF), Late Start (LS),
    Late Finish (LF), and float for all activities based on their
    dependencies.

    Supports all four dependency types:
    - FS (Finish-to-Start): successor.ES = predecessor.EF + lag
    - SS (Start-to-Start): successor.ES = predecessor.ES + lag
    - FF (Finish-to-Finish): successor.EF = predecessor.EF + lag
    - SF (Start-to-Finish): successor.EF = predecessor.ES + lag
    """

    def __init__(
        self,
        activities: list[Activity],
        dependencies: list[Dependency],
    ) -> None:
        """
        Initialize CPM engine with activities and dependencies.

        Args:
            activities: List of activities to schedule
            dependencies: List of dependencies between activities
        """
        self.activities = {a.id: a for a in activities}
        self.dependencies = dependencies
        self.graph = self._build_graph()
        self.results: dict[UUID, ScheduleResult] = {}

    def _build_graph(self) -> nx.DiGraph:
        """Build directed graph from activities and dependencies."""
        graph = nx.DiGraph()

        # Add all activities as nodes
        for activity_id, activity in self.activities.items():
            graph.add_node(activity_id, duration=activity.duration)

        # Add dependencies as edges
        for dep in self.dependencies:
            graph.add_edge(
                dep.predecessor_id,
                dep.successor_id,
                dependency_type=dep.dependency_type,
                lag=dep.lag,
            )

        return graph

    def _detect_cycles(self) -> list[UUID]:
        """Detect and return cycle path if present."""
        try:
            cycle = nx.find_cycle(self.graph)
            return [edge[0] for edge in cycle] + [cycle[-1][1]]
        except nx.NetworkXNoCycle:
            return []

    def calculate(self) -> dict[UUID, ScheduleResult]:
        """
        Perform full CPM calculation.

        Returns:
            Dictionary mapping activity ID to ScheduleResult

        Raises:
            CircularDependencyError: If dependency graph contains cycles
            ScheduleCalculationError: If calculation fails
        """
        # Check for cycles
        cycle_path = self._detect_cycles()
        if cycle_path:
            raise CircularDependencyError(cycle_path)

        # Perform forward and backward passes
        self._forward_pass()
        self._backward_pass()
        self._calculate_float()

        return self.results

    def _forward_pass(self) -> None:
        """
        Calculate Early Start (ES) and Early Finish (EF) for all activities.

        Processes activities in topological order to ensure predecessors
        are calculated before successors.
        """
        # Initialize results with zero ES for all activities
        for activity_id, activity in self.activities.items():
            self.results[activity_id] = ScheduleResult(
                activity_id=activity_id,
                early_start=0,
                early_finish=activity.duration,
                late_start=0,
                late_finish=0,
                total_float=0,
                free_float=0,
            )

        # Process in topological order
        try:
            order = list(nx.topological_sort(self.graph))
        except nx.NetworkXUnfeasible as e:
            raise ScheduleCalculationError(
                "Could not determine activity order",
                "TOPOLOGICAL_SORT_FAILED",
            ) from e

        for activity_id in order:
            activity = self.activities[activity_id]
            max_es = 0

            # Check all predecessor dependencies
            for pred_id in self.graph.predecessors(activity_id):
                edge_data = self.graph.edges[pred_id, activity_id]
                dep_type = edge_data["dependency_type"]
                lag = edge_data["lag"]

                pred_result = self.results[pred_id]

                # Calculate ES based on dependency type
                match dep_type:
                    case DependencyType.FS.value:
                        # Successor starts after predecessor finishes
                        es = pred_result.early_finish + lag
                    case DependencyType.SS.value:
                        # Successor starts after predecessor starts
                        es = pred_result.early_start + lag
                    case DependencyType.FF.value:
                        # Successor finishes after predecessor finishes
                        # ES = pred.EF + lag - duration
                        es = pred_result.early_finish + lag - activity.duration
                    case DependencyType.SF.value:
                        # Successor finishes after predecessor starts
                        # ES = pred.ES + lag - duration
                        es = pred_result.early_start + lag - activity.duration
                    case _:
                        es = pred_result.early_finish + lag

                max_es = max(max_es, es)

            # Ensure ES is not negative
            max_es = max(0, max_es)

            self.results[activity_id].early_start = max_es
            self.results[activity_id].early_finish = max_es + activity.duration

    def _backward_pass(self) -> None:
        """
        Calculate Late Start (LS) and Late Finish (LF) for all activities.

        Processes activities in reverse topological order.
        """
        # Find project end (maximum EF)
        project_end = max(r.early_finish for r in self.results.values())

        # Initialize LF for all activities to project end
        for result in self.results.values():
            result.late_finish = project_end
            activity = self.activities[result.activity_id]
            result.late_start = project_end - activity.duration

        # Process in reverse topological order
        order = list(reversed(list(nx.topological_sort(self.graph))))

        for activity_id in order:
            activity = self.activities[activity_id]
            min_lf = self.results[activity_id].late_finish

            # Check all successor dependencies
            for succ_id in self.graph.successors(activity_id):
                edge_data = self.graph.edges[activity_id, succ_id]
                dep_type = edge_data["dependency_type"]
                lag = edge_data["lag"]

                succ_result = self.results[succ_id]

                # Calculate LF based on dependency type
                match dep_type:
                    case DependencyType.FS.value:
                        # Predecessor finishes before successor starts
                        lf = succ_result.late_start - lag
                    case DependencyType.SS.value:
                        # Predecessor starts before successor starts
                        # LF = succ.LS - lag + duration
                        lf = succ_result.late_start - lag + activity.duration
                    case DependencyType.FF.value:
                        # Predecessor finishes before successor finishes
                        lf = succ_result.late_finish - lag
                    case DependencyType.SF.value:
                        # Predecessor starts before successor finishes
                        # LF = succ.LF - lag + duration
                        lf = succ_result.late_finish - lag + activity.duration
                    case _:
                        lf = succ_result.late_start - lag

                min_lf = min(min_lf, lf)

            self.results[activity_id].late_finish = min_lf
            self.results[activity_id].late_start = min_lf - activity.duration

    def _calculate_float(self) -> None:
        """Calculate total float and free float for all activities."""
        for activity_id, result in self.results.items():
            # Total float = LS - ES = LF - EF
            result.total_float = result.late_start - result.early_start

            # Free float = min(successor.ES) - EF (for FS dependencies)
            min_successor_es = float("inf")

            for succ_id in self.graph.successors(activity_id):
                edge_data = self.graph.edges[activity_id, succ_id]
                dep_type = edge_data["dependency_type"]
                lag = edge_data["lag"]

                succ_result = self.results[succ_id]

                if dep_type == DependencyType.FS.value:
                    min_successor_es = min(
                        min_successor_es,
                        succ_result.early_start - lag,
                    )

            if min_successor_es == float("inf"):
                # No successors, free float equals total float
                result.free_float = result.total_float
            else:
                result.free_float = int(min_successor_es) - result.early_finish

    def get_critical_path(self) -> list[UUID]:
        """
        Get the critical path (activities with zero total float).

        Returns:
            List of activity IDs on the critical path, in order
        """
        if not self.results:
            self.calculate()

        critical_activities = [
            (aid, self.results[aid].early_start)
            for aid in self.results
            if self.results[aid].is_critical
        ]

        # Sort by early start to get proper order
        critical_activities.sort(key=lambda x: x[1])

        return [aid for aid, _ in critical_activities]

    def get_project_duration(self) -> int:
        """Get the total project duration in days."""
        if not self.results:
            self.calculate()

        return max(r.early_finish for r in self.results.values())
