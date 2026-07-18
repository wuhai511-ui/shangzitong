"""RED: Tests for Card CRUD API — Card model, schemas, and API endpoints."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient


class TestCardModel:
    """Test Card SQLAlchemy model (RED — not yet created)."""

    def test_card_creation(self):
        """Card model should accept all required fields."""
        from app.models.card import Card
        from app.core.database import SessionLocal, engine
        from app.models.base import Base
        Base.metadata.create_all(bind=engine)

        card = Card(
            user_id=1,
            bank_name="招商银行",
            card_tail="1234",
            credit_limit=Decimal("50000"),
            used_limit=Decimal("10000"),
            bill_day=5,
            due_day=25,
        )

        with SessionLocal() as session:
            session.add(card)
            session.commit()
            session.refresh(card)
            assert card.id is not None
            assert card.bank_name == "招商银行"
            assert card.avail_limit == Decimal("40000")
            assert card.deleted_at is None

    def test_soft_delete(self):
        """Soft delete should set deleted_at without removing row."""
        from app.models.card import Card
        from app.core.database import SessionLocal, engine
        from app.models.base import Base
        Base.metadata.create_all(bind=engine)

        with SessionLocal() as session:
            card = Card(user_id=1, bank_name="工商银行", card_tail="5678",
                        credit_limit=Decimal("100000"), bill_day=10, due_day=5)
            session.add(card)
            session.commit()

            card.soft_delete()
            session.commit()
            session.refresh(card)
            assert card.deleted_at is not None


class TestCardSchema:
    """Test Pydantic schemas (RED — not yet created)."""

    def test_card_create_valid(self):
        """CardCreate should accept valid data."""
        from app.schemas.card import CardCreate
        data = CardCreate(
            bank_name="招商银行", card_tail="1234",
            credit_limit=Decimal("50000"), used_limit=Decimal("10000"),
            bill_day=5, due_day=25
        )
        assert data.credit_limit == Decimal("50000")

    def test_card_create_invalid_limit(self):
        """CardCreate should reject used_limit > credit_limit."""
        from app.schemas.card import CardCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CardCreate(
                bank_name="招商银行", card_tail="1234",
                credit_limit=Decimal("10000"), used_limit=Decimal("20000"),
                bill_day=5, due_day=25
            )

    def test_card_create_invalid_bill_day(self):
        """CardCreate should reject bill_day outside 1-28."""
        from app.schemas.card import CardCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CardCreate(
                bank_name="招商银行", card_tail="1234",
                credit_limit=Decimal("50000"), bill_day=30, due_day=25
            )


class TestCardAPI:
    """Test Card CRUD API endpoints (RED — not yet created)."""

    @pytest.fixture
    def client(self):
        from app.main import app
        from app.core.database import engine as db_engine
        from app.models.base import Base
        Base.metadata.create_all(bind=db_engine)
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        """Create a user and get auth token."""
        # Register via mock login
        resp = client.post("/api/v1/auth/login", json={"code": "test_user_card"})
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_create_card(self, client, auth_headers):
        """POST /api/v1/cards should create a card."""
        resp = client.post("/api/v1/cards", json={
            "bank_name": "招商银行", "card_tail": "1234",
            "credit_limit": 50000, "used_limit": 10000,
            "bill_day": 5, "due_day": 25
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["bank_name"] == "招商银行"
        assert data["interest_free_info"]["free_days"] > 0

    def test_list_cards(self, client, auth_headers):
        """GET /api/v1/cards should list user's cards."""
        # Create one card first
        client.post("/api/v1/cards", json={
            "bank_name": "招商银行", "card_tail": "1111",
            "credit_limit": 50000, "bill_day": 5, "due_day": 25
        }, headers=auth_headers)
        resp = client.get("/api/v1/cards", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_delete_card(self, client, auth_headers):
        """DELETE /api/v1/cards/{id} should soft-delete."""
        create_resp = client.post("/api/v1/cards", json={
            "bank_name": "招商银行", "card_tail": "9999",
            "credit_limit": 50000, "bill_day": 5, "due_day": 25
        }, headers=auth_headers)
        card_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/cards/{card_id}", headers=auth_headers)
        assert resp.status_code == 200

        # Card should no longer appear in list
        list_resp = client.get("/api/v1/cards", headers=auth_headers)
        card_ids = [c["id"] for c in list_resp.json()]
        assert card_id not in card_ids

    def test_unauthorized(self, client):
        """Card API should reject unauthorized requests."""
        resp = client.get("/api/v1/cards")
        assert resp.status_code == 401
