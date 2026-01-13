"""MS Project XML import service.

This module provides functionality to parse MS Project XML files and convert
them to internal data structures for import into the system.

Supported elements:
- Tasks with duration, dates, WBS codes
- Predecessor links (FS, SS, FF, SF)
- Milestones
- Constraints (SNET, SNLT, FNET, FNLT)
- Notes

Not supported (logged as warnings):
- Resources and assignments
- Calendars (assumes 8hr days)
- Custom fields
- Cost data (imported separately)
"""

import contextlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import ClassVar
from uuid import UUID, uuid4

from src.core.exceptions import ValidationError
from src.models.activity import Activity
from src.models.dependency import Dependency
from src.models.enums import ConstraintType, DependencyType
from src.models.wbs import WBSElement
from src.repositories.wbs import WBSElementRepository


@dataclass
class ImportedTask:
    """Parsed task from MS Project XML."""

    uid: int
    id: int
    name: str
    wbs: str
    outline_level: int
    duration_hours: float
    start: datetime | None
    finish: datetime | None
    is_milestone: bool
    is_summary: bool
    predecessors: list[dict] = field(default_factory=list)
    constraint_type: str | None = None
    constraint_date: datetime | None = None
    percent_complete: Decimal = field(default_factory=lambda: Decimal("0"))
    notes: str | None = None


@dataclass
class ImportedProject:
    """Parsed project from MS Project XML."""

    name: str
    start_date: datetime
    finish_date: datetime
    tasks: list[ImportedTask]
    warnings: list[str] = field(default_factory=list)


