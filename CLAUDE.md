# Defense Program Management Tool - CLAUDE.md

> **Project**: Defense Program Management Tool with EVMS/DFARS Compliance
> **Stack**: Python 3.11+ / FastAPI / React 18 / TypeScript / PostgreSQL 15 / Redis
> **Architecture**: Modular Monolith with Schedule Manager, CPM Engine, EVMS Calculator

---

## Quick Reference

```bash
# Start development environment
docker-compose up -d                    # Start PostgreSQL + Redis
cd api && source venv/bin/activate      # Activate Python venv
uvicorn src.main:app --reload           # Start backend (port 8000)
cd web && npm run dev                   # Start frontend (port 5173)

# Testing
cd api && pytest                        # Run all backend tests
cd api && pytest -m cpm                 # Run CPM engine tests only
cd api && pytest --cov=src --cov-report=html  # With coverage
cd web && npm test                      # Run frontend tests

# Linting & Type Checking
cd api && ruff check src tests          # Python linting
cd api && mypy src                      # Python type checking
cd web && npm run lint                  # TypeScript/React linting

# Database
alembic upgrade head                    # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
```

---

## Project Structure

```
defense-pm-tool/
├── api/                        # FastAPI Backend
│   ├── src/
│   │   ├── main.py            # App entry point
│   │   ├── config.py          # Pydantic settings
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── repositories/      # Data access layer
│   │   ├── services/          # Business logic (CPM, EVMS)
│   │   ├── api/v1/            # Route handlers
│   │   └── core/              # Auth, deps, exceptions
│   ├── tests/
│   │   ├── unit/              # Unit tests
│   │   ├── integration/       # API & DB tests
│   │   └── conftest.py        # Fixtures
│   └── alembic/               # Migrations
├── web/                        # React Frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── hooks/             # Custom hooks
│   │   ├── api/               # API client
│   │   └── types/             # TypeScript types
│   └── tests/
└── docs/                       # Documentation
```

---

## Coding Standards

### Python (Backend)

#### Style Rules
- Use Python 3.11+ features: type hints, match statements, `Self` type
- All functions must have type hints for parameters AND return values
- Use `async def` for all database and I/O operations
- Prefer `Annotated` types for FastAPI dependencies
- Maximum line length: 100 characters
- Use double quotes for strings consistently

#### Naming Conventions
```python
# Classes: PascalCase
class ActivityRepository:
    pass

# Functions/methods: snake_case
async def calculate_critical_path(activities: list[Activity]) -> list[Activity]:
    pass

# Constants: SCREAMING_SNAKE_CASE
MAX_WBS_DEPTH = 10
CPM_CALCULATION_TIMEOUT = 30

# Private methods: single underscore prefix
def _build_dependency_graph(self) -> nx.DiGraph:
    pass

# Type aliases: PascalCase
ActivityDict = dict[UUID, Activity]
```

#### Import Order
```python
# 1. Standard library
from datetime import datetime
from typing import Annotated
from uuid import UUID

# 2. Third-party packages
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import networkx as nx

# 3. Local application imports
from src.models import Activity, Dependency
from src.core.deps import get_db
```

#### Docstring Format
```python
def calculate_forward_pass(
    activities: list[Activity],
    dependencies: list[Dependency]
) -> dict[UUID, ScheduleResult]:
    """
    Calculate Early Start (ES) and Early Finish (EF) for all activities.
    
    Uses topological sort to process activities in dependency order.
    Handles all dependency types: FS, SS, FF, SF with lag/lead.
    
    Args:
        activities: List of activities with duration and constraints
        dependencies: List of dependencies between activities
        
    Returns:
        Dictionary mapping activity ID to ScheduleResult with ES/EF values
        
    Raises:
        CircularDependencyError: If dependency graph contains cycles
        
    Example:
        >>> results = calculate_forward_pass(activities, deps)
        >>> results[activity_id].early_start
        5
    """
```

### TypeScript (Frontend)

#### Style Rules
- Use functional components with hooks exclusively
- Prefer `interface` over `type` for object shapes
- Use `const` assertions for literal types
- Destructure props in function parameters
- Use named exports (not default exports)

