"""RED: Tests for 还款提醒推送 (Module 8)."""
import pytest
import sys
import os
import io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from fastapi.testclient import TestClient
from datetime import date, timedelta
from decimal import Decimal


class TestAlertsAPI:
    """Test alert/notification endpoints (RED → GREEN)."""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        resp = client.post("/api/v1/auth/login", json={"code": "test_alerts_user"})
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def _seed_card(self, client, auth_headers, bank_name="招商银行", bill_day=20, due_day=25,
                   credit_limit=50000, used_limit=20000):
        resp = client.post("/api/v1/cards", json={
            "bank_name": bank_name, "card_tail": "1234",
            "credit_limit": credit_limit, "used_limit": used_limit,
            "bill_day": bill_day, "due_day": due_day
        }, headers=auth_headers)
        assert resp.status_code == 200
        return resp.json()["id"]

    def _seed_settlements(self, client, auth_headers):
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

    def test_alerts_returns_upcoming(self, client, auth_headers):
        """GET /api/v1/alerts/upcoming should return upcoming repayments in 7 days."""
        self._seed_card(client, auth_headers, bank_name="招商银行", bill_day=20, due_day=25)
        self._seed_settlements(client, auth_headers)
        resp = client.get("/api/v1/alerts/upcoming", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "repayments" in data
        # Should have at least one upcoming repayment
        assert len(data["repayments"]) >= 1
        for r in data["repayments"]:
            assert "card_id" in r
            assert "bank_name" in r
            assert "due_date" in r
            assert "amount" in r
            assert "funding_gap" in r
            assert "gap_warning" in r

    def test_alerts_returns_gaps(self, client, auth_headers):
        """When cash flow is insufficient, gap_warning should be True."""
        # Create card with large used_limit that likely exceeds cash pool
        self._seed_card(client, auth_headers, bank_name="工商银行", bill_day=20, due_day=25,
                        credit_limit=200000, used_limit=100000)
        self._seed_settlements(client, auth_headers)
        resp = client.get("/api/v1/alerts/upcoming", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # At least one repayment should have a gap warning since 100k > forecasted settlements
        found_gap = any(r.get("gap_warning") for r in data["repayments"])
        assert found_gap, "Expected at least one repayment with gap_warning=True"

    def test_alerts_unauthorized(self, client):
        """Unauthenticated requests should return 401."""
        resp = client.get("/api/v1/alerts/upcoming")
        assert resp.status_code == 401

    def test_calendar_schedule_and_alerts_share_canonical_gap(self, client):
        """All cashflow consumers should expose the ledger's post-transaction gap."""
        login = client.post(
            "/api/v1/auth/login",
            json={"code": "cross-endpoint-canonical-gap"},
        )
        headers = {
            "Authorization": f"Bearer {login.json()['access_token']}"
        }
        due_date = date.today() + timedelta(days=5)

        profile = client.put(
            "/api/v1/profile/cash",
            json={"available_cash": "100.00"},
            headers=headers,
        )
        assert profile.status_code == 200
        card = client.post(
            "/api/v1/cards",
            json={
                "bank_name": "Canonical Gap Bank",
                "credit_limit": "1000.00",
                "used_limit": "200.00",
                "bill_day": 1,
                "due_day": due_date.day,
            },
            headers=headers,
        )
        assert card.status_code == 200

        calendar = client.get(
            "/api/v1/calendar", headers=headers
        ).json()["days"]
        schedule = client.get(
            "/api/v1/schedule", headers=headers
        ).json()["days"]

        assert [day["funding_gap"] for day in calendar] == [
            day["funding_gap"] for day in schedule
        ]
        gap_day = next(
            day
            for day in calendar
            if day["date"] == str(due_date)
        )
        assert Decimal(gap_day["funding_gap"]) == Decimal("100.00")

        upcoming = client.get(
            "/api/v1/alerts/upcoming", headers=headers
        ).json()
        matching = [
            repayment
            for repayment in upcoming["repayments"]
            if repayment["due_date"] == gap_day["date"]
        ]
        assert matching
        assert all(
            Decimal(repayment["funding_gap"])
            == Decimal(gap_day["funding_gap"])
            for repayment in matching
        )
