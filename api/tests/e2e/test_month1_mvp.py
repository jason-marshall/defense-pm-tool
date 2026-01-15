"""
End-to-End Test Suite for Month 1 MVP.

This module contains comprehensive E2E tests that validate the complete
workflows implemented in Month 1:
1. Program Lifecycle (create, WBS, activities, dependencies, CPM)
2. EVMS Workflow (periods, data entry, metrics calculation)
3. MS Project Import (XML parsing, activity/dependency creation)
4. Report Generation (CPR Format 1)

These tests use mock repositories to simulate database operations
while testing the full integration of services and business logic.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID, uuid4

import pytest

from src.models.enums import ConstraintType, DependencyType
from src.services.cpm import CPMEngine
from src.services.evms import EVMSCalculator
from src.services.msproject_import import MSProjectImporter

# ReportGenerator requires full mock setup, testing EVMS calculations directly instead


@dataclass
class MockActivity:
    """Mock activity for E2E testing."""

    id: UUID
    program_id: UUID
    wbs_id: UUID
    code: str
    name: str
    duration: int
    percent_complete: Decimal = Decimal("0.00")
    budgeted_cost: Decimal = Decimal("0.00")
    actual_cost: Decimal = Decimal("0.00")
    is_milestone: bool = False
    total_float: int | None = None
    free_float: int | None = None
    is_critical: bool = False
    constraint_type: ConstraintType = ConstraintType.ASAP
    constraint_date: date | None = None


@dataclass
class MockDependency:
    """Mock dependency for E2E testing."""

    id: UUID
    predecessor_id: UUID
    successor_id: UUID
    dependency_type: str
    lag: int = 0


@dataclass
class MockWBSElement:
    """Mock WBS element for E2E testing."""

    id: UUID
    program_id: UUID
    parent_id: UUID | None
    wbs_code: str
    name: str
    path: str
    level: int
    budgeted_cost: Decimal = Decimal("0.00")


@dataclass
class MockProgram:
    """Mock program for E2E testing."""

    id: UUID
    name: str
    code: str
    start_date: date
    end_date: date
    budget_at_completion: Decimal = Decimal("1000000.00")
    activities: list[MockActivity] = field(default_factory=list)
    wbs_elements: list[MockWBSElement] = field(default_factory=list)
    dependencies: list[MockDependency] = field(default_factory=list)


@dataclass
class MockEVMSPeriod:
    """Mock EVMS period for testing."""

    id: UUID
    program_id: UUID
    period_name: str
    period_start: date
    period_end: date
    cumulative_bcws: Decimal = Decimal("0.00")
    cumulative_bcwp: Decimal = Decimal("0.00")
    cumulative_acwp: Decimal = Decimal("0.00")


class TestProgramLifecycleE2E:
    """E2E tests for complete program lifecycle."""

    def test_full_program_workflow(self) -> None:
        """
        Test complete program workflow:
        1. Create program
        2. Create WBS hierarchy
        3. Add activities
        4. Create dependencies
        5. Run CPM calculation
        6. Verify critical path
        """
        # 1. Create program
        program = MockProgram(
            id=uuid4(),
            name="Defense Radar System",
            code="DRS-001",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            budget_at_completion=Decimal("5000000.00"),
        )

        # 2. Create WBS hierarchy
        wbs_root = MockWBSElement(
            id=uuid4(),
            program_id=program.id,
            parent_id=None,
            wbs_code="1",
            name="Radar System",
            path="1",
            level=1,
            budgeted_cost=Decimal("5000000.00"),
        )
        wbs_design = MockWBSElement(
            id=uuid4(),
            program_id=program.id,
            parent_id=wbs_root.id,
            wbs_code="1.1",
            name="Design Phase",
            path="1.1",
            level=2,
            budgeted_cost=Decimal("1000000.00"),
        )
        wbs_development = MockWBSElement(
            id=uuid4(),
            program_id=program.id,
            parent_id=wbs_root.id,
            wbs_code="1.2",
            name="Development Phase",
            path="1.2",
            level=2,
            budgeted_cost=Decimal("3000000.00"),
        )
        wbs_testing = MockWBSElement(
            id=uuid4(),
            program_id=program.id,
            parent_id=wbs_root.id,
            wbs_code="1.3",
            name="Testing Phase",
            path="1.3",
            level=2,
            budgeted_cost=Decimal("1000000.00"),
        )

        program.wbs_elements = [wbs_root, wbs_design, wbs_development, wbs_testing]

        # 3. Add activities (chain for critical path)
        activities = [
            MockActivity(
                id=uuid4(),
                program_id=program.id,
                wbs_id=wbs_design.id,
                code="A-001",
                name="Requirements Analysis",
                duration=10,
                budgeted_cost=Decimal("200000.00"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=program.id,
                wbs_id=wbs_design.id,
                code="A-002",
                name="System Design",
                duration=15,
                budgeted_cost=Decimal("300000.00"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=program.id,
                wbs_id=wbs_development.id,
                code="A-003",
                name="Hardware Development",
                duration=30,
                budgeted_cost=Decimal("1500000.00"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=program.id,
                wbs_id=wbs_development.id,
                code="A-004",
                name="Software Development",
                duration=25,
                budgeted_cost=Decimal("1000000.00"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=program.id,
                wbs_id=wbs_testing.id,
                code="A-005",
                name="Integration Testing",
                duration=20,
                budgeted_cost=Decimal("800000.00"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=program.id,
                wbs_id=wbs_testing.id,
                code="A-006",
                name="Acceptance Testing",
                duration=10,
                budgeted_cost=Decimal("200000.00"),
                is_milestone=False,
            ),
        ]
        program.activities = activities

        # 4. Create dependencies
        # A-001 -> A-002 -> A-003 -> A-005 -> A-006 (critical path)
        #                -> A-004 -> A-005 (parallel path, shorter)
        dependencies = [
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[0].id,
                successor_id=activities[1].id,
                dependency_type=DependencyType.FS.value,
            ),
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[1].id,
                successor_id=activities[2].id,
                dependency_type=DependencyType.FS.value,
            ),
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[1].id,
                successor_id=activities[3].id,
                dependency_type=DependencyType.FS.value,
            ),
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[2].id,
                successor_id=activities[4].id,
                dependency_type=DependencyType.FS.value,
            ),
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[3].id,
                successor_id=activities[4].id,
                dependency_type=DependencyType.FS.value,
            ),
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[4].id,
                successor_id=activities[5].id,
                dependency_type=DependencyType.FS.value,
            ),
        ]
        program.dependencies = dependencies

        # 5. Run CPM calculation
        engine = CPMEngine(activities, dependencies)
        results = engine.calculate()

        # 6. Verify critical path
        assert len(results) == 6

        # Verify early start/finish calculations
        # A-001: ES=0, EF=10
        assert results[activities[0].id].early_start == 0
        assert results[activities[0].id].early_finish == 10

        # A-002: ES=10, EF=25
        assert results[activities[1].id].early_start == 10
        assert results[activities[1].id].early_finish == 25

        # A-003: ES=25, EF=55 (hardware, longer path)
        assert results[activities[2].id].early_start == 25
        assert results[activities[2].id].early_finish == 55

        # A-004: ES=25, EF=50 (software, shorter)
        assert results[activities[3].id].early_start == 25
        assert results[activities[3].id].early_finish == 50

        # A-005: ES=55, EF=75 (waits for hardware)
        assert results[activities[4].id].early_start == 55
        assert results[activities[4].id].early_finish == 75

        # A-006: ES=75, EF=85
        assert results[activities[5].id].early_start == 75
        assert results[activities[5].id].early_finish == 85

        # Verify critical path
        critical_path = engine.get_critical_path()
        critical_ids = set(critical_path)

        # Activities on critical path: A-001, A-002, A-003, A-005, A-006
        assert activities[0].id in critical_ids  # A-001
        assert activities[1].id in critical_ids  # A-002
        assert activities[2].id in critical_ids  # A-003 (hardware)
        assert activities[3].id not in critical_ids  # A-004 (software - has float)
        assert activities[4].id in critical_ids  # A-005
        assert activities[5].id in critical_ids  # A-006

        # Verify project duration
        assert engine.get_project_duration() == 85

    def test_milestone_handling(self) -> None:
        """Test that milestones (zero duration) are handled correctly."""
        program_id = uuid4()
        wbs_id = uuid4()

        activities = [
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code="START",
                name="Project Kickoff",
                duration=0,
                is_milestone=True,
            ),
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code="A-001",
                name="Development",
                duration=10,
            ),
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code="END",
                name="Project Complete",
                duration=0,
                is_milestone=True,
            ),
        ]

        dependencies = [
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[0].id,
                successor_id=activities[1].id,
                dependency_type=DependencyType.FS.value,
            ),
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[1].id,
                successor_id=activities[2].id,
                dependency_type=DependencyType.FS.value,
            ),
        ]

        engine = CPMEngine(activities, dependencies)
        results = engine.calculate()

        # Milestone at start: ES=0, EF=0
        assert results[activities[0].id].early_start == 0
        assert results[activities[0].id].early_finish == 0

        # Development: ES=0, EF=10
        assert results[activities[1].id].early_start == 0
        assert results[activities[1].id].early_finish == 10

        # Milestone at end: ES=10, EF=10
        assert results[activities[2].id].early_start == 10
        assert results[activities[2].id].early_finish == 10


class TestEVMSWorkflowE2E:
    """E2E tests for EVMS workflow."""

    def test_evms_metrics_calculation(self) -> None:
        """Test complete EVMS metrics calculation flow."""
        # Setup: Program with BAC of $1,000,000
        bac = Decimal("1000000.00")

        # Period 1 data
        bcws = Decimal("250000.00")  # Planned to complete 25% by now
        bcwp = Decimal("200000.00")  # Actually completed 20% of work
        acwp = Decimal("220000.00")  # Spent $220,000

        # Calculate variances
        cv = EVMSCalculator.calculate_cost_variance(bcwp, acwp)
        sv = EVMSCalculator.calculate_schedule_variance(bcwp, bcws)

        assert cv == Decimal("-20000.00")  # $20k over budget
        assert sv == Decimal("-50000.00")  # $50k behind schedule

        # Calculate indices
        cpi = EVMSCalculator.calculate_cpi(bcwp, acwp)
        spi = EVMSCalculator.calculate_spi(bcwp, bcws)

        assert cpi is not None
        assert cpi < Decimal("1.00")  # CPI < 1 means over budget
        assert float(cpi) == pytest.approx(0.91, rel=0.01)  # 200/220 ≈ 0.91

        assert spi is not None
        assert spi < Decimal("1.00")  # SPI < 1 means behind schedule
        assert float(spi) == pytest.approx(0.80, rel=0.01)  # 200/250 = 0.80

        # Calculate projections
        eac = EVMSCalculator.calculate_eac(bac, acwp, bcwp, "cpi")
        assert eac is not None
        # EAC = BAC / CPI = 1,000,000 / 0.91 ≈ $1,100,000
        assert float(eac) == pytest.approx(1100000, rel=0.05)

        etc = EVMSCalculator.calculate_etc(eac, acwp)
        assert etc is not None
        # ETC formula: EAC - ACWP
        assert float(etc) == pytest.approx(float(eac) - 220000, rel=0.01)

        vac = EVMSCalculator.calculate_vac(bac, eac)
        assert vac is not None
        # VAC = BAC - EAC (negative means overrun)
        assert vac < 0

        # TCPI for completion at BAC
        tcpi = EVMSCalculator.calculate_tcpi(bac, bcwp, acwp, "bac")
        assert tcpi is not None
        # TCPI formula: (BAC - BCWP) / (BAC - ACWP)
        # (1,000,000 - 200,000) / (1,000,000 - 220,000) = 800,000 / 780,000 ≈ 1.03
        assert float(tcpi) == pytest.approx(1.03, rel=0.01)

    def test_evms_zero_division_handling(self) -> None:
        """Test that EVMS calculations handle zero values gracefully."""
        # CPI with zero ACWP
        cpi = EVMSCalculator.calculate_cpi(Decimal("100.00"), Decimal("0.00"))
        assert cpi is None

        # SPI with zero BCWS
        spi = EVMSCalculator.calculate_spi(Decimal("100.00"), Decimal("0.00"))
        assert spi is None

        # TCPI with zero remaining work (BAC == BCWP)
        # When all work is done, TCPI becomes 0 or undefined
        tcpi = EVMSCalculator.calculate_tcpi(
            Decimal("1000.00"),
            Decimal("1000.00"),  # BCWP = BAC, all work done
            Decimal("900.00"),  # ACWP
            "bac",
        )
        # TCPI = (BAC - BCWP) / (BAC - ACWP) = 0 / 100 = 0
        assert tcpi == Decimal("0.00")

    def test_evms_multiple_periods(self) -> None:
        """Test EVMS calculations across multiple periods."""
        bac = Decimal("1000000.00")

        # Period 1 - good performance
        # CPI1 = 95000 / 90000 = 1.06
        period1_bcwp = Decimal("95000.00")
        period1_acwp = Decimal("90000.00")

        # Period 2 (cumulative) - performance declining
        # CPI2 = 240000 / 250000 = 0.96
        period2_bcwp = Decimal("240000.00")
        period2_acwp = Decimal("250000.00")

        # Period 3 (cumulative) - performance worse
        # CPI3 = 380000 / 420000 = 0.90
        period3_bcwp = Decimal("380000.00")
        period3_acwp = Decimal("420000.00")

        # Verify trend: CPI getting worse (declining)
        cpi1 = EVMSCalculator.calculate_cpi(period1_bcwp, period1_acwp)
        cpi2 = EVMSCalculator.calculate_cpi(period2_bcwp, period2_acwp)
        cpi3 = EVMSCalculator.calculate_cpi(period3_bcwp, period3_acwp)

        assert cpi1 is not None
        assert cpi2 is not None
        assert cpi3 is not None

        # CPI should be declining (cost performance worsening)
        assert cpi1 > cpi2 > cpi3

        # EAC should be increasing (projected cost rising)
        eac1 = EVMSCalculator.calculate_eac(bac, period1_acwp, period1_bcwp, "cpi")
        eac2 = EVMSCalculator.calculate_eac(bac, period2_acwp, period2_bcwp, "cpi")
        eac3 = EVMSCalculator.calculate_eac(bac, period3_acwp, period3_bcwp, "cpi")

        assert eac1 is not None
        assert eac2 is not None
        assert eac3 is not None
        assert eac1 < eac2 < eac3


class TestMSProjectImportE2E:
    """E2E tests for MS Project import workflow."""

    def create_sample_msproject_xml(self) -> str:
        """Create a sample MS Project XML string for testing."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
    <Name>Test Import Project</Name>
    <StartDate>2026-02-01T08:00:00</StartDate>
    <FinishDate>2026-06-30T17:00:00</FinishDate>
    <Tasks>
        <Task>
            <UID>0</UID>
            <ID>0</ID>
            <Name>Test Import Project</Name>
            <IsNull>1</IsNull>
        </Task>
        <Task>
            <UID>1</UID>
            <ID>1</ID>
            <Name>Project Start</Name>
            <WBS>1</WBS>
            <OutlineLevel>1</OutlineLevel>
            <Duration>PT0H0M0S</Duration>
            <Start>2026-02-01T08:00:00</Start>
            <Finish>2026-02-01T08:00:00</Finish>
            <Milestone>1</Milestone>
        </Task>
        <Task>
            <UID>2</UID>
            <ID>2</ID>
            <Name>Phase 1: Planning</Name>
            <WBS>1.1</WBS>
            <OutlineLevel>2</OutlineLevel>
            <Duration>PT40H0M0S</Duration>
            <Start>2026-02-02T08:00:00</Start>
            <Finish>2026-02-06T17:00:00</Finish>
            <PercentComplete>50</PercentComplete>
            <PredecessorLink>
                <PredecessorUID>1</PredecessorUID>
                <Type>1</Type>
                <LinkLag>0</LinkLag>
            </PredecessorLink>
        </Task>
        <Task>
            <UID>3</UID>
            <ID>3</ID>
            <Name>Phase 2: Execution</Name>
            <WBS>1.2</WBS>
            <OutlineLevel>2</OutlineLevel>
            <Duration>PT80H0M0S</Duration>
            <Start>2026-02-09T08:00:00</Start>
            <Finish>2026-02-20T17:00:00</Finish>
            <PercentComplete>0</PercentComplete>
            <PredecessorLink>
                <PredecessorUID>2</PredecessorUID>
                <Type>1</Type>
                <LinkLag>0</LinkLag>
            </PredecessorLink>
        </Task>
        <Task>
            <UID>4</UID>
            <ID>4</ID>
            <Name>Parallel Task</Name>
            <WBS>1.3</WBS>
            <OutlineLevel>2</OutlineLevel>
            <Duration>PT60H0M0S</Duration>
            <Start>2026-02-09T08:00:00</Start>
            <Finish>2026-02-17T17:00:00</Finish>
            <PredecessorLink>
                <PredecessorUID>2</PredecessorUID>
                <Type>3</Type>
                <LinkLag>0</LinkLag>
            </PredecessorLink>
        </Task>
        <Task>
            <UID>5</UID>
            <ID>5</ID>
            <Name>Project End</Name>
            <WBS>1.4</WBS>
            <OutlineLevel>2</OutlineLevel>
            <Duration>PT0H0M0S</Duration>
            <Start>2026-02-20T17:00:00</Start>
            <Finish>2026-02-20T17:00:00</Finish>
            <Milestone>1</Milestone>
            <PredecessorLink>
                <PredecessorUID>3</PredecessorUID>
                <Type>0</Type>
                <LinkLag>0</LinkLag>
            </PredecessorLink>
            <PredecessorLink>
                <PredecessorUID>4</PredecessorUID>
                <Type>1</Type>
                <LinkLag>0</LinkLag>
            </PredecessorLink>
        </Task>
    </Tasks>
