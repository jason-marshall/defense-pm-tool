"""Domain enums for the Defense PM Tool.

This module centralizes all enum definitions used throughout the application.
All enums inherit from (str, Enum) for seamless JSON serialization.

Categories:
- User & Authorization: UserRole
- Program Management: ProgramStatus
- Scheduling: ConstraintType, ActivityStatus
- Dependencies: DependencyType
"""

from enum import Enum


class UserRole(str, Enum):
    """
    User roles for Role-Based Access Control (RBAC).

    Roles are hierarchical - higher roles include all permissions of lower roles:

    Permission Hierarchy (lowest to highest):
        VIEWER (1)          - Read-only access to assigned programs
        ANALYST (2)         - View + analyze data, run reports
        SCHEDULER (3)       - Analyst + create/modify activities and dependencies
        PROGRAM_MANAGER (4) - Scheduler + full control over assigned programs
        ADMIN (5)           - System-wide administration, all permissions

    Example:
        >>> user.role = UserRole.SCHEDULER
        >>> user.role.has_permission(UserRole.ANALYST)
        True
        >>> user.role.has_permission(UserRole.ADMIN)
        False
    """

    VIEWER = "viewer"
    ANALYST = "analyst"
    SCHEDULER = "scheduler"
    PROGRAM_MANAGER = "program_manager"
    ADMIN = "admin"

    @classmethod
    def get_hierarchy(cls) -> dict["UserRole", int]:
        """
        Get the permission hierarchy levels.

        Returns:
            Dictionary mapping roles to their hierarchy level (higher = more permissions)
        """
        return {
            cls.VIEWER: 1,
            cls.ANALYST: 2,
            cls.SCHEDULER: 3,
            cls.PROGRAM_MANAGER: 4,
            cls.ADMIN: 5,
        }

    def has_permission(self, required_role: "UserRole") -> bool:
        """
        Check if this role has at least the permissions of the required role.

        Args:
            required_role: The minimum role required for an action

        Returns:
            True if this role's level >= required role's level
        """
        hierarchy = self.get_hierarchy()
        return hierarchy[self] >= hierarchy[required_role]

    @property
    def level(self) -> int:
        """Get the hierarchy level for this role."""
        return self.get_hierarchy()[self]

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        return self.value.replace("_", " ").title()

    @classmethod
    def from_level(cls, level: int) -> "UserRole":
        """
        Get the role for a given hierarchy level.

        Args:
            level: Hierarchy level (1-5)

        Returns:
            UserRole corresponding to that level

        Raises:
            ValueError: If level is out of range
        """
        hierarchy = cls.get_hierarchy()
        for role, role_level in hierarchy.items():
            if role_level == level:
                return role
        raise ValueError(f"Invalid role level: {level}. Must be 1-5.")


class ProgramStatus(str, Enum):
    """
    Program lifecycle status.

    Tracks the current phase of a program from initial planning
    through completion or cancellation.

    Status Flow:
        PLANNING -> ACTIVE -> COMPLETE
                 -> ON_HOLD -> ACTIVE (resume)
                           -> CANCELLED
        ACTIVE -> ON_HOLD
               -> CANCELLED
               -> COMPLETE

    Business Rules:
        - PLANNING: Initial setup, WBS can be modified freely
        - ACTIVE: Program executing, changes tracked in baselines
        - ON_HOLD: Temporarily suspended, no progress updates
        - COMPLETE: Program finished, read-only
        - CANCELLED: Program terminated early, read-only
    """

    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETE = "complete"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"

    @property
    def is_editable(self) -> bool:
        """
        Check if program data can be edited in this status.

        Returns:
            True if status allows modifications
        """
        return self in (ProgramStatus.PLANNING, ProgramStatus.ACTIVE)

    @property
    def is_active(self) -> bool:
        """
        Check if program is in an active working state.

        Returns:
            True if program is being actively worked
        """
        return self in (ProgramStatus.PLANNING, ProgramStatus.ACTIVE)

    @property
    def is_terminal(self) -> bool:
        """
        Check if program is in a terminal (final) state.

        Returns:
            True if program cannot transition to another state
        """
        return self in (ProgramStatus.COMPLETE, ProgramStatus.CANCELLED)

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        return self.value.replace("_", " ").title()

    def can_transition_to(self, new_status: "ProgramStatus") -> bool:
        """
        Check if transition to new status is valid.

        Args:
            new_status: Target status

        Returns:
            True if transition is allowed
        """
        valid_transitions = {
            ProgramStatus.PLANNING: {
                ProgramStatus.ACTIVE,
                ProgramStatus.ON_HOLD,
                ProgramStatus.CANCELLED,
            },
            ProgramStatus.ACTIVE: {
                ProgramStatus.COMPLETE,
                ProgramStatus.ON_HOLD,
                ProgramStatus.CANCELLED,
            },
            ProgramStatus.ON_HOLD: {
                ProgramStatus.ACTIVE,
                ProgramStatus.CANCELLED,
            },
            ProgramStatus.COMPLETE: set(),  # No transitions from complete
            ProgramStatus.CANCELLED: set(),  # No transitions from cancelled
        }
        return new_status in valid_transitions.get(self, set())


