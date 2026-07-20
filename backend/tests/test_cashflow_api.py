"""Tests for the canonical daily cashflow ledger API."""
from datetime import date, timedelta
from decimal import Decimal
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
from fastapi.testclient import TestClient

from core.database import SessionLocal
from models.datasource import DataSource, Settlement


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


@pytest.fixture
def auth_context(client, request):
    response = client.post(
        "/api/v1/auth/login",
        json={"code": f"cashflow-ledger-{request.node.name}"},
    )
    return {
        "headers": {
            "Authorization": f"Bearer {response.json()['access_token']}"
        },
        "user_id": response.json()["user"]["id"],
    }


@pytest.fixture
def auth_headers(auth_context):
    return auth_context["headers"]


def test_unset_available_cash_marks_response_estimated(client, auth_headers):
    response = client.get("/api/v1/cashflow?days=30", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["available_cash"] is None
    assert response.json()["is_estimate"] is True
    assert len(response.json()["days"]) == 30
    assert response.json()["days"][0]["opening_balance"] == "0.00"


@pytest.mark.parametrize("days", [0, 91])
def test_cashflow_rejects_days_outside_supported_range(client, auth_headers, days):
    response = client.get(f"/api/v1/cashflow?days={days}", headers=auth_headers)

    assert response.status_code == 422


def test_cashflow_api_formats_and_rolls_real_events(client, auth_context):
    today = date.today()
    due_date = today + timedelta(days=5)
    headers = auth_context["headers"]
    user_id = auth_context["user_id"]

    profile_response = client.put(
        "/api/v1/profile/cash",
        json={"available_cash": "100.00"},
        headers=headers,
    )
    assert profile_response.status_code == 200

    card_response = client.post(
        "/api/v1/cards",
        json={
            "bank_name": "Integration Bank",
            "credit_limit": "1000.00",
            "used_limit": "200.00",
            "bill_day": 1,
            "due_day": due_date.day,
            "min_payment_ratio": "0.10",
        },
        headers=headers,
    )
    assert card_response.status_code == 200
    card_id = card_response.json()["id"]

    db = SessionLocal()
    try:
        source = DataSource(
            user_id=user_id,
            source_type="upload",
            provider="test",
            label="cashflow-integration",
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        db.add(
            Settlement(
                source_id=source.id,
                user_id=user_id,
                settle_date=today - timedelta(days=7),
                amount=Decimal("50.00"),
                provider="test",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/cashflow?days=7", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["available_cash"] == "100.00"
    assert payload["is_estimate"] is False
    assert payload["days"][0]["settlements"] == "50.00"

    money_fields = {
        "opening_balance",
        "settlements",
        "repayments",
        "purchases",
        "other_outflows",
        "closing_balance",
        "funding_gap",
    }
    for day in payload["days"]:
        for field in money_fields:
            assert isinstance(day[field], str)
            assert day[field] == f"{Decimal(day[field]):.2f}"

    due_day = next(day for day in payload["days"] if day["date"] == str(due_date))
    assert due_day["repayments"] == "200.00"
    assert due_day["closing_balance"] == "-50.00"
    assert due_day["funding_gap"] == "50.00"
    assert due_day["events"] == [
        {
            "type": "repayment",
            "card_id": card_id,
            "bank_name": "Integration Bank",
            "amount": "200.00",
            "min_payment": "20.00",
        }
    ]

    due_index = payload["days"].index(due_day)
    assert payload["days"][due_index + 1]["opening_balance"] == "-50.00"
