"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


DataT = TypeVar("DataT")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
    )


class PaginatedResponse(BaseSchema, Generic[DataT]):
    """Generic paginated response schema."""

    items: list[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseSchema):
    """Error response schema."""

    detail: str
    timestamp: datetime = datetime.now()
