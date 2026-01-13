# Defense Program Management Tool

Schedule optimization and EVMS (Earned Value Management System) analysis for defense program management with DFARS compliance.

## Month 1 MVP Features

### Core Capabilities

- **Program Management**: Create and manage defense programs with contract details
- **Work Breakdown Structure (WBS)**: Hierarchical WBS with PostgreSQL ltree for efficient queries
- **Activity & Dependency Management**: Full CRUD operations with all dependency types (FS, SS, FF, SF)
- **Critical Path Method (CPM) Engine**: Forward/backward pass with float calculation
- **EVMS Dashboard**: Real-time metrics including CPI, SPI, EAC, VAC, TCPI with trend charts
- **MS Project Import**: XML import with preview mode and validation
- **CPR Format 1 Reports**: Contract Performance Reports (WBS Summary) in JSON/HTML

### Performance

- CPM calculation: <500ms for 1000 activities, <2000ms for 5000 activities
- Redis caching for CPM results and EVMS dashboard
- Efficient WBS queries with ltree extension

### Test Coverage

- 558+ automated tests (unit, integration, E2E)
- 80%+ code coverage
- Comprehensive E2E test suite for all workflows

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Pydantic 2.0
- **Frontend**: React 18 / TypeScript / TailwindCSS
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
| **Reports** | CPR Format 1 (JSON, HTML) |

See [API Reference](docs/api.md) for complete documentation.

## Documentation

- [API Reference](docs/api.md) - Complete REST API documentation
- [Deployment Guide](docs/DEPLOYMENT.md) - Deployment and configuration
- [User Guide](docs/USER_GUIDE.md) - End-user documentation
- [Architecture](docs/Architecture.md) - System architecture
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

## Roadmap

### Month 2 (Planned)

- Resource management and assignments
- Gantt chart visualization
- What-if analysis
- Baseline management

### Month 3 (Planned)

- Calendar integration
- Email notifications
- Advanced reporting (CPR Formats 2-5)
- Audit logging

## Contributing

See [CLAUDE.md](CLAUDE.md) for coding standards and development workflows.

## License

Proprietary - All rights reserved

---

*Defense PM Tool v0.1.0 - January 2026*
