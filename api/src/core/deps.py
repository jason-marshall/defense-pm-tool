"""FastAPI dependencies for dependency injection."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import decode_token
from src.core.database import get_db
from src.core.exceptions import AuthenticationError
from src.models.enums import UserRole
from src.models.user import User
from src.repositories.user import UserRepository

# OAuth2 scheme for extracting bearer tokens from Authorization header
# tokenUrl points to the login endpoint for OpenAPI documentation
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login/form",
    auto_error=True,
)

# Optional OAuth2 scheme that doesn't raise error if token is missing
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login/form",
    auto_error=False,
)

# Type alias for database session dependency injection
# Usage: async def endpoint(db: DbSession): ...
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    """
    Validate access token and return the current user.

    This dependency:
    1. Extracts the JWT token from the Authorization header
    2. Decodes and validates the token
    3. Retrieves the user from the database
    4. Verifies the user is active

    Args:
        token: JWT access token from Authorization header
        db: Database session

    Returns:
        The authenticated User object

    Raises:
        HTTPException 401: If token is invalid, expired, or user not found
    """
    try:
        payload = decode_token(token)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token type is access token
    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    try:
        user_id = UUID(payload.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    token: Annotated[str | None, Depends(oauth2_scheme_optional)],
    db: DbSession,
) -> User | None:
    """
    Optionally validate access token and return the current user.

    Similar to get_current_user but returns None if no token is provided.
    Useful for endpoints that behave differently for authenticated users.

    Args:
        token: Optional JWT access token from Authorization header
        db: Database session

    Returns:
        The authenticated User object, or None if no valid token
    """
    if not token:
        return None

    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


def require_role(required_role: UserRole) -> Callable[[User], User]:
    """
    Dependency factory for role-based access control.

    Creates a dependency that validates the current user has at least
    the required role level.

    Args:
        required_role: Minimum role required for access

    Returns:
        Dependency function that validates user role

    Example:
        @router.post("/admin-only")
        async def admin_endpoint(
            user: User = Depends(require_role(UserRole.ADMIN))
        ):
            ...
    """

    def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check if user has required role."""
        if not current_user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher",
            )
        return current_user

    return role_checker


def require_active_user() -> Callable[[User], User]:
    """
    Dependency that ensures the current user is active.

    This is already checked in get_current_user, but can be used
    for explicit documentation purposes.

    Returns:
        Dependency function that validates user is active
    """

    def active_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check if user is active."""
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
            )
        return current_user

    return active_checker


# Pre-configured role dependencies for common use cases
RequireViewer = Depends(require_role(UserRole.VIEWER))
RequireAnalyst = Depends(require_role(UserRole.ANALYST))
RequireScheduler = Depends(require_role(UserRole.SCHEDULER))
RequireProgramManager = Depends(require_role(UserRole.PROGRAM_MANAGER))
RequireAdmin = Depends(require_role(UserRole.ADMIN))

# Type alias for current user dependency
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
