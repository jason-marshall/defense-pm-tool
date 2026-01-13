"""Unit tests for WBS repository."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import hash_password
from src.models.enums import UserRole
from src.models.program import Program
from src.models.user import User
from src.models.wbs import WBSElement
from src.repositories.wbs import WBSElementRepository


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        email=f"wbs_test_{uuid4().hex[:8]}@example.com",
        hashed_password=hash_password("TestPassword123!"),
        full_name="WBS Test User",
        is_active=True,
        role=UserRole.PROGRAM_MANAGER,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_program(db_session: AsyncSession, test_user: User) -> Program:
    """Create a test program."""
    program = Program(
        id=uuid4(),
        name="WBS Test Program",
        code=f"WTP-{uuid4().hex[:6]}",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        budget_at_completion=Decimal("1000000.00"),
        owner_id=test_user.id,
    )
    db_session.add(program)
    await db_session.flush()
    return program


@pytest_asyncio.fixture
async def wbs_hierarchy(db_session: AsyncSession, test_program: Program) -> list[WBSElement]:
    """Create a WBS hierarchy for testing."""
    root = WBSElement(
        id=uuid4(),
        program_id=test_program.id,
        wbs_code="1.0",
        name="Root Element",
        path="1",
        level=1,
        budget_at_completion=Decimal("1000000.00"),
        is_control_account=False,
    )
    db_session.add(root)
    await db_session.flush()

    child1 = WBSElement(
        id=uuid4(),
        program_id=test_program.id,
        parent_id=root.id,
        wbs_code="1.1",
        name="Child 1",
        path="1.1",
        level=2,
        budget_at_completion=Decimal("500000.00"),
        is_control_account=True,
    )
    db_session.add(child1)

    child2 = WBSElement(
        id=uuid4(),
        program_id=test_program.id,
        parent_id=root.id,
        wbs_code="1.2",
        name="Child 2",
        path="1.2",
        level=2,
        budget_at_completion=Decimal("500000.00"),
        is_control_account=True,
    )
    db_session.add(child2)

    await db_session.flush()
    return [root, child1, child2]


class TestWBSElementRepository:
    """Tests for WBS Repository."""

    @pytest.mark.asyncio
    async def test_get_root_elements(
        self, db_session: AsyncSession, test_program: Program, wbs_hierarchy: list[WBSElement]
    ):
        """Test getting root WBS elements."""
        repo = WBSElementRepository(db_session)
        roots = await repo.get_root_elements(test_program.id)
        assert len(roots) == 1
        assert roots[0].name == "Root Element"

    @pytest.mark.asyncio
    async def test_get_children(
        self, db_session: AsyncSession, wbs_hierarchy: list[WBSElement]
    ):
        """Test getting child elements."""
        repo = WBSElementRepository(db_session)
        root = wbs_hierarchy[0]
        children = await repo.get_children(root.id)
        assert len(children) == 2

    @pytest.mark.asyncio
    async def test_get_with_children(
        self, db_session: AsyncSession, wbs_hierarchy: list[WBSElement]
    ):
        """Test getting element with children loaded."""
        repo = WBSElementRepository(db_session)
        root = wbs_hierarchy[0]
        element = await repo.get_with_children(root.id)
        assert element is not None
        assert len(element.children) == 2

    @pytest.mark.asyncio
    async def test_get_by_code(
        self, db_session: AsyncSession, test_program: Program, wbs_hierarchy: list[WBSElement]
    ):
        """Test getting element by code."""
        repo = WBSElementRepository(db_session)
        element = await repo.get_by_code(test_program.id, "1.1")
        assert element is not None
        assert element.name == "Child 1"

        # Non-existent code
        element = await repo.get_by_code(test_program.id, "9.9")
        assert element is None

    @pytest.mark.asyncio
    async def test_get_descendants(
        self, db_session: AsyncSession, wbs_hierarchy: list[WBSElement]
    ):
        """Test getting all descendants."""
        repo = WBSElementRepository(db_session)
        root = wbs_hierarchy[0]
        descendants = await repo.get_descendants(root.id)
        assert len(descendants) == 2

    @pytest.mark.asyncio
    async def test_get_descendants_not_found(
        self, db_session: AsyncSession
    ):
        """Test getting descendants of non-existent element."""
        repo = WBSElementRepository(db_session)
        descendants = await repo.get_descendants(uuid4())
        assert len(descendants) == 0

    @pytest.mark.asyncio
    async def test_get_tree(
        self, db_session: AsyncSession, test_program: Program, wbs_hierarchy: list[WBSElement]
    ):
        """Test getting full WBS tree."""
        repo = WBSElementRepository(db_session)
        tree = await repo.get_tree(test_program.id)
        assert len(tree) == 1  # Only root elements
        assert tree[0].name == "Root Element"
