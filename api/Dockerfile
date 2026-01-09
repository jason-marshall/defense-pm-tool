# =============================================================================
# Defense PM Tool API - Dockerfile
# =============================================================================
# Multi-stage build for development and production environments.
#
# Stages:
#   - base: Common Python setup
#   - development: Includes dev dependencies, enables hot reload
#   - production: Optimized for production deployment
#
# Usage:
#   # Development (default via docker-compose.override.yml)
#   docker-compose up api
#
#   # Production
#   docker build --target production -t defense-pm-api .
#
# =============================================================================

# -----------------------------------------------------------------------------
# Base Stage - Common Setup
# -----------------------------------------------------------------------------
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

# Prevent Python from writing bytecode and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # pip configuration
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
# - curl: for health checks
# - postgresql-client: for pg_isready and database operations
# - build-essential: for compiling Python packages with C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# -----------------------------------------------------------------------------
# Development Stage
# -----------------------------------------------------------------------------
FROM base AS development

# Install development dependencies (includes compilers for some packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt requirements-dev.txt ./

# Install all dependencies (including dev dependencies)
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy application code
# In development, this is overridden by volume mounts in docker-compose
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Default command for development (hot reload enabled)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# -----------------------------------------------------------------------------
# Production Dependencies Stage
# -----------------------------------------------------------------------------
FROM base AS production-deps

# Copy only requirements file for better caching
COPY requirements.txt ./

# Install production dependencies only
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Production Stage
# -----------------------------------------------------------------------------
FROM base AS production

# Copy installed packages from production-deps stage
COPY --from=production-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=production-deps /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command (no reload, multiple workers)
# Workers = 2 * CPU cores + 1 (adjust based on container resources)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# =============================================================================
# Build Examples
# =============================================================================
#
# Build development image:
#   docker build --target development -t defense-pm-api:dev .
#
# Build production image:
#   docker build --target production -t defense-pm-api:latest .
#
# Run development container:
#   docker run -p 8000:8000 -v $(pwd)/src:/app/src defense-pm-api:dev
#
# Run production container:
#   docker run -p 8000:8000 --env-file .env defense-pm-api:latest
#
# =============================================================================
