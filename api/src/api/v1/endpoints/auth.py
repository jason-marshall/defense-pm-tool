"""Authentication endpoints for user registration, login, and token management."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from src.config import settings
from src.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from src.core.deps import DbSession, get_current_user
from src.core.exceptions import AuthenticationError, ConflictError
from src.core.rate_limit import RATE_LIMIT_AUTH, limiter
from src.models.user import User
from src.repositories.user import UserRepository
from src.schemas.errors import (
    AuthenticationErrorResponse,
    ConflictErrorResponse,
    RateLimitErrorResponse,
    ValidationErrorResponse,
)
from src.schemas.user import (
    RefreshTokenRequest,
    TokenPairResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

router = APIRouter(tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register User",
    description="Create a new user account with email, password, and full name.",
    responses={
        201: {"description": "User registered successfully"},
        409: {"model": ConflictErrorResponse, "description": "Email already registered"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(RATE_LIMIT_AUTH)
async def register(
    request: Request,
    user_in: UserCreate,
    db: DbSession,
) -> UserResponse:
    """
    Register a new user account.

    - **email**: Unique email address for login
    - **password**: Password (minimum 8 characters)
    - **full_name**: User's display name

    Returns the created user (without password).
    """
    repo = UserRepository(db)

    # Check if email already exists
    if await repo.email_exists(user_in.email):
        raise ConflictError(
            f"Email {user_in.email} is already registered",
            "EMAIL_ALREADY_EXISTS",
        )

    # Create user
    user = await repo.create_user(user_in)
    await db.commit()

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenPairResponse,
    summary="Login",
    description="Authenticate with email and password to receive access and refresh tokens.",
    responses={
        200: {"description": "Login successful, tokens returned"},
        401: {"model": AuthenticationErrorResponse, "description": "Invalid credentials"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(RATE_LIMIT_AUTH)
async def login(
    request: Request,
    credentials: UserLogin,
    db: DbSession,
) -> TokenPairResponse:
    """
    Authenticate user and return JWT tokens.

    - **email**: Registered email address
    - **password**: Account password

    Returns access token (15 min) and refresh token (7 days).
    """
    repo = UserRepository(db)

    # Authenticate user
    user = await repo.authenticate(credentials.email, credentials.password)
    if not user:
        raise AuthenticationError(
            "Invalid email or password",
            "INVALID_CREDENTIALS",
        )

    # Create tokens
    subject = str(user.id)
    access_token = create_access_token(subject)
    refresh_token = create_refresh_token(subject)

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/login/form",
    response_model=TokenPairResponse,
    summary="Login with OAuth2 form",
    description="OAuth2 compatible login endpoint for form-based authentication.",
    include_in_schema=False,  # Hide from OpenAPI docs (use /login instead)
)
@limiter.limit(RATE_LIMIT_AUTH)
async def login_form(
    request: Request,
    db: DbSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenPairResponse:
    """
    OAuth2 compatible login endpoint.

    Accepts username (email) and password via form data.
    Used by OAuth2PasswordBearer for automatic token handling.
    """
    repo = UserRepository(db)

    # Authenticate user (username is email in our case)
    user = await repo.authenticate(form_data.username, form_data.password)
    if not user:
        raise AuthenticationError(
            "Invalid email or password",
            "INVALID_CREDENTIALS",
        )

    # Create tokens
    subject = str(user.id)
    access_token = create_access_token(subject)
    refresh_token = create_refresh_token(subject)

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenPairResponse,
    summary="Refresh Token",
    description="Exchange a valid refresh token for a new access token.",
    responses={
        200: {"description": "Tokens refreshed successfully"},
        401: {
            "model": AuthenticationErrorResponse,
            "description": "Invalid or expired refresh token",
        },
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(RATE_LIMIT_AUTH)
async def refresh_token(
    request: Request,
    token_request: RefreshTokenRequest,
    db: DbSession,
) -> TokenPairResponse:
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token from login

    Returns new access token and refresh token pair.
    """
    # Decode and validate refresh token
    try:
        payload = decode_token(token_request.refresh_token)
    except AuthenticationError as e:
        raise AuthenticationError(
            "Invalid or expired refresh token",
            "INVALID_REFRESH_TOKEN",
        ) from e

    # Verify token type
    if payload.type != "refresh":
        raise AuthenticationError(
            "Invalid token type",
            "INVALID_TOKEN_TYPE",
        )

    # Verify user still exists and is active
    repo = UserRepository(db)
    user = await repo.get_by_id(UUID(payload.sub))
    if not user:
        raise AuthenticationError(
            "User not found",
            "USER_NOT_FOUND",
        )
    if not user.is_active:
        raise AuthenticationError(
            "User account is deactivated",
            "USER_DEACTIVATED",
        )

    # Create new tokens
    subject = str(user.id)
    access_token = create_access_token(subject)
    new_refresh_token = create_refresh_token(subject)

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Get the currently authenticated user's profile.",
    responses={
        200: {"description": "User profile retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Not authenticated"},
    },
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user's profile.

    Requires valid access token in Authorization header.

    Returns the authenticated user's profile information.
    """
    return UserResponse.model_validate(current_user)
