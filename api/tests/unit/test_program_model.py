"""Unit tests for Program model properties and methods."""

from datetime import date
from uuid import uuid4

from src.models.enums import ProgramStatus
from src.models.program import Program


class TestProgramProperties:
    """Tests for Program model properties."""

    def test_repr(self) -> None:
        """Should return formatted string representation."""
        program = Program(
            id=uuid4(),
            owner_id=uuid4(),
            code="PROG-001",
            name="Test Program",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProgramStatus.ACTIVE,
        )
        repr_str = repr(program)
        assert "Program" in repr_str
        assert "PROG-001" in repr_str
        assert "Test Program" in repr_str
        assert "active" in repr_str

    def test_duration_days(self) -> None:
        """Should calculate duration in days."""
        program = Program(
            id=uuid4(),
            owner_id=uuid4(),
            code="PROG-001",
            name="Test Program",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            status=ProgramStatus.PLANNING,
        )
        assert program.duration_days == 30

    def test_duration_days_one_year(self) -> None:
        """Should calculate full year duration."""
        program = Program(
            id=uuid4(),
            owner_id=uuid4(),
            code="PROG-001",
            name="Test Program",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProgramStatus.ACTIVE,
        )
        assert program.duration_days == 364

    def test_is_editable_true(self) -> None:
        """Should be editable when in editable status."""
        program = Program(
            id=uuid4(),
            owner_id=uuid4(),
            code="PROG-001",
            name="Test Program",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProgramStatus.PLANNING,
        )
        program.deleted_at = None
        assert program.is_editable is True

    def test_is_editable_false_completed(self) -> None:
        """Should not be editable when completed."""
        program = Program(
            id=uuid4(),
            owner_id=uuid4(),
            code="PROG-001",
            name="Test Program",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProgramStatus.COMPLETE,
        )
        program.deleted_at = None
        assert program.is_editable is False

    def test_is_editable_false_deleted(self) -> None:
        """Should not be editable when deleted."""
        from datetime import datetime

        program = Program(
            id=uuid4(),
            owner_id=uuid4(),
            code="PROG-001",
            name="Test Program",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProgramStatus.ACTIVE,
        )
        program.deleted_at = datetime.now()
        assert program.is_editable is False
