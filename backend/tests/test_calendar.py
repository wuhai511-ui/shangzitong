"""RED: Tests for 资金日历API (Module 6)."""
import pytest
import sys
import os
import io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from fastapi.testclient import TestClient
from datetime import date, timedelta
from decimal import Decimal


class TestCalendarAPI:
    """Test calendar endpoints (RED → GREEN)."""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        resp = client.post("/api/v1/auth/login", json={"code": "test_calendar_user"})
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def _seed_card(self, client, auth_headers, bank_name="招商银行", bill_day=5, due_day=25,
                   credit_limit=50000, used_limit=20000):
        """Create a card and return its id."""
        resp = client.post("/api/v1/cards", json={
            "bank_name": bank_name, "card_tail": "1234",
            "credit_limit": credit_limit, "used_limit": used_limit,
            "bill_day": bill_day, "due_day": due_day
        }, headers=auth_headers)
        assert resp.status_code == 200
        return resp.json()["id"]

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

    def test_calendar_returns_30_days(self, client, auth_headers):
        """GET /api/v1/calendar should return 30 days of data."""
        self._seed_card(client, auth_headers)
        self._seed_settlements(client, auth_headers)
        resp = client.get("/api/v1/calendar", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["days"]) == 30
        for day in data["days"]:
            assert "date" in day
            assert "cash_pool" in day
            assert "funding_gap" in day
            assert "settlements" in day
            assert "repayments" in day
            assert "alerts" in day

    def test_calendar_shows_repayments(self, client, auth_headers):
        """Calendar should include credit card repayment info."""
        self._seed_card(client, auth_headers, bank_name="招商银行", bill_day=20, due_day=25)
        self._seed_settlements(client, auth_headers)
        resp = client.get("/api/v1/calendar", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # At least one day should have repayment entries if due_day falls within 30 days
        found_repayment = any(
            len(day["repayments"]) > 0 for day in data["days"]
        )
        # If due_day is within the next 30 days, we should find it
        assert found_repayment, "Expected at least one day with repayment info"

    def test_calendar_unauthorized(self, client):
        """Unauthenticated requests should return 401."""
        resp = client.get("/api/v1/calendar")
        assert resp.status_code == 401
