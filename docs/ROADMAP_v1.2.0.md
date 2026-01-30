# Defense PM Tool - v1.2.0 Roadmap

> **Target Release**: March 2026
> **Focus**: Advanced Resource Management & EVMS Integration
> **Duration**: 6 Weeks (Weeks 17-22)

---

## Release Goals

1. **Resource Cost Integration**: Automatic ACWP calculation from resource actuals
2. **Material Tracking**: Quantity-based resource management
3. **Calendar Import**: MS Project resource calendar support
4. **Parallel Leveling**: Optimized resource leveling algorithm
5. **Cross-Program Resources**: Shared resource pools
6. **Gantt Resource View**: Visual resource assignment management

---

## Week 17: Foundation (Days 113-119)

### Goals
- v1.2.0 roadmap and planning
- Resource cost model enhancement
- Material quantity tracking
- EVMS cost integration foundation

### Deliverables

| Task | Priority | Estimate |
|------|----------|----------|
| v1.2.0 Roadmap document | 🔴 Critical | 2h |
| Resource cost tracking fields | 🔴 Critical | 2h |
| Migration 011_resource_costs | 🔴 Critical | 1h |
| ResourceCostService | 🔴 Critical | 4h |
| Material quantity fields | 🟡 High | 2h |
| Cost and quantity endpoints | 🟡 High | 3h |
| Week 17 E2E tests | 🟡 High | 2h |

### Data Model Changes

```sql
-- Resource cost tracking enhancements
ALTER TABLE resources ADD COLUMN overtime_rate DECIMAL(12,2);
ALTER TABLE resources ADD COLUMN unit_of_measure VARCHAR(20);

-- Resource actuals for ACWP calculation
CREATE TABLE resource_actuals (
    id UUID PRIMARY KEY,
    assignment_id UUID REFERENCES resource_assignments(id),
    date DATE NOT NULL,
    hours_worked DECIMAL(6,2),
    quantity_used DECIMAL(12,4),
    cost_override DECIMAL(12,2),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    UNIQUE(assignment_id, date)
);

-- Material inventory tracking
CREATE TABLE material_inventory (
    id UUID PRIMARY KEY,
    resource_id UUID REFERENCES resources(id),
    quantity_on_hand DECIMAL(12,4) DEFAULT 0,
    quantity_committed DECIMAL(12,4) DEFAULT 0,
    unit_cost DECIMAL(12,2),
    last_updated TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Week 18: Calendar Import (Days 120-126)

### Goals
- MS Project resource calendar parsing
- Calendar import workflow
- Calendar bulk operations

### Deliverables

| Task | Priority | Estimate |
|------|----------|----------|
| MS Project calendar XML parser | 🔴 Critical | 4h |
| CalendarImportService | 🔴 Critical | 3h |
| Calendar import endpoint | 🟡 High | 2h |
| Calendar bulk operations | 🟡 High | 2h |
| Import preview UI | 🟡 High | 3h |
| Week 18 E2E tests | 🟡 High | 2h |

### MS Project Calendar Format

```xml
<!-- Expected MS Project XML structure -->
<Resource>
    <UID>1</UID>
    <Name>Engineer A</Name>
    <CalendarUID>2</CalendarUID>
</Resource>
<Calendar>
    <UID>2</UID>
    <Name>Engineer A Calendar</Name>
    <WeekDays>
        <WeekDay>
            <DayType>1</DayType> <!-- Sunday -->
            <DayWorking>0</DayWorking>
        </WeekDay>
        <!-- ... -->
    </WeekDays>
    <Exceptions>
        <Exception>
            <Name>Holiday</Name>
            <FromDate>2026-02-15</FromDate>
            <ToDate>2026-02-15</ToDate>
            <DayWorking>0</DayWorking>
        </Exception>
    </Exceptions>
</Calendar>
```

---

## Week 19: Parallel Leveling (Days 127-133)

### Goals
- Parallel resource leveling algorithm
- Multi-resource optimization
- Performance benchmarking

### Deliverables

| Task | Priority | Estimate |
|------|----------|----------|
| ParallelLevelingService | 🔴 Critical | 6h |
| Multi-resource conflict resolution | 🔴 Critical | 4h |
| Leveling algorithm options | 🟡 High | 2h |
| Performance optimization | 🟡 High | 3h |
| Leveling comparison endpoint | 🟡 High | 2h |
| Week 19 E2E tests | 🟡 High | 2h |

### Algorithm: Parallel Resource Leveling

```python
# ParallelLevelingService implements:
# 1. Identify all overallocated periods across all resources
# 2. Build conflict graph (activities sharing overallocated resources)
# 3. For each time slice:
#    a. Calculate resource demand vs availability
#    b. Use priority queue (critical path, total float, dependencies)
#    c. Delay lowest-priority activities to resolve conflicts
# 4. Optimize for minimum project duration increase
# 5. Consider activity splitting option (configurable)

