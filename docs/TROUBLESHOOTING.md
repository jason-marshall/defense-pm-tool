# Defense PM Tool - Troubleshooting Guide

> **Version**: 1.2.0
> **Last Updated**: March 2026

This guide covers common issues and their solutions when working with the Defense PM Tool.

---

## Table of Contents

1. [Docker Issues](#docker-issues)
2. [Database Issues](#database-issues)
3. [API Issues](#api-issues)
4. [Frontend Issues](#frontend-issues)
5. [Test Issues](#test-issues)
6. [Performance Issues](#performance-issues)
7. [Authentication Issues](#authentication-issues)

---

## Docker Issues

### Port Already in Use

**Symptom**: `Error: Port 5432 (or 6379, 8000) is already in use`

**Solution**:
```bash
# Find what's using the port (Windows)
netstat -ano | findstr :5432

# Find what's using the port (Linux/Mac)
lsof -i :5432

# Kill the process or change port in docker-compose.yml
# Example: Change postgres port
ports:
  - "5433:5432"  # Use external port 5433
```

### Container Won't Start

**Symptom**: Container exits immediately after starting

**Solution**:
```bash
# Check logs for specific error
docker-compose logs postgres
docker-compose logs api

# Common fixes:
# 1. Remove old volumes (WARNING: deletes data)
docker-compose down -v
docker-compose up -d

# 2. Rebuild images
docker-compose build --no-cache
docker-compose up -d

# 3. Check disk space
docker system df
docker system prune -a  # Clean up unused resources
```

### Database Volume Issues

**Symptom**: PostgreSQL fails with permission errors or corrupt data

**Solution**:
```bash
# Remove and recreate volume
docker-compose down -v
docker volume rm defense-pm-tool_postgres_data
docker-compose up -d

# If using named volumes, list and remove
docker volume ls
docker volume rm <volume_name>
```

### Docker Memory Issues

**Symptom**: Containers randomly crash or OOM errors

**Solution**:
1. Increase Docker Desktop memory allocation (Settings > Resources)
2. Minimum recommended: 4GB for development, 8GB for testing

---

## Database Issues

### Connection Refused

**Symptom**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
```bash
# 1. Check if PostgreSQL container is running
docker-compose ps

# 2. Verify connection string in .env
DATABASE_URL=postgresql+asyncpg://dev_user:dev_password@localhost:5432/defense_pm_dev

# 3. Test connection directly
docker exec -it defense-pm-tool-postgres psql -U dev_user -d defense_pm_dev -c "SELECT 1"

# 4. If using WSL2, try host.docker.internal
DATABASE_URL=postgresql+asyncpg://dev_user:dev_password@host.docker.internal:5432/defense_pm_dev
```

### Migration Failures

**Symptom**: `alembic upgrade head` fails

**Solution**:
```bash
cd api

# Check current revision
alembic current

# Show migration history
alembic history --verbose

# If stuck on a failed migration:
# 1. Check what's in the database
alembic current

# 2. Mark as complete if manually fixed
alembic stamp <revision_id>

# 3. Or downgrade and try again
alembic downgrade -1
alembic upgrade head

# If migration is corrupted, reset (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head
```

### ltree Extension Missing

**Symptom**: `type "ltree" does not exist`

**Solution**:
```bash
# Connect to database and create extension
docker exec -it defense-pm-tool-postgres psql -U dev_user -d defense_pm_dev

# In psql:
CREATE EXTENSION IF NOT EXISTS ltree;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\q

# Or check init.sql was executed
cat docker/postgres/init.sql
```

### Slow Queries

**Symptom**: API responses taking >1 second

**Solution**:
```bash
# Check for missing indexes
docker exec -it defense-pm-tool-postgres psql -U dev_user -d defense_pm_dev

# In psql - check query plan
EXPLAIN ANALYZE SELECT * FROM activities WHERE program_id = 'uuid-here';

# Common missing indexes:
CREATE INDEX IF NOT EXISTS ix_activities_program_id ON activities(program_id);
CREATE INDEX IF NOT EXISTS ix_dependencies_predecessor_id ON dependencies(predecessor_id);
```

---

## API Issues

### API Not Starting

**Symptom**: `uvicorn` command fails or API doesn't respond

**Solution**:
```bash
cd api

# 1. Check virtual environment is active
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 2. Reinstall dependencies
pip install -r requirements.txt

# 3. Check .env file exists and has required values
cat .env

# 4. Run with debug output
uvicorn src.main:app --reload --log-level debug

# 5. Check for import errors
python -c "from src.main import app; print('OK')"
```

### 422 Validation Error

**Symptom**: API returns 422 with validation details

**Solution**:
```json
// Check the response body for details:
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}

// Common causes:
// 1. Missing required field
// 2. Wrong data type (string instead of number)
// 3. Invalid UUID format
// 4. Date format should be "YYYY-MM-DD"
// 5. Decimal values need quotes: "budgeted_cost": "10000.00"
```

### 401 Unauthorized

**Symptom**: API returns 401 even with token

**Solution**:
```bash
# 1. Check token is not expired (default: 30 min)
# Decode JWT at jwt.io to check exp claim

# 2. Verify header format
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" http://localhost:8000/api/v1/programs

# 3. Get new token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your@email.com&password=yourpassword"

# 4. Check SECRET_KEY matches between token creation and validation
```

### 500 Internal Server Error

**Symptom**: API returns 500 with no details

**Solution**:
```bash
# 1. Check API logs
docker-compose logs api

# 2. If running locally, check terminal output
# Look for Python tracebacks

# 3. Enable debug mode temporarily
export DEBUG=true
uvicorn src.main:app --reload

# 4. Common causes:
# - Database connection lost
# - Redis connection failed
# - Missing environment variable
# - Unhandled exception in code
```

---

## Frontend Issues

### npm install Fails

**Symptom**: Dependency installation errors

**Solution**:
```bash
cd web

# 1. Clear npm cache
npm cache clean --force

# 2. Remove node_modules and lock file
rm -rf node_modules package-lock.json

# 3. Reinstall
npm install

# 4. If peer dependency issues (React 19):
npm install --legacy-peer-deps
```

### Build Fails

**Symptom**: `npm run build` errors

**Solution**:
```bash
# 1. Check TypeScript errors
npm run type-check

# 2. Common fixes:
# - Missing type declarations: npm install @types/package-name
# - Unused imports: remove or add eslint-disable
# - Type mismatches: check API response types

# 3. Clear build cache
rm -rf dist .vite
npm run build
```

### API Connection Failed

**Symptom**: Frontend can't reach API

**Solution**:
```bash
# 1. Check API is running
curl http://localhost:8000/health

# 2. Check VITE_API_URL in .env
echo $VITE_API_URL
# Should be: http://localhost:8000/api/v1

# 3. Check CORS settings in API
# api/src/main.py should allow localhost:5173

# 4. Check browser console for specific errors
# Network tab shows actual request/response
```

### Hot Reload Not Working

**Symptom**: Changes not reflected in browser

**Solution**:
```bash
# 1. Check Vite is running in watch mode
npm run dev

# 2. Hard refresh browser
Ctrl+Shift+R (Windows/Linux)
Cmd+Shift+R (Mac)

# 3. Restart Vite
# Stop with Ctrl+C, then npm run dev

# 4. Check file is saved and in src/ directory
```

---

## Test Issues

### Tests Fail to Start

**Symptom**: pytest command fails immediately

**Solution**:
```bash
cd api

# 1. Check virtual environment
which python  # Should show venv path

# 2. Install test dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov httpx

# 3. Check conftest.py exists
ls tests/conftest.py

# 4. Run with verbose output
pytest -v --tb=long
```

### Database Tests Fail

**Symptom**: Integration tests fail with DB errors

**Solution**:
```bash
# 1. Check test database exists
# Tests use in-memory SQLite by default, but some need PostgreSQL

# 2. Run with test database
export DATABASE_URL=postgresql+asyncpg://dev_user:dev_password@localhost:5432/defense_pm_test

# 3. Create test database
docker exec -it defense-pm-tool-postgres psql -U dev_user -c "CREATE DATABASE defense_pm_test"

# 4. Check async issues
# Use pytest-asyncio markers:
# @pytest.mark.asyncio
# async def test_something():
```

### Flaky Tests

**Symptom**: Tests pass sometimes, fail others

**Solution**:
```bash
# 1. Run specific test multiple times
pytest tests/path/to/test.py -v --count=5

# 2. Check for shared state
# - Use fresh fixtures
# - Don't rely on test order
# - Reset database between tests

# 3. Check for timing issues
# Add explicit waits or use pytest-timeout
pytest --timeout=30

# 4. Run tests in isolation
pytest tests/path/to/test.py::test_specific -v
```

---

## Performance Issues

### Slow CPM Calculations

**Symptom**: Schedule calculation takes >5 seconds

**Solution**:
```bash
# 1. Check activity count
curl http://localhost:8000/api/v1/activities?program_id=UUID&page_size=1
# Check "total" in response

# 2. Clear CPM cache
redis-cli KEYS "cpm:*" | xargs redis-cli DEL

# 3. Check for circular dependencies (causes infinite loop protection)
# API will return 400 with CIRCULAR_DEPENDENCY error

# 4. Performance targets:
# - 1000 activities: <500ms
# - 5000 activities: <2000ms
```

### Slow Dashboard Load

**Symptom**: EVMS dashboard takes >3 seconds

**Solution**:
```bash
# 1. Enable caching
export REDIS_URL=redis://localhost:6379

# 2. Check Redis is running
redis-cli ping  # Should return PONG

# 3. Pre-warm cache
curl http://localhost:8000/api/v1/evms/summary/PROGRAM_UUID

# 4. Check for N+1 queries in logs
# Enable SQL logging in development
```

### High Memory Usage

**Symptom**: API process using excessive memory

**Solution**:
```bash
# 1. Check for memory leaks in long-running processes
# Restart API periodically in development

# 2. Limit connection pool size
# In .env:
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5

# 3. For large imports, use streaming
# MS Project import processes in batches
```

---

## Authentication Issues

### Cannot Login

**Symptom**: Login returns 401 with correct credentials

**Solution**:
```bash
# 1. Check user exists
docker exec -it defense-pm-tool-postgres psql -U dev_user -d defense_pm_dev \
  -c "SELECT email, is_active FROM users WHERE email = 'your@email.com'"

# 2. Check user is active (is_active = true)

# 3. Try registering a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "new@example.com", "password": "Test123!", "full_name": "Test User"}'

# 4. Check password requirements:
# - Minimum 8 characters
# - At least one uppercase, lowercase, number
```

### Token Expired Too Quickly

**Symptom**: Need to login frequently

**Solution**:
```bash
# 1. Check token expiration setting
# In .env:
ACCESS_TOKEN_EXPIRE_MINUTES=30  # Default
REFRESH_TOKEN_EXPIRE_DAYS=7

# 2. Use refresh token to get new access token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'

# 3. For API integrations, use API keys instead
# API keys have longer expiration (up to 365 days)
```

### API Key Not Working

**Symptom**: X-API-Key header returns 401

**Solution**:
```bash
# 1. Check key format (starts with dpm_)
# X-API-Key: dpm_a1b2c3d4_...

# 2. Check key hasn't expired
# Create keys with appropriate expiration

# 3. Check key has required scopes
# Scope format: "programs:read", "activities:write"

# 4. Verify key was stored correctly (only shown once on creation)
```

---

## Getting Help

If you're still stuck:

1. **Check existing documentation**:
   - [API Guide](API_GUIDE.md) - Endpoint reference
   - [Deployment Guide](DEPLOYMENT.md) - Production setup
   - [User Guide](USER_GUIDE.md) - Feature usage

2. **Search GitHub Issues**:
   https://github.com/jason-marshall/defense-pm-tool/issues

3. **Create a new issue** with:
   - Environment details (OS, Python version, Node version)
   - Steps to reproduce
   - Error messages and logs
   - Expected vs actual behavior

---

*Defense PM Tool v1.2.0 - Troubleshooting Guide*
*Last Updated: March 2026*
