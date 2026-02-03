# Defense Program Management Tool

[![CI](https://github.com/jason-marshall/defense-pm-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/jason-marshall/defense-pm-tool/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.2.0-green.svg)](docs/RELEASE_NOTES_v1.2.0.md)
[![Coverage](https://img.shields.io/badge/coverage-81%25%2B-green.svg)](https://codecov.io/gh/jason-marshall/defense-pm-tool)
[![Tests](https://img.shields.io/badge/tests-2950%2B-green.svg)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)]()
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)]()

Enterprise-grade program management with EVMS (Earned Value Management System) compliance for defense contractors. Schedule optimization, Monte Carlo simulation, and CPR reporting.

## Features

### Core Capabilities (v1.0.0)

- **Program Management**: Create and manage defense programs with contract details
- **Work Breakdown Structure (WBS)**: Hierarchical WBS with PostgreSQL ltree for efficient queries
- **Activity & Dependency Management**: Full CRUD operations with all dependency types (FS, SS, FF, SF)
- **Critical Path Method (CPM) Engine**: Forward/backward pass with float calculation
- **EVMS Dashboard**: Real-time metrics including CPI, SPI, EAC, VAC, TCPI with trend charts
- **MS Project Import**: XML import with preview mode and validation
- **CPR Format 1, 3, 5 Reports**: Contract Performance Reports with PDF export

### Resource Management (v1.1.0)

- **Resource Tracking**: Labor, equipment, and material resources
- **Resource Assignment**: Allocate resources to activities
- **Resource Leveling**: Resolve overallocations automatically
- **Resource Histogram**: Visual utilization over time

### Advanced Resource Management (v1.2.0)

- **Resource Cost Tracking**: Automatic ACWP calculation from actuals
- **Material Tracking**: Quantity-based inventory management
- **MS Project Calendar Import**: Import resource calendars from XML
- **Parallel Leveling**: Optimized multi-resource leveling algorithm
- **Cross-Program Resource Pools**: Share resources with conflict detection
- **Gantt Resource View**: Visual drag-and-drop assignment editing

### Performance

- CPM calculation: <12ms for 1000 activities
- Dashboard load: <200ms
- Monte Carlo simulation: <5s for 1000 iterations
- All benchmarks GREEN

### Test Coverage

- 2950+ automated tests (unit, integration, E2E, security, performance)
- 81%+ code coverage
- Comprehensive E2E test suite for all workflows
- Performance benchmark tests (all GREEN)

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Pydantic 2.0
- **Frontend**: React 19 / TypeScript / TailwindCSS
- **Database**: PostgreSQL 15 with ltree extension
- **Cache**: Redis 7
- **Architecture**: Modular Monolith

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20 LTS
- Docker Desktop
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/defense-pm-tool.git
   cd defense-pm-tool
   ```

2. **Copy environment file**
   ```bash
   cp .env.example .env
   ```

3. **Start databases**
   ```bash
   docker-compose up -d postgres redis
   ```

4. **Setup backend**
   ```bash
   cd api
   python -m venv venv

   # Windows
   .\venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate

   pip install -r requirements.txt
   alembic upgrade head
   uvicorn src.main:app --reload
   ```

5. **Setup frontend** (new terminal)
   ```bash
   cd web
   npm install
   npm run dev
   ```

6. **Verify installation**
   - API Docs: http://localhost:8000/docs
   - Frontend: http://localhost:5173
   - Health Check: http://localhost:8000/health

## Development

### Running Tests

```bash
cd api

# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test categories
pytest -m cpm           # CPM engine tests
pytest -m evms          # EVMS calculation tests
pytest tests/e2e/       # End-to-end tests
```

### Code Quality

```bash
cd api

# Linting
ruff check src tests --fix
ruff format src tests

# Type checking
mypy src --ignore-missing-imports
```

### Performance Benchmarks

```bash
cd api
python scripts/run_benchmarks.py
```

## Project Structure

```
defense-pm-tool/
├── api/                        # FastAPI Backend
│   ├── src/
│   │   ├── main.py            # App entry point
│   │   ├── config.py          # Settings
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── repositories/      # Data access layer
│   │   ├── services/          # Business logic (CPM, EVMS)
│   │   ├── api/v1/            # Route handlers
│   │   └── core/              # Auth, deps, exceptions, cache
│   ├── tests/
│   │   ├── unit/              # Unit tests
│   │   ├── integration/       # API & DB tests
│   │   └── e2e/               # End-to-end tests
│   └── alembic/               # Migrations
├── web/                        # React Frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── hooks/             # Custom hooks
│   │   ├── services/          # API client
│   │   └── types/             # TypeScript types
│   └── tests/
├── docker/                     # Docker configuration
├── docs/                       # Documentation
└── scripts/                    # Utility scripts
```

## API Endpoints

| Category | Endpoints |
|----------|-----------|
| **Auth** | Register, Login, Refresh, Me |
| **Programs** | List, Get, Create, Update, Delete |
| **WBS** | List, Tree, Get, Create, Update, Delete |
| **Activities** | List, Get, Create, Update, Delete |
| **Dependencies** | List, Create, Update, Delete |
| **Schedule** | Calculate CPM, Critical Path, Duration |
| **EVMS** | Summary Dashboard, Periods, Period Data |
| **Import** | MS Project XML (preview + import) |
| **Reports** | CPR Format 1, 3, 5 (JSON, HTML, PDF) |
| **Variance** | Explanations CRUD, Management Reserve |
| **Jira** | Integration Config, Sync, Mappings, Webhooks |

See [API Guide](docs/API_GUIDE.md) for complete documentation.

## Documentation

- [API Guide](docs/API_GUIDE.md) - Complete REST API documentation (77+ endpoints)
- [Deployment Guide](docs/DEPLOYMENT.md) - Deployment and configuration
- [User Guide](docs/USER_GUIDE.md) - End-user documentation
- [Architecture](docs/Architecture.md) - System architecture
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Frontend Guide](docs/FRONTEND_GUIDE.md) - Frontend development standards
- [Upgrade Guide](docs/UPGRADE_GUIDE.md) - Version migration instructions
- [CPM Algorithm](docs/cpm-algorithm.md) - CPM implementation details
- [EVMS Formulas](docs/evms-formulas.md) - EVMS calculation specifications
- [Coding Standards](CLAUDE.md) - Development guidelines

## Environment Variables

Key configuration options (see `.env.example` for full list):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `SECRET_KEY` | JWT signing key | Required |
| `ENVIRONMENT` | development/staging/production | development |
| `DEBUG` | Enable debug mode | true |
| `CORS_ORIGINS` | Allowed CORS origins | localhost |

## Docker Deployment

```bash
# Development (databases only)
docker-compose up -d postgres redis

# Full stack
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

## Month 2 Features ✅

### Earned Value Management (EVMS)
- **6 EV Methods**: 0/100, 50/50, LOE, milestone weights, % complete, apportioned
- **6 EAC Methods**: CPI, typical, mathematical, comprehensive, independent, composite
- **Baseline Management**: Snapshots, version control, comparison
- **Time-phased Data**: Period tracking with cumulative calculations

### Monte Carlo Simulation
- **Schedule Risk Analysis**: 1000 iterations in <5 seconds
- **CPM Integration**: Network-aware simulation respecting dependencies
- **Sensitivity Analysis**: Correlation with project duration
- **Tornado Charts**: Visual schedule drivers
- **Confidence Bands**: P10/P50/P80/P90 forecasts

### Scenario Planning
- **What-if Analysis**: Branch scenarios from baseline
- **Scenario Simulation**: Run Monte Carlo on scenarios
- **Comparison**: Baseline vs scenario comparison

### Reporting
- **CPR Format 1**: WBS Summary report
- **CPR Format 3**: Time-phased Baseline report
- **S-curve Export**: PNG/SVG export with confidence bands
- **Dashboard**: <100ms load time with caching

### Test Coverage
- 1540+ automated tests (unit, integration, E2E)
- 81%+ code coverage
- Month 2 E2E integration test suite

---

## Month 3 Features ✅

### Week 10: Jira Integration

**Work Package Sync**
- Jira REST API client wrapper with encrypted token storage
- WBS Element to Epic mapping and bidirectional sync
- Activity to Issue mapping with progress tracking
- Variance alert to Jira Issue creation with priority mapping

**Real-time Updates**
- Webhook handler for Jira events (created, updated, deleted)
- Bi-directional status sync (Jira status ↔ percent complete)
- Audit trail for all sync operations

**API Endpoints**
| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/jira/integrations` | Configure Jira connection |
| `POST /api/v1/jira/integrations/{id}/sync` | Trigger sync operation |
| `POST /api/v1/webhooks/jira` | Receive Jira webhooks |
| `GET /api/v1/jira/integrations/{id}/logs` | View sync audit trail |

### Test Coverage
- 1700+ automated tests (unit, integration, E2E)
- 80%+ code coverage maintained
- Week 10 E2E integration test suite

---

### Week 11: Security & Scenario Promotion ✅

**Scenario Promotion Workflow**
- Promote scenarios to baseline with change tracking
- Apply scenario changes to program data
- Simulation and comparison of scenarios vs baseline

**Security Hardening**
- Input validation for XSS and SQL injection prevention
- Rate limiting with slowapi integration
- Maximum field length enforcement

**API Documentation**
- Complete OpenAPI documentation with error schemas
- Swagger UI and ReDoc accessibility
- All endpoints documented with responses

**Performance**
- All scenario operations under 10s (GREEN threshold)
- Performance benchmarks documented in PERFORMANCE.md

### Test Coverage
- 2700+ automated tests (unit, integration, E2E)
- 81%+ code coverage maintained
- Comprehensive E2E test suites for all features

---

## v1.1.0 Release (February 2026)

Defense PM Tool v1.1.0 adds **Resource Management** capabilities:
- Resource types (LABOR, EQUIPMENT, MATERIAL)
- Resource assignment to activities with allocation %
- Capacity calendars and scheduling
- Overallocation detection with period grouping
- Serial resource leveling algorithm
- Resource histogram visualization
- 5 new frontend components

See [Release Notes v1.1.0](docs/RELEASE_NOTES_v1.1.0.md) for complete details.

## v1.0.0 Release (January 2026)

Defense PM Tool v1.0.0 is **production-ready** with:
- Full EVMS compliance (ANSI/EIA-748)
- CPM scheduling with all 4 dependency types
- Monte Carlo simulation for schedule risk
- CPR Formats 1, 3, 5 with PDF export
- Jira Cloud integration
- JWT and API Key authentication
- OWASP Top 10 security compliance
- All performance benchmarks GREEN

See [Release Notes v1.0.0](docs/RELEASE_NOTES_v1.0.0.md) for complete details.

## Roadmap

### v1.2.0 (March 2026) - Advanced Resource Management ✅
- Resource cost integration with automatic ACWP ✅
- Material quantity tracking ✅
- MS Project calendar import ✅
- Parallel resource leveling algorithm ✅
- Cross-program resource pools ✅
- Gantt chart with resource view ✅

See [Release Notes v1.2.0](docs/RELEASE_NOTES_v1.2.0.md) for complete details.

### v1.1.0 (February 2026) - Resource Management ✅
- Resource model and CRUD operations ✅
- Resource assignment to activities ✅
- Capacity calendars ✅
- Serial resource leveling algorithm ✅
- Over-allocation detection ✅
- Resource histogram visualization ✅

## Contributing

See [CLAUDE.md](CLAUDE.md) for coding standards and development workflows.

## License

Proprietary - All rights reserved

---

*Defense PM Tool v1.2.0 - March 2026 - Advanced Resource Management Release*
