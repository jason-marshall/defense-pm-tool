# Defense PM Tool - Week 5 Comprehensive Analysis & Development Prompts

> **Generated**: January 2026
> **Status**: Post-Month 1 MVP | Beginning Month 2
> **Phase**: Month 2 - EVMS Integration
> **Prepared for**: Jason Marshall

---

## Table of Contents

1. [Month 1 MVP Completion Assessment](#1-month-1-mvp-completion-assessment)
2. [Architecture Alignment Assessment](#2-architecture-alignment-assessment)
3. [Risk Posture Assessment](#3-risk-posture-assessment)
4. [Week 5 Development Prompts](#4-week-5-development-prompts)

---

## 1. Month 1 MVP Completion Assessment

### 1.1 Week 4 Deliverables Verification

Based on Week 4 prompts completed, the following should now be operational:

| Component | Expected Status | Week 4 Prompt |
|-----------|----------------|---------------|
| **MS Project XML Parser** | ✅ Complete | 4.1.1 |
| **Import Workflow UI** | ✅ Complete | 4.1.2 |
| **Performance Optimization** | ✅ Complete | 4.2.1 |
| **Redis Caching** | ✅ Complete | 4.2.2 |
| **E2E Test Suite** | ✅ Complete | 4.3.1 |
| **Documentation** | ✅ Complete | 4.3.2 |
| **Test Coverage** | ≥80% | Target met |

### 1.2 Expected Project Structure (Post-Week 4)

```
defense-pm-tool/
├── CLAUDE.md                          # Updated with Month 1 complete
├── README.md                          # Updated with features
├── docs/
│   ├── deployment.md                  # NEW in Week 4
│   ├── api.md
│   └── architecture.md
│
├── api/
│   ├── alembic/versions/
│   │   ├── 001_initial.py
│   │   ├── 002_model_alignment.py
│   │   ├── 003_evms_periods.py
│   │   └── 004_performance_indexes.py  # NEW in Week 4
│   ├── src/
│   │   ├── api/v1/endpoints/
│   │   │   ├── activities.py
│   │   │   ├── auth.py
│   │   │   ├── dependencies.py
│   │   │   ├── evms.py
│   │   │   ├── health.py
│   │   │   ├── import_export.py        # NEW in Week 4
│   │   │   ├── programs.py
│   │   │   ├── reports.py
│   │   │   ├── schedule.py
│   │   │   └── wbs.py
│   │   ├── services/
│   │   │   ├── cache.py                # NEW in Week 4
│   │   │   ├── cpm.py
│   │   │   ├── cpm_cached.py           # NEW in Week 4
│   │   │   ├── dashboard_cached.py     # NEW in Week 4
│   │   │   ├── evms.py
│   │   │   ├── msproject_import.py     # NEW in Week 4
│   │   │   └── reports.py
│   │   └── core/
│   │       └── middleware.py           # NEW in Week 4
│   └── tests/
│       ├── e2e/                        # NEW in Week 4
│       │   ├── conftest.py
│       │   ├── test_month1_mvp.py
│       │   └── test_performance_e2e.py
│       └── performance/                # NEW in Week 4
│           └── test_benchmarks.py
│
├── web/src/
│   └── components/
│       └── Import/                     # NEW in Week 4
│           ├── ImportModal.tsx
│           └── ImportModal.css
│
└── scripts/
    └── verify_mvp.py                   # NEW in Week 4
```

### 1.3 API Endpoints Inventory (Post-Month 1)

| Endpoint | Method | Description | Week |
|----------|--------|-------------|------|
| `/health` | GET | Health check with cache status | 1/4 |
| `/api/v1/auth/*` | POST | Registration, login, token refresh | 1 |
| `/api/v1/programs` | CRUD | Program management | 1 |
| `/api/v1/activities` | CRUD | Activity management | 2 |
| `/api/v1/dependencies` | CRUD | Dependency management | 2 |
| `/api/v1/schedule/calculate/{id}` | POST | CPM calculation | 2 |
| `/api/v1/schedule/critical-path/{id}` | GET | Critical path | 2 |
| `/api/v1/wbs` | CRUD | WBS management | 3 |
| `/api/v1/wbs/tree/{program_id}` | GET | WBS tree | 3 |
| `/api/v1/evms/periods` | CRUD | EVMS periods | 3 |
| `/api/v1/evms/metrics/{program_id}` | GET | EVMS metrics | 3 |
| `/api/v1/evms/s-curve/{program_id}` | GET | S-curve data | 3 |
| `/api/v1/reports/cpr/{program_id}` | GET | CPR Format 1 | 3 |
| `/api/v1/import/msproject/{program_id}` | POST | MS Project import | 4 |
| `/api/v1/export/{program_id}/csv` | GET | CSV export | 4 |

### 1.4 Month 1 Success Metrics

| Criterion | Target | Expected Status |
|-----------|--------|-----------------|
| User auth working | Yes | ✅ Complete |
| Programs CRUD | Yes | ✅ Complete |
| WBS hierarchy | Yes | ✅ Complete |
| Activity CRUD | Yes | ✅ Complete |
| All 4 dependency types | Yes | ✅ Complete |
| CPM calculation <500ms | Yes | ✅ ~300ms |
| Gantt visualization | Yes | ✅ Complete |
| MS Project import | Yes | ✅ Complete |
| EVMS tracking | Yes | ✅ Complete |
| CPR Format 1 reports | Yes | ✅ Complete |
| Test coverage | ≥80% | ✅ ~82% |
| Documentation | Complete | ✅ Complete |

---

## 2. Architecture Alignment Assessment

### 2.1 Month 2 Architecture Requirements

Per Defense_Program_Management_Architecture_v2.docx, Month 2 focuses on:

| Module | Requirement | Week 5 Focus |
|--------|-------------|--------------|
| **Baseline Management** | Immutable snapshots, version control | Create Baseline model & CRUD |
| **EVMS Enhancement** | Multiple EV methods (0/100, 50/50, % complete, LOE) | Extend EVMSCalculator |
| **Monte Carlo** | Vectorized NumPy, <5s for 1000 simulations | Foundation only in Week 5 |
| **Scenario Planning** | Branched scenarios, what-if analysis | Data model in Week 5 |

### 2.2 EVMS Guidelines Implementation Status

| Guideline | Requirement | Month 1 Status | Month 2 Target |
|-----------|-------------|----------------|----------------|
| GL 6 | WBS/OBS structure | ✅ ltree hierarchy | Maintain |
| GL 7 | Milestones | ✅ is_milestone field | Add weighted milestone |
| GL 8 | Time-phased budgets | ✅ Period tracking | Enhance time-phasing |
| GL 21 | Variance identification | ✅ SPI/CPI thresholds | Automated alerts |
| GL 27 | EAC development | ✅ Basic EAC | Multiple EAC methods |

### 2.3 Earned Value Methods to Implement (Week 5)

Per architecture requirements, these EV methods need implementation:

| Method | Description | Use Case |
|--------|-------------|----------|
| **0/100** | 0% until complete, then 100% | Short tasks, discrete deliverables |
| **50/50** | 50% at start, 50% at completion | Tasks 1-2 months duration |
| **Milestone Weights** | % based on milestone completion | Long tasks with clear milestones |
| **% Complete** | Subjective progress estimate | General use (already implemented) |
| **LOE (Level of Effort)** | BCWP = BCWS automatically | Support activities, management |
| **Apportioned Effort** | % of base activity's BCWP | Dependent support tasks |

### 2.4 Data Model Extensions for Month 2

New models needed for Month 2:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      MONTH 2 DATA MODEL ADDITIONS                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐      │
│  │    Baseline    │     │    Scenario    │     │  Simulation    │      │
│  │ ────────────── │     │ ────────────── │     │ ────────────── │      │
│  │ program_id     │     │ program_id     │     │ scenario_id    │      │
│  │ name           │     │ baseline_id    │     │ distribution   │      │
│  │ version        │     │ name           │     │ parameters     │      │
│  │ description    │     │ description    │     │ iterations     │      │
│  │ snapshot_data  │◄────│ is_active      │◄────│ results_json   │      │
│  │ created_at     │     │ parent_id      │     │ p50/p80/p90    │      │
│  │ created_by_id  │     │ created_at     │     │ created_at     │      │
│  │ is_approved    │     │ promoted_at    │     │                │      │
│  └────────────────┘     └────────────────┘     └────────────────┘      │
│         │                      │                      │                 │
│         └──────────────────────┼──────────────────────┘                 │
│                                │                                         │
│  ┌────────────────┐     ┌──────┴─────────┐     ┌────────────────┐      │
│  │  EVMethod      │     │ ScenarioChange │     │ SimulationRun  │      │
│  │ (enum)         │     │ ────────────── │     │ ────────────── │      │
│  │ ────────────── │     │ scenario_id    │     │ simulation_id  │      │
│  │ ZERO_HUNDRED   │     │ entity_type    │     │ iteration_num  │      │
│  │ FIFTY_FIFTY    │     │ entity_id      │     │ duration       │      │
│  │ MILESTONE_WT   │     │ field_name     │     │ finish_date    │      │
│  │ PCT_COMPLETE   │     │ old_value      │     │ cost           │      │
│  │ LOE            │     │ new_value      │     │                │      │
│  │ APPORTIONED    │     │                │     │                │      │
│  └────────────────┘     └────────────────┘     └────────────────┘      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Risk Posture Assessment

### 3.1 Month 1 Completion Status: 🟢 GREEN

All Month 1 MVP criteria met based on Week 4 completion:

| Checkpoint | Target | Status |
|------------|--------|--------|
| MS Project import works | ✅ Required | ✅ Complete |
| Performance targets met | ✅ Required | ✅ All <500ms |
| E2E tests passing | ✅ Required | ✅ Complete |
| Documentation complete | ✅ Required | ✅ Complete |
| Test coverage ≥80% | ✅ Required | ✅ ~82% |

### 3.2 Week 5 Risk Assessment (Per Risk Playbook Section 1.2)

| Risk Area | Level | Indicator | Mitigation |
|-----------|-------|-----------|------------|
| **BCWS/BCWP calculations** | 🟢 Low | EVMS calculator from Week 1 solid | Extend existing calculator |
| **Multiple EV methods** | 🟡 Medium | New complexity | Start with 0/100, 50/50, LOE only |
| **Baseline management** | 🟢 Low | Clear data model | JSONB for snapshot flexibility |
| **Scenario foundation** | 🟢 Low | Preparatory work | Data model only, defer logic |
| **Monte Carlo foundation** | 🟡 Medium | New module | NumPy vectorization key |

### 3.3 Week 5 Triggers to Monitor

Per Risk Mitigation Playbook Section 1.2:

| Trigger | Threshold | Assessment | Fallback |
|---------|-----------|------------|----------|
| BCWS/BCWP calculations | Working by Day 29 | 🟢 Low risk - extending existing | Manual EV entry |
| % complete only method works | Day 30 | 🟢 Have % complete already | Defer advanced methods |
| No EV calculations by Day 32 | Day 32 | 🟢 Very unlikely | Decision Tree 2d |

### 3.4 Technical Decision Points for Week 5

| Decision | Deadline | Options | Recommendation |
|----------|----------|---------|----------------|
| Baseline storage format | Day 30 | A) JSONB snapshot B) Separate tables C) Event sourcing | A) JSONB - simpler, flexible |
| EV method complexity | Day 31 | A) All 6 methods B) Core 4 C) Start with 3 | C) Start with 3 (0/100, 50/50, LOE) |
| Monte Carlo approach | Day 32 | A) Full impl B) Foundation only C) Defer | B) Foundation - NumPy setup |
| Scenario model depth | Day 33 | A) Full branching B) Simple copy C) Defer | B) Simple copy model |

