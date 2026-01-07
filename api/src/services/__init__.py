"""Business logic layer - Service pattern implementation."""

from typing import Generic, TypeVar

from ..models import Base
from ..repositories import BaseRepository


ModelT = TypeVar("ModelT", bound=Base)


class BaseService(Generic[ModelT]):
    """Base service with common business logic."""

    def __init__(self, repository: BaseRepository[ModelT]):
        """Initialize service."""
        self.repository = repository
