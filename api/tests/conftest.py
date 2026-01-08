"""Pytest configuration and fixtures."""

from collections.abc import AsyncGenerator
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import Settings
from src.core.deps import get_db
from src.main import app
from src.models.base import Base
from src.models.activity import Activity
from src.models.dependency import Dependency, DependencyType
from src.models.program import Program


# Test database URL (use SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Override settings for testing."""
    return Settings(
        DATABASE_URL="postgresql://test:test@localhost:5432/test",
        REDIS_URL="redis://localhost:6379/1",
        SECRET_KEY="test-secret-key-do-not-use-in-production",
        ENVIRONMENT="development",
        DEBUG=True,
    )


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async engine for testing."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


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
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing API endpoints."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# Model fixtures

@pytest.fixture
def sample_program_data() -> dict:
    """Sample program data for testing."""
    return {
        "name": "Test Program",
        "code": "TP-001",
        "description": "A test program for unit testing",
        "planned_start_date": "2024-01-01",
        "planned_end_date": "2024-12-31",
        "budget_at_completion": "1000000.00",
        "contract_number": "CONTRACT-001",
        "contract_type": "FFP",
    }


@pytest.fixture
def sample_program() -> Program:
    """Create a sample program instance."""
    return Program(
        id=uuid4(),
        name="Test Program",
        code="TP-001",
        description="A test program",
        planned_start_date="2024-01-01",
        planned_end_date="2024-12-31",
        budget_at_completion=Decimal("1000000.00"),
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
