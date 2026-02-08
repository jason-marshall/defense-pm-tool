"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from src.api.v1.endpoints.health import router as health_router
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
from src.core.middleware import RequestTracingMiddleware, SecurityHeadersMiddleware
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


API_DESCRIPTION = """
## Defense Program Management Tool API

Enterprise-grade project management API with EVMS (Earned Value Management System)
compliance for defense contractors.

### Features

- **Schedule Management**: CPM scheduling with multiple dependency types (FS, FF, SS, SF)
- **EVMS Integration**: 6 EV methods, 6 EAC methods, variance tracking
- **Reporting**: CPR Formats 1, 3, 5 with PDF export
- **Monte Carlo**: Schedule risk analysis with sensitivity analysis
- **Jira Integration**: Bidirectional sync with Jira Cloud
- **Scenario Planning**: What-if analysis with promotion workflow

### Authentication

All endpoints (except `/health` and `/docs`) require JWT authentication.
Include token in Authorization header: `Bearer <token>`

Obtain tokens via:
- `POST /api/v1/auth/register` - Create new account
- `POST /api/v1/auth/login` - Get access/refresh tokens
- `POST /api/v1/auth/refresh` - Refresh access token

### Rate Limits

| Category | Limit | Endpoints |
|----------|-------|-----------|
| Default | 100/min | Most endpoints |
| Auth | 10/min | `/auth/login`, `/auth/register` |
| Reports | 5/min | `/reports/*` PDF generation |
| Sync | 20/min | `/jira/*` sync operations |
| Webhooks | 60/min | `/webhooks/jira` |

### EVMS Compliance

Implements ANSI/EIA-748 guidelines:
- **GL 6**: WBS/OBS integration
- **GL 7**: Milestone tracking
- **GL 8**: Time-phased budgets
- **GL 21**: Variance identification
- **GL 27**: EAC development (6 methods)
- **GL 28**: Management Reserve tracking
- **GL 32**: Audit trail
"""

OPENAPI_TAGS = [
    {
        "name": "Authentication",
        "description": "User authentication and JWT token management. Includes registration, login, and token refresh.",
    },
    {
        "name": "Programs",
        "description": "Program CRUD operations. Programs are top-level containers for WBS, activities, and baselines.",
    },
    {
        "name": "Activities",
        "description": "Activity management and CPM scheduling. Activities are work items with duration, cost, and dependencies.",
    },
    {
        "name": "Dependencies",
        "description": "Activity dependency relationships. Supports FS, FF, SS, SF types with lag/lead times.",
    },
    {
        "name": "WBS",
        "description": "Work Breakdown Structure management. Hierarchical organization of program scope using PostgreSQL ltree.",
    },
    {
        "name": "EVMS Periods",
        "description": "Earned Value period tracking. Monthly/quarterly BCWS, BCWP, ACWP data for variance analysis.",
    },
    {
        "name": "Baselines",
        "description": "Baseline snapshots and comparison. Capture program state for variance tracking.",
    },
    {
        "name": "Scenarios",
        "description": "What-if scenario planning and simulation. Create, evaluate, and promote scenarios to baselines.",
    },
    {
        "name": "Simulations",
        "description": "Monte Carlo schedule risk simulation. Configure distributions and run probabilistic analysis.",
    },
    {
        "name": "Reports",
        "description": "CPR report generation. Formats 1 (WBS), 3 (Baseline), 5 (EVMS) with PDF/JSON export.",
    },
    {
        "name": "Jira Integration",
        "description": "Jira Cloud integration. Connect programs, sync WBS/activities, receive webhooks.",
    },
    {
        "name": "Variance",
        "description": "Variance explanation management. Document and track cost/schedule variances.",
    },
    {
        "name": "Health",
        "description": "API health and status endpoints. No authentication required.",
    },
]

app = FastAPI(
    title="Defense PM Tool API",
    version="1.0.0",
    description=API_DESCRIPTION,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={
        "name": "API Support",
        "email": "support@defense-pm-tool.com",
    },
    license_info={
        "name": "Proprietary",
    },
    openapi_tags=OPENAPI_TAGS,
)

# CORS middleware - allow localhost origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Correlation-ID"],
)

# Request tracing middleware - adds correlation IDs and metrics
app.add_middleware(RequestTracingMiddleware)

# Security headers middleware - adds security headers to all responses
app.add_middleware(
    SecurityHeadersMiddleware,
    csp_enabled=settings.CSP_ENABLED,
    hsts_enabled=settings.HSTS_ENABLED,
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

# Health check endpoints (no auth required, at root level)
app.include_router(health_router)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "Defense PM Tool API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
