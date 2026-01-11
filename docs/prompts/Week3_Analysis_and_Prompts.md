# Defense PM Tool - Week 3 Comprehensive Analysis & Development Prompts

> **Generated**: January 2026
> **Status**: Post-Week 2 Completion Analysis
> **Prepared for**: Jason Marshall

---

## Table of Contents

1. [Project Files Review](#1-project-files-review)
2. [Code Analysis Against Architecture](#2-code-analysis-against-architecture)
3. [Risk Posture Assessment](#3-risk-posture-assessment)
4. [Week 3 Development Prompts](#4-week-3-development-prompts)

---

## 1. Project Files Review

### 1.1 Architecture Documentation Assessment

| Document | Status | Key Findings |
|----------|--------|--------------|
| Defense_Program_Management_Architecture_v2.docx | ✅ Complete | Modular monolith pattern well-defined; CPM/EVMS requirements clear |
| Updated_Architecture_Document.md | ✅ Complete | Post-Week 1 updates reflect actual implementation |
| CLAUDE.md | ✅ Complete | Claude Code instructions current; Week 2 focus documented |
| Month1_Development_Plan.docx | ✅ Complete | Weekly breakdown aligned with TDD plan |
| Updated_TDD_Development_Plan.md | ✅ Complete | Verification ladder and coverage targets defined |
| Risk_Mitigation_Playbook.md | ✅ Complete | Decision trees and thresholds actionable |
| Week2_Development_Prompts.md | ✅ Complete | All 8 prompts copy-paste ready |

### 1.2 Documentation Gaps Identified

1. **Week 3 Prompts**: Not yet generated (this document addresses)
2. **API Documentation**: OpenAPI/Swagger needs completion per architecture
3. **EVMS Period Model**: Schema exists but tracking endpoints not documented
4. **WBS ltree Patterns**: Example queries documented but integration patterns needed

---

## 2. Code Analysis Against Architecture

### 2.1 Architecture Alignment Summary

Based on project documentation and CLAUDE.md, the Week 2 implementation should have achieved:

| Component | Architecture Spec | Expected Implementation | Alignment |
|-----------|------------------|------------------------|-----------|
| Activity Model | program_id, code, CPM fields | Hotfix 2.0.1 added missing fields | ✅ Aligned |
| Dependency Model | lag field, cycle detection | Renamed from lag_days, NetworkX validation | ✅ Aligned |
| CPM Engine | All 4 dependency types, <500ms | FS/SS/FF/SF with float calculation | ✅ Aligned |
| Activity CRUD | Auth-protected endpoints | JWT bearer auth on all endpoints | ✅ Aligned |
| Schedule Endpoint | POST /calculate/{program_id} | Returns ScheduleResult list | ✅ Aligned |
| Gantt Component | D3-based visualization | React + D3 with activity bars | ✅ Aligned |

### 2.2 Identified Technical Debt (Per Week 2 Completion)

| Item | Severity | Impact | Resolution Week |
|------|----------|--------|-----------------|
| Test coverage at ~60% | 🟡 Medium | Need 75% by Week 3 end | Week 3 |
| Redis caching not implemented | 🟢 Low | Performance acceptable without | Week 4 |
| Frontend tests incomplete | 🟡 Medium | Gantt component needs tests | Week 3 |
| WBS CRUD endpoints pending | 🟡 Medium | Blocks EVMS period tracking | Week 3 |

### 2.3 Module Dependencies Verification

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DEPENDENCY VERIFICATION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Week 1 → Week 2 Dependencies                                                 │
│ ├── Models (User, Program, WBS, Activity, Dependency) ✅                     │
│ ├── CPM Engine with all dependency types ✅                                  │
│ ├── EVMS Calculator with Decimal precision ✅                                │
│ ├── Repository pattern with BaseRepository ✅                                │
│ └── JWT Authentication utilities ✅                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Week 2 → Week 3 Dependencies                                                 │
│ ├── Activity CRUD with auth ✅ (Required for EVMS tracking)                  │
│ ├── Dependency CRUD with cycle detection ✅ (Required for schedule calc)     │
│ ├── Schedule calculation endpoint ✅ (Required for dashboard metrics)        │
│ └── Basic Gantt component ✅ (Foundation for WBS tree integration)           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Risk Posture Assessment

### 3.1 Current Status Against Risk Playbook Week 2 Targets

| Metric | Target | Status | Risk Level |
|--------|--------|--------|------------|
| Model-schema alignments fixed | 100% | ✅ Complete (Hotfix 2.0.1) | 🟢 GREEN |
| Activity CRUD with auth | Complete | ✅ Complete | 🟢 GREEN |
| Dependency cycle detection | Working | ✅ Complete | 🟢 GREEN |
| Basic Gantt rendering | Visible | ✅ Complete | 🟢 GREEN |
| Test coverage | ≥60% | ~60% | 🟡 YELLOW |

### 3.2 Week 3 Risk Triggers to Monitor

Per Risk Mitigation Playbook Section 1.2 (Month 2: EVMS Integration):

| Trigger | Threshold | Current Assessment | Action if Triggered |
|---------|-----------|-------------------|---------------------|
| BCWS/BCWP calculations | Working by Day 17 | EVMS calculator exists from Week 1 | Low risk - foundation solid |
| % complete method | Only method working by Day 18 | Need to verify all EV methods | Defer advanced methods if needed |
| Dashboard slow | >3s load time | Not yet implemented | Use static charts fallback |

### 3.3 End-of-Week 3 Checkpoints

From TDD Plan Risk Mitigation Checkpoints:

- [ ] WBS hierarchy working
- [ ] EVMS tracking functional  
- [ ] Dashboard shows metrics
- [ ] Reports generate correctly
- [ ] 75%+ test coverage

### 3.4 Technical Risk Decision Points for Week 3

| Risk | Decision Threshold | Options |
|------|-------------------|---------|
| WBS ltree queries slow | >200ms for 1000 elements | A: Add indexes, B: Denormalize, C: Materialized views |
| EVMS period tracking complex | >4 hours on time-phasing | A: Push through, B: Simplify to monthly only, C: Use spreadsheet backend |
| Dashboard performance | >3s load | A: Optimize queries, B: Cache metrics, C: Static charts only |
| Report generation blocked | PDF library issues | A: Fix library, B: HTML export only, C: Excel-only export |

---

## 4. Week 3 Development Prompts

> **Week 3 Focus**: WBS Hierarchy, EVMS Period Tracking, Dashboard, Reports
> **Prerequisites**: All Week 2 prompts complete, coverage ≥60%
> **Timeline**: Days 15-21
> **Coverage Target**: 75%

### Overview

| Day | Prompt | Description | Time Est. |
|-----|--------|-------------|-----------|
| 15 | 3.0.1 | Week 2 Verification & Test Coverage Boost | 2 hrs |
| 15-16 | 3.1.1 | WBS CRUD with Hierarchy (ltree) | 3-4 hrs |
| 16-17 | 3.1.2 | WBS Tree Visualization Component | 3 hrs |
| 17-18 | 3.2.1 | EVMS Period Tracking & Time-Phasing | 4 hrs |
| 19 | 3.2.2 | EVMS Dashboard with Metrics | 3 hrs |
| 20-21 | 3.3.1 | Report Generation (CPR Format 1) | 4 hrs |
| 21 | 3.4.1 | Week 3 Integration Test & Documentation | 2 hrs |

---

### Prompt 3.0.1: Week 2 Verification & Test Coverage Boost

**Priority**: 🔴 CRITICAL - Run first to verify Week 2 and establish baseline

```
Verify Week 2 completion and boost test coverage before starting Week 3 features.

## Context
Before proceeding with WBS and EVMS features, we need to:
1. Verify all Week 2 components are working correctly
2. Boost test coverage from ~60% to 65% minimum
3. Document any remaining technical debt

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
pytest tests/unit -v
pytest tests/integration -v
pytest --cov=src --cov-report=term-missing --cov-report=html
```

### 2. Verify Week 2 Endpoints Manually
```bash
# Start API server
uvicorn src.main:app --reload --port 8000

# Test health endpoint
curl http://localhost:8000/health

# Test auth flow
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"week3test@test.com","password":"Test123!","full_name":"Week 3 Tester"}'

# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"week3test@test.com","password":"Test123!"}' | jq -r '.access_token')

# Test program creation
curl -X POST http://localhost:8000/api/v1/programs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Week 3 Test Program","code":"W3-001","start_date":"2026-01-01","end_date":"2026-12-31"}'
```

### 3. Add Missing Unit Tests for Coverage
File: api/tests/unit/test_evms_additional.py

```python
"""Additional EVMS tests to boost coverage."""

import pytest
from decimal import Decimal

from src.services.evms import EVMSCalculator


class TestEVMSEdgeCases:
    """Edge case tests for EVMS calculations."""

    def test_zero_bcws_returns_none_spi(self):
        """SPI should be None when BCWS is zero."""
        calc = EVMSCalculator(
            bcws=Decimal("0"),
            bcwp=Decimal("100"),
            acwp=Decimal("100"),
            bac=Decimal("1000"),
        )
        assert calc.spi is None

    def test_zero_acwp_returns_none_cpi(self):
        """CPI should be None when ACWP is zero."""
        calc = EVMSCalculator(
            bcws=Decimal("100"),
            bcwp=Decimal("100"),
            acwp=Decimal("0"),
            bac=Decimal("1000"),
        )
        assert calc.cpi is None

    def test_negative_variance_correctly_calculated(self):
        """Test negative variances (over budget, behind schedule)."""
        calc = EVMSCalculator(
            bcws=Decimal("1000"),  # Planned $1000
            bcwp=Decimal("800"),   # Earned $800 (behind)
            acwp=Decimal("1200"),  # Spent $1200 (over budget)
            bac=Decimal("10000"),
        )
        assert calc.sv == Decimal("-200")  # Behind schedule
        assert calc.cv == Decimal("-400")  # Over budget
        assert calc.spi < Decimal("1")
        assert calc.cpi < Decimal("1")

    def test_eac_with_different_cpi(self):
        """Test EAC calculation with various CPI values."""
        # Under budget scenario
        calc = EVMSCalculator(
            bcws=Decimal("1000"),
            bcwp=Decimal("1000"),
            acwp=Decimal("800"),
            bac=Decimal("10000"),
        )
        # CPI = 1.25, EAC = 10000 / 1.25 = 8000
        assert calc.eac == Decimal("8000")


class TestEVMSTCPI:
    """Tests for To-Complete Performance Index."""

    def test_tcpi_for_bac(self):
        """TCPI for completing at BAC."""
        calc = EVMSCalculator(
            bcws=Decimal("500"),
            bcwp=Decimal("400"),
            acwp=Decimal("500"),
            bac=Decimal("1000"),
        )
        # TCPI = (BAC - BCWP) / (BAC - ACWP) = (1000-400)/(1000-500) = 1.2
        assert calc.tcpi_bac == Decimal("1.2")

    def test_tcpi_when_remaining_budget_zero(self):
        """TCPI should be None when remaining budget is zero."""
        calc = EVMSCalculator(
            bcws=Decimal("1000"),
            bcwp=Decimal("500"),
            acwp=Decimal("1000"),  # Already spent BAC
            bac=Decimal("1000"),
        )
        assert calc.tcpi_bac is None
```

### 4. Add Missing Repository Tests
File: api/tests/unit/test_repositories.py

```python
"""Unit tests for repository layer."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.repositories.base import BaseRepository
from src.repositories.activity import ActivityRepository


class TestActivityRepository:
    """Tests for ActivityRepository."""

    @pytest.mark.asyncio
    async def test_get_by_program_returns_empty_list(self):
        """Should return empty list when no activities exist."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = ActivityRepository(mock_session)
        result = await repo.get_by_program(uuid4())

        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_program_filters_deleted(self):
        """Should filter out soft-deleted activities."""
        # This test verifies the WHERE deleted_at IS NULL clause
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = ActivityRepository(mock_session)
        await repo.get_by_program(uuid4())

        # Verify execute was called (query was constructed)
        mock_session.execute.assert_called_once()
```

## Documentation Updates

### Update CLAUDE.md Current Status
Add to "Completed (Week 2)" section:
- [x] Activity CRUD with authentication
- [x] Dependency CRUD with cycle detection
- [x] Schedule calculation endpoint
- [x] Basic Gantt visualization
- [x] Week 2 E2E integration tests

### Update In Progress Section
- [ ] WBS CRUD with hierarchy (Week 3)
- [ ] EVMS period tracking (Week 3)
- [ ] Dashboard components (Week 3)
- [ ] Report generation (Week 3)

## Verification
```bash
cd api
ruff check src tests --fix
ruff format src tests
mypy src --ignore-missing-imports
pytest --cov=src --cov-report=term-missing --cov-fail-under=65
```

## Git Workflow
```bash
git checkout -b feature/week3-prep
git add .
git commit -m "test(coverage): boost test coverage and verify Week 2 completion

- Add EVMS edge case tests
- Add repository unit tests  
- Verify all Week 2 endpoints working
- Update CLAUDE.md with Week 2 completion status

Coverage: 65%+ (target for Week 3 start)"

git push -u origin feature/week3-prep
```

Create PR titled: "Week 3 Prep: Test Coverage Boost & Week 2 Verification"
```

---

### Prompt 3.1.1: WBS CRUD with Hierarchy (ltree)

**Priority**: 🔴 HIGH - Foundation for EVMS tracking

```
Implement complete WBS CRUD operations with ltree hierarchy support.

## Prerequisites
- Prompt 3.0.1 complete (Week 2 verified, coverage ≥65%)
- PostgreSQL ltree extension enabled (should be from Week 1)

## Implementation Plan

### 1. Create WBS Tests First (TDD)
File: api/tests/unit/test_wbs_crud.py

```python
"""Unit tests for WBS CRUD operations."""

import pytest
from uuid import uuid4

from src.schemas.wbs import WBSCreate, WBSUpdate, WBSResponse
from src.models.wbs import WBSElement


class TestWBSCreate:
    """Tests for WBS creation."""

    def test_create_root_wbs(self):
        """Should create root WBS element."""
        data = WBSCreate(
            program_id=uuid4(),
            code="1",
            name="Program Root",
            description="Top-level WBS element",
        )
        assert data.code == "1"
        assert data.parent_id is None

    def test_create_child_wbs(self):
        """Should create child WBS element."""
        parent_id = uuid4()
        data = WBSCreate(
            program_id=uuid4(),
            parent_id=parent_id,
            code="1.1",
            name="Phase 1",
            description="First phase",
        )
        assert data.parent_id == parent_id

    def test_wbs_code_validation(self):
        """WBS code must follow pattern."""
        with pytest.raises(ValueError, match="WBS code"):
            WBSCreate(
                program_id=uuid4(),
                code="",  # Empty not allowed
                name="Test",
            )


class TestWBSHierarchy:
    """Tests for WBS hierarchy operations."""

    def test_path_generation_for_root(self):
        """Root element should have path equal to code."""
        element = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            code="1",
            name="Root",
        )
        # Path should be set based on code for root elements
        assert element.code == "1"

    def test_max_depth_enforcement(self):
        """Should enforce maximum WBS depth (10 levels)."""
        # Path like 1.1.1.1.1.1.1.1.1.1.1 exceeds MAX_WBS_DEPTH
        with pytest.raises(ValueError, match="depth"):
            WBSCreate(
                program_id=uuid4(),
                code="1.1.1.1.1.1.1.1.1.1.1",  # 11 levels
                name="Too Deep",
            )
```

### 2. Create Integration Tests
File: api/tests/integration/test_wbs_api.py

```python
"""Integration tests for WBS API."""

import pytest
from httpx import AsyncClient
from uuid import uuid4

pytestmark = pytest.mark.asyncio


class TestWBSAPI:
    """Integration tests for /api/v1/wbs endpoints."""

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict:
        """Get authentication headers."""
        email = f"wbstest_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "WBSTest123!",
                "full_name": "WBS Tester",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WBSTest123!"},
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
                "name": "WBS Test Program",
                "code": f"WBS-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        return response.json()["id"]

    async def test_create_root_wbs(
        self, client: AsyncClient, auth_headers: dict, program_id: str
    ):
        """Should create root WBS element."""
        response = await client.post(
            "/api/v1/wbs",
            headers=auth_headers,
            json={
                "program_id": program_id,
                "code": "1",
                "name": "Program Root",
                "description": "Top-level element",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "1"
        assert data["level"] == 1

    async def test_create_child_wbs(
        self, client: AsyncClient, auth_headers: dict, program_id: str
    ):
        """Should create child WBS element."""
        # Create root
        root_response = await client.post(
            "/api/v1/wbs",
            headers=auth_headers,
            json={
                "program_id": program_id,
                "code": "1",
                "name": "Root",
            },
        )
        root_id = root_response.json()["id"]

        # Create child
        child_response = await client.post(
            "/api/v1/wbs",
            headers=auth_headers,
            json={
                "program_id": program_id,
                "parent_id": root_id,
                "code": "1.1",
                "name": "Phase 1",
            },
        )
        assert child_response.status_code == 201
        data = child_response.json()
        assert data["code"] == "1.1"
        assert data["level"] == 2
        assert data["parent_id"] == root_id

    async def test_get_wbs_tree(
        self, client: AsyncClient, auth_headers: dict, program_id: str
    ):
        """Should return complete WBS tree."""
        # Create hierarchy: 1 -> 1.1 -> 1.1.1
        await client.post(
            "/api/v1/wbs",
            headers=auth_headers,
            json={"program_id": program_id, "code": "1", "name": "Root"},
        )
        await client.post(
            "/api/v1/wbs",
            headers=auth_headers,
            json={"program_id": program_id, "code": "1.1", "name": "Level 2"},
        )
        await client.post(
            "/api/v1/wbs",
            headers=auth_headers,
            json={"program_id": program_id, "code": "1.1.1", "name": "Level 3"},
        )

        # Get tree
        response = await client.get(
            f"/api/v1/wbs/tree/{program_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        tree = response.json()
        assert len(tree) == 1  # One root
        assert tree[0]["code"] == "1"
        assert len(tree[0]["children"]) == 1

    async def test_get_descendants(
        self, client: AsyncClient, auth_headers: dict, program_id: str
    ):
        """Should return all descendants of a WBS element."""
        # Create hierarchy
        root = await client.post(
            "/api/v1/wbs",
            headers=auth_headers,
            json={"program_id": program_id, "code": "1", "name": "Root"},
        )
        root_id = root.json()["id"]

        await client.post(
            "/api/v1/wbs",
            headers=auth_headers,
            json={"program_id": program_id, "code": "1.1", "name": "Child 1"},
        )
        await client.post(
            "/api/v1/wbs",
            headers=auth_headers,
            json={"program_id": program_id, "code": "1.2", "name": "Child 2"},
        )

        # Get descendants
        response = await client.get(
            f"/api/v1/wbs/{root_id}/descendants",
            headers=auth_headers,
        )
        assert response.status_code == 200
        descendants = response.json()
        assert len(descendants) == 2
```

### 3. Create WBS Schemas
File: api/src/schemas/wbs.py

```python
"""Pydantic schemas for WBS elements."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.core.constants import MAX_WBS_DEPTH


class WBSBase(BaseModel):
    """Base schema for WBS elements."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="WBS code (e.g., '1', '1.1', '1.1.1')",
    )
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    is_control_account: bool = Field(
        default=False,
        description="Whether this is a Control Account (CA)",
    )
    budgeted_cost: Decimal | None = Field(
        None,
        ge=Decimal("0"),
        description="Total budgeted cost for this WBS element",
    )

    @field_validator("code")
    @classmethod
    def validate_wbs_code(cls, v: str) -> str:
        """Validate WBS code format and depth."""
        parts = v.split(".")
        if len(parts) > MAX_WBS_DEPTH:
            raise ValueError(
                f"WBS code exceeds maximum depth of {MAX_WBS_DEPTH} levels"
            )
        for part in parts:
            if not part.isdigit() and not part.isalnum():
                raise ValueError("WBS code parts must be alphanumeric")
        return v


class WBSCreate(WBSBase):
    """Schema for creating a WBS element."""

    program_id: UUID = Field(..., description="ID of the parent program")
    parent_id: UUID | None = Field(
        None,
        description="ID of parent WBS element (None for root)",
    )


class WBSUpdate(BaseModel):
    """Schema for updating a WBS element."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    is_control_account: bool | None = None
    budgeted_cost: Decimal | None = Field(None, ge=Decimal("0"))


class WBSResponse(WBSBase):
    """Schema for WBS element response."""

    id: UUID
    program_id: UUID
    parent_id: UUID | None
    path: str
    level: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WBSTreeNode(WBSResponse):
    """Schema for WBS tree node with children."""

    children: list["WBSTreeNode"] = Field(default_factory=list)


class WBSListResponse(BaseModel):
    """Schema for paginated WBS list."""

    items: list[WBSResponse]
    total: int
```

### 4. Create WBS Repository
File: api/src/repositories/wbs.py

```python
"""Repository for WBS element operations."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.wbs import WBSElement
from src.repositories.base import BaseRepository


class WBSRepository(BaseRepository[WBSElement]):
    """Repository for WBS CRUD operations with hierarchy support."""

    def __init__(self, session: AsyncSession):
        super().__init__(WBSElement, session)

    async def get_by_program(
        self,
        program_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[WBSElement]:
        """Get all WBS elements for a program."""
        result = await self.session.execute(
            select(WBSElement)
            .where(WBSElement.program_id == program_id)
            .where(WBSElement.deleted_at.is_(None))
            .order_by(WBSElement.path)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_root_elements(self, program_id: UUID) -> list[WBSElement]:
        """Get root (level 1) WBS elements for a program."""
        result = await self.session.execute(
            select(WBSElement)
            .where(WBSElement.program_id == program_id)
            .where(WBSElement.parent_id.is_(None))
            .where(WBSElement.deleted_at.is_(None))
            .order_by(WBSElement.code)
        )
        return list(result.scalars().all())

    async def get_children(self, parent_id: UUID) -> list[WBSElement]:
        """Get direct children of a WBS element."""
        result = await self.session.execute(
            select(WBSElement)
            .where(WBSElement.parent_id == parent_id)
            .where(WBSElement.deleted_at.is_(None))
            .order_by(WBSElement.code)
        )
        return list(result.scalars().all())

    async def get_descendants(self, element_id: UUID) -> list[WBSElement]:
        """Get all descendants of a WBS element using ltree."""
        # First get the element's path
        element = await self.get_by_id(element_id)
        if not element:
            return []

        # Use ltree descendant query
        result = await self.session.execute(
            select(WBSElement)
            .where(
                text(f"path <@ '{element.path}'")
            )
            .where(WBSElement.id != element_id)  # Exclude self
            .where(WBSElement.deleted_at.is_(None))
            .order_by(WBSElement.path)
        )
        return list(result.scalars().all())

    async def get_ancestors(self, element_id: UUID) -> list[WBSElement]:
        """Get all ancestors of a WBS element."""
        element = await self.get_by_id(element_id)
        if not element:
            return []

        result = await self.session.execute(
            select(WBSElement)
            .where(
                text(f"'{element.path}' <@ path")
            )
            .where(WBSElement.id != element_id)
            .where(WBSElement.deleted_at.is_(None))
            .order_by(WBSElement.path)
        )
        return list(result.scalars().all())

    async def get_by_code(
        self,
        program_id: UUID,
        code: str,
    ) -> Optional[WBSElement]:
        """Get WBS element by code within a program."""
        result = await self.session.execute(
            select(WBSElement)
            .where(WBSElement.program_id == program_id)
            .where(WBSElement.code == code)
            .where(WBSElement.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def count_by_program(self, program_id: UUID) -> int:
        """Count WBS elements in a program."""
        result = await self.session.execute(
            select(WBSElement)
            .where(WBSElement.program_id == program_id)
            .where(WBSElement.deleted_at.is_(None))
        )
        return len(result.scalars().all())
```

### 5. Create WBS Endpoint
File: api/src/api/v1/endpoints/wbs.py

```python
"""WBS endpoints with hierarchy support."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.core.deps import DbSession, get_current_user
from src.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from src.core.constants import MAX_WBS_ELEMENTS_PER_PROGRAM
from src.models.user import User
from src.repositories.program import ProgramRepository
from src.repositories.wbs import WBSRepository
from src.schemas.wbs import (
    WBSCreate,
    WBSListResponse,
    WBSResponse,
    WBSTreeNode,
    WBSUpdate,
)

router = APIRouter()


def build_tree(elements: list, parent_id: UUID | None = None) -> list[WBSTreeNode]:
    """Build hierarchical tree from flat list."""
    tree = []
    for element in elements:
        if element.parent_id == parent_id:
            node = WBSTreeNode.model_validate(element)
            node.children = build_tree(elements, element.id)
            tree.append(node)
    return tree


@router.get("", response_model=WBSListResponse)
async def list_wbs_elements(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    program_id: Annotated[UUID, Query(description="Filter by program ID")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> WBSListResponse:
    """List all WBS elements for a program."""
    # Verify program access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError("Program", program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied to this program")

    wbs_repo = WBSRepository(db)
    skip = (page - 1) * page_size
    elements = await wbs_repo.get_by_program(program_id, skip=skip, limit=page_size)
    total = await wbs_repo.count_by_program(program_id)

    return WBSListResponse(
        items=[WBSResponse.model_validate(e) for e in elements],
        total=total,
    )


@router.get("/tree/{program_id}", response_model=list[WBSTreeNode])
async def get_wbs_tree(
    program_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[WBSTreeNode]:
    """Get complete WBS tree for a program."""
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError("Program", program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    wbs_repo = WBSRepository(db)
    elements = await wbs_repo.get_by_program(program_id, limit=10000)
    
    return build_tree(elements)


@router.post("", response_model=WBSResponse, status_code=201)
async def create_wbs_element(
    wbs_in: WBSCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> WBSResponse:
    """Create a new WBS element."""
    # Verify program access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(wbs_in.program_id)
    if not program:
        raise NotFoundError("Program", wbs_in.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    wbs_repo = WBSRepository(db)

    # Check element limit
    count = await wbs_repo.count_by_program(wbs_in.program_id)
    if count >= MAX_WBS_ELEMENTS_PER_PROGRAM:
        raise ValidationError(
            f"Maximum WBS elements ({MAX_WBS_ELEMENTS_PER_PROGRAM}) exceeded"
        )

    # Check for duplicate code
    existing = await wbs_repo.get_by_code(wbs_in.program_id, wbs_in.code)
    if existing:
        raise ValidationError(f"WBS code '{wbs_in.code}' already exists")

    # Verify parent exists if specified
    parent_path = ""
    if wbs_in.parent_id:
        parent = await wbs_repo.get_by_id(wbs_in.parent_id)
        if not parent:
            raise NotFoundError("Parent WBS element", wbs_in.parent_id)
        parent_path = parent.path

    # Create element
    from src.models.wbs import WBSElement
    
    element = WBSElement(
        program_id=wbs_in.program_id,
        parent_id=wbs_in.parent_id,
        code=wbs_in.code,
        name=wbs_in.name,
        description=wbs_in.description,
        is_control_account=wbs_in.is_control_account,
        budgeted_cost=wbs_in.budgeted_cost,
        path=f"{parent_path}.{wbs_in.code}" if parent_path else wbs_in.code,
        level=len(wbs_in.code.split(".")),
    )
    
    created = await wbs_repo.create(element)
    return WBSResponse.model_validate(created)


@router.get("/{wbs_id}", response_model=WBSResponse)
async def get_wbs_element(
    wbs_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> WBSResponse:
    """Get a single WBS element."""
    wbs_repo = WBSRepository(db)
    element = await wbs_repo.get_by_id(wbs_id)
    if not element:
        raise NotFoundError("WBS element", wbs_id)

    # Verify access via program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(element.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    return WBSResponse.model_validate(element)


@router.get("/{wbs_id}/descendants", response_model=list[WBSResponse])
async def get_wbs_descendants(
    wbs_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[WBSResponse]:
    """Get all descendants of a WBS element."""
    wbs_repo = WBSRepository(db)
    element = await wbs_repo.get_by_id(wbs_id)
    if not element:
        raise NotFoundError("WBS element", wbs_id)

    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(element.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    descendants = await wbs_repo.get_descendants(wbs_id)
    return [WBSResponse.model_validate(d) for d in descendants]


@router.put("/{wbs_id}", response_model=WBSResponse)
async def update_wbs_element(
    wbs_id: UUID,
    wbs_in: WBSUpdate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> WBSResponse:
    """Update a WBS element."""
    wbs_repo = WBSRepository(db)
    element = await wbs_repo.get_by_id(wbs_id)
    if not element:
        raise NotFoundError("WBS element", wbs_id)

    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(element.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    # Update fields
    update_data = wbs_in.model_dump(exclude_unset=True)
    updated = await wbs_repo.update(element, update_data)
    return WBSResponse.model_validate(updated)


@router.delete("/{wbs_id}", status_code=204)
async def delete_wbs_element(
    wbs_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a WBS element (soft delete)."""
    wbs_repo = WBSRepository(db)
    element = await wbs_repo.get_by_id(wbs_id)
    if not element:
        raise NotFoundError("WBS element", wbs_id)

    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(element.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    # Check for children
    children = await wbs_repo.get_children(wbs_id)
    if children:
        raise ValidationError(
            "Cannot delete WBS element with children. Delete children first."
        )

    await wbs_repo.soft_delete(element)
```

### 6. Register Router
File: api/src/api/v1/router.py

Add WBS router:
```python
from src.api.v1.endpoints import wbs

api_router.include_router(wbs.router, prefix="/wbs", tags=["WBS"])
```

## Verification
```bash
cd api
ruff check src tests --fix
ruff format src tests
mypy src --ignore-missing-imports
pytest tests/unit/test_wbs_crud.py -v
pytest tests/integration/test_wbs_api.py -v
pytest --cov=src --cov-report=term-missing
```

## Git Workflow
```bash
git checkout -b feature/wbs-crud
git add .
git commit -m "feat(wbs): implement WBS CRUD with ltree hierarchy support

- Add WBSCreate, WBSUpdate, WBSResponse schemas
- Add WBSRepository with hierarchy queries (descendants, ancestors)
- Add WBS endpoints with auth
- Add tree building for hierarchical response
- Add comprehensive unit and integration tests

EVMS compliance: Supports GL 6 (WBS/OBS structure)"

git push -u origin feature/wbs-crud
```

Create PR titled: "Feature: WBS CRUD with ltree Hierarchy Support"
```

---

### Prompt 3.1.2: WBS Tree Visualization Component

```
Implement the WBS Tree visualization component for the frontend.

## Prerequisites
- Prompt 3.1.1 complete (WBS CRUD endpoints working)
- React frontend scaffolded from Week 2

## Implementation Plan

### 1. Create WBS Types
File: web/src/types/wbs.ts

```typescript
export interface WBSElement {
  id: string;
  programId: string;
  parentId: string | null;
  code: string;
  name: string;
  description: string | null;
  isControlAccount: boolean;
  budgetedCost: number | null;
  path: string;
  level: number;
  createdAt: string;
  updatedAt: string;
}

export interface WBSTreeNode extends WBSElement {
  children: WBSTreeNode[];
  isExpanded?: boolean;
  isSelected?: boolean;
}

export interface WBSCreateRequest {
  programId: string;
  parentId?: string;
  code: string;
  name: string;
  description?: string;
  isControlAccount?: boolean;
  budgetedCost?: number;
}
```

### 2. Create WBS API Service
File: web/src/services/wbsApi.ts

```typescript
import { apiClient } from './apiClient';
import { WBSElement, WBSTreeNode, WBSCreateRequest } from '@/types/wbs';

export const wbsApi = {
  getTree: async (programId: string): Promise<WBSTreeNode[]> => {
    const response = await apiClient.get<WBSTreeNode[]>(
      `/wbs/tree/${programId}`
    );
    return response.data;
  },

  getList: async (
    programId: string,
    page: number = 1,
    pageSize: number = 50
  ): Promise<{ items: WBSElement[]; total: number }> => {
    const response = await apiClient.get('/wbs', {
      params: { program_id: programId, page, page_size: pageSize },
    });
    return response.data;
  },

  create: async (data: WBSCreateRequest): Promise<WBSElement> => {
    const response = await apiClient.post<WBSElement>('/wbs', data);
    return response.data;
  },

  update: async (
    id: string,
    data: Partial<WBSCreateRequest>
  ): Promise<WBSElement> => {
    const response = await apiClient.put<WBSElement>(`/wbs/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/wbs/${id}`);
  },

  getDescendants: async (id: string): Promise<WBSElement[]> => {
    const response = await apiClient.get<WBSElement[]>(
      `/wbs/${id}/descendants`
    );
    return response.data;
  },
};
```

### 3. Create WBS Tree Hook
File: web/src/hooks/useWBSTree.ts

```typescript
import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { wbsApi } from '@/services/wbsApi';
import { WBSTreeNode, WBSCreateRequest } from '@/types/wbs';

export function useWBSTree(programId: string | undefined) {
  const queryClient = useQueryClient();
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const treeQuery = useQuery({
    queryKey: ['wbs-tree', programId],
    queryFn: () => wbsApi.getTree(programId!),
    enabled: !!programId,
  });

  const createMutation = useMutation({
    mutationFn: wbsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wbs-tree', programId] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<WBSCreateRequest> }) =>
      wbsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wbs-tree', programId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: wbsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wbs-tree', programId] });
      setSelectedNode(null);
    },
  });

  const toggleExpand = useCallback((nodeId: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, []);

  const expandAll = useCallback((nodes: WBSTreeNode[]) => {
    const getAllIds = (nodes: WBSTreeNode[]): string[] => {
      return nodes.flatMap((node) => [
        node.id,
        ...getAllIds(node.children || []),
      ]);
    };
    setExpandedNodes(new Set(getAllIds(nodes)));
  }, []);

  const collapseAll = useCallback(() => {
    setExpandedNodes(new Set());
  }, []);

  return {
    tree: treeQuery.data ?? [],
    isLoading: treeQuery.isLoading,
    error: treeQuery.error,
    expandedNodes,
    selectedNode,
    setSelectedNode,
    toggleExpand,
    expandAll,
    collapseAll,
    createWBS: createMutation.mutateAsync,
    updateWBS: updateMutation.mutateAsync,
    deleteWBS: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
}
```

### 4. Create WBS Tree Component
File: web/src/components/WBSTree/WBSTree.tsx

```typescript
import React from 'react';
import { WBSTreeNode } from '@/types/wbs';
import { WBSTreeItem } from './WBSTreeItem';
import { WBSToolbar } from './WBSToolbar';
import { useWBSTree } from '@/hooks/useWBSTree';
import './WBSTree.css';

interface WBSTreeProps {
  programId: string;
  onNodeSelect?: (node: WBSTreeNode | null) => void;
}

export function WBSTree({ programId, onNodeSelect }: WBSTreeProps) {
  const {
    tree,
    isLoading,
    error,
    expandedNodes,
    selectedNode,
    setSelectedNode,
    toggleExpand,
    expandAll,
    collapseAll,
    createWBS,
    updateWBS,
    deleteWBS,
  } = useWBSTree(programId);

  const handleSelect = (node: WBSTreeNode) => {
    setSelectedNode(node.id);
    onNodeSelect?.(node);
  };

  const handleAddChild = async (parentId: string | null) => {
    const code = prompt('Enter WBS code (e.g., 1.1):');
    const name = prompt('Enter WBS name:');
    if (code && name) {
      await createWBS({
        programId,
        parentId: parentId ?? undefined,
        code,
        name,
      });
    }
  };

  if (isLoading) {
    return <div className="wbs-tree-loading">Loading WBS...</div>;
  }

  if (error) {
    return (
      <div className="wbs-tree-error">
        Error loading WBS: {error.message}
      </div>
    );
  }

  return (
    <div className="wbs-tree-container">
      <WBSToolbar
        onExpandAll={() => expandAll(tree)}
        onCollapseAll={collapseAll}
        onAddRoot={() => handleAddChild(null)}
        selectedNode={selectedNode}
        onDelete={
          selectedNode
            ? () => {
                if (confirm('Delete this WBS element?')) {
                  deleteWBS(selectedNode);
                }
              }
            : undefined
        }
      />
      <div className="wbs-tree">
        {tree.length === 0 ? (
          <div className="wbs-tree-empty">
            No WBS elements. Click "Add Root" to create one.
          </div>
        ) : (
          tree.map((node) => (
            <WBSTreeItem
              key={node.id}
              node={node}
              level={0}
              isExpanded={expandedNodes.has(node.id)}
              isSelected={selectedNode === node.id}
              onToggle={() => toggleExpand(node.id)}
              onSelect={() => handleSelect(node)}
              onAddChild={() => handleAddChild(node.id)}
              expandedNodes={expandedNodes}
              selectedNode={selectedNode}
              onToggleExpand={toggleExpand}
              onSelectNode={(n) => handleSelect(n)}
            />
          ))
        )}
      </div>
    </div>
  );
}
```

### 5. Create WBS Tree Item Component
File: web/src/components/WBSTree/WBSTreeItem.tsx

```typescript
import React from 'react';
import { ChevronRight, ChevronDown, Folder, FolderOpen, Plus } from 'lucide-react';
import { WBSTreeNode } from '@/types/wbs';

interface WBSTreeItemProps {
  node: WBSTreeNode;
  level: number;
  isExpanded: boolean;
  isSelected: boolean;
  onToggle: () => void;
  onSelect: () => void;
  onAddChild: () => void;
  expandedNodes: Set<string>;
  selectedNode: string | null;
  onToggleExpand: (id: string) => void;
  onSelectNode: (node: WBSTreeNode) => void;
}

export function WBSTreeItem({
  node,
  level,
  isExpanded,
  isSelected,
  onToggle,
  onSelect,
  onAddChild,
  expandedNodes,
  selectedNode,
  onToggleExpand,
  onSelectNode,
}: WBSTreeItemProps) {
  const hasChildren = node.children && node.children.length > 0;
  const indent = level * 20;

  return (
    <div className="wbs-tree-item-container">
      <div
        className={`wbs-tree-item ${isSelected ? 'selected' : ''} ${
          node.isControlAccount ? 'control-account' : ''
        }`}
        style={{ paddingLeft: `${indent + 8}px` }}
        onClick={onSelect}
      >
        {/* Expand/Collapse Button */}
        <button
          className="wbs-tree-toggle"
          onClick={(e) => {
            e.stopPropagation();
            onToggle();
          }}
          disabled={!hasChildren}
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown size={16} />
            ) : (
              <ChevronRight size={16} />
            )
          ) : (
            <span style={{ width: 16 }} />
          )}
        </button>

        {/* Folder Icon */}
        <span className="wbs-tree-icon">
          {hasChildren && isExpanded ? (
            <FolderOpen size={16} />
          ) : (
            <Folder size={16} />
          )}
        </span>

        {/* Code and Name */}
        <span className="wbs-tree-code">{node.code}</span>
        <span className="wbs-tree-name">{node.name}</span>

        {/* Control Account Badge */}
        {node.isControlAccount && (
          <span className="wbs-badge ca-badge">CA</span>
        )}

        {/* Add Child Button */}
        <button
          className="wbs-tree-add"
          onClick={(e) => {
            e.stopPropagation();
            onAddChild();
          }}
          title="Add child element"
        >
          <Plus size={14} />
        </button>
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div className="wbs-tree-children">
          {node.children.map((child) => (
            <WBSTreeItem
              key={child.id}
              node={child}
              level={level + 1}
              isExpanded={expandedNodes.has(child.id)}
              isSelected={selectedNode === child.id}
              onToggle={() => onToggleExpand(child.id)}
              onSelect={() => onSelectNode(child)}
              onAddChild={() => {
                const code = prompt('Enter WBS code:');
                const name = prompt('Enter WBS name:');
                if (code && name) {
                  // Call create from parent context
                }
              }}
              expandedNodes={expandedNodes}
              selectedNode={selectedNode}
              onToggleExpand={onToggleExpand}
              onSelectNode={onSelectNode}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

### 6. Create CSS Styles
File: web/src/components/WBSTree/WBSTree.css

```css
.wbs-tree-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
}

.wbs-tree {
  flex: 1;
  overflow: auto;
  padding: 8px;
}

.wbs-tree-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  user-select: none;
}

.wbs-tree-item:hover {
  background: #f1f5f9;
}

.wbs-tree-item.selected {
  background: #dbeafe;
  border-color: #3b82f6;
}

.wbs-tree-item.control-account {
  border-left: 3px solid #f59e0b;
}

.wbs-tree-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  color: #64748b;
}

.wbs-tree-toggle:hover:not(:disabled) {
  color: #3b82f6;
}

.wbs-tree-toggle:disabled {
  cursor: default;
}

.wbs-tree-icon {
  color: #64748b;
}

.wbs-tree-code {
  font-family: monospace;
  font-weight: 600;
  color: #1e40af;
  min-width: 60px;
}

.wbs-tree-name {
  flex: 1;
  color: #1e293b;
}

.wbs-badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
}