class MSProjectImporter:
    """
    MS Project XML file importer.

    Parses MS Project XML format (2010-2021 compatible) and converts
    to internal data structures for import into the system.
    """

    NAMESPACE: ClassVar[dict[str, str]] = {
        "msp": "http://schemas.microsoft.com/project"
    }

    # MS Project dependency type mapping
    # 0 = FF, 1 = FS, 2 = SF, 3 = SS
    DEPENDENCY_TYPE_MAP: ClassVar[dict[int, DependencyType]] = {
        0: DependencyType.FF,
        1: DependencyType.FS,
        2: DependencyType.SF,
        3: DependencyType.SS,
    }

    # MS Project constraint type mapping
    CONSTRAINT_TYPE_MAP: ClassVar[dict[int, ConstraintType | None]] = {
        0: None,  # As Soon As Possible
        1: None,  # As Late As Possible
        2: ConstraintType.SNET,  # Start No Earlier Than
        3: ConstraintType.SNLT,  # Start No Later Than
        4: ConstraintType.FNET,  # Finish No Earlier Than
        5: ConstraintType.FNLT,  # Finish No Later Than
        6: None,  # Must Finish On (not supported, logged as warning)
        7: None,  # Must Start On (not supported, logged as warning)
    }

    def __init__(self, file_path: str | Path) -> None:
        """
        Initialize importer with file path.

        Args:
            file_path: Path to MS Project XML file
        """
        self.file_path = Path(file_path)
        self.warnings: list[str] = []

    def parse(self) -> ImportedProject:
        """
        Parse MS Project XML file.

        Returns:
            ImportedProject with parsed tasks and metadata

        Raises:
            ValidationError: If file is invalid or cannot be parsed
        """
        if not self.file_path.exists():
            raise ValidationError(f"File not found: {self.file_path}")

        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
        except ET.ParseError as e:
            raise ValidationError(f"Invalid XML: {e}") from e

        # Handle namespace - check if root tag has namespace
        ns = self.NAMESPACE if root.tag.startswith("{") else {}

        # Parse project metadata
        name = self._get_text(root, "Name", ns) or self.file_path.stem
        start_date = self._parse_date(self._get_text(root, "StartDate", ns))
        finish_date = self._parse_date(self._get_text(root, "FinishDate", ns))

        if not start_date:
            start_date = datetime.now()
            self.warnings.append("No project start date found, using today")

        if not finish_date:
            finish_date = start_date + timedelta(days=365)
            self.warnings.append("No project finish date found, defaulting to 1 year")

        # Parse tasks
        tasks = self._parse_tasks(root, ns)

        return ImportedProject(
            name=name,
            start_date=start_date,
            finish_date=finish_date,
            tasks=tasks,
            warnings=self.warnings,
        )

    def _parse_tasks(self, root: ET.Element, ns: dict) -> list[ImportedTask]:
        """Parse all tasks from XML."""
        tasks = []

        tasks_element = root.find("msp:Tasks", ns) if ns else root.find("Tasks")
        if tasks_element is None:
            self.warnings.append("No Tasks element found")
            return tasks

        for task_elem in (
            tasks_element.findall("msp:Task", ns)
            if ns
            else tasks_element.findall("Task")
        ):
            task = self._parse_task(task_elem, ns)
            if task:
                tasks.append(task)

        return tasks

    def _parse_task(self, elem: ET.Element, ns: dict) -> ImportedTask | None:
        """Parse a single task element."""
        uid = self._get_int(elem, "UID", ns)
        if uid is None:
            return None

        # Skip null tasks (MSP uses UID 0 as placeholder)
        is_null = self._get_int(elem, "IsNull", ns)
        if is_null == 1:
            return None

        name = self._get_text(elem, "Name", ns) or f"Task {uid}"
        wbs = self._get_text(elem, "WBS", ns) or str(uid)
        outline_level = self._get_int(elem, "OutlineLevel", ns) or 1

        # Parse duration (ISO 8601 duration format: PT8H0M0S)
        duration_str = self._get_text(elem, "Duration", ns) or "PT0H0M0S"
        duration_hours = self._parse_duration(duration_str)

        # Parse dates
        start = self._parse_date(self._get_text(elem, "Start", ns))
        finish = self._parse_date(self._get_text(elem, "Finish", ns))

        # Flags
        is_milestone = self._get_int(elem, "Milestone", ns) == 1
        is_summary = self._get_int(elem, "Summary", ns) == 1

        # Percent complete
        pct = self._get_int(elem, "PercentComplete", ns) or 0
        percent_complete = Decimal(str(pct))

        # Constraint
        constraint_type, constraint_date = self._parse_constraint(elem, ns, name)

        # Notes
        notes = self._get_text(elem, "Notes", ns)

        # Parse predecessors
        predecessors = self._parse_predecessors(elem, ns)

        return ImportedTask(
            uid=uid,
            id=self._get_int(elem, "ID", ns) or uid,
            name=name,
            wbs=wbs,
            outline_level=outline_level,
            duration_hours=duration_hours,
            start=start,
            finish=finish,
            is_milestone=is_milestone,
            is_summary=is_summary,
            predecessors=predecessors,
            constraint_type=constraint_type,
            constraint_date=constraint_date,
            percent_complete=percent_complete,
            notes=notes,
        )

    def _parse_constraint(
        self, elem: ET.Element, ns: dict, task_name: str
    ) -> tuple[str | None, datetime | None]:
        """Parse constraint type and date for a task."""
        constraint_type_id = self._get_int(elem, "ConstraintType", ns)
        if constraint_type_id is None:
            return None, None

        mapped_constraint = self.CONSTRAINT_TYPE_MAP.get(constraint_type_id)
        if mapped_constraint:
            constraint_type = mapped_constraint.value
            constraint_date = self._parse_date(
                self._get_text(elem, "ConstraintDate", ns)
            )
            return constraint_type, constraint_date

        if constraint_type_id in (6, 7):
            # Must Finish On / Must Start On - not fully supported
            self.warnings.append(
                f"Task '{task_name}': 'Must Finish On' or 'Must Start On' "
                "constraint converted to SNET/FNLT"
            )
            if constraint_type_id == 6:  # Must Finish On
                constraint_type = ConstraintType.FNLT.value
            else:  # Must Start On
                constraint_type = ConstraintType.SNET.value
            constraint_date = self._parse_date(
                self._get_text(elem, "ConstraintDate", ns)
            )
            return constraint_type, constraint_date

        return None, None

    def _parse_predecessors(self, elem: ET.Element, ns: dict) -> list[dict]:
        """Parse predecessor links for a task."""
        predecessors = []

        pred_elements = (
            elem.findall("msp:PredecessorLink", ns)
            if ns
            else elem.findall("PredecessorLink")
        )

        for pred_elem in pred_elements:
            pred_uid = self._get_int(pred_elem, "PredecessorUID", ns)
            if pred_uid is None:
                continue

            link_type_raw = self._get_int(pred_elem, "Type", ns)
            link_type = link_type_raw if link_type_raw is not None else 1
            lag = self._get_int(pred_elem, "LinkLag", ns) or 0

            # Convert lag from tenths of minutes to working days
            # MS Project stores lag as tenths of minutes
            # 1 working day = 8 hours = 480 minutes = 4800 tenths
            lag_days = lag / 4800

            dep_type = self.DEPENDENCY_TYPE_MAP.get(link_type, DependencyType.FS)

            predecessors.append(
                {
                    "predecessor_uid": pred_uid,
                    "type": dep_type.value,
                    "lag": int(lag_days),
                }
            )

        return predecessors

    def _parse_duration(self, duration_str: str) -> float:
        """
        Parse ISO 8601 duration to hours.

        MS Project uses format: PT{hours}H{minutes}M{seconds}S
        Example: PT80H0M0S = 80 hours
        """
        if not duration_str or duration_str == "PT0H0M0S":
            return 0.0

        hours = 0.0

        # Remove PT prefix
        duration_str = duration_str.replace("PT", "")

        # Parse hours
        if "H" in duration_str:
            h_part = duration_str.split("H")[0]
            with contextlib.suppress(ValueError):
                hours = float(h_part)
            duration_str = duration_str.split("H")[1] if "H" in duration_str else ""

        # Parse minutes
        if "M" in duration_str:
            m_part = duration_str.split("M")[0]
            with contextlib.suppress(ValueError):
                hours += float(m_part) / 60

        return hours

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """
        Parse ISO date string.

        MS Project uses format: 2026-01-01T08:00:00
        """
        if not date_str:
            return None
        try:
            # Handle timezone suffix if present
            clean_str = date_str.replace("Z", "+00:00")
            # Try parsing with timezone first
            try:
                return datetime.fromisoformat(clean_str)
            except ValueError:
                # Fall back to parsing without timezone
                return datetime.fromisoformat(date_str.split("+")[0].split("Z")[0])
        except ValueError:
            return None

    def _get_text(self, elem: ET.Element, tag: str, ns: dict) -> str | None:
        """Get text content of child element."""
        child = elem.find(f"msp:{tag}", ns) if ns else elem.find(tag)
        return child.text if child is not None else None

    def _get_int(self, elem: ET.Element, tag: str, ns: dict) -> int | None:
        """Get integer content of child element."""
        text = self._get_text(elem, tag, ns)
        if text is None:
            return None
        try:
            return int(text)
        except ValueError:
            return None


