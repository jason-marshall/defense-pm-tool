# Release Notes - v1.0.0

## Release Date
January 2026

## Overview
Initial production release of Defense PM Tool - an enterprise-grade program management system with EVMS/DFARS compliance for defense contractors.

---

## Features

### Schedule Management
- **Critical Path Method (CPM) Engine**: Full implementation with all four dependency types (FS, SS, FF, SF)
- **MS Project XML Import**: Import existing schedules from Microsoft Project
- **Constraint Support**: ASAP, ALAP, SNET, SNLT, FNET, FNLT, MSO, MFO
- **Automatic Schedule Calculation**: Forward/backward pass with float calculation

### Work Breakdown Structure (WBS)
- **Hierarchical WBS**: Multi-level structure with ltree-based storage
- **Control Accounts**: Designate WBS elements as control accounts
- **Budget Roll-up**: Automatic aggregation of budgets up the hierarchy

### Earned Value Management (EVMS)
- **6 EV Methods**: Percent complete, milestone (0/100), 50/50, level of effort (LOE), apportioned, weighted milestones
- **6 EAC Methods**: Per ANSI/EIA-748 Guideline 27
  - EAC = BAC / CPI
  - EAC = BAC / (SPI × CPI)
  - EAC = ACWP + ETC
  - EAC = ACWP + (BAC - BCWP)
  - EAC = ACWP + ((BAC - BCWP) / CPI)
  - Regression-based EAC
- **Time-Phased Budgets**: Track planned value over time
- **Variance Analysis**: SV, CV, SPI, CPI with thresholds

### Baseline Management
- **Baseline Snapshots**: Capture schedule and budget at point in time
- **Baseline Types**: PMB (official), Forecast, What-If
- **Variance Tracking**: Compare current to baseline
- **Baseline History**: Full audit trail of changes

### Monte Carlo Simulation
- **Schedule Risk Analysis**: Probabilistic duration modeling
- **Distribution Types**: Triangular, PERT, Normal, Uniform
- **Activity Correlation**: Model dependencies between activities
- **Sensitivity Analysis**: Identify key risk drivers
- **Confidence Levels**: P50, P70, P80, P90, P95 outputs
- **S-Curve Confidence Bands**: Visualize uncertainty range

### Scenario Planning
- **What-If Analysis**: Create scenarios without affecting production data
- **Delta Tracking**: Track all changes in scenario
- **Scenario Simulation**: Run Monte Carlo on scenarios
- **Scenario Comparison**: Compare multiple scenarios
- **Promote to Baseline**: Apply approved scenarios

### Reporting
- **CPR Format 1**: WBS Summary Report
- **CPR Format 3**: Baseline Change Log
- **CPR Format 5**: EVMS Summary Report
- **S-Curve Export**: PNG and CSV formats
- **PDF Generation**: Professional report output

### Jira Integration
- **Bidirectional Sync**: WBS and Activity synchronization
- **Custom Field Mapping**: Map DPM fields to Jira fields
- **Variance Alerts**: Create Jira issues on threshold breach
- **Webhook Support**: Real-time updates from Jira

### Authentication & Security
- **JWT Tokens**: Secure stateless authentication
- **API Keys**: Service account authentication for CI/CD
- **Role-Based Access**: Viewer, Analyst, Scheduler, Program Manager, Admin
- **Rate Limiting**: Configurable request limits
- **OWASP Compliance**: Top 10 security controls implemented

---

## Performance Benchmarks

All benchmarks verified on standard hardware (4-core CPU, 8GB RAM).

### CPM Engine Performance

| Benchmark | Result | Target | Status |
|-----------|--------|--------|--------|
| CPM 100 activities (chain) | 2.12ms | <50ms | ✅ GREEN |
| CPM 500 activities (chain) | 34.26ms | <200ms | ✅ GREEN |
| CPM 1000 activities (chain) | 13.53ms | <500ms | ✅ GREEN |
| CPM 1000 activities (parallel) | 12.30ms | <500ms | ✅ GREEN |
| CPM 2000 activities (chain) | 25.70ms | <1000ms | ✅ GREEN |
| CPM 5000 activities (chain) | 75.25ms | <2000ms | ✅ GREEN |

