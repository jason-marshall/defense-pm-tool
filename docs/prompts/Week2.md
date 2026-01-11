# Defense PM Tool - Week 2 Development Prompts

> **Week 2 Focus**: Activity Management, Dependencies, and Basic Gantt
> **Prerequisites**: Week 1 complete, all prompts through 3.2 executed
> **Timeline**: Days 8-14

---

## Overview

| Day | Prompt | Description | Time Est. |
|-----|--------|-------------|-----------|
| 8 | 2.0.1 | Hotfix: Model-Schema Alignment | 1-2 hrs |
| 8-9 | 2.1.1 | Activity CRUD with Auth | 2-3 hrs |
| 9-10 | 2.1.2 | Activity Tests (Comprehensive) | 2 hrs |
| 10-11 | 2.2.1 | Dependency CRUD + Cycle Detection | 3 hrs |
| 11-12 | 2.2.2 | Dependency Tests | 2 hrs |
| 12-13 | 2.3.1 | Schedule Calculation Endpoint | 2 hrs |
| 13-14 | 2.4.1 | Basic Gantt Component (Frontend) | 4 hrs |
| 14 | 2.5.1 | Week 2 Integration Test | 2 hrs |

---

## Prompt 2.0.1: Hotfix - Model-Schema Alignment

**Priority**: 🔴 CRITICAL - Run this first before any other Week 2 work

```
Fix model-schema-repository alignment issues before proceeding with Week 2.

## Context
Code review identified field mismatches between models, schemas, and repositories that will cause runtime errors.

## Required Changes

### 1. Activity Model - Add program_id and code
File: api/src/models/activity.py

Add these fields after wbs_id:

```python
# Direct reference to program for efficient queries
program_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("programs.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
    comment="FK to parent program (denormalized for query efficiency)",
)

# Activity code for identification
code: Mapped[str] = mapped_column(
    String(50),
    nullable=False,
    comment="Unique code within program (e.g., A-001)",
)
```

Add to __table_args__:
```python
# Unique constraint on program_id + code
Index(
    "ix_activities_program_code",
    "program_id",
    "code",
    unique=True,
    postgresql_where=text("deleted_at IS NULL"),
),
```

Add relationship:
```python
program: Mapped["Program"] = relationship(
    "Program",
    back_populates="activities",
)
```

### 2. Program Model - Add activities relationship
File: api/src/models/program.py

Add relationship:
```python
activities: Mapped[list["Activity"]] = relationship(
    "Activity",
    back_populates="program",
    cascade="all, delete-orphan",
    lazy="selectin",
)
```

### 3. Dependency Model - Rename lag_days to lag
File: api/src/models/dependency.py

Change:
- `lag_days` -> `lag` (field name)
- Update all references in the file
- Update docstrings

### 4. Create Migration
```bash
cd api
alembic revision --autogenerate -m "add activity program_id and code, rename dependency lag"
```

Review the generated migration and ensure it:
- Adds activities.program_id with FK
- Adds activities.code
- Creates unique index on (program_id, code)
- Renames dependencies.lag_days to lag

### 5. Update ActivityRepository
File: api/src/repositories/activity.py

Fix get_by_program to use program_id directly:
```python
async def get_by_program(
    self,
    program_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Activity]:
    result = await self.session.execute(
        select(Activity)
        .where(Activity.program_id == program_id)
        .where(Activity.deleted_at.is_(None))
        .offset(skip)
        .limit(limit)
        .order_by(Activity.code)
    )
    return list(result.scalars().all())
```

### 6. Update CPM Engine
File: api/src/services/cpm.py

Change all references from `dep.lag_days` to `dep.lag`

### 7. Update Test Fixtures
File: api/tests/conftest.py

Update sample_activities to include program_id and code:
```python
@pytest.fixture
def sample_activities() -> list[Activity]:
    program_id = uuid4()
    return [
        Activity(
            id=uuid4(),
            program_id=program_id,
            wbs_id=uuid4(),
            name="Activity A",
            code="A",
            duration=5,
        ),
        # ... etc
    ]
