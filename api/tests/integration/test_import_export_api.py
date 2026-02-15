"""Integration tests for Import/Export API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# Minimal MS Project XML fixture for testing
MINIMAL_MSPROJECT_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Project xmlns="http://schemas.microsoft.com/project">
    <Name>Test Project</Name>
    <StartDate>2024-01-01T08:00:00</StartDate>
    <FinishDate>2024-06-30T17:00:00</FinishDate>
    <Tasks>
        <Task>
            <UID>0</UID>
            <ID>0</ID>
            <Name>Test Project</Name>
            <Summary>1</Summary>
            <OutlineLevel>0</OutlineLevel>
            <WBS>0</WBS>
        </Task>
        <Task>
            <UID>1</UID>
            <ID>1</ID>
            <Name>Design Phase</Name>
            <Duration>PT40H0M0S</Duration>
            <DurationFormat>7</DurationFormat>
            <Start>2024-01-01T08:00:00</Start>
            <Finish>2024-01-05T17:00:00</Finish>
            <Milestone>0</Milestone>
            <Summary>0</Summary>
            <OutlineLevel>1</OutlineLevel>
            <WBS>1</WBS>
        </Task>
        <Task>
            <UID>2</UID>
            <ID>2</ID>
            <Name>Implementation</Name>
            <Duration>PT80H0M0S</Duration>
            <DurationFormat>7</DurationFormat>
            <Start>2024-01-08T08:00:00</Start>
            <Finish>2024-01-19T17:00:00</Finish>
            <Milestone>0</Milestone>
            <Summary>0</Summary>
            <OutlineLevel>1</OutlineLevel>
            <WBS>2</WBS>
            <PredecessorLink>
                <PredecessorUID>1</PredecessorUID>
                <Type>1</Type>
                <LinkLag>0</LinkLag>
            </PredecessorLink>
        </Task>
    </Tasks>
</Project>"""


class TestImportExportAuth:
    """Tests for authentication requirements on import/export endpoints."""

    async def test_msproject_import_requires_auth(self, client: AsyncClient):
        """Should return 401 when importing without auth."""
        fake_id = str(uuid4())
        response = await client.post(f"/api/v1/import/msproject/{fake_id}")
        assert response.status_code == 401

    async def test_csv_export_requires_auth(self, client: AsyncClient):
        """Should return 401 when exporting without auth."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/import/export/{fake_id}/csv")
        assert response.status_code == 401


class TestMSProjectImport:
    """Tests for MS Project XML import endpoint."""

    async def test_import_program_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 404 for non-existent program."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/import/msproject/{fake_id}",
            headers=auth_headers,
            files={"file": ("test.xml", b"<Project/>", "application/xml")},
        )
        assert response.status_code == 404

    async def test_import_invalid_file_extension(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Should return 422 for non-XML file."""
        program_id = test_program["id"]
        response = await client.post(
            f"/api/v1/import/msproject/{program_id}",
            headers=auth_headers,
            files={"file": ("test.txt", b"not xml", "text/plain")},
        )
        assert response.status_code == 422

    async def test_import_no_filename(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Should return 422 when filename is empty."""
        program_id = test_program["id"]
        response = await client.post(
            f"/api/v1/import/msproject/{program_id}",
            headers=auth_headers,
            files={"file": ("", b"<Project/>", "application/xml")},
        )
        assert response.status_code == 422

    async def test_import_preview_mode(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Should return preview data without importing."""
        program_id = test_program["id"]
        response = await client.post(
            f"/api/v1/import/msproject/{program_id}?preview=true",
            headers=auth_headers,
            files={
                "file": (
                    "project.xml",
                    MINIMAL_MSPROJECT_XML.encode(),
                    "application/xml",
                )
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preview"] is True
        assert data["project_name"] == "Test Project"
        assert data["task_count"] >= 1
        assert isinstance(data["tasks"], list)

    async def test_import_actual_import(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Should import tasks from MS Project XML."""
        program_id = test_program["id"]
        response = await client.post(
            f"/api/v1/import/msproject/{program_id}",
            headers=auth_headers,
            files={
                "file": (
                    "project.xml",
                    MINIMAL_MSPROJECT_XML.encode(),
                    "application/xml",
                )
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tasks_imported"] > 0


class TestCSVExport:
    """Tests for CSV export endpoint."""

    @pytest_asyncio.fixture
    async def program_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ) -> dict:
        """Create a program with WBS and activity data for export tests."""
        program_id = test_program["id"]

        # Create WBS element (required for activities)
        wbs_resp = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "name": "Work Package 1",
                "wbs_code": "1.1",
            },
            headers=auth_headers,
        )
        wbs_id = wbs_resp.json()["id"]

        # Create an activity
        act_resp = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "Export Test Activity",
                "code": "EXP-001",
                "duration": 5,
            },
            headers=auth_headers,
        )
        assert act_resp.status_code == 201

        return {
            "program_id": program_id,
            "wbs_id": wbs_id,
            "activity": act_resp.json(),
        }

    async def test_export_program_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 404 for non-existent program."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/import/export/{fake_id}/csv",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_export_invalid_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Should return 422 for invalid export type."""
        program_id = test_program["id"]
        response = await client.get(
            f"/api/v1/import/export/{program_id}/csv?export_type=invalid",
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_export_activities(
        self,
        client: AsyncClient,
        auth_headers: dict,
        program_with_data: dict,
    ):
        """Should export activities as CSV."""
        program_id = program_with_data["program_id"]

        response = await client.get(
            f"/api/v1/import/export/{program_id}/csv?export_type=activities",
            headers=auth_headers,
        )
        assert response.status_code == 200
        content = response.text
        assert "Code" in content
        assert "Name" in content
        assert "EXP-001" in content
        assert "Export Test Activity" in content

    async def test_export_empty_program(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Should return CSV with headers only for empty program."""
        program_id = test_program["id"]
        response = await client.get(
            f"/api/v1/import/export/{program_id}/csv?export_type=activities",
            headers=auth_headers,
        )
        assert response.status_code == 200
        content = response.text
        # Should have headers
        assert "Code" in content
        assert "Name" in content

    async def test_export_streaming_response(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Should return proper CSV content type and disposition."""
        program_id = test_program["id"]
        response = await client.get(
            f"/api/v1/import/export/{program_id}/csv?export_type=activities",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers.get("content-disposition", "")

    async def test_export_all(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_program: dict,
    ):
        """Should export all sections with separators."""
        program_id = test_program["id"]

        response = await client.get(
            f"/api/v1/import/export/{program_id}/csv?export_type=all",
            headers=auth_headers,
        )
        assert response.status_code == 200
        content = response.text
        # Should have section headers
        assert "## Activities" in content
        assert "## Resources" in content
        assert "## WBS Elements" in content
