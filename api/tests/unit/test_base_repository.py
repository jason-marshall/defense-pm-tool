"""Unit tests for BaseRepository methods."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.exceptions import ConflictError, NotFoundError
from src.models.activity import Activity
from src.repositories.base import BaseRepository


class MockModel:
    """Mock SQLAlchemy model for testing."""

    __name__ = "MockModel"

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.name = kwargs.get("name", "test")
        self.deleted_at = kwargs.get("deleted_at")
        self.updated_at = kwargs.get("updated_at")


class TestBaseRepositoryApplyOrdering:
    """Tests for _apply_ordering method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    def test_apply_ordering_ascending(self, repo):
        """Should apply ascending order."""
        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query

        result = repo._apply_ordering(mock_query, "name")

        mock_query.order_by.assert_called_once()

    def test_apply_ordering_descending(self, repo):
        """Should apply descending order with - prefix."""
        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query

        result = repo._apply_ordering(mock_query, "-name")

        mock_query.order_by.assert_called_once()

    def test_apply_ordering_none(self, repo):
        """Should not modify query when order_by is None."""
        mock_query = MagicMock()

        result = repo._apply_ordering(mock_query, None)

        mock_query.order_by.assert_not_called()
        assert result == mock_query

    def test_apply_ordering_invalid_column(self, repo):
        """Should not modify query for non-existent column."""
        mock_query = MagicMock()

        result = repo._apply_ordering(mock_query, "nonexistent_column")

        mock_query.order_by.assert_not_called()


class TestBaseRepositoryApplyFilters:
    """Tests for _apply_filters method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    def test_apply_filters_none(self, repo):
        """Should not modify query when filters is None."""
        mock_query = MagicMock()

        result = repo._apply_filters(mock_query, None)

        assert result == mock_query

    def test_apply_filters_empty(self, repo):
        """Should not modify query when filters is empty."""
        mock_query = MagicMock()

        result = repo._apply_filters(mock_query, {})

        assert result == mock_query

    def test_apply_filters_valid_field(self, repo):
        """Should apply filter for valid field."""
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query

        result = repo._apply_filters(mock_query, {"name": "test"})

        mock_query.where.assert_called_once()

    def test_apply_filters_null_value(self, repo):
        """Should skip filter when value is None."""
        mock_query = MagicMock()

        result = repo._apply_filters(mock_query, {"name": None})

        mock_query.where.assert_not_called()


class TestBaseRepositoryGet:
    """Tests for get method (alias for get_by_id)."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_get_found(self, repo, mock_session):
        """Should return model when found."""
        record_id = uuid4()
        mock_activity = Activity(
            id=record_id,
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_activity
        mock_session.execute.return_value = mock_result

        result = await repo.get(record_id)

        assert result == mock_activity

    @pytest.mark.asyncio
    async def test_get_not_found(self, repo, mock_session):
        """Should return None when not found."""
        record_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get(record_id)

        assert result is None


class TestBaseRepositoryGetAll:
    """Tests for get_all method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_get_all_returns_items_and_count(self, repo, mock_session):
        """Should return items and total count."""
        mock_activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
        )

        # First call for count, second for items
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = [mock_activity]

        mock_session.execute.side_effect = [mock_count_result, mock_items_result]

        items, total = await repo.get_all()

        assert items == [mock_activity]
        assert total == 1


class TestBaseRepositoryCount:
    """Tests for count method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_count_returns_count(self, repo, mock_session):
        """Should return count of records."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 10
        mock_session.execute.return_value = mock_result

        result = await repo.count()

        assert result == 10

    @pytest.mark.asyncio
    async def test_count_with_filters(self, repo, mock_session):
        """Should apply filters to count."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_session.execute.return_value = mock_result

        result = await repo.count(filters={"name": "test"})

        assert result == 5


class TestBaseRepositoryCreate:
    """Tests for create method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_create_success(self, repo, mock_session):
        """Should create a new record."""
        data = {
            "program_id": uuid4(),
            "code": "ACT-001",
            "name": "Test Activity",
            "duration": 5,
        }

        result = await repo.create(data)

        assert result.code == "ACT-001"
        assert result.name == "Test Activity"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_integrity_error(self, repo, mock_session):
        """Should raise ConflictError on integrity violation."""
        data = {
            "program_id": uuid4(),
            "code": "ACT-001",
            "name": "Test Activity",
            "duration": 5,
        }

        mock_session.flush.side_effect = IntegrityError(
            "Duplicate key", params=None, orig=Exception("Duplicate")
        )

        with pytest.raises(ConflictError):
            await repo.create(data)

        mock_session.rollback.assert_called_once()


class TestBaseRepositoryUpdate:
    """Tests for update method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_update_success(self, repo, mock_session):
        """Should update record with new data."""
        existing = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Original",
            duration=5,
        )

        result = await repo.update(existing, {"name": "Updated", "duration": 10})

        assert existing.name == "Updated"
        assert existing.duration == 10
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_integrity_error(self, repo, mock_session):
        """Should raise ConflictError on integrity violation."""
        existing = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Original",
            duration=5,
        )

        mock_session.flush.side_effect = IntegrityError(
            "Duplicate key", params=None, orig=Exception("Duplicate")
        )

        with pytest.raises(ConflictError):
            await repo.update(existing, {"code": "ACT-DUP"})


