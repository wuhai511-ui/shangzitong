"""Tests for Card CRUD API — Card model, schemas, and API endpoints."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from decimal import Decimal
from fastapi.testclient import TestClient


class TestCardSchema:
    """Test Pydantic schemas."""

    def test_card_create_valid(self):
        from app.schemas.card import CardCreate
        data = CardCreate(
            bank_name="招商银行", card_tail="1234",
            credit_limit=Decimal("50000"), used_limit=Decimal("10000"),
            bill_day=5, due_day=25
        )
        assert data.credit_limit == Decimal("50000")

    def test_card_create_invalid_limit(self):
        from app.schemas.card import CardCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CardCreate(
                bank_name="招商银行", card_tail="1234",
                credit_limit=Decimal("10000"), used_limit=Decimal("20000"),
                bill_day=5, due_day=25
            )

    def test_card_create_invalid_bill_day(self):
        from app.schemas.card import CardCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CardCreate(
                bank_name="招商银行", card_tail="1234",
                credit_limit=Decimal("50000"), bill_day=30, due_day=25
            )


class TestCardAPI:
    """Test Card CRUD API endpoints."""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        resp = client.post("/api/v1/auth/login", json={"code": "test_user_card"})
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_create_card(self, client, auth_headers):
        resp = client.post("/api/v1/cards", json={
            "bank_name": "招商银行", "card_tail": "1234",
            "credit_limit": 50000, "used_limit": 10000,
            "bill_day": 5, "due_day": 25
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["bank_name"] == "招商银行"

    def test_list_cards(self, client, auth_headers):
        client.post("/api/v1/cards", json={
            "bank_name": "招商银行", "card_tail": "1111",
            "credit_limit": 50000, "bill_day": 5, "due_day": 25
        }, headers=auth_headers)
        resp = client.get("/api/v1/cards", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_delete_card(self, client, auth_headers):
        create_resp = client.post("/api/v1/cards", json={
            "bank_name": "招商银行", "card_tail": "9999",
            "credit_limit": 50000, "bill_day": 5, "due_day": 25
        }, headers=auth_headers)
        card_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/cards/{card_id}", headers=auth_headers)
        assert resp.status_code == 200

        list_resp = client.get("/api/v1/cards", headers=auth_headers)
        card_ids = [c["id"] for c in list_resp.json()]
        assert card_id not in card_ids

    def test_unauthorized(self, client):
        resp = client.get("/api/v1/cards")
        assert resp.status_code == 401  # FastAPI returns 401 for missing auth
