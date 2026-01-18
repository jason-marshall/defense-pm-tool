"""Jira REST API client wrapper.

Provides a robust interface to Jira Cloud REST API with:
- Secure token handling
- Retry logic for transient failures
- Structured error handling
- Logging for audit trail

Usage:
    client = JiraClient(
        jira_url="https://yourcompany.atlassian.net",
        email="user@company.com",
        api_token="token"
    )
    issue = await client.create_issue(
        project_key="PROJ",
        summary="Task from Defense PM Tool",
        issue_type="Task"
    )
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog
from jira import JIRA, JIRAError

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger(__name__)


class JiraIssueType(str, Enum):
    """Standard Jira issue types."""

    EPIC = "Epic"
    STORY = "Story"
    TASK = "Task"
    BUG = "Bug"
    SUBTASK = "Sub-task"


class JiraSyncError(Exception):
    """Base exception for Jira sync errors."""

    def __init__(self, message: str, jira_error: JIRAError | None = None):
        self.message = message
        self.jira_error = jira_error
        super().__init__(message)


class JiraConnectionError(JiraSyncError):
    """Connection to Jira failed."""

    pass


class JiraAuthenticationError(JiraSyncError):
    """Authentication with Jira failed."""

    pass


class JiraNotFoundError(JiraSyncError):
    """Requested Jira resource not found."""

    pass


class JiraRateLimitError(JiraSyncError):
    """Rate limit exceeded."""

    pass


@dataclass
class JiraIssueData:
    """Data structure for Jira issue."""

    key: str
    id: str
    summary: str
    description: str | None
    issue_type: str
    status: str
    assignee: str | None
    created: datetime
    updated: datetime
    epic_key: str | None = None
    labels: list[str] | None = None
    custom_fields: dict[str, Any] | None = None


@dataclass
class JiraEpicData:
    """Data structure for Jira epic."""

    key: str
    id: str
    name: str
    summary: str
    description: str | None
    status: str
    created: datetime
    updated: datetime


@dataclass
class JiraProjectData:
    """Data structure for Jira project."""

    key: str
    id: str
    name: str


class JiraClient:
    """
    Async-friendly Jira REST API client.

    Wraps the jira library with:
    - Connection pooling
    - Retry logic (3 attempts with exponential backoff)
    - Structured logging
    - Type-safe return values
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds

    def __init__(
        self,
        jira_url: str,
        email: str,
        api_token: str,
        timeout: int = 30,
    ) -> None:
        """Initialize Jira client.

        Args:
            jira_url: Jira Cloud URL (e.g., https://company.atlassian.net)
            email: User email for authentication
            api_token: Jira API token
            timeout: Request timeout in seconds
        """
        self.jira_url = jira_url.rstrip("/")
        self.email = email
        self._api_token = api_token
        self.timeout = timeout
        self._client: JIRA | None = None

    def _get_client(self) -> JIRA:
        """Get or create Jira client instance."""
        if self._client is None:
            try:
                self._client = JIRA(
                    server=self.jira_url,
                    basic_auth=(self.email, self._api_token),
                    timeout=self.timeout,
                )
                logger.info("jira_client_connected", url=self.jira_url)
            except JIRAError as e:
                if e.status_code == 401:
                    raise JiraAuthenticationError(
                        f"Authentication failed for {self.email}", jira_error=e
                    ) from e
                raise JiraConnectionError(
                    f"Failed to connect to {self.jira_url}", jira_error=e
                ) from e
        return self._client

    async def _retry_operation(
        self, operation: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute operation with retry logic."""
        last_error: JIRAError | None = None

        for attempt in range(self.MAX_RETRIES):
            try:
                # Run synchronous jira library in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: operation(*args, **kwargs))
                return result
            except JIRAError as e:
                last_error = e
                if e.status_code == 401:
                    raise JiraAuthenticationError("Authentication failed", jira_error=e) from e
                if e.status_code == 404:
                    raise JiraNotFoundError(f"Resource not found: {e.text}", jira_error=e) from e
                if e.status_code == 429:
                    # Rate limit - retry with longer delay
                    delay = self.RETRY_DELAY * (2 ** (attempt + 1))
                    logger.warning(
                        "jira_rate_limit",
                        attempt=attempt + 1,
                        delay=delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                if e.status_code is not None and e.status_code >= 500:
                    # Server error - retry
                    delay = self.RETRY_DELAY * (2**attempt)
                    logger.warning(
                        "jira_retry",
                        attempt=attempt + 1,
                        delay=delay,
                        status_code=e.status_code,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise JiraSyncError(f"Jira API error: {e.text}", jira_error=e) from e
            except Exception as e:
                raise JiraSyncError(f"Unexpected error: {e!s}") from e

        raise JiraSyncError(f"Max retries ({self.MAX_RETRIES}) exceeded", jira_error=last_error)

    async def test_connection(self) -> bool:
        """Test Jira connection and authentication."""
        try:
            client = self._get_client()
            await self._retry_operation(client.myself)
            return True
        except JiraSyncError:
            return False

    async def get_current_user(self) -> dict[str, Any]:
        """Get current authenticated user info."""
        client = self._get_client()
        user = await self._retry_operation(client.myself)
        return {
            "accountId": user.get("accountId"),
            "emailAddress": user.get("emailAddress"),
            "displayName": user.get("displayName"),
        }

    async def get_project(self, project_key: str) -> JiraProjectData:
        """Get Jira project details."""
        client = self._get_client()
        project = await self._retry_operation(client.project, project_key)
        return JiraProjectData(
            key=project.key,
            id=project.id,
            name=project.name,
        )

    async def get_projects(self) -> list[JiraProjectData]:
        """Get all accessible Jira projects."""
        client = self._get_client()
        projects = await self._retry_operation(client.projects)
        return [
            JiraProjectData(
                key=p.key,
                id=p.id,
                name=p.name,
            )
            for p in projects
        ]

    async def create_epic(
        self,
        project_key: str,
        name: str,
        summary: str,
        description: str | None = None,
        labels: list[str] | None = None,
    ) -> JiraEpicData:
        """Create a Jira Epic.

        Args:
            project_key: Jira project key
            name: Epic name (displayed on board)
            summary: Epic summary
            description: Optional detailed description
            labels: Optional labels to apply

        Returns:
            JiraEpicData with created epic details
        """
        client = self._get_client()

        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": "Epic"},
            "customfield_10011": name,  # Epic Name field (may vary by instance)
        }

        if description:
            fields["description"] = description
        if labels:
            fields["labels"] = labels

        issue = await self._retry_operation(client.create_issue, fields=fields)

        logger.info(
            "jira_epic_created",
            key=issue.key,
            project=project_key,
            name=name,
        )

        return JiraEpicData(
            key=issue.key,
            id=issue.id,
            name=name,
            summary=summary,
            description=description,
            status=str(issue.fields.status),
            created=self._parse_datetime(issue.fields.created),
            updated=self._parse_datetime(issue.fields.updated),
        )

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        description: str | None = None,
        epic_key: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
        custom_fields: dict[str, Any] | None = None,
    ) -> JiraIssueData:
        """Create a Jira issue.

        Args:
            project_key: Jira project key
            summary: Issue summary
            issue_type: Issue type (Task, Story, Bug, etc.)
            description: Optional detailed description
            epic_key: Optional parent epic key
            assignee: Optional assignee account ID
            labels: Optional labels to apply
            custom_fields: Optional custom field values

        Returns:
            JiraIssueData with created issue details
        """
        client = self._get_client()

        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }

        if description:
            fields["description"] = description
        if epic_key:
            fields["parent"] = {"key": epic_key}  # For next-gen projects
            # For classic projects: fields["customfield_10014"] = epic_key
        if assignee:
            fields["assignee"] = {"accountId": assignee}
        if labels:
            fields["labels"] = labels
        if custom_fields:
            fields.update(custom_fields)

        issue = await self._retry_operation(client.create_issue, fields=fields)

        logger.info(
            "jira_issue_created",
            key=issue.key,
            project=project_key,
            type=issue_type,
        )

        return JiraIssueData(
            key=issue.key,
            id=issue.id,
            summary=summary,
            description=description,
            issue_type=issue_type,
            status=str(issue.fields.status),
            assignee=assignee,
            created=self._parse_datetime(issue.fields.created),
            updated=self._parse_datetime(issue.fields.updated),
            epic_key=epic_key,
            labels=labels,
            custom_fields=custom_fields,
        )

    async def update_issue(
        self,
        issue_key: str,
        summary: str | None = None,
        description: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
        custom_fields: dict[str, Any] | None = None,
    ) -> JiraIssueData:
        """Update an existing Jira issue."""
        client = self._get_client()

        fields: dict[str, Any] = {}
        if summary is not None:
            fields["summary"] = summary
        if description is not None:
            fields["description"] = description
        if assignee is not None:
            fields["assignee"] = {"accountId": assignee} if assignee else None
        if labels is not None:
            fields["labels"] = labels
        if custom_fields:
            fields.update(custom_fields)

        if fields:
            issue = await self._retry_operation(client.issue, issue_key)
            await self._retry_operation(issue.update, fields=fields)

        # Fetch updated issue
        issue = await self._retry_operation(client.issue, issue_key)

        logger.info("jira_issue_updated", key=issue_key, fields=list(fields.keys()))

        return self._parse_issue(issue)

    async def get_issue(self, issue_key: str) -> JiraIssueData:
        """Get a Jira issue by key."""
        client = self._get_client()
        issue = await self._retry_operation(client.issue, issue_key)
        return self._parse_issue(issue)

    async def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        fields: list[str] | None = None,
    ) -> list[JiraIssueData]:
        """Search issues using JQL.

        Args:
            jql: JQL query string
            max_results: Maximum number of results to return
            fields: Optional list of fields to return

        Returns:
            List of matching issues
        """
        client = self._get_client()
        kwargs: dict[str, Any] = {"maxResults": max_results}
        if fields:
            kwargs["fields"] = ",".join(fields)

        issues = await self._retry_operation(
            client.search_issues,
            jql,
            **kwargs,
        )
        return [self._parse_issue(issue) for issue in issues]

    async def add_comment(
        self,
        issue_key: str,
        body: str,
    ) -> str:
        """Add a comment to an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            body: Comment text

        Returns:
            Comment ID
        """
        client = self._get_client()
        comment = await self._retry_operation(
            client.add_comment,
            issue_key,
            body,
        )
        logger.info("jira_comment_added", key=issue_key, comment_id=comment.id)
        return str(comment.id)

    async def get_transitions(self, issue_key: str) -> list[dict[str, str]]:
        """Get available transitions for an issue.

        Args:
            issue_key: Issue key

        Returns:
            List of transitions with id and name
        """
        client = self._get_client()
        transitions = await self._retry_operation(client.transitions, issue_key)
        return [{"id": t["id"], "name": t["name"]} for t in transitions]

    async def transition_issue(
        self,
        issue_key: str,
        transition_name: str,
    ) -> None:
        """Transition issue to a new status.

        Args:
            issue_key: Issue key
            transition_name: Name of the transition to execute

        Raises:
            JiraSyncError: If transition not found or fails
        """
        client = self._get_client()

        # Get available transitions
        transitions = await self._retry_operation(client.transitions, issue_key)

        # Find matching transition
        transition_id = None
        for t in transitions:
            if t["name"].lower() == transition_name.lower():
                transition_id = t["id"]
                break

        if transition_id is None:
            available = [t["name"] for t in transitions]
            raise JiraSyncError(f"Transition '{transition_name}' not found. Available: {available}")

        await self._retry_operation(
            client.transition_issue,
            issue_key,
            transition_id,
        )
        logger.info(
            "jira_issue_transitioned",
            key=issue_key,
            transition=transition_name,
        )

    async def link_issues(
        self,
        inward_issue: str,
        outward_issue: str,
        link_type: str = "Relates",
    ) -> None:
        """Create a link between two issues.

        Args:
            inward_issue: Issue key for inward link
            outward_issue: Issue key for outward link
            link_type: Link type name (e.g., "Relates", "Blocks", "Clones")
        """
        client = self._get_client()
        await self._retry_operation(
            client.create_issue_link,
            link_type,
            inward_issue,
            outward_issue,
        )
        logger.info(
            "jira_issues_linked",
            inward=inward_issue,
            outward=outward_issue,
            type=link_type,
        )

    def _parse_datetime(self, date_str: str) -> datetime:
        """Parse Jira datetime string to Python datetime."""
        # Handle both formats: with and without microseconds
        date_str = date_str.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            # Try without microseconds
            if "." in date_str:
                date_str = date_str.split(".")[0] + "+00:00"
            return datetime.fromisoformat(date_str)

    def _parse_issue(self, issue: Any) -> JiraIssueData:
        """Parse Jira issue object to data class."""
        fields = issue.fields

        # Handle epic key for different project types
        epic_key = None
        if hasattr(fields, "parent") and fields.parent:
            epic_key = fields.parent.key
        elif hasattr(fields, "customfield_10014") and fields.customfield_10014:
            epic_key = fields.customfield_10014

        return JiraIssueData(
            key=issue.key,
            id=issue.id,
            summary=fields.summary,
            description=getattr(fields, "description", None),
            issue_type=str(fields.issuetype),
            status=str(fields.status),
            assignee=(getattr(fields.assignee, "accountId", None) if fields.assignee else None),
            created=self._parse_datetime(fields.created),
            updated=self._parse_datetime(fields.updated),
            epic_key=epic_key,
            labels=getattr(fields, "labels", []),
        )

    def close(self) -> None:
        """Close the Jira client connection."""
        if self._client is not None:
            self._client.close()  # type: ignore[no-untyped-call]
            self._client = None
            logger.info("jira_client_closed", url=self.jira_url)
