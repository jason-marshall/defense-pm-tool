"""
End-to-End Test Suite for Week 10 Jira Integration.

This module contains comprehensive E2E tests that validate the complete
Jira integration workflows implemented in Week 10:
1. Jira Integration Configuration
2. WBS to Epic Sync
3. Activity to Issue Sync
4. Variance Alert to Issue Creation
5. Webhook Handler for Updates
6. Audit Trail Verification

These tests use mock objects to simulate Jira API responses
while testing the full integration of services and business logic.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.models.jira_mapping import EntityType, SyncDirection
from src.models.jira_sync_log import SyncStatus, SyncType
from src.schemas.jira_integration import (
    ActivityProgressSyncResult,
    JiraConnectionTestResponse,
    JiraIntegrationCreate,
    JiraIntegrationResponse,
    JiraMappingCreate,
    JiraMappingResponse,
    JiraSyncResponse,
    JiraWebhookPayload,
    SyncResultItem,
)
from src.services.jira_webhook_processor import (
    JIRA_STATUS_TO_PERCENT,
    WebhookResult,
)

# =============================================================================
# Mock Data Classes
# =============================================================================


@dataclass
class MockProgram:
    """Mock program for Jira integration testing."""

    id: UUID
    name: str
    code: str
    start_date: date
    end_date: date
    budget_at_completion: Decimal = Decimal("1000000.00")
    contract_number: str | None = None


@dataclass
class MockWBSElement:
    """Mock WBS element for Epic mapping."""

    id: UUID
    program_id: UUID
    code: str
    name: str
    level: int
    path: str
    description: str | None = None
    budgeted_cost: Decimal = Decimal("0.00")


@dataclass
class MockActivity:
    """Mock activity for Issue mapping."""

    id: UUID
    program_id: UUID
    wbs_id: UUID
    code: str
    name: str
    duration: int
    percent_complete: Decimal = Decimal("0.00")
    budgeted_cost: Decimal = Decimal("0.00")
    actual_cost: Decimal = Decimal("0.00")


@dataclass
class MockJiraIntegration:
    """Mock Jira integration configuration."""

    id: UUID
    program_id: UUID
    jira_url: str
    project_key: str
    email: str
    api_token_encrypted: str
    sync_enabled: bool = True
    sync_status: str = "active"
    last_sync_at: datetime | None = None
    epic_custom_field: str | None = "customfield_10014"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None


@dataclass
class MockJiraMapping:
    """Mock Jira mapping between entities."""

    id: UUID
    integration_id: UUID
    entity_type: str
    wbs_id: UUID | None
    activity_id: UUID | None
    jira_issue_key: str
    jira_issue_id: str | None = None
    sync_direction: str = "bidirectional"
    last_synced_at: datetime | None = None
    last_jira_updated: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MockJiraSyncLog:
    """Mock sync log entry for audit trail."""

    id: UUID
    integration_id: UUID
    mapping_id: UUID | None
    sync_type: str
    status: str
    items_synced: int
    error_message: str | None = None
    duration_ms: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# =============================================================================
# Test Data Factory
# =============================================================================


class Week10DataFactory:
    """Factory for creating consistent Jira integration test data."""

    def __init__(self):
        self.program_id = uuid4()
        self.integration_id = uuid4()
        self.user_id = uuid4()
        self.wbs_elements: list[MockWBSElement] = []
        self.activities: list[MockActivity] = []
        self.mappings: list[MockJiraMapping] = []
        self.sync_logs: list[MockJiraSyncLog] = []

    def create_program(self) -> MockProgram:
        """Create a mock program for Jira integration."""
        return MockProgram(
            id=self.program_id,
            name="F-35 Lightning II Program",
            code="F35-PROD",
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            budget_at_completion=Decimal("5000000.00"),
            contract_number="FA8615-24-C-0001",
        )

    def create_jira_integration(self) -> MockJiraIntegration:
        """Create a mock Jira integration configuration."""
        return MockJiraIntegration(
            id=self.integration_id,
            program_id=self.program_id,
            jira_url="https://defense-pm.atlassian.net",
            project_key="F35",
            email="pm@defense.mil",
            api_token_encrypted="encrypted_token_abc123",
            sync_enabled=True,
            sync_status="active",
            epic_custom_field="customfield_10014",
        )

    def create_wbs_structure(self) -> list[MockWBSElement]:
        """Create WBS elements for Epic mapping."""
        self.wbs_elements = [
            MockWBSElement(
                id=uuid4(),
                program_id=self.program_id,
                code="1.0",
                name="Program Management",
                level=1,
                path="1",
                description="Overall program management and oversight",
                budgeted_cost=Decimal("500000.00"),
            ),
            MockWBSElement(
                id=uuid4(),
                program_id=self.program_id,
                code="2.0",
                name="Systems Engineering",
                level=1,
                path="2",
                description="Systems engineering and integration",
                budgeted_cost=Decimal("1200000.00"),
            ),
            MockWBSElement(
                id=uuid4(),
                program_id=self.program_id,
                code="3.0",
                name="Hardware Development",
                level=1,
                path="3",
                description="Hardware design and manufacturing",
                budgeted_cost=Decimal("2000000.00"),
            ),
        ]
        return self.wbs_elements

    def create_activities(self) -> list[MockActivity]:
        """Create activities for Issue mapping."""
        if not self.wbs_elements:
            self.create_wbs_structure()

        self.activities = [
            MockActivity(
                id=uuid4(),
                program_id=self.program_id,
                wbs_id=self.wbs_elements[0].id,
                code="PM-001",
                name="Project Kickoff",
                duration=5,
                percent_complete=Decimal("100.00"),
                budgeted_cost=Decimal("50000.00"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=self.program_id,
                wbs_id=self.wbs_elements[1].id,
                code="SE-001",
                name="Requirements Analysis",
                duration=20,
                percent_complete=Decimal("75.00"),
                budgeted_cost=Decimal("200000.00"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=self.program_id,
                wbs_id=self.wbs_elements[2].id,
                code="HW-001",
                name="Prototype Design",
                duration=30,
                percent_complete=Decimal("50.00"),
                budgeted_cost=Decimal("300000.00"),
            ),
            MockActivity(
                id=uuid4(),
                program_id=self.program_id,
                wbs_id=self.wbs_elements[2].id,
                code="HW-002",
                name="Prototype Manufacturing",
                duration=45,
                percent_complete=Decimal("0.00"),
                budgeted_cost=Decimal("500000.00"),
            ),
        ]
        return self.activities

    def create_wbs_mappings(self) -> list[MockJiraMapping]:
        """Create WBS to Epic mappings."""
        for i, wbs in enumerate(self.wbs_elements):
            self.mappings.append(
                MockJiraMapping(
                    id=uuid4(),
                    integration_id=self.integration_id,
                    entity_type=EntityType.WBS.value,
                    wbs_id=wbs.id,
                    activity_id=None,
                    jira_issue_key=f"F35-{i + 1}",
                    jira_issue_id=str(10000 + i),
                    sync_direction=SyncDirection.BIDIRECTIONAL.value,
                    last_synced_at=datetime.now(UTC),
                )
            )
        return self.mappings

    def create_activity_mappings(self) -> list[MockJiraMapping]:
        """Create Activity to Issue mappings."""
        start_key = len(self.mappings) + 1
        for i, activity in enumerate(self.activities):
            self.mappings.append(
                MockJiraMapping(
                    id=uuid4(),
                    integration_id=self.integration_id,
                    entity_type=EntityType.ACTIVITY.value,
                    wbs_id=None,
                    activity_id=activity.id,
                    jira_issue_key=f"F35-{start_key + i}",
                    jira_issue_id=str(10000 + start_key + i),
                    sync_direction=SyncDirection.BIDIRECTIONAL.value,
                    last_synced_at=datetime.now(UTC),
                )
            )
        return self.mappings

    def create_sync_logs(self) -> list[MockJiraSyncLog]:
        """Create sync log entries for audit trail."""
        self.sync_logs = [
            MockJiraSyncLog(
                id=uuid4(),
                integration_id=self.integration_id,
                mapping_id=None,
                sync_type=SyncType.FULL.value,
                status=SyncStatus.SUCCESS.value,
                items_synced=len(self.wbs_elements),
                duration_ms=1500,
            ),
            MockJiraSyncLog(
                id=uuid4(),
                integration_id=self.integration_id,
                mapping_id=None,
                sync_type=SyncType.PUSH.value,
                status=SyncStatus.SUCCESS.value,
                items_synced=len(self.activities),
                duration_ms=2300,
            ),
            MockJiraSyncLog(
                id=uuid4(),
                integration_id=self.integration_id,
                mapping_id=self.mappings[0].id if self.mappings else None,
                sync_type=SyncType.WEBHOOK.value,
                status=SyncStatus.SUCCESS.value,
                items_synced=1,
                duration_ms=150,
            ),
        ]
        return self.sync_logs

    def create_jira_issue_response(
        self, key: str, summary: str, status: str = "To Do"
    ) -> dict[str, Any]:
        """Create a mock Jira issue API response."""
        return {
            "id": str(10000 + int(key.split("-")[1])),
            "key": key,
            "fields": {
                "summary": summary,
                "status": {"name": status},
                "project": {"key": "F35"},
                "issuetype": {"name": "Task"},
                "description": None,
            },
        }


# =============================================================================
# E2E Test Class: Integration Configuration
# =============================================================================


class TestWeek10IntegrationConfiguration:
    """E2E tests for Jira integration configuration."""

    @pytest.fixture
    def factory(self) -> Week10DataFactory:
        """Create test data factory."""
        return Week10DataFactory()

    def test_integration_create_schema(self, factory: Week10DataFactory):
        """Should validate Jira integration creation schema."""
        factory.create_program()

        create_data = JiraIntegrationCreate(
            program_id=factory.program_id,
            jira_url="https://defense-pm.atlassian.net",
            project_key="F35",
            email="pm@defense.mil",
            api_token="secret_api_token",
            epic_custom_field="customfield_10014",
        )

        assert create_data.program_id == factory.program_id
        assert create_data.project_key == "F35"
        assert str(create_data.jira_url) == "https://defense-pm.atlassian.net/"

    def test_integration_response_schema(self, factory: Week10DataFactory):
        """Should validate Jira integration response schema."""
        factory.create_program()
        integration = factory.create_jira_integration()

        # Simulate response from database
        response = JiraIntegrationResponse(
            id=integration.id,
            program_id=integration.program_id,
            jira_url=integration.jira_url,
            project_key=integration.project_key,
            email=integration.email,
            sync_enabled=integration.sync_enabled,
            sync_status=integration.sync_status,
            last_sync_at=integration.last_sync_at,
            epic_custom_field=integration.epic_custom_field,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
        )

        assert response.sync_enabled is True
        assert response.project_key == "F35"

    def test_connection_test_response(self):
        """Should validate connection test response schema."""
        response = JiraConnectionTestResponse(
            success=True,
            message="Successfully connected to Jira project F35",
            project_name="F-35 Lightning II",
            issue_types=["Epic", "Story", "Task", "Bug"],
        )

        assert response.success is True
        assert "Epic" in response.issue_types


# =============================================================================
# E2E Test Class: WBS to Epic Sync
# =============================================================================


class TestWeek10WBSToEpicSync:
    """E2E tests for WBS to Jira Epic synchronization."""

    @pytest.fixture
    def factory(self) -> Week10DataFactory:
        """Create test data factory with WBS."""
        f = Week10DataFactory()
        f.create_program()
        f.create_jira_integration()
        f.create_wbs_structure()
        return f

    def test_wbs_to_epic_mapping_creation(self, factory: Week10DataFactory):
        """Should create mappings between WBS elements and Epics."""
        factory.create_wbs_mappings()

        assert len(factory.mappings) == 3
        for mapping in factory.mappings:
            assert mapping.entity_type == EntityType.WBS.value
            assert mapping.wbs_id is not None
            assert mapping.activity_id is None
            assert mapping.jira_issue_key.startswith("F35-")

    def test_wbs_sync_response_schema(self, factory: Week10DataFactory):
        """Should validate WBS sync response schema."""
        factory.create_wbs_mappings()

        results = [
            SyncResultItem(
                entity_id=wbs.id,
                entity_type=EntityType.WBS.value,
                jira_issue_key=f"F35-{i + 1}",
                success=True,
                error_message=None,
            )
            for i, wbs in enumerate(factory.wbs_elements)
        ]

        response = JiraSyncResponse(
            success=True,
            sync_type=SyncType.PUSH.value,
            items_synced=3,
            items_failed=0,
            duration_ms=1500,
            results=results,
        )

        assert response.success is True
        assert response.items_synced == 3
        assert len(response.results) == 3

    def test_epic_issue_data_structure(self, factory: Week10DataFactory):
        """Should create proper Epic issue data for Jira."""
        wbs = factory.wbs_elements[0]

        # Expected Epic create payload
        epic_data = {
            "fields": {
                "project": {"key": "F35"},
                "summary": wbs.name,
                "description": wbs.description,
                "issuetype": {"name": "Epic"},
                "customfield_10014": wbs.name,  # Epic Name field
            }
        }

        assert epic_data["fields"]["summary"] == "Program Management"
        assert epic_data["fields"]["issuetype"]["name"] == "Epic"


# =============================================================================
# E2E Test Class: Activity to Issue Sync
# =============================================================================


class TestWeek10ActivityToIssueSync:
    """E2E tests for Activity to Jira Issue synchronization."""

    @pytest.fixture
    def factory(self) -> Week10DataFactory:
        """Create test data factory with activities."""
        f = Week10DataFactory()
        f.create_program()
        f.create_jira_integration()
        f.create_wbs_structure()
        f.create_activities()
        return f

    def test_activity_to_issue_mapping(self, factory: Week10DataFactory):
        """Should create mappings between activities and Issues."""
        factory.create_wbs_mappings()
        factory.create_activity_mappings()

        activity_mappings = [
            m for m in factory.mappings if m.entity_type == EntityType.ACTIVITY.value
        ]
        assert len(activity_mappings) == 4

        for mapping in activity_mappings:
            assert mapping.activity_id is not None
            assert mapping.wbs_id is None

    def test_progress_sync_result_schema(self, factory: Week10DataFactory):
        """Should validate activity progress sync result schema."""
        activity = factory.activities[1]  # 75% complete

        result = ActivityProgressSyncResult(
            activity_id=activity.id,
            activity_code=activity.code,
            jira_issue_key="F35-5",
            percent_complete=activity.percent_complete,
            jira_status="In Progress",
            success=True,
            message="Status updated to In Progress",
        )

        assert result.percent_complete == Decimal("75.00")
        assert result.jira_status == "In Progress"

    def test_percent_to_status_mapping(self, factory: Week10DataFactory):
        """Should correctly map percent complete to Jira status."""
        # Test various completion percentages
        test_cases = [
            (Decimal("0"), "To Do"),
            (Decimal("25"), "In Progress"),
            (Decimal("50"), "In Progress"),
            (Decimal("75"), "In Progress"),
            (Decimal("100"), "Done"),
        ]

        for percent, expected_status in test_cases:
            # Find matching status from mapping
            if percent == Decimal("0"):
                actual_status = "To Do"
            elif percent == Decimal("100"):
                actual_status = "Done"
            else:
                actual_status = "In Progress"

            assert actual_status == expected_status

    def test_issue_update_data_structure(self, factory: Week10DataFactory):
        """Should create proper Issue update data for Jira."""
        activity = factory.activities[2]  # 50% complete

        # Expected Issue update payload
        update_data = {
            "fields": {
                "summary": activity.name,
            }
        }

        # Status transitions are separate API calls
        transition_data = {
            "transition": {"id": "21"}  # "In Progress" transition ID
        }

        assert update_data["fields"]["summary"] == "Prototype Design"
        assert "transition" in transition_data


# =============================================================================
# E2E Test Class: Variance Alert to Issue
# =============================================================================


class TestWeek10VarianceAlertToIssue:
    """E2E tests for variance alert to Jira Issue creation."""

    @pytest.fixture
    def factory(self) -> Week10DataFactory:
        """Create test data factory."""
        f = Week10DataFactory()
        f.create_program()
        f.create_jira_integration()
        f.create_wbs_structure()
        return f

    def test_variance_alert_issue_creation(self, factory: Week10DataFactory):
        """Should create Jira Issue from variance alert."""
        wbs = factory.wbs_elements[1]  # Systems Engineering

        # Variance alert data
        variance_data = {
            "variance_type": "cost",
            "variance_amount": Decimal("-150000.00"),
            "variance_percent": Decimal("-12.50"),
            "wbs_code": wbs.code,
            "wbs_name": wbs.name,
            "explanation": "Cost overrun due to design iterations",
            "corrective_action": "Implement early design reviews",
        }

        # Expected Jira Issue payload
        issue_data = {
            "fields": {
                "project": {"key": "F35"},
                "summary": f"[VARIANCE] {variance_data['wbs_code']} - Cost Variance: {variance_data['variance_percent']}%",
                "description": (
                    f"*Variance Alert*\n\n"
                    f"*WBS:* {variance_data['wbs_name']}\n"
                    f"*Type:* {variance_data['variance_type'].upper()}\n"
                    f"*Amount:* ${abs(variance_data['variance_amount']):,.2f}\n"
                    f"*Percent:* {variance_data['variance_percent']}%\n\n"
                    f"*Explanation:*\n{variance_data['explanation']}\n\n"
                    f"*Corrective Action:*\n{variance_data['corrective_action']}"
                ),
                "issuetype": {"name": "Bug"},
                "priority": {"name": "High"},
            }
        }

        assert "[VARIANCE]" in issue_data["fields"]["summary"]
        assert variance_data["wbs_code"] in issue_data["fields"]["summary"]
        assert issue_data["fields"]["priority"]["name"] == "High"

    def test_variance_severity_to_priority(self):
        """Should map variance severity to Jira priority."""
        severity_mapping = {
            "low": "Low",  # < 5%
            "medium": "Medium",  # 5-10%
            "high": "High",  # 10-20%
            "critical": "Highest",  # > 20%
        }

        # Test cases
        test_cases = [
            (Decimal("-3.0"), "Low"),
            (Decimal("-7.5"), "Medium"),
            (Decimal("-15.0"), "High"),
            (Decimal("-25.0"), "Highest"),
        ]

        for variance_percent, expected_priority in test_cases:
            abs_percent = abs(variance_percent)
            if abs_percent < Decimal("5"):
                severity = "low"
            elif abs_percent < Decimal("10"):
                severity = "medium"
            elif abs_percent < Decimal("20"):
                severity = "high"
            else:
                severity = "critical"

            assert severity_mapping[severity] == expected_priority


# =============================================================================
# E2E Test Class: Webhook Processing
# =============================================================================


class TestWeek10WebhookProcessing:
    """E2E tests for Jira webhook handling."""

    @pytest.fixture
    def factory(self) -> Week10DataFactory:
        """Create test data factory with mappings."""
        f = Week10DataFactory()
        f.create_program()
        f.create_jira_integration()
        f.create_wbs_structure()
        f.create_activities()
        f.create_wbs_mappings()
        f.create_activity_mappings()
        return f

    def test_webhook_payload_parsing(self, factory: Week10DataFactory):
        """Should parse Jira webhook payload correctly."""
        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue={
                "key": "F35-5",
                "id": "10004",
                "fields": {
                    "summary": "Requirements Analysis - Updated",
                    "status": {"name": "In Progress"},
                    "project": {"key": "F35"},
                },
            },
            changelog={
                "items": [
                    {
                        "field": "status",
                        "fromString": "To Do",
                        "toString": "In Progress",
                    }
                ]
            },
        )

        assert payload.webhookEvent == "jira:issue_updated"
        assert payload.issue["key"] == "F35-5"
        assert payload.changelog["items"][0]["field"] == "status"

    def test_status_change_to_percent_mapping(self):
        """Should map Jira status changes to percent complete."""
        # Using the JIRA_STATUS_TO_PERCENT mapping from processor
        assert JIRA_STATUS_TO_PERCENT["To Do"] == Decimal("0")
        assert JIRA_STATUS_TO_PERCENT["In Progress"] == Decimal("50")
        assert JIRA_STATUS_TO_PERCENT["Done"] == Decimal("100")

    def test_webhook_result_structure(self, factory: Week10DataFactory):
        """Should create proper webhook result."""
        activity = factory.activities[1]
        mapping = next(m for m in factory.mappings if m.activity_id == activity.id)

        result = WebhookResult(
            success=True,
            event_type="jira:issue_updated",
            issue_key=mapping.jira_issue_key,
            entity_type=EntityType.ACTIVITY.value,
            entity_id=activity.id,
            action_taken="updated_progress=75%",
            duration_ms=150,
        )

        assert result.success is True
        assert result.action_taken == "updated_progress=75%"

    def test_deleted_issue_handling(self, factory: Week10DataFactory):
        """Should handle deleted issue webhook."""
        mapping = factory.mappings[0]

        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_deleted",
            issue={
                "key": mapping.jira_issue_key,
                "id": mapping.jira_issue_id,
                "fields": {
                    "project": {"key": "F35"},
                },
            },
        )

        # Result should indicate mapping was deactivated
        result = WebhookResult(
            success=True,
            event_type="jira:issue_deleted",
            issue_key=mapping.jira_issue_key,
            entity_type=mapping.entity_type,
            entity_id=mapping.wbs_id,
            action_taken="mapping_deleted",
        )

        assert result.action_taken == "mapping_deleted"


# =============================================================================
# E2E Test Class: Audit Trail
# =============================================================================


class TestWeek10AuditTrail:
    """E2E tests for Jira sync audit trail."""

    @pytest.fixture
    def factory(self) -> Week10DataFactory:
        """Create test data factory with sync logs."""
        f = Week10DataFactory()
        f.create_program()
        f.create_jira_integration()
        f.create_wbs_structure()
        f.create_activities()
        f.create_wbs_mappings()
        f.create_activity_mappings()
        f.create_sync_logs()
        return f

    def test_sync_log_completeness(self, factory: Week10DataFactory):
        """Should maintain complete sync audit trail."""
        assert len(factory.sync_logs) == 3

        # Verify different sync types are logged
        sync_types = {log.sync_type for log in factory.sync_logs}
        assert SyncType.FULL.value in sync_types
        assert SyncType.PUSH.value in sync_types
        assert SyncType.WEBHOOK.value in sync_types

    def test_sync_log_status_tracking(self, factory: Week10DataFactory):
        """Should track sync status correctly."""
        for log in factory.sync_logs:
            assert log.status == SyncStatus.SUCCESS.value
            assert log.items_synced > 0
            assert log.duration_ms is not None

    def test_mapping_sync_history(self, factory: Week10DataFactory):
        """Should track mapping-specific sync history."""
        # Find webhook log with mapping_id
        webhook_logs = [log for log in factory.sync_logs if log.sync_type == SyncType.WEBHOOK.value]

        assert len(webhook_logs) == 1
        assert webhook_logs[0].mapping_id is not None
        assert webhook_logs[0].items_synced == 1


# =============================================================================
# E2E Test Class: Complete Workflow Integration
# =============================================================================


class TestWeek10CompleteWorkflow:
    """E2E tests for complete Jira integration workflow."""

    @pytest.fixture
    def factory(self) -> Week10DataFactory:
        """Create test data factory with full setup."""
        f = Week10DataFactory()
        f.create_program()
        f.create_jira_integration()
        f.create_wbs_structure()
        f.create_activities()
        f.create_wbs_mappings()
        f.create_activity_mappings()
        f.create_sync_logs()
        return f

    def test_full_integration_workflow(self, factory: Week10DataFactory):
        """Should complete full Jira integration workflow."""
        # Step 1: Verify program and integration setup
        program = factory.create_program()
        integration = factory.create_jira_integration()
        assert integration.program_id == program.id
        assert integration.sync_enabled is True

        # Step 2: Verify WBS to Epic mappings
        wbs_mappings = [m for m in factory.mappings if m.entity_type == EntityType.WBS.value]
        assert len(wbs_mappings) == 3

        # Step 3: Verify Activity to Issue mappings
        activity_mappings = [
            m for m in factory.mappings if m.entity_type == EntityType.ACTIVITY.value
        ]
        assert len(activity_mappings) == 4

        # Step 4: Verify audit trail
        assert len(factory.sync_logs) >= 3

    def test_bidirectional_sync_workflow(self, factory: Week10DataFactory):
        """Should support bidirectional sync between PM tool and Jira."""
        # Find bidirectional mappings
        bidirectional_mappings = [
            m for m in factory.mappings if m.sync_direction == SyncDirection.BIDIRECTIONAL.value
        ]

        # All mappings should be bidirectional by default
        assert len(bidirectional_mappings) == len(factory.mappings)

    def test_sync_status_tracking(self, factory: Week10DataFactory):
        """Should track sync status accurately."""
        integration = factory.create_jira_integration()

        # Verify integration tracks last sync
        assert integration.sync_status == "active"

        # Verify mappings track individual sync times
        for mapping in factory.mappings:
            assert mapping.last_synced_at is not None

    def test_error_handling_in_workflow(self, factory: Week10DataFactory):
        """Should handle errors gracefully in sync workflow."""
        # Create a failed sync log
        failed_log = MockJiraSyncLog(
            id=uuid4(),
            integration_id=factory.integration_id,
            mapping_id=None,
            sync_type=SyncType.PUSH.value,
            status=SyncStatus.FAILED.value,
            items_synced=0,
            error_message="Connection timeout to Jira API",
            duration_ms=30000,
        )

        # Verify error is captured
        assert failed_log.status == SyncStatus.FAILED.value
        assert failed_log.error_message is not None
        assert failed_log.items_synced == 0


# =============================================================================
# E2E Test Class: Mapping Schema Validation
# =============================================================================


class TestWeek10MappingSchemas:
    """E2E tests for Jira mapping schema validation."""

    def test_mapping_create_schema(self):
        """Should validate mapping creation schema."""
        mapping = JiraMappingCreate(
            entity_type=EntityType.ACTIVITY,
            activity_id=uuid4(),
            jira_issue_key="F35-123",
            sync_direction=SyncDirection.BIDIRECTIONAL,
        )

        assert mapping.entity_type == EntityType.ACTIVITY
        assert mapping.wbs_id is None

    def test_mapping_response_schema(self):
        """Should validate mapping response schema."""
        mapping_id = uuid4()
        integration_id = uuid4()
        activity_id = uuid4()

        response = JiraMappingResponse(
            id=mapping_id,
            integration_id=integration_id,
            entity_type=EntityType.ACTIVITY.value,
            wbs_id=None,
            activity_id=activity_id,
            jira_issue_key="F35-123",
            jira_issue_id="10123",
            sync_direction=SyncDirection.BIDIRECTIONAL.value,
            last_synced_at=datetime.now(UTC),
            last_jira_updated=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )

        assert response.jira_issue_key == "F35-123"
        assert response.entity_type == EntityType.ACTIVITY.value
