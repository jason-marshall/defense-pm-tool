"""Unit tests for EVMS Period repositories."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import hash_password
from src.models.enums import UserRole
from src.models.evms_period import EVMSPeriod, EVMSPeriodData, PeriodStatus
from src.models.program import Program
from src.models.user import User
from src.models.wbs import WBSElement
from src.repositories.evms_period import EVMSPeriodDataRepository, EVMSPeriodRepository


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        email=f"test_{uuid4().hex[:8]}@example.com",
        hashed_password=hash_password("TestPassword123!"),
        full_name="Test User",
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
        name="Test Program",
        code=f"TP-{uuid4().hex[:6]}",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        budget_at_completion=Decimal("1000000.00"),
        owner_id=test_user.id,
    )
    db_session.add(program)
    await db_session.flush()
    return program


@pytest_asyncio.fixture
async def test_wbs(db_session: AsyncSession, test_program: Program) -> WBSElement:
    """Create a test WBS element."""
    wbs = WBSElement(
        id=uuid4(),
        program_id=test_program.id,
        wbs_code="1.0",
        name="Test WBS",
        path="1",
        level=1,
        budget_at_completion=Decimal("500000.00"),
        is_control_account=True,
    )
    db_session.add(wbs)
    await db_session.flush()
    return wbs


class TestEVMSPeriodRepository:
    """Tests for EVMSPeriodRepository."""

    @pytest.mark.asyncio
    async def test_create_period(
        self, db_session: AsyncSession, test_program: Program
    ):
        """Test creating an EVMS period."""
        repo = EVMSPeriodRepository(db_session)

        period = await repo.create({
            "program_id": test_program.id,
            "period_start": date(2024, 1, 1),
            "period_end": date(2024, 1, 31),
            "period_name": "January 2024",
            "status": PeriodStatus.DRAFT,
        })

        assert period.id is not None
        assert period.program_id == test_program.id
        assert period.period_name == "January 2024"
        assert period.status == PeriodStatus.DRAFT

    @pytest.mark.asyncio
    async def test_get_by_program(
        self, db_session: AsyncSession, test_program: Program
    ):
        """Test getting periods by program."""
        repo = EVMSPeriodRepository(db_session)

        # Create multiple periods
        await repo.create({
            "program_id": test_program.id,
            "period_start": date(2024, 1, 1),
            "period_end": date(2024, 1, 31),
            "period_name": "January 2024",
            "status": PeriodStatus.APPROVED,
        })
        await repo.create({
            "program_id": test_program.id,
            "period_start": date(2024, 2, 1),
            "period_end": date(2024, 2, 29),
            "period_name": "February 2024",
            "status": PeriodStatus.DRAFT,
        })

        await db_session.flush()

        # Get all periods
        periods = await repo.get_by_program(test_program.id)
        assert len(periods) == 2

        # Get by status
        approved = await repo.get_by_program(test_program.id, status=PeriodStatus.APPROVED)
        assert len(approved) == 1
        assert approved[0].period_name == "January 2024"

    @pytest.mark.asyncio
    async def test_get_by_program_with_pagination(
        self, db_session: AsyncSession, test_program: Program
    ):
        """Test pagination in get_by_program."""
        repo = EVMSPeriodRepository(db_session)

        # Create 5 periods
        for i in range(5):
            await repo.create({
                "program_id": test_program.id,
                "period_start": date(2024, i + 1, 1),
                "period_end": date(2024, i + 1, 28),
                "period_name": f"Period {i + 1}",
                "status": PeriodStatus.DRAFT,
            })

        await db_session.flush()

        # Test pagination
        page1 = await repo.get_by_program(test_program.id, skip=0, limit=2)
        assert len(page1) == 2

        page2 = await repo.get_by_program(test_program.id, skip=2, limit=2)
        assert len(page2) == 2

    @pytest.mark.asyncio
    async def test_get_latest_period(
        self, db_session: AsyncSession, test_program: Program
    ):
        """Test getting the latest period."""
        repo = EVMSPeriodRepository(db_session)

        # Create periods with different end dates
        await repo.create({
            "program_id": test_program.id,
            "period_start": date(2024, 1, 1),
            "period_end": date(2024, 1, 31),
            "period_name": "January 2024",
        })
        await repo.create({
            "program_id": test_program.id,
            "period_start": date(2024, 3, 1),
            "period_end": date(2024, 3, 31),
            "period_name": "March 2024",
        })
        await repo.create({
            "program_id": test_program.id,
            "period_start": date(2024, 2, 1),
            "period_end": date(2024, 2, 29),
            "period_name": "February 2024",
        })

        await db_session.flush()

        latest = await repo.get_latest_period(test_program.id)
        assert latest is not None
        assert latest.period_name == "March 2024"

    @pytest.mark.asyncio
    async def test_get_latest_period_none(
        self, db_session: AsyncSession, test_program: Program
    ):
        """Test getting latest period when none exist."""
        repo = EVMSPeriodRepository(db_session)

        latest = await repo.get_latest_period(test_program.id)
        assert latest is None

    @pytest.mark.asyncio
    async def test_get_by_date_range(
        self, db_session: AsyncSession, test_program: Program
    ):
        """Test getting periods by date range."""
        repo = EVMSPeriodRepository(db_session)

        # Create periods
        await repo.create({
            "program_id": test_program.id,
            "period_start": date(2024, 1, 1),
            "period_end": date(2024, 1, 31),
            "period_name": "January 2024",
        })
        await repo.create({
            "program_id": test_program.id,
            "period_start": date(2024, 2, 1),
            "period_end": date(2024, 2, 29),
            "period_name": "February 2024",
        })
        await repo.create({
            "program_id": test_program.id,
            "period_start": date(2024, 3, 1),
            "period_end": date(2024, 3, 31),
            "period_name": "March 2024",
        })

        await db_session.flush()

        # Get periods in Q1
        periods = await repo.get_by_date_range(
            test_program.id,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 2, 15),
        )
        assert len(periods) == 2  # January and February overlap

    @pytest.mark.asyncio
    async def test_period_exists(
        self, db_session: AsyncSession, test_program: Program
    ):
        """Test checking if period exists."""
        repo = EVMSPeriodRepository(db_session)

        period = await repo.create({
            "program_id": test_program.id,
            "period_start": date(2024, 1, 1),
            "period_end": date(2024, 1, 31),
            "period_name": "January 2024",
        })

        await db_session.flush()

        # Same dates should exist
        exists = await repo.period_exists(
            test_program.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
        )
        assert exists is True

        # Different dates should not exist
        exists = await repo.period_exists(
            test_program.id,
            period_start=date(2024, 2, 1),
            period_end=date(2024, 2, 29),
        )
        assert exists is False

        # Exclude self should return False
        exists = await repo.period_exists(
            test_program.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            exclude_id=period.id,
        )
        assert exists is False


class TestEVMSPeriodDataRepository:
    """Tests for EVMSPeriodDataRepository."""

    @pytest_asyncio.fixture
    async def test_period(
        self, db_session: AsyncSession, test_program: Program
    ) -> EVMSPeriod:
        """Create a test period."""
        period = EVMSPeriod(
            id=uuid4(),
            program_id=test_program.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            period_name="January 2024",
            status=PeriodStatus.DRAFT,
        )
        db_session.add(period)
        await db_session.flush()
        return period

    @pytest.mark.asyncio
    async def test_create_period_data(
        self, db_session: AsyncSession, test_period: EVMSPeriod, test_wbs: WBSElement
    ):
        """Test creating period data."""
        repo = EVMSPeriodDataRepository(db_session)

        data = await repo.create({
            "period_id": test_period.id,
            "wbs_id": test_wbs.id,
            "bcws": Decimal("100000.00"),
            "bcwp": Decimal("95000.00"),
            "acwp": Decimal("90000.00"),
            "cumulative_bcws": Decimal("100000.00"),
            "cumulative_bcwp": Decimal("95000.00"),
            "cumulative_acwp": Decimal("90000.00"),
        })

        assert data.id is not None
        assert data.period_id == test_period.id
        assert data.wbs_id == test_wbs.id

    @pytest.mark.asyncio
    async def test_get_by_period(
        self, db_session: AsyncSession, test_period: EVMSPeriod, test_wbs: WBSElement
    ):
        """Test getting data by period."""
        repo = EVMSPeriodDataRepository(db_session)

        await repo.create({
            "period_id": test_period.id,
            "wbs_id": test_wbs.id,
            "bcws": Decimal("100000.00"),
            "bcwp": Decimal("95000.00"),
            "acwp": Decimal("90000.00"),
            "cumulative_bcws": Decimal("100000.00"),
            "cumulative_bcwp": Decimal("95000.00"),
            "cumulative_acwp": Decimal("90000.00"),
        })

        await db_session.flush()

        data_list = await repo.get_by_period(test_period.id)
        assert len(data_list) == 1

    @pytest.mark.asyncio
    async def test_get_by_wbs(
        self, db_session: AsyncSession, test_program: Program, test_wbs: WBSElement
    ):
        """Test getting data by WBS element."""
        period_repo = EVMSPeriodRepository(db_session)
        data_repo = EVMSPeriodDataRepository(db_session)

        # Create multiple periods with same WBS
        period1 = await period_repo.create({
            "program_id": test_program.id,
            "period_start": date(2024, 1, 1),
            "period_end": date(2024, 1, 31),
            "period_name": "January 2024",
        })
        period2 = await period_repo.create({
            "program_id": test_program.id,
            "period_start": date(2024, 2, 1),
            "period_end": date(2024, 2, 29),
            "period_name": "February 2024",
        })

        await data_repo.create({
            "period_id": period1.id,
            "wbs_id": test_wbs.id,
            "bcws": Decimal("100000.00"),
            "bcwp": Decimal("95000.00"),
            "acwp": Decimal("90000.00"),
            "cumulative_bcws": Decimal("100000.00"),
            "cumulative_bcwp": Decimal("95000.00"),
            "cumulative_acwp": Decimal("90000.00"),
        })
        await data_repo.create({
            "period_id": period2.id,
            "wbs_id": test_wbs.id,
            "bcws": Decimal("50000.00"),
            "bcwp": Decimal("48000.00"),
            "acwp": Decimal("45000.00"),
            "cumulative_bcws": Decimal("150000.00"),
            "cumulative_bcwp": Decimal("143000.00"),
            "cumulative_acwp": Decimal("135000.00"),
        })

        await db_session.flush()

        data_list = await data_repo.get_by_wbs(test_wbs.id)
        assert len(data_list) == 2

    @pytest.mark.asyncio
    async def test_get_by_period_and_wbs(
        self, db_session: AsyncSession, test_period: EVMSPeriod, test_wbs: WBSElement
    ):
        """Test getting data by period and WBS."""
        repo = EVMSPeriodDataRepository(db_session)

        created_data = await repo.create({
            "period_id": test_period.id,
            "wbs_id": test_wbs.id,
            "bcws": Decimal("100000.00"),
            "bcwp": Decimal("95000.00"),
            "acwp": Decimal("90000.00"),
            "cumulative_bcws": Decimal("100000.00"),
            "cumulative_bcwp": Decimal("95000.00"),
            "cumulative_acwp": Decimal("90000.00"),
        })

        await db_session.flush()

        data = await repo.get_by_period_and_wbs(test_period.id, test_wbs.id)
        assert data is not None
        assert data.id == created_data.id

        # Non-existent should return None
        data = await repo.get_by_period_and_wbs(test_period.id, uuid4())
        assert data is None

    @pytest.mark.asyncio
    async def test_data_exists(
        self, db_session: AsyncSession, test_period: EVMSPeriod, test_wbs: WBSElement
    ):
        """Test checking if data exists."""
        repo = EVMSPeriodDataRepository(db_session)

        data = await repo.create({
            "period_id": test_period.id,
            "wbs_id": test_wbs.id,
            "bcws": Decimal("100000.00"),
            "bcwp": Decimal("95000.00"),
            "acwp": Decimal("90000.00"),
            "cumulative_bcws": Decimal("100000.00"),
            "cumulative_bcwp": Decimal("95000.00"),
            "cumulative_acwp": Decimal("90000.00"),
        })

        await db_session.flush()

        exists = await repo.data_exists(test_period.id, test_wbs.id)
        assert exists is True

        exists = await repo.data_exists(test_period.id, uuid4())
        assert exists is False

        # Exclude self
        exists = await repo.data_exists(test_period.id, test_wbs.id, exclude_id=data.id)
        assert exists is False

    @pytest.mark.asyncio
    async def test_update_cumulative_totals(
        self, db_session: AsyncSession, test_period: EVMSPeriod, test_wbs: WBSElement
    ):
        """Test updating cumulative totals from period data."""
        period_repo = EVMSPeriodRepository(db_session)
        data_repo = EVMSPeriodDataRepository(db_session)

        # Create period data
        await data_repo.create({
            "period_id": test_period.id,
            "wbs_id": test_wbs.id,
            "bcws": Decimal("100000.00"),
            "bcwp": Decimal("95000.00"),
            "acwp": Decimal("90000.00"),
            "cumulative_bcws": Decimal("100000.00"),
            "cumulative_bcwp": Decimal("95000.00"),
            "cumulative_acwp": Decimal("90000.00"),
        })

        await db_session.flush()

        # Update totals
        updated_period = await period_repo.update_cumulative_totals(test_period.id)
        assert updated_period is not None
        assert updated_period.cumulative_bcws == Decimal("100000.00")
        assert updated_period.cumulative_bcwp == Decimal("95000.00")
        assert updated_period.cumulative_acwp == Decimal("90000.00")

    @pytest.mark.asyncio
    async def test_update_cumulative_totals_not_found(
        self, db_session: AsyncSession
    ):
        """Test updating totals for non-existent period."""
        period_repo = EVMSPeriodRepository(db_session)
        result = await period_repo.update_cumulative_totals(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_previous_period_data(
        self, db_session: AsyncSession, test_program: Program, test_wbs: WBSElement
    ):
        """Test getting previous period data."""
        period_repo = EVMSPeriodRepository(db_session)
        data_repo = EVMSPeriodDataRepository(db_session)

        # Create first period
        period1 = await period_repo.create({
            "program_id": test_program.id,
            "period_start": date(2024, 1, 1),
            "period_end": date(2024, 1, 31),
            "period_name": "January 2024",
        })

        # Create data for first period
        await data_repo.create({
            "period_id": period1.id,
            "wbs_id": test_wbs.id,
            "bcws": Decimal("100000.00"),
            "bcwp": Decimal("95000.00"),
            "acwp": Decimal("90000.00"),
            "cumulative_bcws": Decimal("100000.00"),
            "cumulative_bcwp": Decimal("95000.00"),
            "cumulative_acwp": Decimal("90000.00"),
        })

        await db_session.flush()

        # Get previous data (should find January data when looking before February)
        prev_data = await data_repo.get_previous_period_data(
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            before_date=date(2024, 2, 15),
        )
        assert prev_data is not None
        assert prev_data.bcws == Decimal("100000.00")

        # Get previous data before January (should be None)
        no_data = await data_repo.get_previous_period_data(
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            before_date=date(2024, 1, 1),
        )
        assert no_data is None

    @pytest.mark.asyncio
    async def test_bulk_create_for_period(
        self, db_session: AsyncSession, test_period: EVMSPeriod, test_wbs: WBSElement
    ):
        """Test bulk creating period data."""
        data_repo = EVMSPeriodDataRepository(db_session)

        data_items = [
            {
                "wbs_id": test_wbs.id,
                "bcws": Decimal("50000.00"),
                "bcwp": Decimal("48000.00"),
                "acwp": Decimal("45000.00"),
                "cumulative_bcws": Decimal("50000.00"),
                "cumulative_bcwp": Decimal("48000.00"),
                "cumulative_acwp": Decimal("45000.00"),
            }
        ]

        records = await data_repo.bulk_create_for_period(
            period_id=test_period.id,
            data_items=data_items,
        )

        assert len(records) == 1
        assert records[0].bcws == Decimal("50000.00")
        assert records[0].period_id == test_period.id