async def import_msproject_to_program(
    importer: MSProjectImporter,
    program_id: UUID,
    session,
) -> dict:
    """
    Import parsed MS Project data into database.

    Args:
        importer: MSProjectImporter with parsed data
        program_id: Target program ID
        session: Database session

    Returns:
        Dict with import statistics
    """
    project = importer.parse()
    wbs_repo = WBSElementRepository(session)

    # Track UID to our ID mapping
    uid_to_id: dict[int, UUID] = {}

    # Track created WBS codes to avoid duplicates
    created_wbs_codes: dict[str, UUID] = {}

    # Statistics
    stats: dict = {
        "tasks_imported": 0,
        "dependencies_imported": 0,
        "wbs_elements_created": 0,
        "warnings": list(project.warnings),
        "errors": [],
    }

    # First pass: Create WBS elements and activities
    for task in project.tasks:
        await _import_task(
            task, program_id, session, wbs_repo,
            uid_to_id, created_wbs_codes, stats
        )

    # Flush to ensure activities exist before creating dependencies
    await session.flush()

    # Second pass: Create dependencies
    for task in project.tasks:
        _create_dependencies(task, uid_to_id, session, stats)

    await session.commit()

    return stats


async def _import_task(
    task: ImportedTask,
    program_id: UUID,
    session,
    wbs_repo: WBSElementRepository,
    uid_to_id: dict[int, UUID],
    created_wbs_codes: dict[str, UUID],
    stats: dict,
) -> None:
    """Import a single task as either WBS element or activity."""
    try:
        if task.is_summary:
            await _create_wbs_element(
                task, program_id, session, created_wbs_codes, stats
            )
        else:
            await _create_activity(
                task, program_id, session, wbs_repo,
                uid_to_id, created_wbs_codes, stats
            )
    except Exception as e:
        stats["errors"].append(f"Error importing task '{task.name}': {e!s}")


