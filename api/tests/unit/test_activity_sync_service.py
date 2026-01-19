"""Unit tests for Activity to Jira Issue sync service.

Tests the ActivitySyncService with mocked repositories and Jira client.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.services.jira_activity_sync import (
    JIRA_STATUS_MAPPINGS,
    ActivitySyncError,
    ActivitySyncItem,
    ActivitySyncService,
    IntegrationNotFoundError,
    ParentEpicNotFoundError,
    SyncDisabledError,
    SyncResult,
)
from src.services.jira_client import JiraIssueData, JiraSyncError


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_default_values(self):
        """SyncResult should have sensible defaults."""
        result = SyncResult(success=True, items_synced=0, items_failed=0)
        assert result.success is True
        assert result.items_synced == 0
        assert result.items_failed == 0
        assert result.errors == []
        assert result.created_mappings == []
        assert result.updated_mappings == []
        assert result.duration_ms == 0

    def test_with_values(self):
        """SyncResult should store all values."""
        mapping_id = uuid4()
        result = SyncResult(
            success=False,
            items_synced=5,
            items_failed=2,
            errors=["Error 1", "Error 2"],
            created_mappings=[mapping_id],
            updated_mappings=[],
            duration_ms=1500,
        )
        assert result.success is False
        assert result.items_synced == 5
        assert result.items_failed == 2
        assert len(result.errors) == 2
        assert mapping_id in result.created_mappings


class TestActivitySyncItem:
    """Tests for ActivitySyncItem dataclass."""

    def test_create_action(self):
        """ActivitySyncItem should track create action."""
        mock_activity = MagicMock()
        item = ActivitySyncItem(
            activity=mock_activity,
            mapping=None,
            parent_epic_key=None,
            action="create",
        )
        assert item.action == "create"
        assert item.mapping is None
        assert item.jira_key is None
        assert item.error is None

    def test_update_action(self):
        """ActivitySyncItem should track update action with mapping."""
        mock_activity = MagicMock()
        mock_mapping = MagicMock()
        item = ActivitySyncItem(
            activity=mock_activity,
            mapping=mock_mapping,
            parent_epic_key="PROJ-10",
            action="update",
            jira_key="PROJ-123",
        )
        assert item.action == "update"
        assert item.mapping is mock_mapping
        assert item.jira_key == "PROJ-123"
        assert item.parent_epic_key == "PROJ-10"

    def test_with_parent_epic(self):
        """ActivitySyncItem should track parent epic key."""
        mock_activity = MagicMock()
        item = ActivitySyncItem(
            activity=mock_activity,
            mapping=None,
            parent_epic_key="PROJ-5",
            action="create",
        )
        assert item.parent_epic_key == "PROJ-5"


class TestActivitySyncExceptions:
    """Tests for custom Activity sync exceptions."""

    def test_activity_sync_error(self):
        """ActivitySyncError should store message and details."""
        error = ActivitySyncError("Sync failed", {"reason": "timeout"})
        assert str(error) == "Sync failed"
        assert error.message == "Sync failed"
        assert error.details == {"reason": "timeout"}

    def test_activity_sync_error_default_details(self):
        """ActivitySyncError should default to empty details."""
        error = ActivitySyncError("Error")
        assert error.details == {}

    def test_integration_not_found_error(self):
        """IntegrationNotFoundError should inherit from ActivitySyncError."""
        error = IntegrationNotFoundError("Not found")
        assert isinstance(error, ActivitySyncError)

    def test_sync_disabled_error(self):
        """SyncDisabledError should inherit from ActivitySyncError."""
        error = SyncDisabledError("Disabled")
        assert isinstance(error, ActivitySyncError)

    def test_parent_epic_not_found_error(self):
        """ParentEpicNotFoundError should inherit from ActivitySyncError."""
        error = ParentEpicNotFoundError("No epic mapping")
        assert isinstance(error, ActivitySyncError)


class TestJiraStatusMappings:
    """Tests for JIRA_STATUS_MAPPINGS constant."""

    def test_status_mappings_exist(self):
        """Should have all required status mappings."""
        assert "not_started" in JIRA_STATUS_MAPPINGS
        assert "in_progress" in JIRA_STATUS_MAPPINGS
        assert "completed" in JIRA_STATUS_MAPPINGS

    def test_status_mapping_values(self):
        """Should map to correct Jira statuses."""
        assert JIRA_STATUS_MAPPINGS["not_started"] == "To Do"
        assert JIRA_STATUS_MAPPINGS["in_progress"] == "In Progress"
        assert JIRA_STATUS_MAPPINGS["completed"] == "Done"


class TestActivitySyncServiceInit:
    """Tests for ActivitySyncService initialization."""

    def test_init_stores_dependencies(self):
        """Service should store all dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = MagicMock()
        mock_mapping_repo = MagicMock()
        mock_sync_log_repo = MagicMock()
        mock_activity_repo = MagicMock()

        service = ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

        assert service.jira_client is mock_jira
        assert service.integration_repo is mock_integration_repo
        assert service.mapping_repo is mock_mapping_repo
        assert service.sync_log_repo is mock_sync_log_repo
        assert service.activity_repo is mock_activity_repo


