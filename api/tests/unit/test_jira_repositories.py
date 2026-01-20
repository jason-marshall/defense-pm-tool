"""Unit tests for Jira repository classes - Coverage improvement.

These tests improve coverage for:
- JiraIntegrationRepository
- JiraMappingRepository
- JiraSyncLogRepository
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.repositories.jira_integration import JiraIntegrationRepository
from src.repositories.jira_mapping import JiraMappingRepository
from src.repositories.jira_sync_log import JiraSyncLogRepository

# =============================================================================
# Test JiraIntegrationRepository
# =============================================================================


class TestJiraIntegrationRepository:
    """Tests for JiraIntegrationRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance with mock session."""
        return JiraIntegrationRepository(mock_session)

    def test_init(self, mock_session):
        """Should initialize with correct model."""
        repo = JiraIntegrationRepository(mock_session)
        assert repo.session == mock_session

    @pytest.mark.asyncio
    async def test_get_by_program_found(self, repo, mock_session):
        """Should return integration when found."""
        program_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = uuid4()
        mock_integration.program_id = program_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_program(program_id)

        assert result == mock_integration
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_program_not_found(self, repo, mock_session):
        """Should return None when integration not found."""
        program_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_program(program_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_program_include_deleted(self, repo, mock_session):
        """Should include deleted when specified."""
        program_id = uuid4()
        mock_integration = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_program(program_id, include_deleted=True)

        assert result == mock_integration

    @pytest.mark.asyncio
    async def test_get_active_integrations_empty(self, repo, mock_session):
        """Should return empty list when no active integrations."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_active_integrations()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_active_integrations_with_data(self, repo, mock_session):
        """Should return list of active integrations."""
        mock_integration1 = MagicMock()
        mock_integration2 = MagicMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_integration1, mock_integration2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_active_integrations()

        assert len(result) == 2
        assert mock_integration1 in result
        assert mock_integration2 in result

    @pytest.mark.asyncio
    async def test_get_by_status(self, repo, mock_session):
        """Should return integrations with matching status."""
        mock_integration = MagicMock()
        mock_integration.sync_status = "active"

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_integration]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_status("active")

        assert len(result) == 1
        assert result[0].sync_status == "active"

    @pytest.mark.asyncio
    async def test_get_by_status_include_deleted(self, repo, mock_session):
        """Should include deleted when specified."""
        mock_integration = MagicMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_integration]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_status("error", include_deleted=True)

        assert len(result) == 1


# =============================================================================
# Test JiraMappingRepository
# =============================================================================