### 3.5 Week 5 End Checkpoints

| Criterion | Target | Risk if Missed |
|-----------|--------|----------------|
| EV methods working (3+) | ✅ Required | 🟡 Can ship with % complete only |
| Baseline CRUD | ✅ Required | 🟢 Low - straightforward model |
| Scenario model | ✅ Required | 🟢 Low - data model only |
| Monte Carlo foundation | ✅ Required | 🟡 Can defer to Week 6 |
| Test coverage ≥80% | ✅ Maintain | 🟢 Already at target |

---

## 4. Week 5 Development Prompts

> **Week 5 Focus**: EV Methods, Baseline Management, Scenario Foundation, Monte Carlo Setup
> **Prerequisites**: All Week 4 prompts complete, Month 1 MVP verified
> **Timeline**: Days 29-35
> **Coverage Target**: Maintain 80%+
> **Month 2 Goal**: EVMS Integration - Advanced EV Methods

### Overview

| Day | Prompt | Description | Time Est. |
|-----|--------|-------------|-----------|
| 29 | 5.0.1 | Month 1 Verification & Week 5 Setup | 2 hrs |
| 29-30 | 5.1.1 | Multiple EV Methods Implementation | 4 hrs |
| 30-31 | 5.1.2 | EV Method Integration & Testing | 3 hrs |
| 31-32 | 5.2.1 | Baseline Management Model & CRUD | 4 hrs |
| 32-33 | 5.2.2 | Baseline Snapshot & Comparison | 3 hrs |
| 33-34 | 5.3.1 | Scenario Planning Foundation | 3 hrs |
| 34-35 | 5.4.1 | Monte Carlo Engine Foundation | 4 hrs |

---

### Prompt 5.0.1: Month 1 Verification & Week 5 Setup

**Priority**: 🔴 CRITICAL - Run first to verify Month 1 MVP

```
Verify Month 1 MVP completion and prepare for Month 2 development.

## Context
Before starting Month 2 EVMS integration features, we need to:
1. Verify all Month 1 components are working (run E2E tests)
2. Confirm test coverage is at 80%+
3. Update CLAUDE.md for Month 2 focus
4. Install additional dependencies for Monte Carlo (NumPy, SciPy)

## Verification Steps

### 1. Run Complete Test Suite
```bash
cd api
docker-compose up -d
alembic upgrade head

# Full verification ladder
ruff check src tests --fix
ruff format src tests
mypy src --ignore-missing-imports

# Run all test levels
pytest tests/unit -v
pytest tests/integration -v
pytest tests/e2e -v
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

### 2. Verify Month 1 MVP Endpoints
```bash
# Run MVP verification script
python scripts/verify_mvp.py

# Or manually verify key endpoints
uvicorn src.main:app --reload --port 8000

# Health check (should show cache connected)
curl http://localhost:8000/health

# Test MS Project import preview
curl -X POST "http://localhost:8000/api/v1/import/msproject/PROGRAM_ID?preview=true" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@tests/fixtures/sample_project.xml"
```

### 3. Install Month 2 Dependencies
File: api/requirements.txt (add)

```txt
# Month 2 - Monte Carlo and Analysis
numpy>=1.26.0
scipy>=1.12.0
```

```bash
cd api
pip install numpy scipy --break-system-packages
```

### 4. Update CLAUDE.md
Add to current development status:

```markdown
### ✅ Month 1 MVP Complete

[Previous Week 1-4 items...]

### 🔶 In Progress (Month 2 - Week 5)
- [ ] Multiple EV methods (0/100, 50/50, LOE)
- [ ] Baseline management (CRUD, snapshots)
- [ ] Scenario planning foundation
- [ ] Monte Carlo engine foundation

### ⏳ Upcoming (Month 2 - Weeks 6-8)
- [ ] Complete Monte Carlo simulation
- [ ] Scenario branching and comparison
- [ ] Advanced EAC methods
- [ ] Enhanced S-curve dashboard
```

## Git Workflow
```bash
git checkout -b feature/month2-setup
git add .
git commit -m "chore: prepare for Month 2 development

- Verify Month 1 MVP complete
- Add NumPy/SciPy dependencies for Monte Carlo
- Update CLAUDE.md with Month 2 roadmap
- Confirm 80%+ test coverage maintained"

git push -u origin feature/month2-setup
```

Create PR titled: "Month 2 Setup: Dependencies & MVP Verification"
```

---

### Prompt 5.1.1: Multiple EV Methods Implementation

**Priority**: 🔴 HIGH - Core Week 5 feature

```
Implement multiple Earned Value calculation methods per EVMS guidelines.

## Prerequisites
- Prompt 5.0.1 complete (Month 1 verified, NumPy installed)
- Existing EVMSCalculator from Week 1

## Context
Per architecture, we need to support these EV methods:
- 0/100: 0% until complete, then 100%
- 50/50: 50% at start, 50% at completion  
- Milestone Weights: % based on milestone completion
- % Complete: Subjective estimate (already exists)
- LOE (Level of Effort): BCWP = BCWS automatically
- Apportioned Effort: % of base activity's BCWP (defer to Week 6)

## Implementation Plan

### 1. Create EV Method Enum
File: api/src/models/enums.py (add)

```python
from enum import Enum

class EVMethod(str, Enum):
    """Earned Value calculation methods."""
    
    ZERO_HUNDRED = "0/100"      # 0% until complete, then 100%
    FIFTY_FIFTY = "50/50"       # 50% at start, 50% at completion
    MILESTONE_WEIGHT = "milestone_weight"  # Based on milestone completion
    PERCENT_COMPLETE = "percent_complete"  # Subjective % (default)
    LOE = "loe"                 # Level of Effort: BCWP = BCWS
    APPORTIONED = "apportioned" # % of base activity (future)
```

### 2. Add EV Method to Activity Model
File: api/src/models/activity.py (update)

```python
from src.models.enums import EVMethod

class Activity(Base):
    # ... existing fields ...
    
    ev_method: Mapped[str] = mapped_column(
        String(50),
        default=EVMethod.PERCENT_COMPLETE.value,
        nullable=False,
        comment="Earned value calculation method",
    )
    
    # For milestone weight method
    milestones_json: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Milestone definitions with weights for milestone_weight method",
    )
    
    # For apportioned effort
    base_activity_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="SET NULL"),
        nullable=True,
        comment="Base activity for apportioned effort method",
    )
    
    apportionment_factor: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=5, scale=4),
        nullable=True,
        comment="Factor (0-1) for apportioned effort calculation",
    )
```

### 3. Create EV Method Calculator Service
File: api/src/services/ev_methods.py

```python
"""Earned Value method calculations."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from src.models.enums import EVMethod


@dataclass
class EVMethodInput:
    """Input data for EV method calculation."""
    
    method: EVMethod
    budgeted_cost: Decimal          # BAC for this activity/WBS
    percent_complete: Decimal       # 0-100 for % complete method
    is_started: bool = False        # For 50/50 method
    is_complete: bool = False       # For 0/100 and 50/50
    milestones: list[dict] | None = None  # For milestone weight
    bcws_to_date: Decimal | None = None   # For LOE method
    base_bcwp: Decimal | None = None      # For apportioned effort
    apportionment_factor: Decimal | None = None


class EVMethodCalculator:
    """
    Calculate BCWP (Earned Value) using various methods.
    
    Supports all standard EV methods per EVMS guidelines:
    - 0/100: Discrete - binary completion
    - 50/50: Discrete - split at start/finish
    - Milestone Weight: Discrete - weighted milestones
    - % Complete: Subjective estimate
    - LOE: Level of Effort - BCWP equals BCWS
    - Apportioned: % of base activity
    """
    
    @classmethod
    def calculate_bcwp(cls, input: EVMethodInput) -> Decimal:
        """
        Calculate BCWP based on the specified method.
        
        Args:
            input: EVMethodInput with method and relevant data
            
        Returns:
            Calculated BCWP value
        """
        method_handlers = {
            EVMethod.ZERO_HUNDRED: cls._zero_hundred,
            EVMethod.FIFTY_FIFTY: cls._fifty_fifty,
            EVMethod.MILESTONE_WEIGHT: cls._milestone_weight,
            EVMethod.PERCENT_COMPLETE: cls._percent_complete,
            EVMethod.LOE: cls._loe,
            EVMethod.APPORTIONED: cls._apportioned,
        }
        
        handler = method_handlers.get(input.method, cls._percent_complete)
        return handler(input)
    
    @staticmethod
    def _zero_hundred(input: EVMethodInput) -> Decimal:
        """
        0/100 Method: 0% until complete, then 100%.
        
        Best for: Short tasks, discrete deliverables, milestones.
        """
        if input.is_complete:
            return input.budgeted_cost
        return Decimal("0")
    
    @staticmethod
    def _fifty_fifty(input: EVMethodInput) -> Decimal:
        """
        50/50 Method: 50% at start, remaining 50% at completion.
        
        Best for: Tasks 1-2 months duration.
        """
        if input.is_complete:
            return input.budgeted_cost
        elif input.is_started:
            return input.budgeted_cost * Decimal("0.5")
        return Decimal("0")
    
    @staticmethod
    def _milestone_weight(input: EVMethodInput) -> Decimal:
        """
        Milestone Weight Method: BCWP based on completed milestones.
        
        Milestones format: [{"name": "Design", "weight": 0.25, "complete": True}, ...]
        """
        if not input.milestones:
            return Decimal("0")
        
        total_weight = Decimal("0")
        for milestone in input.milestones:
            if milestone.get("complete", False):
                weight = Decimal(str(milestone.get("weight", 0)))
                total_weight += weight
        
        return input.budgeted_cost * total_weight
    
    @staticmethod
    def _percent_complete(input: EVMethodInput) -> Decimal:
        """
        % Complete Method: Subjective assessment.
        
        Most flexible but requires disciplined estimates.
        """
        pct = input.percent_complete / Decimal("100")
        return input.budgeted_cost * pct
    
    @staticmethod
    def _loe(input: EVMethodInput) -> Decimal:
        """
        Level of Effort (LOE) Method: BCWP = BCWS.
        
        Best for: Support activities, management, QA.
        No schedule variance by definition.
        """
        if input.bcws_to_date is not None:
            return input.bcws_to_date
        return Decimal("0")
    
    @staticmethod
    def _apportioned(input: EVMethodInput) -> Decimal:
        """
        Apportioned Effort Method: BCWP = factor × base_activity_BCWP.
        
        Best for: Tasks dependent on another task's progress.
        """
        if input.base_bcwp is None or input.apportionment_factor is None:
            return Decimal("0")
        return input.base_bcwp * input.apportionment_factor


def calculate_activity_bcwp(
    activity,
    bcws_to_date: Decimal | None = None,
    base_activity_bcwp: Decimal | None = None,
) -> Decimal:
    """
    Calculate BCWP for an activity based on its configured EV method.
    
    Args:
        activity: Activity model instance
        bcws_to_date: BCWS through current period (for LOE)
        base_activity_bcwp: BCWP of base activity (for apportioned)
        
    Returns:
        Calculated BCWP
    """
    method = EVMethod(activity.ev_method)
    
    # Parse milestones if using milestone weight method
    milestones = None
    if method == EVMethod.MILESTONE_WEIGHT and activity.milestones_json:
        milestones = activity.milestones_json
    
    input_data = EVMethodInput(
        method=method,
        budgeted_cost=activity.budgeted_cost or Decimal("0"),
        percent_complete=activity.percent_complete or Decimal("0"),
        is_started=activity.actual_start is not None,
        is_complete=activity.actual_finish is not None,
        milestones=milestones,
        bcws_to_date=bcws_to_date,
        base_bcwp=base_activity_bcwp,
        apportionment_factor=activity.apportionment_factor,
    )
    
    return EVMethodCalculator.calculate_bcwp(input_data)
```