class TestActivitySyncServiceGetIntegration:
    """Tests for _get_integration method."""

    @pytest.fixture
    def service(self):
        """Create an ActivitySyncService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_activity_repo = AsyncMock()

        return ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

    @pytest.mark.asyncio
    async def test_get_integration_success(self, service):
        """Should return integration when found and enabled."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.sync_enabled = True
        service.integration_repo.get_by_id.return_value = mock_integration

        result = await service._get_integration(integration_id)

        assert result is mock_integration
        service.integration_repo.get_by_id.assert_called_once_with(integration_id)

    @pytest.mark.asyncio
    async def test_get_integration_not_found(self, service):
        """Should raise IntegrationNotFoundError when not found."""
        integration_id = uuid4()
        service.integration_repo.get_by_id.return_value = None

        with pytest.raises(IntegrationNotFoundError) as exc:
            await service._get_integration(integration_id)

        assert str(integration_id) in str(exc.value)

    @pytest.mark.asyncio
    async def test_get_integration_disabled(self, service):
        """Should raise SyncDisabledError when sync disabled."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.sync_enabled = False
        service.integration_repo.get_by_id.return_value = mock_integration

        with pytest.raises(SyncDisabledError) as exc:
            await service._get_integration(integration_id)

        assert "disabled" in str(exc.value).lower()


class TestActivitySyncServiceGetSyncableActivities:
    """Tests for _get_syncable_activities method."""

    @pytest.fixture
    def service(self):
        """Create an ActivitySyncService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_activity_repo = AsyncMock()

        return ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

    @pytest.fixture
    def sample_activities(self):
        """Create sample activities."""
        activities = []
        for i in range(5):
            activity = MagicMock()
            activity.id = uuid4()
            activity.code = f"ACT-{i:03d}"
            activity.name = f"Activity {i}"
            activity.duration = 5
            activity.percent_complete = Decimal("0.00")
            activities.append(activity)
        return activities

    @pytest.mark.asyncio
    async def test_returns_all_activities(self, service, sample_activities):
        """Should return all activities for program."""
        program_id = uuid4()
        service.activity_repo.get_by_program.return_value = sample_activities

        result = await service._get_syncable_activities(program_id)

        assert len(result) == 5
        service.activity_repo.get_by_program.assert_called_once_with(program_id)

    @pytest.mark.asyncio
    async def test_filters_by_specific_ids(self, service, sample_activities):
        """Should filter to specific activity IDs when provided."""
        program_id = uuid4()
        target_id = sample_activities[0].id
        service.activity_repo.get_by_program.return_value = sample_activities

        result = await service._get_syncable_activities(program_id, activity_ids=[target_id])

        assert len(result) == 1
        assert result[0].id == target_id

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_activities(self, service):
        """Should return empty list when no activities."""
        program_id = uuid4()
        service.activity_repo.get_by_program.return_value = []

        result = await service._get_syncable_activities(program_id)

        assert len(result) == 0