#### Naming Conventions
```typescript
// Components: PascalCase
export function GanttChart({ activities, onActivityClick }: GanttChartProps) {}

// Hooks: camelCase with 'use' prefix
export function useActivities(programId: string) {}

// Types/Interfaces: PascalCase
interface ActivityResponse {
  id: string;
  name: string;
  earlyStart: string;  // ISO date
}

// Constants: SCREAMING_SNAKE_CASE
const API_BASE_URL = '/api/v1';

// Event handlers: handle + Event
const handleActivityDragEnd = (event: DragEndEvent) => {};
```

---

## Error Handling

### Backend Error Hierarchy

```python
# src/core/exceptions.py

class DomainError(Exception):
    """Base class for all domain errors."""
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)

class ValidationError(DomainError):
    """Invalid input data."""
    pass

class NotFoundError(DomainError):
    """Resource not found."""
    pass

class ConflictError(DomainError):
    """Resource conflict (duplicate, etc.)."""
    pass

class CircularDependencyError(DomainError):
    """Circular dependency detected in schedule."""
    def __init__(self, cycle_path: list[UUID]):
        self.cycle_path = cycle_path
        super().__init__(
            f"Circular dependency: {' -> '.join(str(id) for id in cycle_path)}",
            "CIRCULAR_DEPENDENCY"
        )

class ScheduleCalculationError(DomainError):
    """Error during CPM calculation."""
    pass
```

### Error Response Format

```python
# All API errors return consistent JSON structure
{
    "detail": "Human-readable error message",
    "code": "MACHINE_READABLE_CODE",
    "field_errors": [  # Optional, for validation errors
        {"field": "duration", "message": "Must be >= 0"}
    ]
}
```

### Exception Handler Registration

```python
# src/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    status_map = {
        ValidationError: 422,
        NotFoundError: 404,
        ConflictError: 409,
        CircularDependencyError: 400,
    }
    return JSONResponse(
        status_code=status_map.get(type(exc), 400),
        content={"detail": exc.message, "code": exc.code}
    )
```

---

## Logging Standards

### Configuration

```python
# src/core/logging.py
import logging
import structlog
from src.config import settings

def configure_logging():
    """Configure structured logging for the application."""
    
    # Processors for all environments
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if settings.ENVIRONMENT == "production":
        # JSON output for production (ELK, Datadog, etc.)
        processors = shared_processors + [
            structlog.processors.JSONRenderer()
        ]
    else:
        # Pretty console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Usage
logger = structlog.get_logger()
```

### Logging Guidelines

```python
# ✅ DO: Include context with structured data
logger.info(
    "cpm_calculation_complete",
    program_id=str(program_id),
    activity_count=len(activities),
    duration_ms=elapsed_ms,
    critical_path_length=len(critical_path)
)

# ✅ DO: Log at appropriate levels
logger.debug("forward_pass_started", node_count=len(graph.nodes))
logger.info("activity_created", activity_id=str(activity.id))
logger.warning("near_critical_activity", activity_id=str(id), float_days=3)
logger.error("cpm_calculation_failed", error=str(e), program_id=str(id))

# ❌ DON'T: Log sensitive data
logger.info("user_login", password=password)  # NEVER

# ❌ DON'T: Use string formatting
logger.info(f"Activity {activity_id} created")  # Use structured instead

# ❌ DON'T: Log inside tight loops
for activity in activities:
    logger.debug("processing", id=activity.id)  # Too noisy
```

### Request Logging Middleware

```python
# src/core/middleware.py
import time
from uuid import uuid4
import structlog
from starlette.middleware.base import BaseHTTPMiddleware

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        logger = structlog.get_logger()
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2)
        )
        
        response.headers["X-Request-ID"] = request_id
        return response
```

---

## Testing Requirements

### Coverage Targets
| Module | Target | Rationale |
|--------|--------|-----------|
| `services/cpm.py` | 90%+ | Core algorithm - correctness critical |
| `services/evms.py` | 90%+ | Financial calculations - audit requirements |
| `models/` | 85%+ | Validation logic needs thorough testing |
| `repositories/` | 80%+ | Data access layer |
| `api/` | 75%+ | E2E tests provide additional coverage |
| **Overall** | 80%+ | Project minimum |

