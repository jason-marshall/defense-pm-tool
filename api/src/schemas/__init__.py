"""Pydantic schemas for API request/response validation.

This module exports all Pydantic schemas used for:
- Request validation (Create, Update schemas)
- Response serialization (Response schemas)
- Generic pagination and error handling

Schema Categories:
- Common: PaginatedResponse, ErrorResponse, HealthResponse
- User: Authentication and user management
- Program: Program/project management
- WBS: Work Breakdown Structure hierarchy
- Activity: CPM scheduling activities
- Dependency: Activity dependencies
"""

# Common schemas
from src.schemas.common import (
    ErrorResponse,
    FieldError,
    HealthResponse,
    MessageResponse,
    PaginatedResponse,
)

# User schemas
from src.schemas.user import (
    TokenPayload,
    TokenResponse,
    UserBriefResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserRoleUpdate,
    UserStatusUpdate,
    UserUpdate,
)

# Program schemas
from src.schemas.program import (
    ProgramBriefResponse,
    ProgramCreate,
    ProgramResponse,
    ProgramStatusUpdate,
    ProgramSummaryResponse,
    ProgramUpdate,
)

# WBS schemas
from src.schemas.wbs import (
    WBSBriefResponse,
    WBSCreate,
    WBSMoveRequest,
    WBSResponse,
    WBSSummaryResponse,
    WBSTreeResponse,
    WBSUpdate,
    WBSWithChildrenResponse,
)

# Activity schemas
from src.schemas.activity import (
    ActivityBriefResponse,
    ActivityCreate,
    ActivityProgressUpdate,
    ActivityResponse,
    ActivityUpdate,
    CriticalPathResponse,
    ScheduleResult,
)

# Dependency schemas
from src.schemas.dependency import (
    BulkDependencyCreate,
    DependencyBriefResponse,
    DependencyCreate,
    DependencyResponse,
    DependencyUpdate,
    DependencyValidationResult,
)

__all__ = [
    # Common
    "PaginatedResponse",
    "ErrorResponse",
    "FieldError",
    "HealthResponse",
    "MessageResponse",
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserBriefResponse",
    "UserRoleUpdate",
    "UserStatusUpdate",
    "UserLogin",
    "TokenResponse",
    "TokenPayload",
    # Program
    "ProgramCreate",
    "ProgramUpdate",
    "ProgramResponse",
    "ProgramBriefResponse",
    "ProgramStatusUpdate",
    "ProgramSummaryResponse",
    # WBS
    "WBSCreate",
    "WBSUpdate",
    "WBSResponse",
    "WBSBriefResponse",
    "WBSMoveRequest",
    "WBSTreeResponse",
    "WBSWithChildrenResponse",
    "WBSSummaryResponse",
    # Activity
    "ActivityCreate",
    "ActivityUpdate",
    "ActivityResponse",
    "ActivityBriefResponse",
    "ActivityProgressUpdate",
    "ScheduleResult",
    "CriticalPathResponse",
    # Dependency
    "DependencyCreate",
    "DependencyUpdate",
    "DependencyResponse",
    "DependencyBriefResponse",
    "BulkDependencyCreate",
    "DependencyValidationResult",
]
