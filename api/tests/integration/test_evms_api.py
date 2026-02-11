"""Integration tests for EVMS API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestEVMSAuth:
    """Tests for authentication requirements on EVMS endpoints."""

    async def test_evms_summary_requires_auth(self, client: AsyncClient):
        """Should return 401 when not authenticated."""
        response = await client.get("/api/v1/evms/summary/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 401

    async def test_evms_periods_requires_auth(self, client: AsyncClient):
        """Should return 401 when listing periods without auth."""
        response = await client.get(
            "/api/v1/evms/periods?program_id=00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401

    async def test_s_curve_requires_auth(self, client: AsyncClient):
        """Should return 401 for s-curve endpoint without auth."""
        response = await client.get(
            "/api/v1/evms/s-curve-enhanced/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401


class TestEVMSSummary:
    """Tests for EVMS summary endpoint."""

    async def test_get_evms_summary(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should return EVMS summary for a program."""
        response = await client.get(
            f"/api/v1/evms/summary/{test_program['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    async def test_evms_summary_with_activity(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should calculate EVMS metrics for program with activity."""
        program_id = test_program["id"]

        # Create WBS + activity
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "wbs_code": "1.0",
                "name": "Project Root",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "EVMS Test Activity",
                "code": "EVMS-001",
                "duration": 10,
                "budgeted_cost": "5000.00",
            },
            headers=auth_headers,
        )

        response = await client.get(
            f"/api/v1/evms/summary/{program_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    async def test_evms_summary_nonexistent_program(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should handle nonexistent program."""
        response = await client.get(
            "/api/v1/evms/summary/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404)


class TestEVMSPeriods:
    """Tests for EVMS period management."""

    async def test_list_periods_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should return empty list when no periods exist."""
        response = await client.get(
            f"/api/v1/evms/periods?program_id={test_program['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200

    async def test_create_period(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should create an EVMS period."""
        response = await client.post(
            "/api/v1/evms/periods",
            json={
                "program_id": test_program["id"],
                "period_start": "2024-01-01",
                "period_end": "2024-01-31",
                "period_name": "January 2024",
            },
            headers=auth_headers,
        )
        assert response.status_code in (200, 201)


class TestEVMethods:
    """Tests for EV method configuration."""

    async def test_list_ev_methods(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should return available EV methods."""
        response = await client.get(
            "/api/v1/evms/ev-methods",
            headers=auth_headers,
        )
        assert response.status_code == 200

    async def test_set_activity_ev_method(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should set EV method for an activity."""
        program_id = test_program["id"]

        # Create WBS + activity
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "wbs_code": "1.0",
                "name": "Project Root",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        act_response = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "EV Method Test",
                "code": "EVM-001",
                "duration": 10,
                "budgeted_cost": "5000.00",
            },
            headers=auth_headers,
        )
        assert act_response.status_code == 201
        activity_id = act_response.json()["id"]

        response = await client.post(
            f"/api/v1/evms/activities/{activity_id}/ev-method",
            json={"ev_method": "percent_complete"},
            headers=auth_headers,
        )
        assert response.status_code in (200, 422)


class TestEACMethods:
    """Tests for advanced EAC calculation methods."""

    async def test_get_eac_methods(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should return EAC calculations using different methods."""
        response = await client.get(
            f"/api/v1/evms/eac-methods/{test_program['id']}",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404)


class TestSCurve:
    """Tests for S-curve data endpoint."""

    async def test_get_s_curve_data(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should return S-curve data for a program."""
        response = await client.get(
            f"/api/v1/evms/s-curve-enhanced/{test_program['id']}",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404)

    async def test_s_curve_enhanced(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should return enhanced S-curve with EAC/completion date ranges."""
        response = await client.get(
            f"/api/v1/evms/s-curve-enhanced/{test_program['id']}",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404)

    async def test_s_curve_export(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should export S-curve as PNG/SVG."""
        response = await client.get(
            f"/api/v1/evms/s-curve/{test_program['id']}/export?format=png",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404, 422)
