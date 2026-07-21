"""Tests for manual settlement entry API and cashflow replacement."""
import os
import sys
from datetime import date, timedelta
from decimal import Decimal

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
        json={"code": f"manual-settlement-{request.node.name}"},
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


def test_create_day_entry_and_list(client, auth_headers):
    today = date.today()
    payload = {
        "period_type": "day",
        "period_date": str(today - timedelta(days=14)),
        "amount": "1234.56",
        "note": "test day",
    }
    resp = client.post("/api/v1/manual-settlement", json=payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["period_type"] == "day"
    assert body["period_date"] == str(today - timedelta(days=14))
    assert body["amount"] == "1234.56"
    assert body["note"] == "test day"
    assert "id" in body and "created_at" in body

    listing = client.get("/api/v1/manual-settlement", headers=auth_headers)
    assert listing.status_code == 200
    rows = listing.json()
    assert len(rows) == 1
    assert rows[0]["id"] == body["id"]
    assert rows[0]["amount"] == "1234.56"


def test_create_month_entry_normalizes_to_first(client, auth_headers):
    payload = {
        "period_type": "month",
        "period_date": "2026-06-15",
        "amount": "300000",
    }
    resp = client.post("/api/v1/manual-settlement", json=payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["period_type"] == "month"
    assert body["period_date"] == "2026-06-01"
    assert body["amount"] == "300000.00"
    assert body["note"] is None


def test_amount_negative_rejected(client, auth_headers):
    payload = {
        "period_type": "day",
        "period_date": str(date.today()),
        "amount": "-1.00",
    }
    resp = client.post("/api/v1/manual-settlement", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_delete_soft_deletes_then_404(client, auth_headers):
    resp = client.post(
        "/api/v1/manual-settlement",
        json={
            "period_type": "day",
            "period_date": str(date.today()),
            "amount": "10.00",
        },
        headers=auth_headers,
    )
    entry_id = resp.json()["id"]

    delete_resp = client.delete(
        f"/api/v1/manual-settlement/{entry_id}", headers=auth_headers
    )
    assert delete_resp.status_code == 200

    listing = client.get("/api/v1/manual-settlement", headers=auth_headers)
    assert listing.json() == []

    second_delete = client.delete(
        f"/api/v1/manual-settlement/{entry_id}", headers=auth_headers
    )
    assert second_delete.status_code == 404


def test_cross_user_delete_returns_404(client):
    owner = client.post(
        "/api/v1/auth/login", json={"code": "manual-owner-cross-user"}
    ).json()
    owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}

    other = client.post(
        "/api/v1/auth/login", json={"code": "manual-other-cross-user"}
    ).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    create = client.post(
        "/api/v1/manual-settlement",
        json={
            "period_type": "day",
            "period_date": str(date.today()),
            "amount": "5.00",
        },
        headers=owner_headers,
    )
    entry_id = create.json()["id"]

    cross = client.delete(
        f"/api/v1/manual-settlement/{entry_id}", headers=other_headers
    )
    assert cross.status_code == 404

    owner_listing = client.get(
        "/api/v1/manual-settlement", headers=owner_headers
    )
    assert len(owner_listing.json()) == 1


def test_cashflow_uses_manual_when_present(client, auth_context):
    today = date.today()
    headers = auth_context["headers"]
    user_id = auth_context["user_id"]

    manual_date = today - timedelta(days=14)
    distinctive_amount = "7777.77"

    create = client.post(
        "/api/v1/manual-settlement",
        json={
            "period_type": "day",
            "period_date": str(manual_date),
            "amount": distinctive_amount,
        },
        headers=headers,
    )
    assert create.status_code == 201

    uploaded_date = today - timedelta(days=21)
    db = SessionLocal()
    try:
        source = DataSource(
            user_id=user_id,
            source_type="upload",
            provider="test",
            label="manual-replace",
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        db.add(
            Settlement(
                source_id=source.id,
                user_id=user_id,
                settle_date=uploaded_date,
                amount=Decimal("1.11"),
                provider="test",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/cashflow?days=7", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()

    settlement_values = [day["settlements"] for day in payload["days"]]

    def matches_history(day, history_amount):
        # The forecast for `day` uses history entries at day-7/14/21/28.
        return day - timedelta(days=14) == manual_date

    forecast_day = next(
        (d for d in payload["days"] if matches_history(date.fromisoformat(d["date"]), Decimal(distinctive_amount))),
        None,
    )
    assert forecast_day is not None, "expected a forecast day derived from manual history"
    assert forecast_day["settlements"] == distinctive_amount

    assert "1.11" not in settlement_values


def test_cashflow_unchanged_without_manual(client, auth_context):
    today = date.today()
    headers = auth_context["headers"]
    user_id = auth_context["user_id"]

    uploaded_date = today - timedelta(days=7)
    db = SessionLocal()
    try:
        source = DataSource(
            user_id=user_id,
            source_type="upload",
            provider="test",
            label="no-manual",
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        db.add(
            Settlement(
                source_id=source.id,
                user_id=user_id,
                settle_date=uploaded_date,
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
    assert payload["days"][0]["settlements"] == "50.00"
