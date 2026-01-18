"""Jira mapping model for WBS/Activity to Issue relationships.

Tracks bidirectional mappings between Defense PM Tool entities
and Jira issues/epics.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.activity import Activity
    from src.models.jira_integration import JiraIntegration
    from src.models.wbs import WBSElement


class SyncDirection(str, Enum):
    """Sync direction for mappings."""

    TO_JIRA = "to_jira"  # Push from Defense PM to Jira
    FROM_JIRA = "from_jira"  # Pull from Jira to Defense PM
    BIDIRECTIONAL = "bidirectional"  # Sync both ways


class EntityType(str, Enum):
    """Type of mapped entity."""

    WBS = "wbs"
    ACTIVITY = "activity"


class JiraMapping(Base):
    """
    Mapping between Defense PM entities and Jira issues.

    Supports:
    - WBS -> Epic mappings
    - Activity -> Issue mappings
    - Bidirectional or one-way sync

    Attributes:
        integration_id: Parent Jira integration
        entity_type: Type of Defense PM entity (wbs/activity)
        wbs_id: WBS element ID (if type is wbs)
        activity_id: Activity ID (if type is activity)
        jira_issue_key: Jira issue key (e.g., "PROJ-123")
        jira_issue_id: Jira issue ID (numeric)
        sync_direction: Direction of sync
        last_synced_at: Last successful sync
        last_jira_updated: Last update timestamp from Jira
    """

    __tablename__ = "jira_mappings"
    __table_args__ = (
        # Ensure unique mapping per WBS entity
        UniqueConstraint(
            "integration_id",
            "entity_type",
            "wbs_id",
            name="uq_jira_mapping_wbs",
        ),
        # Ensure unique mapping per Activity entity
        UniqueConstraint(
            "integration_id",
            "entity_type",
            "activity_id",
            name="uq_jira_mapping_activity",
        ),
        # Ensure unique mapping per Jira issue
        UniqueConstraint(
            "integration_id",
            "jira_issue_key",
            name="uq_jira_mapping_issue",
        ),
        {"comment": "Mappings between Defense PM entities and Jira issues"},
    )

    integration_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jira_integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent Jira integration",
    )

    entity_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type of Defense PM entity (wbs/activity)",
    )

    wbs_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("wbs_elements.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="FK to WBS element (if entity_type is wbs)",
    )

    activity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="FK to Activity (if entity_type is activity)",
    )

    jira_issue_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Jira issue key (e.g., PROJ-123)",
    )

    jira_issue_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Jira issue numeric ID",
    )

    sync_direction: Mapped[str] = mapped_column(
        String(20),
        default=SyncDirection.TO_JIRA.value,
        nullable=False,
        comment="Sync direction (to_jira, from_jira, bidirectional)",
    )

    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last successful sync",
    )

    last_jira_updated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last update timestamp from Jira API",
    )

    # Relationships
    integration: Mapped["JiraIntegration"] = relationship(
        "JiraIntegration",
        back_populates="mappings",
    )

    wbs: Mapped["WBSElement | None"] = relationship(
        "WBSElement",
        back_populates="jira_mapping",
    )

    activity: Mapped["Activity | None"] = relationship(
        "Activity",
        back_populates="jira_mapping",
    )

    def __repr__(self) -> str:
        entity = f"wbs={self.wbs_id}" if self.wbs_id else f"activity={self.activity_id}"
        return f"<JiraMapping {entity} -> {self.jira_issue_key}>"