class TestActivitySyncServicePrepareSyncItems:
    """Tests for _prepare_sync_items method."""

    @pytest.fixture
    def service(self):
        """Create an ActivitySyncService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_activity_repo = AsyncMock()

        return ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

    @pytest.mark.asyncio
    async def test_create_action_for_unmapped(self, service):
        """Should assign 'create' action for unmapped activity."""
        integration_id = uuid4()
        activity = MagicMock()
        activity.id = uuid4()
        activity.wbs_id = uuid4()
        service.mapping_repo.get_by_activity.return_value = None
        service.mapping_repo.get_by_wbs.return_value = None

        result = await service._prepare_sync_items(integration_id, [activity])

        assert len(result) == 1
        assert result[0].action == "create"
        assert result[0].mapping is None

    @pytest.mark.asyncio
    async def test_update_action_for_bidirectional_mapping(self, service):
        """Should assign 'update' action for bidirectional mapping."""
        integration_id = uuid4()
        activity = MagicMock()
        activity.id = uuid4()
        activity.wbs_id = uuid4()
        mapping = MagicMock()
        mapping.sync_direction = "bidirectional"
        service.mapping_repo.get_by_activity.return_value = mapping
        service.mapping_repo.get_by_wbs.return_value = None

        result = await service._prepare_sync_items(integration_id, [activity])

        assert len(result) == 1
        assert result[0].action == "update"
        assert result[0].mapping is mapping

    @pytest.mark.asyncio
    async def test_update_action_for_to_jira_mapping(self, service):
        """Should assign 'update' action for to_jira mapping."""
        integration_id = uuid4()
        activity = MagicMock()
        activity.id = uuid4()
        activity.wbs_id = uuid4()
        mapping = MagicMock()
        mapping.sync_direction = "to_jira"
        service.mapping_repo.get_by_activity.return_value = mapping
        service.mapping_repo.get_by_wbs.return_value = None

        result = await service._prepare_sync_items(integration_id, [activity])

        assert result[0].action == "update"

    @pytest.mark.asyncio
    async def test_skip_action_for_from_jira_mapping(self, service):
        """Should assign 'skip' action for from_jira only mapping."""
        integration_id = uuid4()
        activity = MagicMock()
        activity.id = uuid4()
        activity.wbs_id = uuid4()
        mapping = MagicMock()
        mapping.sync_direction = "from_jira"
        service.mapping_repo.get_by_activity.return_value = mapping
        service.mapping_repo.get_by_wbs.return_value = None

        result = await service._prepare_sync_items(integration_id, [activity])

        assert result[0].action == "skip"

    @pytest.mark.asyncio
    async def test_includes_parent_epic_key(self, service):
        """Should include parent epic key from WBS mapping."""
        integration_id = uuid4()
        activity = MagicMock()
        activity.id = uuid4()
        activity.wbs_id = uuid4()

        wbs_mapping = MagicMock()
        wbs_mapping.jira_issue_key = "PROJ-10"

        service.mapping_repo.get_by_activity.return_value = None
        service.mapping_repo.get_by_wbs.return_value = wbs_mapping

        result = await service._prepare_sync_items(integration_id, [activity])

        assert result[0].parent_epic_key == "PROJ-10"


class TestActivitySyncServiceGetParentEpicKey:
    """Tests for _get_parent_epic_key method."""

    @pytest.fixture
    def service(self):
        """Create an ActivitySyncService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_activity_repo = AsyncMock()

        return ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

    @pytest.mark.asyncio
    async def test_returns_epic_key_when_mapping_exists(self, service):
        """Should return epic key from WBS mapping."""
        integration_id = uuid4()
        wbs_id = uuid4()

        wbs_mapping = MagicMock()
        wbs_mapping.jira_issue_key = "PROJ-10"
        service.mapping_repo.get_by_wbs.return_value = wbs_mapping

        result = await service._get_parent_epic_key(integration_id, wbs_id)

        assert result == "PROJ-10"
        service.mapping_repo.get_by_wbs.assert_called_once_with(integration_id, wbs_id)

    @pytest.mark.asyncio
    async def test_returns_none_when_no_mapping(self, service):
        """Should return None when no WBS mapping."""
        integration_id = uuid4()
        wbs_id = uuid4()
        service.mapping_repo.get_by_wbs.return_value = None

        result = await service._get_parent_epic_key(integration_id, wbs_id)

        assert result is None