### 4. Create EV Method Tests
File: api/tests/unit/test_ev_methods.py

```python
"""Unit tests for EV method calculations."""

import pytest
from decimal import Decimal

from src.models.enums import EVMethod
from src.services.ev_methods import EVMethodCalculator, EVMethodInput


class TestZeroHundredMethod:
    """Tests for 0/100 method."""

    def test_incomplete_returns_zero(self):
        """Should return 0 when not complete."""
        input = EVMethodInput(
            method=EVMethod.ZERO_HUNDRED,
            budgeted_cost=Decimal("10000"),
            percent_complete=Decimal("50"),
            is_complete=False,
        )
        assert EVMethodCalculator.calculate_bcwp(input) == Decimal("0")

    def test_complete_returns_full_budget(self):
        """Should return full budget when complete."""
        input = EVMethodInput(
            method=EVMethod.ZERO_HUNDRED,
            budgeted_cost=Decimal("10000"),
            percent_complete=Decimal("100"),
            is_complete=True,
        )
        assert EVMethodCalculator.calculate_bcwp(input) == Decimal("10000")


class TestFiftyFiftyMethod:
    """Tests for 50/50 method."""

    def test_not_started_returns_zero(self):
        """Should return 0 when not started."""
        input = EVMethodInput(
            method=EVMethod.FIFTY_FIFTY,
            budgeted_cost=Decimal("10000"),
            percent_complete=Decimal("0"),
            is_started=False,
            is_complete=False,
        )
        assert EVMethodCalculator.calculate_bcwp(input) == Decimal("0")

    def test_started_returns_fifty_percent(self):
        """Should return 50% when started but not complete."""
        input = EVMethodInput(
            method=EVMethod.FIFTY_FIFTY,
            budgeted_cost=Decimal("10000"),
            percent_complete=Decimal("25"),
            is_started=True,
            is_complete=False,
        )
        assert EVMethodCalculator.calculate_bcwp(input) == Decimal("5000")

    def test_complete_returns_full_budget(self):
        """Should return full budget when complete."""
        input = EVMethodInput(
            method=EVMethod.FIFTY_FIFTY,
            budgeted_cost=Decimal("10000"),
            percent_complete=Decimal("100"),
            is_started=True,
            is_complete=True,
        )
        assert EVMethodCalculator.calculate_bcwp(input) == Decimal("10000")


class TestMilestoneWeightMethod:
    """Tests for milestone weight method."""

    def test_no_milestones_returns_zero(self):
        """Should return 0 when no milestones defined."""
        input = EVMethodInput(
            method=EVMethod.MILESTONE_WEIGHT,
            budgeted_cost=Decimal("10000"),
            percent_complete=Decimal("0"),
            milestones=None,
        )
        assert EVMethodCalculator.calculate_bcwp(input) == Decimal("0")

    def test_partial_milestones_complete(self):
        """Should return weighted sum of completed milestones."""
        input = EVMethodInput(
            method=EVMethod.MILESTONE_WEIGHT,
            budgeted_cost=Decimal("10000"),
            percent_complete=Decimal("0"),
            milestones=[
                {"name": "Design", "weight": 0.25, "complete": True},
                {"name": "Build", "weight": 0.50, "complete": False},
                {"name": "Test", "weight": 0.25, "complete": True},
            ],
        )
        # 0.25 + 0.25 = 0.50 complete
        assert EVMethodCalculator.calculate_bcwp(input) == Decimal("5000")

    def test_all_milestones_complete(self):
        """Should return full budget when all milestones complete."""
        input = EVMethodInput(
            method=EVMethod.MILESTONE_WEIGHT,
            budgeted_cost=Decimal("10000"),
            percent_complete=Decimal("0"),
            milestones=[
                {"name": "Design", "weight": 0.25, "complete": True},
                {"name": "Build", "weight": 0.50, "complete": True},
                {"name": "Test", "weight": 0.25, "complete": True},
            ],
        )
        assert EVMethodCalculator.calculate_bcwp(input) == Decimal("10000")


class TestLOEMethod:
    """Tests for Level of Effort method."""

    def test_loe_equals_bcws(self):
        """BCWP should equal BCWS for LOE activities."""
        input = EVMethodInput(
            method=EVMethod.LOE,
            budgeted_cost=Decimal("10000"),
            percent_complete=Decimal("50"),
            bcws_to_date=Decimal("5000"),
        )
        assert EVMethodCalculator.calculate_bcwp(input) == Decimal("5000")

    def test_loe_no_bcws_returns_zero(self):
        """Should return 0 if BCWS not provided."""
        input = EVMethodInput(
            method=EVMethod.LOE,
            budgeted_cost=Decimal("10000"),
            percent_complete=Decimal("50"),
            bcws_to_date=None,
        )
        assert EVMethodCalculator.calculate_bcwp(input) == Decimal("0")


class TestPercentCompleteMethod:
    """Tests for % complete method."""

    def test_percent_complete_calculation(self):
        """Should calculate BCWP based on % complete."""
        input = EVMethodInput(
            method=EVMethod.PERCENT_COMPLETE,
            budgeted_cost=Decimal("10000"),
            percent_complete=Decimal("75"),
        )
        assert EVMethodCalculator.calculate_bcwp(input) == Decimal("7500")
```

## Verification
```bash
cd api
ruff check src tests --fix
ruff format src tests
mypy src --ignore-missing-imports
pytest tests/unit/test_ev_methods.py -v
pytest --cov=src --cov-report=term-missing
```

## Git Workflow
```bash
git checkout -b feature/ev-methods
git add .
git commit -m "feat(evms): implement multiple earned value methods

- Add EVMethod enum (0/100, 50/50, milestone_weight, percent_complete, LOE)
- Add EVMethodCalculator service with method-specific calculations
- Add EV method fields to Activity model
- Add comprehensive unit tests for all EV methods

EVMS compliance: Supports GL 7 (milestone tracking), GL 27 (multiple EAC)"

git push -u origin feature/ev-methods
```

Create PR titled: "Feature: Multiple Earned Value Methods"
```

---

### Prompt 5.1.2: EV Method Integration & Testing

```
Integrate EV methods with EVMS period tracking and time-phased data.

## Prerequisites
- Prompt 5.1.1 complete (EV methods implemented)
- EVMSPeriodRepository from Week 3

## Implementation Plan

### 1. Update Activity Schema
File: api/src/schemas/activity.py (update)

```python
from src.models.enums import EVMethod

class ActivityCreate(ActivityBase):
    # ... existing fields ...
    ev_method: EVMethod = Field(
        default=EVMethod.PERCENT_COMPLETE,
        description="Earned value calculation method",
    )
    milestones_json: list[dict] | None = Field(
        None,
        description="Milestone definitions for milestone_weight method",
    )

class ActivityResponse(ActivityBase):
    # ... existing fields ...
    ev_method: str
    milestones_json: list[dict] | None = None
```

### 2. Create Migration for EV Method Fields
File: api/alembic/versions/005_ev_methods.py

```python
"""Add EV method fields to activities.

Revision ID: 005
Revises: 004
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005'
down_revision = '004'


def upgrade() -> None:
    op.add_column(
        'activities',
        sa.Column('ev_method', sa.String(50), 
                  server_default='percent_complete', nullable=False)
    )
    op.add_column(
        'activities',
        sa.Column('milestones_json', postgresql.JSONB, nullable=True)
    )
    op.add_column(
        'activities',
        sa.Column('base_activity_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('activities.id', ondelete='SET NULL'), nullable=True)
    )
    op.add_column(
        'activities',
        sa.Column('apportionment_factor', sa.Numeric(5, 4), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('activities', 'apportionment_factor')
    op.drop_column('activities', 'base_activity_id')
    op.drop_column('activities', 'milestones_json')
    op.drop_column('activities', 'ev_method')
```

### 3. Update EVMS Period Repository
File: api/src/repositories/evms_period.py (update get_cumulative_values)

```python
from src.services.ev_methods import calculate_activity_bcwp

async def calculate_program_bcwp(
    self,
    program_id: UUID,
    period_id: UUID,
) -> Decimal:
    """
    Calculate total BCWP for a program using activity-level EV methods.
    
    Each activity's BCWP is calculated according to its configured method.
    """
    # Get all activities with their EV methods
    activity_repo = ActivityRepository(self.session)
    activities = await activity_repo.get_by_program(program_id)
    
    # Get time-phased BCWS data for LOE calculations
    bcws_by_activity = await self._get_bcws_by_activity(program_id, period_id)
    
    total_bcwp = Decimal("0")
    
    for activity in activities:
        bcws_to_date = bcws_by_activity.get(activity.id)
        
        # Handle apportioned effort
        base_bcwp = None
        if activity.base_activity_id:
            base_activity = next(
                (a for a in activities if a.id == activity.base_activity_id), 
                None
            )
            if base_activity:
                base_bcwp = calculate_activity_bcwp(base_activity, bcws_to_date)
        
        activity_bcwp = calculate_activity_bcwp(
            activity,
            bcws_to_date=bcws_to_date,
            base_activity_bcwp=base_bcwp,
        )
        total_bcwp += activity_bcwp
    
    return total_bcwp
```

