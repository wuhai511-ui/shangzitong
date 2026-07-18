"""RED: Tests for settlement forecast API."""
import pytest
import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from fastapi.testclient import TestClient
from datetime import date, timedelta
from decimal import Decimal


class TestSettlementAPI:
    """Test settlement forecast endpoints (RED)."""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        resp = client.post("/api/v1/auth/login", json={"code": "test_forecast_user"})
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def _seed_settlements(self, client, auth_headers):
        """Insert some historical settlement data via upload."""
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

    def test_forecast_returns_30_days(self, client, auth_headers):
        """GET /api/v1/settlements/forecast should return 30 days."""
        self._seed_settlements(client, auth_headers)
        resp = client.get("/api/v1/settlements/forecast", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["days"] == 30
        assert len(data["forecast"]) == 30

    def test_forecast_has_confidence(self, client, auth_headers):
        """Each forecast entry should have confidence and arrival."""
        self._seed_settlements(client, auth_headers)
        resp = client.get("/api/v1/settlements/forecast", headers=auth_headers)
        data = resp.json()
        for entry in data["forecast"]:
            assert "date" in entry
            assert "amount" in entry
            assert "confidence" in entry
            assert "arrival" in entry