class DependencyType(str, Enum):
    """
    Types of dependencies between activities in CPM scheduling.

    Dependency types define the logical relationship between a predecessor
    and successor activity. Each type determines how the successor's dates
    are calculated relative to the predecessor.

    Types:
        FS (Finish-to-Start):
            Most common (~90% of dependencies). Successor cannot start
            until predecessor finishes.
            Formula: successor.ES = predecessor.EF + lag
            Example: "Testing starts after Development finishes"

        SS (Start-to-Start):
            Successor cannot start until predecessor starts.
            Formula: successor.ES = predecessor.ES + lag
            Example: "Documentation starts 2 days after Development starts"

        FF (Finish-to-Finish):
            Successor cannot finish until predecessor finishes.
            Formula: successor.EF = predecessor.EF + lag
            Example: "Testing must finish when Development finishes"

        SF (Start-to-Finish):
            Rare. Successor cannot finish until predecessor starts.
            Formula: successor.EF = predecessor.ES + lag
            Example: "Old system runs until new system starts"

    Lag/Lead:
        Positive lag: Delay between activities
        Negative lag (lead): Overlap between activities
    """

    FS = "FS"  # Finish-to-Start (most common, ~90% of dependencies)
    SS = "SS"  # Start-to-Start
    FF = "FF"  # Finish-to-Finish
    SF = "SF"  # Start-to-Finish (rare)

    @property
    def full_name(self) -> str:
        """Get the full dependency type name."""
        names = {
            DependencyType.FS: "Finish-to-Start",
            DependencyType.SS: "Start-to-Start",
            DependencyType.FF: "Finish-to-Finish",
            DependencyType.SF: "Start-to-Finish",
        }
        return names[self]

    @property
    def description(self) -> str:
        """Get a description of the dependency type."""
        descriptions = {
            DependencyType.FS: "Successor starts after predecessor finishes",
            DependencyType.SS: "Successor starts after predecessor starts",
            DependencyType.FF: "Successor finishes after predecessor finishes",
            DependencyType.SF: "Successor finishes after predecessor starts",
        }
        return descriptions[self]

    @property
    def affects_start(self) -> bool:
        """
        Check if this dependency type affects successor's start date.

        Returns:
            True if FS or SS (affects Early Start calculation)
        """
        return self in (DependencyType.FS, DependencyType.SS)

    @property
    def affects_finish(self) -> bool:
        """
        Check if this dependency type affects successor's finish date.

        Returns:
            True if FF or SF (affects Early Finish calculation)
        """
        return self in (DependencyType.FF, DependencyType.SF)

    @property
    def uses_predecessor_finish(self) -> bool:
        """
        Check if this dependency uses predecessor's finish date.

        Returns:
            True if FS or FF
        """
        return self in (DependencyType.FS, DependencyType.FF)

    @property
    def uses_predecessor_start(self) -> bool:
        """
        Check if this dependency uses predecessor's start date.

        Returns:
            True if SS or SF
        """
        return self in (DependencyType.SS, DependencyType.SF)


