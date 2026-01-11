# Defense PM Tool - TDD Development Plan v2.0

> **Updated**: January 2026 (Post Week 1 Implementation)
> **Status**: Week 1 Complete, Week 2 Starting

---

## Development Methodology

### Test-Driven Development Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    TDD Cycle (Red-Green-Refactor)               │
│                                                                  │
│   ┌─────────┐      ┌─────────┐      ┌─────────┐                │
│   │  RED    │─────▶│  GREEN  │─────▶│REFACTOR │────┐           │
│   │  Write  │      │  Write  │      │ Improve │    │           │
│   │ Failing │      │ Minimal │      │  Code   │    │           │
│   │  Test   │      │  Code   │      │ Quality │    │           │
│   └─────────┘      └─────────┘      └─────────┘    │           │
│        ▲                                            │           │
│        └────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Verification Ladder (Required for ALL prompts)

```bash
# Level 1: Static Analysis
ruff check src tests --fix
ruff format src tests

# Level 2: Type Checking
mypy src --ignore-missing-imports

# Level 3: Unit Tests
pytest tests/unit -v

# Level 4: Integration Tests
pytest tests/integration -v

# Level 5: Full Suite with Coverage
pytest --cov=src --cov-report=term-missing --cov-fail-under=60

# Level 6: Manual Verification
# - API responds correctly
# - Edge cases handled
# - Error messages helpful
```

---

## Progress Summary

### Week 1: Foundation ✅ COMPLETE

| Prompt | Description | Status | Notes |
|--------|-------------|--------|-------|
| 1.1 | Project scaffold | ✅ | Full structure created |
| 1.2 | FastAPI + Pydantic setup | ✅ | Config, settings, schemas |
| 2.1 | SQLAlchemy models | ✅ | All 5 models with relationships |
| 2.2 | Alembic migration | ✅ | Comprehensive initial migration |
| 2.3 | Repository pattern | ✅ | Generic base + specialized |
| 3.1 | CPM engine | ✅ | All dependency types |
| 3.2 | EVMS calculator | ✅ | All metrics implemented |
| 4.1 | JWT auth utilities | ✅ | Token creation/validation |
| 4.2 | Auth endpoints | 🔶 | Needs verification |
| 5.1-5.3 | Integration | 🔶 | Basic integration done |

### Known Issues to Address

| Issue | Priority | Resolution |
|-------|----------|------------|
| Model field mismatches | 🔴 High | Hotfix prompt at Week 2 start |
| Low test coverage | 🟡 Medium | Add tests in Week 2 |
| Auth flow incomplete | 🟡 Medium | Complete in Week 2 |
| Redis not implemented | 🟢 Low | Defer to Week 3 |

---

## Week 2: Activity Management & Gantt (Days 8-14)

### Goals
- Complete activity CRUD with full authentication
- Implement dependency management with cycle detection
- Create basic Gantt chart visualization
- Achieve 60%+ test coverage

### Day 8-9: Model Alignment & Activity CRUD

#### Prompt 2.1.0 (Hotfix): Model-Schema Alignment

**Purpose**: Fix field mismatches between models, schemas, and repositories before proceeding.

```
Fix model-schema-repository alignment issues identified in code review.

## Required Changes

### 1. Update Activity Model
File: api/src/models/activity.py

Add these fields:
- program_id: UUID FK to programs.id (required for direct program queries)
- code: str, max 50 chars (unique within program for identification)

Update __table_args__ to add:
- Composite unique constraint on (program_id, code) where deleted_at IS NULL
- Index on program_id

### 2. Update Dependency Model  
File: api/src/models/dependency.py

Rename field:
- lag_days -> lag (to match CPM engine and schemas)

### 3. Update Program Model (if code field missing)
File: api/src/models/program.py

Verify or add:
- code: str, max 50 chars, unique, not null

### 4. Create New Migration
File: api/alembic/versions/002_model_alignment.py

Migration should:
- Add programs.code if missing (with unique index)
- Add activities.program_id FK
- Add activities.code with composite unique constraint
- Rename dependencies.lag_days to lag

### 5. Update Repositories
Files: api/src/repositories/activity.py, dependency.py, program.py

Ensure all queries reference correct field names.

### 6. Update conftest.py Fixtures
File: api/tests/conftest.py

Update sample_activities and sample_dependencies fixtures to use correct field names.

## Verification Ladder
```bash
cd api
ruff check src tests --fix
ruff format src tests
mypy src --ignore-missing-imports
alembic upgrade head
pytest tests/unit -v
pytest tests/integration -v
```

## Git Workflow
```bash
git checkout -b hotfix/model-alignment
# Make changes
git add .
git commit -m "fix(models): align model fields with schemas and repositories"
git push -u origin hotfix/model-alignment
# Create PR: "Hotfix: Model-Schema Alignment"
```
```