```

Update sample_dependencies to use `lag` instead of `lag_days`

### 8. Update Schemas
File: api/src/schemas/activity.py

Add to ActivityCreate:
```python
program_id: UUID = Field(..., description="ID of the parent program")
code: str | None = Field(None, max_length=50, description="Activity code (auto-generated if not provided)")
```

File: api/src/schemas/dependency.py

Change lag_days to lag in all schemas.

## Verification
```bash
cd api
alembic upgrade head
ruff check src tests --fix
ruff format src tests
mypy src --ignore-missing-imports
pytest tests/unit -v
pytest tests/integration -v
```

## Git Workflow
```bash
git checkout -b hotfix/model-schema-alignment
# Make all changes
git add .
git commit -m "fix(models): align Activity and Dependency fields with schemas

- Add program_id FK to Activity for direct program queries
- Add code field to Activity for identification
- Rename Dependency.lag_days to lag for consistency
- Update repositories and CPM engine
- Update test fixtures

This fixes runtime errors in activity and dependency endpoints."

git push -u origin hotfix/model-schema-alignment
```

Create PR titled: "Hotfix: Model-Schema Alignment"
```

---

## Prompt 2.1.1: Activity CRUD with Authentication

```
Implement complete Activity CRUD operations with authentication and authorization.

## Prerequisites
- Hotfix 2.0.1 merged and migrations applied
- Auth endpoints working (verify with: curl http://localhost:8000/api/v1/auth/me)

## Implementation Plan

### 1. Update Activity Endpoint with Auth
File: api/src/api/v1/endpoints/activities.py

```python
"""Activity endpoints with authentication."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.core.deps import DbSession, get_current_user
from src.core.exceptions import AuthorizationError, NotFoundError
from src.models.user import User
from src.repositories.activity import ActivityRepository
from src.repositories.program import ProgramRepository
from src.schemas.activity import (
    ActivityCreate,
    ActivityListResponse,
    ActivityResponse,
    ActivityUpdate,
)

router = APIRouter()


def generate_activity_code(existing_codes: list[str], prefix: str = "A") -> str:
    """Generate next activity code based on existing codes."""
    if not existing_codes:
        return f"{prefix}-001"
    
    # Extract numbers and find max
    numbers = []
    for code in existing_codes:
        try:
            num = int(code.split("-")[-1])
            numbers.append(num)
        except (ValueError, IndexError):
            continue
    
    next_num = max(numbers, default=0) + 1
    return f"{prefix}-{next_num:03d}"


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    program_id: Annotated[UUID, Query(description="Filter by program ID")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ActivityListResponse:
    """List all activities for a program with pagination."""
    # Verify user has access to program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")
    
    # Check authorization (owner or admin)
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Not authorized to view this program's activities")
    
    repo = ActivityRepository(db)
    skip = (page - 1) * page_size
    
    activities = await repo.get_by_program(program_id, skip=skip, limit=page_size)
    total = await repo.count(filters={"program_id": program_id})
    
    return ActivityListResponse(
        items=[ActivityResponse.model_validate(a) for a in activities],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ActivityResponse, status_code=201)
async def create_activity(
    activity_in: ActivityCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ActivityResponse:
    """Create a new activity."""
    # Verify program exists and user has access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity_in.program_id)
    
    if not program:
        raise NotFoundError(f"Program {activity_in.program_id} not found", "PROGRAM_NOT_FOUND")
    
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Not authorized to add activities to this program")
    
    activity_repo = ActivityRepository(db)
    
    # Auto-generate code if not provided
    activity_data = activity_in.model_dump()
    if not activity_data.get("code"):
        existing = await activity_repo.get_by_program(activity_in.program_id)
        existing_codes = [a.code for a in existing if a.code]
        activity_data["code"] = generate_activity_code(existing_codes)
    
    activity = await activity_repo.create(activity_data)
    await db.commit()
    await db.refresh(activity)
    
    return ActivityResponse.model_validate(activity)


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ActivityResponse:
    """Get a single activity by ID."""
    repo = ActivityRepository(db)
    activity = await repo.get_by_id(activity_id)
    
    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")
    
    # Verify access through program
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity.program_id)
    
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Not authorized to view this activity")
    
    return ActivityResponse.model_validate(activity)


@router.patch("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: UUID,
    activity_in: ActivityUpdate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ActivityResponse:
    """Update an existing activity."""
    repo = ActivityRepository(db)
    activity = await repo.get_by_id(activity_id)
    
    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")
    
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity.program_id)
    
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Not authorized to modify this activity")
    
    updated = await repo.update(activity, activity_in.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(updated)
    
    return ActivityResponse.model_validate(updated)


@router.delete("/{activity_id}", status_code=204)
async def delete_activity(
    activity_id: UUID,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete an activity."""
    repo = ActivityRepository(db)
    activity = await repo.get_by_id(activity_id)
    
    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")
    
    # Verify access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity.program_id)
    
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Not authorized to delete this activity")
    
    await repo.delete(activity)
    await db.commit()
