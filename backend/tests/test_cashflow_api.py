"""Tests for the canonical daily cashflow ledger API."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    response = client.post("/api/v1/auth/login", json={"code": "cashflow-ledger-user"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


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
