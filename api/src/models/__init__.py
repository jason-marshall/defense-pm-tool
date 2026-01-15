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
from src.models.base import Base, SoftDeleteMixin
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
from src.models.program import Program

# Import models
from src.models.user import User
from src.models.wbs import LtreeType, WBSElement

__all__ = [
    "Activity",
    "ActivityStatus",
    # Base classes
    "Base",
    "ConstraintType",
    "Dependency",
    "DependencyType",
    "EVMSPeriod",
    "EVMSPeriodData",
    "LtreeType",
    "PeriodStatus",
    "Program",
    "ProgramStatus",
    "SoftDeleteMixin",
    # Models
    "User",
    # Enums
    "UserRole",
    "WBSElement",
]