class ConstraintType(str, Enum):
    """
    Activity scheduling constraint types for CPM calculations.

    Constraints affect how the CPM engine calculates activity dates.
    They can force activities to start or finish on specific dates
    regardless of predecessor dependencies.

    Types:
        ASAP (As Soon As Possible):
            Default constraint. Activity scheduled at earliest possible
            date based on dependencies. No constraint date needed.

        ALAP (As Late As Possible):
            Activity scheduled at latest possible date without delaying
            project. No constraint date needed.

        SNET (Start No Earlier Than):
            Activity cannot start before constraint_date.
            Use when work cannot begin until a specific date.
            Example: Waiting for equipment delivery

        SNLT (Start No Later Than):
            Activity must start by constraint_date.
            Use for deadline-driven starts.
            Example: Must begin testing by regulatory deadline

        FNET (Finish No Earlier Than):
            Activity cannot finish before constraint_date.
            Use when deliverable cannot be submitted early.
            Example: Contract milestone date

        FNLT (Finish No Later Than):
            Activity must finish by constraint_date.
            Use for hard deadlines.
            Example: Must complete before trade show

    Note:
        SNET, SNLT, FNET, and FNLT require a constraint_date to be set.
        ASAP and ALAP do not use constraint_date.
    """

    ASAP = "asap"  # As Soon As Possible (default)
    ALAP = "alap"  # As Late As Possible
    SNET = "snet"  # Start No Earlier Than
    SNLT = "snlt"  # Start No Later Than
    FNET = "fnet"  # Finish No Earlier Than
    FNLT = "fnlt"  # Finish No Later Than

    @property
    def full_name(self) -> str:
        """Get the full constraint type name."""
        names = {
            ConstraintType.ASAP: "As Soon As Possible",
            ConstraintType.ALAP: "As Late As Possible",
            ConstraintType.SNET: "Start No Earlier Than",
            ConstraintType.SNLT: "Start No Later Than",
            ConstraintType.FNET: "Finish No Earlier Than",
            ConstraintType.FNLT: "Finish No Later Than",
        }
        return names[self]

    @property
    def requires_date(self) -> bool:
        """
        Check if this constraint type requires a constraint_date.

        Returns:
            True if constraint needs a specific date
        """
        return self not in (ConstraintType.ASAP, ConstraintType.ALAP)

    @property
    def affects_start(self) -> bool:
        """
        Check if constraint affects activity start date.

        Returns:
            True if SNET or SNLT
        """
        return self in (ConstraintType.SNET, ConstraintType.SNLT)

    @property
    def affects_finish(self) -> bool:
        """
        Check if constraint affects activity finish date.

        Returns:
            True if FNET or FNLT
        """
        return self in (ConstraintType.FNET, ConstraintType.FNLT)

    @property
    def is_no_earlier_than(self) -> bool:
        """
        Check if this is a "no earlier than" constraint.

        Returns:
            True if SNET or FNET
        """
        return self in (ConstraintType.SNET, ConstraintType.FNET)

    @property
    def is_no_later_than(self) -> bool:
        """
        Check if this is a "no later than" constraint.

        Returns:
            True if SNLT or FNLT
        """
        return self in (ConstraintType.SNLT, ConstraintType.FNLT)


class EVMethod(str, Enum):
    """
    Earned Value (EV) calculation methods for EVMS compliance.

    Different activities require different methods for measuring earned value
    (BCWP - Budgeted Cost of Work Performed) based on their nature and duration.

    Methods:
        ZERO_HUNDRED (0/100):
            BCWP = 0 until complete, then BAC (full budget).
            Best for: Short discrete tasks (< 1 month)
            Example: Document review, inspection

        FIFTY_FIFTY (50/50):
            BCWP = 50% of BAC when started, 100% when complete.
            Best for: 1-2 month tasks where progress is hard to measure
            Example: Design tasks, analysis activities

        PERCENT_COMPLETE:
            BCWP = BAC * (percent_complete / 100)
            Default method. Best for: General use, measurable progress
            Example: Construction, manufacturing

        MILESTONE_WEIGHT:
            BCWP = BAC * sum(completed milestone weights)
            Best for: Long tasks (3+ months) with defined milestones
            Example: Software development phases

        LOE (Level of Effort):
            BCWP = BCWS (always equals planned value)
            Best for: Support activities, overhead tasks
            Example: Project management, quality assurance

        APPORTIONED:
            BCWP = factor * base_activity_BCWP
            Best for: Activities tied to another (deferred to Week 6)
            Example: Inspection tied to manufacturing

    EVMS Compliance:
        Per DI-MGMT-81466 and EIA-748, the EV method should match
        the work content and allow objective measurement of progress.
    """

    ZERO_HUNDRED = "0/100"
    FIFTY_FIFTY = "50/50"
    PERCENT_COMPLETE = "percent_complete"
    MILESTONE_WEIGHT = "milestone_weight"
    LOE = "loe"
    APPORTIONED = "apportioned"

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        names = {
            EVMethod.ZERO_HUNDRED: "0/100 (Discrete)",
            EVMethod.FIFTY_FIFTY: "50/50",
            EVMethod.PERCENT_COMPLETE: "Percent Complete",
            EVMethod.MILESTONE_WEIGHT: "Milestone Weight",
            EVMethod.LOE: "Level of Effort",
            EVMethod.APPORTIONED: "Apportioned Effort",
        }
        return names[self]

    @property
    def description(self) -> str:
        """Get description of the method."""
        descriptions = {
            EVMethod.ZERO_HUNDRED: "0% until complete, then 100%",
            EVMethod.FIFTY_FIFTY: "50% at start, 100% at finish",
            EVMethod.PERCENT_COMPLETE: "Based on reported percent complete",
            EVMethod.MILESTONE_WEIGHT: "Based on completed milestone weights",
            EVMethod.LOE: "Equals planned value (BCWP = BCWS)",
            EVMethod.APPORTIONED: "Based on related activity's earned value",
        }
        return descriptions[self]

    @property
    def recommended_duration(self) -> str:
        """Get recommended task duration for this method."""
        durations = {
            EVMethod.ZERO_HUNDRED: "< 1 month",
            EVMethod.FIFTY_FIFTY: "1-2 months",
            EVMethod.PERCENT_COMPLETE: "Any duration",
            EVMethod.MILESTONE_WEIGHT: "3+ months",
            EVMethod.LOE: "Any duration (support work)",
            EVMethod.APPORTIONED: "Tied to base activity",
        }
        return durations[self]

    @property
    def requires_milestones(self) -> bool:
        """Check if method requires milestone definitions."""
        return self == EVMethod.MILESTONE_WEIGHT

    @property
    def requires_base_activity(self) -> bool:
        """Check if method requires a base activity reference."""
        return self == EVMethod.APPORTIONED