#### Prompt 2.1.1: Activity CRUD with Authentication

```
Implement complete Activity CRUD operations with authentication and authorization.

## Prerequisites
- Model alignment hotfix (2.1.0) is merged
- Database migrations are current

## Implementation

### 1. Create Activity Tests First (TDD)
File: api/tests/unit/test_activity_crud.py

```python
"""Unit tests for Activity CRUD operations."""

import pytest
from decimal import Decimal
from uuid import uuid4

from src.models.activity import Activity
from src.models.enums import ConstraintType
from src.schemas.activity import ActivityCreate, ActivityUpdate


class TestActivityCreate:
    """Tests for activity creation."""

    def test_create_activity_valid(self):
        """Should create activity with valid data."""
        data = ActivityCreate(
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Design Review",
            code="DR-001",
            duration=5,
            budgeted_cost=Decimal("10000.00"),
        )
        assert data.name == "Design Review"
        assert data.duration == 5

    def test_create_milestone_forces_zero_duration(self):
        """Milestone should have duration forced to 0."""
        data = ActivityCreate(
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Phase 1 Complete",
            code="M-001",
            duration=5,  # Will be forced to 0
            is_milestone=True,
        )
        assert data.duration == 0
        assert data.is_milestone is True

    def test_constraint_date_required_for_snet(self):
        """SNET constraint requires constraint_date."""
        with pytest.raises(ValueError, match="constraint_date is required"):
            ActivityCreate(
                program_id=uuid4(),
                wbs_id=uuid4(),
                name="Test",
                code="T-001",
                constraint_type=ConstraintType.SNET,
                constraint_date=None,
            )


class TestActivityUpdate:
    """Tests for activity updates."""

    def test_update_partial(self):
        """Should allow partial updates."""
        data = ActivityUpdate(name="Updated Name")
        assert data.name == "Updated Name"
        assert data.duration is None  # Not provided

    def test_update_percent_complete_range(self):
        """Percent complete must be 0-100."""
        with pytest.raises(ValueError):
            ActivityUpdate(percent_complete=Decimal("150.00"))
```

### 2. Create Integration Tests
File: api/tests/integration/test_activities_api.py

```python
"""Integration tests for Activities API."""

import pytest
from httpx import AsyncClient
from uuid import uuid4

pytestmark = pytest.mark.asyncio