class TestBaseRepositoryDelete:
    """Tests for delete method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_delete_soft_success(self, repo, mock_session):
        """Should soft delete by setting deleted_at."""
        record_id = uuid4()
        existing = Activity(
            id=record_id,
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
        )

        with patch.object(repo, "get_by_id", new_callable=AsyncMock, return_value=existing):
            result = await repo.delete(record_id, soft=True)

        assert result is True
        assert existing.deleted_at is not None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo, mock_session):
        """Should return False when record not found."""
        record_id = uuid4()

        with patch.object(repo, "get_by_id", new_callable=AsyncMock, return_value=None):
            result = await repo.delete(record_id)

        assert result is False


class TestBaseRepositoryHardDelete:
    """Tests for hard_delete method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_hard_delete(self, repo, mock_session):
        """Should permanently delete record."""
        existing = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
        )

        await repo.hard_delete(existing)

        mock_session.delete.assert_called_once_with(existing)
        mock_session.flush.assert_called_once()


class TestBaseRepositoryRestore:
    """Tests for restore method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_restore_success(self, repo, mock_session):
        """Should restore soft-deleted record."""
        record_id = uuid4()
        existing = Activity(
            id=record_id,
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
            deleted_at=datetime.now(timezone.utc),
        )

        with patch.object(repo, "get_by_id", new_callable=AsyncMock, return_value=existing):
            result = await repo.restore(record_id)

        assert result == existing
        assert existing.deleted_at is None

    @pytest.mark.asyncio
    async def test_restore_not_found(self, repo, mock_session):
        """Should return None when record not found."""
        record_id = uuid4()

        with patch.object(repo, "get_by_id", new_callable=AsyncMock, return_value=None):
            result = await repo.restore(record_id)

        assert result is None


class TestBaseRepositoryExists:
    """Tests for exists method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_exists_true(self, repo, mock_session):
        """Should return True when record exists."""
        record_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 1
        mock_session.execute.return_value = mock_result

        result = await repo.exists(record_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, repo, mock_session):
        """Should return False when record does not exist."""
        record_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        result = await repo.exists(record_id)

        assert result is False


class TestBaseRepositoryFindOne:
    """Tests for find_one method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_find_one_found(self, repo, mock_session):
        """Should return matching record."""
        mock_activity = Activity(
            id=uuid4(),
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_activity
        mock_session.execute.return_value = mock_result

        result = await repo.find_one({"code": "ACT-001"})

        assert result == mock_activity

    @pytest.mark.asyncio
    async def test_find_one_not_found(self, repo, mock_session):
        """Should return None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.find_one({"code": "NONEXISTENT"})

        assert result is None


