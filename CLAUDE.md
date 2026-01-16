# Defense Program Management Tool - Claude Code Instructions

> **Project**: Defense PM Tool with EVMS/CPM capabilities
> **Repository**: https://github.com/jason-marshall/defense-pm-tool
> **Developer**: Single developer, 3-month timeline
> **Current Phase**: Month 2, Week 6 - Monte Carlo Integration & Scenario Analysis

---

## Quick Reference

```bash
# Start development environment
docker-compose up -d

# Run verification ladder (always run before commits)
cd api
ruff check src tests --fix && ruff format src tests
mypy src --ignore-missing-imports
pytest tests/unit -v
pytest tests/integration -v
pytest --cov=src --cov-report=term-missing

# Database operations
alembic upgrade head          # Apply migrations
alembic downgrade -1          # Rollback one migration
alembic revision --autogenerate -m "description"  # Create migration

# API server
uvicorn src.main:app --reload --port 8000

# Frontend (when implemented)
cd web && npm run dev
```

---

## Project Structure

```
defense-pm-tool/
├── CLAUDE.md                    # This file - Claude Code reads this automatically
├── docker-compose.yml           # PostgreSQL + Redis + API containers
├── .env.example                 # Environment template
│
├── api/                         # Backend (FastAPI + Python 3.11+)
│   ├── alembic/                 # Database migrations
│   │   ├── versions/            # Migration files (001_initial.py, etc.)
│   │   └── env.py
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py    # API router aggregation
│   │   │       └── endpoints/   # Route handlers
│   │   │           ├── activities.py
│   │   │           ├── auth.py
│   │   │           ├── dependencies.py
│   │   │           ├── programs.py
│   │   │           └── health.py
│   │   ├── core/                # Configuration & utilities
│   │   │   ├── config.py        # Settings via pydantic-settings
│   │   │   ├── database.py      # Async SQLAlchemy session
│   │   │   ├── auth.py          # JWT utilities, password hashing
│   │   │   ├── deps.py          # FastAPI dependencies (get_current_user, etc.)
│   │   │   └── exceptions.py    # Custom exception hierarchy
│   │   ├── models/              # SQLAlchemy 2.0 models
│   │   │   ├── base.py          # Base model with id, timestamps, soft delete
│   │   │   ├── user.py
│   │   │   ├── program.py
│   │   │   ├── wbs.py           # Work Breakdown Structure (ltree)
│   │   │   ├── activity.py
│   │   │   ├── dependency.py
│   │   │   └── enums.py         # DependencyType, ConstraintType, etc.
│   │   ├── schemas/             # Pydantic v2 schemas
│   │   │   ├── activity.py      # ActivityCreate, ActivityResponse, etc.
│   │   │   ├── dependency.py
│   │   │   ├── program.py
│   │   │   └── user.py
│   │   ├── repositories/        # Data access layer
│   │   │   ├── base.py          # BaseRepository[T] with CRUD
│   │   │   ├── activity.py
│   │   │   ├── dependency.py
│   │   │   ├── program.py
│   │   │   └── user.py
│   │   └── services/            # Business logic
│   │       ├── cpm.py           # Critical Path Method engine
│   │       └── evms.py          # Earned Value calculations
│   ├── tests/
│   │   ├── conftest.py          # Pytest fixtures
│   │   ├── unit/                # Unit tests (no DB)
│   │   │   ├── test_cpm.py      # ✅ Comprehensive CPM tests
│   │   │   └── test_evms.py     # ✅ EVMS calculation tests
│   │   └── integration/         # Integration tests (with DB)
│   │       ├── test_activities_api.py
│   │       └── test_auth_api.py
│   ├── requirements.txt         # Python dependencies (pinned)
│   ├── pyproject.toml           # Ruff, mypy, pytest config
│   └── Dockerfile
│
├── web/                         # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── pages/               # Route pages
│   │   ├── hooks/               # Custom React hooks
│   │   ├── services/            # API client
│   │   ├── types/               # TypeScript interfaces
│   │   └── utils/               # Helper functions
│   ├── package.json
│   └── vite.config.ts
│
└── docs/                        # Documentation
    ├── ARCHITECTURE.md          # System design, ERD, components
    ├── TDD_PLAN.md              # Development prompts & milestones
    └── prompts/                 # Week-by-week prompts
        └── WEEK2.md
```

