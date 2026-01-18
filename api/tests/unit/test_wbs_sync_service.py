"""Unit tests for WBS to Jira Epic sync service.

Tests the WBSSyncService with mocked repositories and Jira client.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.services.jira_client import JiraEpicData, JiraIssueData, JiraSyncError
from src.services.jira_wbs_sync import (
    IntegrationNotFoundError,
    SyncDisabledError,
    SyncResult,
    WBSSyncError,
    WBSSyncItem,
    WBSSyncService,
)


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


class TestWBSSyncItem:
    """Tests for WBSSyncItem dataclass."""

    def test_create_action(self):
        """WBSSyncItem should track create action."""
        mock_wbs = MagicMock()
        item = WBSSyncItem(wbs=mock_wbs, mapping=None, action="create")
        assert item.action == "create"
        assert item.mapping is None
        assert item.jira_key is None
        assert item.error is None

    def test_update_action(self):
        """WBSSyncItem should track update action with mapping."""
        mock_wbs = MagicMock()
        mock_mapping = MagicMock()
        item = WBSSyncItem(wbs=mock_wbs, mapping=mock_mapping, action="update", jira_key="PROJ-123")
        assert item.action == "update"
        assert item.mapping is mock_mapping
        assert item.jira_key == "PROJ-123"


class TestWBSSyncExceptions:
    """Tests for custom WBS sync exceptions."""

    def test_wbs_sync_error(self):
        """WBSSyncError should store message and details."""
        error = WBSSyncError("Sync failed", {"reason": "timeout"})
        assert str(error) == "Sync failed"
        assert error.message == "Sync failed"
        assert error.details == {"reason": "timeout"}

    def test_wbs_sync_error_default_details(self):
        """WBSSyncError should default to empty details."""
        error = WBSSyncError("Error")
        assert error.details == {}

    def test_integration_not_found_error(self):
        """IntegrationNotFoundError should inherit from WBSSyncError."""
        error = IntegrationNotFoundError("Not found")
        assert isinstance(error, WBSSyncError)

    def test_sync_disabled_error(self):
        """SyncDisabledError should inherit from WBSSyncError."""
        error = SyncDisabledError("Disabled")
        assert isinstance(error, WBSSyncError)


class TestWBSSyncServiceInit:
    """Tests for WBSSyncService initialization."""

    def test_init_stores_dependencies(self):
        """Service should store all dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = MagicMock()
        mock_mapping_repo = MagicMock()
        mock_sync_log_repo = MagicMock()
        mock_wbs_repo = MagicMock()

        service = WBSSyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            wbs_repo=mock_wbs_repo,
        )

        assert service.jira_client is mock_jira
        assert service.integration_repo is mock_integration_repo
        assert service.mapping_repo is mock_mapping_repo
        assert service.sync_log_repo is mock_sync_log_repo
        assert service.wbs_repo is mock_wbs_repo

    def test_max_wbs_level_constant(self):
        """Service should have MAX_WBS_LEVEL constant."""
        assert WBSSyncService.MAX_WBS_LEVEL == 2


class TestWBSSyncServiceGetIntegration:
    """Tests for _get_integration method."""

    @pytest.fixture
    def service(self):
        """Create a WBSSyncService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_wbs_repo = AsyncMock()

        return WBSSyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            wbs_repo=mock_wbs_repo,
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


class TestWBSSyncServiceGetSyncableWBS:
    """Tests for _get_syncable_wbs method."""

    @pytest.fixture
    def service(self):
        """Create a WBSSyncService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_wbs_repo = AsyncMock()

        return WBSSyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            wbs_repo=mock_wbs_repo,
        )

    @pytest.fixture
    def sample_wbs_elements(self):
        """Create sample WBS elements at different levels."""
        elements = []
        for i in range(5):
            wbs = MagicMock()
            wbs.id = uuid4()
            wbs.level = i + 1  # Levels 1-5
            wbs.wbs_code = f"1.{'1.' * i}1"
            elements.append(wbs)
        return elements

    @pytest.mark.asyncio
    async def test_filters_by_level(self, service, sample_wbs_elements):
        """Should only return WBS elements at level 1-2."""
        program_id = uuid4()
        service.wbs_repo.get_by_program.return_value = sample_wbs_elements

        result = await service._get_syncable_wbs(program_id)

        assert len(result) == 2  # Only levels 1 and 2
        assert all(w.level <= 2 for w in result)

    @pytest.mark.asyncio
    async def test_filters_by_specific_ids(self, service, sample_wbs_elements):
        """Should filter to specific WBS IDs when provided."""
        program_id = uuid4()
        target_id = sample_wbs_elements[0].id
        service.wbs_repo.get_by_program.return_value = sample_wbs_elements

        result = await service._get_syncable_wbs(program_id, wbs_ids=[target_id])

        assert len(result) == 1
        assert result[0].id == target_id

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_eligible(self, service):
        """Should return empty list when no eligible WBS elements."""
        program_id = uuid4()
        # Create only level 3+ elements
        high_level_elements = []
        for i in range(3, 6):
            wbs = MagicMock()
            wbs.id = uuid4()
            wbs.level = i
            high_level_elements.append(wbs)
        service.wbs_repo.get_by_program.return_value = high_level_elements

        result = await service._get_syncable_wbs(program_id)

        assert len(result) == 0