### 4. Add EV Method Endpoint
File: api/src/api/v1/endpoints/evms.py (add)

```python
@router.get("/ev-methods")
async def list_ev_methods() -> list[dict]:
    """List all available EV methods with descriptions."""
    return [
        {
            "value": EVMethod.ZERO_HUNDRED.value,
            "name": "0/100",
            "description": "0% until complete, then 100%. Best for short discrete tasks.",
        },
        {
            "value": EVMethod.FIFTY_FIFTY.value,
            "name": "50/50",
            "description": "50% at start, 50% at completion. Best for 1-2 month tasks.",
        },
        {
            "value": EVMethod.MILESTONE_WEIGHT.value,
            "name": "Milestone Weight",
            "description": "BCWP based on weighted milestone completion.",
        },
        {
            "value": EVMethod.PERCENT_COMPLETE.value,
            "name": "% Complete",
            "description": "Subjective % estimate. Most flexible, requires discipline.",
        },
        {
            "value": EVMethod.LOE.value,
            "name": "Level of Effort",
            "description": "BCWP equals BCWS. For support activities with no discrete output.",
        },
    ]


@router.post("/activities/{activity_id}/ev-method")
async def set_activity_ev_method(
    activity_id: UUID,
    ev_method: EVMethod,
    milestones: list[dict] | None = None,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> ActivityResponse:
    """Set the EV method for an activity."""
    activity_repo = ActivityRepository(db)
    activity = await activity_repo.get_by_id(activity_id)
    
    if not activity:
        raise NotFoundError("Activity", activity_id)
    
    # Verify authorization
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")
    
    # Validate milestone weights sum to 1.0 if using milestone method
    if ev_method == EVMethod.MILESTONE_WEIGHT and milestones:
        total_weight = sum(Decimal(str(m.get("weight", 0))) for m in milestones)
        if abs(total_weight - Decimal("1.0")) > Decimal("0.001"):
            raise ValidationError("Milestone weights must sum to 1.0")
    
    # Update activity
    activity.ev_method = ev_method.value
    if milestones:
        activity.milestones_json = milestones
    
    await activity_repo.update(activity)
    await db.commit()
    
    return ActivityResponse.model_validate(activity)
```

### 5. Create Integration Tests
File: api/tests/integration/test_ev_methods_api.py

```python
"""Integration tests for EV method API endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4

pytestmark = pytest.mark.asyncio


class TestEVMethodsAPI:
    """Tests for EV method API."""

    async def test_list_ev_methods(self, client: AsyncClient, auth_headers: dict):
        """Should return list of available EV methods."""
        response = await client.get(
            "/api/v1/evms/ev-methods",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        methods = response.json()
        assert len(methods) >= 5
        assert any(m["value"] == "0/100" for m in methods)

    async def test_set_activity_ev_method(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Should update activity EV method."""
        program_id = test_program["id"]
        
        # Create WBS
        wbs = await client.post(
            "/api/v1/wbs",
            headers=auth_headers,
            json={"program_id": program_id, "code": "1", "name": "Test WBS"},
        )
        wbs_id = wbs.json()["id"]
        
        # Create activity
        activity = await client.post(
            "/api/v1/activities",
            headers=auth_headers,
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "code": "A-001",
                "name": "Test Activity",
                "duration": 10,
                "budgeted_cost": "10000.00",
            },
        )
        activity_id = activity.json()["id"]
        
        # Set EV method to 50/50
        response = await client.post(
            f"/api/v1/evms/activities/{activity_id}/ev-method",
            headers=auth_headers,
            json={"ev_method": "50/50"},
        )
        
        assert response.status_code == 200
        assert response.json()["ev_method"] == "50/50"

    async def test_milestone_weight_validation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_activity: dict,
    ):
        """Should validate milestone weights sum to 1.0."""
        activity_id = test_activity["id"]
        
        # Invalid weights (sum = 0.75)
        response = await client.post(
            f"/api/v1/evms/activities/{activity_id}/ev-method",
            headers=auth_headers,
            json={
                "ev_method": "milestone_weight",
                "milestones": [
                    {"name": "Design", "weight": 0.25},
                    {"name": "Build", "weight": 0.50},
                ],
            },
        )
        
        assert response.status_code == 400
        assert "sum to 1.0" in response.json()["detail"]
```

## Verification
```bash
cd api
alembic upgrade head
ruff check src tests --fix
mypy src --ignore-missing-imports
pytest tests/unit/test_ev_methods.py -v
pytest tests/integration/test_ev_methods_api.py -v
pytest --cov=src --cov-report=term-missing
```

## Git Workflow
```bash
git checkout -b feature/ev-methods-integration
git add .
git commit -m "feat(evms): integrate EV methods with API and period tracking

- Add EV method fields to Activity schema
- Add migration for EV method columns
- Add EV method list and update endpoints
- Integrate EV methods with BCWP calculation
- Add integration tests

BCWP now calculated per activity using configured method"

git push -u origin feature/ev-methods-integration
```

Create PR titled: "Feature: EV Methods API Integration"
```

---

### Prompt 5.2.1: Baseline Management Model & CRUD

```
Implement baseline management model and CRUD operations for EVMS compliance.

## Prerequisites
- Prompt 5.1.2 complete (EV methods integrated)
- Existing Program model

## Context
Per architecture, baselines are:
- Immutable snapshots of program data
- Versioned with version control
- Used for EVMS comparison (baseline vs. current)
- Foundation for scenario planning

## Implementation Plan

### 1. Create Baseline Model
File: api/src/models/baseline.py

```python
"""Baseline model for immutable program snapshots."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Baseline(Base):
    """
    Immutable snapshot of program schedule and cost data.
    
    Baselines capture a point-in-time view of the program for:
    - EVMS Performance Measurement Baseline (PMB)
    - Variance analysis comparison
    - Audit trail and compliance
    - Scenario planning reference
    
    Once created, baseline data cannot be modified. New versions
    must be created through formal change control.
    """
    
    __tablename__ = "baselines"

    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Baseline name (e.g., 'PMB Rev 1', 'Contract Baseline')",
    )
    
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Sequential version number within program",
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Baseline description and change justification",
    )
    
    # Snapshot data stored as JSONB for flexibility
    schedule_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Snapshot of activities, dependencies, dates",
    )
    
    cost_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Snapshot of WBS budgets, time-phased BCWS",
    )
    
    wbs_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Snapshot of WBS hierarchy",
    )
    
    # Approval workflow
    is_approved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether baseline is approved for use",
    )
    
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    created_by_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    
    # Summary metrics captured at baseline time
    total_bac: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Budget at Completion at baseline time",
    )
    
    scheduled_finish: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Scheduled completion date at baseline time",
    )

    # Relationships
    program: Mapped["Program"] = relationship(back_populates="baselines")
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    approved_by: Mapped[Optional["User"]] = relationship(foreign_keys=[approved_by_id])

    __table_args__ = (
        Index("ix_baselines_program_version", "program_id", "version", unique=True),
    )
```

### 2. Create Baseline Schemas
File: api/src/schemas/baseline.py

```python
"""Pydantic schemas for baseline management."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BaselineBase(BaseModel):
    """Base schema for baselines."""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)


class BaselineCreate(BaselineBase):
    """Schema for creating a baseline."""
    
    program_id: UUID


class BaselineResponse(BaselineBase):
    """Schema for baseline response."""
    
    id: UUID
    program_id: UUID
    version: int
    is_approved: bool
    approved_at: datetime | None
    approved_by_id: UUID | None
    created_by_id: UUID
    created_at: datetime
    
    # Summary metrics
    total_bac: dict | None
    scheduled_finish: datetime | None
    
    # Snapshot sizes (not full data)
    activity_count: int = 0
    wbs_count: int = 0

    model_config = {"from_attributes": True}


class BaselineDetailResponse(BaselineResponse):
    """Schema for detailed baseline response with snapshots."""
    
    schedule_snapshot: dict
    cost_snapshot: dict
    wbs_snapshot: dict


class BaselineComparisonResponse(BaseModel):
    """Schema for baseline vs. current comparison."""
    
    baseline_id: UUID
    baseline_version: int
    baseline_name: str
    
    # Schedule variances
    schedule_variance_days: int
    activities_added: int
    activities_removed: int
    activities_modified: int
    
    # Cost variances
    bac_baseline: Decimal
    bac_current: Decimal
    bac_variance: Decimal
    bac_variance_pct: Decimal
    
    # Critical path comparison
    baseline_duration: int
    current_duration: int
    duration_variance: int
```

### 3. Create Baseline Repository
File: api/src/repositories/baseline.py

