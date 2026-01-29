#!/bin/bash
# =============================================================================
# Stop Isolated Development Environment
# =============================================================================
# Stops the isolated Docker containers. Add -v flag to also remove volumes.
#
# Usage:
#   ./scripts/isolated-down.sh        # Stop containers, keep data
#   ./scripts/isolated-down.sh -v     # Stop containers and remove volumes
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Stopping isolated development environment..."
docker compose -f docker-compose.dev-isolated.yml -p dpmt-isolated down "$@"

echo "Isolated environment stopped."