async def _create_wbs_element(
    task: ImportedTask,
    program_id: UUID,
    session,
    created_wbs_codes: dict[str, UUID],
    stats: dict,
) -> None:
    """Create WBS element for a summary task."""
    if task.wbs in created_wbs_codes:
        return

    # Determine parent WBS
    parent_wbs = ".".join(task.wbs.split(".")[:-1]) if "." in task.wbs else None
    parent_id = created_wbs_codes.get(parent_wbs) if parent_wbs else None

    wbs = WBSElement(
        id=uuid4(),
        program_id=program_id,
        parent_id=parent_id,
        wbs_code=task.wbs,
        name=task.name,
        description=task.notes,
        path=task.wbs.replace(".", "_"),
        level=task.outline_level,
        is_control_account=False,
    )
    session.add(wbs)
    created_wbs_codes[task.wbs] = wbs.id
    stats["wbs_elements_created"] += 1


async def _create_activity(
    task: ImportedTask,
    program_id: UUID,
    session,
    wbs_repo: WBSElementRepository,
    uid_to_id: dict[int, UUID],
    created_wbs_codes: dict[str, UUID],
    stats: dict,
) -> None:
    """Create activity for a non-summary task."""
    activity_id = uuid4()

    # Find or create parent WBS element
    parent_wbs = ".".join(task.wbs.split(".")[:-1]) if "." in task.wbs else task.wbs
    wbs_id = await _get_or_create_wbs(
        parent_wbs, program_id, session, wbs_repo, created_wbs_codes, stats
    )

    # Convert hours to working days (8 hours/day)
    duration_days = int(task.duration_hours / 8) if task.duration_hours else 0

    activity = Activity(
        id=activity_id,
        program_id=program_id,
        wbs_id=wbs_id,
        code=f"IMP-{task.uid:04d}",
        name=task.name,
        duration=max(duration_days, 0 if task.is_milestone else 1),
        is_milestone=task.is_milestone,
        planned_start=task.start.date() if task.start else None,
        planned_finish=task.finish.date() if task.finish else None,
        percent_complete=task.percent_complete,
        description=task.notes,
    )

    # Set constraint if present
    if task.constraint_type:
        try:
            activity.constraint_type = ConstraintType(task.constraint_type)
            if task.constraint_date:
                activity.constraint_date = task.constraint_date.date()
        except ValueError:
            stats["warnings"].append(
                f"Unknown constraint type for task '{task.name}'"
            )

    session.add(activity)
    uid_to_id[task.uid] = activity_id
    stats["tasks_imported"] += 1


async def _get_or_create_wbs(
    wbs_code: str,
    program_id: UUID,
    session,
    wbs_repo: WBSElementRepository,
    created_wbs_codes: dict[str, UUID],
    stats: dict,
) -> UUID:
    """Get existing WBS ID or create a new minimal WBS element."""
    wbs_id = created_wbs_codes.get(wbs_code)
    if wbs_id:
        return wbs_id

    # Check if WBS exists in database
    existing_wbs = await wbs_repo.get_by_code(program_id, wbs_code)
    if existing_wbs:
        created_wbs_codes[wbs_code] = existing_wbs.id
        return existing_wbs.id

    # Create minimal WBS element
    wbs = WBSElement(
        id=uuid4(),
        program_id=program_id,
        wbs_code=wbs_code,
        name=f"WBS {wbs_code}",
        path=wbs_code.replace(".", "_"),
        level=len(wbs_code.split(".")),
        is_control_account=False,
    )
    session.add(wbs)
    created_wbs_codes[wbs_code] = wbs.id
    stats["wbs_elements_created"] += 1
    return wbs.id


def _create_dependencies(
    task: ImportedTask,
    uid_to_id: dict[int, UUID],
    session,
    stats: dict,
) -> None:
    """Create dependencies for a task."""
    if task.is_summary:
        return

    successor_id = uid_to_id.get(task.uid)
    if not successor_id:
        return

    for pred in task.predecessors:
        predecessor_id = uid_to_id.get(pred["predecessor_uid"])
        if not predecessor_id:
            stats["warnings"].append(
                f"Predecessor UID {pred['predecessor_uid']} "
                f"not found for task '{task.name}'"
            )
            continue

        try:
            dep = Dependency(
                id=uuid4(),
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                dependency_type=DependencyType(pred["type"]),
                lag=pred["lag"],
            )
            session.add(dep)
            stats["dependencies_imported"] += 1
        except Exception as e:
            stats["errors"].append(
                f"Error creating dependency for task '{task.name}': {e!s}"
            )