class TestActivitySyncServiceBuildIssueDescription:
    """Tests for _build_issue_description method."""

    @pytest.fixture
    def service(self):
        """Create an ActivitySyncService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_activity_repo = AsyncMock()

        return ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

    def test_includes_activity_code_and_duration(self, service):
        """Description should include activity code and duration."""
        activity = MagicMock()
        activity.code = "ACT-001"
        activity.duration = 10
        activity.planned_start = None
        activity.planned_finish = None
        activity.early_start = None
        activity.early_finish = None
        activity.percent_complete = Decimal("50.00")
        activity.is_critical = False
        activity.is_milestone = False
        activity.description = None

        result = service._build_issue_description(activity)

        assert "*Activity Code:* ACT-001" in result
        assert "*Duration:* 10 days" in result

    def test_includes_dates_when_present(self, service):
        """Description should include dates when available."""
        from datetime import date

        activity = MagicMock()
        activity.code = "ACT-001"
        activity.duration = 5
        activity.planned_start = date(2026, 1, 15)
        activity.planned_finish = date(2026, 1, 20)
        activity.early_start = date(2026, 1, 15)
        activity.early_finish = date(2026, 1, 20)
        activity.percent_complete = Decimal("0.00")
        activity.is_critical = False
        activity.is_milestone = False
        activity.description = None

        result = service._build_issue_description(activity)

        assert "*Planned Start:*" in result
        assert "*Planned Finish:*" in result
        assert "*Early Start:*" in result
        assert "*Early Finish:*" in result

    def test_includes_progress(self, service):
        """Description should include progress percentage."""
        activity = MagicMock()
        activity.code = "ACT-001"
        activity.duration = 5
        activity.planned_start = None
        activity.planned_finish = None
        activity.early_start = None
        activity.early_finish = None
        activity.percent_complete = Decimal("75.00")
        activity.is_critical = False
        activity.is_milestone = False
        activity.description = None

        result = service._build_issue_description(activity)

        assert "*Progress:* 75.00%" in result

    def test_includes_critical_path_indicator(self, service):
        """Description should indicate if on critical path."""
        activity = MagicMock()
        activity.code = "ACT-001"
        activity.duration = 5
        activity.planned_start = None
        activity.planned_finish = None
        activity.early_start = None
        activity.early_finish = None
        activity.percent_complete = Decimal("0.00")
        activity.is_critical = True
        activity.is_milestone = False
        activity.description = None

        result = service._build_issue_description(activity)

        assert "critical path" in result.lower()

    def test_includes_milestone_indicator(self, service):
        """Description should indicate if milestone."""
        activity = MagicMock()
        activity.code = "ACT-001"
        activity.duration = 0
        activity.planned_start = None
        activity.planned_finish = None
        activity.early_start = None
        activity.early_finish = None
        activity.percent_complete = Decimal("0.00")
        activity.is_critical = False
        activity.is_milestone = True
        activity.description = None

        result = service._build_issue_description(activity)

        assert "milestone" in result.lower()

    def test_includes_description_when_present(self, service):
        """Description should include activity description."""
        activity = MagicMock()
        activity.code = "ACT-001"
        activity.duration = 5
        activity.planned_start = None
        activity.planned_finish = None
        activity.early_start = None
        activity.early_finish = None
        activity.percent_complete = Decimal("0.00")
        activity.is_critical = False
        activity.is_milestone = False
        activity.description = "Complete detailed design review"

        result = service._build_issue_description(activity)

        assert "Complete detailed design review" in result

    def test_includes_sync_attribution(self, service):
        """Description should include sync attribution."""
        activity = MagicMock()
        activity.code = "ACT-001"
        activity.duration = 5
        activity.planned_start = None
        activity.planned_finish = None
        activity.early_start = None
        activity.early_finish = None
        activity.percent_complete = Decimal("0.00")
        activity.is_critical = False
        activity.is_milestone = False
        activity.description = None

        result = service._build_issue_description(activity)

        assert "Defense PM Tool" in result


class TestActivitySyncServiceCreateIssue:
    """Tests for _create_issue method."""

    @pytest.fixture
    def service(self):
        """Create an ActivitySyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_activity_repo = AsyncMock()

        return ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

    @pytest.mark.asyncio
    async def test_creates_issue_in_jira(self, service):
        """Should call jira_client.create_issue with correct params."""
        integration = MagicMock()
        integration.id = uuid4()
        integration.project_key = "PROJ"

        activity = MagicMock()
        activity.id = uuid4()
        activity.code = "ACT-001"
        activity.name = "Design Review"
        activity.duration = 5
        activity.planned_start = None
        activity.planned_finish = None
        activity.early_start = None
        activity.early_finish = None
        activity.percent_complete = Decimal("0.00")
        activity.is_critical = False
        activity.is_milestone = False
        activity.description = None

        item = ActivitySyncItem(
            activity=activity,
            mapping=None,
            parent_epic_key="PROJ-10",
            action="create",
        )

        now = datetime.now(UTC)
        issue_data = JiraIssueData(
            key="PROJ-123",
            id="10123",
            summary="Design Review",
            description=None,
            issue_type="Task",
            status="To Do",
            assignee=None,
            created=now,
            updated=now,
        )
        service.jira_client.create_issue.return_value = issue_data

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        service.mapping_repo.create.return_value = mock_mapping

        result = await service._create_issue(integration, item)

        service.jira_client.create_issue.assert_called_once()
        call_kwargs = service.jira_client.create_issue.call_args[1]
        assert call_kwargs["project_key"] == "PROJ"
        assert call_kwargs["summary"] == "Design Review"
        assert call_kwargs["issue_type"] == "Task"
        assert call_kwargs["epic_key"] == "PROJ-10"
        assert "defense-pm-tool" in call_kwargs["labels"]

    @pytest.mark.asyncio
    async def test_creates_mapping_record(self, service):
        """Should create JiraMapping record."""
        integration = MagicMock()
        integration.id = uuid4()
        integration.project_key = "PROJ"

        activity = MagicMock()
        activity.id = uuid4()
        activity.code = "ACT-001"
        activity.name = "Design Review"
        activity.duration = 5
        activity.planned_start = None
        activity.planned_finish = None
        activity.early_start = None
        activity.early_finish = None
        activity.percent_complete = Decimal("0.00")
        activity.is_critical = False
        activity.is_milestone = False
        activity.description = None

        item = ActivitySyncItem(
            activity=activity,
            mapping=None,
            parent_epic_key=None,
            action="create",
        )

        now = datetime.now(UTC)
        issue_data = JiraIssueData(
            key="PROJ-123",
            id="10123",
            summary="Design Review",
            description=None,
            issue_type="Task",
            status="To Do",
            assignee=None,
            created=now,
            updated=now,
        )
        service.jira_client.create_issue.return_value = issue_data

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        service.mapping_repo.create.return_value = mock_mapping

        result = await service._create_issue(integration, item)

        assert result is mock_mapping
        service.mapping_repo.create.assert_called_once()


