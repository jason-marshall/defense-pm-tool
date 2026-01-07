"""Custom exceptions for the application."""


class DefensePMException(Exception):
    """Base exception for Defense PM Tool."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(DefensePMException):
    """Resource not found exception."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class UnauthorizedException(DefensePMException):
    """Unauthorized access exception."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ForbiddenException(DefensePMException):
    """Forbidden access exception."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class ValidationException(DefensePMException):
    """Validation error exception."""

    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=422)
