#!/bin/bash
# =============================================================================
# Start Isolated Development Environment
# =============================================================================
# Starts the isolated Docker containers without conflicting with main dev.
#
# Usage: ./scripts/isolated-up.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Starting isolated development environment..."
docker compose -f docker-compose.dev-isolated.yml -p dpmt-isolated up -d

echo ""
echo "Isolated environment started!"
echo "  API:        http://localhost:8001"
echo "  API Docs:   http://localhost:8001/docs"
echo "  PostgreSQL: localhost:5433"
echo "  Redis:      localhost:6380"
echo ""
echo "To check status: docker compose -f docker-compose.dev-isolated.yml -p dpmt-isolated ps"
echo "To view logs:    docker compose -f docker-compose.dev-isolated.yml -p dpmt-isolated logs -f"
