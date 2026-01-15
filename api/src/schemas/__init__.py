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
from src.schemas.common import (
    ErrorResponse,
    FieldError,
    HealthResponse,
    MessageResponse,
    PaginatedResponse,
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

# EVMS Period schemas
from src.schemas.evms_period import (
    EVMSPeriodCreate,
    EVMSPeriodDataCreate,
    EVMSPeriodDataResponse,
    EVMSPeriodDataUpdate,
    EVMSPeriodListResponse,
    EVMSPeriodResponse,
    EVMSPeriodUpdate,
    EVMSPeriodWithDataResponse,
    EVMSSummaryResponse,
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

__all__ = [
    "ActivityBriefResponse",
    # Activity
    "ActivityCreate",
    "ActivityProgressUpdate",
    "ActivityResponse",
    "ActivityUpdate",
    "BulkDependencyCreate",
    "CriticalPathResponse",
    "DependencyBriefResponse",
    # Dependency
    "DependencyCreate",
    "DependencyResponse",
    "DependencyUpdate",
    "DependencyValidationResult",
    # EVMS Period
    "EVMSPeriodCreate",
    "EVMSPeriodDataCreate",
    "EVMSPeriodDataResponse",
    "EVMSPeriodDataUpdate",
    "EVMSPeriodListResponse",
    "EVMSPeriodResponse",
    "EVMSPeriodUpdate",
    "EVMSPeriodWithDataResponse",
    "EVMSSummaryResponse",
    "ErrorResponse",
    "FieldError",
    "HealthResponse",
    "MessageResponse",
    # Common
    "PaginatedResponse",
    "ProgramBriefResponse",
    # Program
    "ProgramCreate",
    "ProgramResponse",
    "ProgramStatusUpdate",
    "ProgramSummaryResponse",
    "ProgramUpdate",
    "ScheduleResult",
    "TokenPayload",
    "TokenResponse",
    "UserBriefResponse",
    # User
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserRoleUpdate",
    "UserStatusUpdate",
    "UserUpdate",
    "WBSBriefResponse",
    # WBS
    "WBSCreate",
    "WBSMoveRequest",
    "WBSResponse",
    "WBSSummaryResponse",
    "WBSTreeResponse",
    "WBSUpdate",
    "WBSWithChildrenResponse",
]