```

### 2. Add get_current_user Dependency
File: api/src/core/deps.py

```python
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import decode_token
from src.core.database import get_db
from src.core.exceptions import AuthenticationError
from src.models.user import User
from src.repositories.user import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    """Get current authenticated user from JWT token."""
    try:
        payload = decode_token(token)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(payload.sub)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user
```

### 3. Create UserRepository (if not exists)
File: api/src/repositories/user.py

```python
"""Repository for User model."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import hash_password, verify_password
from src.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """Check if email is already registered."""
        user = await self.get_by_email(email)
        return user is not None

    async def authenticate(self, email: str, password: str) -> User | None:
        """Authenticate user by email and password."""
        user = await self.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
    ) -> User:
        """Create a new user with hashed password."""
        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user
```

## Verification
```bash
cd api
ruff check src tests --fix
ruff format src tests
mypy src --ignore-missing-imports
pytest tests/unit -v
pytest tests/integration -v
```

## Git Workflow
```bash
git checkout -b feature/activity-crud-auth
git add .
git commit -m "feat(activities): implement activity CRUD with authentication

- Add authentication to all activity endpoints
- Add authorization checks (owner or admin)
- Auto-generate activity codes
- Add UserRepository for auth support
- Update get_current_user dependency"

git push -u origin feature/activity-crud-auth
```
```

---

## Prompt 2.1.2: Activity Tests (Comprehensive)

```
Create comprehensive tests for Activity CRUD operations.

## Unit Tests
File: api/tests/unit/test_activity_crud.py

```python
"""Unit tests for Activity CRUD operations."""

import pytest
from decimal import Decimal
from uuid import uuid4

from src.models.activity import Activity
from src.models.enums import ConstraintType
from src.schemas.activity import ActivityCreate, ActivityUpdate


class TestActivityModel:
    """Tests for Activity model."""

    def test_activity_properties(self):
        """Test Activity computed properties."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Test",
            code="T-001",
            duration=10,
            percent_complete=Decimal("50.00"),
            budgeted_cost=Decimal("10000.00"),
            actual_cost=Decimal("4500.00"),
        )
        
        assert activity.remaining_duration == 5
        assert activity.earned_value == Decimal("5000.00")
        assert not activity.is_completed
        assert not activity.is_started  # actual_start is None

    def test_milestone_has_zero_duration(self):
        """Milestone should have duration 0."""
        activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Milestone",
            code="M-001",
            duration=0,
            is_milestone=True,
        )
        assert activity.is_milestone
        assert activity.duration == 0


class TestActivityCreate:
    """Tests for ActivityCreate schema."""

    def test_valid_activity(self):
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

    def test_milestone_forces_zero_duration(self):
        """Milestone should force duration to 0."""
        data = ActivityCreate(
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Phase Complete",
            code="M-001",
            duration=5,
            is_milestone=True,
        )
        assert data.duration == 0
        assert data.is_milestone

    def test_constraint_date_required_for_snet(self):
        """SNET constraint requires date."""
        with pytest.raises(ValueError, match="constraint_date is required"):
            ActivityCreate(
                program_id=uuid4(),
                wbs_id=uuid4(),
                name="Test",
                code="T-001",
                constraint_type=ConstraintType.SNET,
            )

    def test_constraint_date_required_for_fnlt(self):
        """FNLT constraint requires date."""
        with pytest.raises(ValueError, match="constraint_date is required"):
            ActivityCreate(
                program_id=uuid4(),
                wbs_id=uuid4(),
                name="Test",
                code="T-001",
                constraint_type=ConstraintType.FNLT,
            )

    def test_asap_does_not_require_date(self):
        """ASAP constraint does not require date."""
        data = ActivityCreate(
            program_id=uuid4(),
            wbs_id=uuid4(),
            name="Test",
            code="T-001",
            constraint_type=ConstraintType.ASAP,
        )
        assert data.constraint_type == ConstraintType.ASAP
        assert data.constraint_date is None