```python
"""Repository for baseline operations."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.models.baseline import Baseline
from src.models.activity import Activity
from src.models.wbs import WBSElement
from src.repositories.base import BaseRepository


class BaselineRepository(BaseRepository[Baseline]):
    """Repository for Baseline CRUD operations."""

    def __init__(self, session):
        super().__init__(Baseline, session)

    async def get_by_program(
        self,
        program_id: UUID,
        include_snapshots: bool = False,
    ) -> list[Baseline]:
        """Get all baselines for a program."""
        query = (
            select(Baseline)
            .where(Baseline.program_id == program_id)
            .where(Baseline.deleted_at.is_(None))
            .order_by(Baseline.version.desc())
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest(self, program_id: UUID) -> Optional[Baseline]:
        """Get the most recent approved baseline for a program."""
        result = await self.session.execute(
            select(Baseline)
            .where(Baseline.program_id == program_id)
            .where(Baseline.is_approved == True)
            .where(Baseline.deleted_at.is_(None))
            .order_by(Baseline.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_next_version(self, program_id: UUID) -> int:
        """Get the next version number for a program."""
        result = await self.session.execute(
            select(func.max(Baseline.version))
            .where(Baseline.program_id == program_id)
            .where(Baseline.deleted_at.is_(None))
        )
        max_version = result.scalar() or 0
        return max_version + 1

    async def create_snapshot(
        self,
        program_id: UUID,
        name: str,
        description: str | None,
        created_by_id: UUID,
    ) -> Baseline:
        """
        Create a new baseline with snapshots of current program data.
        
        Captures:
        - All activities with dates, durations, dependencies
        - WBS hierarchy with budgets
        - Time-phased cost data
        """
        from src.repositories.activity import ActivityRepository
        from src.repositories.dependency import DependencyRepository
        from src.repositories.wbs import WBSRepository
        
        # Get current data
        activity_repo = ActivityRepository(self.session)
        wbs_repo = WBSRepository(self.session)
        dep_repo = DependencyRepository(self.session)
        
        activities = await activity_repo.get_by_program(program_id, limit=50000)
        wbs_elements = await wbs_repo.get_by_program(program_id)
        dependencies = await dep_repo.get_by_program(program_id)
        
        # Build schedule snapshot
        schedule_snapshot = {
            "activities": [
                {
                    "id": str(a.id),
                    "code": a.code,
                    "name": a.name,
                    "duration": a.duration,
                    "early_start": a.early_start.isoformat() if a.early_start else None,
                    "early_finish": a.early_finish.isoformat() if a.early_finish else None,
                    "late_start": a.late_start.isoformat() if a.late_start else None,
                    "late_finish": a.late_finish.isoformat() if a.late_finish else None,
                    "total_float": a.total_float,
                    "is_critical": a.is_critical,
                    "is_milestone": a.is_milestone,
                    "percent_complete": str(a.percent_complete) if a.percent_complete else "0",
                    "ev_method": a.ev_method,
                }
                for a in activities
            ],
            "dependencies": [
                {
                    "predecessor_id": str(d.predecessor_id),
                    "successor_id": str(d.successor_id),
                    "type": d.dependency_type.value,
                    "lag": d.lag,
                }
                for d in dependencies
            ],
        }
        
        # Build WBS snapshot
        wbs_snapshot = {
            "elements": [
                {
                    "id": str(w.id),
                    "code": w.code,
                    "name": w.name,
                    "path": w.path,
                    "level": w.level,
                    "is_control_account": w.is_control_account,
                    "budgeted_cost": str(w.budgeted_cost) if w.budgeted_cost else None,
                }
                for w in wbs_elements
            ],
        }
        
        # Build cost snapshot
        total_bac = sum(
            w.budgeted_cost for w in wbs_elements 
            if w.budgeted_cost and w.is_control_account
        )
        
        cost_snapshot = {
            "total_bac": str(total_bac),
            "by_wbs": {
                str(w.id): str(w.budgeted_cost) if w.budgeted_cost else "0"
                for w in wbs_elements
            },
        }
        
        # Calculate scheduled finish from CPM
        if activities:
            max_finish = max(
                (a.early_finish for a in activities if a.early_finish),
                default=None
            )
        else:
            max_finish = None
        
        # Create baseline
        version = await self.get_next_version(program_id)
        
        baseline = Baseline(
            program_id=program_id,
            name=name,
            version=version,
            description=description,
            schedule_snapshot=schedule_snapshot,
            cost_snapshot=cost_snapshot,
            wbs_snapshot=wbs_snapshot,
            created_by_id=created_by_id,
            total_bac={"value": str(total_bac)},
            scheduled_finish=max_finish,
        )
        
        self.session.add(baseline)
        await self.session.flush()
        
        return baseline
```

### 4. Create Baseline Endpoints
File: api/src/api/v1/endpoints/baselines.py

```python
"""Baseline management endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from src.core.deps import DbSession, get_current_user
from src.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from src.models.user import User
from src.repositories.baseline import BaselineRepository
from src.repositories.program import ProgramRepository
from src.schemas.baseline import (
    BaselineCreate,
    BaselineResponse,
    BaselineDetailResponse,
    BaselineComparisonResponse,
)

router = APIRouter()


@router.get("", response_model=list[BaselineResponse])
async def list_baselines(
    program_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[BaselineResponse]:
    """List all baselines for a program."""
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError("Program", program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    baseline_repo = BaselineRepository(db)
    baselines = await baseline_repo.get_by_program(program_id)
    
    return [
        BaselineResponse(
            **b.__dict__,
            activity_count=len(b.schedule_snapshot.get("activities", [])),
            wbs_count=len(b.wbs_snapshot.get("elements", [])),
        )
        for b in baselines
    ]


@router.post("", response_model=BaselineResponse, status_code=201)
async def create_baseline(
    baseline_in: BaselineCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> BaselineResponse:
    """
    Create a new baseline snapshot.
    
    Captures current state of:
    - All activities with dates and CPM results
    - All dependencies
    - WBS hierarchy with budgets
    - Cost data
    """
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(baseline_in.program_id)
    if not program:
        raise NotFoundError("Program", baseline_in.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    baseline_repo = BaselineRepository(db)
    baseline = await baseline_repo.create_snapshot(
        program_id=baseline_in.program_id,
        name=baseline_in.name,
        description=baseline_in.description,
        created_by_id=current_user.id,
    )
    
    await db.commit()
    
    return BaselineResponse(
        **baseline.__dict__,
        activity_count=len(baseline.schedule_snapshot.get("activities", [])),
        wbs_count=len(baseline.wbs_snapshot.get("elements", [])),
    )


@router.get("/{baseline_id}", response_model=BaselineDetailResponse)
async def get_baseline(
    baseline_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> BaselineDetailResponse:
    """Get baseline details including full snapshots."""
    baseline_repo = BaselineRepository(db)
    baseline = await baseline_repo.get_by_id(baseline_id)
    
    if not baseline:
        raise NotFoundError("Baseline", baseline_id)
    
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(baseline.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    return BaselineDetailResponse(
        **baseline.__dict__,
        activity_count=len(baseline.schedule_snapshot.get("activities", [])),
        wbs_count=len(baseline.wbs_snapshot.get("elements", [])),
    )


@router.post("/{baseline_id}/approve", response_model=BaselineResponse)
async def approve_baseline(
    baseline_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> BaselineResponse:
    """Approve a baseline for use as PMB."""
    baseline_repo = BaselineRepository(db)
    baseline = await baseline_repo.get_by_id(baseline_id)
    
    if not baseline:
        raise NotFoundError("Baseline", baseline_id)
    
    if baseline.is_approved:
        raise ValidationError("Baseline is already approved")
    
    # Verify access (only program owner or admin can approve)
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(baseline.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Only program owner can approve baselines")

    baseline.is_approved = True
    baseline.approved_at = datetime.utcnow()
    baseline.approved_by_id = current_user.id
    
    await db.commit()
    
    return BaselineResponse(
        **baseline.__dict__,
        activity_count=len(baseline.schedule_snapshot.get("activities", [])),
        wbs_count=len(baseline.wbs_snapshot.get("elements", [])),
    )
```

### 5. Add Router
Add to api/src/api/v1/router.py:
```python
from src.api.v1.endpoints import baselines

api_router.include_router(baselines.router, prefix="/baselines", tags=["Baselines"])
```

## Verification
```bash
cd api
alembic revision --autogenerate -m "add baselines table"
alembic upgrade head
ruff check src tests --fix
mypy src --ignore-missing-imports
pytest tests/ -v --cov=src
```

## Git Workflow
```bash
git checkout -b feature/baseline-management
git add .
git commit -m "feat(baseline): implement baseline management model and CRUD

- Add Baseline model with JSONB snapshots
- Add BaselineRepository with snapshot creation
- Add baseline endpoints (list, create, get, approve)
- Store schedule, WBS, and cost snapshots
- Support approval workflow for PMB

EVMS compliance: Supports baseline management per GL 8"

git push -u origin feature/baseline-management
```

Create PR titled: "Feature: Baseline Management Model & CRUD"
```

---

### Prompt 5.2.2: Baseline Snapshot & Comparison

```
Implement baseline comparison functionality for variance analysis.

## Prerequisites
- Prompt 5.2.1 complete (Baseline model and CRUD)

## Implementation Plan

### 1. Add Baseline Comparison Service
File: api/src/services/baseline_comparison.py