class TestActivitySyncServiceUpdateIssue:
    """Tests for _update_issue method."""

    @pytest.fixture
    def service(self):
        """Create an ActivitySyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_activity_repo = AsyncMock()

        return ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

    @pytest.mark.asyncio
    async def test_returns_none_for_no_mapping(self, service):
        """Should return None when mapping is None."""
        integration = MagicMock()
        activity = MagicMock()

        result = await service._update_issue(integration, activity, None)

        assert result is None

    @pytest.mark.asyncio
    async def test_updates_issue_in_jira(self, service):
        """Should call jira_client.update_issue."""
        integration = MagicMock()
        integration.id = uuid4()
        integration.project_key = "PROJ"

        activity = MagicMock()
        activity.id = uuid4()
        activity.code = "ACT-001"
        activity.name = "Updated Design Review"
        activity.duration = 5
        activity.planned_start = None
        activity.planned_finish = None
        activity.early_start = None
        activity.early_finish = None
        activity.percent_complete = Decimal("50.00")
        activity.is_critical = False
        activity.is_milestone = False
        activity.description = "Updated description"

        mapping = MagicMock()
        mapping.id = uuid4()
        mapping.jira_issue_key = "PROJ-123"
        mapping.last_synced_at = None

        result = await service._update_issue(integration, activity, mapping)

        service.jira_client.update_issue.assert_called_once()
        call_kwargs = service.jira_client.update_issue.call_args[1]
        assert call_kwargs["issue_key"] == "PROJ-123"
        assert call_kwargs["summary"] == "Updated Design Review"

    @pytest.mark.asyncio
    async def test_updates_mapping_timestamp(self, service):
        """Should update mapping's last_synced_at."""
        integration = MagicMock()
        integration.id = uuid4()
        integration.project_key = "PROJ"

        activity = MagicMock()
        activity.id = uuid4()
        activity.code = "ACT-001"
        activity.name = "Design Review"
        activity.duration = 5
        activity.planned_start = None
        activity.planned_finish = None
        activity.early_start = None
        activity.early_finish = None
        activity.percent_complete = Decimal("0.00")
        activity.is_critical = False
        activity.is_milestone = False
        activity.description = None

        mapping = MagicMock()
        mapping.id = uuid4()
        mapping.jira_issue_key = "PROJ-123"

        result = await service._update_issue(integration, activity, mapping)

        service.mapping_repo.update.assert_called_once()
        assert result is mapping