class TestActivityUpdate:
    """Tests for ActivityUpdate schema."""

    def test_partial_update(self):
        """Should allow partial updates."""
        data = ActivityUpdate(name="Updated Name")
        assert data.name == "Updated Name"
        assert data.duration is None

    def test_percent_complete_range(self):
        """Percent complete must be 0-100."""
        with pytest.raises(ValueError):
            ActivityUpdate(percent_complete=Decimal("150.00"))

    def test_percent_complete_negative(self):
        """Percent complete cannot be negative."""
        with pytest.raises(ValueError):
            ActivityUpdate(percent_complete=Decimal("-10.00"))
```

## Integration Tests
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
        email = f"activity_test_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPass123!",
                "full_name": "Activity Tester",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "TestPass123!"},
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
                "code": f"TP-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        return response.json()["id"]

    async def test_create_activity_requires_auth(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.post(
            "/api/v1/activities",
            json={
                "program_id": str(uuid4()),
                "name": "Test Activity",
            },
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
        assert data["code"] == "DR-001"
        assert data["duration"] == 5

    async def test_create_activity_auto_code(
        self, client: AsyncClient, auth_headers: dict, program_id: str
    ):
        """Should auto-generate code if not provided."""
        response = await client.post(
            "/api/v1/activities",
            headers=auth_headers,
            json={
                "program_id": program_id,
                "name": "Auto Code Activity",
                "duration": 3,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] is not None
        assert data["code"].startswith("A-")

    async def test_list_activities_by_program(
        self, client: AsyncClient, auth_headers: dict, program_id: str
    ):
        """Should list activities filtered by program."""
        # Create multiple activities
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

    async def test_get_activity_success(
        self, client: AsyncClient, auth_headers: dict, program_id: str
    ):
        """Should get activity by ID."""
        # Create activity
        create_response = await client.post(
            "/api/v1/activities",
            headers=auth_headers,
            json={
                "program_id": program_id,
                "name": "Test Activity",
                "code": "TA-001",
                "duration": 5,
            },
        )
        activity_id = create_response.json()["id"]

        # Get activity
        response = await client.get(
            f"/api/v1/activities/{activity_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == activity_id

    async def test_update_activity_success(
        self, client: AsyncClient, auth_headers: dict, program_id: str
    ):
        """Should update activity."""
        # Create activity
        create_response = await client.post(
            "/api/v1/activities",
            headers=auth_headers,
            json={
                "program_id": program_id,
                "name": "Original Name",
                "code": "ON-001",
                "duration": 5,
            },
        )
        activity_id = create_response.json()["id"]

        # Update activity
        response = await client.patch(
            f"/api/v1/activities/{activity_id}",
            headers=auth_headers,
            json={"name": "Updated Name", "duration": 10},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["duration"] == 10

    async def test_delete_activity_success(
        self, client: AsyncClient, auth_headers: dict, program_id: str
    ):
        """Should delete activity."""
        # Create activity
        create_response = await client.post(
            "/api/v1/activities",
            headers=auth_headers,
            json={
                "program_id": program_id,
                "name": "To Delete",
                "code": "TD-001",
                "duration": 5,
            },
        )
        activity_id = create_response.json()["id"]

        # Delete activity
        response = await client.delete(
            f"/api/v1/activities/{activity_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify deleted
        get_response = await client.get(
            f"/api/v1/activities/{activity_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    async def test_unauthorized_access_other_user_program(
        self, client: AsyncClient, auth_headers: dict, program_id: str
    ):
        """Should not allow access to other user's program activities."""
        # Create another user
        other_email = f"other_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": other_email,
                "password": "OtherPass123!",
                "full_name": "Other User",
            },
        )
        other_response = await client.post(
            "/api/v1/auth/login",
            json={"email": other_email, "password": "OtherPass123!"},
        )
        other_headers = {
            "Authorization": f"Bearer {other_response.json()['access_token']}"
        }

        # Try to list activities from first user's program
        response = await client.get(
            f"/api/v1/activities?program_id={program_id}",
            headers=other_headers,
        )
        assert response.status_code == 403
```