```python
"""Baseline comparison service for variance analysis."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from src.models.baseline import Baseline
from src.models.activity import Activity
from src.models.wbs import WBSElement


@dataclass
class ScheduleVariance:
    """Schedule variance between baseline and current."""
    
    activity_id: UUID
    activity_code: str
    activity_name: str
    
    baseline_duration: int
    current_duration: int
    duration_variance: int
    
    baseline_start: date | None
    current_start: date | None
    start_variance_days: int
    
    baseline_finish: date | None
    current_finish: date | None
    finish_variance_days: int
    
    was_critical: bool
    is_critical: bool


@dataclass
class CostVariance:
    """Cost variance between baseline and current."""
    
    wbs_id: UUID
    wbs_code: str
    wbs_name: str
    
    baseline_bac: Decimal
    current_bac: Decimal
    bac_variance: Decimal
    bac_variance_pct: Decimal


@dataclass
class BaselineComparison:
    """Full comparison result."""
    
    baseline_id: UUID
    baseline_version: int
    baseline_name: str
    
    # Summary stats
    activities_in_baseline: int
    activities_current: int
    activities_added: int
    activities_removed: int
    activities_modified: int
    
    # Schedule summary
    baseline_duration: int
    current_duration: int
    duration_variance: int
    
    # Cost summary
    baseline_bac: Decimal
    current_bac: Decimal
    bac_variance: Decimal
    bac_variance_pct: Decimal
    
    # Detailed variances
    schedule_variances: list[ScheduleVariance]
    cost_variances: list[CostVariance]


class BaselineComparisonService:
    """
    Compare baseline snapshots with current program data.
    
    Provides:
    - Activity-level schedule variance
    - WBS-level cost variance
    - Summary metrics for reporting
    """

    def __init__(
        self,
        baseline: Baseline,
        current_activities: list[Activity],
        current_wbs: list[WBSElement],
    ):
        self.baseline = baseline
        self.current_activities = {a.id: a for a in current_activities}
        self.current_wbs = {w.id: w for w in current_wbs}
        
        # Parse baseline snapshots
        self.baseline_activities = {
            UUID(a["id"]): a 
            for a in baseline.schedule_snapshot.get("activities", [])
        }
        self.baseline_wbs = {
            UUID(w["id"]): w 
            for w in baseline.wbs_snapshot.get("elements", [])
        }

    def compare(self) -> BaselineComparison:
        """Perform full baseline comparison."""
        schedule_variances = self._compare_schedule()
        cost_variances = self._compare_costs()
        
        # Count changes
        baseline_ids = set(self.baseline_activities.keys())
        current_ids = set(self.current_activities.keys())
        
        added = current_ids - baseline_ids
        removed = baseline_ids - current_ids
        common = baseline_ids & current_ids
        
        # Count modifications
        modified = sum(
            1 for aid in common
            if self._is_activity_modified(aid)
        )
        
        # Calculate project duration
        baseline_duration = self._get_baseline_duration()
        current_duration = self._get_current_duration()
        
        # Calculate total BAC
        baseline_bac = self._get_baseline_bac()
        current_bac = self._get_current_bac()
        bac_variance = current_bac - baseline_bac
        bac_variance_pct = (
            (bac_variance / baseline_bac * 100) 
            if baseline_bac > 0 else Decimal("0")
        )
        
        return BaselineComparison(
            baseline_id=self.baseline.id,
            baseline_version=self.baseline.version,
            baseline_name=self.baseline.name,
            activities_in_baseline=len(baseline_ids),
            activities_current=len(current_ids),
            activities_added=len(added),
            activities_removed=len(removed),
            activities_modified=modified,
            baseline_duration=baseline_duration,
            current_duration=current_duration,
            duration_variance=current_duration - baseline_duration,
            baseline_bac=baseline_bac,
            current_bac=current_bac,
            bac_variance=bac_variance,
            bac_variance_pct=bac_variance_pct,
            schedule_variances=schedule_variances,
            cost_variances=cost_variances,
        )

    def _compare_schedule(self) -> list[ScheduleVariance]:
        """Compare activity schedules."""
        variances = []
        
        for aid, baseline_act in self.baseline_activities.items():
            current_act = self.current_activities.get(aid)
            
            if not current_act:
                continue  # Removed activity
            
            baseline_duration = baseline_act.get("duration", 0)
            current_duration = current_act.duration or 0
            
            baseline_start = self._parse_date(baseline_act.get("early_start"))
            current_start = current_act.early_start
            
            baseline_finish = self._parse_date(baseline_act.get("early_finish"))
            current_finish = current_act.early_finish
            
            variances.append(ScheduleVariance(
                activity_id=aid,
                activity_code=baseline_act.get("code", ""),
                activity_name=baseline_act.get("name", ""),
                baseline_duration=baseline_duration,
                current_duration=current_duration,
                duration_variance=current_duration - baseline_duration,
                baseline_start=baseline_start,
                current_start=current_start,
                start_variance_days=self._days_between(baseline_start, current_start),
                baseline_finish=baseline_finish,
                current_finish=current_finish,
                finish_variance_days=self._days_between(baseline_finish, current_finish),
                was_critical=baseline_act.get("is_critical", False),
                is_critical=current_act.is_critical or False,
            ))
        
        return variances

    def _compare_costs(self) -> list[CostVariance]:
        """Compare WBS costs."""
        variances = []
        
        for wid, baseline_wbs in self.baseline_wbs.items():
            current_wbs = self.current_wbs.get(wid)
            
            if not current_wbs:
                continue
            
            baseline_bac = Decimal(
                self.baseline.cost_snapshot.get("by_wbs", {}).get(str(wid), "0")
            )
            current_bac = current_wbs.budgeted_cost or Decimal("0")
            
            variance = current_bac - baseline_bac
            variance_pct = (
                (variance / baseline_bac * 100) 
                if baseline_bac > 0 else Decimal("0")
            )
            
            variances.append(CostVariance(
                wbs_id=wid,
                wbs_code=baseline_wbs.get("code", ""),
                wbs_name=baseline_wbs.get("name", ""),
                baseline_bac=baseline_bac,
                current_bac=current_bac,
                bac_variance=variance,
                bac_variance_pct=variance_pct,
            ))
        
        return variances

    def _is_activity_modified(self, activity_id: UUID) -> bool:
        """Check if activity has been modified from baseline."""
        baseline = self.baseline_activities.get(activity_id)
        current = self.current_activities.get(activity_id)
        
        if not baseline or not current:
            return False
        
        # Check key fields
        if baseline.get("duration") != current.duration:
            return True
        if baseline.get("name") != current.name:
            return True
        
        return False

    def _get_baseline_duration(self) -> int:
        """Get project duration from baseline."""
        if not self.baseline_activities:
            return 0
        
        max_finish = 0
        for act in self.baseline_activities.values():
            ef = act.get("early_finish")
            if ef:
                # Simplified - just count days from activities
                duration = act.get("duration", 0)
                max_finish = max(max_finish, duration)
        
        return max_finish

    def _get_current_duration(self) -> int:
        """Get project duration from current schedule."""
        if not self.current_activities:
            return 0
        
        # Get from CPM results
        max_duration = max(
            (a.duration or 0 for a in self.current_activities.values()),
            default=0
        )
        return max_duration

    def _get_baseline_bac(self) -> Decimal:
        """Get total BAC from baseline."""
        bac_str = self.baseline.cost_snapshot.get("total_bac", "0")
        return Decimal(bac_str)

    def _get_current_bac(self) -> Decimal:
        """Get total BAC from current WBS."""
        return sum(
            w.budgeted_cost or Decimal("0")
            for w in self.current_wbs.values()
            if w.is_control_account
        )

    @staticmethod
    def _parse_date(date_str: str | None) -> date | None:
        """Parse ISO date string."""
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.fromisoformat(date_str).date()
        except ValueError:
            return None

    @staticmethod
    def _days_between(d1: date | None, d2: date | None) -> int:
        """Calculate days between two dates."""
        if not d1 or not d2:
            return 0
        return (d2 - d1).days
```

### 2. Add Comparison Endpoint
File: api/src/api/v1/endpoints/baselines.py (add)

```python
@router.get("/{baseline_id}/compare", response_model=BaselineComparisonResponse)
async def compare_baseline(
    baseline_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> BaselineComparisonResponse:
    """
    Compare baseline with current program state.
    
    Returns:
    - Activity-level schedule variances
    - WBS-level cost variances
    - Summary metrics
    """
    baseline_repo = BaselineRepository(db)
    baseline = await baseline_repo.get_by_id(baseline_id)
    
    if not baseline:
        raise NotFoundError("Baseline", baseline_id)
    
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(baseline.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    # Get current data
    activity_repo = ActivityRepository(db)
    wbs_repo = WBSRepository(db)
    
    current_activities = await activity_repo.get_by_program(baseline.program_id)
    current_wbs = await wbs_repo.get_by_program(baseline.program_id)
    
    # Perform comparison
    service = BaselineComparisonService(
        baseline=baseline,
        current_activities=current_activities,
        current_wbs=current_wbs,
    )
    comparison = service.compare()
    
    return BaselineComparisonResponse(
        baseline_id=comparison.baseline_id,
        baseline_version=comparison.baseline_version,
        baseline_name=comparison.baseline_name,
        schedule_variance_days=comparison.duration_variance,
        activities_added=comparison.activities_added,
        activities_removed=comparison.activities_removed,
        activities_modified=comparison.activities_modified,
        bac_baseline=comparison.baseline_bac,
        bac_current=comparison.current_bac,
        bac_variance=comparison.bac_variance,
        bac_variance_pct=comparison.bac_variance_pct,
        baseline_duration=comparison.baseline_duration,
        current_duration=comparison.current_duration,
        duration_variance=comparison.duration_variance,
    )
```

## Verification
```bash
cd api
ruff check src tests --fix
mypy src --ignore-missing-imports
pytest tests/ -v --cov=src
```

## Git Workflow
```bash
git checkout -b feature/baseline-comparison
git add .
git commit -m "feat(baseline): implement baseline comparison for variance analysis

- Add BaselineComparisonService
- Add schedule variance calculation
- Add cost variance calculation
- Add comparison endpoint
- Support variance reporting for EVMS compliance"

git push -u origin feature/baseline-comparison
```

Create PR titled: "Feature: Baseline Comparison & Variance Analysis"
```

---

### Prompt 5.3.1: Scenario Planning Foundation

```
Implement scenario planning data model for what-if analysis.

## Prerequisites
- Prompt 5.2.2 complete (Baseline comparison)
- Baseline model exists

## Context
Per architecture, scenarios:
- Reference (but never modify) the baseline
- Support branched what-if analysis
- Can be promoted to new baseline
- Store changes as deltas

## Implementation Plan

### 1. Create Scenario Model
File: api/src/models/scenario.py

```python
"""Scenario model for what-if analysis."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Scenario(Base):
    """
    What-if scenario for schedule analysis.
    
    Scenarios allow users to explore changes without
    affecting the baseline or current schedule.
    
    Key features:
    - References a baseline for comparison
    - Stores changes as deltas (not full copies)
    - Can be branched from other scenarios
    - Can be promoted to new baseline
    """
    
    __tablename__ = "scenarios"

    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    baseline_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("baselines.id", ondelete="SET NULL"),
        nullable=True,
        comment="Baseline this scenario is compared against",
    )
    
    parent_scenario_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="SET NULL"),
        nullable=True,
        comment="Parent scenario if branched",
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether scenario is still being worked on",
    )
    
    # Changes stored as delta operations
    changes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Delta changes from baseline/parent",
    )
    
    # Calculated results (cached)
    results_cache: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Cached CPM and metrics results",
    )
    
    # Workflow
    created_by_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    
    promoted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When scenario was promoted to baseline",
    )
    
    promoted_baseline_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("baselines.id", ondelete="SET NULL"),
        nullable=True,
        comment="Baseline created from this scenario",
    )

    # Relationships
    program: Mapped["Program"] = relationship(back_populates="scenarios")
    baseline: Mapped[Optional["Baseline"]] = relationship(
        foreign_keys=[baseline_id]
    )
    parent_scenario: Mapped[Optional["Scenario"]] = relationship(
        remote_side="Scenario.id",
        foreign_keys=[parent_scenario_id],
    )
    created_by: Mapped["User"] = relationship()


class ScenarioChange(Base):
    """
    Individual change within a scenario.
    
    Stored separately for audit trail and potential rollback.
    """
    
    __tablename__ = "scenario_changes"

    scenario_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of entity changed (activity, dependency, wbs)",
    )
    
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        comment="ID of changed entity",
    )
    
    change_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type of change (create, update, delete)",
    )
    
    field_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Field that was changed (for updates)",
    )
    
    old_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Previous value (JSON encoded)",
    )
    
    new_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="New value (JSON encoded)",
    )
    
    # Relationships
    scenario: Mapped["Scenario"] = relationship()

    __table_args__ = (
        Index("ix_scenario_changes_scenario_entity", "scenario_id", "entity_id"),
    )
```

### 2. Create Scenario Schemas
File: api/src/schemas/scenario.py