### Test File Naming
```
tests/
├── unit/
│   ├── test_cpm_forward_pass.py
│   ├── test_cpm_backward_pass.py
│   ├── test_evms_calculations.py
│   └── test_activity_validation.py
├── integration/
│   ├── test_activity_api.py
│   ├── test_program_workflow.py
│   └── test_cpm_integration.py
└── e2e/
    └── test_schedule_creation.py
```

### Test Structure (AAA Pattern)

```python
class TestForwardPass:
    """Tests for CPM forward pass calculation."""
    
    def test_simple_chain_calculates_correct_dates(self):
        """A(5d) -> B(3d) -> C(2d) should give ES/EF: 0/5, 5/8, 8/10."""
        # Arrange
        activities = [
            Activity(id=uuid4(), name="A", duration=5),
            Activity(id=uuid4(), name="B", duration=3),
            Activity(id=uuid4(), name="C", duration=2),
        ]
        dependencies = [
            Dependency(predecessor_id=activities[0].id, 
                      successor_id=activities[1].id, type=DependencyType.FS),
            Dependency(predecessor_id=activities[1].id, 
                      successor_id=activities[2].id, type=DependencyType.FS),
        ]
        engine = CPMEngine(activities, dependencies)
        
        # Act
        result = engine.forward_pass()
        
        # Assert
        assert result[activities[0].id].early_start == 0
        assert result[activities[0].id].early_finish == 5
        assert result[activities[1].id].early_start == 5
        assert result[activities[1].id].early_finish == 8
        assert result[activities[2].id].early_start == 8
        assert result[activities[2].id].early_finish == 10
```

### Pytest Markers

```python
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests (no external dependencies)",
    "integration: Integration tests (requires database)",
    "slow: Tests that take > 1 second",
    "cpm: CPM engine tests",
    "evms: EVMS calculation tests",
]

# Usage
@pytest.mark.cpm
@pytest.mark.unit
def test_forward_pass_simple():
    ...

# Run specific markers
# pytest -m "cpm and not slow"
```

---

## Verification Ladder

Before marking any task complete, verify at each level:

### Level 1: Syntax & Types
```bash
ruff check src tests           # No linting errors
mypy src --strict              # No type errors
```

### Level 2: Unit Tests
```bash
pytest tests/unit -v           # All unit tests pass
pytest --cov=src               # Coverage meets targets
```

### Level 3: Integration Tests
```bash
pytest tests/integration -v    # All integration tests pass
```

### Level 4: Manual Verification
- [ ] Feature works as expected in browser/API client
- [ ] Edge cases handled (empty inputs, invalid data)
- [ ] Error messages are clear and helpful

### Level 5: Code Quality
- [ ] No hardcoded values (use constants/config)
- [ ] No commented-out code
- [ ] Docstrings on public functions
- [ ] No TODO comments (create issues instead)

---

## Git Workflow

### Branch Naming
```
feature/DPM-123-add-gantt-chart
bugfix/DPM-456-fix-cpm-calculation
refactor/DPM-789-optimize-queries
hotfix/DPM-999-security-patch
```

### Commit Message Format
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`

Examples:
```
feat(cpm): implement forward pass with all dependency types

- Add support for FS, SS, FF, SF dependencies
- Handle positive and negative lag
- Detect circular dependencies

Closes #123
```

```
fix(evms): correct SPI calculation when BCWS is zero

Return None instead of raising ZeroDivisionError.
Add unit test for edge case.

Fixes #456
```

---

## PR Template

When creating PRs, use this template (saved as `.github/PULL_REQUEST_TEMPLATE.md`):

```markdown
## Description
<!-- Brief description of changes and why they're needed -->

## Type of Change
- [ ] 🐛 Bug fix (non-breaking change fixing an issue)
- [ ] ✨ New feature (non-breaking change adding functionality)
- [ ] 💥 Breaking change (fix or feature causing existing functionality to change)
- [ ] 📝 Documentation update
- [ ] ♻️ Refactoring (no functional changes)
- [ ] 🧪 Test update

