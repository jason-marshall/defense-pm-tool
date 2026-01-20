"""Unit tests for MS Project XML importer."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.core.exceptions import ValidationError
from src.services.msproject_import import (
    ImportedProject,
    ImportedTask,
    MSProjectImporter,
)


class TestMSProjectImporter:
    """Tests for MS Project XML parsing."""

    @pytest.fixture
    def sample_xml_path(self, tmp_path: Path) -> Path:
        """Create sample MS Project XML file."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Name>Test Project</Name>
  <StartDate>2026-01-01T08:00:00</StartDate>
  <FinishDate>2026-06-30T17:00:00</FinishDate>
  <Tasks>
    <Task>
      <UID>0</UID>
      <ID>0</ID>
      <Name>Project Summary</Name>
      <IsNull>1</IsNull>
    </Task>
    <Task>
      <UID>1</UID>
      <ID>1</ID>
      <Name>Project Start</Name>
      <WBS>1</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT0H0M0S</Duration>
      <Start>2026-01-01T08:00:00</Start>
      <Finish>2026-01-01T08:00:00</Finish>
      <Milestone>1</Milestone>
      <PercentComplete>0</PercentComplete>
    </Task>
    <Task>
      <UID>2</UID>
      <ID>2</ID>
      <Name>Design Phase</Name>
      <WBS>1.1</WBS>
      <OutlineLevel>2</OutlineLevel>
      <Duration>PT80H0M0S</Duration>
      <Start>2026-01-02T08:00:00</Start>
      <Finish>2026-01-13T17:00:00</Finish>
      <PercentComplete>50</PercentComplete>
      <Notes>Design documentation</Notes>
      <PredecessorLink>
        <PredecessorUID>1</PredecessorUID>
        <Type>1</Type>
        <LinkLag>0</LinkLag>
      </PredecessorLink>
    </Task>
    <Task>
      <UID>3</UID>
      <ID>3</ID>
      <Name>Development</Name>
      <WBS>1.2</WBS>
      <OutlineLevel>2</OutlineLevel>
      <Duration>PT40H0M0S</Duration>
      <Start>2026-01-14T08:00:00</Start>
      <Finish>2026-01-17T17:00:00</Finish>
      <ConstraintType>2</ConstraintType>
      <ConstraintDate>2026-01-14T08:00:00</ConstraintDate>
      <PredecessorLink>
        <PredecessorUID>2</PredecessorUID>
        <Type>1</Type>
        <LinkLag>4800</LinkLag>
      </PredecessorLink>
    </Task>
  </Tasks>
</Project>"""

        xml_file = tmp_path / "test_project.xml"
        xml_file.write_text(xml_content)
        return xml_file

    @pytest.fixture
    def sample_xml_no_namespace(self, tmp_path: Path) -> Path:
        """Create sample MS Project XML without namespace."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>No Namespace Project</Name>
  <StartDate>2026-02-01T08:00:00</StartDate>
  <FinishDate>2026-07-01T17:00:00</FinishDate>
  <Tasks>
    <Task>
      <UID>1</UID>
      <ID>1</ID>
      <Name>Task One</Name>
      <WBS>1</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT16H0M0S</Duration>
      <Start>2026-02-01T08:00:00</Start>
      <Finish>2026-02-03T17:00:00</Finish>
    </Task>
  </Tasks>
