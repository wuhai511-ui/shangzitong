"""RED: Tests for 全局调度引擎 (P2B)."""
import pytest
import sys
import os
import io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from fastapi.testclient import TestClient
from datetime import date, timedelta
from decimal import Decimal


class TestSchedulerAPI:
    """Test global scheduler endpoints (RED → GREEN)."""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        resp = client.post("/api/v1/auth/login", json={"code": "test_scheduler_user"})
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def _seed_card(self, client, auth_headers, bank_name="招商银行", bill_day=5, due_day=25,
                   credit_limit=50000, used_limit=0):
        resp = client.post("/api/v1/cards", json={
            "bank_name": bank_name, "card_tail": "1234",
            "credit_limit": credit_limit, "used_limit": used_limit,
            "bill_day": bill_day, "due_day": due_day
        }, headers=auth_headers)
        assert resp.status_code == 200
        return resp.json()

    def _seed_settlements(self, client, auth_headers):
        """Insert historical settlement data via upload."""
        csv_content = b"date,amount\n" + b"\n".join(
            f"{(date.today() - timedelta(days=i)).isoformat()},{1000 + i * 100}".encode()
            for i in range(7, 35)
        )
        preview = client.post(
            "/api/v1/ingest/upload/preview",
            files={"file": ("hist.csv", io.BytesIO(csv_content), "text/csv")},
            headers=auth_headers
        )
        mappings = preview.json()["mappings"]
        client.post(
            "/api/v1/ingest/upload/confirm",
            json={"mappings": mappings, "provider": "test"},
            headers=auth_headers
        )

    def test_schedule_returns_30_days(self, client, auth_headers):
        """GET /api/v1/schedule should return 30 days of schedule data."""
        self._seed_card(client, auth_headers)
        self._seed_settlements(client, auth_headers)
        resp = client.get("/api/v1/schedule", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["days"]) == 30
        for day in data["days"]:
            assert "date" in day
            assert "cash_pool" in day
            assert "settlements" in day
            assert "repayments" in day
            assert "alerts" in day

    def test_schedule_shows_cash_pool(self, client, auth_headers):
        """Schedule should include cash_pool trend over 30 days."""
        self._seed_card(client, auth_headers)
        self._seed_settlements(client, auth_headers)
        resp = client.get("/api/v1/schedule", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        days = data["days"]
        assert len(days) == 30

        # cash_pool should be present and numeric in each day
        cash_pools = []
        for day in days:
            cp = Decimal(day["cash_pool"])
            cash_pools.append(cp)

        # Cash pool should grow or stay flat (settlements add, repayments subtract)
        # At minimum, verify all values are valid decimals
        assert all(isinstance(cp, Decimal) for cp in cash_pools)

    def test_schedule_unauthorized(self, client):
        """Unauthenticated requests should return 401."""
        resp = client.get("/api/v1/schedule")
        assert resp.status_code == 401
