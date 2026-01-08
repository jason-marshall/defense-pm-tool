"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.v1.router import api_router
from src.config import settings
from src.core.exceptions import DomainError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection
    yield
    # Shutdown
    # TODO: Close database connections
    # TODO: Close Redis connections


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Defense Program Management Tool with EVMS/DFARS Compliance",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Handle domain-specific errors with consistent JSON responses."""
    from src.core.exceptions import (
        CircularDependencyError,
        ConflictError,
        NotFoundError,
        ValidationError,
    )

    status_map: dict[type[DomainError], int] = {
        ValidationError: 422,
        NotFoundError: 404,
        ConflictError: 409,
        CircularDependencyError: 400,
    }
    status_code = status_map.get(type(exc), 400)

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message, "code": exc.code},
    )


# Include API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.APP_VERSION}