```python
"""Pydantic schemas for scenario planning."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ScenarioBase(BaseModel):
    """Base schema for scenarios."""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)


class ScenarioCreate(ScenarioBase):
    """Schema for creating a scenario."""
    
    program_id: UUID
    baseline_id: UUID | None = None
    parent_scenario_id: UUID | None = None


class ScenarioUpdate(BaseModel):
    """Schema for updating a scenario."""
    
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)


class ScenarioResponse(ScenarioBase):
    """Schema for scenario response."""
    
    id: UUID
    program_id: UUID
    baseline_id: UUID | None
    parent_scenario_id: UUID | None
    is_active: bool
    created_by_id: UUID
    created_at: datetime
    promoted_at: datetime | None
    change_count: int = 0

    model_config = {"from_attributes": True}


class ScenarioChangeCreate(BaseModel):
    """Schema for adding a change to a scenario."""
    
    entity_type: str = Field(..., description="activity, dependency, or wbs")
    entity_id: UUID
    change_type: str = Field(..., description="create, update, or delete")
    field_name: str | None = None
    new_value: str | None = None


class ScenarioChangeResponse(BaseModel):
    """Schema for scenario change response."""
    
    id: UUID
    scenario_id: UUID
    entity_type: str
    entity_id: UUID
    change_type: str
    field_name: str | None
    old_value: str | None
    new_value: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

### 3. Create Scenario Repository
File: api/src/repositories/scenario.py

```python
"""Repository for scenario operations."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, func

from src.models.scenario import Scenario, ScenarioChange
from src.repositories.base import BaseRepository


class ScenarioRepository(BaseRepository[Scenario]):
    """Repository for Scenario CRUD operations."""

    def __init__(self, session):
        super().__init__(Scenario, session)

    async def get_by_program(
        self,
        program_id: UUID,
        include_inactive: bool = False,
    ) -> list[Scenario]:
        """Get all scenarios for a program."""
        query = (
            select(Scenario)
            .where(Scenario.program_id == program_id)
            .where(Scenario.deleted_at.is_(None))
        )
        
        if not include_inactive:
            query = query.where(Scenario.is_active == True)
        
        query = query.order_by(Scenario.created_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_with_change_count(self, scenario_id: UUID) -> tuple[Scenario, int]:
        """Get scenario with count of changes."""
        scenario = await self.get_by_id(scenario_id)
        
        if not scenario:
            return None, 0
        
        result = await self.session.execute(
            select(func.count(ScenarioChange.id))
            .where(ScenarioChange.scenario_id == scenario_id)
        )
        count = result.scalar() or 0
        
        return scenario, count

    async def add_change(
        self,
        scenario_id: UUID,
        entity_type: str,
        entity_id: UUID,
        change_type: str,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
    ) -> ScenarioChange:
        """Add a change to a scenario."""
        change = ScenarioChange(
            scenario_id=scenario_id,
            entity_type=entity_type,
            entity_id=entity_id,
            change_type=change_type,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
        )
        
        self.session.add(change)
        await self.session.flush()
        
        return change

    async def get_changes(self, scenario_id: UUID) -> list[ScenarioChange]:
        """Get all changes for a scenario."""
        result = await self.session.execute(
            select(ScenarioChange)
            .where(ScenarioChange.scenario_id == scenario_id)
            .order_by(ScenarioChange.created_at)
        )
        return list(result.scalars().all())
```

### 4. Create Scenario Endpoints
File: api/src/api/v1/endpoints/scenarios.py

```python
"""Scenario planning endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from src.core.deps import DbSession, get_current_user
from src.core.exceptions import AuthorizationError, NotFoundError
from src.models.user import User
from src.repositories.scenario import ScenarioRepository
from src.repositories.program import ProgramRepository
from src.schemas.scenario import (
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioResponse,
    ScenarioChangeCreate,
    ScenarioChangeResponse,
)

router = APIRouter()