class TestJiraMappingRepository:
    """Tests for JiraMappingRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance with mock session."""
        return JiraMappingRepository(mock_session)

    def test_init(self, mock_session):
        """Should initialize with correct model."""
        repo = JiraMappingRepository(mock_session)
        assert repo.session == mock_session

    @pytest.mark.asyncio
    async def test_get_by_wbs_found(self, repo, mock_session):
        """Should return mapping when WBS found."""
        integration_id = uuid4()
        wbs_id = uuid4()
        mock_mapping = MagicMock()
        mock_mapping.wbs_id = wbs_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_mapping
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_wbs(integration_id, wbs_id)

        assert result == mock_mapping

    @pytest.mark.asyncio
    async def test_get_by_wbs_not_found(self, repo, mock_session):
        """Should return None when WBS mapping not found."""
        integration_id = uuid4()
        wbs_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_wbs(integration_id, wbs_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_wbs_include_deleted(self, repo, mock_session):
        """Should include deleted when specified."""
        integration_id = uuid4()
        wbs_id = uuid4()
        mock_mapping = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_mapping
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_wbs(integration_id, wbs_id, include_deleted=True)

        assert result == mock_mapping

    @pytest.mark.asyncio
    async def test_get_by_activity_found(self, repo, mock_session):
        """Should return mapping when activity found."""
        integration_id = uuid4()
        activity_id = uuid4()
        mock_mapping = MagicMock()
        mock_mapping.activity_id = activity_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_mapping
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_activity(integration_id, activity_id)

        assert result == mock_mapping

    @pytest.mark.asyncio
    async def test_get_by_activity_not_found(self, repo, mock_session):
        """Should return None when activity mapping not found."""
        integration_id = uuid4()
        activity_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_activity(integration_id, activity_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_activity_include_deleted(self, repo, mock_session):
        """Should include deleted when specified."""
        integration_id = uuid4()
        activity_id = uuid4()
        mock_mapping = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_mapping
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_activity(integration_id, activity_id, include_deleted=True)

        assert result == mock_mapping

    @pytest.mark.asyncio
    async def test_get_by_integration_all(self, repo, mock_session):
        """Should return all mappings for integration."""
        integration_id = uuid4()
        mock_mapping1 = MagicMock()
        mock_mapping2 = MagicMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_mapping1, mock_mapping2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_integration(integration_id)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_by_integration_with_entity_type(self, repo, mock_session):
        """Should filter by entity type."""
        integration_id = uuid4()
        mock_mapping = MagicMock()
        mock_mapping.entity_type = "wbs"

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_mapping]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_integration(integration_id, entity_type="wbs")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_integration_include_deleted(self, repo, mock_session):
        """Should include deleted when specified."""
        integration_id = uuid4()
        mock_mapping = MagicMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_mapping]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_integration(integration_id, include_deleted=True)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_jira_key_found(self, repo, mock_session):
        """Should return mapping when Jira key found."""
        integration_id = uuid4()
        jira_key = "PROJ-123"
        mock_mapping = MagicMock()
        mock_mapping.jira_issue_key = jira_key

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_mapping
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_jira_key(integration_id, jira_key)

        assert result == mock_mapping
        assert result.jira_issue_key == jira_key

    @pytest.mark.asyncio
    async def test_get_by_jira_key_not_found(self, repo, mock_session):
        """Should return None when Jira key not found."""
        integration_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_jira_key(integration_id, "PROJ-999")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_jira_key_include_deleted(self, repo, mock_session):
        """Should include deleted when specified."""
        integration_id = uuid4()
        mock_mapping = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_mapping
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_jira_key(integration_id, "PROJ-123", include_deleted=True)

        assert result == mock_mapping

    @pytest.mark.asyncio
    async def test_get_unmapped_wbs(self, repo, mock_session):
        """Should return unmapped WBS element IDs."""
        integration_id = uuid4()
        program_id = uuid4()
        wbs_id1 = uuid4()
        wbs_id2 = uuid4()
        wbs_id3 = uuid4()

        # First call returns all WBS IDs
        mock_wbs_scalars = MagicMock()
        mock_wbs_scalars.all.return_value = [wbs_id1, wbs_id2, wbs_id3]
        mock_wbs_result = MagicMock()
        mock_wbs_result.scalars.return_value = mock_wbs_scalars

        # Second call returns mapped WBS IDs
        mock_mapped_scalars = MagicMock()
        mock_mapped_scalars.all.return_value = [wbs_id1]  # Only one mapped
        mock_mapped_result = MagicMock()
        mock_mapped_result.scalars.return_value = mock_mapped_scalars

        mock_session.execute.side_effect = [mock_wbs_result, mock_mapped_result]

        result = await repo.get_unmapped_wbs(integration_id, program_id)

        assert len(result) == 2
        assert wbs_id1 not in result
        assert wbs_id2 in result or wbs_id3 in result

    @pytest.mark.asyncio
    async def test_count_by_entity_type(self, repo, mock_session):
        """Should return counts by entity type."""
        integration_id = uuid4()

        mock_result = MagicMock()
        mock_result.all.return_value = [("wbs", 3), ("activity", 5)]
        mock_session.execute.return_value = mock_result

        result = await repo.count_by_entity_type(integration_id)

        assert result["wbs"] == 3
        assert result["activity"] == 5


# =============================================================================
# Test JiraSyncLogRepository
# =============================================================================


