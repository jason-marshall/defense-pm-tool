"""Unit tests for calendar import endpoints."""

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.calendar_import import (
    import_calendars,
    preview_calendar_import,
)
from src.core.exceptions import ValidationError


def _make_upload_file(filename: str = "project.xml", content: bytes = b"<xml/>") -> MagicMock:
    """Create a mock UploadFile with the given filename and content."""
    mock_file = MagicMock()
    mock_file.filename = filename
    mock_file.read = AsyncMock(return_value=content)
    return mock_file


class TestPreviewCalendarImport:
    """Tests for preview_calendar_import endpoint."""

    @pytest.mark.asyncio
    async def test_preview_success(self):
        """Should return preview response with calendar summaries and mappings."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        start = date(2026, 1, 1)
        end = date(2026, 12, 31)
        mock_file = _make_upload_file()

        mock_preview = MagicMock()
        mock_preview.calendars = [{"uid": 1, "name": "Standard", "is_base": True, "holidays": 10}]
        mock_preview.resource_mappings = [
            {"ms_project_resource": "Engineer A", "matched_resource_id": str(uuid4())}
        ]
        mock_preview.total_holidays = 10
        mock_preview.date_range_start = start
        mock_preview.date_range_end = end
        mock_preview.warnings = []

        with patch(
            "src.api.v1.endpoints.calendar_import.CalendarImportService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.preview_import = AsyncMock(return_value=mock_preview)
            mock_service_class.return_value = mock_service

            with patch("src.api.v1.endpoints.calendar_import.NamedTemporaryFile") as mock_tmpfile:
                mock_tmp = MagicMock()
                mock_tmp.name = "/tmp/test_cal.xml"
                mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
                mock_tmp.__exit__ = MagicMock(return_value=False)
                mock_tmpfile.return_value = mock_tmp

                with patch("src.api.v1.endpoints.calendar_import.Path") as mock_path_cls:
                    mock_path = MagicMock(spec=Path)
                    mock_path_cls.return_value = mock_path

                    result = await preview_calendar_import(
                        program_id=program_id,
                        file=mock_file,
                        start_date=start,
                        end_date=end,
                        db=mock_db,
                        current_user=mock_user,
                    )

                    assert result.total_holidays == 10
                    assert result.date_range_start == start
                    assert result.date_range_end == end
                    assert len(result.calendars) == 1
                    assert result.calendars[0]["name"] == "Standard"
                    assert len(result.resource_mappings) == 1
                    assert result.warnings == []
                    mock_service.preview_import.assert_called_once()
                    mock_path.unlink.assert_called_once()

    @pytest.mark.asyncio
    async def test_preview_rejects_non_xml_file(self):
        """Should raise ValidationError for non-XML file."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        mock_file = _make_upload_file(filename="project.csv")

        with pytest.raises(ValidationError) as exc_info:
            await preview_calendar_import(
                program_id=program_id,
                file=mock_file,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                db=mock_db,
                current_user=mock_user,
            )

        assert exc_info.value.code == "INVALID_FILE_TYPE"

    @pytest.mark.asyncio
    async def test_preview_rejects_file_without_extension(self):
        """Should raise ValidationError when filename has no .xml extension."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        mock_file = _make_upload_file(filename="project")

        with pytest.raises(ValidationError) as exc_info:
            await preview_calendar_import(
                program_id=program_id,
                file=mock_file,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                db=mock_db,
                current_user=mock_user,
            )

        assert exc_info.value.code == "INVALID_FILE_TYPE"

    @pytest.mark.asyncio
    async def test_preview_rejects_file_with_no_filename(self):
        """Should raise ValidationError when filename is None."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        mock_file = _make_upload_file()
        mock_file.filename = None

        with pytest.raises(ValidationError) as exc_info:
            await preview_calendar_import(
                program_id=program_id,
                file=mock_file,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                db=mock_db,
                current_user=mock_user,
            )

        assert exc_info.value.code == "INVALID_FILE_TYPE"

    @pytest.mark.asyncio
    async def test_preview_rejects_end_date_before_start_date(self):
        """Should raise ValidationError when end_date is before start_date."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        mock_file = _make_upload_file()

        with pytest.raises(ValidationError) as exc_info:
            await preview_calendar_import(
                program_id=program_id,
                file=mock_file,
                start_date=date(2026, 12, 31),
                end_date=date(2026, 1, 1),
                db=mock_db,
                current_user=mock_user,
            )

        assert exc_info.value.code == "INVALID_DATE_RANGE"

    @pytest.mark.asyncio
    async def test_preview_with_warnings(self):
        """Should propagate warnings from the import service."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        start = date(2026, 1, 1)
        end = date(2026, 6, 30)
        mock_file = _make_upload_file()

        mock_preview = MagicMock()
        mock_preview.calendars = []
        mock_preview.resource_mappings = []
        mock_preview.total_holidays = 0
        mock_preview.date_range_start = start
        mock_preview.date_range_end = end
        mock_preview.warnings = [
            "Unknown calendar type encountered",
            "Resource 'Bob' has no calendar assigned",
        ]

        with patch(
            "src.api.v1.endpoints.calendar_import.CalendarImportService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.preview_import = AsyncMock(return_value=mock_preview)
            mock_service_class.return_value = mock_service

            with patch("src.api.v1.endpoints.calendar_import.NamedTemporaryFile") as mock_tmpfile:
                mock_tmp = MagicMock()
                mock_tmp.name = "/tmp/test_cal.xml"
                mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
                mock_tmp.__exit__ = MagicMock(return_value=False)
                mock_tmpfile.return_value = mock_tmp

                with patch("src.api.v1.endpoints.calendar_import.Path") as mock_path_cls:
                    mock_path = MagicMock(spec=Path)
                    mock_path_cls.return_value = mock_path

                    result = await preview_calendar_import(
                        program_id=program_id,
                        file=mock_file,
                        start_date=start,
                        end_date=end,
                        db=mock_db,
                        current_user=mock_user,
                    )

                    assert len(result.warnings) == 2
                    assert "Unknown calendar type encountered" in result.warnings

    @pytest.mark.asyncio
    async def test_preview_cleans_up_temp_file_on_service_error(self):
        """Should delete temp file even when service raises an exception."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        mock_file = _make_upload_file()

        with patch(
            "src.api.v1.endpoints.calendar_import.CalendarImportService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.preview_import = AsyncMock(side_effect=RuntimeError("Parse failed"))
            mock_service_class.return_value = mock_service

            with patch("src.api.v1.endpoints.calendar_import.NamedTemporaryFile") as mock_tmpfile:
                mock_tmp = MagicMock()
                mock_tmp.name = "/tmp/test_cal.xml"
                mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
                mock_tmp.__exit__ = MagicMock(return_value=False)
                mock_tmpfile.return_value = mock_tmp

                with patch("src.api.v1.endpoints.calendar_import.Path") as mock_path_cls:
                    mock_path = MagicMock(spec=Path)
                    mock_path_cls.return_value = mock_path

                    with pytest.raises(RuntimeError, match="Parse failed"):
                        await preview_calendar_import(
                            program_id=program_id,
                            file=mock_file,
                            start_date=date(2026, 1, 1),
                            end_date=date(2026, 12, 31),
                            db=mock_db,
                            current_user=mock_user,
                        )

                    # Temp file cleanup must still happen in the finally block
                    mock_path.unlink.assert_called_once()

    @pytest.mark.asyncio
    async def test_preview_passes_correct_args_to_service(self):
        """Should pass program_id, file path, and date range to the service."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        start = date(2026, 3, 1)
        end = date(2026, 9, 30)
        mock_file = _make_upload_file(content=b"<Project>data</Project>")

        mock_preview = MagicMock()
        mock_preview.calendars = []
        mock_preview.resource_mappings = []
        mock_preview.total_holidays = 0
        mock_preview.date_range_start = start
        mock_preview.date_range_end = end
        mock_preview.warnings = []

        with patch(
            "src.api.v1.endpoints.calendar_import.CalendarImportService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.preview_import = AsyncMock(return_value=mock_preview)
            mock_service_class.return_value = mock_service

            with patch("src.api.v1.endpoints.calendar_import.NamedTemporaryFile") as mock_tmpfile:
                mock_tmp = MagicMock()
                mock_tmp.name = "/tmp/specific_path.xml"
                mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
                mock_tmp.__exit__ = MagicMock(return_value=False)
                mock_tmpfile.return_value = mock_tmp

                with patch("src.api.v1.endpoints.calendar_import.Path") as mock_path_cls:
                    mock_path = MagicMock(spec=Path)
                    mock_path_cls.return_value = mock_path

                    await preview_calendar_import(
                        program_id=program_id,
                        file=mock_file,
                        start_date=start,
                        end_date=end,
                        db=mock_db,
                        current_user=mock_user,
                    )

                    # Verify service was constructed with db
                    mock_service_class.assert_called_once_with(mock_db)

                    # Verify preview_import was called with correct args
                    call_kwargs = mock_service.preview_import.call_args.kwargs
                    assert call_kwargs["file_path"] == mock_path
                    assert call_kwargs["program_id"] == program_id
                    assert call_kwargs["date_range_start"] == start
                    assert call_kwargs["date_range_end"] == end


class TestImportCalendars:
    """Tests for import_calendars endpoint."""

    @pytest.mark.asyncio
    async def test_import_success(self):
        """Should import calendars and return success response."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        start = date(2026, 1, 1)
        end = date(2026, 12, 31)
        mock_file = _make_upload_file()

        mock_result = MagicMock()
        mock_result.resources_updated = 3
        mock_result.calendar_entries_created = 750
        mock_result.templates_created = 2
        mock_result.warnings = []

        with patch(
            "src.api.v1.endpoints.calendar_import.CalendarImportService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.import_calendars = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            with patch("src.api.v1.endpoints.calendar_import.NamedTemporaryFile") as mock_tmpfile:
                mock_tmp = MagicMock()
                mock_tmp.name = "/tmp/import_cal.xml"
                mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
                mock_tmp.__exit__ = MagicMock(return_value=False)
                mock_tmpfile.return_value = mock_tmp

                with patch("src.api.v1.endpoints.calendar_import.Path") as mock_path_cls:
                    mock_path = MagicMock(spec=Path)
                    mock_path_cls.return_value = mock_path

                    result = await import_calendars(
                        program_id=program_id,
                        file=mock_file,
                        start_date=start,
                        end_date=end,
                        db=mock_db,
                        current_user=mock_user,
                    )

                    assert result.success is True
                    assert result.resources_updated == 3
                    assert result.calendar_entries_created == 750
                    assert result.templates_created == 2
                    assert result.warnings == []
                    mock_path.unlink.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_rejects_non_xml_file(self):
        """Should raise ValidationError for non-XML file."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        mock_file = _make_upload_file(filename="schedule.mpp")

        with pytest.raises(ValidationError) as exc_info:
            await import_calendars(
                program_id=program_id,
                file=mock_file,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                db=mock_db,
                current_user=mock_user,
            )

        assert exc_info.value.code == "INVALID_FILE_TYPE"

    @pytest.mark.asyncio
    async def test_import_rejects_empty_filename(self):
        """Should raise ValidationError when filename is empty string."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        mock_file = _make_upload_file(filename="")

        with pytest.raises(ValidationError) as exc_info:
            await import_calendars(
                program_id=program_id,
                file=mock_file,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                db=mock_db,
                current_user=mock_user,
            )

        assert exc_info.value.code == "INVALID_FILE_TYPE"

    @pytest.mark.asyncio
    async def test_import_with_warnings(self):
        """Should propagate warnings from the import service."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        start = date(2026, 1, 1)
        end = date(2026, 6, 30)
        mock_file = _make_upload_file()

        mock_result = MagicMock()
        mock_result.resources_updated = 1
        mock_result.calendar_entries_created = 100
        mock_result.templates_created = 1
        mock_result.warnings = [
            "Resource 'Contractor X' not found, skipping",
            "Calendar 5 not found for 'Intern Y'",
        ]

        with patch(
            "src.api.v1.endpoints.calendar_import.CalendarImportService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.import_calendars = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            with patch("src.api.v1.endpoints.calendar_import.NamedTemporaryFile") as mock_tmpfile:
                mock_tmp = MagicMock()
                mock_tmp.name = "/tmp/import_cal.xml"
                mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
                mock_tmp.__exit__ = MagicMock(return_value=False)
                mock_tmpfile.return_value = mock_tmp

                with patch("src.api.v1.endpoints.calendar_import.Path") as mock_path_cls:
                    mock_path = MagicMock(spec=Path)
                    mock_path_cls.return_value = mock_path

                    result = await import_calendars(
                        program_id=program_id,
                        file=mock_file,
                        start_date=start,
                        end_date=end,
                        db=mock_db,
                        current_user=mock_user,
                    )

                    assert result.success is True
                    assert len(result.warnings) == 2
                    assert "Contractor X" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_import_cleans_up_temp_file_on_service_error(self):
        """Should delete temp file even when import service raises."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        mock_file = _make_upload_file()

        with patch(
            "src.api.v1.endpoints.calendar_import.CalendarImportService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.import_calendars = AsyncMock(side_effect=RuntimeError("XML parse error"))
            mock_service_class.return_value = mock_service

            with patch("src.api.v1.endpoints.calendar_import.NamedTemporaryFile") as mock_tmpfile:
                mock_tmp = MagicMock()
                mock_tmp.name = "/tmp/import_cal.xml"
                mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
                mock_tmp.__exit__ = MagicMock(return_value=False)
                mock_tmpfile.return_value = mock_tmp

                with patch("src.api.v1.endpoints.calendar_import.Path") as mock_path_cls:
                    mock_path = MagicMock(spec=Path)
                    mock_path_cls.return_value = mock_path

                    with pytest.raises(RuntimeError, match="XML parse error"):
                        await import_calendars(
                            program_id=program_id,
                            file=mock_file,
                            start_date=date(2026, 1, 1),
                            end_date=date(2026, 12, 31),
                            db=mock_db,
                            current_user=mock_user,
                        )

                    mock_path.unlink.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_passes_correct_args_to_service(self):
        """Should pass correct arguments to CalendarImportService.import_calendars."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        start = date(2026, 4, 1)
        end = date(2026, 10, 31)
        xml_content = b"<Project><Calendars/></Project>"
        mock_file = _make_upload_file(content=xml_content)

        mock_result = MagicMock()
        mock_result.resources_updated = 0
        mock_result.calendar_entries_created = 0
        mock_result.templates_created = 0
        mock_result.warnings = []

        with patch(
            "src.api.v1.endpoints.calendar_import.CalendarImportService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.import_calendars = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            with patch("src.api.v1.endpoints.calendar_import.NamedTemporaryFile") as mock_tmpfile:
                mock_tmp = MagicMock()
                mock_tmp.name = "/tmp/import_path.xml"
                mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
                mock_tmp.__exit__ = MagicMock(return_value=False)
                mock_tmpfile.return_value = mock_tmp

                with patch("src.api.v1.endpoints.calendar_import.Path") as mock_path_cls:
                    mock_path = MagicMock(spec=Path)
                    mock_path_cls.return_value = mock_path

                    await import_calendars(
                        program_id=program_id,
                        file=mock_file,
                        start_date=start,
                        end_date=end,
                        db=mock_db,
                        current_user=mock_user,
                    )

                    mock_service_class.assert_called_once_with(mock_db)

                    call_kwargs = mock_service.import_calendars.call_args.kwargs
                    assert call_kwargs["file_path"] == mock_path
                    assert call_kwargs["program_id"] == program_id
                    assert call_kwargs["date_range_start"] == start
                    assert call_kwargs["date_range_end"] == end

    @pytest.mark.asyncio
    async def test_import_writes_uploaded_content_to_temp_file(self):
        """Should write file content to temporary file before passing to service."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        xml_content = b"<Project><Calendars><Calendar/></Calendars></Project>"
        mock_file = _make_upload_file(content=xml_content)

        mock_result = MagicMock()
        mock_result.resources_updated = 0
        mock_result.calendar_entries_created = 0
        mock_result.templates_created = 0
        mock_result.warnings = []

        with patch(
            "src.api.v1.endpoints.calendar_import.CalendarImportService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.import_calendars = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            with patch("src.api.v1.endpoints.calendar_import.NamedTemporaryFile") as mock_tmpfile:
                mock_tmp = MagicMock()
                mock_tmp.name = "/tmp/content_check.xml"
                mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
                mock_tmp.__exit__ = MagicMock(return_value=False)
                mock_tmpfile.return_value = mock_tmp

                with patch("src.api.v1.endpoints.calendar_import.Path") as mock_path_cls:
                    mock_path = MagicMock(spec=Path)
                    mock_path_cls.return_value = mock_path

                    await import_calendars(
                        program_id=program_id,
                        file=mock_file,
                        start_date=date(2026, 1, 1),
                        end_date=date(2026, 12, 31),
                        db=mock_db,
                        current_user=mock_user,
                    )

                    # Verify file content was read and written to temp file
                    mock_file.read.assert_called_once()
                    mock_tmp.write.assert_called_once_with(xml_content)

    @pytest.mark.asyncio
    async def test_import_zero_resources_still_succeeds(self):
        """Should return success even when no resources were updated."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()
        mock_file = _make_upload_file()

        mock_result = MagicMock()
        mock_result.resources_updated = 0
        mock_result.calendar_entries_created = 0
        mock_result.templates_created = 0
        mock_result.warnings = ["No matching resources found"]

        with patch(
            "src.api.v1.endpoints.calendar_import.CalendarImportService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.import_calendars = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            with patch("src.api.v1.endpoints.calendar_import.NamedTemporaryFile") as mock_tmpfile:
                mock_tmp = MagicMock()
                mock_tmp.name = "/tmp/empty_import.xml"
                mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
                mock_tmp.__exit__ = MagicMock(return_value=False)
                mock_tmpfile.return_value = mock_tmp

                with patch("src.api.v1.endpoints.calendar_import.Path") as mock_path_cls:
                    mock_path = MagicMock(spec=Path)
                    mock_path_cls.return_value = mock_path

                    result = await import_calendars(
                        program_id=program_id,
                        file=mock_file,
                        start_date=date(2026, 1, 1),
                        end_date=date(2026, 12, 31),
                        db=mock_db,
                        current_user=mock_user,
                    )

                    assert result.success is True
                    assert result.resources_updated == 0
                    assert result.calendar_entries_created == 0
                    assert result.templates_created == 0
                    assert len(result.warnings) == 1