</Project>"""

    def test_msproject_import_complete_workflow(self) -> None:
        """Test complete MS Project import workflow."""
        xml_content = self.create_sample_msproject_xml()

        # Write to temp file
        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        try:
            # Parse the file
            importer = MSProjectImporter(temp_path)
            project = importer.parse()

            # Verify project metadata
            assert project.name == "Test Import Project"
            assert project.start_date.date() == date(2026, 2, 1)
            assert project.finish_date.date() == date(2026, 6, 30)

            # Verify tasks (excluding null task)
            assert len(project.tasks) == 5

            # Verify task properties
            task1 = project.tasks[0]  # Project Start (milestone)
            assert task1.name == "Project Start"
            assert task1.is_milestone is True
            assert task1.duration_hours == 0

            task2 = project.tasks[1]  # Phase 1
            assert task2.name == "Phase 1: Planning"
            assert task2.duration_hours == 40
            assert task2.percent_complete == Decimal("50")
            assert len(task2.predecessors) == 1

            task3 = project.tasks[2]  # Phase 2
            assert task3.name == "Phase 2: Execution"
            assert task3.duration_hours == 80
            assert len(task3.predecessors) == 1
            # FS dependency (Type 1)
            assert task3.predecessors[0]["type"] == DependencyType.FS.value

            task4 = project.tasks[3]  # Parallel Task
            assert task4.name == "Parallel Task"
            assert len(task4.predecessors) == 1
            # SS dependency (Type 3)
            assert task4.predecessors[0]["type"] == DependencyType.SS.value

            task5 = project.tasks[4]  # Project End (milestone)
            assert task5.name == "Project End"
            assert task5.is_milestone is True
            assert len(task5.predecessors) == 2
            # FF and FS dependencies (stored as string values)
            dep_types = {p["type"] for p in task5.predecessors}
            assert DependencyType.FF.value in dep_types
            assert DependencyType.FS.value in dep_types

        finally:
            temp_path.unlink()

    def test_msproject_import_with_constraints(self) -> None:
        """Test MS Project import with scheduling constraints."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
    <Name>Constraint Test</Name>
    <StartDate>2026-01-01T08:00:00</StartDate>
    <FinishDate>2026-03-31T17:00:00</FinishDate>
    <Tasks>
        <Task>
            <UID>0</UID>
            <ID>0</ID>
            <Name>Constraint Test</Name>
            <IsNull>1</IsNull>
        </Task>
        <Task>
            <UID>1</UID>
            <ID>1</ID>
            <Name>SNET Task</Name>
            <WBS>1</WBS>
            <OutlineLevel>1</OutlineLevel>
            <Duration>PT40H0M0S</Duration>
            <ConstraintType>2</ConstraintType>
            <ConstraintDate>2026-01-15T08:00:00</ConstraintDate>
        </Task>
        <Task>
            <UID>2</UID>
            <ID>2</ID>
            <Name>FNLT Task</Name>
            <WBS>2</WBS>
            <OutlineLevel>1</OutlineLevel>
            <Duration>PT40H0M0S</Duration>
            <ConstraintType>5</ConstraintType>
            <ConstraintDate>2026-02-28T17:00:00</ConstraintDate>
        </Task>
    </Tasks>
