# Defense PM Tool - Upgrade Guide

> **Last Updated**: March 2026
> **Current Version**: 1.2.0

This guide provides step-by-step instructions for upgrading between versions of the Defense PM Tool.

---

## Table of Contents

1. [General Upgrade Process](#general-upgrade-process)
2. [v1.0.0 to v1.1.0](#v100-to-v110)
3. [v1.1.0 to v1.2.0](#v110-to-v120)
4. [Database Migration Checklist](#database-migration-checklist)
5. [Rollback Procedures](#rollback-procedures)
6. [Breaking Changes Summary](#breaking-changes-summary)

---

## General Upgrade Process

### Pre-Upgrade Checklist

Before any upgrade:

- [ ] **Backup database**
  ```bash
  pg_dump -h localhost -U dev_user -d defense_pm_prod > backup_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] **Backup Redis data** (if using persistence)
  ```bash
  redis-cli BGSAVE
  cp /var/lib/redis/dump.rdb backup_redis_$(date +%Y%m%d).rdb
  ```

- [ ] **Note current version**
  ```bash
  curl http://localhost:8000/health | jq '.version'
  ```

- [ ] **Review release notes** for breaking changes

- [ ] **Test upgrade in staging** before production

### Standard Upgrade Steps

```bash
# 1. Pull latest code
git fetch origin
git checkout v1.2.0  # or desired version

# 2. Update backend dependencies
cd api
pip install -r requirements.txt

# 3. Run database migrations
alembic upgrade head

# 4. Update frontend dependencies
cd ../web
npm install

# 5. Build frontend
npm run build

# 6. Restart services
docker-compose restart api
# Or if running directly:
# pkill -f uvicorn
# uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# 7. Verify upgrade
curl http://localhost:8000/health
```

---

## v1.0.0 to v1.1.0

**Release**: February 2026
**Theme**: Resource Management

### New Features

- Resource model (LABOR, EQUIPMENT, MATERIAL types)
- Resource assignment to activities
- Resource calendars
- Overallocation detection
- Serial resource leveling algorithm
- Resource histogram visualization
- 5 new frontend components

### Migration Steps

#### 1. Update Code

```bash
git fetch origin
git checkout v1.1.0
```

#### 2. Install New Dependencies

```bash
cd api
pip install -r requirements.txt
# New dependency: none for v1.1.0
```

#### 3. Run Database Migrations

```bash
cd api
alembic upgrade head
```

**New tables created:**
- `resources` - Resource definitions
- `resource_assignments` - Activity-resource links
- `resource_calendars` - Availability calendars

#### 4. Update Frontend

```bash
cd web
npm install
npm run build
```

#### 5. Configuration Changes

No environment variable changes required.

#### 6. Verify Upgrade

```bash
# Check version
curl http://localhost:8000/health
# Expected: {"version": "1.1.0", ...}

# Test new endpoints
curl http://localhost:8000/api/v1/resources -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with empty list
```

### Breaking Changes

**None** - v1.1.0 is fully backward compatible with v1.0.0.

### Rollback (if needed)

```bash
# Rollback migrations
cd api
alembic downgrade 009  # Last v1.0.0 migration

# Checkout previous version
git checkout v1.0.0

# Reinstall dependencies
pip install -r requirements.txt

# Rebuild frontend
cd ../web
npm install
npm run build
```

---

## v1.1.0 to v1.2.0

**Release**: March 2026
**Theme**: Advanced Resource Management

### New Features

- Resource cost tracking with automatic ACWP calculation
- Material quantity tracking
- MS Project calendar import
- Parallel resource leveling algorithm
- Cross-program resource pools
- Gantt resource view with drag-drop editing
- React 19 upgrade

### Migration Steps

#### 1. Pre-requisites

- Node.js 20+ required (for React 19)
- Ensure sufficient disk space for new database columns

#### 2. Update Code

```bash
git fetch origin
git checkout v1.2.0
```

#### 3. Install New Dependencies

```bash
cd api
pip install -r requirements.txt
```

**New/updated dependencies:**
- numpy>=1.26.0 (parallel leveling optimization)

#### 4. Run Database Migrations

```bash
cd api
alembic upgrade head
```

**Schema changes:**

Migration `010_resource_costs.py`:
- Adds `hourly_rate`, `overtime_rate` to `resources`
- Adds `cost`, `overtime_hours` to `resource_assignments`
- Adds `quantity_budgeted`, `quantity_actual` to `resource_assignments`

Migration `013_resource_pools.py`:
- Creates `resource_pools` table
- Creates `resource_pool_members` table
- Adds `pool_id` to `resources`

#### 5. Update Frontend

```bash
cd web

# Clean install (React 19 upgrade)
rm -rf node_modules package-lock.json
npm install

# If peer dependency warnings:
npm install --legacy-peer-deps

npm run build
```

#### 6. Configuration Changes

New optional environment variables:

```bash
# Enable parallel leveling (recommended for large programs)
PARALLEL_LEVELING_ENABLED=true

# Resource pool conflict detection
RESOURCE_POOL_CONFLICT_WINDOW_DAYS=7
```

#### 7. Cache Invalidation

Clear cached data after upgrade:

```bash
# Clear all caches
redis-cli FLUSHDB

# Or clear specific keys
redis-cli KEYS "resource:*" | xargs redis-cli DEL
redis-cli KEYS "leveling:*" | xargs redis-cli DEL
```

#### 8. Verify Upgrade

```bash
# Check version
curl http://localhost:8000/health
# Expected: {"version": "1.2.0", ...}

# Test resource cost endpoint
curl http://localhost:8000/api/v1/resources/UUID/costs -H "Authorization: Bearer $TOKEN"

# Test resource pools endpoint
curl http://localhost:8000/api/v1/resource-pools -H "Authorization: Bearer $TOKEN"

# Test parallel leveling
curl -X POST "http://localhost:8000/api/v1/resources/leveling/program/UUID?algorithm=parallel" \
  -H "Authorization: Bearer $TOKEN"
```

### Breaking Changes

#### API Changes

1. **Resource response includes new fields**
   ```json
   {
     "id": "...",
     "name": "Engineer",
     "hourly_rate": "75.00",     // NEW
     "overtime_rate": "112.50",  // NEW
     "pool_id": null             // NEW (optional)
   }
   ```

2. **Assignment response includes cost data**
   ```json
   {
     "id": "...",
     "resource_id": "...",
     "activity_id": "...",
     "cost": "600.00",           // NEW (calculated)
     "overtime_hours": 0,        // NEW
     "quantity_budgeted": null,  // NEW (for materials)
     "quantity_actual": null     // NEW (for materials)
   }
   ```

3. **Leveling endpoint has new algorithm parameter**
   ```bash
   # Old (still works, defaults to serial)
   POST /api/v1/resources/leveling/program/{id}

   # New (explicit algorithm)
   POST /api/v1/resources/leveling/program/{id}?algorithm=parallel
   ```

#### Frontend Changes

1. **React 19 upgrade** - May require updates to custom components
2. **Gantt view has new resource lanes** - CSS changes may be needed

### Data Migration Notes

Existing data is preserved:
- Resources get default `hourly_rate` of 0.00
- Assignments get `cost` calculated on first access
- No data loss occurs

### Rollback (if needed)

```bash
# Rollback migrations
cd api
alembic downgrade 009  # Before resource costs

# Checkout previous version
git checkout v1.1.0

# Reinstall dependencies
pip install -r requirements.txt

# Rebuild frontend (React 18)
cd ../web
rm -rf node_modules package-lock.json
npm install
npm run build

# Clear caches
redis-cli FLUSHDB
```

---

## Database Migration Checklist

Use this checklist for any version upgrade:

### Before Migration

- [ ] Current database backup created and verified
- [ ] Current alembic revision noted: `alembic current`
- [ ] Downgrade path tested in staging
- [ ] Sufficient disk space available
- [ ] Database connection count checked (close excess connections)
- [ ] Application in maintenance mode (if production)

### During Migration

- [ ] Run migrations: `alembic upgrade head`
- [ ] Check for errors in migration output
- [ ] Verify new tables/columns exist
- [ ] Verify existing data intact

### After Migration

- [ ] Application starts without errors
- [ ] Key workflows tested
- [ ] Performance acceptable
- [ ] Monitoring shows no anomalies
- [ ] Remove maintenance mode

### Migration Commands Reference

```bash
# Check current revision
alembic current

# Show migration history
alembic history --verbose

# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade abc123

# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade abc123

# Show SQL without running (dry run)
alembic upgrade head --sql

# Mark revision without running (dangerous)
alembic stamp abc123
```

---

## Rollback Procedures

### Quick Rollback (within 24 hours)

```bash
# 1. Stop application
docker-compose stop api

# 2. Downgrade database
cd api
alembic downgrade -1  # Or specific revision

# 3. Checkout previous version
git checkout v1.1.0  # Previous version

# 4. Install previous dependencies
pip install -r requirements.txt

# 5. Restart
docker-compose start api
```

### Full Rollback (restore from backup)

```bash
# 1. Stop application
docker-compose stop api

# 2. Drop current database
docker exec -it postgres psql -U dev_user -c "DROP DATABASE defense_pm_prod"
docker exec -it postgres psql -U dev_user -c "CREATE DATABASE defense_pm_prod"

# 3. Restore backup
psql -h localhost -U dev_user -d defense_pm_prod < backup_20260301.sql

# 4. Checkout previous version
git checkout v1.1.0

# 5. Install dependencies and start
pip install -r requirements.txt
docker-compose start api
```

---

## Breaking Changes Summary

| Version | Change | Impact | Migration |
|---------|--------|--------|-----------|
| v1.1.0 | None | None | Automatic |
| v1.2.0 | Resource cost fields | API responses have new fields | Backward compatible |
| v1.2.0 | React 19 | Frontend build changes | Clean npm install |
| v1.2.0 | Resource pools | New tables added | Automatic migration |

---

## Version Compatibility Matrix

| Component | v1.0.0 | v1.1.0 | v1.2.0 |
|-----------|--------|--------|--------|
| Python | 3.11+ | 3.11+ | 3.11+ |
| Node.js | 18+ | 20+ | 20+ |
| PostgreSQL | 15+ | 15+ | 15+ |
| Redis | 7+ | 7+ | 7+ |
| React | 18 | 18 | 19 |

---

## Getting Help

If you encounter issues during upgrade:

1. Check [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review release notes for known issues
3. Search [GitHub Issues](https://github.com/jason-marshall/defense-pm-tool/issues)
4. Create new issue with:
   - Source version
   - Target version
   - Error messages
   - Migration logs

---

*Defense PM Tool v1.2.0 - Upgrade Guide*
*Last Updated: March 2026*