## Related Issues
<!-- Link to related issues: Fixes #123, Relates to #456 -->

## Changes Made
<!-- List the specific changes made -->
- 
- 

## Testing
<!-- How was this tested? -->
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Verification Checklist
- [ ] `ruff check` passes
- [ ] `mypy` passes
- [ ] All tests pass
- [ ] Coverage meets targets
- [ ] Documentation updated (if needed)
- [ ] No hardcoded values
- [ ] Error handling is appropriate

## Screenshots (if applicable)
<!-- Add screenshots for UI changes -->

## Notes for Reviewers
<!-- Any specific areas to focus on? -->
```

---

## Domain-Specific Rules

### CPM Engine

```python
# All CPM calculations must:
# 1. Use NetworkX for graph operations
# 2. Handle all 4 dependency types (FS, SS, FF, SF)
# 3. Support positive and negative lag
# 4. Detect cycles before calculation
# 5. Complete in <500ms for 1000 activities

from enum import Enum

class DependencyType(str, Enum):
    FS = "FS"  # Finish-to-Start (most common)
    SS = "SS"  # Start-to-Start
    FF = "FF"  # Finish-to-Finish
    SF = "SF"  # Start-to-Finish (rare)

# Dependency formulas:
# FS: successor.ES = predecessor.EF + lag
# SS: successor.ES = predecessor.ES + lag
# FF: successor.EF = predecessor.EF + lag
# SF: successor.EF = predecessor.ES + lag
```

### EVMS Calculations

```python
# All EVMS metrics must:
# 1. Use Decimal for financial calculations (not float)
# 2. Handle division by zero gracefully (return None)
# 3. Round to 2 decimal places for display
# 4. Support all EV methods: 0/100, 50/50, % complete, milestone

from decimal import Decimal, ROUND_HALF_UP

def calculate_spi(bcwp: Decimal, bcws: Decimal) -> Decimal | None:
    """Schedule Performance Index = BCWP / BCWS."""
    if bcws == 0:
        return None
    return (bcwp / bcws).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

### WBS Hierarchy

```python
# WBS uses PostgreSQL ltree for efficient hierarchy queries
# Path format: "1.2.3.4" representing WBS code hierarchy

# Efficient queries using ltree:
# - Get all descendants: WHERE path <@ '1.2'
# - Get all ancestors: WHERE '1.2.3.4' <@ path
# - Get direct children: WHERE path ~ '1.2.*{1}'
```

---

## Security Guidelines

### Never Commit
- API keys, passwords, secrets
- .env files with real credentials
- Database dumps with real data
- Private keys or certificates

### Input Validation
- Validate all user input at API boundary
- Use Pydantic models for automatic validation
- Sanitize file uploads (MS Project XML)
- Escape output to prevent XSS

### Authentication
- JWT tokens expire in 15 minutes
- Refresh tokens expire in 7 days
- Passwords hashed with bcrypt (cost factor 12)
- Rate limit auth endpoints

---

## When Stuck

1. **Build errors**: Check `docker-compose logs` for service issues
2. **Type errors**: Run `mypy src` and fix one file at a time
3. **Test failures**: Run single test with `-v` flag for details
4. **Database issues**: Check migrations with `alembic current`
5. **Import errors**: Verify virtual environment is activated

### Common Issues

```bash
# ModuleNotFoundError
source venv/bin/activate  # Forgot to activate venv

# Database connection refused
docker-compose up -d      # Start containers first

# Alembic "Target database is not up to date"
alembic upgrade head      # Apply pending migrations

# Port already in use
lsof -i :8000            # Find process using port
kill -9 <PID>            # Kill it
```

---

## File References

For detailed documentation, see:
- `@docs/architecture.md` - System architecture and design decisions
- `@docs/api.md` - API endpoint documentation
- `@docs/cpm-algorithm.md` - CPM implementation details
- `@docs/evms-formulas.md` - EVMS calculation specifications
- `@README.md` - Project overview and setup instructions

---

*Last updated: January 2026*
*Maintained by: Defense PM Tool Development Team*
