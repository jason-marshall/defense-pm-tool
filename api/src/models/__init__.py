"""SQLAlchemy models for Defense PM Tool.

This module exports all SQLAlchemy models and related enums for the
defense program management application.

Models:
    - Base: Base class with common fields (id, timestamps, soft delete)
    - User: User accounts for authentication and authorization
    - Program: Defense programs/projects
    - WBSElement: Work Breakdown Structure elements with ltree hierarchy
    - Activity: Schedulable activities with CPM support
    - Dependency: Activity dependencies for CPM calculations

Enums (from src.models.enums):
    - UserRole: Role-based access control levels
    - ProgramStatus: Program lifecycle status
    - ConstraintType: Activity scheduling constraint types
    - DependencyType: Types of dependencies (FS, SS, FF, SF)
    - ActivityStatus: Activity execution status
"""

from src.models.activity import Activity
from src.models.api_key import APIKey
from src.models.base import Base, SoftDeleteMixin
from src.models.calendar_template import CalendarTemplate, CalendarTemplateHoliday
from src.models.dependency import Dependency

# Import enums from centralized location
from src.models.enums import (
    ActivityStatus,
    ConstraintType,
    DependencyType,
    ProgramStatus,
    UserRole,
)
from src.models.evms_period import EVMSPeriod, EVMSPeriodData, PeriodStatus

# Week 10: Jira integration models
from src.models.jira_integration import JiraIntegration, JiraIntegrationStatus
from src.models.jira_mapping import EntityType, JiraMapping, SyncDirection
from src.models.jira_sync_log import JiraSyncLog, SyncStatus, SyncType
from src.models.management_reserve_log import ManagementReserveLog
from src.models.program import Program
from src.models.report_audit import ReportAudit

# Week 14: Resource models
from src.models.resource import Resource, ResourceAssignment, ResourceCalendar

# Week 17: Resource cost tracking
from src.models.resource_cost import ResourceCostEntry

# Week 20: Resource pools for cross-program sharing
from src.models.resource_pool import (
    PoolAccessLevel,
    ResourcePool,
    ResourcePoolAccess,
    ResourcePoolMember,
)

# Import models
from src.models.user import User
from src.models.variance_explanation import VarianceExplanation
from src.models.wbs import LtreeType, WBSElement

__all__ = [
    "Activity",
    "ActivityStatus",
    "APIKey",
    # Base classes
    "Base",
    # Week 18: Calendar templates
    "CalendarTemplate",
    "CalendarTemplateHoliday",
    "ConstraintType",
    "Dependency",
    "DependencyType",
    # Week 10: Jira integration
    "EntityType",
    "EVMSPeriod",
    "EVMSPeriodData",
    "JiraIntegration",
    "JiraIntegrationStatus",
    "JiraMapping",
    "JiraSyncLog",
    "LtreeType",
    "ManagementReserveLog",
    "PeriodStatus",
    "Program",
    "ProgramStatus",
    "ReportAudit",
    # Week 14: Resource models
    "Resource",
    "ResourceAssignment",
    "ResourceCalendar",
    # Week 17: Resource cost tracking
    "ResourceCostEntry",
    # Week 20: Resource pools
    "ResourcePool",
    "ResourcePoolAccess",
    "ResourcePoolMember",
    "PoolAccessLevel",
    "SoftDeleteMixin",
    "SyncDirection",
    "SyncStatus",
    "SyncType",
    # Models
    "User",
    # Enums
    "UserRole",
    "VarianceExplanation",
    "WBSElement",
]