class TestWBSSyncServicePrepareSyncItems:
    """Tests for _prepare_sync_items method."""

    @pytest.fixture
    def service(self):
        """Create a WBSSyncService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_wbs_repo = AsyncMock()

        return WBSSyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            wbs_repo=mock_wbs_repo,
        )

    @pytest.mark.asyncio
    async def test_create_action_for_unmapped(self, service):
        """Should assign 'create' action for unmapped WBS."""
        integration_id = uuid4()
        wbs = MagicMock()
        wbs.id = uuid4()
        service.mapping_repo.get_by_wbs.return_value = None

        result = await service._prepare_sync_items(integration_id, [wbs])

        assert len(result) == 1
        assert result[0].action == "create"
        assert result[0].mapping is None

    @pytest.mark.asyncio
    async def test_update_action_for_bidirectional_mapping(self, service):
        """Should assign 'update' action for bidirectional mapping."""
        integration_id = uuid4()
        wbs = MagicMock()
        wbs.id = uuid4()
        mapping = MagicMock()
        mapping.sync_direction = "bidirectional"
        service.mapping_repo.get_by_wbs.return_value = mapping

        result = await service._prepare_sync_items(integration_id, [wbs])

        assert len(result) == 1
        assert result[0].action == "update"
        assert result[0].mapping is mapping

    @pytest.mark.asyncio
    async def test_update_action_for_to_jira_mapping(self, service):
        """Should assign 'update' action for to_jira mapping."""
        integration_id = uuid4()
        wbs = MagicMock()
        wbs.id = uuid4()
        mapping = MagicMock()
        mapping.sync_direction = "to_jira"
        service.mapping_repo.get_by_wbs.return_value = mapping

        result = await service._prepare_sync_items(integration_id, [wbs])

        assert result[0].action == "update"

    @pytest.mark.asyncio
    async def test_skip_action_for_from_jira_mapping(self, service):
        """Should assign 'skip' action for from_jira only mapping."""
        integration_id = uuid4()
        wbs = MagicMock()
        wbs.id = uuid4()
        mapping = MagicMock()
        mapping.sync_direction = "from_jira"
        service.mapping_repo.get_by_wbs.return_value = mapping

        result = await service._prepare_sync_items(integration_id, [wbs])

        assert result[0].action == "skip"


class TestWBSSyncServiceBuildEpicDescription:
    """Tests for _build_epic_description method."""

    @pytest.fixture
    def service(self):
        """Create a WBSSyncService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_wbs_repo = AsyncMock()

        return WBSSyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            wbs_repo=mock_wbs_repo,
        )

    def test_includes_wbs_code_and_path(self, service):
        """Description should include WBS code and path."""
        wbs = MagicMock()
        wbs.wbs_code = "1.2.3"
        wbs.path = "1.2.3"
        wbs.level = 3
        wbs.description = None
        wbs.is_control_account = False
        wbs.budget_at_completion = Decimal("0.00")

        result = service._build_epic_description(wbs)

        assert "*WBS Element:* 1.2.3" in result
        assert "*Path:* 1.2.3" in result
        assert "*Level:* 3" in result

    def test_includes_description_when_present(self, service):
        """Description should include WBS description."""
        wbs = MagicMock()
        wbs.wbs_code = "1.1"
        wbs.path = "1.1"
        wbs.level = 2
        wbs.description = "This is the subsystem design phase"
        wbs.is_control_account = False
        wbs.budget_at_completion = Decimal("0.00")

        result = service._build_epic_description(wbs)

        assert "This is the subsystem design phase" in result

    def test_includes_control_account_indicator(self, service):
        """Description should indicate if control account."""
        wbs = MagicMock()
        wbs.wbs_code = "1.1"
        wbs.path = "1.1"
        wbs.level = 2
        wbs.description = None
        wbs.is_control_account = True
        wbs.budget_at_completion = Decimal("0.00")

        result = service._build_epic_description(wbs)

        assert "Control Account" in result

    def test_includes_budget_when_present(self, service):
        """Description should include budget when non-zero."""
        wbs = MagicMock()
        wbs.wbs_code = "1.1"
        wbs.path = "1.1"
        wbs.level = 2
        wbs.description = None
        wbs.is_control_account = False
        wbs.budget_at_completion = Decimal("150000.00")

        result = service._build_epic_description(wbs)

        assert "$150,000.00" in result

    def test_includes_sync_attribution(self, service):
        """Description should include sync attribution."""
        wbs = MagicMock()
        wbs.wbs_code = "1.1"
        wbs.path = "1.1"
        wbs.level = 2
        wbs.description = None
        wbs.is_control_account = False
        wbs.budget_at_completion = Decimal("0.00")

        result = service._build_epic_description(wbs)

        assert "Defense PM Tool" in result


