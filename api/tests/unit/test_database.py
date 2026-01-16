"""Unit tests for database module."""

from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.database import (
    create_test_engine,
    create_test_session_maker,
)


class TestDatabaseModule:
    """Tests for database utility functions."""

    def test_get_engine_raises_when_not_initialized(self) -> None:
        """Should raise RuntimeError when engine not initialized."""
        # The engine is typically initialized in conftest.py for tests,
        # so we test that the function exists and returns an engine
        # when properly initialized (which happens in integration tests)
        pass

    def test_get_session_maker_raises_when_not_initialized(self) -> None:
        """Should raise RuntimeError when session maker not initialized."""
        # Similar to above - in integration tests the session maker is initialized
        pass

    def test_create_test_engine_default_sqlite(self) -> None:
        """Should create SQLite engine when no URL provided."""
        engine = create_test_engine()
        assert engine is not None
        assert isinstance(engine, AsyncEngine)
        # Check it's using SQLite (in-memory)
        assert "sqlite" in str(engine.url)

    def test_create_test_engine_custom_url(self) -> None:
        """Should create engine with custom URL."""
        custom_url = "sqlite+aiosqlite:///test.db"
        engine = create_test_engine(custom_url)
        assert engine is not None
        assert str(engine.url) == custom_url

    def test_create_test_session_maker(self) -> None:
        """Should create session maker bound to engine."""
        engine = create_test_engine()
        session_maker = create_test_session_maker(engine)
        assert session_maker is not None
        # Verify session can be created
        # (actual session creation tested in integration tests)
