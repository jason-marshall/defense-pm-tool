"""Base Pydantic schema with common configuration.

This module provides base classes and mixins for Pydantic schemas.
All schemas should inherit from BaseSchema for consistent configuration.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """
    Base schema with common configuration for all schemas.

    Configuration:
    - from_attributes: Enable ORM mode for SQLAlchemy model conversion
    - populate_by_name: Allow population by field name or alias
    - str_strip_whitespace: Automatically strip whitespace from strings
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampMixin(BaseModel):
    """
    Mixin for timestamp fields.

    Use with response schemas that need created_at/updated_at fields.
    """

    created_at: datetime
    updated_at: datetime


class IDMixin(BaseModel):
    """
    Mixin for UUID primary key field.

    Use with response schemas that need an id field.
    """

    id: UUID


class AuditMixin(IDMixin, TimestampMixin):
    """
    Combined mixin for id and timestamp fields.

    Convenience mixin combining IDMixin and TimestampMixin.
    Use with response schemas for full audit trail.
    """

    pass