</Project>"""

        xml_file = tmp_path / "no_namespace.xml"
        xml_file.write_text(xml_content)
        return xml_file

    def test_parse_project_metadata(self, sample_xml_path: Path) -> None:
        """Should parse project name and dates."""
        importer = MSProjectImporter(sample_xml_path)
        project = importer.parse()

        assert project.name == "Test Project"
        assert project.start_date.year == 2026
        assert project.start_date.month == 1
        assert project.start_date.day == 1
        assert project.finish_date.month == 6
        assert project.finish_date.day == 30

    def test_parse_tasks(self, sample_xml_path: Path) -> None:
        """Should parse all tasks, excluding null tasks."""
        importer = MSProjectImporter(sample_xml_path)
        project = importer.parse()

        # Should have 3 tasks (null task excluded)
        assert len(project.tasks) == 3

        # First task is milestone
        assert project.tasks[0].name == "Project Start"
        assert project.tasks[0].is_milestone is True
        assert project.tasks[0].duration_hours == 0

        # Second task has duration
        assert project.tasks[1].name == "Design Phase"
        assert project.tasks[1].duration_hours == 80

    def test_parse_milestones(self, sample_xml_path: Path) -> None:
        """Should correctly identify milestones."""
        importer = MSProjectImporter(sample_xml_path)
        project = importer.parse()

        milestone = project.tasks[0]
        assert milestone.is_milestone is True
        assert milestone.duration_hours == 0

        regular_task = project.tasks[1]
        assert regular_task.is_milestone is False
        assert regular_task.duration_hours > 0

    def test_parse_predecessors(self, sample_xml_path: Path) -> None:
        """Should parse predecessor links."""
        importer = MSProjectImporter(sample_xml_path)
        project = importer.parse()

        # Second task has predecessor (first task)
        task2 = project.tasks[1]
        assert len(task2.predecessors) == 1
        assert task2.predecessors[0]["predecessor_uid"] == 1
        assert task2.predecessors[0]["type"] == "FS"
        assert task2.predecessors[0]["lag"] == 0

    def test_parse_predecessor_with_lag(self, sample_xml_path: Path) -> None:
        """Should parse predecessor lag."""
        importer = MSProjectImporter(sample_xml_path)
        project = importer.parse()

        # Third task has predecessor with lag
        task3 = project.tasks[2]
        assert len(task3.predecessors) == 1
        assert task3.predecessors[0]["predecessor_uid"] == 2
        # 4800 tenths of minutes = 1 working day
        assert task3.predecessors[0]["lag"] == 1

    def test_parse_wbs_codes(self, sample_xml_path: Path) -> None:
        """Should parse WBS codes."""
        importer = MSProjectImporter(sample_xml_path)
        project = importer.parse()

        assert project.tasks[0].wbs == "1"
        assert project.tasks[1].wbs == "1.1"
        assert project.tasks[2].wbs == "1.2"

    def test_parse_outline_levels(self, sample_xml_path: Path) -> None:
        """Should parse outline levels."""
        importer = MSProjectImporter(sample_xml_path)
        project = importer.parse()

        assert project.tasks[0].outline_level == 1
        assert project.tasks[1].outline_level == 2
        assert project.tasks[2].outline_level == 2

    def test_parse_percent_complete(self, sample_xml_path: Path) -> None:
        """Should parse percent complete."""
        importer = MSProjectImporter(sample_xml_path)
        project = importer.parse()

        assert project.tasks[0].percent_complete == Decimal("0")
        assert project.tasks[1].percent_complete == Decimal("50")

    def test_parse_constraint(self, sample_xml_path: Path) -> None:
        """Should parse constraint type and date."""
        importer = MSProjectImporter(sample_xml_path)
        project = importer.parse()

        # Third task has SNET constraint (type 2)
        task3 = project.tasks[2]
        assert task3.constraint_type == "snet"
        assert task3.constraint_date is not None
        assert task3.constraint_date.year == 2026
        assert task3.constraint_date.month == 1
        assert task3.constraint_date.day == 14

    def test_parse_notes(self, sample_xml_path: Path) -> None:
        """Should parse task notes."""
        importer = MSProjectImporter(sample_xml_path)
        project = importer.parse()

        # Second task has notes
        assert project.tasks[1].notes == "Design documentation"
        # Third task has no notes
        assert project.tasks[2].notes is None

    def test_parse_dates(self, sample_xml_path: Path) -> None:
        """Should parse start and finish dates."""
        importer = MSProjectImporter(sample_xml_path)
        project = importer.parse()

        task = project.tasks[1]
        assert task.start is not None
        assert task.start.year == 2026
        assert task.start.month == 1
        assert task.start.day == 2

        assert task.finish is not None
        assert task.finish.month == 1
        assert task.finish.day == 13

    def test_parse_without_namespace(self, sample_xml_no_namespace: Path) -> None:
        """Should parse XML without namespace."""
        importer = MSProjectImporter(sample_xml_no_namespace)
        project = importer.parse()

        assert project.name == "No Namespace Project"
        assert len(project.tasks) == 1
        assert project.tasks[0].name == "Task One"
        assert project.tasks[0].duration_hours == 16

    def test_file_not_found_raises_error(self, tmp_path: Path) -> None:
        """Should raise error for missing file."""
        importer = MSProjectImporter(tmp_path / "nonexistent.xml")

        with pytest.raises(ValidationError, match="File not found"):
            importer.parse()

    def test_invalid_xml_raises_error(self, tmp_path: Path) -> None:
        """Should raise error for invalid XML."""
        bad_file = tmp_path / "bad.xml"
        bad_file.write_text("not valid xml <><>")

        importer = MSProjectImporter(bad_file)

        with pytest.raises(ValidationError, match="Invalid XML"):
            importer.parse()

    def test_missing_project_dates_adds_warnings(self, tmp_path: Path) -> None:
        """Should add warnings for missing project dates."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>No Dates Project</Name>
  <Tasks>
    <Task>
      <UID>1</UID>
      <ID>1</ID>
      <Name>Task</Name>
      <WBS>1</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
    </Task>
  </Tasks>
</Project>"""

        xml_file = tmp_path / "no_dates.xml"
        xml_file.write_text(xml_content)

        importer = MSProjectImporter(xml_file)
        project = importer.parse()

        assert len(project.warnings) >= 1
        assert any("start date" in w.lower() for w in project.warnings)

    def test_empty_tasks_adds_warning(self, tmp_path: Path) -> None:
        """Should add warning when no tasks element found."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>Empty Project</Name>
  <StartDate>2026-01-01T08:00:00</StartDate>
  <FinishDate>2026-12-31T17:00:00</FinishDate>
</Project>"""

        xml_file = tmp_path / "empty.xml"
        xml_file.write_text(xml_content)

        importer = MSProjectImporter(xml_file)
        project = importer.parse()

        assert len(project.tasks) == 0
        assert len(project.warnings) >= 1
        assert any("Tasks" in w for w in project.warnings)


class TestDurationParsing:
    """Tests for ISO 8601 duration parsing."""

    def test_parse_hours_only(self, tmp_path: Path) -> None:
        """Should parse duration with hours only."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>Test</Name>
  <StartDate>2026-01-01T08:00:00</StartDate>
  <FinishDate>2026-12-31T17:00:00</FinishDate>
  <Tasks>
    <Task>
      <UID>1</UID>
      <Name>Task</Name>
      <WBS>1</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT80H0M0S</Duration>
    </Task>
  </Tasks>
</Project>"""

        xml_file = tmp_path / "test.xml"
        xml_file.write_text(xml_content)

        importer = MSProjectImporter(xml_file)
        project = importer.parse()

        assert project.tasks[0].duration_hours == 80.0

    def test_parse_hours_and_minutes(self, tmp_path: Path) -> None:
        """Should parse duration with hours and minutes."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>Test</Name>
  <StartDate>2026-01-01T08:00:00</StartDate>
  <FinishDate>2026-12-31T17:00:00</FinishDate>
  <Tasks>
    <Task>
      <UID>1</UID>
      <Name>Task</Name>
      <WBS>1</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT8H30M0S</Duration>
    </Task>
  </Tasks>