---

## Coding Standards

### Python (Backend)

```python
# Imports: stdlib → third-party → local (blank line between groups)
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import DbSession, get_current_user
from src.models.activity import Activity
from src.schemas.activity import ActivityCreate, ActivityResponse

# Type hints: Required on all functions
async def get_activity(
    activity_id: UUID,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> ActivityResponse:
    """
    Get a single activity by ID.
    
    Args:
        activity_id: UUID of the activity to retrieve
        db: Database session (injected)
        current_user: Authenticated user (injected)
        
    Returns:
        ActivityResponse with activity details
        
    Raises:
        NotFoundError: If activity doesn't exist
        AuthorizationError: If user doesn't have access
    """
    ...

# Naming conventions
class ActivityRepository:     # PascalCase for classes
    async def get_by_id():    # snake_case for functions/methods
        activity_name = ""    # snake_case for variables
        MAX_PAGE_SIZE = 100   # UPPER_SNAKE for constants

# Decimal for money - NEVER use float
budgeted_cost: Decimal = Decimal("10000.00")
earned_value = budgeted_cost * (percent_complete / Decimal("100"))

# Async everywhere for I/O
async def create_activity(...) -> Activity:
    result = await self.session.execute(...)
    await self.session.commit()
    return result
```

### TypeScript (Frontend)

```typescript
// Explicit types, no 'any'
interface Activity {
  id: string;
  name: string;
  duration: number;
  earlyStart: number | null;
  isCritical: boolean;
}

// Functional components with typed props
interface GanttChartProps {
  activities: Activity[];
  onActivityClick: (id: string) => void;
}

const GanttChart: React.FC<GanttChartProps> = ({ activities, onActivityClick }) => {
  // Component implementation
};

// Custom hooks for data fetching
const useActivities = (programId: string) => {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  
  useEffect(() => {
    // Fetch logic
  }, [programId]);
  
  return { activities, loading, error };
};
```

---

## Architecture Patterns

### Layered Architecture (Backend)

```
Request → Router → Endpoint → Repository → Model → Database
                      ↓
                   Service (business logic)
```

**Endpoints** (`api/v1/endpoints/`): HTTP handling, auth, validation
```python
@router.post("", response_model=ActivityResponse, status_code=201)
async def create_activity(
    activity_in: ActivityCreate,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> ActivityResponse:
    # Validate authorization
    # Call repository
    # Return response
```

**Repositories** (`repositories/`): Data access, queries
```python
class ActivityRepository(BaseRepository[Activity]):
    async def get_by_program(self, program_id: UUID) -> list[Activity]:
        result = await self.session.execute(
            select(Activity)
            .where(Activity.program_id == program_id)
            .where(Activity.deleted_at.is_(None))
        )
        return list(result.scalars().all())
```

**Services** (`services/`): Business logic, calculations
```python
class CPMEngine:
    def calculate(self) -> dict[UUID, ScheduleResult]:
        self._forward_pass()
        self._backward_pass()
        self._calculate_float()
        return self._results
```

### Exception Hierarchy