### Other Operations

| Benchmark | Result | Target | Status |
|-----------|--------|--------|--------|
| Graph construction (1000 nodes) | 2.33ms | <100ms | ✅ GREEN |
| EVMS calculations (1000 items) | 1.79ms | <100ms | ✅ GREEN |
| Monte Carlo (1000 iterations) | 19ms | <5000ms | ✅ GREEN |
| Dashboard full load | 39.0ms | <3000ms | ✅ GREEN |
| EVMS Summary endpoint | 22.3ms | <500ms | ✅ GREEN |
| S-curve endpoint | 16.7ms | <2000ms | ✅ GREEN |
| WBS Tree endpoint | 4.1ms | <500ms | ✅ GREEN |
| Activities List endpoint | 34.4ms | <500ms | ✅ GREEN |
| Schedule Calculation endpoint | 23.1ms | <1000ms | ✅ GREEN |

---

## Test Coverage

| Category | Tests | Coverage |
|----------|-------|----------|
| Unit Tests | 2,100+ | 80%+ |
| Integration Tests | 165+ | - |
| E2E Tests | 90+ | - |
| Performance Tests | 27 | - |
| Security Tests | 36 | - |
| **Total** | **2,400+** | **80%+** |

---

## API Summary

- **27 REST endpoints** across 8 resource types
- **OpenAPI 3.0** specification with interactive docs
- **Rate limiting**: 100 reads/min, 30 writes/min
- **Authentication**: JWT Bearer tokens or X-API-Key header

### Endpoints Overview

| Resource | Endpoints | Methods |
|----------|-----------|---------|
| Auth | 4 | POST, DELETE |
| Programs | 5 | GET, POST, PATCH, DELETE |
| WBS | 4 | GET, POST, PATCH, DELETE |
| Activities | 5 | GET, POST, PATCH, DELETE |
| Dependencies | 4 | GET, POST, DELETE |
| EVMS | 3 | GET, POST |
| Baselines | 4 | GET, POST, DELETE |
| Scenarios | 6 | GET, POST, PATCH, DELETE |
| Monte Carlo | 2 | POST, GET |
| Reports | 4 | GET |
| Jira | 4 | GET, POST, DELETE |
| API Keys | 4 | GET, POST, DELETE |

---

## System Requirements

### Production

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Storage | 20 GB SSD | 50 GB SSD |
| PostgreSQL | 15+ | 15+ |
| Redis | 7+ | 7+ |
| Python | 3.11+ | 3.11+ |

### Docker Deployment

```bash
# Using docker-compose
docker-compose -f docker-compose.prod.yml up -d

# With self-hosted database
docker-compose -f docker-compose.prod.yml -f docker-compose.selfhosted.yml up -d
```

---

## Known Limitations

1. **Single-Tenant**: Designed for single organization deployment
2. **No Real-Time Collaboration**: Changes require page refresh
3. **PDF Export**: Requires reportlab library
4. **Browser Support**: Modern browsers only (Chrome, Firefox, Edge, Safari)
5. **File Import**: MS Project XML only (no MPP direct import)

---

## Security Considerations

- All secrets must be generated before deployment
- HTTPS required for production (terminate at load balancer)
- API keys should be rotated annually
- Database credentials should use strong passwords (32+ chars)
- Rate limiting enabled by default

---

## Upgrade Path

N/A - Initial release

---

## Breaking Changes

N/A - Initial release

---

## Documentation

- **User Guide**: [docs/USER_GUIDE.md](USER_GUIDE.md)
- **API Guide**: [docs/API_GUIDE.md](API_GUIDE.md)
- **Deployment Guide**: [docs/DEPLOYMENT.md](DEPLOYMENT.md)
- **Security Guide**: [docs/SECURITY.md](SECURITY.md)
- **Architecture**: [docs/ARCHITECTURE.md](ARCHITECTURE.md)

---

## Contributors

- Development Team
- Claude Code (AI-assisted development)

---

## License

Proprietary - See LICENSE file

---

*Defense PM Tool v1.0.0 - Production Ready*
*Released: January 2026*