class ActivityStatus(str, Enum):
    """
    Activity execution status.

    Tracks the current state of an activity during program execution.
    Status is typically derived from actual dates and percent complete,
    but can also be manually set.

    Status Flow:
        NOT_STARTED -> IN_PROGRESS -> COMPLETE
                    -> ON_HOLD -> IN_PROGRESS (resume)

    Derivation Rules:
        - NOT_STARTED: actual_start is None and percent_complete == 0
        - IN_PROGRESS: actual_start is set and percent_complete < 100
        - COMPLETE: percent_complete == 100 or actual_finish is set
        - ON_HOLD: Manually set when work is paused
    """

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    ON_HOLD = "on_hold"

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        return self.value.replace("_", " ").title()

    @property
    def is_active(self) -> bool:
        """
        Check if activity is in an active working state.

        Returns:
            True if work can be performed
        """
        return self == ActivityStatus.IN_PROGRESS

    @property
    def is_complete(self) -> bool:
        """
        Check if activity is finished.

        Returns:
            True if activity is complete
        """
        return self == ActivityStatus.COMPLETE

    @property
    def allows_progress_updates(self) -> bool:
        """
        Check if progress can be updated in this status.

        Returns:
            True if progress updates are allowed
        """
        return self in (ActivityStatus.NOT_STARTED, ActivityStatus.IN_PROGRESS)

    @classmethod
    def from_progress(
        cls,
        actual_start: bool,
        actual_finish: bool,
        percent_complete: float,
    ) -> "ActivityStatus":
        """
        Derive status from activity progress data.

        Args:
            actual_start: Whether actual_start date is set
            actual_finish: Whether actual_finish date is set
            percent_complete: Progress percentage (0-100)

        Returns:
            Derived ActivityStatus
        """
        if actual_finish or percent_complete >= 100:
            return cls.COMPLETE
        elif actual_start or percent_complete > 0:
            return cls.IN_PROGRESS
        else:
            return cls.NOT_STARTED


class ResourceType(str, Enum):
    """
    Resource type classification.

    Resources are categorized by their nature for proper handling
    of allocation, leveling, and cost calculations.

    Types:
        LABOR: Human resources (engineers, managers, technicians)
        EQUIPMENT: Machinery and tools with limited availability
        MATERIAL: Consumable supplies and components

    Cost Implications:
        - LABOR: Time-based cost (hours * rate)
        - EQUIPMENT: Time-based or usage-based cost
        - MATERIAL: Unit-based cost (quantity * unit price)

    Leveling Behavior:
        - LABOR: Can be overallocated (overtime) within limits
        - EQUIPMENT: Strict capacity constraints
        - MATERIAL: No leveling (consumed, not time-bound)
    """

    LABOR = "labor"
    EQUIPMENT = "equipment"
    MATERIAL = "material"

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        return self.value.title()

    @property
    def is_time_based(self) -> bool:
        """Check if resource is allocated by time."""
        return self in (ResourceType.LABOR, ResourceType.EQUIPMENT)

    @property
    def supports_leveling(self) -> bool:
        """Check if resource type supports leveling."""
        return self in (ResourceType.LABOR, ResourceType.EQUIPMENT)
