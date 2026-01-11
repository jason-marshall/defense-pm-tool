"""Async SQLAlchemy database configuration and session management."""

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.config import settings

logger = structlog.get_logger(__name__)

# Global engine instance - initialized on startup
_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """
    Get the async SQLAlchemy engine.

    Returns:
        The configured AsyncEngine instance.

    Raises:
        RuntimeError: If engine has not been initialized.
    """
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Get the async session maker.

    Returns:
        The configured async_sessionmaker instance.

    Raises:
        RuntimeError: If session maker has not been initialized.
    """
    if _async_session_maker is None:
        raise RuntimeError("Session maker not initialized. Call init_engine() first.")
    return _async_session_maker


async def init_engine() -> AsyncEngine:
    """
    Initialize the async SQLAlchemy engine and session maker.

    Creates the engine with connection pool configured according to settings.
    This should be called during application startup.

    Returns:
        The initialized AsyncEngine instance.
    """
    global _engine, _async_session_maker

    if _engine is not None:
        logger.warning("database_engine_already_initialized")
        return _engine

    logger.info(
        "initializing_database_engine",
        pool_min_size=settings.DATABASE_POOL_MIN_SIZE,
        pool_max_size=settings.DATABASE_POOL_MAX_SIZE,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
    )

    # Create async engine with asyncpg driver
    _engine = create_async_engine(
        settings.database_url_async,
        pool_size=settings.DATABASE_POOL_MIN_SIZE,
        max_overflow=settings.DATABASE_POOL_MAX_SIZE - settings.DATABASE_POOL_MIN_SIZE,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        pool_pre_ping=True,  # Verify connections before use
        echo=settings.DATABASE_ECHO,
    )

    # Create async session factory
    _async_session_maker = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    logger.info("database_engine_initialized")
    return _engine


async def dispose_engine() -> None:
    """
    Dispose of the async SQLAlchemy engine.

    Closes all connections in the connection pool.
    This should be called during application shutdown.
    """
    global _engine, _async_session_maker

    if _engine is not None:
        logger.info("disposing_database_engine")
        await _engine.dispose()
        _engine = None
        _async_session_maker = None
        logger.info("database_engine_disposed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.

    Yields a new session for each request and handles cleanup.
    Automatically rolls back on exception and closes the session.

    Yields:
        AsyncSession: A database session for the request.

    Example:
        ```python
        @router.get("/items")
        async def get_items(db: DbSession):
            result = await db.execute(select(Item))
            return result.scalars().all()
        ```
    """
    session_maker = get_session_maker()

    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def create_test_engine(database_url: str | None = None) -> AsyncEngine:
    """
    Create an async engine for testing.

    Uses NullPool to avoid connection pooling issues in tests.

    Args:
        database_url: Optional database URL. If not provided, uses
            an in-memory SQLite database.

    Returns:
        An AsyncEngine configured for testing.
    """
    url = database_url or "sqlite+aiosqlite:///:memory:"

    return create_async_engine(
        url,
        poolclass=NullPool,
        echo=False,
    )


def create_test_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Create an async session maker for testing.

    Args:
        engine: The AsyncEngine to bind to.

    Returns:
        An async_sessionmaker configured for testing.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
