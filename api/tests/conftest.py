"""Pytest configuration and fixtures."""

import contextlib
import os
import tempfile
from collections.abc import AsyncGenerator
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Disable rate limiting for tests - must be set before importing app
os.environ["RATE_LIMIT_ENABLED"] = "false"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import Settings
from src.core.auth import hash_password
from src.core.deps import get_db
from src.main import app
from src.models.activity import Activity
from src.models.base import Base
from src.models.dependency import Dependency, DependencyType
from src.models.enums import UserRole
from src.models.program import Program
from src.models.user import User

# Test secret key (32+ characters required)
TEST_SECRET_KEY = "test-secret-key-for-testing-purposes-only-32chars"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Override settings for testing."""
    return Settings(
        DATABASE_URL="postgresql://test:test@localhost:5432/test",
        REDIS_URL="redis://localhost:6379/1",
        SECRET_KEY=TEST_SECRET_KEY,
        ENVIRONMENT="development",
        DEBUG=True,
    )


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async engine for testing using a unique temp file database."""
    # Create a unique temp file for each test to avoid state issues
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)  # Close the file descriptor, SQLite will handle the file

    db_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()

    # Clean up the temp file
    with contextlib.suppress(OSError):
        Path(db_path).unlink()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for testing."""
    session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, async_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing API endpoints."""
    import src.core.database as db_module

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Also set up the global session maker for health endpoints
    test_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    original_session_maker = db_module._async_session_maker
    db_module._async_session_maker = test_session_maker

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Clean up
    db_module._async_session_maker = original_session_maker
    app.dependency_overrides.clear()


# Auth helper fixtures


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, sample_user_data: dict) -> dict[str, str]:
    """
    Register a user and return auth headers with valid access token.

    Use this fixture when tests need authentication.
    """
    # Register user
    await client.post("/api/v1/auth/register", json=sample_user_data)

    # Login to get token
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"],
        },
    )
    token = login_response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(client: AsyncClient) -> dict[str, str]:
    """
    Register an admin user and return auth headers with valid access token.

    Use this fixture when tests need admin authentication.
    """
    admin_data = {
        "email": "admin@example.com",
        "password": "AdminPassword123!",
        "full_name": "Admin User",
    }

    # Register admin
    await client.post("/api/v1/auth/register", json=admin_data)

    # Update role to admin via direct database access
    # For tests, we need to manually set admin role after registration

    # Login to get token
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": admin_data["email"],
            "password": admin_data["password"],
        },
    )
    token = login_response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


# Model fixtures


@pytest.fixture
def sample_program_data() -> dict:
    """Sample program data for testing."""
    return {
        "name": "Test Program",
        "code": "TP-001",
        "description": "A test program for unit testing",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "budget_at_completion": "1000000.00",
        "contract_number": "CONTRACT-001",
    }


@pytest.fixture
def sample_program() -> Program:
    """Create a sample program instance."""
    return Program(
        id=uuid4(),
        name="Test Program",
        code="TP-001",
        description="A test program",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        budget_at_completion=Decimal("1000000.00"),
        owner_id=uuid4(),
    )


@pytest.fixture
def sample_activities() -> list[Activity]:
    """Create sample activities for CPM testing."""
    program_id = uuid4()
    return [
        Activity(
            id=uuid4(),
            program_id=program_id,
            name="Activity A",
            code="A",
            duration=5,
            budgeted_cost=Decimal("10000.00"),
        ),
        Activity(
            id=uuid4(),
            program_id=program_id,
            name="Activity B",
            code="B",
            duration=3,
            budgeted_cost=Decimal("8000.00"),
        ),
        Activity(
            id=uuid4(),
            program_id=program_id,
            name="Activity C",
            code="C",
            duration=2,
            budgeted_cost=Decimal("5000.00"),
        ),
    ]


@pytest.fixture
def sample_dependencies(sample_activities: list[Activity]) -> list[Dependency]:
    """Create sample dependencies for CPM testing (A -> B -> C)."""
    return [
        Dependency(
            id=uuid4(),
            predecessor_id=sample_activities[0].id,
            successor_id=sample_activities[1].id,
            dependency_type=DependencyType.FS.value,
            lag=0,
        ),
        Dependency(
            id=uuid4(),
            predecessor_id=sample_activities[1].id,
            successor_id=sample_activities[2].id,
            dependency_type=DependencyType.FS.value,
            lag=0,
        ),
    ]


# User fixtures for authentication testing


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data for testing registration."""
    return {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test User",
    }


@pytest.fixture
def sample_user() -> User:
    """Create a sample user instance (not saved to database)."""
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password=hash_password("SecurePassword123!"),
        full_name="Test User",
        is_active=True,
        role=UserRole.VIEWER,
    )


@pytest.fixture
def sample_admin_user() -> User:
    """Create a sample admin user instance (not saved to database)."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password=hash_password("AdminPassword123!"),
        full_name="Admin User",
        is_active=True,
        role=UserRole.ADMIN,
    )


@pytest.fixture
def inactive_user() -> User:
    """Create an inactive user instance (not saved to database)."""
    return User(
        id=uuid4(),
        email="inactive@example.com",
        hashed_password=hash_password("InactivePassword123!"),
        full_name="Inactive User",
        is_active=False,
        role=UserRole.VIEWER,
    )


@pytest_asyncio.fixture
async def test_program(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_program_data: dict,
) -> dict:
    """Create a test program via API and return its data."""
    response = await client.post(
        "/api/v1/programs",
        json=sample_program_data,
        headers=auth_headers,
    )
    return response.json()


@pytest_asyncio.fixture
async def test_activity(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_program: dict,
) -> dict:
    """Create a test activity via API and return its data."""
    activity_data = {
        "program_id": test_program["id"],
        "name": "Test Activity",
        "code": "ACT-001",
        "duration": 10,
        "budgeted_cost": "5000.00",
    }
    response = await client.post(
        "/api/v1/activities",
        json=activity_data,
        headers=auth_headers,
    )
    return response.json()
