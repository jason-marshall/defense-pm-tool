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

## Week 15: Resource Leveling

### Goals
- Resource loading calculation
- Over-allocation detection
- Basic leveling algorithm (serial method)
- Resource histogram visualization

### Deliverables

| Task | Priority | Estimate |
|------|----------|----------|
| Resource loading service | 🔴 Critical | 4h |
| Over-allocation detection | 🔴 Critical | 2h |
| Serial leveling algorithm | 🔴 Critical | 6h |
| Resource histogram endpoint | 🟡 High | 3h |
| Leveling API endpoint | 🟡 High | 2h |
| Frontend histogram | 🟡 High | 4h |
| Performance optimization | 🟡 High | 2h |
| Tests (unit + integration) | 🟡 High | 4h |

### Algorithm: Serial Resource Leveling
```python
def level_resources_serial(activities, resources, assignments):
    """
    Serial resource leveling algorithm.

    1. Sort activities by early start, then by float (ascending)
    2. For each activity:
       a. Check resource availability
       b. If overallocated, delay activity
       c. Recalculate CPM dates
    3. Repeat until no overallocations
    """
    pass
```

---

## Week 16: Polish & Release

### Goals
- Resource management UI
- Documentation update
- Performance verification
- v1.1.0 release

### Deliverables

| Task | Priority | Estimate |
|------|----------|----------|
| Resource management pages | 🟡 High | 4h |
| Resource assignment UI | 🟡 High | 3h |
| Update USER_GUIDE.md | 🟡 High | 2h |
| Update API_GUIDE.md | 🟡 High | 2h |
| Final performance tests | 🟡 High | 2h |
| RELEASE_NOTES_v1.1.0.md | 🟡 High | 1h |
| v1.1.0 tag and release | 🔴 Critical | 1h |

---

## Success Metrics

| Metric | v1.0.0 | v1.1.0 Target |
|--------|--------|---------------|
| Test Count | 2,400+ | 2,600+ |
| Coverage | 80%+ | 80%+ |
| API Endpoints | 45+ | 55+ |
| Concurrent Users | Unknown | 50+ verified |
| Resource Leveling | No | Yes |
| CI/CD | No | Yes |
| Monitoring | Partial | Full |

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

*Document Version: 1.0*
*Created: January 2026*
*Target: February 2026*
