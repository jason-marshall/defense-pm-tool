"""Tests for base schema classes."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.schemas.base import AuditMixin, BaseSchema, IDMixin, TimestampMixin


class TestBaseSchema:
    """Tests for BaseSchema."""

    def test_base_schema_strips_whitespace(self):
        """Should strip whitespace from string fields."""

        class TestSchema(BaseSchema):
            name: str

        schema = TestSchema(name="  test  ")
        assert schema.name == "test"

    def test_base_schema_from_attributes(self):
        """Should support from_attributes for ORM conversion."""

        class MockModel:
            name = "test"

        class TestSchema(BaseSchema):
            name: str

        schema = TestSchema.model_validate(MockModel())
        assert schema.name == "test"


class TestTimestampMixin:
    """Tests for TimestampMixin."""

    def test_timestamp_mixin_fields(self):
        """Should have created_at and updated_at fields."""

        class TestSchema(TimestampMixin):
            pass

        now = datetime.now(UTC)
        schema = TestSchema(created_at=now, updated_at=now)
        assert schema.created_at == now
        assert schema.updated_at == now

    def test_timestamp_mixin_requires_fields(self):
        """Should require both timestamp fields."""

        class TestSchema(TimestampMixin):
            pass

        with pytest.raises(ValidationError):
            TestSchema()


class TestIDMixin:
    """Tests for IDMixin."""

    def test_id_mixin_uuid(self):
        """Should accept UUID for id field."""

        class TestSchema(IDMixin):
            pass

        id_val = uuid4()
        schema = TestSchema(id=id_val)
        assert schema.id == id_val

    def test_id_mixin_requires_id(self):
        """Should require id field."""

        class TestSchema(IDMixin):
            pass

        with pytest.raises(ValidationError):
            TestSchema()


class TestAuditMixin:
    """Tests for AuditMixin."""

    def test_audit_mixin_all_fields(self):
        """Should have id, created_at, and updated_at."""

        class TestSchema(AuditMixin):
            pass

        id_val = uuid4()
        now = datetime.now(UTC)
        schema = TestSchema(id=id_val, created_at=now, updated_at=now)
        assert schema.id == id_val
        assert schema.created_at == now
        assert schema.updated_at == now