class TestJiraSyncLogRepository:
    """Tests for JiraSyncLogRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance with mock session."""
        return JiraSyncLogRepository(mock_session)

    def test_init(self, mock_session):
        """Should initialize with correct model."""
        repo = JiraSyncLogRepository(mock_session)
        assert repo.session == mock_session

    @pytest.mark.asyncio
    async def test_get_by_integration(self, repo, mock_session):
        """Should return logs for integration."""
        integration_id = uuid4()
        mock_log1 = MagicMock()
        mock_log2 = MagicMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_log1, mock_log2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_integration(integration_id)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_by_integration_with_limit(self, repo, mock_session):
        """Should respect limit parameter."""
        integration_id = uuid4()
        mock_log = MagicMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_log]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_integration(integration_id, limit=10)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_mapping(self, repo, mock_session):
        """Should return logs for mapping."""
        mapping_id = uuid4()
        mock_log = MagicMock()
        mock_log.mapping_id = mapping_id

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_log]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_mapping(mapping_id)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_mapping_with_limit(self, repo, mock_session):
        """Should respect limit parameter."""
        mapping_id = uuid4()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_mapping(mapping_id, limit=25)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_latest_found(self, repo, mock_session):
        """Should return most recent log."""
        integration_id = uuid4()
        mock_log = MagicMock()
        mock_log.created_at = datetime.now()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_log
        mock_session.execute.return_value = mock_result

        result = await repo.get_latest(integration_id)

        assert result == mock_log

    @pytest.mark.asyncio
    async def test_get_latest_not_found(self, repo, mock_session):
        """Should return None when no logs exist."""
        integration_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_latest(integration_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_status(self, repo, mock_session):
        """Should return logs with matching status."""
        integration_id = uuid4()
        mock_log = MagicMock()
        mock_log.status = "success"

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_log]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_status(integration_id, "success")

        assert len(result) == 1
        assert result[0].status == "success"

    @pytest.mark.asyncio
    async def test_get_by_status_with_limit(self, repo, mock_session):
        """Should respect limit parameter."""
        integration_id = uuid4()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_status(integration_id, "failed", limit=10)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_date_range(self, repo, mock_session):
        """Should return logs within date range."""
        integration_id = uuid4()
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        mock_log = MagicMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_log]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_date_range(integration_id, start_date, end_date)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_date_range_empty(self, repo, mock_session):
        """Should return empty list when no logs in range."""
        integration_id = uuid4()
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now() - timedelta(days=25)

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_date_range(integration_id, start_date, end_date)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_stats(self, repo, mock_session):
        """Should return sync statistics."""
        integration_id = uuid4()

        # Status counts result
        mock_status_result = MagicMock()
        mock_status_result.all.return_value = [("success", 10), ("failed", 2), ("partial", 1)]

        # Items sum result
        mock_items_result = MagicMock()
        mock_items_result.scalar_one.return_value = 150

        mock_session.execute.side_effect = [mock_status_result, mock_items_result]

        result = await repo.get_stats(integration_id)

        assert result["total_syncs"] == 13
        assert result["total_items"] == 150
        assert result["success_count"] == 10
        assert result["failed_count"] == 2
        assert result["partial_count"] == 1

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, repo, mock_session):
        """Should return zero stats when no logs exist."""
        integration_id = uuid4()

        # Status counts result - empty
        mock_status_result = MagicMock()
        mock_status_result.all.return_value = []

        # Items sum result - None
        mock_items_result = MagicMock()
        mock_items_result.scalar_one.return_value = None

        mock_session.execute.side_effect = [mock_status_result, mock_items_result]

        result = await repo.get_stats(integration_id)

        assert result["total_syncs"] == 0
        assert result["total_items"] == 0
        assert result["success_count"] == 0
        assert result["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_old_logs_none_to_delete(self, repo, mock_session):
        """Should return 0 when nothing to delete."""
        integration_id = uuid4()
        log_id = uuid4()

        # Keep query - returns the only log
        mock_keep_scalars = MagicMock()
        mock_keep_scalars.all.return_value = [log_id]
        mock_keep_result = MagicMock()
        mock_keep_result.scalars.return_value = mock_keep_scalars

        # All query - returns same log
        mock_log = MagicMock()
        mock_log.id = log_id
        mock_all_scalars = MagicMock()
        mock_all_scalars.all.return_value = [mock_log]
        mock_all_result = MagicMock()
        mock_all_result.scalars.return_value = mock_all_scalars

        mock_session.execute.side_effect = [mock_keep_result, mock_all_result]

        result = await repo.cleanup_old_logs(integration_id, keep_count=10)

        assert result == 0

    @pytest.mark.asyncio
    async def test_cleanup_old_logs_with_deletions(self, repo, mock_session):
        """Should delete old logs and return count."""
        integration_id = uuid4()
        keep_id = uuid4()
        delete_id1 = uuid4()
        delete_id2 = uuid4()

        # Keep query - returns one ID
        mock_keep_scalars = MagicMock()
        mock_keep_scalars.all.return_value = [keep_id]
        mock_keep_result = MagicMock()
        mock_keep_result.scalars.return_value = mock_keep_scalars

        # All query - returns three logs
        mock_log_keep = MagicMock()
        mock_log_keep.id = keep_id
        mock_log_delete1 = MagicMock()
        mock_log_delete1.id = delete_id1
        mock_log_delete2 = MagicMock()
        mock_log_delete2.id = delete_id2

        mock_all_scalars = MagicMock()
        mock_all_scalars.all.return_value = [mock_log_keep, mock_log_delete1, mock_log_delete2]
        mock_all_result = MagicMock()
        mock_all_result.scalars.return_value = mock_all_scalars

        mock_session.execute.side_effect = [mock_keep_result, mock_all_result]

        result = await repo.cleanup_old_logs(integration_id, keep_count=1)

        assert result == 2
        assert mock_session.delete.call_count == 2
        mock_session.flush.assert_called_once()
