"""Unit tests for Jira integration API endpoints."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.v1.endpoints.jira_integration import (
    create_integration,
    create_mapping,
    delete_integration,
    delete_mapping,
    get_integration,
    get_program_integration,
    list_mappings,
    list_sync_logs,
    pull_from_jira,
    sync_activities_to_jira,
    sync_activity_progress,
    sync_wbs_to_jira,
    update_integration,
)

# Alias to avoid pytest collecting the imported function as a test
# (its name starts with "test_" which conflicts with pytest collection)
from src.api.v1.endpoints.jira_integration import (
    test_connection as _test_connection_endpoint,
)
from src.core.exceptions import NotFoundError


def _make_integration_mock(integration_id=None, program_id=None, sync_enabled=True):
    """Create a mock JiraIntegration model."""
    mock = MagicMock()
    mock.id = integration_id or uuid4()
    mock.program_id = program_id or uuid4()
    mock.jira_url = "https://test.atlassian.net"
    mock.project_key = "TEST"
    mock.email = "user@example.com"
    mock.api_token_encrypted = b"encrypted_token_value"
    mock.sync_enabled = sync_enabled
    mock.sync_status = "active"
    mock.last_sync_at = None
    mock.epic_custom_field = None
    mock.created_at = datetime.now(UTC)
    mock.updated_at = None
    return mock


def _make_sync_result(success=True, items_synced=3, items_failed=0):
    """Create a mock SyncResult dataclass."""
    result = MagicMock()
    result.success = success
    result.items_synced = items_synced
    result.items_failed = items_failed
    result.duration_ms = 150
    result.errors = [] if success else ["sync error"]
    result.created_mappings = [uuid4() for _ in range(items_synced)]
    result.updated_mappings = [uuid4() for _ in range(items_synced)]
    return result


class TestCreateIntegration:
    """Tests for create_integration endpoint."""

    @pytest.mark.asyncio
    async def test_create_integration_success(self):
        """Should create a Jira integration when program exists and no duplicate."""
        from src.schemas.jira_integration import JiraIntegrationCreate

        mock_db = AsyncMock()
        program_id = uuid4()
        integration_id = uuid4()

        integration_in = JiraIntegrationCreate(
            program_id=program_id,
            jira_url="https://test.atlassian.net",
            project_key="TEST",
            email="user@example.com",
            api_token="secret-token",
        )

        mock_program = MagicMock()
        mock_program.id = program_id

        mock_integration = _make_integration_mock(
            integration_id=integration_id, program_id=program_id
        )

        with (
            patch("src.api.v1.endpoints.jira_integration.ProgramRepository") as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_int_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.encrypt_token") as mock_encrypt,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationResponse"
            ) as mock_response_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_int_repo = MagicMock()
            mock_int_repo.get_by_program = AsyncMock(return_value=None)
            mock_int_repo.create = AsyncMock(return_value=mock_integration)
            mock_int_repo_cls.return_value = mock_int_repo

            mock_encrypt.return_value = "encrypted_value"

            mock_resp = MagicMock()
            mock_resp.id = integration_id
            mock_resp.program_id = program_id
            mock_response_cls.model_validate.return_value = mock_resp

            result = await create_integration(integration_in, mock_db)

            assert result.id == integration_id
            assert result.program_id == program_id
            mock_db.commit.assert_called_once()
            mock_int_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_integration_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        from src.schemas.jira_integration import JiraIntegrationCreate

        mock_db = AsyncMock()
        program_id = uuid4()

        integration_in = JiraIntegrationCreate(
            program_id=program_id,
            jira_url="https://test.atlassian.net",
            project_key="TEST",
            email="user@example.com",
            api_token="secret-token",
        )

        with patch("src.api.v1.endpoints.jira_integration.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_integration(integration_in, mock_db)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_integration_duplicate(self):
        """Should raise HTTPException 409 when integration already exists for program."""
        from src.schemas.jira_integration import JiraIntegrationCreate

        mock_db = AsyncMock()
        program_id = uuid4()

        integration_in = JiraIntegrationCreate(
            program_id=program_id,
            jira_url="https://test.atlassian.net",
            project_key="TEST",
            email="user@example.com",
            api_token="secret-token",
        )

        mock_program = MagicMock()
        mock_program.id = program_id
        mock_existing = _make_integration_mock(program_id=program_id)

        with (
            patch("src.api.v1.endpoints.jira_integration.ProgramRepository") as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_int_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_int_repo = MagicMock()
            mock_int_repo.get_by_program = AsyncMock(return_value=mock_existing)
            mock_int_repo_cls.return_value = mock_int_repo

            with pytest.raises(HTTPException) as exc_info:
                await create_integration(integration_in, mock_db)

            assert exc_info.value.status_code == 409


class TestGetIntegration:
    """Tests for get_integration endpoint."""

    @pytest.mark.asyncio
    async def test_get_integration_success(self):
        """Should return integration when found."""
        mock_db = AsyncMock()
        integration_id = uuid4()
        mock_integration = _make_integration_mock(integration_id=integration_id)

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_repo_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationResponse"
            ) as mock_response_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_repo_cls.return_value = mock_repo

            mock_resp = MagicMock()
            mock_resp.id = integration_id
            mock_response_cls.model_validate.return_value = mock_resp

            result = await get_integration(integration_id, mock_db)

            assert result.id == integration_id
            mock_repo.get_by_id.assert_called_once_with(integration_id)

    @pytest.mark.asyncio
    async def test_get_integration_not_found(self):
        """Should raise NotFoundError when integration does not exist."""
        mock_db = AsyncMock()
        integration_id = uuid4()

        with patch(
            "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_integration(integration_id, mock_db)

            assert exc_info.value.code == "JIRA_INTEGRATION_NOT_FOUND"


class TestGetProgramIntegration:
    """Tests for get_program_integration endpoint."""

    @pytest.mark.asyncio
    async def test_get_program_integration_success(self):
        """Should return integration for a given program."""
        mock_db = AsyncMock()
        program_id = uuid4()
        mock_integration = _make_integration_mock(program_id=program_id)

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_repo_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationResponse"
            ) as mock_response_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_program = AsyncMock(return_value=mock_integration)
            mock_repo_cls.return_value = mock_repo

            mock_resp = MagicMock()
            mock_resp.program_id = program_id
            mock_response_cls.model_validate.return_value = mock_resp

            result = await get_program_integration(program_id, mock_db)

            assert result.program_id == program_id
            mock_repo.get_by_program.assert_called_once_with(program_id)

    @pytest.mark.asyncio
    async def test_get_program_integration_not_found(self):
        """Should raise NotFoundError when no integration exists for program."""
        mock_db = AsyncMock()
        program_id = uuid4()

        with patch(
            "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_program = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_program_integration(program_id, mock_db)

            assert exc_info.value.code == "JIRA_INTEGRATION_NOT_FOUND"


class TestUpdateIntegration:
    """Tests for update_integration endpoint."""

    @pytest.mark.asyncio
    async def test_update_integration_success(self):
        """Should update integration settings."""
        from src.schemas.jira_integration import JiraIntegrationUpdate

        mock_db = AsyncMock()
        integration_id = uuid4()
        mock_integration = _make_integration_mock(integration_id=integration_id)

        update_in = JiraIntegrationUpdate(sync_enabled=False)

        mock_updated = _make_integration_mock(integration_id=integration_id)
        mock_updated.sync_enabled = False

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_repo_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationResponse"
            ) as mock_response_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_repo.update = AsyncMock(return_value=mock_updated)
            mock_repo_cls.return_value = mock_repo

            mock_resp = MagicMock()
            mock_resp.id = integration_id
            mock_resp.sync_enabled = False
            mock_response_cls.model_validate.return_value = mock_resp

            result = await update_integration(integration_id, update_in, mock_db)

            assert result.id == integration_id
            assert result.sync_enabled is False
            mock_db.commit.assert_called_once()
            mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_integration_not_found(self):
        """Should raise NotFoundError when integration does not exist."""
        from src.schemas.jira_integration import JiraIntegrationUpdate

        mock_db = AsyncMock()
        integration_id = uuid4()
        update_in = JiraIntegrationUpdate(sync_enabled=True)

        with patch(
            "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await update_integration(integration_id, update_in, mock_db)

            assert exc_info.value.code == "JIRA_INTEGRATION_NOT_FOUND"


class TestDeleteIntegration:
    """Tests for delete_integration endpoint."""

    @pytest.mark.asyncio
    async def test_delete_integration_success(self):
        """Should delete integration and commit."""
        mock_db = AsyncMock()
        integration_id = uuid4()
        mock_integration = _make_integration_mock(integration_id=integration_id)

        with patch(
            "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_repo.delete = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            result = await delete_integration(integration_id, mock_db)

            assert result is None
            mock_repo.delete.assert_called_once_with(mock_integration.id)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_integration_not_found(self):
        """Should raise NotFoundError when integration does not exist."""
        mock_db = AsyncMock()
        integration_id = uuid4()

        with patch(
            "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await delete_integration(integration_id, mock_db)

            assert exc_info.value.code == "JIRA_INTEGRATION_NOT_FOUND"
            mock_db.commit.assert_not_called()


class TestTestConnection:
    """Tests for test_connection endpoint."""

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Should return success when Jira connection works."""
        mock_db = AsyncMock()
        iid = uuid4()
        mock_integration = _make_integration_mock(integration_id=iid)

        mock_project_info = MagicMock()
        mock_project_info.name = "Test Project"

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.decrypt_token") as mock_decrypt,
            patch("src.api.v1.endpoints.jira_integration.JiraClient") as mock_client_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_repo_cls.return_value = mock_repo

            mock_decrypt.return_value = "decrypted-token"

            mock_client = MagicMock()
            mock_client.get_project = AsyncMock(return_value=mock_project_info)
            mock_client_cls.return_value = mock_client

            result = await _test_connection_endpoint(iid, mock_db)

            assert result.success is True
            assert result.message == "Connection successful"
            assert result.project_name == "Test Project"

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Should return failure response when Jira connection fails."""
        mock_db = AsyncMock()
        iid = uuid4()
        mock_integration = _make_integration_mock(integration_id=iid)

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.decrypt_token") as mock_decrypt,
            patch("src.api.v1.endpoints.jira_integration.JiraClient") as mock_client_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_repo_cls.return_value = mock_repo

            mock_decrypt.return_value = "decrypted-token"

            mock_client = MagicMock()
            mock_client.get_project = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_cls.return_value = mock_client

            result = await _test_connection_endpoint(iid, mock_db)

            assert result.success is False
            assert "Connection failed" in result.message

    @pytest.mark.asyncio
    async def test_test_connection_integration_not_found(self):
        """Should raise NotFoundError when integration does not exist."""
        mock_db = AsyncMock()
        iid = uuid4()

        with patch(
            "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await _test_connection_endpoint(iid, mock_db)

            assert exc_info.value.code == "JIRA_INTEGRATION_NOT_FOUND"


class TestSyncWBSToJira:
    """Tests for sync_wbs_to_jira endpoint."""

    @pytest.mark.asyncio
    async def test_sync_wbs_success(self):
        """Should sync WBS elements to Jira and return response."""
        from src.schemas.jira_integration import JiraSyncRequest

        mock_db = AsyncMock()
        mock_request = MagicMock()
        integration_id = uuid4()
        mock_integration = _make_integration_mock(integration_id=integration_id)

        wbs_ids = [uuid4(), uuid4()]
        sync_request = JiraSyncRequest(entity_ids=wbs_ids)
        mock_result = _make_sync_result(success=True, items_synced=2)

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_int_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.decrypt_token") as mock_decrypt,
            patch("src.api.v1.endpoints.jira_integration.JiraClient") as mock_client_cls,
            patch("src.api.v1.endpoints.jira_integration.JiraMappingRepository"),
            patch("src.api.v1.endpoints.jira_integration.JiraSyncLogRepository"),
            patch("src.api.v1.endpoints.jira_integration.WBSElementRepository"),
            patch("src.api.v1.endpoints.jira_integration.WBSSyncService") as mock_service_cls,
        ):
            mock_int_repo = MagicMock()
            mock_int_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_int_repo_cls.return_value = mock_int_repo

            mock_decrypt.return_value = "decrypted-token"
            mock_client_cls.return_value = MagicMock()

            mock_service = MagicMock()
            mock_service.sync_wbs_to_jira = AsyncMock(return_value=mock_result)
            mock_service_cls.return_value = mock_service

            result = await sync_wbs_to_jira(mock_request, integration_id, sync_request, mock_db)

            assert result.success is True
            assert result.sync_type == "push"
            assert result.items_synced == 2
            assert result.items_failed == 0
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_wbs_integration_not_found(self):
        """Should raise NotFoundError when integration does not exist."""
        from src.schemas.jira_integration import JiraSyncRequest

        mock_db = AsyncMock()
        mock_request = MagicMock()
        integration_id = uuid4()
        sync_request = JiraSyncRequest(entity_ids=[uuid4()])

        with patch(
            "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await sync_wbs_to_jira(mock_request, integration_id, sync_request, mock_db)

            assert exc_info.value.code == "JIRA_INTEGRATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_sync_wbs_disabled_raises_400(self):
        """Should raise HTTPException 400 when sync is disabled."""
        from src.schemas.jira_integration import JiraSyncRequest
        from src.services.jira_wbs_sync import SyncDisabledError

        mock_db = AsyncMock()
        mock_request = MagicMock()
        integration_id = uuid4()
        mock_integration = _make_integration_mock(integration_id=integration_id)
        sync_request = JiraSyncRequest(entity_ids=[uuid4()])

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_int_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.decrypt_token") as mock_decrypt,
            patch("src.api.v1.endpoints.jira_integration.JiraClient") as mock_client_cls,
            patch("src.api.v1.endpoints.jira_integration.JiraMappingRepository"),
            patch("src.api.v1.endpoints.jira_integration.JiraSyncLogRepository"),
            patch("src.api.v1.endpoints.jira_integration.WBSElementRepository"),
            patch("src.api.v1.endpoints.jira_integration.WBSSyncService") as mock_service_cls,
        ):
            mock_int_repo = MagicMock()
            mock_int_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_int_repo_cls.return_value = mock_int_repo

            mock_decrypt.return_value = "decrypted-token"
            mock_client_cls.return_value = MagicMock()

            mock_service = MagicMock()
            mock_service.sync_wbs_to_jira = AsyncMock(
                side_effect=SyncDisabledError("Sync is disabled")
            )
            mock_service_cls.return_value = mock_service

            with pytest.raises(HTTPException) as exc_info:
                await sync_wbs_to_jira(mock_request, integration_id, sync_request, mock_db)

            assert exc_info.value.status_code == 400


class TestSyncActivitiesToJira:
    """Tests for sync_activities_to_jira endpoint."""

    @pytest.mark.asyncio
    async def test_sync_activities_success(self):
        """Should sync activities to Jira and return response."""
        from src.schemas.jira_integration import JiraSyncRequest

        mock_db = AsyncMock()
        mock_request = MagicMock()
        integration_id = uuid4()
        mock_integration = _make_integration_mock(integration_id=integration_id)

        activity_ids = [uuid4(), uuid4(), uuid4()]
        sync_request = JiraSyncRequest(entity_ids=activity_ids)
        mock_result = _make_sync_result(success=True, items_synced=3)

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_int_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.decrypt_token") as mock_decrypt,
            patch("src.api.v1.endpoints.jira_integration.JiraClient") as mock_client_cls,
            patch("src.api.v1.endpoints.jira_integration.JiraMappingRepository"),
            patch("src.api.v1.endpoints.jira_integration.JiraSyncLogRepository"),
            patch("src.api.v1.endpoints.jira_integration.ActivityRepository"),
            patch("src.api.v1.endpoints.jira_integration.ActivitySyncService") as mock_service_cls,
        ):
            mock_int_repo = MagicMock()
            mock_int_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_int_repo_cls.return_value = mock_int_repo

            mock_decrypt.return_value = "decrypted-token"
            mock_client_cls.return_value = MagicMock()

            mock_service = MagicMock()
            mock_service.sync_activities_to_jira = AsyncMock(return_value=mock_result)
            mock_service_cls.return_value = mock_service

            result = await sync_activities_to_jira(
                mock_request, integration_id, sync_request, mock_db
            )

            assert result.success is True
            assert result.sync_type == "push"
            assert result.items_synced == 3
            assert result.items_failed == 0
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_activities_integration_not_found(self):
        """Should raise NotFoundError when integration does not exist."""
        from src.schemas.jira_integration import JiraSyncRequest

        mock_db = AsyncMock()
        mock_request = MagicMock()
        integration_id = uuid4()
        sync_request = JiraSyncRequest(entity_ids=[uuid4()])

        with patch(
            "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await sync_activities_to_jira(mock_request, integration_id, sync_request, mock_db)

            assert exc_info.value.code == "JIRA_INTEGRATION_NOT_FOUND"


class TestSyncActivityProgress:
    """Tests for sync_activity_progress endpoint."""

    @pytest.mark.asyncio
    async def test_sync_progress_success(self):
        """Should sync progress and return detailed results."""
        from src.schemas.jira_integration import ActivityProgressSyncRequest

        mock_db = AsyncMock()
        mock_request = MagicMock()
        integration_id = uuid4()
        mock_integration = _make_integration_mock(integration_id=integration_id)

        activity_ids = [uuid4()]
        sync_req = ActivityProgressSyncRequest(activity_ids=activity_ids)

        mapping_id = uuid4()
        activity_id = uuid4()
        mock_result = _make_sync_result(success=True, items_synced=1)
        mock_result.updated_mappings = [mapping_id]

        mock_mapping = MagicMock()
        mock_mapping.activity_id = activity_id
        mock_mapping.jira_issue_key = "TEST-42"

        mock_activity = MagicMock()
        mock_activity.id = activity_id
        mock_activity.code = "ACT-001"
        mock_activity.percent_complete = Decimal("75.00")

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_int_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.decrypt_token") as mock_decrypt,
            patch("src.api.v1.endpoints.jira_integration.JiraClient") as mock_client_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraMappingRepository"
            ) as mock_map_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.JiraSyncLogRepository"),
            patch("src.api.v1.endpoints.jira_integration.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.ActivitySyncService") as mock_service_cls,
        ):
            mock_int_repo = MagicMock()
            mock_int_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_int_repo_cls.return_value = mock_int_repo

            mock_decrypt.return_value = "decrypted-token"
            mock_client_cls.return_value = MagicMock()

            mock_map_repo = MagicMock()
            mock_map_repo.get_by_id = AsyncMock(return_value=mock_mapping)
            mock_map_repo_cls.return_value = mock_map_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_activity)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_service = MagicMock()
            mock_service.sync_progress = AsyncMock(return_value=mock_result)
            mock_service_cls.return_value = mock_service

            result = await sync_activity_progress(mock_request, integration_id, sync_req, mock_db)

            assert result.success is True
            assert result.synced_count == 1
            assert result.failed_count == 0
            assert len(result.results) == 1
            assert result.results[0].activity_code == "ACT-001"
            assert result.results[0].jira_issue_key == "TEST-42"
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_progress_integration_not_found(self):
        """Should raise NotFoundError when integration does not exist."""
        from src.schemas.jira_integration import ActivityProgressSyncRequest

        mock_db = AsyncMock()
        mock_request = MagicMock()
        integration_id = uuid4()
        sync_req = ActivityProgressSyncRequest(activity_ids=[uuid4()])

        with patch(
            "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await sync_activity_progress(mock_request, integration_id, sync_req, mock_db)

            assert exc_info.value.code == "JIRA_INTEGRATION_NOT_FOUND"


class TestPullFromJira:
    """Tests for pull_from_jira endpoint."""

    @pytest.mark.asyncio
    async def test_pull_from_jira_success(self):
        """Should pull updates from Jira and return response."""
        from src.schemas.jira_integration import JiraSyncRequest

        mock_db = AsyncMock()
        integration_id = uuid4()
        mock_integration = _make_integration_mock(integration_id=integration_id)

        mapping_ids = [uuid4(), uuid4()]
        sync_request = JiraSyncRequest(entity_ids=mapping_ids)
        mock_result = _make_sync_result(success=True, items_synced=2)

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_int_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.decrypt_token") as mock_decrypt,
            patch("src.api.v1.endpoints.jira_integration.JiraClient") as mock_client_cls,
            patch("src.api.v1.endpoints.jira_integration.JiraMappingRepository"),
            patch("src.api.v1.endpoints.jira_integration.JiraSyncLogRepository"),
            patch("src.api.v1.endpoints.jira_integration.ActivityRepository"),
            patch("src.api.v1.endpoints.jira_integration.ActivitySyncService") as mock_service_cls,
        ):
            mock_int_repo = MagicMock()
            mock_int_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_int_repo_cls.return_value = mock_int_repo

            mock_decrypt.return_value = "decrypted-token"
            mock_client_cls.return_value = MagicMock()

            mock_service = MagicMock()
            mock_service.pull_from_jira = AsyncMock(return_value=mock_result)
            mock_service_cls.return_value = mock_service

            result = await pull_from_jira(integration_id, sync_request, mock_db)

            assert result.success is True
            assert result.sync_type == "pull"
            assert result.items_synced == 2
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_pull_from_jira_integration_not_found(self):
        """Should raise NotFoundError when integration does not exist."""
        from src.schemas.jira_integration import JiraSyncRequest

        mock_db = AsyncMock()
        integration_id = uuid4()
        sync_request = JiraSyncRequest(entity_ids=[uuid4()])

        with patch(
            "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await pull_from_jira(integration_id, sync_request, mock_db)

            assert exc_info.value.code == "JIRA_INTEGRATION_NOT_FOUND"


class TestListMappings:
    """Tests for list_mappings endpoint."""

    @pytest.mark.asyncio
    async def test_list_mappings_success(self):
        """Should return list of mappings for integration."""
        mock_db = AsyncMock()
        integration_id = uuid4()
        now = datetime.now(UTC)

        mock_mapping1 = MagicMock()
        mock_mapping1.id = uuid4()
        mock_mapping1.integration_id = integration_id
        mock_mapping1.entity_type = "wbs"
        mock_mapping1.jira_issue_key = "TEST-1"
        mock_mapping1.created_at = now

        mock_mapping2 = MagicMock()
        mock_mapping2.id = uuid4()
        mock_mapping2.integration_id = integration_id
        mock_mapping2.entity_type = "activity"
        mock_mapping2.jira_issue_key = "TEST-2"
        mock_mapping2.created_at = now

        with (
            patch("src.api.v1.endpoints.jira_integration.JiraMappingRepository") as mock_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.JiraMappingResponse") as mock_response_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_integration = AsyncMock(return_value=[mock_mapping1, mock_mapping2])
            mock_repo_cls.return_value = mock_repo

            mock_resp1 = MagicMock()
            mock_resp1.jira_issue_key = "TEST-1"
            mock_resp2 = MagicMock()
            mock_resp2.jira_issue_key = "TEST-2"
            mock_response_cls.model_validate.side_effect = [mock_resp1, mock_resp2]

            result = await list_mappings(integration_id, mock_db)

            assert len(result) == 2
            mock_repo.get_by_integration.assert_called_once_with(integration_id, entity_type=None)

    @pytest.mark.asyncio
    async def test_list_mappings_with_entity_type_filter(self):
        """Should filter mappings by entity type."""
        from src.schemas.jira_integration import EntityType

        mock_db = AsyncMock()
        integration_id = uuid4()

        mock_mapping = MagicMock()
        mock_mapping.entity_type = "wbs"

        with (
            patch("src.api.v1.endpoints.jira_integration.JiraMappingRepository") as mock_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.JiraMappingResponse") as mock_response_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_integration = AsyncMock(return_value=[mock_mapping])
            mock_repo_cls.return_value = mock_repo

            mock_response_cls.model_validate.return_value = MagicMock()

            result = await list_mappings(integration_id, mock_db, entity_type=EntityType.WBS)

            assert len(result) == 1
            mock_repo.get_by_integration.assert_called_once_with(integration_id, entity_type="wbs")

    @pytest.mark.asyncio
    async def test_list_mappings_empty(self):
        """Should return empty list when no mappings exist."""
        mock_db = AsyncMock()
        integration_id = uuid4()

        with patch("src.api.v1.endpoints.jira_integration.JiraMappingRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_integration = AsyncMock(return_value=[])
            mock_repo_cls.return_value = mock_repo

            result = await list_mappings(integration_id, mock_db)

            assert len(result) == 0


class TestCreateMapping:
    """Tests for create_mapping endpoint."""

    @pytest.mark.asyncio
    async def test_create_wbs_mapping_success(self):
        """Should create mapping for WBS entity type."""
        from src.schemas.jira_integration import (
            EntityType,
            JiraMappingCreate,
            SyncDirection,
        )

        mock_db = AsyncMock()
        integration_id = uuid4()
        wbs_id = uuid4()
        mock_integration = _make_integration_mock(integration_id=integration_id)

        mapping_in = JiraMappingCreate(
            entity_type=EntityType.WBS,
            wbs_id=wbs_id,
            jira_issue_key="TEST-10",
            sync_direction=SyncDirection.TO_JIRA,
        )

        mock_wbs = MagicMock()
        mock_wbs.id = wbs_id

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        mock_mapping.integration_id = integration_id
        mock_mapping.entity_type = "wbs"
        mock_mapping.jira_issue_key = "TEST-10"

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_int_repo_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.WBSElementRepository"
            ) as mock_wbs_repo_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraMappingRepository"
            ) as mock_map_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.JiraMappingResponse") as mock_response_cls,
        ):
            mock_int_repo = MagicMock()
            mock_int_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_int_repo_cls.return_value = mock_int_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get_by_id = AsyncMock(return_value=mock_wbs)
            mock_wbs_repo_cls.return_value = mock_wbs_repo

            mock_map_repo = MagicMock()
            mock_map_repo.create = AsyncMock(return_value=mock_mapping)
            mock_map_repo_cls.return_value = mock_map_repo

            mock_resp = MagicMock()
            mock_resp.jira_issue_key = "TEST-10"
            mock_response_cls.model_validate.return_value = mock_resp

            result = await create_mapping(integration_id, mapping_in, mock_db)

            assert result.jira_issue_key == "TEST-10"
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_activity_mapping_success(self):
        """Should create mapping for Activity entity type."""
        from src.schemas.jira_integration import (
            EntityType,
            JiraMappingCreate,
            SyncDirection,
        )

        mock_db = AsyncMock()
        integration_id = uuid4()
        activity_id = uuid4()
        mock_integration = _make_integration_mock(integration_id=integration_id)

        mapping_in = JiraMappingCreate(
            entity_type=EntityType.ACTIVITY,
            activity_id=activity_id,
            jira_issue_key="TEST-20",
            sync_direction=SyncDirection.BIDIRECTIONAL,
        )

        mock_activity = MagicMock()
        mock_activity.id = activity_id

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        mock_mapping.jira_issue_key = "TEST-20"

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_int_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.ActivityRepository") as mock_act_repo_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraMappingRepository"
            ) as mock_map_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.JiraMappingResponse") as mock_response_cls,
        ):
            mock_int_repo = MagicMock()
            mock_int_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_int_repo_cls.return_value = mock_int_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_activity)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_map_repo = MagicMock()
            mock_map_repo.create = AsyncMock(return_value=mock_mapping)
            mock_map_repo_cls.return_value = mock_map_repo

            mock_resp = MagicMock()
            mock_resp.jira_issue_key = "TEST-20"
            mock_response_cls.model_validate.return_value = mock_resp

            result = await create_mapping(integration_id, mapping_in, mock_db)

            assert result.jira_issue_key == "TEST-20"
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_mapping_integration_not_found(self):
        """Should raise NotFoundError when integration does not exist."""
        from src.schemas.jira_integration import (
            EntityType,
            JiraMappingCreate,
        )

        mock_db = AsyncMock()
        integration_id = uuid4()

        mapping_in = JiraMappingCreate(
            entity_type=EntityType.WBS,
            wbs_id=uuid4(),
            jira_issue_key="TEST-99",
        )

        with patch(
            "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
        ) as mock_int_repo_cls:
            mock_int_repo = MagicMock()
            mock_int_repo.get_by_id = AsyncMock(return_value=None)
            mock_int_repo_cls.return_value = mock_int_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_mapping(integration_id, mapping_in, mock_db)

            assert exc_info.value.code == "JIRA_INTEGRATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_mapping_wbs_entity_not_found(self):
        """Should raise NotFoundError when WBS element does not exist."""
        from src.schemas.jira_integration import (
            EntityType,
            JiraMappingCreate,
        )

        mock_db = AsyncMock()
        integration_id = uuid4()
        wbs_id = uuid4()
        mock_integration = _make_integration_mock(integration_id=integration_id)

        mapping_in = JiraMappingCreate(
            entity_type=EntityType.WBS,
            wbs_id=wbs_id,
            jira_issue_key="TEST-99",
        )

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_int_repo_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.WBSElementRepository"
            ) as mock_wbs_repo_cls,
        ):
            mock_int_repo = MagicMock()
            mock_int_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_int_repo_cls.return_value = mock_int_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get_by_id = AsyncMock(return_value=None)
            mock_wbs_repo_cls.return_value = mock_wbs_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_mapping(integration_id, mapping_in, mock_db)

            assert exc_info.value.code == "WBS_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_mapping_activity_entity_not_found(self):
        """Should raise NotFoundError when Activity does not exist."""
        from src.schemas.jira_integration import (
            EntityType,
            JiraMappingCreate,
        )

        mock_db = AsyncMock()
        integration_id = uuid4()
        activity_id = uuid4()
        mock_integration = _make_integration_mock(integration_id=integration_id)

        mapping_in = JiraMappingCreate(
            entity_type=EntityType.ACTIVITY,
            activity_id=activity_id,
            jira_issue_key="TEST-99",
        )

        with (
            patch(
                "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
            ) as mock_int_repo_cls,
            patch("src.api.v1.endpoints.jira_integration.ActivityRepository") as mock_act_repo_cls,
        ):
            mock_int_repo = MagicMock()
            mock_int_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_int_repo_cls.return_value = mock_int_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=None)
            mock_act_repo_cls.return_value = mock_act_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_mapping(integration_id, mapping_in, mock_db)

            assert exc_info.value.code == "ACTIVITY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_mapping_missing_entity_id(self):
        """Should raise HTTPException 400 when entity ID is missing for entity type."""
        from src.schemas.jira_integration import (
            EntityType,
            JiraMappingCreate,
        )

        mock_db = AsyncMock()
        integration_id = uuid4()
        mock_integration = _make_integration_mock(integration_id=integration_id)

        # WBS type but no wbs_id
        mapping_in = JiraMappingCreate(
            entity_type=EntityType.ACTIVITY,
            wbs_id=None,
            activity_id=None,
            jira_issue_key="TEST-99",
        )

        with patch(
            "src.api.v1.endpoints.jira_integration.JiraIntegrationRepository"
        ) as mock_int_repo_cls:
            mock_int_repo = MagicMock()
            mock_int_repo.get_by_id = AsyncMock(return_value=mock_integration)
            mock_int_repo_cls.return_value = mock_int_repo

            with pytest.raises(HTTPException) as exc_info:
                await create_mapping(integration_id, mapping_in, mock_db)

            assert exc_info.value.status_code == 400
            assert "Entity ID" in exc_info.value.detail


class TestDeleteMapping:
    """Tests for delete_mapping endpoint."""

    @pytest.mark.asyncio
    async def test_delete_mapping_success(self):
        """Should delete mapping and commit."""
        mock_db = AsyncMock()
        mapping_id = uuid4()

        mock_mapping = MagicMock()
        mock_mapping.id = mapping_id

        with patch("src.api.v1.endpoints.jira_integration.JiraMappingRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_mapping)
            mock_repo.delete = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            result = await delete_mapping(mapping_id, mock_db)

            assert result is None
            mock_repo.delete.assert_called_once_with(mapping_id)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_mapping_not_found(self):
        """Should raise NotFoundError when mapping does not exist."""
        mock_db = AsyncMock()
        mapping_id = uuid4()

        with patch("src.api.v1.endpoints.jira_integration.JiraMappingRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(NotFoundError) as exc_info:
                await delete_mapping(mapping_id, mock_db)

            assert exc_info.value.code == "MAPPING_NOT_FOUND"
            mock_db.commit.assert_not_called()


class TestListSyncLogs:
    """Tests for list_sync_logs endpoint."""

    @pytest.mark.asyncio
    async def test_list_sync_logs_success(self):
        """Should return paginated sync logs."""
        mock_db = AsyncMock()
        integration_id = uuid4()

        mock_log1 = MagicMock()
        mock_log2 = MagicMock()

        mock_resp1 = MagicMock()
        mock_resp2 = MagicMock()

        with (
            patch("src.api.v1.endpoints.jira_integration.JiraSyncLogRepository") as mock_repo_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraSyncLogResponse"
            ) as mock_log_response_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraSyncLogListResponse"
            ) as mock_list_response_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_integration = AsyncMock(return_value=[mock_log1, mock_log2])
            mock_repo_cls.return_value = mock_repo

            mock_log_response_cls.model_validate.side_effect = [mock_resp1, mock_resp2]

            mock_result = MagicMock()
            mock_result.total = 2
            mock_result.page = 1
            mock_result.per_page = 20
            mock_result.items = [mock_resp1, mock_resp2]
            mock_list_response_cls.return_value = mock_result

            result = await list_sync_logs(integration_id, mock_db)

            assert result.total == 2
            assert result.page == 1
            assert result.per_page == 20
            assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_list_sync_logs_pagination(self):
        """Should paginate logs correctly with page and per_page."""
        mock_db = AsyncMock()
        integration_id = uuid4()

        # Create 5 mock logs
        mock_logs = [MagicMock() for _ in range(5)]

        with (
            patch("src.api.v1.endpoints.jira_integration.JiraSyncLogRepository") as mock_repo_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraSyncLogResponse"
            ) as mock_log_response_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraSyncLogListResponse"
            ) as mock_list_response_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_integration = AsyncMock(return_value=mock_logs)
            mock_repo_cls.return_value = mock_repo

            # Page 2, per_page 2 -> slices indices 2 and 3
            mock_resp_a = MagicMock()
            mock_resp_b = MagicMock()
            mock_log_response_cls.model_validate.side_effect = [mock_resp_a, mock_resp_b]

            mock_result = MagicMock()
            mock_result.total = 5
            mock_result.page = 2
            mock_result.per_page = 2
            mock_result.items = [mock_resp_a, mock_resp_b]
            mock_list_response_cls.return_value = mock_result

            result = await list_sync_logs(integration_id, mock_db, page=2, per_page=2)

            assert result.total == 5
            assert result.page == 2
            assert result.per_page == 2
            assert len(result.items) == 2

            # Verify the list response was constructed with correct total and page
            call_kwargs = mock_list_response_cls.call_args
            assert call_kwargs.kwargs["total"] == 5
            assert call_kwargs.kwargs["page"] == 2
            assert call_kwargs.kwargs["per_page"] == 2

    @pytest.mark.asyncio
    async def test_list_sync_logs_empty(self):
        """Should return empty list when no sync logs exist."""
        mock_db = AsyncMock()
        integration_id = uuid4()

        with (
            patch("src.api.v1.endpoints.jira_integration.JiraSyncLogRepository") as mock_repo_cls,
            patch(
                "src.api.v1.endpoints.jira_integration.JiraSyncLogListResponse"
            ) as mock_list_response_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_integration = AsyncMock(return_value=[])
            mock_repo_cls.return_value = mock_repo

            mock_result = MagicMock()
            mock_result.total = 0
            mock_result.items = []
            mock_list_response_cls.return_value = mock_result

            result = await list_sync_logs(integration_id, mock_db)

            assert result.total == 0
            assert len(result.items) == 0
