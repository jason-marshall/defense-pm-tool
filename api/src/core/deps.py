"""FastAPI dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db

# Type alias for database session dependency injection
# Usage: async def endpoint(db: DbSession): ...
DbSession = Annotated[AsyncSession, Depends(get_db)]