class ParallelLevelingService:
    def level(
        self,
        program_id: UUID,
        options: LevelingOptions,
    ) -> LevelingResult:
        # Build resource demand matrix
        # Identify conflicts using interval trees
        # Apply priority-based resolution
        # Return optimized schedule
```

### Performance Targets

| Scenario | Serial (v1.1.0) | Parallel Target |
|----------|-----------------|-----------------|
| 100 activities, 10 resources | 2s | <1s |
| 500 activities, 20 resources | 15s | <5s |
| 1000 activities, 50 resources | N/A | <15s |

---

## Week 20: Cross-Program Resources (Days 134-140)

### Goals
- Resource pool model
- Cross-program sharing workflow
- Conflict detection across programs

### Deliverables

| Task | Priority | Estimate |
|------|----------|----------|
| ResourcePool model | 🔴 Critical | 3h |
| Pool membership endpoints | 🔴 Critical | 2h |
| Cross-program availability | 🔴 Critical | 4h |
| Sharing workflow UI | 🟡 High | 3h |
| Conflict detection service | 🟡 High | 3h |
| Week 20 E2E tests | 🟡 High | 2h |

### Data Model

```sql
-- Resource pools for cross-program sharing
CREATE TABLE resource_pools (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    owner_id UUID REFERENCES users(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- Pool membership (resources belong to pools)
CREATE TABLE resource_pool_members (
    id UUID PRIMARY KEY,
    pool_id UUID REFERENCES resource_pools(id),
    resource_id UUID REFERENCES resources(id),
    priority INTEGER DEFAULT 0, -- Higher = preferred for this pool
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pool_id, resource_id)
);

-- Pool access (programs can access pools)
CREATE TABLE resource_pool_access (
    id UUID PRIMARY KEY,
    pool_id UUID REFERENCES resource_pools(id),
    program_id UUID REFERENCES programs(id),
    access_level VARCHAR(20) DEFAULT 'READ', -- READ, ASSIGN, MANAGE
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pool_id, program_id)
);
```

---

## Week 21: Gantt Resource View (Days 141-147)

### Goals
- Resource lane visualization
- Assignment editing from Gantt
- Resource filter/search

### Deliverables

| Task | Priority | Estimate |
|------|----------|----------|
| GanttResourceView component | 🔴 Critical | 4h |
| Resource lane rendering | 🔴 Critical | 3h |
| Assignment drag-drop | 🟡 High | 3h |
| Resource filter panel | 🟡 High | 2h |
| Gantt-Histogram sync | 🟡 High | 2h |
| Week 21 E2E tests | 🟡 High | 2h |

### Component Architecture

```typescript
// GanttResourceView component structure
interface GanttResourceViewProps {
  programId: string;
  startDate: Date;
  endDate: Date;
  resources?: string[]; // Filter to specific resources
  onAssignmentChange?: (change: AssignmentChange) => void;
}

// Resource lane configuration
interface ResourceLane {
  resourceId: string;
  resourceName: string;
  resourceType: ResourceType;
  assignments: AssignmentBar[];
  utilization: number; // 0-100%
}

