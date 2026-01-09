"""Core module with shared utilities."""

from src.core.database import (
    dispose_engine,
    get_db,
    get_engine,
    get_session_maker,
    init_engine,
)
from src.core.deps import DbSession
from src.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    CircularDependencyError,
    ConflictError,
    DomainError,
    NotFoundError,
    ScheduleCalculationError,
    ValidationError,
)

__all__ = [
    # Database
    "dispose_engine",
    "get_db",
    "get_engine",
    "get_session_maker",
    "init_engine",
    # Dependencies
    "DbSession",
    # Exceptions
    "AuthenticationError",
    "AuthorizationError",
    "CircularDependencyError",
    "ConflictError",
    "DomainError",
    "NotFoundError",
    "ScheduleCalculationError",
    "ValidationError",
]
