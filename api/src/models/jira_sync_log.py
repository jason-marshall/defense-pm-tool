"""Jira sync log model for audit trail.

Tracks all sync operations for debugging and compliance.
"""

from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.jira_integration import JiraIntegration
    from src.models.jira_mapping import JiraMapping


class SyncType(str, Enum):
    """Type of sync operation."""

    PUSH = "push"  # Defense PM -> Jira
    PULL = "pull"  # Jira -> Defense PM
    WEBHOOK = "webhook"  # Triggered by Jira webhook
    FULL = "full"  # Full bidirectional sync


class SyncStatus(str, Enum):
    """Status of sync operation."""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class JiraSyncLog(Base):
    """
    Audit log for Jira sync operations.

    Tracks:
    - Sync type (push/pull/webhook)
    - Success/failure status
    - Number of items synced
    - Error messages for debugging

    Attributes:
        integration_id: Associated Jira integration
        mapping_id: Specific mapping (if single-entity sync)
        sync_type: Type of sync operation
        status: Success/failure status
        items_synced: Count of synced items
        error_message: Error details if failed
        duration_ms: Sync duration in milliseconds
    """

    __tablename__ = "jira_sync_logs"

    integration_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jira_integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent Jira integration",
    )

    mapping_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jira_mappings.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to specific mapping (if single-entity sync)",
    )

    sync_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type of sync operation (push/pull/webhook/full)",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Sync status (success/failed/partial)",
    )

    items_synced: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of items synced",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if sync failed",
    )

    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Sync duration in milliseconds",
    )

    # Relationships
    integration: Mapped["JiraIntegration"] = relationship(
        "JiraIntegration",
        back_populates="sync_logs",
    )

    mapping: Mapped["JiraMapping | None"] = relationship(
        "JiraMapping",
    )

    def __repr__(self) -> str:
        return f"<JiraSyncLog {self.sync_type} status={self.status}>"
