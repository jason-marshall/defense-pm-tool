"""Domain-specific exceptions."""

from uuid import UUID


class DomainError(Exception):
    """Base class for all domain errors."""

    def __init__(self, message: str, code: str) -> None:
        """
        Initialize domain error.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
        """
        self.message = message
        self.code = code
        super().__init__(message)


class ValidationError(DomainError):
    """Invalid input data."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR") -> None:
        """Initialize validation error."""
        super().__init__(message, code)


class NotFoundError(DomainError):
    """Resource not found."""

    def __init__(self, message: str, code: str = "NOT_FOUND") -> None:
        """Initialize not found error."""
        super().__init__(message, code)


class ConflictError(DomainError):
    """Resource conflict (duplicate, etc.)."""

    def __init__(self, message: str, code: str = "CONFLICT") -> None:
        """Initialize conflict error."""
        super().__init__(message, code)


class CircularDependencyError(DomainError):
    """Circular dependency detected in schedule."""

    def __init__(self, cycle_path: list[UUID]) -> None:
        """
        Initialize circular dependency error.

        Args:
            cycle_path: List of activity IDs forming the cycle
        """
        self.cycle_path = cycle_path
        message = f"Circular dependency: {' -> '.join(str(id) for id in cycle_path)}"
        super().__init__(message, "CIRCULAR_DEPENDENCY")


class ScheduleCalculationError(DomainError):
    """Error during CPM calculation."""

    def __init__(
        self,
        message: str,
        code: str = "SCHEDULE_CALCULATION_ERROR",
    ) -> None:
        """Initialize schedule calculation error."""
        super().__init__(message, code)


class AuthenticationError(DomainError):
    """Authentication failed."""

    def __init__(
        self,
        message: str = "Authentication required",
        code: str = "AUTHENTICATION_REQUIRED",
    ) -> None:
        """Initialize authentication error."""
        super().__init__(message, code)


class AuthorizationError(DomainError):
    """Authorization failed."""

    def __init__(
        self,
        message: str = "Permission denied",
        code: str = "PERMISSION_DENIED",
    ) -> None:
        """Initialize authorization error."""
        super().__init__(message, code)