</Project>"""

        xml_file = tmp_path / "test.xml"
        xml_file.write_text(xml_content)

        importer = MSProjectImporter(xml_file)
        project = importer.parse()

        assert project.tasks[0].duration_hours == 8.5

    def test_parse_zero_duration(self, tmp_path: Path) -> None:
        """Should parse zero duration (milestone)."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>Test</Name>
  <StartDate>2026-01-01T08:00:00</StartDate>
  <FinishDate>2026-12-31T17:00:00</FinishDate>
  <Tasks>
    <Task>
      <UID>1</UID>
      <Name>Milestone</Name>
      <WBS>1</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT0H0M0S</Duration>
      <Milestone>1</Milestone>
    </Task>
  </Tasks>
</Project>"""

        xml_file = tmp_path / "test.xml"
        xml_file.write_text(xml_content)

        importer = MSProjectImporter(xml_file)
        project = importer.parse()

        assert project.tasks[0].duration_hours == 0.0
        assert project.tasks[0].is_milestone is True


class TestDependencyTypeParsing:
    """Tests for dependency type parsing."""

    @pytest.fixture
    def xml_with_deps(self, tmp_path: Path) -> Path:
        """Create XML with various dependency types."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>Deps Test</Name>
  <StartDate>2026-01-01T08:00:00</StartDate>
  <FinishDate>2026-12-31T17:00:00</FinishDate>
  <Tasks>
    <Task>
      <UID>1</UID>
      <Name>First</Name>
      <WBS>1</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
    </Task>
    <Task>
      <UID>2</UID>
      <Name>FS Link</Name>
      <WBS>2</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
      <PredecessorLink>
        <PredecessorUID>1</PredecessorUID>
        <Type>1</Type>
        <LinkLag>0</LinkLag>
      </PredecessorLink>
    </Task>
    <Task>
      <UID>3</UID>
      <Name>FF Link</Name>
      <WBS>3</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
      <PredecessorLink>
        <PredecessorUID>1</PredecessorUID>
        <Type>0</Type>
        <LinkLag>0</LinkLag>
      </PredecessorLink>
    </Task>
    <Task>
      <UID>4</UID>
      <Name>SS Link</Name>
      <WBS>4</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
      <PredecessorLink>
        <PredecessorUID>1</PredecessorUID>
        <Type>3</Type>
        <LinkLag>0</LinkLag>
      </PredecessorLink>
    </Task>
    <Task>
      <UID>5</UID>
      <Name>SF Link</Name>
      <WBS>5</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
      <PredecessorLink>
        <PredecessorUID>1</PredecessorUID>
        <Type>2</Type>
        <LinkLag>0</LinkLag>
      </PredecessorLink>
    </Task>
  </Tasks>
</Project>"""

        xml_file = tmp_path / "deps.xml"
        xml_file.write_text(xml_content)
        return xml_file

    def test_parse_fs_dependency(self, xml_with_deps: Path) -> None:
        """Should parse Finish-to-Start dependency (Type 1)."""
        importer = MSProjectImporter(xml_with_deps)
        project = importer.parse()

        task = next(t for t in project.tasks if t.name == "FS Link")
        assert task.predecessors[0]["type"] == "FS"

    def test_parse_ff_dependency(self, xml_with_deps: Path) -> None:
        """Should parse Finish-to-Finish dependency (Type 0)."""
        importer = MSProjectImporter(xml_with_deps)
        project = importer.parse()

        task = next(t for t in project.tasks if t.name == "FF Link")
        assert task.predecessors[0]["type"] == "FF"

    def test_parse_ss_dependency(self, xml_with_deps: Path) -> None:
        """Should parse Start-to-Start dependency (Type 3)."""
        importer = MSProjectImporter(xml_with_deps)
        project = importer.parse()

        task = next(t for t in project.tasks if t.name == "SS Link")
        assert task.predecessors[0]["type"] == "SS"

    def test_parse_sf_dependency(self, xml_with_deps: Path) -> None:
        """Should parse Start-to-Finish dependency (Type 2)."""
        importer = MSProjectImporter(xml_with_deps)
        project = importer.parse()

        task = next(t for t in project.tasks if t.name == "SF Link")
        assert task.predecessors[0]["type"] == "SF"


class TestImportedDataclasses:
    """Tests for imported data structures."""

    def test_imported_task_defaults(self) -> None:
        """ImportedTask should have correct defaults."""
        task = ImportedTask(
            uid=1,
            id=1,
            name="Test",
            wbs="1",
            outline_level=1,
            duration_hours=8.0,
            start=None,
            finish=None,
            is_milestone=False,
            is_summary=False,
        )

        assert task.predecessors == []
        assert task.constraint_type is None
        assert task.constraint_date is None
        assert task.percent_complete == Decimal("0")
        assert task.notes is None

    def test_imported_project_defaults(self) -> None:
        """ImportedProject should have correct defaults."""
        project = ImportedProject(
            name="Test",
            start_date=datetime(2026, 1, 1),
            finish_date=datetime(2026, 12, 31),
            tasks=[],
        )

        assert project.warnings == []


class TestConstraintParsing:
    """Tests for constraint type parsing."""

    @pytest.fixture
    def xml_with_must_finish_on(self, tmp_path: Path) -> Path:
        """Create XML with Must Finish On constraint (type 6)."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>Constraint Test</Name>
  <StartDate>2026-01-01T08:00:00</StartDate>
  <FinishDate>2026-12-31T17:00:00</FinishDate>
  <Tasks>
    <Task>
      <UID>1</UID>
      <Name>Must Finish On Task</Name>
      <WBS>1</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
      <ConstraintType>6</ConstraintType>
      <ConstraintDate>2026-03-15T17:00:00</ConstraintDate>
    </Task>
  </Tasks>