class TestWBSSyncServiceCreateEpic:
    """Tests for _create_epic method."""

    @pytest.fixture
    def service(self):
        """Create a WBSSyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_wbs_repo = AsyncMock()

        return WBSSyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            wbs_repo=mock_wbs_repo,
        )

    @pytest.mark.asyncio
    async def test_creates_epic_in_jira(self, service):
        """Should call jira_client.create_epic with correct params."""
        integration = MagicMock()
        integration.id = uuid4()
        integration.project_key = "PROJ"

        wbs = MagicMock()
        wbs.id = uuid4()
        wbs.wbs_code = "1.1"
        wbs.name = "Design Phase"
        wbs.path = "1.1"
        wbs.level = 2
        wbs.description = None
        wbs.is_control_account = False
        wbs.budget_at_completion = Decimal("0.00")

        now = datetime.now(UTC)
        epic_data = JiraEpicData(
            key="PROJ-10",
            id="10010",
            name="1.1 - Design Phase",
            summary="Design Phase",
            description=None,
            status="To Do",
            created=now,
            updated=now,
        )
        service.jira_client.create_epic.return_value = epic_data

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        service.mapping_repo.create.return_value = mock_mapping

        result = await service._create_epic(integration, wbs)

        service.jira_client.create_epic.assert_called_once()
        call_kwargs = service.jira_client.create_epic.call_args[1]
        assert call_kwargs["project_key"] == "PROJ"
        assert call_kwargs["name"] == "1.1 - Design Phase"
        assert call_kwargs["summary"] == "Design Phase"
        assert "defense-pm-tool" in call_kwargs["labels"]

    @pytest.mark.asyncio
    async def test_creates_mapping_record(self, service):
        """Should create JiraMapping record."""
        integration = MagicMock()
        integration.id = uuid4()
        integration.project_key = "PROJ"

        wbs = MagicMock()
        wbs.id = uuid4()
        wbs.wbs_code = "1.1"
        wbs.name = "Design Phase"
        wbs.path = "1.1"
        wbs.level = 2
        wbs.description = None
        wbs.is_control_account = False
        wbs.budget_at_completion = Decimal("0.00")

        now = datetime.now(UTC)
        epic_data = JiraEpicData(
            key="PROJ-10",
            id="10010",
            name="1.1 - Design Phase",
            summary="Design Phase",
            description=None,
            status="To Do",
            created=now,
            updated=now,
        )
        service.jira_client.create_epic.return_value = epic_data

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        service.mapping_repo.create.return_value = mock_mapping

        result = await service._create_epic(integration, wbs)

        assert result is mock_mapping
        service.mapping_repo.create.assert_called_once()


class TestWBSSyncServiceUpdateEpic:
    """Tests for _update_epic method."""

    @pytest.fixture
    def service(self):
        """Create a WBSSyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_wbs_repo = AsyncMock()

        return WBSSyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            wbs_repo=mock_wbs_repo,
        )

    @pytest.mark.asyncio
    async def test_returns_none_for_no_mapping(self, service):
        """Should return None when mapping is None."""
        integration = MagicMock()
        wbs = MagicMock()

        result = await service._update_epic(integration, wbs, None)

        assert result is None

    @pytest.mark.asyncio
    async def test_updates_epic_in_jira(self, service):
        """Should call jira_client.update_issue."""
        integration = MagicMock()
        integration.id = uuid4()
        integration.project_key = "PROJ"
        integration.epic_custom_field = "customfield_10011"

        wbs = MagicMock()
        wbs.id = uuid4()
        wbs.wbs_code = "1.1"
        wbs.name = "Updated Design Phase"
        wbs.path = "1.1"
        wbs.level = 2
        wbs.description = "New description"
        wbs.is_control_account = False
        wbs.budget_at_completion = Decimal("0.00")

        mapping = MagicMock()
        mapping.id = uuid4()
        mapping.jira_issue_key = "PROJ-10"
        mapping.last_synced_at = None

        result = await service._update_epic(integration, wbs, mapping)

        service.jira_client.update_issue.assert_called_once()
        call_kwargs = service.jira_client.update_issue.call_args[1]
        assert call_kwargs["issue_key"] == "PROJ-10"
        assert call_kwargs["summary"] == "Updated Design Phase"

    @pytest.mark.asyncio
    async def test_updates_mapping_timestamp(self, service):
        """Should update mapping's last_synced_at."""
        integration = MagicMock()
        integration.id = uuid4()
        integration.project_key = "PROJ"
        integration.epic_custom_field = None

        wbs = MagicMock()
        wbs.id = uuid4()
        wbs.wbs_code = "1.1"
        wbs.name = "Design Phase"
        wbs.path = "1.1"
        wbs.level = 2
        wbs.description = None
        wbs.is_control_account = False
        wbs.budget_at_completion = Decimal("0.00")

        mapping = MagicMock()
        mapping.id = uuid4()
        mapping.jira_issue_key = "PROJ-10"

        result = await service._update_epic(integration, wbs, mapping)

        service.mapping_repo.update.assert_called_once()
        assert result is mapping