</Project>"""

        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        try:
            importer = MSProjectImporter(temp_path)
            project = importer.parse()

            assert len(project.tasks) == 2

            # SNET constraint
            snet_task = project.tasks[0]
            assert snet_task.constraint_type == ConstraintType.SNET
            assert snet_task.constraint_date.date() == date(2026, 1, 15)

            # FNLT constraint
            fnlt_task = project.tasks[1]
            assert fnlt_task.constraint_type == ConstraintType.FNLT
            assert fnlt_task.constraint_date.date() == date(2026, 2, 28)

        finally:
            temp_path.unlink()

    def test_msproject_import_with_lag(self) -> None:
        """Test MS Project import with lag values."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
    <Name>Lag Test</Name>
    <StartDate>2026-01-01T08:00:00</StartDate>
    <FinishDate>2026-03-31T17:00:00</FinishDate>
    <Tasks>
        <Task>
            <UID>0</UID>
            <ID>0</ID>
            <Name>Lag Test</Name>
            <IsNull>1</IsNull>
        </Task>
        <Task>
            <UID>1</UID>
            <ID>1</ID>
            <Name>Task A</Name>
            <WBS>1</WBS>
            <Duration>PT40H0M0S</Duration>
        </Task>
        <Task>
            <UID>2</UID>
            <ID>2</ID>
            <Name>Task B with 2-day lag</Name>
            <WBS>2</WBS>
            <Duration>PT40H0M0S</Duration>
            <PredecessorLink>
                <PredecessorUID>1</PredecessorUID>
                <Type>1</Type>
                <LinkLag>9600</LinkLag>
            </PredecessorLink>
        </Task>
    </Tasks>
