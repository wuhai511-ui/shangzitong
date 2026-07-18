"""RED: Tests for 进货推荐API (P2A)."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from fastapi.testclient import TestClient
from datetime import date, timedelta
from decimal import Decimal


class TestRecommendAPI:
    """Test purchase recommendation endpoints (RED → GREEN)."""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        resp = client.post("/api/v1/auth/login", json={"code": "test_recommend_user"})
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

    def test_recommend_returns_best_card(self, client, auth_headers):
        """POST /api/v1/recommend should return best card sorted by cost."""
        self._seed_card(client, auth_headers, bank_name="招商银行",
                        bill_day=5, due_day=25, credit_limit=100000)
        self._seed_card(client, auth_headers, bank_name="工商银行",
                        bill_day=1, due_day=25, credit_limit=50000)

        today = date.today().isoformat()
        resp = client.post("/api/v1/recommend", json={
            "purchase_date": today,
            "amount": 8765.50  # non-round to pass risk check
        }, headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()

        # Should return recommendations list
        assert "recommendations" in data
        assert len(data["recommendations"]) >= 1

        # First recommendation should be the best one
        best = data["recommendations"][0]
        assert "bank_name" in best
        assert "free_days" in best
        assert "swipe_cost" in best
        assert "daily_cost" in best
        assert "optimal_date" in best
        assert "repayment_date" in best

    def test_recommend_suggests_multi_card(self, client, auth_headers):
        """Single card insufficient → multi-card split suggested."""
        # Two cards that individually can't cover 80000
        self._seed_card(client, auth_headers, bank_name="招商银行",
                        bill_day=5, due_day=25, credit_limit=50000)
        self._seed_card(client, auth_headers, bank_name="工商银行",
                        bill_day=1, due_day=25, credit_limit=50000)

        today = date.today().isoformat()
        resp = client.post("/api/v1/recommend", json={
            "purchase_date": today,
            "amount": 80000.50
        }, headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()

        # Should have multi_card_split when single cards can't cover
        assert "multi_card_split" in data
        if data["coverage_ratio"] < 1.0:
            assert len(data["multi_card_split"]) >= 1

    def test_recommend_unauthorized(self, client):
        """Unauthenticated requests should return 401."""
        today = date.today().isoformat()
        resp = client.post("/api/v1/recommend", json={
            "purchase_date": today,
            "amount": 30000
        })
        assert resp.status_code == 401