class TestActivitySyncServiceSyncActivitiesToJira:
    """Tests for sync_activities_to_jira method."""

    @pytest.fixture
    def service(self):
        """Create an ActivitySyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_activity_repo = AsyncMock()

        return ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

    @pytest.mark.asyncio
    async def test_raises_for_missing_integration(self, service):
        """Should raise IntegrationNotFoundError."""
        integration_id = uuid4()
        service.integration_repo.get_by_id.return_value = None

        with pytest.raises(IntegrationNotFoundError):
            await service.sync_activities_to_jira(integration_id)

    @pytest.mark.asyncio
    async def test_raises_for_disabled_sync(self, service):
        """Should raise SyncDisabledError."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.sync_enabled = False
        service.integration_repo.get_by_id.return_value = mock_integration

        with pytest.raises(SyncDisabledError):
            await service.sync_activities_to_jira(integration_id)

    @pytest.mark.asyncio
    async def test_returns_empty_result_for_no_activities(self, service):
        """Should return empty result when no activities."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.sync_enabled = True
        mock_integration.program_id = uuid4()
        service.integration_repo.get_by_id.return_value = mock_integration
        service.activity_repo.get_by_program.return_value = []

        result = await service.sync_activities_to_jira(integration_id)

        assert result.success is True
        assert result.items_synced == 0
        assert result.items_failed == 0

    @pytest.mark.asyncio
    async def test_creates_issues_for_unmapped_activities(self, service):
        """Should create Issues for unmapped activities."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.program_id = uuid4()
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        activity = MagicMock()
        activity.id = uuid4()
        activity.wbs_id = uuid4()
        activity.code = "ACT-001"
        activity.name = "Design Review"
        activity.duration = 5
        activity.planned_start = None
        activity.planned_finish = None
        activity.early_start = None
        activity.early_finish = None
        activity.percent_complete = Decimal("0.00")
        activity.is_critical = False
        activity.is_milestone = False
        activity.description = None
        service.activity_repo.get_by_program.return_value = [activity]
        service.mapping_repo.get_by_activity.return_value = None
        service.mapping_repo.get_by_wbs.return_value = None

        now = datetime.now(UTC)
        issue_data = JiraIssueData(
            key="PROJ-123",
            id="10123",
            summary="Design Review",
            description=None,
            issue_type="Task",
            status="To Do",
            assignee=None,
            created=now,
            updated=now,
        )
        service.jira_client.create_issue.return_value = issue_data

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        service.mapping_repo.create.return_value = mock_mapping

        result = await service.sync_activities_to_jira(integration_id)

        assert result.success is True
        assert result.items_synced == 1
        assert len(result.created_mappings) == 1

    @pytest.mark.asyncio
    async def test_logs_sync_operation(self, service):
        """Should create sync log entry."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.program_id = uuid4()
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        activity = MagicMock()
        activity.id = uuid4()
        activity.wbs_id = uuid4()
        activity.code = "ACT-001"
        activity.name = "Design Review"
        activity.duration = 5
        activity.planned_start = None
        activity.planned_finish = None
        activity.early_start = None
        activity.early_finish = None
        activity.percent_complete = Decimal("0.00")
        activity.is_critical = False
        activity.is_milestone = False
        activity.description = None
        service.activity_repo.get_by_program.return_value = [activity]
        service.mapping_repo.get_by_activity.return_value = None
        service.mapping_repo.get_by_wbs.return_value = None

        now = datetime.now(UTC)
        issue_data = JiraIssueData(
            key="PROJ-123",
            id="10123",
            summary="Design Review",
            description=None,
            issue_type="Task",
            status="To Do",
            assignee=None,
            created=now,
            updated=now,
        )
        service.jira_client.create_issue.return_value = issue_data

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        service.mapping_repo.create.return_value = mock_mapping

        await service.sync_activities_to_jira(integration_id)

        service.sync_log_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_partial_failure(self, service):
        """Should report partial success on some failures."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.program_id = uuid4()
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        # Create two activities
        activity1 = MagicMock()
        activity1.id = uuid4()
        activity1.wbs_id = uuid4()
        activity1.code = "ACT-001"
        activity1.name = "Activity 1"
        activity1.duration = 5
        activity1.planned_start = None
        activity1.planned_finish = None
        activity1.early_start = None
        activity1.early_finish = None
        activity1.percent_complete = Decimal("0.00")
        activity1.is_critical = False
        activity1.is_milestone = False
        activity1.description = None

        activity2 = MagicMock()
        activity2.id = uuid4()
        activity2.wbs_id = uuid4()
        activity2.code = "ACT-002"
        activity2.name = "Activity 2"
        activity2.duration = 5
        activity2.planned_start = None
        activity2.planned_finish = None
        activity2.early_start = None
        activity2.early_finish = None
        activity2.percent_complete = Decimal("0.00")
        activity2.is_critical = False
        activity2.is_milestone = False
        activity2.description = None

        service.activity_repo.get_by_program.return_value = [activity1, activity2]
        service.mapping_repo.get_by_activity.return_value = None
        service.mapping_repo.get_by_wbs.return_value = None

        # First succeeds, second fails
        now = datetime.now(UTC)
        issue_data = JiraIssueData(
            key="PROJ-123",
            id="10123",
            summary="Activity 1",
            description=None,
            issue_type="Task",
            status="To Do",
            assignee=None,
            created=now,
            updated=now,
        )
        service.jira_client.create_issue.side_effect = [
            issue_data,
            JiraSyncError("Jira API error"),
        ]

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        service.mapping_repo.create.return_value = mock_mapping

        result = await service.sync_activities_to_jira(integration_id)

        assert result.success is True  # Partial success
        assert result.items_synced == 1
        assert result.items_failed == 1
        assert len(result.errors) == 1