## Verification
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
git checkout -b feature/activity-tests
git add .
git commit -m "test(activities): add comprehensive activity CRUD tests

- Unit tests for Activity model and schemas
- Integration tests for all CRUD endpoints
- Auth and authorization tests
- Edge case coverage"

git push -u origin feature/activity-tests
```
```

---

## Prompt 2.2.1: Dependency CRUD with Cycle Detection

```
Implement dependency management with pre-creation cycle detection.

## Implementation

### 1. Update Dependency Endpoint
File: api/src/api/v1/endpoints/dependencies.py

Add cycle detection before creating dependencies:

```python
"""Dependency endpoints with cycle detection."""

from uuid import UUID

from fastapi import APIRouter, Depends

from src.core.deps import DbSession, get_current_user
from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.models.user import User
from src.repositories.activity import ActivityRepository
from src.repositories.dependency import DependencyRepository
from src.schemas.dependency import (
    DependencyCreate,
    DependencyListResponse,
    DependencyResponse,
)
from src.services.cpm import CPMEngine
from src.core.exceptions import CircularDependencyError

router = APIRouter()


async def would_create_cycle(
    db,
    program_id: UUID,
    predecessor_id: UUID,
    successor_id: UUID,
) -> tuple[bool, list[UUID] | None]:
    """
    Check if adding this dependency would create a cycle.
    
    Returns:
        Tuple of (would_create_cycle, cycle_path)
    """
    activity_repo = ActivityRepository(db)
    dep_repo = DependencyRepository(db)
    
    # Get all activities for the program
    activities = await activity_repo.get_by_program(program_id, limit=10000)
    
    if not activities:
        return False, None
    
    # Get existing dependencies
    all_deps = []
    for activity in activities:
        deps = await dep_repo.get_successors(activity.id)
        all_deps.extend(deps)
    
    # Create temporary dependency for testing
    from src.models.dependency import Dependency
    temp_dep = Dependency(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        predecessor_id=predecessor_id,
        successor_id=successor_id,
        dependency_type="FS",
        lag=0,
    )
    
    # Test with CPM engine
    try:
        engine = CPMEngine(activities, all_deps + [temp_dep])
        cycle = engine._detect_cycles()
        if cycle:
            return True, cycle
        return False, None
    except CircularDependencyError as e:
        return True, e.cycle_path


