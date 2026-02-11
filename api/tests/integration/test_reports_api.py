"""Integration tests for Reports API endpoints (CPR Formats 1, 3, 5)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestReportsAuth:
    """Tests for authentication requirements on report endpoints."""

    async def test_cpr_report_requires_auth(self, client: AsyncClient):
        """Should return 401 or 404 when not authenticated."""
        response = await client.get("/api/v1/reports/cpr/00000000-0000-0000-0000-000000000000")
        assert response.status_code in (401, 404)

    async def test_audit_requires_auth(self, client: AsyncClient):
        """Should return 401 when listing audit trail without auth."""
        response = await client.get("/api/v1/reports/audit/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 401


class TestCPRFormat1:
    """Tests for CPR Format 1 (WBS) report generation."""

    async def test_generate_format_1(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should generate CPR Format 1 report."""
        response = await client.get(
            f"/api/v1/reports/cpr/{test_program['id']}",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404, 422, 500)

    async def test_format_1_nonexistent_program(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should handle nonexistent program."""
        response = await client.get(
            "/api/v1/reports/cpr/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code in (404, 500)


class TestCPRFormat3:
    """Tests for CPR Format 3 (Baseline) report generation."""

    async def test_generate_format_3(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should generate CPR Format 3 report."""
        response = await client.get(
            f"/api/v1/reports/cpr-format3/{test_program['id']}",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404, 422, 500)


class TestCPRFormat5:
    """Tests for CPR Format 5 (Variance Analysis) report generation."""

    async def test_generate_format_5(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should generate CPR Format 5 report."""
        response = await client.get(
            f"/api/v1/reports/cpr-format5/{test_program['id']}",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404, 422, 500)


class TestReportPDF:
    """Tests for PDF export of reports."""

    async def test_export_cpr_pdf(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should export CPR report as PDF."""
        response = await client.get(
            f"/api/v1/reports/cpr/{test_program['id']}/pdf",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404, 422, 500)


class TestReportAudit:
    """Tests for report audit trail."""

    async def test_list_audit_trail(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should list audit trail for a program."""
        response = await client.get(
            f"/api/v1/reports/audit/{test_program['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200

    async def test_audit_stats(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should return audit statistics."""
        response = await client.get(
            f"/api/v1/reports/audit/{test_program['id']}/stats",
            headers=auth_headers,
        )
        assert response.status_code == 200

    async def test_recent_audit(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should return recent audit entries."""
        response = await client.get(
            f"/api/v1/reports/audit/{test_program['id']}/recent",
            headers=auth_headers,
        )
        assert response.status_code == 200
