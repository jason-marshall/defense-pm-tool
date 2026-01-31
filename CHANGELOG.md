# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - March 2026

### Added
- Resource cost tracking with automatic ACWP calculation
- Material quantity tracking and consumption recording
- MS Project calendar import (XML format)
- Parallel resource leveling algorithm with comparison tool
- Cross-program resource pools with conflict detection
- Gantt resource view component with drag-and-drop editing
- Resource filter panel with search and quick filters
- Pool availability endpoint for cross-program coordination
- 20+ new API endpoints for v1.2.0 features

### Changed
- Improved leveling performance with parallel algorithm option
- Enhanced resource loading calculations
- Updated API_GUIDE.md with all new endpoints (77+ total)
- Updated USER_GUIDE.md with new feature documentation

### Fixed
- Various minor bug fixes and performance improvements

## [1.1.0] - February 2026

### Added
- Resource model (LABOR, EQUIPMENT, MATERIAL types)
- Resource CRUD endpoints (13 endpoints)
- Resource assignment system
- Resource calendar support with bulk operations
- Overallocation detection service
- Serial resource leveling algorithm
- Resource histogram visualization
- ResourceList, ResourceForm, AssignmentModal components
- ResourceHistogram, LevelingPanel components
- CI/CD pipeline (GitHub Actions)
- Production monitoring (Prometheus)
- Redis caching implementation
- Load testing with Locust

### Changed
- Enhanced dashboard performance
- Improved error handling

## [1.0.0] - January 2026

### Added
- Program management with contract details
- Work Breakdown Structure (WBS) with ltree hierarchy
- Activity & dependency management (FS, SS, FF, SF)
- Critical Path Method (CPM) engine
- EVMS dashboard with CPI, SPI, EAC metrics
- Multiple EV methods (0/100, 50/50, LOE, milestone, %)
- Baseline management with JSONB snapshots
- Monte Carlo simulation for schedule risk
- Scenario planning with what-if analysis
- CPR Format 1, 3, 5 reports with PDF export
- MS Project XML import
- Jira Cloud integration
- JWT and API Key authentication
- Rate limiting for API endpoints
- OWASP Top 10 security compliance

### Performance
- CPM: <500ms for 1000 activities
- Monte Carlo: <5s for 10000 iterations
- Dashboard: <3s full load
- All benchmarks GREEN

### Test Coverage
- 2400+ tests
- 80%+ coverage
