"""RED: Tests for 诊断报告API (P3B)."""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestReportAPI:
    """Test the monthly diagnostic report endpoint."""

    @pytest.fixture
    def client(self):
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        resp = client.post("/api/v1/auth/login", json={"code": "test_report_user"})
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def _seed_card(self, client, auth_headers, bank_name="招商银行", bill_day=5, due_day=25,
                   credit_limit=50000, used_limit=10000):
        resp = client.post("/api/v1/cards", json={
            "bank_name": bank_name, "card_tail": "1234",
            "credit_limit": credit_limit, "used_limit": used_limit,
            "bill_day": bill_day, "due_day": due_day
        }, headers=auth_headers)
        assert resp.status_code == 200
        return resp.json()

    def test_monthly_report(self, client, auth_headers):
        """GET /api/v1/report/monthly should return a diagnostic report."""
        self._seed_card(client, auth_headers, bank_name="招商银行",
                        bill_day=5, due_day=25, credit_limit=50000, used_limit=10000)

        resp = client.get("/api/v1/report/monthly", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "grade" in data
        assert "dimensions" in data
        assert "card_count" in data
        assert "total_limit" in data
        assert "avg_utilization" in data
        assert "suggestions" in data

    def test_report_has_score(self, client, auth_headers):
        """Report should include a valid health score between 0-100."""
        self._seed_card(client, auth_headers, bank_name="招商银行",
                        bill_day=5, due_day=25, credit_limit=50000, used_limit=10000)

        resp = client.get("/api/v1/report/monthly", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["score"], (int, float))
        assert 0 <= data["score"] <= 100

    def test_report_unauthorized(self, client):
        """Unauthenticated requests should return 401."""
        resp = client.get("/api/v1/report/monthly")
        assert resp.status_code == 401
