# Defense PM Tool - Deployment Guide

This guide covers deployment options for the Defense Program Management Tool v1.2.0.

> **Note**: v1.2.0 includes React 19 upgrade in the frontend. Ensure Node.js 20+ is installed.

## Table of Contents

1. [Quick Start (Production)](#quick-start-production)
2. [Prerequisites](#prerequisites)
3. [Environment Configuration](#environment-configuration)
4. [Development Setup](#development-setup)
5. [Docker Deployment](#docker-deployment)
6. [Production Deployment](#production-deployment)
7. [Database Management](#database-management)
8. [Monitoring & Health Checks](#monitoring--health-checks)
9. [Security Considerations](#security-considerations)
10. [Production Checklist](#production-checklist)
11. [Troubleshooting](#troubleshooting)

---

## Quick Start (Production)

### 1. Clone and Configure

```bash
git clone https://github.com/org/defense-pm-tool.git
cd defense-pm-tool
cp .env.production.template .env.production
```

### 2. Generate Secrets

```bash
# Generate all required secrets
python -c "import secrets; print('SECRET_KEY:', secrets.token_urlsafe(64))"
python -c "import secrets; print('DB_PASSWORD:', secrets.token_urlsafe(32))"
python -c "import secrets; print('REDIS_PASSWORD:', secrets.token_urlsafe(32))"
```

### 3. Edit Configuration

Edit `.env.production` with your generated secrets and configuration.

### 4. Deploy

**Option A: Self-Hosted (includes PostgreSQL + Redis)**

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml -f docker-compose.selfhosted.yml \
    --env-file .env.production up -d

# Run database migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Verify health
curl http://localhost:8000/health
```

**Option B: Managed Services (external PostgreSQL + Redis)**

```bash
# Build and start API only
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# Run database migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Verify health
curl http://localhost:8000/health
```

### 5. Verify Deployment

```bash
# Check health
curl http://localhost:8000/health
# Expected: {"status":"healthy","database":"connected","cache":"connected"}

# Check API documentation
curl http://localhost:8000/docs
```

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 20 LTS | Frontend build |
| Docker | 24.0+ | Containerization |
| Docker Compose | 2.20+ | Multi-container orchestration |
| PostgreSQL | 15+ | Primary database |
| Redis | 7+ | Caching layer |

### Hardware Requirements

**Development:**
- 4 GB RAM
- 2 CPU cores
- 10 GB disk space

**Production (Minimum):**
- 8 GB RAM
- 4 CPU cores
- 50 GB SSD

**Production (Recommended for 1000+ users):**
- 16 GB RAM
- 8 CPU cores
- 100 GB SSD
- Dedicated PostgreSQL instance

---

## Environment Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# =============================================================================
# Application Settings
# =============================================================================
APP_NAME=Defense PM Tool
APP_VERSION=0.1.0
ENVIRONMENT=development  # development, staging, production
DEBUG=true              # Set false in production

# =============================================================================
# Database Configuration
# =============================================================================
# PostgreSQL connection URL
DATABASE_URL=postgresql+asyncpg://dev_user:dev_password@localhost:5432/defense_pm_dev

# Connection pool settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30

# =============================================================================
# Redis Configuration
# =============================================================================
REDIS_URL=redis://localhost:6379

# =============================================================================
# Security Settings
# =============================================================================
# Generate with: openssl rand -hex 32
SECRET_KEY=your-secret-key-change-in-production

# JWT settings
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
ALGORITHM=HS256

# Password hashing
BCRYPT_ROUNDS=12

# =============================================================================
# CORS Configuration
# =============================================================================
# Comma-separated list of allowed origins
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# =============================================================================
# API Settings
# =============================================================================
API_V1_PREFIX=/api/v1

# =============================================================================
# Performance Settings
# =============================================================================
# CPM calculation timeout (seconds)
CPM_TIMEOUT=30

# Maximum activities per program
MAX_ACTIVITIES=10000

# Cache TTL (seconds)
CPM_CACHE_TTL=3600      # 1 hour
EVMS_CACHE_TTL=300      # 5 minutes
WBS_CACHE_TTL=1800      # 30 minutes
```

### Production Environment Variables

For production, ensure these additional settings:

```bash
# Production-specific
ENVIRONMENT=production
DEBUG=false

# Strong secret key (generate new for production)
SECRET_KEY=<generated-64-char-hex-string>

# Production database (use managed service)
DATABASE_URL=postgresql+asyncpg://user:password@db.example.com:5432/defense_pm_prod

# Production Redis (use managed service)
REDIS_URL=redis://:password@redis.example.com:6379

# Restrict CORS to production domains
CORS_ORIGINS=https://app.example.com

# SSL settings (handled by reverse proxy)
FORWARDED_ALLOW_IPS=*
```

---

## Development Setup

### Quick Start

1. **Clone and configure:**
   ```bash
   git clone https://github.com/your-org/defense-pm-tool.git
   cd defense-pm-tool
   cp .env.example .env
   ```

2. **Start database services:**
   ```bash
   docker-compose up -d postgres redis
   ```

3. **Setup backend:**
   ```bash
   cd api
   python -m venv venv

   # Windows
   .\venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate

   pip install -r requirements.txt
   alembic upgrade head
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Setup frontend (new terminal):**
   ```bash
   cd web
   npm install
   npm run dev
   ```

5. **Verify:**
   - API: http://localhost:8000/docs
   - Frontend: http://localhost:5173
   - Health: http://localhost:8000/health

---

## Docker Deployment

### Development with Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build api
```

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    restart: always
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2'
        reservations:
          memory: 512M
          cpus: '0.5'

  web:
    build:
      context: ./web
      dockerfile: Dockerfile
      args:
        - VITE_API_URL=${API_URL}
    restart: always
    ports:
      - "80:80"
    depends_on:
      - api
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'

  # Use managed services for postgres/redis in production
```

### Docker Commands

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start production
docker-compose -f docker-compose.prod.yml up -d

# Scale API servers
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# View status
docker-compose -f docker-compose.prod.yml ps

# Rolling update
docker-compose -f docker-compose.prod.yml up -d --no-deps --build api
```

---

## Production Deployment

### Cloud Deployment Options

#### AWS

1. **ECS/Fargate:**
   - Containerized deployment
   - Auto-scaling based on CPU/memory
   - Use RDS for PostgreSQL
   - Use ElastiCache for Redis

2. **EC2:**
   - Traditional VM deployment
   - Use Application Load Balancer
   - Auto Scaling Groups for API

#### Azure

1. **Azure Container Apps:**
   - Managed container platform
   - Built-in scaling
   - Use Azure Database for PostgreSQL
   - Use Azure Cache for Redis

#### GCP

1. **Cloud Run:**
   - Serverless containers
   - Automatic scaling to zero
   - Use Cloud SQL for PostgreSQL
   - Use Memorystore for Redis

### Deployment Checklist

#### Pre-Deployment

- [ ] All tests passing (`pytest tests/`)
- [ ] Linting passes (`ruff check src tests`)
- [ ] Type checking passes (`mypy src`)
- [ ] Environment variables configured
- [ ] SSL certificates provisioned
- [ ] Database backups configured
- [ ] Monitoring/alerting setup

#### Deployment

- [ ] Run database migrations
- [ ] Deploy API servers
- [ ] Deploy frontend
- [ ] Update DNS if needed
- [ ] Verify health endpoints
- [ ] Test critical workflows

#### Post-Deployment

- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Verify logs are flowing
- [ ] Update documentation

---

## Database Management

### Migrations

```bash
# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Create new migration
alembic revision --autogenerate -m "description"

# Show current revision
alembic current

# Show migration history
alembic history
```

### PostgreSQL Extensions

Required extensions (created automatically by init.sql):

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "ltree";
```

### Backup and Restore

```bash
# Backup
pg_dump -h localhost -U dev_user -d defense_pm_dev > backup.sql

# Restore
psql -h localhost -U dev_user -d defense_pm_dev < backup.sql

# Backup with Docker
docker exec defense-pm-tool-postgres pg_dump -U dev_user defense_pm_dev > backup.sql
```

---

## Monitoring & Health Checks

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Basic health check |
| `GET /` | API info and version |

### Recommended Monitoring

1. **Application Metrics:**
   - Request latency (p50, p95, p99)
   - Error rate by endpoint
   - Active connections
   - CPM calculation duration

2. **Infrastructure Metrics:**
   - CPU/Memory utilization
   - Disk I/O
   - Network throughput
   - Container restarts

3. **Database Metrics:**
   - Connection pool usage
   - Query execution time
   - Lock contention
   - Replication lag (if applicable)

4. **Cache Metrics:**
   - Hit/miss ratio
   - Memory usage
   - Eviction rate

### Logging

Structured JSON logs in production:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info",
  "logger": "src.api.v1.endpoints.schedule",
  "message": "cpm_calculation_complete",
  "request_id": "abc-123",
  "program_id": "uuid",
  "duration_ms": 45.2
}
```

---

## Security Considerations

### Checklist

- [ ] Use HTTPS only (redirect HTTP)
- [ ] Strong SECRET_KEY (64+ chars)
- [ ] Database credentials rotated regularly
- [ ] Rate limiting enabled
- [ ] CORS restricted to known origins
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (sanitized output)
- [ ] Regular dependency updates

### Network Security

```
Internet → WAF → Load Balancer → API Servers → Database
                                      ↓
                                    Redis
```

- WAF rules for common attacks
- Load balancer SSL termination
- Private subnet for database/Redis
- Security groups restrict access

### Secrets Management

Use a secrets manager in production:
- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault

---

## Production Checklist

### Pre-Deployment Security

- [ ] SECRET_KEY generated (64+ characters, unique)
- [ ] DB_PASSWORD strong (32+ characters)
- [ ] REDIS_PASSWORD set
- [ ] CORS_ORIGINS configured for production domains only
- [ ] HTTPS configured (via reverse proxy/load balancer)
- [ ] Rate limiting enabled (`RATE_LIMIT_ENABLED=true`)
- [ ] Debug disabled (`DEBUG=false`)
- [ ] Environment set to production (`ENVIRONMENT=production`)

### Database Readiness

- [ ] PostgreSQL 15+ deployed (managed or self-hosted)
- [ ] Database connection verified
- [ ] All migrations applied (`alembic upgrade head`)
- [ ] Connection pool sized appropriately
- [ ] Automated backups configured
- [ ] Backup restore tested

### Cache Readiness

- [ ] Redis 7+ deployed (managed or self-hosted)
- [ ] Redis password authentication enabled
- [ ] Persistence configured (if needed)
- [ ] Connection verified

### Application Readiness

- [ ] Production Docker image built (`docker-compose.prod.yml build`)
- [ ] Health endpoint responding (`/health`)
- [ ] API replicas configured (2+ for HA)
- [ ] Resource limits set (memory, CPU)
- [ ] Logging configured (JSON format, log aggregation)

### Monitoring & Alerting

- [ ] Health endpoint monitored (interval: 30s)
- [ ] Log aggregation configured (ELK, CloudWatch, etc.)
- [ ] Error alerting enabled
- [ ] Performance metrics collected

### Backup & Recovery

- [ ] Database backup schedule configured
- [ ] Backup retention policy defined
- [ ] Restore procedure documented and tested
- [ ] Disaster recovery plan documented

### v1.2.0 Release Verification

```bash
# Verify build
docker build -f api/Dockerfile.prod -t defense-pm-tool-api:1.2.0 ./api

# Verify health endpoint
curl http://localhost:8000/health

# Verify API version
curl http://localhost:8000/ | jq '.version'

# Run smoke tests
curl http://localhost:8000/api/v1/programs -H "Authorization: Bearer $TOKEN"
```

---

## Troubleshooting

### Common Issues

#### Database Connection Refused

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection string
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

#### Redis Connection Failed

```bash
# Check Redis is running
docker-compose ps redis

# Test connection
redis-cli -h localhost ping
```

#### API Not Starting

```bash
# Check logs
docker-compose logs api

# Common issues:
# - DATABASE_URL not set
# - Migrations not applied
# - Port already in use
```

#### Slow CPM Calculations

```bash
# Check activity count
SELECT COUNT(*) FROM activities WHERE program_id = 'uuid';

# Check for missing indexes
EXPLAIN ANALYZE SELECT * FROM dependencies WHERE predecessor_id = 'uuid';

# Clear CPM cache
redis-cli KEYS "cpm:*" | xargs redis-cli DEL
```

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
uvicorn src.main:app --reload --log-level debug
```

### Support

For issues:
1. Check existing documentation
2. Search GitHub issues
3. Create new issue with:
   - Environment details
   - Steps to reproduce
   - Error messages/logs

---

## Backup and Restore (Production)

### Database Backup

```bash
# Self-hosted PostgreSQL
docker-compose -f docker-compose.prod.yml -f docker-compose.selfhosted.yml \
    exec postgres pg_dump -U $DB_USER $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql

# Managed PostgreSQL (adjust connection string)
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Database Restore

```bash
# Self-hosted PostgreSQL
docker-compose -f docker-compose.prod.yml -f docker-compose.selfhosted.yml \
    exec -T postgres psql -U $DB_USER $DB_NAME < backup_20260124_120000.sql

# Managed PostgreSQL
psql $DATABASE_URL < backup_20260124_120000.sql
```

### Automated Backup Script

Create `scripts/backup.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/defense_pm_$DATE.sql.gz"

# Create backup
pg_dump $DATABASE_URL | gzip > $BACKUP_FILE

# Keep only last 7 days
find $BACKUP_DIR -name "defense_pm_*.sql.gz" -mtime +7 -delete

echo "Backup created: $BACKUP_FILE"
```

---

*Defense PM Tool v1.2.0 - Last updated: March 2026*
