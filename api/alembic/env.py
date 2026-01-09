"""Alembic environment configuration for async migrations.

This module configures Alembic to work with:
- Async SQLAlchemy engine (asyncpg driver)
- All application models for autogenerate support
- Database URL from application settings
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Add the api/src directory to the path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.models.base import Base

# Import ALL models to ensure they are registered with Base.metadata
# This is critical for autogenerate to detect all tables
from src.models import (  # noqa: F401
    Activity,
    ConstraintType,
    Dependency,
    DependencyType,
    Program,
    ProgramStatus,
    User,
    UserRole,
    WBSElement,
)

# Alembic Config object - provides access to alembic.ini values
config = context.config

# Build the async database URL from settings
# Convert postgresql:// to postgresql+asyncpg:// for async driver
database_url = str(settings.DATABASE_URL)
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif not database_url.startswith("postgresql+asyncpg://"):
    database_url = f"postgresql+asyncpg://{database_url.split('://', 1)[-1]}"

config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model MetaData for autogenerate support
# Alembic will compare this metadata against the database schema
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects to include in migrations.

    Excludes system tables and other objects we don't want to manage.
    """
    # Skip PostgreSQL system schemas
    if hasattr(object, "schema") and object.schema in ("pg_catalog", "information_schema"):
        return False

    # Include all other objects
    return True


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Useful for generating SQL scripts without database connectivity.

    Calls to context.execute() emit SQL to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run migrations with the given synchronous connection.

    This is called by run_sync() from the async context.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
        # Render column types using PostgreSQL dialect
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in async mode using asyncpg.

    Creates an async engine, connects, and runs migrations
    synchronously within the async connection context.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Creates an async Engine and associates a connection with the context.
    Migrations are executed within a transaction.
    """
    # Handle Windows event loop policy for asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(run_async_migrations())


# Determine which mode to run migrations in
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
