"""Unit tests for Activity model."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from src.models.activity import Activity
from src.models.enums import ActivityStatus, ConstraintType


class TestActivityModel:
    """Tests for Activity model class."""

    def test_activity_status_default(self):
        """Test default activity status."""
        assert ActivityStatus.NOT_STARTED.value == "not_started"

    def test_activity_constraint_types(self):
        """Test constraint type enum values."""
        assert ConstraintType.ASAP.value == "asap"
        assert ConstraintType.ALAP.value == "alap"

    def test_activity_status_values(self):
        """Test all activity status values."""
        assert ActivityStatus.NOT_STARTED.value == "not_started"
        assert ActivityStatus.IN_PROGRESS.value == "in_progress"
        assert ActivityStatus.COMPLETE.value == "complete"
        assert ActivityStatus.ON_HOLD.value == "on_hold"


class TestActivityEnumMethods:
    """Tests for Activity-related enum methods."""

    def test_constraint_type_asap(self):
        """Test ASAP constraint."""
        constraint = ConstraintType.ASAP
        assert constraint.value == "asap"

    def test_constraint_type_alap(self):
        """Test ALAP constraint."""
        constraint = ConstraintType.ALAP
        assert constraint.value == "alap"

    def test_activity_status_from_string(self):
        """Test creating status from string."""
        status = ActivityStatus("in_progress")
        assert status == ActivityStatus.IN_PROGRESS

    def test_constraint_from_string(self):
        """Test creating constraint from string."""
        constraint = ConstraintType("asap")
        assert constraint == ConstraintType.ASAP