class TestWBSSyncServiceSyncWBSToJira:
    """Tests for sync_wbs_to_jira method."""

    @pytest.fixture
    def service(self):
        """Create a WBSSyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_wbs_repo = AsyncMock()

        return WBSSyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            wbs_repo=mock_wbs_repo,
        )

    @pytest.mark.asyncio
    async def test_raises_for_missing_integration(self, service):
        """Should raise IntegrationNotFoundError."""
        integration_id = uuid4()
        service.integration_repo.get_by_id.return_value = None

        with pytest.raises(IntegrationNotFoundError):
            await service.sync_wbs_to_jira(integration_id)

    @pytest.mark.asyncio
    async def test_raises_for_disabled_sync(self, service):
        """Should raise SyncDisabledError."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.sync_enabled = False
        service.integration_repo.get_by_id.return_value = mock_integration

        with pytest.raises(SyncDisabledError):
            await service.sync_wbs_to_jira(integration_id)

    @pytest.mark.asyncio
    async def test_returns_empty_result_for_no_elements(self, service):
        """Should return empty result when no WBS elements."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.sync_enabled = True
        mock_integration.program_id = uuid4()
        service.integration_repo.get_by_id.return_value = mock_integration
        service.wbs_repo.get_by_program.return_value = []

        result = await service.sync_wbs_to_jira(integration_id)

        assert result.success is True
        assert result.items_synced == 0
        assert result.items_failed == 0

    @pytest.mark.asyncio
    async def test_creates_epics_for_unmapped_wbs(self, service):
        """Should create Epics for unmapped WBS elements."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.program_id = uuid4()
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        wbs = MagicMock()
        wbs.id = uuid4()
        wbs.wbs_code = "1.1"
        wbs.name = "Design"
        wbs.level = 2
        wbs.path = "1.1"
        wbs.description = None
        wbs.is_control_account = False
        wbs.budget_at_completion = Decimal("0.00")
        service.wbs_repo.get_by_program.return_value = [wbs]
        service.mapping_repo.get_by_wbs.return_value = None

        now = datetime.now(UTC)
        epic_data = JiraEpicData(
            key="PROJ-10",
            id="10010",
            name="1.1 - Design",
            summary="Design",
            description=None,
            status="To Do",
            created=now,
            updated=now,
        )
        service.jira_client.create_epic.return_value = epic_data

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        service.mapping_repo.create.return_value = mock_mapping

        result = await service.sync_wbs_to_jira(integration_id)

        assert result.success is True
        assert result.items_synced == 1
        assert len(result.created_mappings) == 1

    @pytest.mark.asyncio
    async def test_logs_sync_operation(self, service):
        """Should create sync log entry when there's something to sync."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.program_id = uuid4()
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        # Add a WBS element so sync actually happens
        wbs = MagicMock()
        wbs.id = uuid4()
        wbs.wbs_code = "1.1"
        wbs.name = "Design"
        wbs.level = 2
        wbs.path = "1.1"
        wbs.description = None
        wbs.is_control_account = False
        wbs.budget_at_completion = Decimal("0.00")
        service.wbs_repo.get_by_program.return_value = [wbs]
        service.mapping_repo.get_by_wbs.return_value = None

        now = datetime.now(UTC)
        epic_data = JiraEpicData(
            key="PROJ-10",
            id="10010",
            name="1.1 - Design",
            summary="Design",
            description=None,
            status="To Do",
            created=now,
            updated=now,
        )
        service.jira_client.create_epic.return_value = epic_data

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        service.mapping_repo.create.return_value = mock_mapping

        await service.sync_wbs_to_jira(integration_id)

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

        # Create two WBS elements
        wbs1 = MagicMock()
        wbs1.id = uuid4()
        wbs1.wbs_code = "1.1"
        wbs1.name = "Design"
        wbs1.level = 2
        wbs1.path = "1.1"
        wbs1.description = None
        wbs1.is_control_account = False
        wbs1.budget_at_completion = Decimal("0.00")

        wbs2 = MagicMock()
        wbs2.id = uuid4()
        wbs2.wbs_code = "1.2"
        wbs2.name = "Build"
        wbs2.level = 2
        wbs2.path = "1.2"
        wbs2.description = None
        wbs2.is_control_account = False
        wbs2.budget_at_completion = Decimal("0.00")

        service.wbs_repo.get_by_program.return_value = [wbs1, wbs2]
        service.mapping_repo.get_by_wbs.return_value = None

        # First succeeds, second fails
        now = datetime.now(UTC)
        epic_data = JiraEpicData(
            key="PROJ-10",
            id="10010",
            name="1.1 - Design",
            summary="Design",
            description=None,
            status="To Do",
            created=now,
            updated=now,
        )
        service.jira_client.create_epic.side_effect = [
            epic_data,
            JiraSyncError("Jira API error"),
        ]

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        service.mapping_repo.create.return_value = mock_mapping

        result = await service.sync_wbs_to_jira(integration_id)

        assert result.success is True  # Partial success
        assert result.items_synced == 1
        assert result.items_failed == 1
        assert len(result.errors) == 1


class TestWBSSyncServicePullFromJira:
    """Tests for pull_from_jira method."""

    @pytest.fixture
    def service(self):
        """Create a WBSSyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_wbs_repo = AsyncMock()

        return WBSSyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            wbs_repo=mock_wbs_repo,
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
    async def test_updates_wbs_from_epic(self, service):
        """Should update WBS when Jira has newer changes."""
        integration_id = uuid4()
        wbs_id = uuid4()

        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.program_id = uuid4()
        service.integration_repo.get_by_id.return_value = mock_integration

        mapping = MagicMock()
        mapping.id = uuid4()
        mapping.wbs_id = wbs_id
        mapping.jira_issue_key = "PROJ-10"
        mapping.sync_direction = "bidirectional"
        mapping.last_jira_updated = datetime(2026, 1, 1, tzinfo=UTC)
        service.mapping_repo.get_by_integration.return_value = [mapping]

        wbs = MagicMock()
        wbs.id = wbs_id
        wbs.wbs_code = "1.1"
        service.wbs_repo.get_by_id.return_value = wbs

        # Jira has newer update
        epic_data = JiraIssueData(
            key="PROJ-10",
            id="10010",
            summary="Updated Epic Name",
            description="New description",
            issue_type="Epic",
            status="In Progress",
            assignee=None,
            created=datetime(2026, 1, 1, tzinfo=UTC),
            updated=datetime(2026, 1, 18, tzinfo=UTC),  # Newer
        )
        service.jira_client.get_issue.return_value = epic_data

        result = await service.pull_from_jira(integration_id)

        assert result.items_synced == 1
        service.wbs_repo.update.assert_called_once()


class TestWBSSyncServiceLogSync:
    """Tests for _log_sync method."""

    @pytest.fixture
    def service(self):
        """Create a WBSSyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_wbs_repo = AsyncMock()

        return WBSSyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            wbs_repo=mock_wbs_repo,
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


class TestWBSSyncServiceUpdateIntegrationSyncTime:
    """Tests for _update_integration_sync_time method."""

    @pytest.fixture
    def service(self):
        """Create a WBSSyncService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()
        mock_wbs_repo = AsyncMock()

        return WBSSyncService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
            wbs_repo=mock_wbs_repo,
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