// Assignment bar for rendering
interface AssignmentBar {
  assignmentId: string;
  activityId: string;
  activityName: string;
  startDate: Date;
  endDate: Date;
  units: number;
  isCritical: boolean;
  isOverallocated: boolean;
}
```

---

## Week 22: Polish & Release (Days 148-154)

### Goals
- Documentation updates
- Final performance verification
- v1.2.0 release

### Deliverables

| Task | Priority | Estimate |
|------|----------|----------|
| Update USER_GUIDE.md | 🟡 High | 2h |
| Update API_GUIDE.md | 🟡 High | 2h |
| RELEASE_NOTES_v1.2.0.md | 🔴 Critical | 2h |
| Final performance verification | 🔴 Critical | 2h |
| v1.2.0 tag and release | 🔴 Critical | 1h |

---

## Success Metrics

| Metric | v1.1.0 | v1.2.0 Target |
|--------|--------|---------------|
| Test Count | 2,700+ | 2,900+ |
| Coverage | 81%+ | 81%+ |
| API Endpoints | 57+ | 65+ |
| Frontend Components | 17 | 20 |
| Parallel Leveling | No | Yes |
| Cross-Program Resources | No | Yes |
| Automatic ACWP | No | Yes |
| Material Quantity | No | Yes |
| Calendar Import | No | Yes |

---

## API Endpoints (v1.2.0 New)

### Resource Cost Endpoints

```
POST   /api/v1/resources/{id}/actuals         # Record resource actual
GET    /api/v1/resources/{id}/actuals         # Get resource actuals
PUT    /api/v1/actuals/{id}                   # Update actual record
DELETE /api/v1/actuals/{id}                   # Delete actual record
GET    /api/v1/assignments/{id}/cost          # Get assignment cost summary
GET    /api/v1/programs/{id}/resource-costs   # Get program resource costs
```

### Material Tracking Endpoints

```
GET    /api/v1/resources/{id}/inventory       # Get material inventory
PUT    /api/v1/resources/{id}/inventory       # Update inventory levels
POST   /api/v1/resources/{id}/consume         # Record material consumption
GET    /api/v1/programs/{id}/material-status  # Get program material status
```

### Calendar Import Endpoints

```
POST   /api/v1/programs/{id}/import/calendar  # Import MS Project calendars
GET    /api/v1/programs/{id}/import/calendar/preview  # Preview import
```

### Parallel Leveling Endpoints

```
POST   /api/v1/programs/{id}/level/parallel   # Run parallel leveling
GET    /api/v1/programs/{id}/level/compare    # Compare serial vs parallel
```

### Resource Pool Endpoints

```
POST   /api/v1/pools                          # Create resource pool
GET    /api/v1/pools                          # List resource pools
GET    /api/v1/pools/{id}                     # Get pool details
PUT    /api/v1/pools/{id}                     # Update pool
DELETE /api/v1/pools/{id}                     # Delete pool
POST   /api/v1/pools/{id}/members             # Add resource to pool
DELETE /api/v1/pools/{id}/members/{rid}       # Remove resource from pool
POST   /api/v1/pools/{id}/access              # Grant program access
DELETE /api/v1/pools/{id}/access/{pid}        # Revoke program access
GET    /api/v1/pools/{id}/availability        # Get pool availability
```

---

## Frontend Components (v1.2.0 New)

| Component | Description |
|-----------|-------------|
| ResourceActualsForm | Record actual hours/quantities |
| MaterialInventory | View and manage material stock |
| CalendarImportModal | Import MS Project calendars |
| GanttResourceView | Resource-centric Gantt visualization |
| ResourcePoolManager | Create and manage resource pools |
| PoolAccessControl | Configure program access to pools |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Parallel leveling complexity | Medium | High | Start with simpler heuristic, optimize later |
| Cross-program data isolation | Medium | High | Strict authorization checks, audit logging |
| Calendar import edge cases | Low | Medium | Comprehensive test suite with real MS Project files |
| Gantt performance with many resources | Medium | Medium | Virtual scrolling, lazy loading |
| EVMS integration complexity | Low | Medium | Incremental approach, validate against v1.1.0 calculations |

---

## Dependencies

- v1.1.0 release complete ✅
- Resource management stable ✅
- Redis caching operational ✅
- CI/CD pipeline running ✅

---

## Performance Targets

| Operation | v1.1.0 | v1.2.0 Target |
|-----------|--------|---------------|
| Serial Leveling (500 activities) | <5s | <5s (maintained) |
| Parallel Leveling (500 activities) | N/A | <5s |
| Parallel Leveling (1000 activities) | N/A | <15s |
| Resource Cost Calculation | N/A | <200ms |
| Calendar Import (100 resources) | N/A | <5s |
| Gantt Resource View (50 resources) | N/A | <2s initial load |
| Cross-Program Availability | N/A | <500ms |

---

## Migration Notes

### From v1.1.0 to v1.2.0

1. **Database Migration**: Run `alembic upgrade head` to create new tables
2. **Resource Pools**: Existing program resources remain program-scoped by default
3. **Cost Tracking**: Historical ACWP data unchanged; new actuals table optional
4. **No Breaking Changes**: All v1.1.0 APIs remain compatible

---

## v1.3.0 Preview

Planned features for the next release:

- Resource skills and certification tracking
- Automated resource recommendations (ML-based)
- Resource request/approval workflow
- Mobile resource time entry
- Advanced resource analytics dashboard
- Integration with HR systems

---

*Document Version: 1.0*
*Created: February 2026*
*Target Release: March 2026*