</Project>"""
        xml_file = tmp_path / "must_finish.xml"
        xml_file.write_text(xml_content)
        return xml_file

    @pytest.fixture
    def xml_with_must_start_on(self, tmp_path: Path) -> Path:
        """Create XML with Must Start On constraint (type 7)."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>Constraint Test</Name>
  <StartDate>2026-01-01T08:00:00</StartDate>
  <FinishDate>2026-12-31T17:00:00</FinishDate>
  <Tasks>
    <Task>
      <UID>1</UID>
      <Name>Must Start On Task</Name>
      <WBS>1</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
      <ConstraintType>7</ConstraintType>
      <ConstraintDate>2026-03-15T08:00:00</ConstraintDate>
    </Task>
  </Tasks>
</Project>"""
        xml_file = tmp_path / "must_start.xml"
        xml_file.write_text(xml_content)
        return xml_file

    def test_must_finish_on_converted_to_fnlt(self, xml_with_must_finish_on: Path) -> None:
        """Should convert Must Finish On (type 6) to FNLT with warning."""
        importer = MSProjectImporter(xml_with_must_finish_on)
        project = importer.parse()

        task = project.tasks[0]
        assert task.constraint_type == "fnlt"
        assert task.constraint_date is not None
        # Should have warning about conversion
        assert any("Must Finish On" in w or "Must Start On" in w for w in project.warnings)

    def test_must_start_on_converted_to_snet(self, xml_with_must_start_on: Path) -> None:
        """Should convert Must Start On (type 7) to SNET with warning."""
        importer = MSProjectImporter(xml_with_must_start_on)
        project = importer.parse()

        task = project.tasks[0]
        assert task.constraint_type == "snet"
        assert task.constraint_date is not None
        # Should have warning about conversion
        assert any("Must Finish On" in w or "Must Start On" in w for w in project.warnings)

    @pytest.fixture
    def xml_with_all_constraints(self, tmp_path: Path) -> Path:
        """Create XML with all constraint types."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>All Constraints</Name>
  <StartDate>2026-01-01T08:00:00</StartDate>
  <FinishDate>2026-12-31T17:00:00</FinishDate>
  <Tasks>
    <Task>
      <UID>1</UID><Name>ASAP</Name><WBS>1</WBS><OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
      <ConstraintType>0</ConstraintType>
    </Task>
    <Task>
      <UID>2</UID><Name>ALAP</Name><WBS>2</WBS><OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
      <ConstraintType>1</ConstraintType>
    </Task>
    <Task>
      <UID>3</UID><Name>SNLT</Name><WBS>3</WBS><OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
      <ConstraintType>3</ConstraintType>
      <ConstraintDate>2026-02-01T08:00:00</ConstraintDate>
    </Task>
    <Task>
      <UID>4</UID><Name>FNET</Name><WBS>4</WBS><OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
      <ConstraintType>4</ConstraintType>
      <ConstraintDate>2026-02-15T17:00:00</ConstraintDate>
    </Task>
    <Task>
      <UID>5</UID><Name>FNLT</Name><WBS>5</WBS><OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
      <ConstraintType>5</ConstraintType>
      <ConstraintDate>2026-02-28T17:00:00</ConstraintDate>
    </Task>
  </Tasks>
</Project>"""
        xml_file = tmp_path / "all_constraints.xml"
        xml_file.write_text(xml_content)
        return xml_file

    def test_asap_alap_constraints_ignored(self, xml_with_all_constraints: Path) -> None:
        """Should return None for ASAP (0) and ALAP (1) constraints."""
        importer = MSProjectImporter(xml_with_all_constraints)
        project = importer.parse()

        asap_task = next(t for t in project.tasks if t.name == "ASAP")
        alap_task = next(t for t in project.tasks if t.name == "ALAP")

        assert asap_task.constraint_type is None
        assert alap_task.constraint_type is None

    def test_snlt_constraint(self, xml_with_all_constraints: Path) -> None:
        """Should parse SNLT constraint (type 3)."""
        importer = MSProjectImporter(xml_with_all_constraints)
        project = importer.parse()

        task = next(t for t in project.tasks if t.name == "SNLT")
        assert task.constraint_type == "snlt"
        assert task.constraint_date is not None

    def test_fnet_constraint(self, xml_with_all_constraints: Path) -> None:
        """Should parse FNET constraint (type 4)."""
        importer = MSProjectImporter(xml_with_all_constraints)
        project = importer.parse()

        task = next(t for t in project.tasks if t.name == "FNET")
        assert task.constraint_type == "fnet"
        assert task.constraint_date is not None

    def test_fnlt_constraint(self, xml_with_all_constraints: Path) -> None:
        """Should parse FNLT constraint (type 5)."""
        importer = MSProjectImporter(xml_with_all_constraints)
        project = importer.parse()

        task = next(t for t in project.tasks if t.name == "FNLT")
        assert task.constraint_type == "fnlt"
        assert task.constraint_date is not None


class TestSummaryTasks:
    """Tests for summary task parsing."""

    @pytest.fixture
    def xml_with_summary_tasks(self, tmp_path: Path) -> Path:
        """Create XML with summary and non-summary tasks."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>Summary Tasks</Name>
  <StartDate>2026-01-01T08:00:00</StartDate>
  <FinishDate>2026-12-31T17:00:00</FinishDate>
  <Tasks>
    <Task>
      <UID>1</UID>
      <Name>Phase 1</Name>
      <WBS>1</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT80H0M0S</Duration>
      <Summary>1</Summary>
    </Task>
    <Task>
      <UID>2</UID>
      <Name>Task 1.1</Name>
      <WBS>1.1</WBS>
      <OutlineLevel>2</OutlineLevel>
      <Duration>PT40H0M0S</Duration>
      <Summary>0</Summary>
    </Task>
  </Tasks>
