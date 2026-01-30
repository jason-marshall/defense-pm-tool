"""E2E tests for Week 18 calendar import functionality."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from httpx import AsyncClient

SAMPLE_CALENDAR_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Calendars>
    <Calendar>
      <UID>1</UID>
      <Name>Standard</Name>
      <IsBaseCalendar>1</IsBaseCalendar>
      <WeekDays>
        <WeekDay><DayType>1</DayType><DayWorking>0</DayWorking></WeekDay>
        <WeekDay><DayType>2</DayType><DayWorking>1</DayWorking>
          <WorkingTimes>
            <WorkingTime><FromTime>08:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
          </WorkingTimes>
        </WeekDay>
        <WeekDay><DayType>3</DayType><DayWorking>1</DayWorking>
          <WorkingTimes>
            <WorkingTime><FromTime>08:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
          </WorkingTimes>
        </WeekDay>
        <WeekDay><DayType>4</DayType><DayWorking>1</DayWorking>
          <WorkingTimes>
            <WorkingTime><FromTime>08:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
          </WorkingTimes>
        </WeekDay>
        <WeekDay><DayType>5</DayType><DayWorking>1</DayWorking>
          <WorkingTimes>
            <WorkingTime><FromTime>08:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
          </WorkingTimes>
        </WeekDay>
        <WeekDay><DayType>6</DayType><DayWorking>1</DayWorking>
          <WorkingTimes>
            <WorkingTime><FromTime>08:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
          </WorkingTimes>
        </WeekDay>
        <WeekDay><DayType>7</DayType><DayWorking>0</DayWorking></WeekDay>
      </WeekDays>
    </Calendar>
  </Calendars>
  <Resources>
    <Resource>
      <UID>1</UID>
      <Name>Test Engineer</Name>
      <CalendarUID>1</CalendarUID>
    </Resource>
  </Resources>
</Project>"""


