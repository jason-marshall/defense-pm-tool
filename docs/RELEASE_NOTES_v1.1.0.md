# Release Notes - v1.1.0

**Release Date:** February 2026

## Overview

Version 1.1.0 adds comprehensive resource management capabilities including resource tracking, assignment, capacity calendars, overallocation detection, resource leveling algorithm, and histogram visualization.

---

## New Features

### Resource Management

- **Resource Types**: Support for Labor, Equipment, and Material resources
- **Resource CRUD**: Create, read, update, delete resources with program scoping
- **Capacity Configuration**: Define daily availability for each resource
- **Cost Tracking**: Optional hourly cost rates for budgeting integration

### Resource Assignment

- **Activity-Resource Links**: Assign resources to activities with allocation percentage
- **Flexible Allocation**: Support for part-time (0.5), full-time (1.0), and overtime (2.0)
- **Date Overrides**: Override activity dates for specific resource assignments
- **Multiple Assignments**: Assign multiple resources to the same activity

### Overallocation Detection

- **Automatic Detection**: Identifies periods where assigned hours exceed available capacity
- **Period Grouping**: Combines consecutive overallocated days into manageable periods
- **Critical Path Impact**: Flags when overallocation affects critical path activities
- **Program-wide Analysis**: View overallocations across all program resources

### Resource Leveling

- **Serial Algorithm**: Priority-based leveling (early start, then total float)
- **Preserve Critical Path**: Option to protect critical activities from delays
- **Float Constraints**: Level only within available total float
- **Preview Mode**: Review proposed schedule changes before applying
- **Selective Apply**: Choose which activity shifts to accept
- **Iteration Control**: Configurable maximum iterations for complex schedules

### Resource Histogram

- **Visual Loading Chart**: Bar chart showing available vs. assigned hours
- **Granularity Options**: Daily or weekly aggregation views
- **Summary Statistics**: Peak utilization, average utilization, overallocated days
- **Program View**: Aggregate histogram across all resources in a program
- **Overallocation Highlighting**: Red bars indicate periods exceeding capacity

### Frontend Components

- **ResourceList**: Manage resources with type filtering and CRUD actions
- **ResourceForm**: Create and edit resource modal with validation
- **AssignmentModal**: Assign resources to activities with allocation input
- **ResourceHistogram**: Interactive utilization chart built with Recharts
- **LevelingPanel**: Configure, run, and apply resource leveling

---

## API Changes

### New Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/resources` | POST | Create resource |
| `/resources` | GET | List resources (with filters) |
| `/resources/{id}` | GET | Get resource details |
| `/resources/{id}` | PUT | Update resource |
| `/resources/{id}` | DELETE | Delete resource |
| `/resources/{id}/assignments` | POST | Create assignment |
| `/resources/{id}/assignments` | GET | List resource assignments |
| `/resources/{id}/calendar` | GET | Get calendar entries |
| `/resources/{id}/calendar` | POST | Create calendar entries |
| `/resources/{id}/calendar` | DELETE | Delete calendar range |
| `/resources/{id}/histogram` | GET | Get resource histogram |
| `/activities/{id}/assignments` | GET | List activity assignments |
| `/assignments/{id}` | GET | Get assignment details |
| `/assignments/{id}` | PUT | Update assignment |
| `/assignments/{id}` | DELETE | Delete assignment |
| `/programs/{id}/overallocations` | GET | Get program overallocations |
| `/programs/{id}/level` | POST | Run resource leveling |
| `/programs/{id}/level/preview` | GET | Preview leveling results |
| `/programs/{id}/level/apply` | POST | Apply leveling shifts |
| `/programs/{id}/histogram` | GET | Get program histogram |

### Query Parameters

**Resource List:**
- `program_id` (required): Filter by program
- `resource_type`: Filter by LABOR, EQUIPMENT, or MATERIAL
- `is_active`: Filter by active status

**Histogram:**
- `start_date` (required): Period start
- `end_date` (required): Period end
- `granularity`: "daily" or "weekly" (default: daily)

**Leveling:**
- `preserve_critical_path`: Boolean (default: true)
- `max_iterations`: Integer (default: 100)
- `level_within_float`: Boolean (default: true)

---

## Performance

| Operation | v1.0.0 | v1.1.0 | Target |
|-----------|--------|--------|--------|
| CPM Calculation (1000 activities) | <500ms | <500ms | Maintained |
| Resource Loading | N/A | <100ms | <200ms |
| Overallocation Detection | N/A | <500ms | <1s |
| Serial Leveling (500 activities) | N/A | <5s | <10s |
| Histogram (single resource, 90 days) | N/A | <200ms | <500ms |
| Histogram (program, 20 resources) | N/A | <1s | <2s |

---

## Test Coverage

| Metric | v1.0.0 | v1.1.0 |
|--------|--------|--------|
| Total Tests | 2,400+ | 2,700+ |
| Coverage | 80%+ | 80%+ |
| API Endpoints | 45+ | 57+ |
| Frontend Components | 12 | 17 |

---

## Database Changes

### New Tables

```sql
-- Resources table
CREATE TABLE resources (
    id UUID PRIMARY KEY,
    program_id UUID REFERENCES programs(id),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) NOT NULL,
    resource_type VARCHAR(20) NOT NULL,
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
    units DECIMAL(5,2) DEFAULT 1.0,
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

### Migration

Run migration to create new tables:

```bash
cd api
alembic upgrade head
```

---

## Upgrade Notes

### From v1.0.0 to v1.1.0

1. **Database Migration**: Run `alembic upgrade head` to create new tables
2. **No Breaking Changes**: All v1.0.0 APIs remain compatible
3. **Frontend Update**: Update frontend build to include new components
4. **Dependencies**: New dependency added: `recharts` for histogram visualization

### Breaking Changes

**None** - v1.1.0 is fully backward compatible with v1.0.0.

---

## Known Limitations

1. **Leveling Algorithm**: Serial method only (parallel leveling planned for v1.2.0)
2. **Calendar Import**: No MS Project resource calendar import yet
3. **Histogram Range**: Limited to 366 days per query for performance
4. **Material Resources**: Quantity tracking not yet implemented
5. **Multi-Project Resources**: Resources are program-scoped (cross-program sharing in v1.2.0)

---

## Roadmap Preview: v1.2.0

Planned features for the next release:

- Parallel resource leveling algorithm
- Cross-program resource sharing
- Resource calendar import from MS Project
- Material quantity tracking
- Resource cost integration with EVMS
- Gantt chart with resource view

---

## Contributors

- Development Team
- Claude Code (AI-assisted development)

---

## Documentation

- [API Guide](API_GUIDE.md) - Updated with Resource Management section
- [User Guide](USER_GUIDE.md) - Updated with Resource Management section
- [Roadmap](ROADMAP_v1.1.0.md) - Week-by-week development plan

---

*Defense PM Tool v1.1.0 - Resource Management Release*
*Released: February 2026*