```python
from src.core.exceptions import (
    AppException,           # Base - all custom exceptions inherit from this
    NotFoundError,          # 404 - Resource not found
    ValidationError,        # 400 - Invalid input
    AuthenticationError,    # 401 - Not authenticated
    AuthorizationError,     # 403 - Not authorized
    ConflictError,          # 409 - Duplicate/conflict
    CircularDependencyError,# 400 - Cycle detected in dependencies
)

# Usage
if not activity:
    raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")

if would_create_cycle:
    raise CircularDependencyError(cycle_path)
```

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    User     │       │   Program   │       │     WBS     │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │──┐    │ id (PK)     │──┐    │ id (PK)     │
│ email       │  │    │ owner_id(FK)│◄─┘    │ program_id  │◄─┐
│ full_name   │  │    │ code        │       │ path (ltree)│  │
│ hashed_pass │  │    │ name        │       │ code        │  │
│ is_active   │  │    │ start_date  │       │ name        │  │
│ is_admin    │  │    │ end_date    │       │ level       │  │
└─────────────┘  │    │ status      │       └─────────────┘  │
                 │    └─────────────┘                        │
                 │           │                               │
                 └───────────┼───────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Activity     │
                    ├─────────────────┤
                    │ id (PK)         │
                    │ program_id (FK) │◄── Direct FK for query efficiency
                    │ wbs_id (FK)     │
                    │ code            │    Unique within program
                    │ name            │
                    │ duration        │    Working days
                    │ percent_complete│    Decimal 0-100
                    │ budgeted_cost   │    Decimal (BCWS)
                    │ actual_cost     │    Decimal (ACWP)
                    │ constraint_type │    ASAP, SNET, FNLT, etc.
                    │ constraint_date │
                    │ early_start     │    CPM calculated
                    │ early_finish    │
                    │ late_start      │
                    │ late_finish     │
                    │ total_float     │
                    │ free_float      │
                    │ is_critical     │
                    │ is_milestone    │
                    └─────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Dependency    │
                    ├─────────────────┤
                    │ id (PK)         │
                    │ predecessor_id  │◄── FK to Activity
                    │ successor_id    │◄── FK to Activity
                    │ dependency_type │    FS, FF, SS, SF
                    │ lag             │    Days (can be negative)
                    └─────────────────┘
```

### Key Constraints

- `activities.program_id + activities.code` → UNIQUE (when not deleted)
- `dependencies.predecessor_id + dependencies.successor_id` → UNIQUE
- WBS uses PostgreSQL `ltree` for hierarchical paths (e.g., "1.2.3")
- All tables have soft delete via `deleted_at` timestamp

---

## Testing Requirements

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # No database, fast
│   ├── test_cpm.py          # CPM engine logic
│   ├── test_evms.py         # EVMS calculations
│   └── test_schemas.py      # Pydantic validation
└── integration/             # With database, slower
    ├── test_activities_api.py
    ├── test_dependencies_api.py
    └── test_auth_api.py
```

### Test Pattern (AAA)

```python
class TestActivityCreate:
    """Tests for activity creation."""
    
    async def test_create_activity_success(self, client: AsyncClient, auth_headers: dict):
        """Should create activity with valid data."""
        # Arrange
        program_id = await create_test_program(client, auth_headers)
        activity_data = {
            "program_id": program_id,
            "name": "Design Review",
            "code": "DR-001",
            "duration": 5,
        }
        
        # Act
        response = await client.post(
            "/api/v1/activities",
            headers=auth_headers,
            json=activity_data,
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Design Review"
        assert data["code"] == "DR-001"
```

### Coverage Targets

| Week | Overall | New Code |
|------|---------|----------|
| 1    | 40%     | 80%      |
| 2    | 60%     | 80%      |
| 3    | 75%     | 80%      |
| 4    | 80%     | 80%      |

---

## Verification Ladder

**Run ALL levels before every commit:**

```bash
cd api

# Level 1: Static Analysis
ruff check src tests --fix
ruff format src tests

# Level 2: Type Checking  
mypy src --ignore-missing-imports

# Level 3: Unit Tests
pytest tests/unit -v

# Level 4: Integration Tests
pytest tests/integration -v

# Level 5: Coverage
pytest --cov=src --cov-report=term-missing --cov-fail-under=60

# Level 6: Manual Verification (API testing)
# curl or httpie commands as needed
```

---

## Git Workflow

### Branch Naming

```
feature/activity-crud       # New features
bugfix/cpm-float-calc       # Bug fixes
hotfix/model-alignment      # Urgent fixes
refactor/repository-pattern # Code improvements
```

### Commit Messages (Conventional Commits)

```bash
# Format: type(scope): description
git commit -m "feat(activities): implement activity CRUD with authentication"
git commit -m "fix(cpm): correct backward pass float calculation"
git commit -m "test(dependencies): add cycle detection tests"
git commit -m "refactor(repos): extract base repository pattern"
git commit -m "docs(api): add endpoint documentation"

# Types: feat, fix, test, refactor, docs, chore, perf
# Scopes: activities, dependencies, cpm, evms, auth, api, models, schemas, frontend
```

