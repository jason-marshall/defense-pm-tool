"""Tests for base repository operations."""

import pytest
from datetime import datetime, UTC
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.repositories.base import BaseRepository


class MockModel(Base):
    """Mock model for testing repository operations."""

    __tablename__ = "mock_models"

    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TestBaseRepositoryHelpers:
    """Tests for repository helper methods."""

    def test_apply_soft_delete_filter_excludes_deleted(self):
        """Should exclude deleted records by default."""
        from sqlalchemy import select

        # Create a mock session and repo
        class MockSession:
            pass

        repo = BaseRepository(MockModel, MockSession())
        query = select(MockModel)

        # Apply filter
        filtered = repo._apply_soft_delete_filter(query, include_deleted=False)

        # Check that a where clause was added
        assert str(filtered) != str(query)

    def test_apply_soft_delete_filter_includes_deleted(self):
        """Should include deleted records when requested."""
        from sqlalchemy import select

        class MockSession:
            pass

        repo = BaseRepository(MockModel, MockSession())
        query = select(MockModel)

        # Apply filter with include_deleted=True
        filtered = repo._apply_soft_delete_filter(query, include_deleted=True)

        # No filter should be added
        assert str(filtered) == str(query)

    def test_apply_ordering_ascending(self):
        """Should apply ascending order."""
        from sqlalchemy import select

        class MockSession:
            pass

        repo = BaseRepository(MockModel, MockSession())
        query = select(MockModel)

        # Apply ascending order
        ordered = repo._apply_ordering(query, "name")

        # Check that order by was added
        assert "ORDER BY" in str(ordered)

    def test_apply_ordering_descending(self):
        """Should apply descending order with - prefix."""
        from sqlalchemy import select

        class MockSession:
            pass

        repo = BaseRepository(MockModel, MockSession())
        query = select(MockModel)

        # Apply descending order
        ordered = repo._apply_ordering(query, "-name")

        # Check that order by was added with DESC
        assert "ORDER BY" in str(ordered)
        assert "DESC" in str(ordered)

    def test_apply_ordering_no_order(self):
        """Should not modify query when order_by is None."""
        from sqlalchemy import select

        class MockSession:
            pass

        repo = BaseRepository(MockModel, MockSession())
        query = select(MockModel)

        # Apply no ordering
        ordered = repo._apply_ordering(query, None)

        # Query should be unchanged
        assert str(ordered) == str(query)

    def test_apply_filters(self):
        """Should apply filters to query."""
        from sqlalchemy import select

        class MockSession:
            pass

        repo = BaseRepository(MockModel, MockSession())
        query = select(MockModel)

        # Apply filters
        filtered = repo._apply_filters(query, {"name": "test"})

        # Check that where clause was added
        assert "WHERE" in str(filtered)

    def test_apply_filters_none(self):
        """Should not modify query when filters is None."""
        from sqlalchemy import select

        class MockSession:
            pass

        repo = BaseRepository(MockModel, MockSession())
        query = select(MockModel)

        # Apply no filters
        filtered = repo._apply_filters(query, None)

        # Query should be unchanged
        assert str(filtered) == str(query)

    def test_apply_filters_ignores_invalid_field(self):
        """Should ignore filter for non-existent field."""
        from sqlalchemy import select

        class MockSession:
            pass

        repo = BaseRepository(MockModel, MockSession())
        query = select(MockModel)

        # Apply filter for non-existent field
        filtered = repo._apply_filters(query, {"nonexistent": "value"})

        # Query should be unchanged (no WHERE clause for invalid field)
        assert str(filtered) == str(query)

    def test_apply_ordering_ignores_invalid_field(self):
        """Should ignore order by for non-existent field."""
        from sqlalchemy import select

        class MockSession:
            pass

        repo = BaseRepository(MockModel, MockSession())
        query = select(MockModel)

        # Apply order by for non-existent field
        ordered = repo._apply_ordering(query, "nonexistent")

        # Query should be unchanged
        assert "ORDER BY" not in str(ordered)
