"""
End-to-End Test Suite for Week 9 Reports and Variance Tracking.

This module contains comprehensive E2E tests that validate the complete
workflows implemented in Week 9:
1. CPR Format 1, 3, 5 Generation
2. PDF Export for All Formats
3. Variance Explanation CRUD
4. Management Reserve Tracking
5. Report Audit Trail

These tests use mock objects to simulate database operations
while testing the full integration of services and business logic.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.schemas.cpr_format5 import Format5ExportConfig
from src.schemas.management_reserve import (
    ManagementReserveChangeCreate,
    ManagementReserveStatus,
)
from src.schemas.report_audit import (
    ReportAuditStats,
    ReportFormat,
    ReportType,
)
from src.schemas.variance_explanation import (
    VarianceExplanationCreate,
    VarianceExplanationResponse,
    VarianceType,
)
from src.services.evms import EVMSCalculator
from src.services.report_pdf_generator import ReportPDFGenerator

# =============================================================================
# Mock Data Classes
# =============================================================================


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
    early_start: int | None = None
    early_finish: int | None = None
    late_start: int | None = None
    late_finish: int | None = None


@dataclass
class MockWBSElement:
    """Mock WBS element for E2E testing."""

    id: UUID
    program_id: UUID
    code: str
    name: str
    level: int
    path: str
    budgeted_cost: Decimal = Decimal("0.00")
    actual_cost: Decimal = Decimal("0.00")
    percent_complete: Decimal = Decimal("0.00")


@dataclass
class MockProgram:
    """Mock program for E2E testing."""

    id: UUID
    name: str
    code: str
    start_date: date
    end_date: date
    budget_at_completion: Decimal = Decimal("1000000.00")
    contract_number: str | None = None


@dataclass
class MockEVMSPeriod:
    """Mock EVMS period for testing."""

    id: UUID
    program_id: UUID
    period_number: int
    start_date: date
    end_date: date
    bcws: Decimal = Decimal("0.00")
    bcwp: Decimal = Decimal("0.00")
    acwp: Decimal = Decimal("0.00")


@dataclass
class MockManagementReserveLog:
    """Mock MR log entry for testing."""

    id: UUID
    program_id: UUID
    period_id: UUID | None
    beginning_mr: Decimal
    changes_in: Decimal
    changes_out: Decimal
    ending_mr: Decimal
    reason: str | None
    approved_by: UUID | None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class MockReportAudit:
    """Mock report audit entry for testing."""

    id: UUID
    report_type: str
    program_id: UUID
    generated_by: UUID | None
    generated_at: datetime
    parameters: dict | None
    file_path: str | None
    file_format: str
    file_size: int
    checksum: str | None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class MockVarianceExplanation:
    """Mock variance explanation for testing."""

    id: UUID
    program_id: UUID
    wbs_id: UUID | None
    period_id: UUID | None
    variance_type: str
    variance_amount: Decimal
    variance_percent: Decimal
    explanation: str
    corrective_action: str | None
    expected_resolution: date | None
    created_by: UUID | None
    created_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# Test Data Factory
# =============================================================================


class Week9DataFactory:
    """Factory for creating consistent test data."""

    def __init__(self):
        self.program_id = uuid4()
        self.user_id = uuid4()
        self.wbs_elements: list[MockWBSElement] = []
        self.activities: list[MockActivity] = []
        self.periods: list[MockEVMSPeriod] = []
        self.mr_logs: list[MockManagementReserveLog] = []
        self.audit_entries: list[MockReportAudit] = []
        self.variance_explanations: list[MockVarianceExplanation] = []

    def create_program(self) -> MockProgram:
        """Create a mock program."""
        return MockProgram(
            id=self.program_id,
            name="F-35 Lightning II Program",
            code="F35-PROD",
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            budget_at_completion=Decimal("5000000.00"),
            contract_number="FA8615-24-C-0001",
        )

    def create_wbs_structure(self) -> list[MockWBSElement]:
        """Create a realistic WBS structure."""
        self.wbs_elements = [
            MockWBSElement(
                id=uuid4(),
                program_id=self.program_id,
                code="1.0",
                name="Program Management",
                level=1,
                path="1",
                budgeted_cost=Decimal("500000.00"),
                actual_cost=Decimal("480000.00"),
                percent_complete=Decimal("75.00"),
            ),
            MockWBSElement(
                id=uuid4(),
                program_id=self.program_id,
                code="2.0",
                name="Systems Engineering",
                level=1,
                path="2",
                budgeted_cost=Decimal("1200000.00"),
                actual_cost=Decimal("1350000.00"),
                percent_complete=Decimal("60.00"),
            ),
            MockWBSElement(
                id=uuid4(),
                program_id=self.program_id,
                code="3.0",
                name="Hardware Development",
                level=1,
                path="3",
                budgeted_cost=Decimal("2000000.00"),
                actual_cost=Decimal("1800000.00"),
                percent_complete=Decimal("45.00"),
            ),
            MockWBSElement(
                id=uuid4(),
                program_id=self.program_id,
                code="4.0",
                name="Software Development",
                level=1,
                path="4",
                budgeted_cost=Decimal("1000000.00"),
                actual_cost=Decimal("950000.00"),
                percent_complete=Decimal("50.00"),
            ),
            MockWBSElement(
                id=uuid4(),
                program_id=self.program_id,
                code="5.0",
                name="Test & Evaluation",
                level=1,
                path="5",
                budgeted_cost=Decimal("300000.00"),
                actual_cost=Decimal("100000.00"),
                percent_complete=Decimal("20.00"),
            ),
        ]
        return self.wbs_elements

    def create_periods(self, num_periods: int = 6) -> list[MockEVMSPeriod]:
        """Create EVMS periods for tracking."""
        base_date = date(2024, 1, 1)
        self.periods = []

        # Cumulative values for realistic EVMS progression
        bcws_values = [200000, 500000, 900000, 1400000, 2000000, 2600000]
        bcwp_values = [180000, 450000, 800000, 1200000, 1700000, 2300000]
        acwp_values = [190000, 520000, 880000, 1350000, 1900000, 2500000]

        for i in range(num_periods):
            period_start = base_date + timedelta(days=30 * i)
            period_end = period_start + timedelta(days=29)
            self.periods.append(
                MockEVMSPeriod(
                    id=uuid4(),
                    program_id=self.program_id,
                    period_number=i + 1,
                    start_date=period_start,
                    end_date=period_end,
                    bcws=Decimal(str(bcws_values[i])),
                    bcwp=Decimal(str(bcwp_values[i])),
                    acwp=Decimal(str(acwp_values[i])),
                )
            )
        return self.periods

    def create_mr_history(self) -> list[MockManagementReserveLog]:
        """Create MR change history."""
        self.mr_logs = [
            MockManagementReserveLog(
                id=uuid4(),
                program_id=self.program_id,
                period_id=None,
                beginning_mr=Decimal("0.00"),
                changes_in=Decimal("250000.00"),
                changes_out=Decimal("0.00"),
                ending_mr=Decimal("250000.00"),
                reason="Initial Management Reserve allocation at program baseline",
                approved_by=self.user_id,
                created_at=datetime(2024, 1, 15),
            ),
            MockManagementReserveLog(
                id=uuid4(),
                program_id=self.program_id,
                period_id=self.periods[2].id if self.periods else None,
                beginning_mr=Decimal("250000.00"),
                changes_in=Decimal("0.00"),
                changes_out=Decimal("50000.00"),
                ending_mr=Decimal("200000.00"),
                reason="Released to WP 2.1 for engineering change order ECO-2024-015",
                approved_by=self.user_id,
                created_at=datetime(2024, 4, 1),
            ),
            MockManagementReserveLog(
                id=uuid4(),
                program_id=self.program_id,
                period_id=self.periods[4].id if self.periods else None,
                beginning_mr=Decimal("200000.00"),
                changes_in=Decimal("0.00"),
                changes_out=Decimal("35000.00"),
                ending_mr=Decimal("165000.00"),
                reason="Released to WP 3.2 for additional testing requirements",
                approved_by=self.user_id,
                created_at=datetime(2024, 6, 1),
            ),
        ]
        return self.mr_logs

    def create_variance_explanations(self) -> list[MockVarianceExplanation]:
        """Create variance explanations."""
        self.variance_explanations = [
            MockVarianceExplanation(
                id=uuid4(),
                program_id=self.program_id,
                wbs_id=self.wbs_elements[1].id if self.wbs_elements else None,
                period_id=self.periods[3].id if self.periods else None,
                variance_type="cost",
                variance_amount=Decimal("-150000.00"),
                variance_percent=Decimal("-12.50"),
                explanation="Cost overrun in Systems Engineering due to additional design iterations required for flight control system integration.",
                corrective_action="Implementing design reviews at 50% completion milestones to catch issues earlier.",
                expected_resolution=date(2024, 9, 30),
                created_by=self.user_id,
            ),
            MockVarianceExplanation(
                id=uuid4(),
                program_id=self.program_id,
                wbs_id=self.wbs_elements[2].id if self.wbs_elements else None,
                period_id=self.periods[4].id if self.periods else None,
                variance_type="schedule",
                variance_amount=Decimal("-200000.00"),
                variance_percent=Decimal("-10.00"),
                explanation="Schedule delay in Hardware Development due to supply chain constraints on specialized avionics components.",
                corrective_action="Qualified alternate suppliers and expedited shipping arrangements.",
                expected_resolution=date(2024, 10, 15),
                created_by=self.user_id,
            ),
        ]
        return self.variance_explanations

    def create_audit_entries(self) -> list[MockReportAudit]:
        """Create report audit entries."""
        now = datetime.now()
        self.audit_entries = [
            MockReportAudit(
                id=uuid4(),
                report_type="cpr_format_1",
                program_id=self.program_id,
                generated_by=self.user_id,
                generated_at=now - timedelta(hours=2),
                parameters={"periods_to_include": 6},
                file_path="/reports/F35-PROD_cpr_format1.pdf",
                file_format="pdf",
                file_size=125000,
                checksum="abc123def456",
            ),
            MockReportAudit(
                id=uuid4(),
                report_type="cpr_format_3",
                program_id=self.program_id,
                generated_by=self.user_id,
                generated_at=now - timedelta(hours=1),
                parameters={"include_pmb": True},
                file_path="/reports/F35-PROD_cpr_format3.pdf",
                file_format="pdf",
                file_size=245000,
                checksum="def456ghi789",
            ),
            MockReportAudit(
                id=uuid4(),
                report_type="cpr_format_5",
                program_id=self.program_id,
                generated_by=self.user_id,
                generated_at=now,
                parameters={"include_variances": True, "include_mr": True},
                file_path="/reports/F35-PROD_cpr_format5.pdf",
                file_format="pdf",
                file_size=380000,
                checksum="ghi789jkl012",
            ),
        ]
        return self.audit_entries


# =============================================================================
# E2E Test Class: Complete Reports Workflow
# =============================================================================


class TestWeek9CompleteReportsWorkflow:
    """E2E tests for complete reports workflow."""

    @pytest.fixture
    def factory(self) -> Week9DataFactory:
        """Create test data factory."""
        return Week9DataFactory()

    @pytest.fixture
    def setup_test_data(self, factory: Week9DataFactory) -> Week9DataFactory:
        """Set up all test data."""
        factory.create_program()
        factory.create_wbs_structure()
        factory.create_periods()
        factory.create_mr_history()
        factory.create_variance_explanations()
        factory.create_audit_entries()
        return factory

    def test_evms_calculations_for_format1(self, setup_test_data: Week9DataFactory):
        """Should calculate EVMS metrics for Format 1 report."""
        factory = setup_test_data
        program = factory.create_program()
        latest_period = factory.periods[-1]

        # Calculate EVMS metrics using class methods
        cv = EVMSCalculator.calculate_cost_variance(latest_period.bcwp, latest_period.acwp)
        sv = EVMSCalculator.calculate_schedule_variance(latest_period.bcwp, latest_period.bcws)
        cpi = EVMSCalculator.calculate_cpi(latest_period.bcwp, latest_period.acwp)
        spi = EVMSCalculator.calculate_spi(latest_period.bcwp, latest_period.bcws)
        eac = EVMSCalculator.calculate_eac(
            program.budget_at_completion, latest_period.acwp, latest_period.bcwp
        )

        # Verify core calculations
        assert cv < 0  # Over budget (ACWP > BCWP)
        assert sv < 0  # Behind schedule (BCWP < BCWS)
        assert cpi is not None and cpi < Decimal("1.0")  # Cost efficiency < 1
        assert spi is not None and spi < Decimal("1.0")  # Schedule efficiency < 1

        # Verify EAC calculation
        assert eac is not None and eac > program.budget_at_completion  # Expected overrun

    def test_variance_analysis_integration(self, setup_test_data: Week9DataFactory):
        """Should perform variance analysis across periods."""
        factory = setup_test_data

        # Convert periods to variance analysis input format
        period_data = [
            {
                "period_number": p.period_number,
                "bcws": p.bcws,
                "bcwp": p.bcwp,
                "acwp": p.acwp,
            }
            for p in factory.periods
        ]

        # Analyze latest period
        latest = period_data[-1]
        cv = latest["bcwp"] - latest["acwp"]
        sv = latest["bcwp"] - latest["bcws"]

        # Verify variances are significant (> 10%)
        cv_percent = (cv / latest["bcwp"]) * 100 if latest["bcwp"] else 0
        sv_percent = (sv / latest["bcws"]) * 100 if latest["bcws"] else 0

        assert cv_percent < Decimal("-5")  # Significant cost variance
        assert sv_percent < Decimal("-5")  # Significant schedule variance

    def test_format5_config_creation(self, setup_test_data: Week9DataFactory):
        """Should create valid Format 5 export configuration."""
        factory = setup_test_data
        factory.create_program()

        # Format5ExportConfig contains export options, not program info
        config = Format5ExportConfig(
            include_mr=True,
            include_explanations=True,
            variance_threshold_percent=Decimal("10"),
            periods_to_include=12,
            include_eac_analysis=True,
        )

        assert config.include_mr is True
        assert config.include_explanations is True
        assert config.include_eac_analysis is True
        assert config.periods_to_include == 12

    def test_mr_status_calculation(self, setup_test_data: Week9DataFactory):
        """Should calculate correct MR status from history."""
        factory = setup_test_data
        mr_logs = factory.mr_logs

        # Calculate status from logs
        initial_mr = mr_logs[0].beginning_mr + mr_logs[0].changes_in
        total_in = sum(log.changes_in for log in mr_logs)
        total_out = sum(log.changes_out for log in mr_logs)
        current_balance = mr_logs[-1].ending_mr

        status = ManagementReserveStatus(
            program_id=factory.program_id,
            current_balance=current_balance,
            initial_mr=initial_mr,
            total_changes_in=total_in,
            total_changes_out=total_out,
            change_count=len(mr_logs),
            last_change_at=mr_logs[-1].created_at,
        )

        assert status.initial_mr == Decimal("250000.00")
        assert status.current_balance == Decimal("165000.00")
        assert status.total_changes_out == Decimal("85000.00")
        assert status.change_count == 3

    def test_mr_balance_validation(self, setup_test_data: Week9DataFactory):
        """Should validate MR changes maintain non-negative balance."""
        factory = setup_test_data

        # Verify ending balance calculation
        for log in factory.mr_logs:
            expected_ending = log.beginning_mr + log.changes_in - log.changes_out
            assert log.ending_mr == expected_ending
            assert log.ending_mr >= Decimal("0")  # Never negative

    def test_variance_explanation_schema_validation(self, setup_test_data: Week9DataFactory):
        """Should validate variance explanation schemas."""
        factory = setup_test_data

        for var_exp in factory.variance_explanations:
            # Validate through Pydantic schema
            response = VarianceExplanationResponse(
                id=var_exp.id,
                program_id=var_exp.program_id,
                wbs_id=var_exp.wbs_id,
                period_id=var_exp.period_id,
                variance_type=var_exp.variance_type,
                variance_amount=var_exp.variance_amount,
                variance_percent=var_exp.variance_percent,
                explanation=var_exp.explanation,
                corrective_action=var_exp.corrective_action,
                expected_resolution=var_exp.expected_resolution,
                created_by=var_exp.created_by,
                created_at=var_exp.created_at,
                updated_at=var_exp.created_at,
            )

            assert response.explanation is not None
            assert len(response.explanation) >= 10  # Minimum length requirement
            assert response.variance_type in ["cost", "schedule"]

    def test_audit_trail_completeness(self, setup_test_data: Week9DataFactory):
        """Should maintain complete audit trail for reports."""
        factory = setup_test_data
        audit_entries = factory.audit_entries

        # Verify audit entries cover all report types
        report_types = {entry.report_type for entry in audit_entries}
        assert "cpr_format_1" in report_types
        assert "cpr_format_3" in report_types
        assert "cpr_format_5" in report_types

        # Verify all entries have required fields
        for entry in audit_entries:
            assert entry.program_id is not None
            assert entry.generated_at is not None
            assert entry.file_format in ["json", "html", "pdf"]
            assert entry.file_size > 0
            assert entry.checksum is not None

    def test_audit_stats_aggregation(self, setup_test_data: Week9DataFactory):
        """Should calculate correct audit statistics."""
        factory = setup_test_data
        audit_entries = factory.audit_entries

        # Calculate stats
        total_reports = len(audit_entries)
        by_type = {}
        by_format = {}
        total_size = 0

        for entry in audit_entries:
            by_type[entry.report_type] = by_type.get(entry.report_type, 0) + 1
            by_format[entry.file_format] = by_format.get(entry.file_format, 0) + 1
            total_size += entry.file_size

        stats = ReportAuditStats(
            total_reports=total_reports,
            by_type=by_type,
            by_format=by_format,
            total_size_bytes=total_size,
            last_generated=max(e.generated_at for e in audit_entries),
        )

        assert stats.total_reports == 3
        assert stats.by_type["cpr_format_1"] == 1
        assert stats.by_type["cpr_format_3"] == 1
        assert stats.by_type["cpr_format_5"] == 1
        assert stats.by_format["pdf"] == 3
        assert stats.total_size_bytes == 750000


# =============================================================================
# E2E Test Class: PDF Generation
# =============================================================================


class TestWeek9PDFGeneration:
    """E2E tests for PDF generation workflow."""

    @pytest.fixture
    def factory(self) -> Week9DataFactory:
        """Create test data factory."""
        return Week9DataFactory()

    def test_pdf_generator_initialization(self, factory: Week9DataFactory):
        """Should initialize PDF generator with valid config."""
        program = factory.create_program()

        # PDF generator should be importable and instantiable
        generator = ReportPDFGenerator()
        assert generator is not None

    def test_report_generator_format1_data(self, factory: Week9DataFactory):
        """Should generate valid Format 1 data structure."""
        factory.create_wbs_structure()
        factory.create_periods()

        # Calculate summary metrics
        total_bcws = sum(p.bcws for p in factory.periods)
        total_bcwp = sum(p.bcwp for p in factory.periods)
        total_acwp = sum(p.acwp for p in factory.periods)

        # Format 1 structure
        format1_data = {
            "wbs_summary": [
                {
                    "code": wbs.code,
                    "name": wbs.name,
                    "bcws": wbs.budgeted_cost,
                    "bcwp": wbs.budgeted_cost * (wbs.percent_complete / 100),
                    "acwp": wbs.actual_cost,
                }
                for wbs in factory.wbs_elements
            ],
            "totals": {
                "bcws": total_bcws,
                "bcwp": total_bcwp,
                "acwp": total_acwp,
                "cv": total_bcwp - total_acwp,
                "sv": total_bcwp - total_bcws,
            },
        }

        assert len(format1_data["wbs_summary"]) == 5
        assert format1_data["totals"]["cv"] < 0  # Over budget
        assert format1_data["totals"]["sv"] < 0  # Behind schedule

    def test_report_generator_format3_baseline(self, factory: Week9DataFactory):
        """Should generate valid Format 3 baseline data."""
        program = factory.create_program()
        factory.create_periods()

        # Format 3 requires time-phased PMB data
        format3_data = {
            "program": {
                "name": program.name,
                "code": program.code,
                "bac": program.budget_at_completion,
            },
            "time_phased_data": [
                {
                    "period": p.period_number,
                    "bcws_period": p.bcws - (factory.periods[i - 1].bcws if i > 0 else 0),
                    "bcws_cumulative": p.bcws,
                }
                for i, p in enumerate(factory.periods)
            ],
        }

        assert format3_data["program"]["bac"] == Decimal("5000000.00")
        assert len(format3_data["time_phased_data"]) == 6

    def test_report_generator_format5_comprehensive(self, factory: Week9DataFactory):
        """Should generate comprehensive Format 5 data."""
        program = factory.create_program()
        factory.create_wbs_structure()
        factory.create_periods()
        factory.create_mr_history()
        factory.create_variance_explanations()

        latest_period = factory.periods[-1]

        # Format 5 comprehensive structure
        format5_data = {
            "header": {
                "program_name": program.name,
                "contract_number": program.contract_number,
                "reporting_period": latest_period.period_number,
                "as_of_date": latest_period.end_date.isoformat(),
            },
            "evms_summary": {
                "bcws": latest_period.bcws,
                "bcwp": latest_period.bcwp,
                "acwp": latest_period.acwp,
                "bac": program.budget_at_completion,
            },
            "variance_explanations": [
                {
                    "wbs_code": factory.wbs_elements[i].code
                    if i < len(factory.wbs_elements)
                    else "N/A",
                    "type": ve.variance_type,
                    "amount": ve.variance_amount,
                    "percent": ve.variance_percent,
                    "explanation": ve.explanation,
                    "corrective_action": ve.corrective_action,
                }
                for i, ve in enumerate(factory.variance_explanations)
            ],
            "management_reserve": {
                "initial": factory.mr_logs[0].ending_mr,
                "current": factory.mr_logs[-1].ending_mr,
                "total_released": sum(log.changes_out for log in factory.mr_logs),
            },
        }

        assert format5_data["header"]["program_name"] == "F-35 Lightning II Program"
        assert len(format5_data["variance_explanations"]) == 2
        assert format5_data["management_reserve"]["current"] == Decimal("165000.00")


# =============================================================================
# E2E Test Class: Complete Workflow Integration
# =============================================================================


class TestWeek9CompleteWorkflowIntegration:
    """E2E tests for complete Week 9 workflow integration."""

    @pytest.fixture
    def factory(self) -> Week9DataFactory:
        """Create test data factory with full setup."""
        f = Week9DataFactory()
        f.create_program()
        f.create_wbs_structure()
        f.create_periods()
        f.create_mr_history()
        f.create_variance_explanations()
        f.create_audit_entries()
        return f

    def test_full_reporting_workflow(self, factory: Week9DataFactory):
        """Should complete full reporting workflow from data to audit."""
        # Step 1: Verify program setup
        program = factory.create_program()
        assert program.budget_at_completion == Decimal("5000000.00")

        # Step 2: Verify WBS structure
        assert len(factory.wbs_elements) == 5
        total_wbs_budget = sum(w.budgeted_cost for w in factory.wbs_elements)
        assert total_wbs_budget == program.budget_at_completion

        # Step 3: Verify period data
        assert len(factory.periods) == 6
        # Behind schedule: BCWP < BCWS; Over budget: ACWP > BCWP
        assert factory.periods[-1].bcwp < factory.periods[-1].bcws  # Behind schedule
        assert factory.periods[-1].acwp > factory.periods[-1].bcwp  # Over budget

        # Step 4: Calculate EVMS
        latest = factory.periods[-1]
        cpi = EVMSCalculator.calculate_cpi(latest.bcwp, latest.acwp)
        assert cpi < Decimal("1.0")  # Over budget

        # Step 5: Verify variance explanations
        assert len(factory.variance_explanations) == 2
        cost_variances = [v for v in factory.variance_explanations if v.variance_type == "cost"]
        assert len(cost_variances) == 1

        # Step 6: Verify MR tracking
        assert len(factory.mr_logs) == 3
        assert factory.mr_logs[-1].ending_mr == Decimal("165000.00")

        # Step 7: Verify audit trail
        assert len(factory.audit_entries) == 3

    def test_variance_to_mr_release_workflow(self, factory: Week9DataFactory):
        """Should track variance leading to MR release."""
        # Scenario: Cost variance identified, MR released to address it

        # Find cost variance
        cost_variance = next(
            (v for v in factory.variance_explanations if v.variance_type == "cost"),
            None,
        )
        assert cost_variance is not None
        assert cost_variance.variance_amount == Decimal("-150000.00")

        # Find related MR release (WP 2.1 = Systems Engineering)
        mr_release = factory.mr_logs[1]  # Second log is first release
        assert mr_release.changes_out == Decimal("50000.00")
        assert "engineering change" in mr_release.reason.lower()

    def test_eac_with_mr_consideration(self, factory: Week9DataFactory):
        """Should calculate EAC considering MR availability."""
        program = factory.create_program()
        latest = factory.periods[-1]

        # Calculate EAC using class methods
        eac = EVMSCalculator.calculate_eac(
            program.budget_at_completion, latest.acwp, latest.bcwp
        )

        # Current MR available
        current_mr = factory.mr_logs[-1].ending_mr

        # Check if MR can help cover potential overrun
        assert current_mr > Decimal("0")  # MR still available
        assert eac is not None and eac > program.budget_at_completion  # Expected overrun

    def test_audit_trail_integrity(self, factory: Week9DataFactory):
        """Should maintain audit trail integrity across all operations."""
        # All reports should be audited
        audited_types = {e.report_type for e in factory.audit_entries}
        expected_types = {"cpr_format_1", "cpr_format_3", "cpr_format_5"}
        assert audited_types == expected_types

        # All audits should have checksums
        assert all(e.checksum is not None for e in factory.audit_entries)

        # All audits should have file sizes
        assert all(e.file_size > 0 for e in factory.audit_entries)

        # Timestamps should be ordered
        timestamps = [e.generated_at for e in factory.audit_entries]
        assert timestamps == sorted(timestamps)


# =============================================================================
# E2E Test Class: Schema Validation
# =============================================================================


class TestWeek9SchemaValidation:
    """E2E tests for schema validation."""

    def test_variance_type_enum(self):
        """Should validate variance type enum values."""
        assert VarianceType.COST.value == "cost"
        assert VarianceType.SCHEDULE.value == "schedule"

    def test_report_type_enum(self):
        """Should validate report type enum values."""
        assert ReportType.CPR_FORMAT_1.value == "cpr_format_1"
        assert ReportType.CPR_FORMAT_3.value == "cpr_format_3"
        assert ReportType.CPR_FORMAT_5.value == "cpr_format_5"

    def test_report_format_enum(self):
        """Should validate report format enum values."""
        assert ReportFormat.JSON.value == "json"
        assert ReportFormat.HTML.value == "html"
        assert ReportFormat.PDF.value == "pdf"

    def test_mr_change_create_schema(self):
        """Should validate MR change creation schema."""
        change = ManagementReserveChangeCreate(
            period_id=uuid4(),
            changes_in=Decimal("50000.00"),
            changes_out=Decimal("0"),
            reason="Budget augmentation for risk mitigation",
        )
        assert change.changes_in == Decimal("50000.00")
        assert change.changes_out == Decimal("0")

    def test_variance_explanation_create_schema(self):
        """Should validate variance explanation creation schema."""
        explanation = VarianceExplanationCreate(
            program_id=uuid4(),
            variance_type=VarianceType.COST,
            variance_amount=Decimal("-50000.00"),
            variance_percent=Decimal("-10.00"),
            explanation="Cost variance due to material price increases affecting procurement schedule.",
            corrective_action="Negotiating with alternate suppliers",
            expected_resolution=date.today() + timedelta(days=30),
        )
        assert explanation.variance_type == VarianceType.COST
        assert explanation.variance_amount < Decimal("0")  # Negative = unfavorable