class TestActivitySyncServicePullFromJira:
    """Tests for pull_from_jira method."""

    @pytest.fixture
    def service(self):
        """Create an ActivitySyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_activity_repo = AsyncMock()

        return ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

    @pytest.mark.asyncio
    async def test_raises_for_missing_integration(self, service):
        """Should raise IntegrationNotFoundError."""
        integration_id = uuid4()
        service.integration_repo.get_by_id.return_value = None

        with pytest.raises(IntegrationNotFoundError):
            await service.pull_from_jira(integration_id)

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_mappings(self, service):
        """Should return empty result when no pullable mappings."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.program_id = uuid4()
        service.integration_repo.get_by_id.return_value = mock_integration
        service.mapping_repo.get_by_integration.return_value = []

        result = await service.pull_from_jira(integration_id)

        assert result.success is True
        assert result.items_synced == 0

    @pytest.mark.asyncio
    async def test_filters_pullable_mappings(self, service):
        """Should only pull from bidirectional or from_jira mappings."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.program_id = uuid4()
        service.integration_repo.get_by_id.return_value = mock_integration

        # Create mapping with to_jira direction (should be skipped)
        mapping = MagicMock()
        mapping.id = uuid4()
        mapping.sync_direction = "to_jira"
        service.mapping_repo.get_by_integration.return_value = [mapping]

        result = await service.pull_from_jira(integration_id)

        # No pullable mappings
        assert result.items_synced == 0

    @pytest.mark.asyncio
    async def test_updates_activity_from_issue(self, service):
        """Should update Activity when Jira has newer changes."""
        integration_id = uuid4()
        activity_id = uuid4()

        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.program_id = uuid4()
        service.integration_repo.get_by_id.return_value = mock_integration

        mapping = MagicMock()
        mapping.id = uuid4()
        mapping.activity_id = activity_id
        mapping.jira_issue_key = "PROJ-123"
        mapping.sync_direction = "bidirectional"
        mapping.last_jira_updated = datetime(2026, 1, 1, tzinfo=UTC)
        service.mapping_repo.get_by_integration.return_value = [mapping]

        activity = MagicMock()
        activity.id = activity_id
        activity.code = "ACT-001"
        activity.percent_complete = Decimal("0.00")
        service.activity_repo.get_by_id.return_value = activity

        # Jira has newer update
        issue_data = JiraIssueData(
            key="PROJ-123",
            id="10123",
            summary="Updated Activity Name",
            description="New description",
            issue_type="Task",
            status="In Progress",
            assignee=None,
            created=datetime(2026, 1, 1, tzinfo=UTC),
            updated=datetime(2026, 1, 18, tzinfo=UTC),  # Newer
        )
        service.jira_client.get_issue.return_value = issue_data

        result = await service.pull_from_jira(integration_id)

        assert result.items_synced == 1
        service.activity_repo.update.assert_called_once()


class TestActivitySyncServiceSyncProgress:
    """Tests for sync_progress method."""

    @pytest.fixture
    def service(self):
        """Create an ActivitySyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_activity_repo = AsyncMock()

        return ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

    @pytest.mark.asyncio
    async def test_syncs_progress_to_jira(self, service):
        """Should sync activity progress to Jira."""
        integration_id = uuid4()
        activity_id = uuid4()

        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.program_id = uuid4()
        service.integration_repo.get_by_id.return_value = mock_integration

        mapping = MagicMock()
        mapping.id = uuid4()
        mapping.activity_id = activity_id
        mapping.jira_issue_key = "PROJ-123"
        service.mapping_repo.get_by_integration.return_value = [mapping]

        activity = MagicMock()
        activity.id = activity_id
        activity.code = "ACT-001"
        activity.percent_complete = Decimal("50.00")
        service.activity_repo.get_by_id.return_value = activity

        issue_data = JiraIssueData(
            key="PROJ-123",
            id="10123",
            summary="Activity",
            description=None,
            issue_type="Task",
            status="To Do",
            assignee=None,
            created=datetime.now(UTC),
            updated=datetime.now(UTC),
        )
        service.jira_client.get_issue.return_value = issue_data

        result = await service.sync_progress(integration_id)

        assert result.success is True
        # Should have attempted to transition the status
        service.jira_client.transition_issue.assert_called_once()


