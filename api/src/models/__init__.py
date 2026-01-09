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

Enums:
    - UserRole: Role-based access control levels
    - ProgramStatus: Program lifecycle status
    - ConstraintType: Activity scheduling constraint types
    - DependencyType: Types of dependencies (FS, SS, FF, SF)
"""

from src.models.base import Base, SoftDeleteMixin
from src.models.user import User, UserRole
from src.models.program import Program, ProgramStatus
from src.models.wbs import WBSElement, LtreeType
from src.models.activity import Activity, ConstraintType
from src.models.dependency import Dependency, DependencyType

__all__ = [
    # Base classes
    "Base",
    "SoftDeleteMixin",
    # User model and enums
    "User",
    "UserRole",
    # Program model and enums
    "Program",
    "ProgramStatus",
    # WBS model and types
    "WBSElement",
    "LtreeType",
    # Activity model and enums
    "Activity",
    "ConstraintType",
    # Dependency model and enums
    "Dependency",
    "DependencyType",
]