</Project>"""
        xml_file = tmp_path / "summary.xml"
        xml_file.write_text(xml_content)
        return xml_file

    def test_summary_task_flag(self, xml_with_summary_tasks: Path) -> None:
        """Should correctly identify summary tasks."""
        importer = MSProjectImporter(xml_with_summary_tasks)
        project = importer.parse()

        summary = next(t for t in project.tasks if t.name == "Phase 1")
        regular = next(t for t in project.tasks if t.name == "Task 1.1")

        assert summary.is_summary is True
        assert regular.is_summary is False


class TestDateTimeParsing:
    """Tests for datetime parsing edge cases."""

    @pytest.fixture
    def xml_with_timezone(self, tmp_path: Path) -> Path:
        """Create XML with timezone in dates."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>Timezone Test</Name>
  <StartDate>2026-01-01T08:00:00Z</StartDate>
  <FinishDate>2026-12-31T17:00:00+00:00</FinishDate>
  <Tasks>
    <Task>
      <UID>1</UID>
      <Name>Task</Name>
      <WBS>1</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT8H0M0S</Duration>
      <Start>2026-01-15T08:00:00Z</Start>
      <Finish>2026-01-15T17:00:00+05:30</Finish>
    </Task>
  </Tasks>
</Project>"""
        xml_file = tmp_path / "timezone.xml"
        xml_file.write_text(xml_content)
        return xml_file

    def test_parse_dates_with_timezone(self, xml_with_timezone: Path) -> None:
        """Should parse dates with timezone suffixes."""
        importer = MSProjectImporter(xml_with_timezone)
        project = importer.parse()

        assert project.start_date is not None
        assert project.finish_date is not None
        assert project.tasks[0].start is not None
        assert project.tasks[0].finish is not None


class TestMissingTaskData:
    """Tests for tasks with missing optional data."""

    @pytest.fixture
    def xml_minimal_task(self, tmp_path: Path) -> Path:
        """Create XML with minimal task data."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>Minimal</Name>
  <StartDate>2026-01-01T08:00:00</StartDate>
  <FinishDate>2026-12-31T17:00:00</FinishDate>
  <Tasks>
    <Task>
      <UID>1</UID>
    </Task>
  </Tasks>