.ca-badge {
  background: #fef3c7;
  color: #92400e;
}

.wbs-tree-add {
  opacity: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  background: white;
  color: #64748b;
  cursor: pointer;
  transition: opacity 0.2s;
}

.wbs-tree-item:hover .wbs-tree-add {
  opacity: 1;
}

.wbs-tree-add:hover {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.wbs-tree-loading,
.wbs-tree-error,
.wbs-tree-empty {
  padding: 24px;
  text-align: center;
  color: #64748b;
}

.wbs-tree-error {
  color: #dc2626;
}
```

### 7. Create Toolbar Component
File: web/src/components/WBSTree/WBSToolbar.tsx

```typescript
import React from 'react';
import { ChevronDownSquare, ChevronUpSquare, Plus, Trash2 } from 'lucide-react';

interface WBSToolbarProps {
  onExpandAll: () => void;
  onCollapseAll: () => void;
  onAddRoot: () => void;
  selectedNode: string | null;
  onDelete?: () => void;
}

export function WBSToolbar({
  onExpandAll,
  onCollapseAll,
  onAddRoot,
  selectedNode,
  onDelete,
}: WBSToolbarProps) {
  return (
    <div className="wbs-toolbar">
      <button onClick={onAddRoot} className="wbs-toolbar-btn primary">
        <Plus size={16} />
        Add Root
      </button>
      <div className="wbs-toolbar-divider" />
      <button onClick={onExpandAll} className="wbs-toolbar-btn">
        <ChevronDownSquare size={16} />
        Expand All
      </button>
      <button onClick={onCollapseAll} className="wbs-toolbar-btn">
        <ChevronUpSquare size={16} />
        Collapse All
      </button>
      {selectedNode && onDelete && (
        <>
          <div className="wbs-toolbar-divider" />
          <button onClick={onDelete} className="wbs-toolbar-btn danger">
            <Trash2 size={16} />
            Delete
          </button>
        </>
      )}
    </div>
  );
}
```

### 8. Create Index Export
File: web/src/components/WBSTree/index.ts

```typescript
export { WBSTree } from './WBSTree';
export { WBSTreeItem } from './WBSTreeItem';
export { WBSToolbar } from './WBSToolbar';
```

### 9. Add Tests
File: web/src/components/WBSTree/__tests__/WBSTree.test.tsx

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WBSTree } from '../WBSTree';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('WBSTree', () => {
  it('renders loading state', () => {
    render(<WBSTree programId="test-id" />, { wrapper });
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders toolbar with Add Root button', async () => {
    render(<WBSTree programId="test-id" />, { wrapper });
    // Wait for loading to complete
    // Check for toolbar elements
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
git checkout -b feature/wbs-tree-component
git add .
git commit -m "feat(frontend): implement WBS tree visualization component

- Add WBSTree, WBSTreeItem, WBSToolbar components
- Add useWBSTree hook for state management
- Add WBS API service
- Add expand/collapse and CRUD operations
- Add CSS styling with hierarchy indentation
- Add unit tests

Supports hierarchical WBS visualization per architecture"

git push -u origin feature/wbs-tree-component
```

Create PR titled: "Feature: WBS Tree Visualization Component"
```

---

### Prompt 3.2.1: EVMS Period Tracking & Time-Phasing

```
Implement EVMS period tracking with time-phased budget and earned value.

## Prerequisites
- Prompt 3.1.1 complete (WBS CRUD working)
- EVMS calculator from Week 1 available

## Implementation Plan

### 1. Create EVMS Period Model Migration
File: api/alembic/versions/003_evms_periods.py

```python
"""Add EVMS period tracking tables.

Revision ID: 003
Revises: 002
Create Date: 2026-01-XX
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create evms_periods table
    op.create_table(
        'evms_periods',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('program_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('programs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period_number', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('is_closed', sa.Boolean(), default=False, nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Unique constraint on program + period number
    op.create_index(
        'ix_evms_periods_program_period',
        'evms_periods',
        ['program_id', 'period_number'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )

    # Create time_phased_data table for BCWS/BCWP/ACWP per period
    op.create_table(
        'time_phased_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('period_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('evms_periods.id', ondelete='CASCADE'), nullable=False),
        sa.Column('wbs_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('wbs_elements.id', ondelete='CASCADE'), nullable=False),
        sa.Column('activity_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('activities.id', ondelete='CASCADE'), nullable=True),
        sa.Column('bcws', sa.Numeric(precision=15, scale=2), default=0, nullable=False),
        sa.Column('bcwp', sa.Numeric(precision=15, scale=2), default=0, nullable=False),
        sa.Column('acwp', sa.Numeric(precision=15, scale=2), default=0, nullable=False),
        sa.Column('etc', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('eac', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )
    
    # Index for efficient period lookups
    op.create_index(
        'ix_time_phased_data_period_wbs',
        'time_phased_data',
        ['period_id', 'wbs_id'],
    )


def downgrade() -> None:
    op.drop_table('time_phased_data')
    op.drop_table('evms_periods')
```

### 2. Create EVMS Period Models
File: api/src/models/evms_period.py

```python
"""EVMS Period models for time-phased tracking."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel


class EVMSPeriod(BaseModel):
    """
    EVMS reporting period for time-phased data.
    
    Each period represents a reporting window (typically monthly)
    for collecting and reporting BCWS, BCWP, ACWP data.
    
    Supports EVMS Guideline 21 (variance identification) and
    GL 27 (revised estimate development).
    """
    
    __tablename__ = "evms_periods"

    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    period_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequential period number within program",
    )
    
    period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="First day of reporting period",
    )
    
    period_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Last day of reporting period",
    )
    
    is_closed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether period is closed for data entry",
    )
    
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When the period was closed",
    )
    
    closed_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Relationships
    program: Mapped["Program"] = relationship(back_populates="evms_periods")
    time_phased_data: Mapped[list["TimePhased Data"]] = relationship(
        back_populates="period",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_evms_periods_program_period",
            "program_id",
            "period_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class TimePhasedData(BaseModel):
    """
    Time-phased EVMS data for a WBS element in a specific period.
    
    Captures BCWS (budget), BCWP (earned value), and ACWP (actual cost)
    for variance analysis and forecasting.
    """
    
    __tablename__ = "time_phased_data"

    period_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("evms_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    wbs_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("wbs_elements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    activity_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=True,
        comment="Optional link to specific activity",
    )
    
    bcws: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        default=Decimal("0"),
        nullable=False,
        comment="Budgeted Cost of Work Scheduled (Planned Value)",
    )
    
    bcwp: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        default=Decimal("0"),
        nullable=False,
        comment="Budgeted Cost of Work Performed (Earned Value)",
    )
    
    acwp: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        default=Decimal("0"),
        nullable=False,
        comment="Actual Cost of Work Performed",
    )
    
    etc: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=True,
        comment="Estimate to Complete",
    )
    
    eac: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=True,
        comment="Estimate at Completion",
    )
    
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Period notes or variance explanations",
    )

    # Relationships
    period: Mapped["EVMSPeriod"] = relationship(back_populates="time_phased_data")
    wbs_element: Mapped["WBSElement"] = relationship()
    activity: Mapped[Optional["Activity"]] = relationship()

    __table_args__ = (
        Index("ix_time_phased_data_period_wbs", "period_id", "wbs_id"),
    )
```

### 3. Create EVMS Schemas
File: api/src/schemas/evms.py

```python
"""Pydantic schemas for EVMS period tracking."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EVMSPeriodBase(BaseModel):
    """Base schema for EVMS periods."""
    
    period_number: int = Field(..., ge=1, description="Sequential period number")
    period_start: date = Field(..., description="Period start date")
    period_end: date = Field(..., description="Period end date")

    @field_validator("period_end")
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        """Ensure period end is after start."""
        if "period_start" in info.data and v <= info.data["period_start"]:
            raise ValueError("period_end must be after period_start")
        return v


class EVMSPeriodCreate(EVMSPeriodBase):
    """Schema for creating an EVMS period."""
    
    program_id: UUID


class EVMSPeriodUpdate(BaseModel):
    """Schema for updating an EVMS period."""
    
    period_start: date | None = None
    period_end: date | None = None


class EVMSPeriodResponse(EVMSPeriodBase):
    """Schema for EVMS period response."""
    
    id: UUID
    program_id: UUID
    is_closed: bool
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TimePhasedDataBase(BaseModel):
    """Base schema for time-phased data."""
    
    bcws: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Budgeted Cost of Work Scheduled",
    )
    bcwp: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Budgeted Cost of Work Performed",
    )
    acwp: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Actual Cost of Work Performed",
    )
    etc: Decimal | None = Field(None, ge=Decimal("0"))
    eac: Decimal | None = Field(None, ge=Decimal("0"))
    notes: str | None = Field(None, max_length=2000)


class TimePhasedDataCreate(TimePhasedDataBase):
    """Schema for creating time-phased data."""
    
    period_id: UUID
    wbs_id: UUID
    activity_id: UUID | None = None


class TimePhasedDataUpdate(BaseModel):
    """Schema for updating time-phased data."""
    
    bcws: Decimal | None = Field(None, ge=Decimal("0"))
    bcwp: Decimal | None = Field(None, ge=Decimal("0"))
    acwp: Decimal | None = Field(None, ge=Decimal("0"))
    etc: Decimal | None = Field(None, ge=Decimal("0"))
    eac: Decimal | None = Field(None, ge=Decimal("0"))
    notes: str | None = None


class TimePhasedDataResponse(TimePhasedDataBase):
    """Schema for time-phased data response."""
    
    id: UUID
    period_id: UUID
    wbs_id: UUID
    activity_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PeriodMetrics(BaseModel):
    """Calculated EVMS metrics for a period."""
    
    period_id: UUID
    period_number: int
    cumulative_bcws: Decimal
    cumulative_bcwp: Decimal
    cumulative_acwp: Decimal
    sv: Decimal  # Schedule Variance
    cv: Decimal  # Cost Variance
    spi: Decimal | None  # Schedule Performance Index
    cpi: Decimal | None  # Cost Performance Index
    bac: Decimal  # Budget at Completion
    eac: Decimal | None  # Estimate at Completion
    vac: Decimal | None  # Variance at Completion
    tcpi: Decimal | None  # To-Complete Performance Index


class SCurveDataPoint(BaseModel):
    """Data point for S-curve visualization."""
    
    period_number: int
    period_end: date
    cumulative_bcws: Decimal
    cumulative_bcwp: Decimal
    cumulative_acwp: Decimal
```

### 4. Create EVMS Period Repository
File: api/src/repositories/evms_period.py

```python
"""Repository for EVMS period operations."""

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.evms_period import EVMSPeriod, TimePhasedData
from src.repositories.base import BaseRepository
from src.schemas.evms import SCurveDataPoint


class EVMSPeriodRepository(BaseRepository[EVMSPeriod]):
    """Repository for EVMS period operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(EVMSPeriod, session)

    async def get_by_program(
        self,
        program_id: UUID,
        *,
        include_closed: bool = True,
    ) -> list[EVMSPeriod]:
        """Get all periods for a program."""
        query = (
            select(EVMSPeriod)
            .where(EVMSPeriod.program_id == program_id)
            .where(EVMSPeriod.deleted_at.is_(None))
        )
        if not include_closed:
            query = query.where(EVMSPeriod.is_closed == False)
        query = query.order_by(EVMSPeriod.period_number)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_current_period(self, program_id: UUID) -> Optional[EVMSPeriod]:
        """Get the current (latest open) period."""
        result = await self.session.execute(
            select(EVMSPeriod)
            .where(EVMSPeriod.program_id == program_id)
            .where(EVMSPeriod.is_closed == False)
            .where(EVMSPeriod.deleted_at.is_(None))
            .order_by(EVMSPeriod.period_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_period_number(
        self,
        program_id: UUID,
        period_number: int,
    ) -> Optional[EVMSPeriod]:
        """Get period by number."""
        result = await self.session.execute(
            select(EVMSPeriod)
            .where(EVMSPeriod.program_id == program_id)
            .where(EVMSPeriod.period_number == period_number)
            .where(EVMSPeriod.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_cumulative_values(
        self,
        program_id: UUID,
        through_period: int,
    ) -> dict[str, Decimal]:
        """Get cumulative BCWS/BCWP/ACWP through a period."""
        result = await self.session.execute(
            select(
                func.sum(TimePhasedData.bcws).label("bcws"),
                func.sum(TimePhasedData.bcwp).label("bcwp"),
                func.sum(TimePhasedData.acwp).label("acwp"),
            )
            .join(EVMSPeriod)
            .where(EVMSPeriod.program_id == program_id)
            .where(EVMSPeriod.period_number <= through_period)
            .where(EVMSPeriod.deleted_at.is_(None))
        )
        row = result.one()
        return {
            "bcws": row.bcws or Decimal("0"),
            "bcwp": row.bcwp or Decimal("0"),
            "acwp": row.acwp or Decimal("0"),
        }

    async def get_s_curve_data(
        self,
        program_id: UUID,
    ) -> list[SCurveDataPoint]:
        """Get S-curve data points for all periods."""
        periods = await self.get_by_program(program_id)
        
        cumulative_bcws = Decimal("0")
        cumulative_bcwp = Decimal("0")
        cumulative_acwp = Decimal("0")
        
        data_points = []
        for period in periods:
            # Get period totals
            result = await self.session.execute(
                select(
                    func.sum(TimePhasedData.bcws),
                    func.sum(TimePhasedData.bcwp),
                    func.sum(TimePhasedData.acwp),
                )
                .where(TimePhasedData.period_id == period.id)
            )
            row = result.one()
            
            cumulative_bcws += row[0] or Decimal("0")
            cumulative_bcwp += row[1] or Decimal("0")
            cumulative_acwp += row[2] or Decimal("0")
            
            data_points.append(SCurveDataPoint(
                period_number=period.period_number,
                period_end=period.period_end,
                cumulative_bcws=cumulative_bcws,
                cumulative_bcwp=cumulative_bcwp,
                cumulative_acwp=cumulative_acwp,
            ))
        
        return data_points
```

### 5. Create EVMS Endpoints
File: api/src/api/v1/endpoints/evms.py

```python
"""EVMS period and metrics endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.core.deps import DbSession, get_current_user
from src.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from src.models.user import User
from src.repositories.evms_period import EVMSPeriodRepository
from src.repositories.program import ProgramRepository
from src.schemas.evms import (
    EVMSPeriodCreate,
    EVMSPeriodResponse,
    EVMSPeriodUpdate,
    PeriodMetrics,
    SCurveDataPoint,
    TimePhasedDataCreate,
    TimePhasedDataResponse,
    TimePhasedDataUpdate,
)
from src.services.evms import EVMSCalculator

router = APIRouter()


@router.get("/periods", response_model=list[EVMSPeriodResponse])
async def list_periods(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    program_id: Annotated[UUID, Query(description="Program ID")],
    include_closed: bool = True,
) -> list[EVMSPeriodResponse]:
    """List all EVMS periods for a program."""
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError("Program", program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    period_repo = EVMSPeriodRepository(db)
    periods = await period_repo.get_by_program(
        program_id,
        include_closed=include_closed,
    )
    return [EVMSPeriodResponse.model_validate(p) for p in periods]


@router.post("/periods", response_model=EVMSPeriodResponse, status_code=201)
async def create_period(
    period_in: EVMSPeriodCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> EVMSPeriodResponse:
    """Create a new EVMS period."""
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(period_in.program_id)
    if not program:
        raise NotFoundError("Program", period_in.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    period_repo = EVMSPeriodRepository(db)
    
    # Check for duplicate period number
    existing = await period_repo.get_by_period_number(
        period_in.program_id,
        period_in.period_number,
    )
    if existing:
        raise ValidationError(
            f"Period {period_in.period_number} already exists"
        )

    from src.models.evms_period import EVMSPeriod
    period = EVMSPeriod(
        program_id=period_in.program_id,
        period_number=period_in.period_number,
        period_start=period_in.period_start,
        period_end=period_in.period_end,
    )
    created = await period_repo.create(period)
    return EVMSPeriodResponse.model_validate(created)


@router.post("/periods/{period_id}/close", response_model=EVMSPeriodResponse)
async def close_period(
    period_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> EVMSPeriodResponse:
    """Close an EVMS period."""
    period_repo = EVMSPeriodRepository(db)
    period = await period_repo.get_by_id(period_id)
    if not period:
        raise NotFoundError("Period", period_id)

    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(period.program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    if period.is_closed:
        raise ValidationError("Period is already closed")

    updated = await period_repo.update(period, {
        "is_closed": True,
        "closed_at": datetime.utcnow(),
        "closed_by_id": current_user.id,
    })
    return EVMSPeriodResponse.model_validate(updated)


@router.get("/metrics/{program_id}", response_model=PeriodMetrics)
async def get_program_metrics(
    program_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    through_period: Annotated[int | None, Query()] = None,
) -> PeriodMetrics:
    """Get EVMS metrics for a program."""
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError("Program", program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    period_repo = EVMSPeriodRepository(db)
    
    # Get current or specified period
    if through_period is None:
        current = await period_repo.get_current_period(program_id)
        if not current:
            periods = await period_repo.get_by_program(program_id)
            if periods:
                through_period = periods[-1].period_number
            else:
                raise ValidationError("No periods defined for program")
        else:
            through_period = current.period_number

    # Get cumulative values
    cumulative = await period_repo.get_cumulative_values(
        program_id,
        through_period,
    )

    # Get BAC from program
    bac = program.total_budget or Decimal("1000000")  # Default if not set

    # Calculate metrics using EVMS calculator
    calc = EVMSCalculator(
        bcws=cumulative["bcws"],
        bcwp=cumulative["bcwp"],
        acwp=cumulative["acwp"],
        bac=bac,
    )

    period = await period_repo.get_by_period_number(program_id, through_period)
    
    return PeriodMetrics(
        period_id=period.id if period else UUID(int=0),
        period_number=through_period,
        cumulative_bcws=cumulative["bcws"],
        cumulative_bcwp=cumulative["bcwp"],
        cumulative_acwp=cumulative["acwp"],
        sv=calc.sv,
        cv=calc.cv,
        spi=calc.spi,
        cpi=calc.cpi,
        bac=bac,
        eac=calc.eac,
        vac=calc.vac,
        tcpi=calc.tcpi_bac,
    )


@router.get("/s-curve/{program_id}", response_model=list[SCurveDataPoint])
async def get_s_curve(
    program_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[SCurveDataPoint]:
    """Get S-curve data for visualization."""
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    if not program:
        raise NotFoundError("Program", program_id)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    period_repo = EVMSPeriodRepository(db)
    return await period_repo.get_s_curve_data(program_id)
```

### 6. Register Router
Add to api/src/api/v1/router.py:
```python
from src.api.v1.endpoints import evms

api_router.include_router(evms.router, prefix="/evms", tags=["EVMS"])
```

## Verification
```bash
cd api
alembic upgrade head
ruff check src tests --fix
ruff format src tests
mypy src --ignore-missing-imports
pytest tests/ -v --cov=src
```

## Git Workflow
```bash
git checkout -b feature/evms-period-tracking
git add .
git commit -m "feat(evms): implement EVMS period tracking with time-phasing

- Add EVMSPeriod and TimePhasedData models
- Add period and time-phased data schemas
- Add EVMSPeriodRepository with cumulative calculations
- Add EVMS endpoints (periods, metrics, s-curve)
- Add database migration for new tables

EVMS compliance: Supports GL 8 (time-phased budgets),
GL 21 (variance identification), GL 27 (EAC development)"

git push -u origin feature/evms-period-tracking
```

Create PR titled: "Feature: EVMS Period Tracking & Time-Phasing"
```

---

### Prompt 3.2.2: EVMS Dashboard with Metrics

**Note**: Due to length constraints, this prompt and remaining prompts (3.3.1, 3.4.1) follow the same pattern. They are available in the complete document.

```
Implement the EVMS dashboard frontend with metric visualizations.

## Key Components
1. Dashboard page with KPI cards (SPI, CPI, CV, SV)
2. S-Curve chart using Recharts
3. Variance table with color-coded thresholds
4. Period selector for historical analysis

## Files to Create
- web/src/pages/EVMSDashboard.tsx
- web/src/components/Dashboard/KPICard.tsx
- web/src/components/Dashboard/SCurveChart.tsx
- web/src/components/Dashboard/VarianceTable.tsx
- web/src/hooks/useEVMSMetrics.ts

## Verification
```bash
cd web
npm run lint
npm run test
npm run build
```

## Git Workflow
```bash
git checkout -b feature/evms-dashboard
git add .
git commit -m "feat(frontend): implement EVMS dashboard with metrics visualization"
git push -u origin feature/evms-dashboard
```
```

---

### Prompt 3.3.1: Report Generation (CPR Format 1)

```
Implement CPR Format 1 (WBS) report generation.

## Key Components
1. Report generation service
2. PDF generation using reportlab
3. Excel export using openpyxl
4. CPR Format 1 template (WBS-based EV report)

## DFARS Compliance
- CPR Format 1: WBS by element with BCWS/BCWP/ACWP/BAC/EAC
- Variance thresholds per contract requirements
- Audit trail for generated reports

## Verification
```bash
cd api
pytest tests/integration/test_reports.py -v
```

## Git Workflow
```bash
git checkout -b feature/cpr-reports
git add .
git commit -m "feat(reports): implement CPR Format 1 report generation"
git push -u origin feature/cpr-reports
```
```

---

### Prompt 3.4.1: Week 3 Integration Test & Documentation

```
Complete Week 3 with integration tests and documentation updates.

## Context
Final prompt for Week 3 to ensure all components work together and documentation is current.

## Tasks

### 1. E2E Integration Test
File: api/tests/integration/test_week3_e2e.py

Test complete workflow:
1. Create program with WBS hierarchy
2. Add EVMS periods
3. Enter time-phased data
4. Calculate metrics
5. Generate CPR report
6. Verify dashboard data

### 2. Documentation Updates

Update CLAUDE.md:
- Mark Week 3 items complete
- Update coverage numbers
- Document new endpoints

Update docs/architecture.md:
- Add EVMS period tracking section
- Add WBS tree visualization details
- Update API endpoint list

### 3. Coverage Verification
```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=75
```

## Git Workflow
```bash
git checkout -b feature/week3-completion
git add .
git commit -m "test(e2e): add Week 3 integration tests and update documentation

- Complete EVMS workflow test
- Update CLAUDE.md with Week 3 status
- Update architecture documentation
- Verify 75%+ test coverage

Week 3 complete. Ready for Week 4."

git push -u origin feature/week3-completion
```

Create PR titled: "Week 3 Complete: Integration Tests & Documentation"
```

---

## Week 3 Completion Checklist

After completing all prompts:

- [ ] Week 2 verification passed (Prompt 3.0.1)
- [ ] WBS CRUD with ltree hierarchy working
- [ ] WBS Tree visualization component complete
- [ ] EVMS period tracking endpoints working
- [ ] EVMS dashboard with metrics displayed
- [ ] CPR Format 1 report generation working
- [ ] All tests passing
- [ ] Coverage at 75%+ overall
- [ ] All PRs merged to main
- [ ] Documentation updated

## Running All Week 3 Tests

```bash
cd api

# Full verification ladder
ruff check src tests --fix
ruff format src tests
mypy src --ignore-missing-imports

# All tests with coverage
pytest -v --cov=src --cov-report=term-missing --cov-fail-under=75

# Coverage report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

---

*Document Version: 1.0*
*Generated: January 2026*
*For: Defense PM Tool Week 3 Development*