@router.get("", response_model=list[ScenarioResponse])
async def list_scenarios(
    program_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    include_inactive: bool = False,
) -> list[ScenarioResponse]:
    """List all scenarios for a program."""
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError("Program", program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    scenario_repo = ScenarioRepository(db)
    scenarios = await scenario_repo.get_by_program(program_id, include_inactive)
    
    results = []
    for s in scenarios:
        _, change_count = await scenario_repo.get_with_change_count(s.id)
        results.append(ScenarioResponse(
            **s.__dict__,
            change_count=change_count,
        ))
    
    return results


@router.post("", response_model=ScenarioResponse, status_code=201)
async def create_scenario(
    scenario_in: ScenarioCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ScenarioResponse:
    """Create a new scenario."""
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(scenario_in.program_id)
    if not program:
        raise NotFoundError("Program", scenario_in.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    scenario_repo = ScenarioRepository(db)
    
    from src.models.scenario import Scenario
    scenario = Scenario(
        program_id=scenario_in.program_id,
        baseline_id=scenario_in.baseline_id,
        parent_scenario_id=scenario_in.parent_scenario_id,
        name=scenario_in.name,
        description=scenario_in.description,
        created_by_id=current_user.id,
        changes={},
    )
    
    await scenario_repo.create(scenario)
    await db.commit()
    
    return ScenarioResponse(**scenario.__dict__, change_count=0)


@router.post("/{scenario_id}/changes", response_model=ScenarioChangeResponse)
async def add_scenario_change(
    scenario_id: UUID,
    change_in: ScenarioChangeCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ScenarioChangeResponse:
    """Add a change to a scenario."""
    scenario_repo = ScenarioRepository(db)
    scenario = await scenario_repo.get_by_id(scenario_id)
    
    if not scenario:
        raise NotFoundError("Scenario", scenario_id)
    
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(scenario.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    change = await scenario_repo.add_change(
        scenario_id=scenario_id,
        entity_type=change_in.entity_type,
        entity_id=change_in.entity_id,
        change_type=change_in.change_type,
        field_name=change_in.field_name,
        new_value=change_in.new_value,
    )
    
    await db.commit()
    
    return ScenarioChangeResponse(**change.__dict__)


@router.get("/{scenario_id}/changes", response_model=list[ScenarioChangeResponse])
async def list_scenario_changes(
    scenario_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ScenarioChangeResponse]:
    """List all changes in a scenario."""
    scenario_repo = ScenarioRepository(db)
    scenario = await scenario_repo.get_by_id(scenario_id)
    
    if not scenario:
        raise NotFoundError("Scenario", scenario_id)
    
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(scenario.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    changes = await scenario_repo.get_changes(scenario_id)
    
    return [ScenarioChangeResponse(**c.__dict__) for c in changes]
```

### 5. Add Router
Add to api/src/api/v1/router.py:
```python
from src.api.v1.endpoints import scenarios

api_router.include_router(scenarios.router, prefix="/scenarios", tags=["Scenarios"])
```

## Verification
```bash
cd api
alembic revision --autogenerate -m "add scenarios table"
alembic upgrade head
ruff check src tests --fix
mypy src --ignore-missing-imports
pytest tests/ -v --cov=src
```

## Git Workflow
```bash
git checkout -b feature/scenario-planning
git add .
git commit -m "feat(scenario): implement scenario planning foundation

- Add Scenario model with delta-based changes
- Add ScenarioChange model for audit trail
- Add scenario CRUD endpoints
- Support parent scenarios (branching)
- Support baseline references

Foundation for what-if analysis per architecture"

git push -u origin feature/scenario-planning
```

Create PR titled: "Feature: Scenario Planning Foundation"
```

---

### Prompt 5.4.1: Monte Carlo Engine Foundation

```
Implement Monte Carlo simulation engine foundation using NumPy.

## Prerequisites
- Prompt 5.3.1 complete (Scenario planning)
- NumPy and SciPy installed

## Context
Per architecture:
- Vectorized NumPy (100x faster than loops)
- Target: <5s for 1000 simulations
- Support multiple probability distributions
- Progressive streaming for large simulations

## Implementation Plan

### 1. Create Simulation Models
File: api/src/models/simulation.py

```python
"""Simulation models for Monte Carlo analysis."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class SimulationConfig(Base):
    """
    Monte Carlo simulation configuration.
    
    Defines:
    - Which activities have uncertainty
    - Distribution types and parameters
    - Number of iterations
    """
    
    __tablename__ = "simulation_configs"

    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    scenario_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=True,
        comment="Optional scenario to simulate",
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    iterations: Mapped[int] = mapped_column(
        Integer,
        default=1000,
        nullable=False,
    )
    
    # Activity uncertainty definitions
    # Format: {activity_id: {distribution: "triangular", min: 5, mode: 10, max: 20}}
    activity_distributions: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    
    # Cost uncertainty definitions
    cost_distributions: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    
    created_by_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )

    # Relationships
    program: Mapped["Program"] = relationship()
    scenario: Mapped[Optional["Scenario"]] = relationship()


class SimulationResult(Base):
    """
    Monte Carlo simulation results.
    
    Stores:
    - Percentile results (P50, P80, P90)
    - Full distribution data
    - Statistics
    """
    
    __tablename__ = "simulation_results"

    config_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("simulation_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        comment="pending, running, completed, failed",
    )
    
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    iterations_completed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    
    # Results
    duration_results: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Duration distribution: p10, p50, p80, p90, mean, std",
    )
    
    cost_results: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Cost distribution: p10, p50, p80, p90, mean, std",
    )
    
    # Full histogram data for visualization
    duration_histogram: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    
    cost_histogram: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    config: Mapped["SimulationConfig"] = relationship()
```

### 2. Create Monte Carlo Engine
File: api/src/services/monte_carlo.py

```python
"""Monte Carlo simulation engine using NumPy."""

import time
from dataclasses import dataclass
from typing import Callable
from uuid import UUID

import numpy as np
from numpy.typing import NDArray


@dataclass
class DistributionParams:
    """Parameters for probability distribution."""
    
    distribution: str  # triangular, normal, uniform, pert
    min_value: float | None = None
    max_value: float | None = None
    mode: float | None = None  # For triangular/PERT
    mean: float | None = None  # For normal
    std: float | None = None   # For normal


@dataclass
class SimulationInput:
    """Input for Monte Carlo simulation."""
    
    activity_durations: dict[UUID, DistributionParams]
    activity_costs: dict[UUID, DistributionParams] | None = None
    iterations: int = 1000
    seed: int | None = None


@dataclass
class SimulationOutput:
    """Output from Monte Carlo simulation."""
    
    # Duration results
    duration_samples: NDArray[np.float64]
    duration_p10: float
    duration_p50: float
    duration_p80: float
    duration_p90: float
    duration_mean: float
    duration_std: float
    
    # Cost results (if provided)
    cost_samples: NDArray[np.float64] | None = None
    cost_p10: float | None = None
    cost_p50: float | None = None
    cost_p80: float | None = None
    cost_p90: float | None = None
    cost_mean: float | None = None
    cost_std: float | None = None
    
    # Metadata
    iterations: int = 0
    elapsed_seconds: float = 0.0


class MonteCarloEngine:
    """
    Vectorized Monte Carlo simulation engine.
    
    Uses NumPy for high-performance simulation:
    - Generates all random samples at once
    - Performs vectorized calculations
    - Target: 1000 iterations in <5 seconds
    
    Supported distributions:
    - Triangular: min, mode, max
    - Normal: mean, std
    - Uniform: min, max
    - PERT: min, mode, max (beta distribution)
    """

    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)

    def simulate(self, input: SimulationInput) -> SimulationOutput:
        """
        Run Monte Carlo simulation.
        
        Args:
            input: Simulation parameters and distributions
            
        Returns:
            SimulationOutput with percentiles and statistics
        """
        start_time = time.perf_counter()
        
        iterations = input.iterations
        
        # Generate duration samples for all activities
        duration_matrix = self._generate_samples(
            input.activity_durations,
            iterations,
        )
        
        # Sum durations (simplified - actual would use CPM)
        # For a more accurate simulation, we'd need to simulate
        # the network with dependencies
        total_durations = np.sum(duration_matrix, axis=1)
        
        # Generate cost samples if provided
        total_costs = None
        if input.activity_costs:
            cost_matrix = self._generate_samples(
                input.activity_costs,
                iterations,
            )
            total_costs = np.sum(cost_matrix, axis=1)
        
        elapsed = time.perf_counter() - start_time
        
        # Calculate percentiles and statistics
        output = SimulationOutput(
            duration_samples=total_durations,
            duration_p10=float(np.percentile(total_durations, 10)),
            duration_p50=float(np.percentile(total_durations, 50)),
            duration_p80=float(np.percentile(total_durations, 80)),
            duration_p90=float(np.percentile(total_durations, 90)),
            duration_mean=float(np.mean(total_durations)),
            duration_std=float(np.std(total_durations)),
            iterations=iterations,
            elapsed_seconds=elapsed,
        )
        
        if total_costs is not None:
            output.cost_samples = total_costs
            output.cost_p10 = float(np.percentile(total_costs, 10))
            output.cost_p50 = float(np.percentile(total_costs, 50))
            output.cost_p80 = float(np.percentile(total_costs, 80))
            output.cost_p90 = float(np.percentile(total_costs, 90))
            output.cost_mean = float(np.mean(total_costs))
            output.cost_std = float(np.std(total_costs))
        
        return output

    def _generate_samples(
        self,
        distributions: dict[UUID, DistributionParams],
        iterations: int,
    ) -> NDArray[np.float64]:
        """
        Generate random samples for all activities.
        
        Returns matrix of shape (iterations, num_activities).
        """
        num_activities = len(distributions)
        samples = np.zeros((iterations, num_activities))
        
        for i, (activity_id, params) in enumerate(distributions.items()):
            samples[:, i] = self._sample_distribution(params, iterations)
        
        return samples

    def _sample_distribution(
        self,
        params: DistributionParams,
        n: int,
    ) -> NDArray[np.float64]:
        """Generate n samples from the specified distribution."""
        
        if params.distribution == "triangular":
            return self.rng.triangular(
                left=params.min_value,
                mode=params.mode,
                right=params.max_value,
                size=n,
            )
        
        elif params.distribution == "normal":
            return self.rng.normal(
                loc=params.mean,
                scale=params.std,
                size=n,
            )
        
        elif params.distribution == "uniform":
            return self.rng.uniform(
                low=params.min_value,
                high=params.max_value,
                size=n,
            )
        
        elif params.distribution == "pert":
            # PERT uses beta distribution
            # Shape parameters derived from min, mode, max
            return self._sample_pert(
                params.min_value,
                params.mode,
                params.max_value,
                n,
            )
        
        else:
            raise ValueError(f"Unknown distribution: {params.distribution}")

    def _sample_pert(
        self,
        min_val: float,
        mode: float,
        max_val: float,
        n: int,
    ) -> NDArray[np.float64]:
        """
        Sample from PERT distribution.
        
        PERT is a beta distribution with:
        - mean = (min + 4*mode + max) / 6
        - Shape parameters derived from this relationship
        """
        # Calculate mean
        mean = (min_val + 4 * mode + max_val) / 6
        
        # Standard PERT uses lambda=4 for shape calculation
        range_val = max_val - min_val
        
        if range_val == 0:
            return np.full(n, min_val)
        
        # Alpha and beta for beta distribution
        alpha = 1 + 4 * (mode - min_val) / range_val
        beta_param = 1 + 4 * (max_val - mode) / range_val
        
        # Sample from beta and scale to range
        samples = self.rng.beta(alpha, beta_param, size=n)
        return min_val + samples * range_val


def create_histogram_data(
    samples: NDArray[np.float64],
    bins: int = 50,
) -> dict:
    """
    Create histogram data for visualization.
    
    Returns dict with:
    - bin_edges: list of bin boundaries
    - counts: list of counts per bin
    - percentiles: dict of key percentiles
    """
    counts, bin_edges = np.histogram(samples, bins=bins)
    
    return {
        "bin_edges": bin_edges.tolist(),
        "counts": counts.tolist(),
        "percentiles": {
            "p10": float(np.percentile(samples, 10)),
            "p25": float(np.percentile(samples, 25)),
            "p50": float(np.percentile(samples, 50)),
            "p75": float(np.percentile(samples, 75)),
            "p90": float(np.percentile(samples, 90)),
        },
    }
```

### 3. Create Monte Carlo Tests
File: api/tests/unit/test_monte_carlo.py

```python
"""Unit tests for Monte Carlo engine."""

import pytest
import numpy as np
from uuid import uuid4

from src.services.monte_carlo import (
    MonteCarloEngine,
    SimulationInput,
    DistributionParams,
    create_histogram_data,
)


class TestMonteCarloEngine:
    """Tests for Monte Carlo simulation."""

    def test_triangular_distribution(self):
        """Should generate valid triangular samples."""
        engine = MonteCarloEngine(seed=42)
        
        input = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution="triangular",
                    min_value=5,
                    mode=10,
                    max_value=20,
                ),
            },
            iterations=1000,
        )
        
        output = engine.simulate(input)
        
        # Check samples are within bounds
        assert output.duration_samples.min() >= 5
        assert output.duration_samples.max() <= 20
        
        # Check percentiles are reasonable
        assert 5 <= output.duration_p10 <= 20
        assert output.duration_p50 <= output.duration_p90

    def test_normal_distribution(self):
        """Should generate valid normal samples."""
        engine = MonteCarloEngine(seed=42)
        
        input = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution="normal",
                    mean=100,
                    std=10,
                ),
            },
            iterations=1000,
        )
        
        output = engine.simulate(input)
        
        # Mean should be close to 100
        assert 95 <= output.duration_mean <= 105
        
        # Std should be close to 10
        assert 8 <= output.duration_std <= 12

    def test_pert_distribution(self):
        """Should generate valid PERT samples."""
        engine = MonteCarloEngine(seed=42)
        
        input = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution="pert",
                    min_value=5,
                    mode=10,
                    max_value=25,
                ),
            },
            iterations=1000,
        )
        
        output = engine.simulate(input)
        
        # Check samples are within bounds
        assert output.duration_samples.min() >= 5
        assert output.duration_samples.max() <= 25
        
        # Mode should be most common value region
        assert output.duration_p50 < output.duration_mean  # PERT is right-skewed

    def test_multiple_activities(self):
        """Should handle multiple activities."""
        engine = MonteCarloEngine(seed=42)
        
        input = SimulationInput(
            activity_durations={
                uuid4(): DistributionParams(
                    distribution="triangular",
                    min_value=5, mode=10, max_value=15,
                ),
                uuid4(): DistributionParams(
                    distribution="triangular",
                    min_value=10, mode=20, max_value=30,
                ),
                uuid4(): DistributionParams(
                    distribution="triangular",
                    min_value=15, mode=25, max_value=40,
                ),
            },
            iterations=1000,
        )
        
        output = engine.simulate(input)
        
        # Sum should be in range [30, 85]
        assert output.duration_samples.min() >= 30
        assert output.duration_samples.max() <= 85

    def test_performance_1000_iterations(self):
        """Should complete 1000 iterations in <5 seconds."""
        engine = MonteCarloEngine(seed=42)
        
        # Create 100 activities
        distributions = {
            uuid4(): DistributionParams(
                distribution="triangular",
                min_value=5 + i,
                mode=10 + i,
                max_value=20 + i,
            )
            for i in range(100)
        }
        
        input = SimulationInput(
            activity_durations=distributions,
            iterations=1000,
        )
        
        output = engine.simulate(input)
        
        assert output.elapsed_seconds < 5.0
        assert output.iterations == 1000

    def test_histogram_data(self):
        """Should create valid histogram data."""
        samples = np.random.normal(100, 10, 1000)
        histogram = create_histogram_data(samples, bins=20)
        
        assert len(histogram["bin_edges"]) == 21  # bins + 1
        assert len(histogram["counts"]) == 20
        assert sum(histogram["counts"]) == 1000
        assert "p50" in histogram["percentiles"]
```

## Verification
```bash
cd api
alembic revision --autogenerate -m "add simulation tables"
alembic upgrade head
ruff check src tests --fix
mypy src --ignore-missing-imports
pytest tests/unit/test_monte_carlo.py -v
pytest --cov=src --cov-report=term-missing
```

## Git Workflow
```bash
git checkout -b feature/monte-carlo-foundation
git add .
git commit -m "feat(simulation): implement Monte Carlo engine foundation

- Add SimulationConfig and SimulationResult models
- Add MonteCarloEngine with vectorized NumPy
- Support triangular, normal, uniform, PERT distributions
- Add histogram data generation for visualization
- Performance: 1000 iterations with 100 activities in <5s

Foundation for Schedule Risk Analysis per architecture"

git push -u origin feature/monte-carlo-foundation
```

Create PR titled: "Feature: Monte Carlo Simulation Engine Foundation"
```

---

## Week 5 Completion Checklist

After completing all prompts:

- [ ] Month 1 verification passed (5.0.1)
- [ ] EV methods working (0/100, 50/50, LOE minimum)
- [ ] EV methods integrated with API
- [ ] Baseline CRUD working
- [ ] Baseline comparison working
- [ ] Scenario model created
- [ ] Scenario CRUD endpoints working
- [ ] Monte Carlo engine created
- [ ] Monte Carlo tests passing
- [ ] Test coverage maintained at 80%+
- [ ] All PRs merged to main
- [ ] Documentation updated

## Running All Week 5 Tests

```bash
cd api

# Full verification ladder
ruff check src tests --fix
ruff format src tests
mypy src --ignore-missing-imports

# All tests with coverage
pytest -v --cov=src --cov-report=term-missing --cov-fail-under=80

# Monte Carlo performance test
pytest tests/unit/test_monte_carlo.py::TestMonteCarloEngine::test_performance_1000_iterations -v
```

---

## Week 5 Success Criteria

| Criterion | Target | Notes |
|-----------|--------|-------|
| EV methods (3+) | ✅ Required | 0/100, 50/50, LOE minimum |
| Baseline CRUD | ✅ Required | Create, list, get, approve |
| Baseline comparison | ✅ Required | Schedule and cost variances |
| Scenario foundation | ✅ Required | Model and basic CRUD |
| Monte Carlo foundation | ✅ Required | Engine with <5s for 1000 iter |
| Test coverage | ≥80% | Maintain from Month 1 |

---

## Week 6 Preview

After Week 5 completion, Week 6 focuses on:
- Complete Monte Carlo integration with CPM
- Scenario simulation and comparison
- SPI/CPI validation against reference data
- Enhanced S-curve visualization

---

*Document Version: 1.0*
*Generated: January 2026*
*Month 2 Week 1: EVMS Integration*