class TestCalendarImportPreview:
    """Tests for calendar import preview."""

    @pytest.mark.asyncio
    async def test_preview_calendar_import(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Test previewing calendar import."""
        # Create temp XML file
        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(SAMPLE_CALENDAR_XML)
            xml_path = Path(f.name)

        try:
            with xml_path.open("rb") as f:
                response = await client.post(
                    "/api/v1/calendars/import/preview",
                    params={
                        "program_id": str(test_program["id"]),
                        "start_date": "2026-01-01",
                        "end_date": "2026-12-31",
                    },
                    files={"file": ("test.xml", f, "application/xml")},
                    headers=auth_headers,
                )

            assert response.status_code == 200
            data = response.json()

            assert len(data["calendars"]) == 1
            assert data["calendars"][0]["name"] == "Standard"
            assert len(data["resource_mappings"]) == 1
        finally:
            xml_path.unlink()

    @pytest.mark.asyncio
    async def test_preview_invalid_file_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Test preview with invalid file type."""
        with NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("not xml content")
            txt_path = Path(f.name)

        try:
            with txt_path.open("rb") as f:
                response = await client.post(
                    "/api/v1/calendars/import/preview",
                    params={
                        "program_id": str(test_program["id"]),
                        "start_date": "2026-01-01",
                        "end_date": "2026-12-31",
                    },
                    files={"file": ("test.txt", f, "text/plain")},
                    headers=auth_headers,
                )

            assert response.status_code == 400
        finally:
            txt_path.unlink()

    @pytest.mark.asyncio
    async def test_preview_working_days_extraction(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Test that working days are correctly extracted."""
        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(SAMPLE_CALENDAR_XML)
            xml_path = Path(f.name)

        try:
            with xml_path.open("rb") as f:
                response = await client.post(
                    "/api/v1/calendars/import/preview",
                    params={
                        "program_id": str(test_program["id"]),
                        "start_date": "2026-01-01",
                        "end_date": "2026-01-31",
                    },
                    files={"file": ("test.xml", f, "application/xml")},
                    headers=auth_headers,
                )

            data = response.json()
            calendar = data["calendars"][0]

            # Should have Mon-Fri as working days (ISO: 1-5)
            assert calendar["working_days"] == [1, 2, 3, 4, 5]
            assert calendar["hours_per_day"] == 9.0  # 8am to 5pm
        finally:
            xml_path.unlink()


class TestCalendarImport:
    """Tests for full calendar import."""

    @pytest.mark.asyncio
    async def test_import_calendars(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Test importing calendars from MS Project XML."""
        # Create a resource that matches the XML
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": str(test_program["id"]),
                "name": "Test Engineer",
                "code": "ENG-001",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        assert resource_response.status_code == 201

        # Import calendars
        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(SAMPLE_CALENDAR_XML)
            xml_path = Path(f.name)

        try:
            with xml_path.open("rb") as f:
                response = await client.post(
                    "/api/v1/calendars/import",
                    params={
                        "program_id": str(test_program["id"]),
                        "start_date": "2026-01-01",
                        "end_date": "2026-01-31",
                    },
                    files={"file": ("test.xml", f, "application/xml")},
                    headers=auth_headers,
                )

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["resources_updated"] == 1
            assert data["templates_created"] >= 1
            assert data["calendar_entries_created"] == 31  # January has 31 days
        finally:
            xml_path.unlink()

    @pytest.mark.asyncio
    async def test_import_with_no_matching_resources(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Test import when no resources match."""
        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(SAMPLE_CALENDAR_XML)
            xml_path = Path(f.name)

        try:
            with xml_path.open("rb") as f:
                response = await client.post(
                    "/api/v1/calendars/import",
                    params={
                        "program_id": str(test_program["id"]),
                        "start_date": "2026-01-01",
                        "end_date": "2026-01-07",
                    },
                    files={"file": ("test.xml", f, "application/xml")},
                    headers=auth_headers,
                )

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["resources_updated"] == 0
            # Templates should still be created
            assert data["templates_created"] >= 1
            # Should have warning about unmatched resource
            assert len(data["warnings"]) > 0
        finally:
            xml_path.unlink()


class TestCalendarTemplates:
    """Tests for calendar templates."""

    @pytest.mark.asyncio
    async def test_imported_template_applied(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Test that imported templates are applied to resources."""
        # Create resource
        resource_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": str(test_program["id"]),
                "name": "Template Test",
                "code": "TPL-001",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        resource = resource_response.json()

        # Import with matching resource
        xml_content = SAMPLE_CALENDAR_XML.replace("Test Engineer", "Template Test")

        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            xml_path = Path(f.name)

        try:
            with xml_path.open("rb") as f:
                import_response = await client.post(
                    "/api/v1/calendars/import",
                    params={
                        "program_id": str(test_program["id"]),
                        "start_date": "2026-01-01",
                        "end_date": "2026-01-07",
                    },
                    files={"file": ("test.xml", f, "application/xml")},
                    headers=auth_headers,
                )

            assert import_response.status_code == 200

            # Verify resource has template assigned
            updated_resource = await client.get(
                f"/api/v1/resources/{resource['id']}",
                headers=auth_headers,
            )
            assert updated_resource.status_code == 200
            # Resource should have been updated
            data = updated_resource.json()
            assert data["name"] == "Template Test"
        finally:
            xml_path.unlink()

    @pytest.mark.asyncio
    async def test_multiple_calendars_import(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Test importing multiple calendars."""
        multi_calendar_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Calendars>
    <Calendar>
      <UID>1</UID>
      <Name>Standard</Name>
      <IsBaseCalendar>1</IsBaseCalendar>
      <WeekDays>
        <WeekDay><DayType>2</DayType><DayWorking>1</DayWorking></WeekDay>
        <WeekDay><DayType>3</DayType><DayWorking>1</DayWorking></WeekDay>
        <WeekDay><DayType>4</DayType><DayWorking>1</DayWorking></WeekDay>
        <WeekDay><DayType>5</DayType><DayWorking>1</DayWorking></WeekDay>
        <WeekDay><DayType>6</DayType><DayWorking>1</DayWorking></WeekDay>
      </WeekDays>
    </Calendar>
    <Calendar>
      <UID>2</UID>
      <Name>Night Shift</Name>
      <IsBaseCalendar>1</IsBaseCalendar>
      <WeekDays>
        <WeekDay><DayType>2</DayType><DayWorking>1</DayWorking></WeekDay>
        <WeekDay><DayType>3</DayType><DayWorking>1</DayWorking></WeekDay>
        <WeekDay><DayType>4</DayType><DayWorking>1</DayWorking></WeekDay>
        <WeekDay><DayType>5</DayType><DayWorking>1</DayWorking></WeekDay>
        <WeekDay><DayType>6</DayType><DayWorking>1</DayWorking></WeekDay>
      </WeekDays>
    </Calendar>
  </Calendars>
</Project>"""

        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(multi_calendar_xml)
            xml_path = Path(f.name)

        try:
            with xml_path.open("rb") as f:
                response = await client.post(
                    "/api/v1/calendars/import/preview",
                    params={
                        "program_id": str(test_program["id"]),
                        "start_date": "2026-01-01",
                        "end_date": "2026-01-31",
                    },
                    files={"file": ("test.xml", f, "application/xml")},
                    headers=auth_headers,
                )

            assert response.status_code == 200
            data = response.json()

            assert len(data["calendars"]) == 2
            calendar_names = [c["name"] for c in data["calendars"]]
            assert "Standard" in calendar_names
            assert "Night Shift" in calendar_names
        finally:
            xml_path.unlink()


class TestCalendarImportValidation:
    """Tests for calendar import validation."""

    @pytest.mark.asyncio
    async def test_invalid_date_range(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Test import with end date before start date."""
        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(SAMPLE_CALENDAR_XML)
            xml_path = Path(f.name)

        try:
            with xml_path.open("rb") as f:
                response = await client.post(
                    "/api/v1/calendars/import/preview",
                    params={
                        "program_id": str(test_program["id"]),
                        "start_date": "2026-12-31",
                        "end_date": "2026-01-01",
                    },
                    files={"file": ("test.xml", f, "application/xml")},
                    headers=auth_headers,
                )

            assert response.status_code == 400
        finally:
            xml_path.unlink()

    @pytest.mark.asyncio
    async def test_import_requires_authentication(
        self,
        client: AsyncClient,
        test_program: dict,
    ):
        """Test that import requires authentication."""
        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(SAMPLE_CALENDAR_XML)
            xml_path = Path(f.name)

        try:
            with xml_path.open("rb") as f:
                response = await client.post(
                    "/api/v1/calendars/import",
                    params={
                        "program_id": str(test_program["id"]),
                        "start_date": "2026-01-01",
                        "end_date": "2026-01-31",
                    },
                    files={"file": ("test.xml", f, "application/xml")},
                    # No auth headers
                )

            assert response.status_code == 401
        finally:
            xml_path.unlink()
