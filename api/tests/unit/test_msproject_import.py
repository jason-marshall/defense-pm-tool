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
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
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
</Project>'''

        xml_file = tmp_path / "test_project.xml"
        xml_file.write_text(xml_content)
        return xml_file

    @pytest.fixture
    def sample_xml_no_namespace(self, tmp_path: Path) -> Path:
        """Create sample MS Project XML without namespace."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
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
</Project>'''

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
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
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
</Project>'''

        xml_file = tmp_path / "no_dates.xml"
        xml_file.write_text(xml_content)

        importer = MSProjectImporter(xml_file)
        project = importer.parse()

        assert len(project.warnings) >= 1
        assert any("start date" in w.lower() for w in project.warnings)

    def test_empty_tasks_adds_warning(self, tmp_path: Path) -> None:
        """Should add warning when no tasks element found."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Name>Empty Project</Name>
  <StartDate>2026-01-01T08:00:00</StartDate>
  <FinishDate>2026-12-31T17:00:00</FinishDate>
</Project>'''

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
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
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
</Project>'''

        xml_file = tmp_path / "test.xml"
        xml_file.write_text(xml_content)

        importer = MSProjectImporter(xml_file)
        project = importer.parse()

        assert project.tasks[0].duration_hours == 80.0

    def test_parse_hours_and_minutes(self, tmp_path: Path) -> None:
        """Should parse duration with hours and minutes."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
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
</Project>'''

        xml_file = tmp_path / "test.xml"
        xml_file.write_text(xml_content)

        importer = MSProjectImporter(xml_file)
        project = importer.parse()

        assert project.tasks[0].duration_hours == 8.5

    def test_parse_zero_duration(self, tmp_path: Path) -> None:
        """Should parse zero duration (milestone)."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
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
</Project>'''

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
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
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
</Project>'''

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