@router.post("", response_model=DependencyResponse, status_code=201)
async def create_dependency(
    dependency_in: DependencyCreate,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> DependencyResponse:
    """Create a new dependency between two activities."""
    activity_repo = ActivityRepository(db)
    dep_repo = DependencyRepository(db)

    # Verify predecessor exists
    predecessor = await activity_repo.get_by_id(dependency_in.predecessor_id)
    if not predecessor:
        raise NotFoundError(
            f"Predecessor activity {dependency_in.predecessor_id} not found",
            "PREDECESSOR_NOT_FOUND",
        )

    # Verify successor exists
    successor = await activity_repo.get_by_id(dependency_in.successor_id)
    if not successor:
        raise NotFoundError(
            f"Successor activity {dependency_in.successor_id} not found",
            "SUCCESSOR_NOT_FOUND",
        )

    # Verify same program
    if predecessor.program_id != successor.program_id:
        raise ValidationError(
            "Predecessor and successor must belong to the same program",
            "CROSS_PROGRAM_DEPENDENCY",
        )

    # Check for duplicate
    if await dep_repo.dependency_exists(
        dependency_in.predecessor_id,
        dependency_in.successor_id,
    ):
        raise ConflictError(
            "Dependency already exists between these activities",
            "DUPLICATE_DEPENDENCY",
        )

    # Check for cycle
    would_cycle, cycle_path = await would_create_cycle(
        db,
        predecessor.program_id,
        dependency_in.predecessor_id,
        dependency_in.successor_id,
    )
    
    if would_cycle:
        raise CircularDependencyError(cycle_path or [])

    # Create dependency
    dependency = await dep_repo.create(dependency_in.model_dump())
    await db.commit()
    await db.refresh(dependency)

    return DependencyResponse.model_validate(dependency)


@router.get("/program/{program_id}", response_model=DependencyListResponse)
async def list_dependencies_for_program(
    program_id: UUID,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> DependencyListResponse:
    """List all dependencies for a program."""
    dep_repo = DependencyRepository(db)
    dependencies = await dep_repo.get_by_program(program_id)

    return DependencyListResponse(
        items=[DependencyResponse.model_validate(d) for d in dependencies],
        total=len(dependencies),
    )


# ... rest of endpoints with auth
```

### 2. Add get_by_program to DependencyRepository
File: api/src/repositories/dependency.py

```python
async def get_by_program(self, program_id: UUID) -> list[Dependency]:
    """Get all dependencies for activities in a program."""
    # Get all activity IDs for the program
    activity_result = await self.session.execute(
        select(Activity.id).where(Activity.program_id == program_id)
    )
    activity_ids = [row[0] for row in activity_result.all()]
    
    if not activity_ids:
        return []
    
    # Get dependencies where predecessor is in the program
    result = await self.session.execute(
        select(Dependency)
        .where(Dependency.predecessor_id.in_(activity_ids))
        .where(Dependency.deleted_at.is_(None))
    )
    return list(result.scalars().all())
```

## Verification
```bash
cd api
ruff check src tests --fix
mypy src --ignore-missing-imports
pytest tests/unit/test_cpm.py -v
pytest tests/integration/test_dependencies_api.py -v
```

## Git Workflow
```bash
git checkout -b feature/dependency-cycle-detection
git add .
git commit -m "feat(dependencies): add pre-creation cycle detection

- Check for cycles before creating dependency
- Return cycle path in error response
- Add get_by_program to DependencyRepository
- Integration with CPM engine"

git push -u origin feature/dependency-cycle-detection
```
```

---

## Prompt 2.3.1: Schedule Calculation Endpoint

```
Implement the schedule calculation endpoint that triggers CPM calculation.

## Implementation
File: api/src/api/v1/endpoints/schedule.py

```python
"""Schedule and CPM calculation endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends

from src.core.deps import DbSession, get_current_user
from src.core.exceptions import NotFoundError, AuthorizationError
from src.models.user import User
from src.repositories.activity import ActivityRepository
from src.repositories.dependency import DependencyRepository
from src.repositories.program import ProgramRepository
from src.schemas.activity import ScheduleResult
from src.services.cpm import CPMEngine

router = APIRouter()


@router.post("/calculate/{program_id}", response_model=list[ScheduleResult])
async def calculate_schedule(
    program_id: UUID,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> list[ScheduleResult]:
    """
    Calculate the CPM schedule for a program.

    Performs forward and backward pass calculations to determine:
    - Early Start (ES) and Early Finish (EF)
    - Late Start (LS) and Late Finish (LF)
    - Total Float and Free Float
    - Critical Path identification

    Updates all activities with calculated values and returns results.
    """
    # Verify program exists and user has access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")
    
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Not authorized to calculate schedule for this program")

    # Get all activities
    activity_repo = ActivityRepository(db)
    activities = await activity_repo.get_by_program(program_id, limit=10000)

    if not activities:
        return []

    # Get all dependencies
    dep_repo = DependencyRepository(db)
    all_dependencies = await dep_repo.get_by_program(program_id)

    # Run CPM calculation
    engine = CPMEngine(activities, all_dependencies)
    results = engine.calculate()

    # Update activities with calculated values
    for activity in activities:
        if activity.id in results:
            result = results[activity.id]
            activity.early_start = None  # Store as date if needed
            activity.early_finish = None
            activity.late_start = None
            activity.late_finish = None
            activity.total_float = result.total_float
            activity.free_float = result.free_float
            activity.is_critical = result.is_critical

    await db.commit()

    # Return results
    return [
        ScheduleResult(
            activity_id=r.activity_id,
            early_start=r.early_start,
            early_finish=r.early_finish,
            late_start=r.late_start,
            late_finish=r.late_finish,
            total_float=r.total_float,
            free_float=r.free_float,
            is_critical=r.is_critical,
        )
        for r in results.values()
    ]


@router.get("/critical-path/{program_id}", response_model=list[UUID])
async def get_critical_path(
    program_id: UUID,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> list[UUID]:
    """Get activity IDs on the critical path."""
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")
    
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Not authorized to view this program")

    activity_repo = ActivityRepository(db)
    critical = await activity_repo.get_critical_path(program_id)

    return [a.id for a in critical]


@router.get("/duration/{program_id}")
async def get_project_duration(
    program_id: UUID,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Get the total project duration in working days."""
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(program_id)
    
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")
    
    if program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Not authorized to view this program")

    activity_repo = ActivityRepository(db)
    activities = await activity_repo.get_by_program(program_id, limit=10000)

    if not activities:
        return {"duration": 0}

    dep_repo = DependencyRepository(db)
    all_dependencies = await dep_repo.get_by_program(program_id)

    engine = CPMEngine(activities, all_dependencies)
    engine.calculate()

    return {"duration": engine.get_project_duration()}
```

## Verification
```bash
cd api
ruff check src tests --fix
mypy src --ignore-missing-imports
pytest tests/unit/test_cpm.py -v
pytest -v
```

## Git Workflow
```bash
git checkout -b feature/schedule-endpoint
git add .
git commit -m "feat(schedule): implement CPM calculation endpoint

- POST /schedule/calculate/{program_id}
- GET /schedule/critical-path/{program_id}
- GET /schedule/duration/{program_id}
- Integrates with CPM engine
- Updates activities with calculated values"

git push -u origin feature/schedule-endpoint
```
```

---

## Prompt 2.5.1: Week 2 Integration Test

```
Create a comprehensive end-to-end integration test for Week 2 functionality.

## Implementation
File: api/tests/integration/test_week2_e2e.py

```python
"""End-to-end integration test for Week 2 functionality."""

import pytest
from httpx import AsyncClient
from uuid import uuid4

pytestmark = pytest.mark.asyncio


class TestWeek2EndToEnd:
    """Complete workflow test for Week 2 features."""

    @pytest.fixture
    async def setup_user(self, client: AsyncClient) -> tuple[dict, str]:
        """Create user and return auth headers + user email."""
        email = f"e2e_test_{uuid4().hex[:8]}@example.com"
        
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "E2ETestPass123!",
                "full_name": "E2E Test User",
            },
        )
        
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "E2ETestPass123!"},
        )
        token = response.json()["access_token"]
        
        return {"Authorization": f"Bearer {token}"}, email

    async def test_complete_schedule_workflow(
        self, client: AsyncClient, setup_user: tuple
    ):
        """
        Test complete workflow:
        1. Create program
        2. Create activities (A -> B -> C -> D with parallel path)
        3. Create dependencies
        4. Calculate schedule
        5. Verify critical path
        """
        headers, _ = setup_user

        # Step 1: Create program
        program_response = await client.post(
            "/api/v1/programs",
            headers=headers,
            json={
                "name": "E2E Test Program",
                "code": f"E2E-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Step 2: Create activities
        # Critical path: Start -> A(5d) -> B(3d) -> D(2d) -> End
        # Parallel:      Start -> C(4d) -------> D(2d) -> End
        
        activities = {}
        activity_data = [
            {"name": "Start", "code": "START", "duration": 0, "is_milestone": True},
            {"name": "Activity A", "code": "A", "duration": 5},
            {"name": "Activity B", "code": "B", "duration": 3},
            {"name": "Activity C", "code": "C", "duration": 4},
            {"name": "Activity D", "code": "D", "duration": 2},
            {"name": "End", "code": "END", "duration": 0, "is_milestone": True},
        ]

        for data in activity_data:
            response = await client.post(
                "/api/v1/activities",
                headers=headers,
                json={"program_id": program_id, **data},
            )
            assert response.status_code == 201, f"Failed to create {data['name']}"
            activities[data["code"]] = response.json()["id"]

        # Step 3: Create dependencies
        dependencies = [
            ("START", "A"),  # Start -> A
            ("START", "C"),  # Start -> C
            ("A", "B"),      # A -> B
            ("B", "D"),      # B -> D
            ("C", "D"),      # C -> D
            ("D", "END"),    # D -> End
        ]

        for pred_code, succ_code in dependencies:
            response = await client.post(
                "/api/v1/dependencies",
                headers=headers,
                json={
                    "predecessor_id": activities[pred_code],
                    "successor_id": activities[succ_code],
                    "dependency_type": "FS",
                    "lag": 0,
                },
            )
            assert response.status_code == 201, f"Failed: {pred_code} -> {succ_code}"

        # Step 4: Calculate schedule
        schedule_response = await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=headers,
        )
        assert schedule_response.status_code == 200
        results = {r["activity_id"]: r for r in schedule_response.json()}

        # Step 5: Verify calculations
        # Critical path: Start(0) -> A(0-5) -> B(5-8) -> D(8-10) -> End(10)
        # Parallel:      Start(0) -> C(0-4) -> (wait for B) -> D(8-10)
        
        # A should be critical (on longest path)
        assert results[activities["A"]]["is_critical"] is True
        assert results[activities["A"]]["early_start"] == 0
        assert results[activities["A"]]["early_finish"] == 5
        
        # B should be critical
        assert results[activities["B"]]["is_critical"] is True
        assert results[activities["B"]]["early_start"] == 5
        assert results[activities["B"]]["early_finish"] == 8
        
        # C should have float (not critical)
        assert results[activities["C"]]["is_critical"] is False
        assert results[activities["C"]]["total_float"] > 0
        
        # D should be critical
        assert results[activities["D"]]["is_critical"] is True
        
        # Step 6: Get critical path
        critical_response = await client.get(
            f"/api/v1/schedule/critical-path/{program_id}",
            headers=headers,
        )
        assert critical_response.status_code == 200
        critical_ids = critical_response.json()
        
        # A, B, D should be on critical path
        assert activities["A"] in critical_ids
        assert activities["B"] in critical_ids
        assert activities["D"] in critical_ids
        # C should NOT be on critical path
        assert activities["C"] not in critical_ids

        # Step 7: Get duration
        duration_response = await client.get(
            f"/api/v1/schedule/duration/{program_id}",
            headers=headers,
        )
        assert duration_response.status_code == 200
        assert duration_response.json()["duration"] == 10  # 5 + 3 + 2

    async def test_cycle_detection_prevents_invalid_dependency(
        self, client: AsyncClient, setup_user: tuple
    ):
        """Test that creating a circular dependency is prevented."""
        headers, _ = setup_user

        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            headers=headers,
            json={
                "name": "Cycle Test",
                "code": f"CYC-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        program_id = program_response.json()["id"]

        # Create 3 activities
        activity_ids = []
        for i, name in enumerate(["A", "B", "C"]):
            response = await client.post(
                "/api/v1/activities",
                headers=headers,
                json={
                    "program_id": program_id,
                    "name": f"Activity {name}",
                    "code": name,
                    "duration": 5,
                },
            )
            activity_ids.append(response.json()["id"])

        # Create A -> B
        await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
            },
        )

        # Create B -> C
        await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[1],
                "successor_id": activity_ids[2],
            },
        )

        # Try to create C -> A (would create cycle)
        response = await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[2],
                "successor_id": activity_ids[0],
            },
        )
        
        assert response.status_code == 400
        assert "CIRCULAR_DEPENDENCY" in response.json()["code"]
```

## Verification
```bash
cd api
pytest tests/integration/test_week2_e2e.py -v
pytest --cov=src --cov-report=term-missing --cov-fail-under=60
```

## Git Workflow
```bash
git checkout -b feature/week2-e2e-test
git add .
git commit -m "test(e2e): add comprehensive Week 2 integration tests

- Complete schedule workflow test
- Cycle detection test
- Critical path verification
- Float calculation validation"

git push -u origin feature/week2-e2e-test
```
```

---

## Week 2 Completion Checklist

After completing all prompts:

- [ ] Hotfix 2.0.1 merged - Model alignment fixed
- [ ] Activity CRUD with auth working
- [ ] Activity tests comprehensive (80%+ coverage for activities)
- [ ] Dependency CRUD with cycle detection
- [ ] Schedule calculation endpoint working
- [ ] Critical path correctly identified
- [ ] All tests passing
- [ ] Coverage at 60%+ overall
- [ ] All PRs merged to main

## Running All Week 2 Tests

```bash
cd api

# Full verification
ruff check src tests --fix
ruff format src tests
mypy src --ignore-missing-imports

# All tests
pytest -v

# Coverage report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

---

*Document Version: 1.0*
*Created: January 2026*