### Workflow

```bash
# 1. Create branch from main
git checkout main
git pull
git checkout -b feature/new-feature

# 2. Make changes with atomic commits
git add .
git commit -m "feat(scope): description"

# 3. Push and create PR
git push -u origin feature/new-feature
# Create PR via GitHub

# 4. After merge, clean up
git checkout main
git pull
git branch -d feature/new-feature
```

---

## Domain-Specific Rules

### CPM (Critical Path Method)

```python
# Dependency Types
FS = "Finish-to-Start"   # Most common: B starts after A finishes
FF = "Finish-to-Finish"  # B finishes when A finishes
SS = "Start-to-Start"    # B starts when A starts
SF = "Start-to-Finish"   # Rare: B finishes when A starts

# Forward Pass: Calculate Early Start (ES) and Early Finish (EF)
ES = max(EF of all predecessors + lag)
EF = ES + duration

# Backward Pass: Calculate Late Start (LS) and Late Finish (LF)
LF = min(LS of all successors - lag)
LS = LF - duration

# Float
Total Float = LS - ES = LF - EF  # Delay without affecting project end
Free Float = min(ES of successors) - EF  # Delay without affecting successors
Critical Path = activities where Total Float = 0
```

### EVMS (Earned Value Management)

```python
from decimal import Decimal

# Core Metrics (all Decimal, never float)
BCWS = budgeted_cost                           # Planned Value (PV)
BCWP = budgeted_cost * (percent_complete/100)  # Earned Value (EV)
ACWP = actual_cost                             # Actual Cost (AC)

# Variances
CV = BCWP - ACWP   # Cost Variance (negative = over budget)
SV = BCWP - BCWS   # Schedule Variance (negative = behind schedule)

# Performance Indices
CPI = BCWP / ACWP  # Cost Performance Index (< 1.0 = over budget)
SPI = BCWP / BCWS  # Schedule Performance Index (< 1.0 = behind schedule)

# Estimates at Completion
EAC = BAC / CPI              # Estimate at Completion
ETC = EAC - ACWP             # Estimate to Complete
VAC = BAC - EAC              # Variance at Completion
TCPI = (BAC - BCWP) / (BAC - ACWP)  # To-Complete Performance Index
```

### WBS (Work Breakdown Structure)

```python
# PostgreSQL ltree paths
"1"         # Level 1: Program
"1.1"       # Level 2: Phase
"1.1.1"     # Level 3: Work Package
"1.1.1.1"   # Level 4: Task

# Query descendants
SELECT * FROM wbs WHERE path <@ '1.1';  # All under 1.1

# Query ancestors
SELECT * FROM wbs WHERE '1.1.1' <@ path;  # Parents of 1.1.1
```

---

## Security Guidelines

1. **Authentication**: JWT tokens with bcrypt password hashing
2. **Authorization**: Check `program.owner_id == current_user.id` or `is_admin`
3. **Input Validation**: Pydantic schemas validate all input
4. **SQL Injection**: Use SQLAlchemy ORM, never raw SQL with user input
5. **Secrets**: Never commit `.env`, use environment variables
6. **CORS**: Configure allowed origins in production

---

## Common Issues & Solutions

### Docker Issues

```bash
# Port 5432 in use
docker-compose down
# Or: Change port in docker-compose.yml

# Database won't start (leftover volume)
docker-compose down -v  # Removes volumes
docker-compose up -d

# Check container logs
docker-compose logs api
docker-compose logs postgres
```

### Database Issues

```bash
# Migration conflicts
alembic downgrade base
alembic upgrade head

# Check current revision
alembic current

# Generate new migration
alembic revision --autogenerate -m "description"
```

### Test Issues

```bash
# Test database connection issues
docker exec -it defense-pm-tool-postgres psql -U dev_user -d defense_pm_dev

# Run single test
pytest tests/unit/test_cpm.py::TestCPMEngine::test_forward_pass -v

# Show print output
pytest -v -s
```

---

## Current Development Status