class TestBaseRepositoryFindMany:
    """Tests for find_many method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_find_many_returns_list(self, repo, mock_session):
        """Should return list of matching records."""
        activities = [
            Activity(
                id=uuid4(),
                program_id=uuid4(),
                code=f"ACT-{i:03d}",
                name=f"Test {i}",
                duration=5,
            )
            for i in range(3)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = activities
        mock_session.execute.return_value = mock_result

        result = await repo.find_many({"duration": 5})

        assert result == activities


class TestBaseRepositoryGetOrRaise:
    """Tests for get_or_raise method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_get_or_raise_found(self, repo, mock_session):
        """Should return record when found."""
        record_id = uuid4()
        mock_activity = Activity(
            id=record_id,
            program_id=uuid4(),
            code="ACT-001",
            name="Test",
            duration=5,
        )

        with patch.object(repo, "get_by_id", new_callable=AsyncMock, return_value=mock_activity):
            result = await repo.get_or_raise(record_id)

        assert result == mock_activity

    @pytest.mark.asyncio
    async def test_get_or_raise_not_found(self, repo, mock_session):
        """Should raise NotFoundError when not found."""
        record_id = uuid4()

        with patch.object(repo, "get_by_id", new_callable=AsyncMock, return_value=None):
            with pytest.raises(NotFoundError) as exc_info:
                await repo.get_or_raise(record_id)

        assert "Activity" in str(exc_info.value)


class TestBaseRepositoryBulkCreate:
    """Tests for bulk_create method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_bulk_create_empty(self, repo, mock_session):
        """Should return empty list for empty input."""
        result = await repo.bulk_create([])

        assert result == []
        mock_session.add_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_create_success(self, repo, mock_session):
        """Should create multiple records."""
        items = [
            {
                "program_id": uuid4(),
                "code": f"ACT-{i:03d}",
                "name": f"Activity {i}",
                "duration": 5,
            }
            for i in range(3)
        ]

        result = await repo.bulk_create(items)

        assert len(result) == 3
        mock_session.add_all.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_integrity_error(self, repo, mock_session):
        """Should raise ConflictError on integrity violation."""
        items = [
            {
                "program_id": uuid4(),
                "code": "ACT-001",
                "name": "Activity",
                "duration": 5,
            }
        ]

        mock_session.flush.side_effect = IntegrityError(
            "Duplicate key", params=None, orig=Exception("Duplicate")
        )

        with pytest.raises(ConflictError):
            await repo.bulk_create(items)


class TestBaseRepositoryBulkUpdate:
    """Tests for bulk_update method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_bulk_update_empty(self, repo, mock_session):
        """Should return 0 for empty input."""
        result = await repo.bulk_update([])

        assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_update_success(self, repo, mock_session):
        """Should update multiple records."""
        updates = [
            (uuid4(), {"name": "Updated 1"}),
            (uuid4(), {"name": "Updated 2"}),
        ]

        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_session.execute.return_value = mock_cursor

        result = await repo.bulk_update(updates)

        assert result == 2


class TestBaseRepositoryBulkDelete:
    """Tests for bulk_delete method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaseRepository(Activity, mock_session)

    @pytest.mark.asyncio
    async def test_bulk_delete_empty(self, repo, mock_session):
        """Should return 0 for empty input."""
        result = await repo.bulk_delete([])

        assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_delete_soft(self, repo, mock_session):
        """Should soft delete multiple records."""
        ids = [uuid4(), uuid4(), uuid4()]

        mock_cursor = MagicMock()
        mock_cursor.rowcount = 3
        mock_session.execute.return_value = mock_cursor

        result = await repo.bulk_delete(ids, soft=True)

        assert result == 3
