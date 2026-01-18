"""Unit tests for Jira client service.

Tests the JiraClient wrapper with mocked JIRA library responses.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from jira import JIRAError

from src.services.jira_client import (
    JiraAuthenticationError,
    JiraClient,
    JiraConnectionError,
    JiraEpicData,
    JiraIssueData,
    JiraIssueType,
    JiraNotFoundError,
    JiraProjectData,
    JiraRateLimitError,
    JiraSyncError,
)


class TestJiraIssueType:
    """Tests for JiraIssueType enum."""

    def test_issue_types_exist(self):
        """Should have all standard issue types."""
        assert JiraIssueType.EPIC == "Epic"
        assert JiraIssueType.STORY == "Story"
        assert JiraIssueType.TASK == "Task"
        assert JiraIssueType.BUG == "Bug"
        assert JiraIssueType.SUBTASK == "Sub-task"

    def test_issue_type_is_string(self):
        """Issue types should be usable as strings."""
        assert JiraIssueType.TASK.value == "Task"
        assert JiraIssueType.EPIC.value == "Epic"


class TestJiraExceptions:
    """Tests for custom Jira exceptions."""

    def test_jira_sync_error(self):
        """JiraSyncError should store message and optional jira_error."""
        error = JiraSyncError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.jira_error is None

    def test_jira_sync_error_with_jira_error(self):
        """JiraSyncError should store the original JIRAError."""
        jira_error = JIRAError(status_code=500, text="Server error")
        error = JiraSyncError("Wrapped error", jira_error=jira_error)
        assert error.jira_error is jira_error

    def test_jira_connection_error(self):
        """JiraConnectionError should inherit from JiraSyncError."""
        error = JiraConnectionError("Connection failed")
        assert isinstance(error, JiraSyncError)

    def test_jira_authentication_error(self):
        """JiraAuthenticationError should inherit from JiraSyncError."""
        error = JiraAuthenticationError("Auth failed")
        assert isinstance(error, JiraSyncError)

    def test_jira_not_found_error(self):
        """JiraNotFoundError should inherit from JiraSyncError."""
        error = JiraNotFoundError("Resource not found")
        assert isinstance(error, JiraSyncError)

    def test_jira_rate_limit_error(self):
        """JiraRateLimitError should inherit from JiraSyncError."""
        error = JiraRateLimitError("Rate limit exceeded")
        assert isinstance(error, JiraSyncError)


class TestJiraDataClasses:
    """Tests for Jira data classes."""

    def test_jira_issue_data(self):
        """JiraIssueData should hold issue information."""
        now = datetime.now()
        issue = JiraIssueData(
            key="PROJ-123",
            id="10001",
            summary="Test issue",
            description="Description",
            issue_type="Task",
            status="To Do",
            assignee="user-123",
            created=now,
            updated=now,
            epic_key="PROJ-1",
            labels=["test"],
            custom_fields={"field_1": "value"},
        )
        assert issue.key == "PROJ-123"
        assert issue.id == "10001"
        assert issue.summary == "Test issue"
        assert issue.epic_key == "PROJ-1"
        assert issue.labels == ["test"]

    def test_jira_epic_data(self):
        """JiraEpicData should hold epic information."""
        now = datetime.now()
        epic = JiraEpicData(
            key="PROJ-1",
            id="10000",
            name="Epic Name",
            summary="Epic Summary",
            description="Epic description",
            status="In Progress",
            created=now,
            updated=now,
        )
        assert epic.key == "PROJ-1"
        assert epic.name == "Epic Name"

    def test_jira_project_data(self):
        """JiraProjectData should hold project information."""
        project = JiraProjectData(
            key="PROJ",
            id="10000",
            name="Test Project",
        )
        assert project.key == "PROJ"
        assert project.name == "Test Project"


class TestJiraClientInit:
    """Tests for JiraClient initialization."""

    def test_init_stores_config(self):
        """Client should store configuration values."""
        client = JiraClient(
            jira_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="secret-token",
            timeout=60,
        )
        assert client.jira_url == "https://test.atlassian.net"
        assert client.email == "test@example.com"
        assert client._api_token == "secret-token"
        assert client.timeout == 60

    def test_init_strips_trailing_slash(self):
        """Client should strip trailing slash from URL."""
        client = JiraClient(
            jira_url="https://test.atlassian.net/",
            email="test@example.com",
            api_token="token",
        )
        assert client.jira_url == "https://test.atlassian.net"

    def test_init_default_timeout(self):
        """Client should have default timeout of 30 seconds."""
        client = JiraClient(
            jira_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="token",
        )
        assert client.timeout == 30


class TestJiraClientConnection:
    """Tests for JiraClient connection handling."""

    @patch("src.services.jira_client.JIRA")
    def test_get_client_creates_connection(self, mock_jira_class):
        """_get_client should create JIRA instance."""
        mock_jira = MagicMock()
        mock_jira_class.return_value = mock_jira

        client = JiraClient(
            jira_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="token",
        )
        result = client._get_client()

        mock_jira_class.assert_called_once_with(
            server="https://test.atlassian.net",
            basic_auth=("test@example.com", "token"),
            timeout=30,
        )
        assert result is mock_jira

    @patch("src.services.jira_client.JIRA")
    def test_get_client_caches_connection(self, mock_jira_class):
        """_get_client should cache the JIRA instance."""
        mock_jira = MagicMock()
        mock_jira_class.return_value = mock_jira

        client = JiraClient(
            jira_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="token",
        )
        client._get_client()
        client._get_client()

        mock_jira_class.assert_called_once()

    @patch("src.services.jira_client.JIRA")
    def test_get_client_auth_error(self, mock_jira_class):
        """_get_client should raise JiraAuthenticationError on 401."""
        mock_jira_class.side_effect = JIRAError(status_code=401, text="Unauthorized")

        client = JiraClient(
            jira_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="bad-token",
        )

        with pytest.raises(JiraAuthenticationError) as exc:
            client._get_client()
        assert "Authentication failed" in str(exc.value)

    @patch("src.services.jira_client.JIRA")
    def test_get_client_connection_error(self, mock_jira_class):
        """_get_client should raise JiraConnectionError on connection failure."""
        mock_jira_class.side_effect = JIRAError(status_code=503, text="Unavailable")

        client = JiraClient(
            jira_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="token",
        )

        with pytest.raises(JiraConnectionError) as exc:
            client._get_client()
        assert "Failed to connect" in str(exc.value)


class TestJiraClientOperations:
    """Tests for JiraClient operations."""

    @pytest.fixture
    def mock_jira(self):
        """Create a mock JIRA client."""
        return MagicMock()

    @pytest.fixture
    def client(self, mock_jira):
        """Create a JiraClient with mocked JIRA instance."""
        with patch("src.services.jira_client.JIRA", return_value=mock_jira):
            client = JiraClient(
                jira_url="https://test.atlassian.net",
                email="test@example.com",
                api_token="token",
            )
            client._client = mock_jira
            return client

    @pytest.mark.asyncio
    async def test_test_connection_success(self, client, mock_jira):
        """test_connection should return True on success."""
        mock_jira.myself.return_value = {"accountId": "123"}

        result = await client.test_connection()

        assert result is True
        mock_jira.myself.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, client, mock_jira):
        """test_connection should return False on failure."""
        mock_jira.myself.side_effect = JIRAError(status_code=401, text="Unauthorized")

        result = await client.test_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_current_user(self, client, mock_jira):
        """get_current_user should return user info dict."""
        mock_jira.myself.return_value = {
            "accountId": "123",
            "emailAddress": "user@example.com",
            "displayName": "Test User",
        }

        result = await client.get_current_user()

        assert result["accountId"] == "123"
        assert result["emailAddress"] == "user@example.com"
        assert result["displayName"] == "Test User"

    @pytest.mark.asyncio
    async def test_get_project(self, client, mock_jira):
        """get_project should return project data."""
        mock_project = MagicMock()
        mock_project.key = "PROJ"
        mock_project.id = "10000"
        mock_project.name = "Test Project"
        mock_jira.project.return_value = mock_project

        result = await client.get_project("PROJ")

        assert isinstance(result, JiraProjectData)
        assert result.key == "PROJ"
        assert result.name == "Test Project"
        mock_jira.project.assert_called_once_with("PROJ")

    @pytest.mark.asyncio
    async def test_get_projects(self, client, mock_jira):
        """get_projects should return list of project data."""
        mock_proj1 = MagicMock()
        mock_proj1.key = "PROJ1"
        mock_proj1.id = "10000"
        mock_proj1.name = "Project 1"
        mock_proj2 = MagicMock()
        mock_proj2.key = "PROJ2"
        mock_proj2.id = "10001"
        mock_proj2.name = "Project 2"
        mock_jira.projects.return_value = [mock_proj1, mock_proj2]

        result = await client.get_projects()

        assert len(result) == 2
        assert result[0].key == "PROJ1"
        assert result[1].key == "PROJ2"

    @pytest.mark.asyncio
    async def test_create_issue(self, client, mock_jira):
        """create_issue should return created issue data."""
        mock_issue = MagicMock()
        mock_issue.key = "PROJ-123"
        mock_issue.id = "10001"
        mock_issue.fields.status = "To Do"
        mock_issue.fields.created = "2026-01-18T10:00:00.000+0000"
        mock_issue.fields.updated = "2026-01-18T10:00:00.000+0000"
        mock_jira.create_issue.return_value = mock_issue

        result = await client.create_issue(
            project_key="PROJ",
            summary="Test task",
            issue_type="Task",
            description="Task description",
        )

        assert isinstance(result, JiraIssueData)
        assert result.key == "PROJ-123"
        assert result.summary == "Test task"
        mock_jira.create_issue.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_epic(self, client, mock_jira):
        """create_epic should return created epic data."""
        mock_issue = MagicMock()
        mock_issue.key = "PROJ-1"
        mock_issue.id = "10000"
        mock_issue.fields.status = "To Do"
        mock_issue.fields.created = "2026-01-18T10:00:00.000+0000"
        mock_issue.fields.updated = "2026-01-18T10:00:00.000+0000"
        mock_jira.create_issue.return_value = mock_issue

        result = await client.create_epic(
            project_key="PROJ",
            name="Epic Name",
            summary="Epic Summary",
        )

        assert isinstance(result, JiraEpicData)
        assert result.key == "PROJ-1"
        assert result.name == "Epic Name"

    @pytest.mark.asyncio
    async def test_get_issue(self, client, mock_jira):
        """get_issue should return issue data."""
        mock_issue = MagicMock()
        mock_issue.key = "PROJ-123"
        mock_issue.id = "10001"
        mock_issue.fields.summary = "Test issue"
        mock_issue.fields.description = "Description"
        mock_issue.fields.issuetype = "Task"
        mock_issue.fields.status = "In Progress"
        mock_issue.fields.assignee = None
        mock_issue.fields.created = "2026-01-18T10:00:00.000+0000"
        mock_issue.fields.updated = "2026-01-18T10:00:00.000+0000"
        mock_issue.fields.parent = None
        mock_issue.fields.labels = ["label1"]
        mock_jira.issue.return_value = mock_issue

        result = await client.get_issue("PROJ-123")

        assert isinstance(result, JiraIssueData)
        assert result.key == "PROJ-123"
        assert result.summary == "Test issue"
        mock_jira.issue.assert_called_once_with("PROJ-123")

    @pytest.mark.asyncio
    async def test_search_issues(self, client, mock_jira):
        """search_issues should return list of matching issues."""
        mock_issue = MagicMock()
        mock_issue.key = "PROJ-123"
        mock_issue.id = "10001"
        mock_issue.fields.summary = "Test issue"
        mock_issue.fields.description = None
        mock_issue.fields.issuetype = "Task"
        mock_issue.fields.status = "To Do"
        mock_issue.fields.assignee = None
        mock_issue.fields.created = "2026-01-18T10:00:00.000+0000"
        mock_issue.fields.updated = "2026-01-18T10:00:00.000+0000"
        mock_issue.fields.parent = None
        mock_issue.fields.labels = []
        mock_jira.search_issues.return_value = [mock_issue]

        result = await client.search_issues("project = PROJ")

        assert len(result) == 1
        assert result[0].key == "PROJ-123"

    @pytest.mark.asyncio
    async def test_add_comment(self, client, mock_jira):
        """add_comment should return comment ID."""
        mock_comment = MagicMock()
        mock_comment.id = "10050"
        mock_jira.add_comment.return_value = mock_comment

        result = await client.add_comment("PROJ-123", "Test comment")

        assert result == "10050"
        mock_jira.add_comment.assert_called_once_with("PROJ-123", "Test comment")

    @pytest.mark.asyncio
    async def test_get_transitions(self, client, mock_jira):
        """get_transitions should return available transitions."""
        mock_jira.transitions.return_value = [
            {"id": "11", "name": "To Do"},
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ]

        result = await client.get_transitions("PROJ-123")

        assert len(result) == 3
        assert result[0] == {"id": "11", "name": "To Do"}

    @pytest.mark.asyncio
    async def test_transition_issue(self, client, mock_jira):
        """transition_issue should execute the transition."""
        mock_jira.transitions.return_value = [
            {"id": "21", "name": "In Progress"},
        ]

        await client.transition_issue("PROJ-123", "In Progress")

        mock_jira.transition_issue.assert_called_once_with("PROJ-123", "21")

    @pytest.mark.asyncio
    async def test_transition_issue_not_found(self, client, mock_jira):
        """transition_issue should raise error if transition not found."""
        mock_jira.transitions.return_value = [
            {"id": "21", "name": "In Progress"},
        ]

        with pytest.raises(JiraSyncError) as exc:
            await client.transition_issue("PROJ-123", "Unknown Status")
        assert "Transition 'Unknown Status' not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_link_issues(self, client, mock_jira):
        """link_issues should create a link between issues."""
        await client.link_issues("PROJ-1", "PROJ-2", "Blocks")

        mock_jira.create_issue_link.assert_called_once_with("Blocks", "PROJ-1", "PROJ-2")

    def test_close(self, client, mock_jira):
        """close should close the JIRA client connection."""
        client.close()

        mock_jira.close.assert_called_once()
        assert client._client is None


class TestJiraClientRetry:
    """Tests for JiraClient retry logic."""

    @pytest.fixture
    def mock_jira(self):
        """Create a mock JIRA client."""
        return MagicMock()

    @pytest.fixture
    def client(self, mock_jira):
        """Create a JiraClient with mocked JIRA instance."""
        with patch("src.services.jira_client.JIRA", return_value=mock_jira):
            client = JiraClient(
                jira_url="https://test.atlassian.net",
                email="test@example.com",
                api_token="token",
            )
            client._client = mock_jira
            return client

    @pytest.mark.asyncio
    async def test_retry_on_server_error(self, client, mock_jira):
        """Should retry on 5xx server errors."""
        # Fail twice, then succeed
        mock_jira.myself.side_effect = [
            JIRAError(status_code=500, text="Server error"),
            JIRAError(status_code=502, text="Bad gateway"),
            {"accountId": "123"},
        ]

        result = await client.test_connection()

        assert result is True
        assert mock_jira.myself.call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, client, mock_jira):
        """Should fail after max retries exceeded."""
        mock_jira.myself.side_effect = JIRAError(status_code=500, text="Persistent error")

        result = await client.test_connection()

        assert result is False
        assert mock_jira.myself.call_count == 3  # MAX_RETRIES

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self, client, mock_jira):
        """Should not retry on authentication errors."""
        mock_jira.myself.side_effect = JIRAError(status_code=401, text="Unauthorized")

        result = await client.test_connection()

        assert result is False
        mock_jira.myself.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_retry_on_not_found(self, client, mock_jira):
        """Should not retry on 404 errors."""
        mock_jira.issue.side_effect = JIRAError(status_code=404, text="Not found")

        with pytest.raises(JiraNotFoundError):
            await client.get_issue("PROJ-999")

        mock_jira.issue.assert_called_once()


class TestJiraClientDateParsing:
    """Tests for JiraClient date parsing."""

    def test_parse_datetime_with_timezone(self):
        """Should parse datetime with timezone offset."""
        client = JiraClient(
            jira_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="token",
        )
        result = client._parse_datetime("2026-01-18T10:30:00.000+0000")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 18

    def test_parse_datetime_with_z_suffix(self):
        """Should parse datetime with Z suffix."""
        client = JiraClient(
            jira_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="token",
        )
        result = client._parse_datetime("2026-01-18T10:30:00Z")
        assert result.year == 2026
        assert result.month == 1

    def test_parse_datetime_without_microseconds(self):
        """Should parse datetime without microseconds."""
        client = JiraClient(
            jira_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="token",
        )
        result = client._parse_datetime("2026-01-18T10:30:00+00:00")
        assert result.year == 2026