### ✅ Completed (Week 1)
- [x] Project structure and Docker setup
- [x] PostgreSQL with ltree extension
- [x] SQLAlchemy 2.0 async models (User, Program, WBS, Activity, Dependency)
- [x] Pydantic v2 schemas with validation
- [x] Repository pattern with BaseRepository
- [x] CPM engine with all 4 dependency types
- [x] EVMS calculator with Decimal precision
- [x] JWT authentication utilities
- [x] Initial Alembic migration
- [x] Unit tests for CPM and EVMS

### ✅ Completed (Week 2)
- [x] Model-schema alignment fixes
- [x] Activity CRUD with authentication
- [x] Dependency CRUD with cycle detection
- [x] Schedule calculation endpoint
- [x] 157 tests passing, 71% coverage

### ✅ Completed (Week 3)
- [x] WBS CRUD with ltree hierarchy
- [x] WBS Tree visualization component
- [x] EVMS period tracking
- [x] EVMS dashboard with metrics
- [x] CPR Format 1 report generation
- [x] Week 3 integration tests
- [x] 486 tests passing, 75%+ coverage achieved

### ✅ Completed (Week 4)
- [x] Performance optimization
- [x] MS Project XML import
- [x] End-to-end tests
- [x] Redis caching infrastructure
- [x] Documentation complete

### ✅ Completed (Month 2 - Week 5)
- [x] Multiple EV methods (0/100, 50/50, LOE, milestone weights, % complete)
- [x] Baseline management model & CRUD with JSONB snapshots
- [x] Baseline comparison service for variance analysis
- [x] Scenario planning foundation (model, repository, schemas)
- [x] Monte Carlo engine with NumPy vectorization
- [x] Support for triangular, PERT, normal, uniform distributions
- [x] EVMS reference validation test suite (59 tests)
- [x] Industry-standard EVMS reference data fixture
- [x] 1173 tests passing (1032 unit + 141 integration)
- [x] 80% test coverage achieved

### ✅ Completed (Month 2 - Week 6)
- [x] Monte Carlo API endpoints (run simulation, get results)
- [x] CPM + Monte Carlo integration for schedule risk
- [x] Advanced EAC methods (CPI, Typical, Mathematical, Comprehensive, Independent, Composite)
- [x] EVMS validation against reference data (0.5% tolerance per Risk Playbook)
- [x] Scenario simulation with what-if analysis (simulate, compare endpoints)
- [x] S-curve confidence bands from Monte Carlo results
- [x] Enhanced S-curve endpoint with EAC/completion date ranges
- [x] 1133+ unit tests passing, 80%+ coverage maintained

---

## Performance Baselines (Week 3)

Established baselines for Week 4 optimization targets:

| Benchmark | Current | Target | Status |
|-----------|---------|--------|--------|
| CPM 100 activities (chain) | 1.86ms | <50ms | ✅ |
| CPM 500 activities (chain) | 5.77ms | <200ms | ✅ |
| CPM 1000 activities (chain) | 11.88ms | <500ms | ✅ |
| CPM 1000 activities (parallel) | 14.06ms | <500ms | ✅ |
| CPM 2000 activities (chain) | 26.71ms | <1000ms | ✅ |
| CPM 5000 activities (chain) | 83.65ms | <2000ms | ✅ |
| Graph construction (1000 nodes) | 5.43ms | <100ms | ✅ |
| EVMS calculations (1000 items) | 1.52ms | <100ms | ✅ |

Run benchmarks: `cd api && python scripts/run_benchmarks.py`

---

## Important Notes for Claude Code

1. **Always run verification ladder** before suggesting code is complete
2. **TDD approach**: Write tests first, then implementation
3. **Decimal for money**: Never use float for financial calculations
4. **Async everywhere**: All database operations must be async
5. **Type hints required**: All functions need parameter and return types
6. **Check authorization**: Every endpoint must verify user access
7. **Soft deletes**: Use `deleted_at` timestamp, not hard deletes
8. **Atomic commits**: One logical change per commit
9. **Run benchmarks**: Before performance changes, run `python scripts/run_benchmarks.py`

---

*Last Updated: January 2026*
*Month 2, Week 6 Complete - 1133+ tests, 80%+ coverage*