</Project>"""
        xml_file = tmp_path / "minimal.xml"
        xml_file.write_text(xml_content)
        return xml_file

    def test_minimal_task_has_defaults(self, xml_minimal_task: Path) -> None:
        """Should use defaults for missing task fields."""
        importer = MSProjectImporter(xml_minimal_task)
        project = importer.parse()

        task = project.tasks[0]
        assert task.name == "Task 1"  # Default name
        assert task.wbs == "1"  # Default WBS
        assert task.outline_level == 1
        assert task.duration_hours == 0
        assert task.is_milestone is False
        assert task.is_summary is False


class TestImportFunctions:
    """Tests for import helper functions (import_msproject_to_program and helpers)."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        from unittest.mock import AsyncMock, MagicMock

        session = MagicMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def sample_import_xml(self, tmp_path: Path) -> Path:
        """Create sample MS Project XML for import testing."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>Import Test Project</Name>
  <StartDate>2026-01-01T08:00:00</StartDate>
  <FinishDate>2026-06-30T17:00:00</FinishDate>
  <Tasks>
    <Task>
      <UID>1</UID>
      <ID>1</ID>
      <Name>Phase 1</Name>
      <WBS>1</WBS>
      <OutlineLevel>1</OutlineLevel>
      <Duration>PT0H0M0S</Duration>
      <Summary>1</Summary>
    </Task>
    <Task>
      <UID>2</UID>
      <ID>2</ID>
      <Name>Task A</Name>
      <WBS>1.1</WBS>
      <OutlineLevel>2</OutlineLevel>
      <Duration>PT40H0M0S</Duration>
      <Start>2026-01-02T08:00:00</Start>
      <Finish>2026-01-06T17:00:00</Finish>
      <Summary>0</Summary>
      <PercentComplete>25</PercentComplete>
    </Task>
    <Task>
      <UID>3</UID>
      <ID>3</ID>
      <Name>Task B</Name>
      <WBS>1.2</WBS>
      <OutlineLevel>2</OutlineLevel>
      <Duration>PT80H0M0S</Duration>
      <Summary>0</Summary>
      <ConstraintType>2</ConstraintType>
      <ConstraintDate>2026-01-07T08:00:00</ConstraintDate>
      <PredecessorLink>
        <PredecessorUID>2</PredecessorUID>
        <Type>1</Type>
        <LinkLag>0</LinkLag>
      </PredecessorLink>
    </Task>
    <Task>
      <UID>4</UID>
      <ID>4</ID>
      <Name>Milestone</Name>
      <WBS>1.3</WBS>
      <OutlineLevel>2</OutlineLevel>
      <Duration>PT0H0M0S</Duration>
      <Summary>0</Summary>
      <Milestone>1</Milestone>
      <PredecessorLink>
        <PredecessorUID>3</PredecessorUID>
        <Type>1</Type>
        <LinkLag>0</LinkLag>
      </PredecessorLink>
    </Task>
  </Tasks>
</Project>"""
        xml_file = tmp_path / "import_test.xml"
        xml_file.write_text(xml_content)
        return xml_file

    @pytest.mark.asyncio
    async def test_import_msproject_to_program(self, sample_import_xml: Path, mock_session) -> None:
        """Should import MS Project file to program."""
        from unittest.mock import AsyncMock, patch
        from uuid import uuid4

        from src.services.msproject_import import import_msproject_to_program

        importer = MSProjectImporter(sample_import_xml)
        program_id = uuid4()

        with patch("src.services.msproject_import.WBSElementRepository") as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_by_code = AsyncMock(return_value=None)

            stats = await import_msproject_to_program(importer, program_id, mock_session)

        assert stats["wbs_elements_created"] >= 1
        assert stats["tasks_imported"] >= 1
        assert stats["dependencies_imported"] >= 1
        assert mock_session.commit.called
        assert mock_session.flush.called

    @pytest.mark.asyncio
    async def test_import_task_summary(self, mock_session) -> None:
        """Should create WBS element for summary task."""
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _import_task

        task = ImportedTask(
            uid=1,
            id=1,
            name="Phase 1",
            wbs="1",
            outline_level=1,
            duration_hours=0,
            start=None,
            finish=None,
            is_milestone=False,
            is_summary=True,
        )

        program_id = uuid4()
        uid_to_id = {}
        created_wbs_codes = {}
        stats = {
            "tasks_imported": 0,
            "dependencies_imported": 0,
            "wbs_elements_created": 0,
            "warnings": [],
            "errors": [],
        }

        await _import_task(
            task, program_id, mock_session, None, uid_to_id, created_wbs_codes, stats
        )

        assert stats["wbs_elements_created"] == 1
        assert "1" in created_wbs_codes

    @pytest.mark.asyncio
    async def test_import_task_activity(self, mock_session) -> None:
        """Should create activity for non-summary task."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _import_task

        task = ImportedTask(
            uid=2,
            id=2,
            name="Task A",
            wbs="1.1",
            outline_level=2,
            duration_hours=40,
            start=datetime(2026, 1, 2, 8, 0),
            finish=datetime(2026, 1, 6, 17, 0),
            is_milestone=False,
            is_summary=False,
            percent_complete=Decimal("25"),
        )

        program_id = uuid4()
        wbs_id = uuid4()
        uid_to_id = {}
        created_wbs_codes = {"1": wbs_id}
        stats = {
            "tasks_imported": 0,
            "dependencies_imported": 0,
            "wbs_elements_created": 0,
            "warnings": [],
            "errors": [],
        }

        mock_wbs_repo = MagicMock()
        mock_wbs_repo.get_by_code = AsyncMock(return_value=None)

        await _import_task(
            task, program_id, mock_session, mock_wbs_repo, uid_to_id, created_wbs_codes, stats
        )

        assert stats["tasks_imported"] == 1
        assert 2 in uid_to_id

    @pytest.mark.asyncio
    async def test_import_task_error_handling(self, mock_session) -> None:
        """Should catch and log errors during task import."""
        from unittest.mock import MagicMock
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _import_task

        task = ImportedTask(
            uid=1,
            id=1,
            name="Error Task",
            wbs="1",
            outline_level=1,
            duration_hours=8,
            start=None,
            finish=None,
            is_milestone=False,
            is_summary=False,
        )

        program_id = uuid4()
        uid_to_id = {}
        created_wbs_codes = {}
        stats = {
            "tasks_imported": 0,
            "dependencies_imported": 0,
            "wbs_elements_created": 0,
            "warnings": [],
            "errors": [],
        }

        # Make session.add raise an exception
        mock_session.add.side_effect = Exception("Database error")

        mock_wbs_repo = MagicMock()

        await _import_task(
            task, program_id, mock_session, mock_wbs_repo, uid_to_id, created_wbs_codes, stats
        )

        assert len(stats["errors"]) == 1
        assert "Error importing task" in stats["errors"][0]

    @pytest.mark.asyncio
    async def test_create_wbs_element(self, mock_session) -> None:
        """Should create WBS element for summary task."""
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _create_wbs_element

        task = ImportedTask(
            uid=1,
            id=1,
            name="Phase 1",
            wbs="1",
            outline_level=1,
            duration_hours=0,
            start=None,
            finish=None,
            is_milestone=False,
            is_summary=True,
            notes="Phase description",
        )

        program_id = uuid4()
        created_wbs_codes = {}
        stats = {"wbs_elements_created": 0}

        await _create_wbs_element(task, program_id, mock_session, created_wbs_codes, stats)

        assert mock_session.add.called
        assert "1" in created_wbs_codes
        assert stats["wbs_elements_created"] == 1

    @pytest.mark.asyncio
    async def test_create_wbs_element_with_parent(self, mock_session) -> None:
        """Should create WBS element with parent reference."""
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _create_wbs_element

        parent_id = uuid4()
        created_wbs_codes = {"1": parent_id}

        task = ImportedTask(
            uid=2,
            id=2,
            name="Sub Phase",
            wbs="1.1",
            outline_level=2,
            duration_hours=0,
            start=None,
            finish=None,
            is_milestone=False,
            is_summary=True,
        )

        program_id = uuid4()
        stats = {"wbs_elements_created": 0}

        await _create_wbs_element(task, program_id, mock_session, created_wbs_codes, stats)

        # Verify parent_id was set
        call_args = mock_session.add.call_args
        wbs_element = call_args[0][0]
        assert wbs_element.parent_id == parent_id

    @pytest.mark.asyncio
    async def test_create_wbs_element_already_exists(self, mock_session) -> None:
        """Should skip creating WBS element if code already exists."""
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _create_wbs_element

        existing_id = uuid4()
        created_wbs_codes = {"1": existing_id}

        task = ImportedTask(
            uid=1,
            id=1,
            name="Duplicate",
            wbs="1",
            outline_level=1,
            duration_hours=0,
            start=None,
            finish=None,
            is_milestone=False,
            is_summary=True,
        )

        stats = {"wbs_elements_created": 0}

        await _create_wbs_element(task, uuid4(), mock_session, created_wbs_codes, stats)

        assert not mock_session.add.called
        assert stats["wbs_elements_created"] == 0

    @pytest.mark.asyncio
    async def test_create_activity(self, mock_session) -> None:
        """Should create activity for non-summary task."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _create_activity

        task = ImportedTask(
            uid=10,
            id=10,
            name="Design Review",
            wbs="1.1.1",
            outline_level=3,
            duration_hours=40,
            start=datetime(2026, 1, 15, 8, 0),
            finish=datetime(2026, 1, 19, 17, 0),
            is_milestone=False,
            is_summary=False,
            percent_complete=Decimal("50"),
            notes="Review design",
        )

        program_id = uuid4()
        wbs_id = uuid4()
        uid_to_id = {}
        created_wbs_codes = {"1.1": wbs_id}
        stats = {"tasks_imported": 0, "wbs_elements_created": 0, "warnings": []}

        mock_wbs_repo = MagicMock()
        mock_wbs_repo.get_by_code = AsyncMock(return_value=None)

        await _create_activity(
            task, program_id, mock_session, mock_wbs_repo, uid_to_id, created_wbs_codes, stats
        )

        assert mock_session.add.called
        assert 10 in uid_to_id
        assert stats["tasks_imported"] == 1

    @pytest.mark.asyncio
    async def test_create_activity_milestone(self, mock_session) -> None:
        """Should create milestone activity with zero duration."""
        from unittest.mock import MagicMock
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _create_activity

        task = ImportedTask(
            uid=20,
            id=20,
            name="Project Kickoff",
            wbs="1",
            outline_level=1,
            duration_hours=0,
            start=datetime(2026, 1, 1, 8, 0),
            finish=datetime(2026, 1, 1, 8, 0),
            is_milestone=True,
            is_summary=False,
        )

        program_id = uuid4()
        wbs_id = uuid4()
        uid_to_id = {}
        created_wbs_codes = {"1": wbs_id}
        stats = {"tasks_imported": 0, "wbs_elements_created": 0, "warnings": []}

        mock_wbs_repo = MagicMock()

        await _create_activity(
            task, program_id, mock_session, mock_wbs_repo, uid_to_id, created_wbs_codes, stats
        )

        call_args = mock_session.add.call_args
        activity = call_args[0][0]
        assert activity.is_milestone is True
        assert activity.duration == 0

    @pytest.mark.asyncio
    async def test_create_activity_with_constraint(self, mock_session) -> None:
        """Should set constraint on activity."""
        from unittest.mock import MagicMock
        from uuid import uuid4

        from src.models.enums import ConstraintType
        from src.services.msproject_import import ImportedTask, _create_activity

        task = ImportedTask(
            uid=30,
            id=30,
            name="Constrained Task",
            wbs="1",
            outline_level=1,
            duration_hours=8,
            start=datetime(2026, 2, 1, 8, 0),
            finish=datetime(2026, 2, 1, 17, 0),
            is_milestone=False,
            is_summary=False,
            constraint_type="snet",
            constraint_date=datetime(2026, 2, 1, 8, 0),
        )

        program_id = uuid4()
        wbs_id = uuid4()
        uid_to_id = {}
        created_wbs_codes = {"1": wbs_id}
        stats = {"tasks_imported": 0, "wbs_elements_created": 0, "warnings": []}

        mock_wbs_repo = MagicMock()

        await _create_activity(
            task, program_id, mock_session, mock_wbs_repo, uid_to_id, created_wbs_codes, stats
        )

        call_args = mock_session.add.call_args
        activity = call_args[0][0]
        assert activity.constraint_type == ConstraintType.SNET

    @pytest.mark.asyncio
    async def test_create_activity_invalid_constraint(self, mock_session) -> None:
        """Should add warning for invalid constraint type."""
        from unittest.mock import MagicMock
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _create_activity

        task = ImportedTask(
            uid=31,
            id=31,
            name="Invalid Constraint Task",
            wbs="1",
            outline_level=1,
            duration_hours=8,
            start=None,
            finish=None,
            is_milestone=False,
            is_summary=False,
            constraint_type="invalid_type",
            constraint_date=datetime(2026, 2, 1, 8, 0),
        )

        program_id = uuid4()
        wbs_id = uuid4()
        uid_to_id = {}
        created_wbs_codes = {"1": wbs_id}
        stats = {"tasks_imported": 0, "wbs_elements_created": 0, "warnings": []}

        mock_wbs_repo = MagicMock()

        await _create_activity(
            task, program_id, mock_session, mock_wbs_repo, uid_to_id, created_wbs_codes, stats
        )

        assert len(stats["warnings"]) == 1
        assert "Unknown constraint type" in stats["warnings"][0]

    @pytest.mark.asyncio
    async def test_get_or_create_wbs_existing_in_cache(self) -> None:
        """Should return cached WBS ID."""
        from unittest.mock import MagicMock
        from uuid import uuid4

        from src.services.msproject_import import _get_or_create_wbs

        wbs_id = uuid4()
        created_wbs_codes = {"1.1": wbs_id}

        result = await _get_or_create_wbs(
            "1.1", uuid4(), MagicMock(), MagicMock(), created_wbs_codes, {}
        )

        assert result == wbs_id

    @pytest.mark.asyncio
    async def test_get_or_create_wbs_existing_in_db(self) -> None:
        """Should find existing WBS in database."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from src.services.msproject_import import _get_or_create_wbs

        wbs_id = uuid4()
        program_id = uuid4()

        mock_wbs = MagicMock()
        mock_wbs.id = wbs_id

        mock_wbs_repo = MagicMock()
        mock_wbs_repo.get_by_code = AsyncMock(return_value=mock_wbs)

        mock_session = MagicMock()
        created_wbs_codes = {}
        stats = {"wbs_elements_created": 0}

        result = await _get_or_create_wbs(
            "2.1", program_id, mock_session, mock_wbs_repo, created_wbs_codes, stats
        )

        assert result == wbs_id
        assert created_wbs_codes["2.1"] == wbs_id
        assert stats["wbs_elements_created"] == 0

    @pytest.mark.asyncio
    async def test_get_or_create_wbs_create_new(self) -> None:
        """Should create new WBS if not found."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from src.services.msproject_import import _get_or_create_wbs

        program_id = uuid4()

        mock_wbs_repo = MagicMock()
        mock_wbs_repo.get_by_code = AsyncMock(return_value=None)

        mock_session = MagicMock()
        created_wbs_codes = {}
        stats = {"wbs_elements_created": 0}

        result = await _get_or_create_wbs(
            "3.1", program_id, mock_session, mock_wbs_repo, created_wbs_codes, stats
        )

        assert result is not None
        assert "3.1" in created_wbs_codes
        assert stats["wbs_elements_created"] == 1
        assert mock_session.add.called


