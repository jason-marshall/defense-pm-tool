# Defense PM Tool - v1.1.0 Roadmap

> **Target Release**: February 2026
> **Focus**: Resource Management & Infrastructure Hardening
> **Duration**: 4 Weeks (Weeks 13-16)

---

## Release Goals

1. **Resource Management**: Full resource tracking, assignment, and basic leveling
2. **Infrastructure Maturity**: CI/CD, monitoring, caching operational
3. **Performance Validation**: Load tested to 50+ concurrent users
4. **Code Quality**: 2600+ tests, 80%+ coverage maintained

---

## Week 13: Stabilization (Complete)

| Deliverable | Status | Notes |
|-------------|--------|-------|
| CI/CD Pipeline | ✅ | GitHub Actions |
| Production Monitoring | ✅ | Prometheus metrics |
| Redis Caching | ✅ | CPM + dashboard caching |
| Load Testing | ✅ | Locust, 50 users |
| Frontend Polish | ✅ | Error handling, toasts |

---

## Week 14: Resource Foundation

### Goals
- Resource model and database schema
- Resource CRUD endpoints
- Activity-resource assignment
- Capacity calendar support

### Deliverables

| Task | Priority | Estimate |
|------|----------|----------|
| Resource model (api/src/models/resource.py) | 🔴 Critical | 2h |
| Migration 010_resources | 🔴 Critical | 1h |
| Resource repository | 🔴 Critical | 2h |
| Resource CRUD endpoints | 🔴 Critical | 3h |
| Assignment model | 🟡 High | 2h |
| Calendar model | 🟡 High | 2h |
| Unit tests | 🟡 High | 2h |
| Integration tests | 🟡 High | 2h |

### Data Model
```sql
-- Resources table
CREATE TABLE resources (
    id UUID PRIMARY KEY,
    program_id UUID REFERENCES programs(id),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) NOT NULL,
    resource_type VARCHAR(20) NOT NULL, -- LABOR, EQUIPMENT, MATERIAL
    capacity_per_day DECIMAL(10,2) DEFAULT 8.0,
    cost_rate DECIMAL(12,2),
    effective_date DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- Resource assignments
CREATE TABLE resource_assignments (
    id UUID PRIMARY KEY,
    activity_id UUID REFERENCES activities(id),
    resource_id UUID REFERENCES resources(id),
    units DECIMAL(5,2) DEFAULT 1.0, -- % allocation
    start_date DATE,
    finish_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- Resource calendars
CREATE TABLE resource_calendars (
    id UUID PRIMARY KEY,
    resource_id UUID REFERENCES resources(id),
    date DATE NOT NULL,
    available_hours DECIMAL(4,2) DEFAULT 8.0,
    is_working_day BOOLEAN DEFAULT true,
    UNIQUE(resource_id, date)
);
```

---

## Week 15: Resource Leveling (Complete)

### Goals
- Resource loading calculation ✅
- Over-allocation detection ✅
- Basic leveling algorithm (serial method) ✅
- Resource histogram visualization ✅

### Deliverables

| Task | Status | Notes |
|------|--------|-------|
| Resource loading service | ✅ | ResourceLoadingService with activity dates |
| Over-allocation detection | ✅ | OverallocationService with period detection |
| Serial leveling algorithm | ✅ | ResourceLevelingService with priority-based leveling |
| Resource histogram endpoint | ✅ | Daily/weekly granularity support |
| Leveling API endpoint | ✅ | POST /level, GET /level/preview, POST /level/apply |
| Week 15 E2E tests | ✅ | Full workflow tests |

### Algorithm: Serial Resource Leveling (Implemented)
```python
# ResourceLevelingService implements:
# 1. Sort activities by (early_start, total_float, id)
# 2. For each activity, check resource availability
# 3. If overallocated, find next available slot
# 4. Delay activity if allowed (respects critical path, float)
# 5. Propagate changes to successors
# 6. Repeat until no changes or max iterations
```

---

## Week 16: Polish & Release (Complete)

### Goals
- Resource management UI ✅
- Documentation update ✅
- Performance verification ✅
- v1.1.0 release ✅

### Deliverables

| Task | Status | Notes |
|------|--------|-------|
| ResourceList component | ✅ | PR #103 |
| ResourceForm component | ✅ | PR #103 |
| AssignmentModal component | ✅ | PR #104 |
| ResourceHistogram component | ✅ | PR #105, Recharts |
| LevelingPanel component | ✅ | PR #106 |
| Update USER_GUIDE.md | ✅ | Resource Management section |
| Update API_GUIDE.md | ✅ | v1.1.0 updates |
| RELEASE_NOTES_v1.1.0.md | ✅ | Complete release notes |
| v1.1.0 tag and release | ✅ | February 2026 |

---

## Success Metrics

| Metric | v1.0.0 | v1.1.0 Target | v1.1.0 Achieved |
|--------|--------|---------------|-----------------|
| Test Count | 2,400+ | 2,600+ | 2,700+ ✅ |
| Coverage | 80%+ | 80%+ | 81%+ ✅ |
| API Endpoints | 45+ | 55+ | 57+ ✅ |
| Concurrent Users | Unknown | 50+ verified | 50+ ✅ |
| Resource Leveling | No | Yes | Yes ✅ |
| CI/CD | No | Yes | Yes ✅ |
| Monitoring | Partial | Full | Full ✅ |
| Frontend Components | 12 | 17 | 17 ✅ |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Leveling algorithm complexity | Medium | High | Start with serial method, defer parallel |
| Resource model scope creep | Medium | Medium | Define MVP feature set upfront |
| Performance regression | Low | High | Continuous benchmarking |
| Coverage drop | Low | Medium | Maintain test-first approach |

---

## Dependencies

- Week 13 stabilization complete ✅
- Redis operational for caching ✅
- CI/CD pipeline running ✅
- Load testing baseline established ✅

---

## API Endpoints (v1.1.0)

### New Resource Endpoints
```
POST   /api/v1/resources                   # Create resource
GET    /api/v1/resources                   # List resources
GET    /api/v1/resources/{id}              # Get resource
PUT    /api/v1/resources/{id}              # Update resource
DELETE /api/v1/resources/{id}              # Delete resource

POST   /api/v1/resources/{id}/assignments  # Assign to activity
GET    /api/v1/resources/{id}/assignments  # List assignments
DELETE /api/v1/assignments/{id}            # Remove assignment

GET    /api/v1/resources/{id}/loading      # Get resource loading
POST   /api/v1/programs/{id}/level         # Level resources
GET    /api/v1/programs/{id}/histogram     # Resource histogram
```

---

## Frontend Components (v1.1.0)

| Component | Description |
|-----------|-------------|
| ResourceList | List and manage resources |
| ResourceForm | Create/edit resource |
| AssignmentModal | Assign resources to activities |
| ResourceHistogram | Visualize resource loading |
| LevelingPanel | Run and preview leveling |

---

---

## v1.2.0 Preview

Planned features for the next release:

- Parallel resource leveling algorithm
- Cross-program resource sharing
- Resource calendar import from MS Project
- Material quantity tracking
- Resource cost integration with EVMS
- Gantt chart with resource view

---

*Document Version: 1.1*
*Created: January 2026*
*Released: February 2026*
