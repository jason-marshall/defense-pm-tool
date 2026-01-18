"""Jira integration model for storing connection configurations.

Stores encrypted API tokens and tracks sync status per program.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.jira_mapping import JiraMapping
    from src.models.jira_sync_log import JiraSyncLog
    from src.models.program import Program


class JiraIntegrationStatus:
    """Sync status values."""

    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class JiraIntegration(Base):
    """
    Jira integration configuration for a program.

    Stores connection details and sync settings.
    API tokens are encrypted at rest.

    Attributes:
        program_id: Associated program
        jira_url: Jira Cloud URL
        project_key: Target Jira project
        email: User email for auth
        api_token_encrypted: Encrypted API token
        sync_enabled: Whether sync is active
        last_sync_at: Last successful sync timestamp
        sync_status: Current sync status
        epic_custom_field: Custom field ID for epic name
    """

    __tablename__ = "jira_integrations"

    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="FK to parent program",
    )

    jira_url: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Jira Cloud URL (e.g., https://company.atlassian.net)",
    )

    project_key: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Target Jira project key",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User email for Jira authentication",
    )

    api_token_encrypted: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
        comment="Encrypted Jira API token",
    )

    sync_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether bidirectional sync is active",
    )

    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last successful sync",
    )

    sync_status: Mapped[str] = mapped_column(
        String(20),
        default=JiraIntegrationStatus.ACTIVE,
        nullable=False,
        comment="Current sync status (active, paused, error, disconnected)",
    )

    epic_custom_field: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Custom field ID for Epic Name (varies by Jira instance)",
    )

    # Relationships
    program: Mapped["Program"] = relationship(
        "Program",
        back_populates="jira_integration",
    )

    mappings: Mapped[list["JiraMapping"]] = relationship(
        "JiraMapping",
        back_populates="integration",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    sync_logs: Mapped[list["JiraSyncLog"]] = relationship(
        "JiraSyncLog",
        back_populates="integration",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="JiraSyncLog.created_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<JiraIntegration program={self.program_id} project={self.project_key}>"
