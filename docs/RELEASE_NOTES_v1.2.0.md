# Defense PM Tool v1.2.0 Release Notes

> **Release Date**: March 2026
> **Focus**: Advanced Resource Management & EVMS Integration

---

## Highlights

v1.2.0 brings significant enhancements to resource management capabilities:

- **Automatic ACWP Calculation**: Resource costs automatically sync to EVMS
- **Material Tracking**: Full quantity-based inventory management
- **MS Project Calendar Import**: Import resource calendars from MS Project XML
- **Parallel Leveling**: Faster, optimized multi-resource leveling algorithm
- **Cross-Program Resources**: Share resources across programs with conflict detection
- **Gantt Resource View**: Visual resource assignment management with drag-and-drop

---

## New Features

### Resource Cost Tracking
- Record actual hours and costs per assignment
- Automatic ACWP calculation from resource actuals
- Cost sync to EVMS periods
- Labor, equipment, and material cost tracking
- Activity, WBS, and program-level cost summaries

### Material Management
- Quantity-based resource tracking
- Consumption recording and validation
- Inventory level monitoring
- Program-wide material summaries
- Unit cost and value calculations

### MS Project Calendar Import
- Import resource calendars from MS Project XML
- Support for working days, hours, and holidays
- Calendar templates for reuse
- Preview before import
- Automatic resource matching

### Parallel Resource Leveling
- Multi-resource simultaneous optimization
- Algorithm comparison tool (serial vs parallel)
- Priority-based conflict resolution
- Configurable options (preserve critical path, level within float)
- Detailed shift reports with reasons

### Cross-Program Resource Pools
- Create shared resource pools
- Grant program access with permission levels (READ, ASSIGN, MANAGE)
- Detect cross-program conflicts
- Pool-wide availability view
- Conflict checking before assignment

### Gantt Resource View
- Resource-centric timeline visualization
- Drag-and-drop assignment editing (move, resize)
- Utilization overlay with color coding
- Resource filtering and search
- Day/Week/Month scale options

---

## API Changes

### New Endpoints (20+)

#### Resource Cost Tracking
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/cost/activities/{id}` | GET | Get activity cost breakdown |
| `/cost/wbs/{id}` | GET | Get WBS cost rollup |
| `/cost/programs/{id}` | GET | Get program cost summary |
| `/cost/programs/{id}/evms-sync` | POST | Sync costs to EVMS |
| `/cost/assignments/{id}/entries` | POST | Record cost entry |

#### Material Tracking
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/materials/resources/{id}` | GET | Get material status |
| `/materials/assignments/{id}/consume` | POST | Record consumption |
| `/materials/programs/{id}` | GET | Get program materials |

#### Calendar Import
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/calendars/import/preview` | POST | Preview calendar import |
| `/calendars/import` | POST | Import MS Project calendars |

#### Parallel Leveling
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/programs/{id}/level-parallel` | POST | Run parallel leveling |
| `/programs/{id}/level-parallel/preview` | GET | Preview parallel leveling |
| `/programs/{id}/level/compare` | GET | Compare algorithms |

#### Resource Pools
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/resource-pools` | POST | Create resource pool |
| `/resource-pools` | GET | List accessible pools |
| `/resource-pools/{id}` | GET | Get pool details |
| `/resource-pools/{id}` | PATCH | Update pool |
| `/resource-pools/{id}` | DELETE | Delete pool |
| `/resource-pools/{id}/members` | POST | Add resource to pool |
| `/resource-pools/{id}/members` | GET | List pool members |
| `/resource-pools/{id}/members/{mid}` | DELETE | Remove from pool |
| `/resource-pools/{id}/access` | POST | Grant program access |
| `/resource-pools/{id}/availability` | GET | Get pool availability |
| `/resource-pools/check-conflict` | POST | Check assignment conflict |

### Breaking Changes

**None** - v1.2.0 is fully backward compatible with v1.1.0.

---

## Database Changes

### New Tables
- `resource_actuals` - Resource actual hours/costs by date
- `material_inventory` - Material quantity tracking
- `calendar_templates` - Reusable calendar templates
- `calendar_template_holidays` - Template holiday entries
- `resource_pools` - Cross-program resource pools
- `resource_pool_members` - Pool membership records
- `resource_pool_access` - Program access grants

### Migrations
Run `alembic upgrade head` to apply migrations:
- 011_resource_costs
- 012_calendar_templates
- 013_resource_pools

---

## Performance

All benchmarks GREEN:

| Operation | Target | Achieved | Status |
|-----------|--------|----------|--------|
| CPM (1000 activities) | <500ms | 11.66ms | GREEN |
| EVMS Summary | <500ms | 19.5ms | GREEN |
| WBS Tree | <500ms | 13.0ms | GREEN |
| Activities List (50) | <1000ms | 92.9ms | GREEN |
| Schedule Calc (50) | <2000ms | 116.4ms | GREEN |
| Full Dashboard Load | <3000ms | 189.0ms | GREEN |
| S-curve Enhanced | <2000ms | 75.5ms | GREEN |
| Monte Carlo (1000 iter) | <5s | 0.035s | GREEN |

---

## Test Coverage

| Metric | v1.1.0 | v1.2.0 |
|--------|--------|--------|
| Total Tests | 2,700+ | 2,950+ |
| Coverage | 81%+ | 81%+ |
| API Endpoints | 57+ | 77+ |
| Frontend Components | 17 | 20 |

---

## Upgrade Notes

### From v1.1.0 to v1.2.0

1. **Database Migration**
   ```bash
   cd api
   alembic upgrade head
   ```

2. **No Breaking Changes**: All v1.1.0 APIs remain compatible

3. **Frontend Update**: Rebuild frontend for new components
   ```bash
   cd web
   npm install
   npm run build
   ```

4. **New Dependencies**: None required

---

## Known Limitations

1. Calendar import supports MS Project 2019+ XML format only
2. Parallel leveling limited to 1000 activities per run
3. Resource pools are organization-scoped (no cross-org sharing)
4. Gantt resource view optimized for up to 100 resources

---

## Frontend Components (New)

| Component | Description |
|-----------|-------------|
| `GanttResourceView` | Resource-centric Gantt visualization |
| `ResourceFilterPanel` | Filter/search for resources |
| `AssignmentBars` | Drag-drop assignment editing |

---

## Roadmap Preview: v1.3.0

Planned features for the next release:
- Resource skills and certification tracking
- Automated resource recommendations (ML-based)
- Resource request/approval workflow
- Mobile resource time entry
- Advanced resource analytics dashboard
- Integration with HR systems

---

## Contributors

- Development Team
- Claude Code (AI-assisted development)

---

*Defense PM Tool v1.2.0 - Advanced Resource Management Release*
*Released: March 2026*
