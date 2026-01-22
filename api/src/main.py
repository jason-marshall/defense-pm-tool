"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from src.api.v1.router import api_router
from src.config import settings
from src.core.cache import cache_manager, close_redis, init_redis
from src.core.database import dispose_engine, init_engine
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
from src.core.rate_limit import limiter, rate_limit_exceeded_handler

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup/shutdown events.

    Handles initialization and cleanup of database connections,
    Redis connections, and other resources.
    """
    # Startup
    logger.info(
        "application_startup",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    # Initialize database engine
    await init_engine()
    logger.info("database_initialized")

    # Initialize Redis connection
    try:
        redis_client = await init_redis()
        cache_manager.redis = redis_client
        app.state.redis = redis_client
        logger.info("redis_initialized")
    except Exception as e:
        logger.warning("redis_init_failed", error=str(e))
        cache_manager.disable()

    yield

    # Shutdown
    logger.info("application_shutdown")

    # Close database connections
    await dispose_engine()
    logger.info("database_connections_closed")

    # Close Redis connections
    if hasattr(app.state, "redis") and app.state.redis:
        await close_redis(app.state.redis)
        logger.info("redis_connections_closed")


app = FastAPI(
    title="Defense PM Tool API",
    version="0.1.0",
    description="Defense Program Management Tool with EVMS/DFARS Compliance",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware - allow localhost origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (can be disabled via RATE_LIMIT_ENABLED=false for testing)
if settings.RATE_LIMIT_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Handle domain-specific errors with consistent JSON responses."""
    status_map: dict[type[DomainError], int] = {
        ValidationError: 422,
        NotFoundError: 404,
        ConflictError: 409,
        CircularDependencyError: 400,
        ScheduleCalculationError: 400,
        AuthenticationError: 401,
        AuthorizationError: 403,
    }
    status_code = status_map.get(type(exc), 400)

    logger.warning(
        "domain_error",
        error_code=exc.code,
        error_message=exc.message,
        status_code=status_code,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message, "code": exc.code},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with logging."""
    logger.exception(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "code": "INTERNAL_SERVER_ERROR",
        },
    )


# Include API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns the current health status and version of the API.
    Used by load balancers and monitoring systems.
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "Defense PM Tool API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