class TestActivitiesAPI:
    """Integration tests for /api/v1/activities endpoints."""

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict:
        """Get authentication headers."""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "activitytest@example.com",
                "password": "TestPass123",
                "full_name": "Activity Tester",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "activitytest@example.com", "password": "TestPass123"},
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def program_id(self, client: AsyncClient, auth_headers: dict) -> str:
        """Create a program and return its ID."""
        response = await client.post(
            "/api/v1/programs",
            headers=auth_headers,
            json={
                "name": "Test Program",
                "code": "TP-001",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        return response.json()["id"]

    async def test_create_activity_requires_auth(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.post(
            "/api/v1/activities",
            json={"name": "Test", "program_id": str(uuid4())},
        )
        assert response.status_code == 401

    async def test_create_activity_success(
        self, client: AsyncClient, auth_headers: dict, program_id: str
    ):
        """Should create activity with valid data."""
        response = await client.post(
            "/api/v1/activities",
            headers=auth_headers,
            json={
                "program_id": program_id,
                "name": "Design Review",
                "code": "DR-001",
                "duration": 5,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Design Review"
        assert data["duration"] == 5

    async def test_list_activities_by_program(
        self, client: AsyncClient, auth_headers: dict, program_id: str
    ):
        """Should list activities filtered by program."""
        # Create activities
        for i in range(3):
            await client.post(
                "/api/v1/activities",
                headers=auth_headers,
                json={
                    "program_id": program_id,
                    "name": f"Activity {i}",
                    "code": f"A-{i:03d}",
                    "duration": i + 1,
                },
            )

        response = await client.get(
            f"/api/v1/activities?program_id={program_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
```

### 3. Update Activity Endpoint
File: api/src/api/v1/endpoints/activities.py

Add authentication to all endpoints:
- Inject current_user via Depends(get_current_user)
- Verify user owns program or is admin for modifications
- Filter list by user's accessible programs

### 4. Update Activity Schema
File: api/src/schemas/activity.py

Add to ActivityCreate:
- program_id: UUID (required)
- code: str (optional, auto-generated if not provided)

Add to ActivityListResponse:
- items: list[ActivityResponse]
- total: int
- page: int
- page_size: int

## Verification Ladder
```bash
cd api
ruff check src tests --fix
mypy src --ignore-missing-imports
pytest tests/unit/test_activity_crud.py -v
pytest tests/integration/test_activities_api.py -v
pytest --cov=src --cov-report=term-missing
```

## Git Workflow
```bash
git checkout -b feature/activity-crud-auth
git add .
git commit -m "feat(activities): implement activity CRUD with authentication"
git push -u origin feature/activity-crud-auth
# Create PR
```
```

### Day 10-11: Dependency Management

#### Prompt 2.2.1: Dependency CRUD with Cycle Detection

```
Implement dependency management with cycle detection and validation.

## Implementation

### 1. Create Dependency Tests First
File: api/tests/unit/test_dependency_validation.py

```python
"""Unit tests for dependency validation."""

import pytest
from uuid import uuid4

from src.schemas.dependency import DependencyCreate
from src.models.enums import DependencyType


class TestDependencyCreate:
    """Tests for dependency creation validation."""

    def test_create_valid_dependency(self):
        """Should create dependency with valid data."""
        pred_id = uuid4()
        succ_id = uuid4()
        data = DependencyCreate(
            predecessor_id=pred_id,
            successor_id=succ_id,
            dependency_type=DependencyType.FS,
            lag=0,
        )
        assert data.predecessor_id == pred_id
        assert data.successor_id == succ_id

    def test_self_dependency_rejected(self):
        """Should reject self-referencing dependency."""
        activity_id = uuid4()
        with pytest.raises(ValueError, match="cannot depend on itself"):
            DependencyCreate(
                predecessor_id=activity_id,
                successor_id=activity_id,
                dependency_type=DependencyType.FS,
            )

    def test_default_lag_is_zero(self):
        """Default lag should be 0."""
        data = DependencyCreate(
            predecessor_id=uuid4(),
            successor_id=uuid4(),
        )
        assert data.lag == 0

    def test_negative_lag_allowed(self):
        """Negative lag (lead time) should be allowed."""
        data = DependencyCreate(
            predecessor_id=uuid4(),
            successor_id=uuid4(),
            lag=-2,  # 2 day lead
        )
        assert data.lag == -2
```

### 2. Create Cycle Detection Tests
File: api/tests/unit/test_cycle_detection.py

```python
"""Unit tests for circular dependency detection."""

import pytest
from uuid import uuid4

from src.services.cpm import CPMEngine
from src.core.exceptions import CircularDependencyError
from src.models.activity import Activity
from src.models.dependency import Dependency


class TestCycleDetection:
    """Tests for cycle detection in dependency graph."""

    def test_simple_cycle_detected(self):
        """Should detect A -> B -> C -> A cycle."""
        program_id = uuid4()
        a = Activity(id=uuid4(), program_id=program_id, name="A", code="A", duration=5)
        b = Activity(id=uuid4(), program_id=program_id, name="B", code="B", duration=3)
        c = Activity(id=uuid4(), program_id=program_id, name="C", code="C", duration=2)

        deps = [
            Dependency(predecessor_id=a.id, successor_id=b.id, dependency_type="FS", lag=0),
            Dependency(predecessor_id=b.id, successor_id=c.id, dependency_type="FS", lag=0),
            Dependency(predecessor_id=c.id, successor_id=a.id, dependency_type="FS", lag=0),
        ]

        engine = CPMEngine([a, b, c], deps)
        
        with pytest.raises(CircularDependencyError) as exc_info:
            engine.calculate()
        
        # Verify cycle path is returned
        assert len(exc_info.value.cycle_path) >= 3

    def test_no_cycle_valid(self):
        """Should not raise for valid acyclic graph."""
        program_id = uuid4()
        a = Activity(id=uuid4(), program_id=program_id, name="A", code="A", duration=5)
        b = Activity(id=uuid4(), program_id=program_id, name="B", code="B", duration=3)

        deps = [
            Dependency(predecessor_id=a.id, successor_id=b.id, dependency_type="FS", lag=0),
        ]

        engine = CPMEngine([a, b], deps)
        result = engine.calculate()  # Should not raise
        
        assert a.id in result
        assert b.id in result
```

### 3. Create Integration Tests
File: api/tests/integration/test_dependencies_api.py

```python
"""Integration tests for Dependencies API."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestDependenciesAPI:
    """Integration tests for /api/v1/dependencies endpoints."""

    async def test_create_dependency_success(
        self, client: AsyncClient, auth_headers: dict, two_activities: tuple
    ):
        """Should create dependency between activities."""
        pred_id, succ_id = two_activities
        
        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_headers,
            json={
                "predecessor_id": pred_id,
                "successor_id": succ_id,
                "dependency_type": "FS",
                "lag": 0,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["predecessor_id"] == pred_id
        assert data["successor_id"] == succ_id

    async def test_create_duplicate_dependency_fails(
        self, client: AsyncClient, auth_headers: dict, two_activities: tuple
    ):
        """Should reject duplicate dependency."""
        pred_id, succ_id = two_activities
        
        # Create first
        await client.post(
            "/api/v1/dependencies",
            headers=auth_headers,
            json={"predecessor_id": pred_id, "successor_id": succ_id},
        )
        
        # Try duplicate
        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_headers,
            json={"predecessor_id": pred_id, "successor_id": succ_id},
        )
        assert response.status_code == 409

    async def test_create_circular_dependency_fails(
        self, client: AsyncClient, auth_headers: dict, three_activities: tuple
    ):
        """Should reject dependency that creates cycle."""
        a_id, b_id, c_id = three_activities
        
        # Create A -> B -> C
        await client.post(
            "/api/v1/dependencies",
            headers=auth_headers,
            json={"predecessor_id": a_id, "successor_id": b_id},
        )
        await client.post(
            "/api/v1/dependencies",
            headers=auth_headers,
            json={"predecessor_id": b_id, "successor_id": c_id},
        )
        
        # Try C -> A (would create cycle)
        response = await client.post(
            "/api/v1/dependencies",
            headers=auth_headers,
            json={"predecessor_id": c_id, "successor_id": a_id},
        )
        assert response.status_code == 400
        assert "CIRCULAR_DEPENDENCY" in response.json()["code"]
```

### 4. Implement Pre-Creation Cycle Check
File: api/src/api/v1/endpoints/dependencies.py

Before creating a dependency, check if it would create a cycle:

```python
async def would_create_cycle(
    db: AsyncSession,
    program_id: UUID,
    predecessor_id: UUID,
    successor_id: UUID,
) -> bool:
    """Check if adding this dependency would create a cycle."""
    # Get all activities and existing dependencies
    activity_repo = ActivityRepository(db)
    dep_repo = DependencyRepository(db)
    
    activities = await activity_repo.get_by_program(program_id)
    dependencies = await dep_repo.get_by_program(program_id)
    
    # Add proposed dependency temporarily
    temp_dep = Dependency(
        predecessor_id=predecessor_id,
        successor_id=successor_id,
        dependency_type=DependencyType.FS,
        lag=0,
    )
    
    engine = CPMEngine(activities, dependencies + [temp_dep])
    
    try:
        engine._detect_cycles()
        return False  # No cycle
    except CircularDependencyError:
        return True  # Would create cycle
```

## Verification Ladder
```bash
cd api
ruff check src tests --fix
mypy src --ignore-missing-imports
pytest tests/unit/test_dependency_validation.py -v
pytest tests/unit/test_cycle_detection.py -v
pytest tests/integration/test_dependencies_api.py -v
pytest --cov=src --cov-report=term-missing
```

## Git Workflow
```bash
git checkout -b feature/dependency-management
git add .
git commit -m "feat(dependencies): implement dependency CRUD with cycle detection"
git push -u origin feature/dependency-management
```
```

### Day 12-14: Basic Gantt Visualization

#### Prompt 2.3.1: Gantt Chart Component

```
Create a basic Gantt chart visualization component for the frontend.

## Prerequisites
- Backend activity and dependency endpoints working
- Frontend scaffold in place

## Implementation

### 1. Install Dependencies
```bash
cd web
npm install d3 @types/d3 date-fns
```

### 2. Create Gantt Types
File: web/src/types/gantt.ts

```typescript
export interface GanttActivity {
  id: string;
  name: string;
  code: string;
  startDate: Date;
  endDate: Date;
  duration: number;
  percentComplete: number;
  isCritical: boolean;
  isMilestone: boolean;
  wbsLevel: number;
}

export interface GanttDependency {
  id: string;
  predecessorId: string;
  successorId: string;
  type: 'FS' | 'SS' | 'FF' | 'SF';
  lag: number;
}

export interface GanttViewConfig {
  startDate: Date;
  endDate: Date;
  scale: 'day' | 'week' | 'month';
  rowHeight: number;
  headerHeight: number;
  sidebarWidth: number;
}
```

### 3. Create Gantt Hook
File: web/src/hooks/useGanttData.ts

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { GanttActivity, GanttDependency } from '@/types/gantt';

export function useGanttData(programId: string) {
  const activitiesQuery = useQuery({
    queryKey: ['gantt-activities', programId],
    queryFn: async () => {
      const response = await apiClient.get(`/activities?program_id=${programId}&page_size=1000`);
      return response.data.items.map(transformToGanttActivity);
    },
    enabled: !!programId,
  });

  const dependenciesQuery = useQuery({
    queryKey: ['gantt-dependencies', programId],
    queryFn: async () => {
      const response = await apiClient.get(`/dependencies/program/${programId}`);
      return response.data.items;
    },
    enabled: !!programId,
  });

  return {
    activities: activitiesQuery.data ?? [],
    dependencies: dependenciesQuery.data ?? [],
    isLoading: activitiesQuery.isLoading || dependenciesQuery.isLoading,
    error: activitiesQuery.error || dependenciesQuery.error,
  };
}

function transformToGanttActivity(activity: any): GanttActivity {
  return {
    id: activity.id,
    name: activity.name,
    code: activity.code,
    startDate: new Date(activity.earlyStart || activity.plannedStart),
    endDate: new Date(activity.earlyFinish || activity.plannedFinish),
    duration: activity.duration,
    percentComplete: parseFloat(activity.percentComplete),
    isCritical: activity.isCritical,
    isMilestone: activity.isMilestone,
    wbsLevel: activity.wbsElement?.level ?? 1,
  };
}
```

### 4. Create Gantt Chart Component
File: web/src/components/GanttChart/GanttChart.tsx

```typescript
import React, { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import { GanttActivity, GanttDependency, GanttViewConfig } from '@/types/gantt';
import { GanttSidebar } from './GanttSidebar';
import { GanttTimeline } from './GanttTimeline';
import { GanttBars } from './GanttBars';
import './GanttChart.css';

interface GanttChartProps {
  activities: GanttActivity[];
  dependencies: GanttDependency[];
  onActivityClick?: (activity: GanttActivity) => void;
  onActivityDoubleClick?: (activity: GanttActivity) => void;
}

export function GanttChart({
  activities,
  dependencies,
  onActivityClick,
  onActivityDoubleClick,
}: GanttChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [config, setConfig] = useState<GanttViewConfig>({
    startDate: new Date(),
    endDate: new Date(),
    scale: 'week',
    rowHeight: 32,
    headerHeight: 50,
    sidebarWidth: 300,
  });

  // Calculate date range from activities
  useEffect(() => {
    if (activities.length === 0) return;

    const dates = activities.flatMap(a => [a.startDate, a.endDate]);
    const minDate = d3.min(dates) ?? new Date();
    const maxDate = d3.max(dates) ?? new Date();

    // Add padding
    const paddedStart = d3.timeDay.offset(minDate, -7);
    const paddedEnd = d3.timeDay.offset(maxDate, 14);

    setConfig(prev => ({
      ...prev,
      startDate: paddedStart,
      endDate: paddedEnd,
    }));
  }, [activities]);

  const timeScale = d3.scaleTime()
    .domain([config.startDate, config.endDate])
    .range([0, containerRef.current?.clientWidth ?? 800 - config.sidebarWidth]);

  return (
    <div className="gantt-container" ref={containerRef}>
      <div className="gantt-sidebar" style={{ width: config.sidebarWidth }}>
        <GanttSidebar 
          activities={activities} 
          rowHeight={config.rowHeight}
          headerHeight={config.headerHeight}
        />
      </div>
      <div className="gantt-main">
        <GanttTimeline
          config={config}
          timeScale={timeScale}
        />
        <GanttBars
          activities={activities}
          dependencies={dependencies}
          config={config}
          timeScale={timeScale}
          onActivityClick={onActivityClick}
          onActivityDoubleClick={onActivityDoubleClick}
        />
      </div>
    </div>
  );
}
```

### 5. Create Supporting Components
Files to create:
- web/src/components/GanttChart/GanttSidebar.tsx
- web/src/components/GanttChart/GanttTimeline.tsx
- web/src/components/GanttChart/GanttBars.tsx
- web/src/components/GanttChart/GanttChart.css
- web/src/components/GanttChart/index.ts

### 6. Create Gantt Page
File: web/src/pages/ProgramGantt.tsx

```typescript
import React from 'react';
import { useParams } from 'react-router-dom';
import { GanttChart } from '@/components/GanttChart';
import { useGanttData } from '@/hooks/useGanttData';

export function ProgramGantt() {
  const { programId } = useParams<{ programId: string }>();
  const { activities, dependencies, isLoading, error } = useGanttData(programId!);

  if (isLoading) {
    return <div className="loading">Loading schedule...</div>;
  }

  if (error) {
    return <div className="error">Error loading schedule: {error.message}</div>;
  }

  return (
    <div className="program-gantt-page">
      <h1>Program Schedule</h1>
      <GanttChart
        activities={activities}
        dependencies={dependencies}
        onActivityClick={(activity) => console.log('Clicked:', activity)}
      />
    </div>
  );
}
```

### 7. Add Tests
File: web/src/components/GanttChart/__tests__/GanttChart.test.tsx

```typescript
import { render, screen } from '@testing-library/react';
import { GanttChart } from '../GanttChart';

describe('GanttChart', () => {
  const mockActivities = [
    {
      id: '1',
      name: 'Activity A',
      code: 'A',
      startDate: new Date('2026-01-01'),
      endDate: new Date('2026-01-05'),
      duration: 5,
      percentComplete: 50,
      isCritical: true,
      isMilestone: false,
      wbsLevel: 1,
    },
  ];

  it('renders without crashing', () => {
    render(<GanttChart activities={mockActivities} dependencies={[]} />);
    expect(screen.getByText('Activity A')).toBeInTheDocument();
  });

  it('shows empty state when no activities', () => {
    render(<GanttChart activities={[]} dependencies={[]} />);
    // Should show empty state or nothing
  });
});
```

## Verification
```bash
cd web
npm run lint
npm run test
npm run build
```

## Git Workflow
```bash
git checkout -b feature/gantt-chart
git add .
git commit -m "feat(frontend): implement basic Gantt chart visualization"
git push -u origin feature/gantt-chart
```
```

---

## Week 3: WBS & EVMS Integration (Days 15-21)

### Goals
- Complete WBS hierarchy management
- Implement EVMS period tracking
- Create dashboard components
- Add report generation

### Prompts Overview

| Prompt | Day | Description |
|--------|-----|-------------|
| 3.1.1 | 15 | WBS CRUD with hierarchy |
| 3.1.2 | 16 | WBS tree visualization |
| 3.2.1 | 17-18 | EVMS period tracking |
| 3.2.2 | 19 | EVMS dashboard |
| 3.3.1 | 20-21 | Report generation |

---

## Week 4: Polish & MS Project (Days 22-28)

### Goals
- MS Project XML import
- Performance optimization
- End-to-end testing
- Documentation completion

### Prompts Overview

| Prompt | Day | Description |
|--------|-----|-------------|
| 4.1.1 | 22-23 | MS Project XML parser |
| 4.1.2 | 24 | Import workflow UI |
| 4.2.1 | 25 | Performance optimization |
| 4.2.2 | 26 | Caching implementation |
| 4.3.1 | 27 | E2E test suite |
| 4.3.2 | 28 | Documentation & deploy |

---

## Coverage Targets by Week

| Week | Target | Focus Areas |
|------|--------|-------------|
| 1 | 40% | Core models, CPM, EVMS |
| 2 | 60% | Activity CRUD, Dependencies, Gantt |
| 3 | 75% | WBS, EVMS tracking, Dashboard |
| 4 | 80% | Integration, E2E, Import |

---

## Risk Mitigation Checkpoints

### End of Week 2
- [ ] All model-schema alignments fixed
- [ ] Activity CRUD with auth complete
- [ ] Dependency cycle detection working
- [ ] Basic Gantt rendering
- [ ] 60%+ test coverage

### End of Week 3
- [ ] WBS hierarchy working
- [ ] EVMS tracking functional
- [ ] Dashboard shows metrics
- [ ] Reports generate correctly
- [ ] 75%+ test coverage

### End of Week 4
- [ ] MS Project import works
- [ ] Performance targets met
- [ ] E2E tests passing
- [ ] Documentation complete
- [ ] 80%+ test coverage

---

*Document Version: 2.0*
*Last Updated: January 2026*
