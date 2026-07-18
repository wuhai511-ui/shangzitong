"""Tests for stop-loss recommendation API."""
import pytest
import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from fastapi.testclient import TestClient


class TestStopLossAPI:
    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        resp = client.post("/api/v1/auth/login", json={"code": "test_stoploss"})
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def _setup_card(self, client, headers):
        return client.post("/api/v1/cards", json={
            "bank_name": "招商银行", "card_tail": "1111",
            "credit_limit": 50000, "used_limit": 30000,
            "bill_day": 5, "due_day": 25,
            "interest_rate": 0.0005, "min_payment_ratio": 0.1,
            "swipe_fee_rate": 0.006
        }, headers=headers).json()

    def test_stoploss_returns_three_options(self, client, auth_headers):
        """POST /api/v1/stoploss should return 3 plan options."""
        card = self._setup_card(client, auth_headers)
        resp = client.post("/api/v1/stoploss", json={
            "card_id": card["id"], "gap_amount": 5000
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "plan_a" in data  # full repayment via loan
        assert "plan_b" in data  # minimum payment
        assert "plan_c" in data  # installment
        assert "recommendation" in data

    def test_stoploss_unauthorized(self, client):
        resp = client.post("/api/v1/stoploss", json={
            "card_id": 1, "gap_amount": 1000
        })
        assert resp.status_code == 401