class TestCreateDependencies:
    """Tests for dependency creation function."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        from unittest.mock import MagicMock

        return MagicMock()

    def test_create_dependencies_success(self, mock_session) -> None:
        """Should create dependencies for task."""
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _create_dependencies

        task = ImportedTask(
            uid=2,
            id=2,
            name="Task B",
            wbs="1.1",
            outline_level=2,
            duration_hours=40,
            start=None,
            finish=None,
            is_milestone=False,
            is_summary=False,
            predecessors=[{"predecessor_uid": 1, "type": "FS", "lag": 0}],
        )

        pred_id = uuid4()
        succ_id = uuid4()
        uid_to_id = {1: pred_id, 2: succ_id}

        stats = {"dependencies_imported": 0, "warnings": [], "errors": []}

        _create_dependencies(task, uid_to_id, mock_session, stats)

        assert mock_session.add.called
        assert stats["dependencies_imported"] == 1

    def test_create_dependencies_skip_summary(self, mock_session) -> None:
        """Should skip dependencies for summary tasks."""
        from src.services.msproject_import import ImportedTask, _create_dependencies

        task = ImportedTask(
            uid=1,
            id=1,
            name="Summary",
            wbs="1",
            outline_level=1,
            duration_hours=0,
            start=None,
            finish=None,
            is_milestone=False,
            is_summary=True,
            predecessors=[{"predecessor_uid": 0, "type": "FS", "lag": 0}],
        )

        stats = {"dependencies_imported": 0, "warnings": [], "errors": []}

        _create_dependencies(task, {}, mock_session, stats)

        assert not mock_session.add.called

    def test_create_dependencies_missing_successor(self, mock_session) -> None:
        """Should handle missing successor ID."""
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _create_dependencies

        task = ImportedTask(
            uid=99,
            id=99,
            name="Orphan",
            wbs="1",
            outline_level=1,
            duration_hours=8,
            start=None,
            finish=None,
            is_milestone=False,
            is_summary=False,
            predecessors=[{"predecessor_uid": 1, "type": "FS", "lag": 0}],
        )

        # UID 99 not in mapping
        uid_to_id = {1: uuid4()}

        stats = {"dependencies_imported": 0, "warnings": [], "errors": []}

        _create_dependencies(task, uid_to_id, mock_session, stats)

        assert not mock_session.add.called

    def test_create_dependencies_missing_predecessor(self, mock_session) -> None:
        """Should add warning for missing predecessor."""
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _create_dependencies

        succ_id = uuid4()

        task = ImportedTask(
            uid=2,
            id=2,
            name="Task B",
            wbs="1.1",
            outline_level=2,
            duration_hours=40,
            start=None,
            finish=None,
            is_milestone=False,
            is_summary=False,
            predecessors=[{"predecessor_uid": 999, "type": "FS", "lag": 0}],
        )

        uid_to_id = {2: succ_id}

        stats = {"dependencies_imported": 0, "warnings": [], "errors": []}

        _create_dependencies(task, uid_to_id, mock_session, stats)

        assert not mock_session.add.called
        assert len(stats["warnings"]) == 1
        assert "999 not found" in stats["warnings"][0]

    def test_create_dependencies_with_lag(self, mock_session) -> None:
        """Should create dependency with lag days."""
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _create_dependencies

        task = ImportedTask(
            uid=2,
            id=2,
            name="Task B",
            wbs="1.1",
            outline_level=2,
            duration_hours=40,
            start=None,
            finish=None,
            is_milestone=False,
            is_summary=False,
            predecessors=[{"predecessor_uid": 1, "type": "FS", "lag": 2}],
        )

        pred_id = uuid4()
        succ_id = uuid4()
        uid_to_id = {1: pred_id, 2: succ_id}

        stats = {"dependencies_imported": 0, "warnings": [], "errors": []}

        _create_dependencies(task, uid_to_id, mock_session, stats)

        call_args = mock_session.add.call_args
        dependency = call_args[0][0]
        assert dependency.lag == 2

    def test_create_dependencies_error_handling(self, mock_session) -> None:
        """Should catch and log errors during dependency creation."""
        from uuid import uuid4

        from src.services.msproject_import import ImportedTask, _create_dependencies

        task = ImportedTask(
            uid=2,
            id=2,
            name="Task B",
            wbs="1.1",
            outline_level=2,
            duration_hours=40,
            start=None,
            finish=None,
            is_milestone=False,
            is_summary=False,
            predecessors=[{"predecessor_uid": 1, "type": "FS", "lag": 0}],
        )

        pred_id = uuid4()
        succ_id = uuid4()
        uid_to_id = {1: pred_id, 2: succ_id}

        mock_session.add.side_effect = Exception("Database error")

        stats = {"dependencies_imported": 0, "warnings": [], "errors": []}

        _create_dependencies(task, uid_to_id, mock_session, stats)

        assert len(stats["errors"]) == 1
        assert "Error creating dependency" in stats["errors"][0]