class TestActivitySyncServiceSyncActivityProgress:
    """Tests for _sync_activity_progress method."""

    @pytest.fixture
    def service(self):
        """Create an ActivitySyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_activity_repo = AsyncMock()

        return ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

    @pytest.mark.asyncio
    async def test_transitions_to_done_at_100_percent(self, service):
        """Should transition to Done when percent_complete is 100."""
        mapping = MagicMock()
        mapping.jira_issue_key = "PROJ-123"
        mapping.last_synced_at = None

        activity = MagicMock()
        activity.percent_complete = Decimal("100.00")

        issue_data = JiraIssueData(
            key="PROJ-123",
            id="10123",
            summary="Activity",
            description=None,
            issue_type="Task",
            status="In Progress",
            assignee=None,
            created=datetime.now(UTC),
            updated=datetime.now(UTC),
        )
        service.jira_client.get_issue.return_value = issue_data

        await service._sync_activity_progress(mapping, activity)

        service.jira_client.transition_issue.assert_called_once_with("PROJ-123", "Done")

    @pytest.mark.asyncio
    async def test_transitions_to_in_progress_for_partial(self, service):
        """Should transition to In Progress when 0 < percent_complete < 100."""
        mapping = MagicMock()
        mapping.jira_issue_key = "PROJ-123"
        mapping.last_synced_at = None

        activity = MagicMock()
        activity.percent_complete = Decimal("50.00")

        issue_data = JiraIssueData(
            key="PROJ-123",
            id="10123",
            summary="Activity",
            description=None,
            issue_type="Task",
            status="To Do",
            assignee=None,
            created=datetime.now(UTC),
            updated=datetime.now(UTC),
        )
        service.jira_client.get_issue.return_value = issue_data

        await service._sync_activity_progress(mapping, activity)

        service.jira_client.transition_issue.assert_called_once_with("PROJ-123", "In Progress")

    @pytest.mark.asyncio
    async def test_no_transition_when_already_correct(self, service):
        """Should not transition when already in correct status."""
        mapping = MagicMock()
        mapping.jira_issue_key = "PROJ-123"
        mapping.last_synced_at = None

        activity = MagicMock()
        activity.percent_complete = Decimal("50.00")

        issue_data = JiraIssueData(
            key="PROJ-123",
            id="10123",
            summary="Activity",
            description=None,
            issue_type="Task",
            status="In Progress",  # Already correct
            assignee=None,
            created=datetime.now(UTC),
            updated=datetime.now(UTC),
        )
        service.jira_client.get_issue.return_value = issue_data

        await service._sync_activity_progress(mapping, activity)

        service.jira_client.transition_issue.assert_not_called()


class TestActivitySyncServiceLogSync:
    """Tests for _log_sync method."""

    @pytest.fixture
    def service(self):
        """Create an ActivitySyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_activity_repo = AsyncMock()

        return ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

    @pytest.mark.asyncio
    async def test_creates_sync_log_entry(self, service):
        """Should create sync log with all parameters."""
        integration_id = uuid4()
        mapping_id = uuid4()

        await service._log_sync(
            integration_id=integration_id,
            sync_type="push",
            status="success",
            items_synced=5,
            error_message=None,
            duration_ms=1500,
            mapping_id=mapping_id,
        )

        service.sync_log_repo.create.assert_called_once()


class TestActivitySyncServiceUpdateIntegrationSyncTime:
    """Tests for _update_integration_sync_time method."""

    @pytest.fixture
    def service(self):
        """Create an ActivitySyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_activity_repo = AsyncMock()

        return ActivitySyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            activity_repo=mock_activity_repo,
        )

    @pytest.mark.asyncio
    async def test_updates_last_sync_at(self, service):
        """Should update integration's last_sync_at."""
        integration = MagicMock()
        integration.id = uuid4()

        await service._update_integration_sync_time(integration)

        service.integration_repo.update.assert_called_once()
        call_args = service.integration_repo.update.call_args
        assert call_args[0][0] is integration  # First arg is the model
        assert "last_sync_at" in call_args[0][1]  # Second arg is the update data