</Project>"""

        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        try:
            importer = MSProjectImporter(temp_path)
            project = importer.parse()

            task_b = project.tasks[1]
            assert len(task_b.predecessors) == 1
            # 9600 tenths of minutes = 960 minutes = 16 hours = 2 working days
            assert task_b.predecessors[0]["lag"] == 2

        finally:
            temp_path.unlink()


class TestReportGenerationE2E:
    """E2E tests for report generation data preparation."""

    def test_cpr_format1_data_preparation(self) -> None:
        """Test CPR Format 1 report data preparation and calculations."""
        # Create mock data for report - simulating WBS-level aggregation
        wbs_data = [
            {
                "wbs_code": "1.1",
                "wbs_name": "Engineering",
                "bcws": Decimal("100000.00"),
                "bcwp": Decimal("95000.00"),
                "acwp": Decimal("98000.00"),
                "bac": Decimal("500000.00"),
            },
            {
                "wbs_code": "1.2",
                "wbs_name": "Manufacturing",
                "bcws": Decimal("150000.00"),
                "bcwp": Decimal("140000.00"),
                "acwp": Decimal("155000.00"),
                "bac": Decimal("800000.00"),
            },
            {
                "wbs_code": "1.3",
                "wbs_name": "Testing",
                "bcws": Decimal("50000.00"),
                "bcwp": Decimal("45000.00"),
                "acwp": Decimal("48000.00"),
                "bac": Decimal("200000.00"),
            },
        ]

        # Calculate totals (simulating report aggregation)
        total_bcws = sum(d["bcws"] for d in wbs_data)
        total_bcwp = sum(d["bcwp"] for d in wbs_data)
        total_acwp = sum(d["acwp"] for d in wbs_data)
        total_bac = sum(d["bac"] for d in wbs_data)

        # Verify totals
        assert total_bcws == Decimal("300000.00")
        assert total_bcwp == Decimal("280000.00")
        assert total_acwp == Decimal("301000.00")
        assert total_bac == Decimal("1500000.00")

        # Calculate variances
        cv = EVMSCalculator.calculate_cost_variance(total_bcwp, total_acwp)
        sv = EVMSCalculator.calculate_schedule_variance(total_bcwp, total_bcws)

        assert cv == Decimal("-21000.00")  # BCWP - ACWP
        assert sv == Decimal("-20000.00")  # BCWP - BCWS

        # Calculate indices
        cpi = EVMSCalculator.calculate_cpi(total_bcwp, total_acwp)
        spi = EVMSCalculator.calculate_spi(total_bcwp, total_bcws)

        assert cpi is not None
        assert spi is not None
        assert float(cpi) < 1.0  # Over budget
        assert float(spi) < 1.0  # Behind schedule

        # Calculate projections
        eac = EVMSCalculator.calculate_eac(total_bac, total_acwp, total_bcwp, "cpi")
        assert eac is not None
        assert eac > total_bac  # Project will overrun

        # Calculate percent complete
        percent_complete = (total_bcwp / total_bac * 100).quantize(Decimal("0.01"))
        percent_spent = (total_acwp / total_bac * 100).quantize(Decimal("0.01"))

        # 280000 / 1500000 * 100 = 18.67%
        assert float(percent_complete) == pytest.approx(18.67, rel=0.01)
        # 301000 / 1500000 * 100 = 20.07%
        assert float(percent_spent) == pytest.approx(20.07, rel=0.01)

        # Verify that percent spent > percent complete (overrun indicator)
        assert percent_spent > percent_complete


class TestIntegrationScenarios:
    """Integration tests combining multiple features."""

    def test_import_and_calculate_schedule(self) -> None:
        """Test importing MS Project and running CPM calculation."""
        # Create a simple project XML
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
    <Name>Integration Test</Name>
    <StartDate>2026-01-01T08:00:00</StartDate>
    <FinishDate>2026-03-31T17:00:00</FinishDate>
    <Tasks>
        <Task>
            <UID>0</UID>
            <ID>0</ID>
            <Name>Integration Test</Name>
            <IsNull>1</IsNull>
        </Task>
        <Task>
            <UID>1</UID>
            <ID>1</ID>
            <Name>Task A</Name>
            <WBS>1</WBS>
            <Duration>PT40H0M0S</Duration>
        </Task>
        <Task>
            <UID>2</UID>
            <ID>2</ID>
            <Name>Task B</Name>
            <WBS>2</WBS>
            <Duration>PT80H0M0S</Duration>
            <PredecessorLink>
                <PredecessorUID>1</PredecessorUID>
                <Type>1</Type>
                <LinkLag>0</LinkLag>
            </PredecessorLink>
        </Task>
        <Task>
            <UID>3</UID>
            <ID>3</ID>
            <Name>Task C</Name>
            <WBS>3</WBS>
            <Duration>PT40H0M0S</Duration>
            <PredecessorLink>
                <PredecessorUID>2</PredecessorUID>
                <Type>1</Type>
                <LinkLag>0</LinkLag>
            </PredecessorLink>
        </Task>
    </Tasks>
</Project>"""

        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        try:
            # Step 1: Import the project
            importer = MSProjectImporter(temp_path)
            project = importer.parse()

            assert len(project.tasks) == 3

            # Step 2: Convert imported tasks to mock activities
            program_id = uuid4()
            wbs_id = uuid4()
            uid_to_id: dict[int, UUID] = {}

            activities = []
            for task in project.tasks:
                activity_id = uuid4()
                uid_to_id[task.uid] = activity_id
                activities.append(
                    MockActivity(
                        id=activity_id,
                        program_id=program_id,
                        wbs_id=wbs_id,
                        code=f"A-{task.uid:03d}",
                        name=task.name,
                        duration=int(task.duration_hours / 8),  # Convert hours to days
                    )
                )

            # Step 3: Convert imported dependencies
            dependencies = []
            for task in project.tasks:
                for pred in task.predecessors:
                    pred_uid = pred["predecessor_uid"]
                    if pred_uid in uid_to_id:
                        dependencies.append(
                            MockDependency(
                                id=uuid4(),
                                predecessor_id=uid_to_id[pred_uid],
                                successor_id=uid_to_id[task.uid],
                                dependency_type=pred["type"],  # Already a string value
                                lag=pred["lag"],
                            )
                        )

            # Step 4: Run CPM
            engine = CPMEngine(activities, dependencies)
            results = engine.calculate()

            # Step 5: Verify results
            assert len(results) == 3

            # Task A: 5 days (40h/8h), ES=0, EF=5
            task_a_id = uid_to_id[1]
            assert results[task_a_id].early_start == 0
            assert results[task_a_id].early_finish == 5

            # Task B: 10 days (80h/8h), ES=5, EF=15
            task_b_id = uid_to_id[2]
            assert results[task_b_id].early_start == 5
            assert results[task_b_id].early_finish == 15

            # Task C: 5 days, ES=15, EF=20
            task_c_id = uid_to_id[3]
            assert results[task_c_id].early_start == 15
            assert results[task_c_id].early_finish == 20

            # All tasks should be on critical path (single chain)
            critical_path = engine.get_critical_path()
            assert len(critical_path) == 3

        finally:
            temp_path.unlink()

    def test_evms_with_cpm_data(self) -> None:
        """Test EVMS calculations using CPM schedule data."""
        # Create activities with schedule and cost data
        program_id = uuid4()
        wbs_id = uuid4()

        activities = [
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code="A-001",
                name="Design",
                duration=10,
                budgeted_cost=Decimal("50000.00"),
                percent_complete=Decimal("100.00"),
                actual_cost=Decimal("52000.00"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code="A-002",
                name="Development",
                duration=20,
                budgeted_cost=Decimal("100000.00"),
                percent_complete=Decimal("50.00"),
                actual_cost=Decimal("55000.00"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=program_id,
                wbs_id=wbs_id,
                code="A-003",
                name="Testing",
                duration=10,
                budgeted_cost=Decimal("30000.00"),
                percent_complete=Decimal("0.00"),
                actual_cost=Decimal("0.00"),
            ),
        ]

        dependencies = [
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[0].id,
                successor_id=activities[1].id,
                dependency_type=DependencyType.FS.value,
            ),
            MockDependency(
                id=uuid4(),
                predecessor_id=activities[1].id,
                successor_id=activities[2].id,
                dependency_type=DependencyType.FS.value,
            ),
        ]

        # Run CPM
        engine = CPMEngine(activities, dependencies)
        engine.calculate()

        # Calculate EVMS from schedule data
        # BAC = sum of budgeted costs
        bac = sum(a.budgeted_cost for a in activities)
        assert bac == Decimal("180000.00")

        # BCWP = sum of earned values (budgeted * % complete)
        bcwp = sum(a.budgeted_cost * a.percent_complete / Decimal("100") for a in activities)
        # 50000 * 1.0 + 100000 * 0.5 + 30000 * 0 = 100000
        assert bcwp == Decimal("100000.00")

        # ACWP = sum of actual costs
        acwp = sum(a.actual_cost for a in activities)
        assert acwp == Decimal("107000.00")

        # Calculate indices
        cpi = EVMSCalculator.calculate_cpi(bcwp, acwp)
        assert cpi is not None
        # CPI = 100000 / 107000 ≈ 0.93
        assert float(cpi) == pytest.approx(0.93, rel=0.02)

        # Project duration from CPM
        project_duration = engine.get_project_duration()
        assert project_duration == 40  # 10 + 20 + 10 days
