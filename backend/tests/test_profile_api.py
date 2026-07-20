"""Tests for the optional available-cash profile API."""
from datetime import datetime
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
    response = client.post("/api/v1/auth/login", json={"code": "cash-profile-user"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_cash_profile_distinguishes_unset_from_zero(client, auth_headers):
    initial = client.get("/api/v1/profile/cash", headers=auth_headers)
    assert initial.status_code == 200
    assert initial.json() == {
        "available_cash": None,
        "available_cash_updated_at": None,
        "is_estimate": True,
    }

    saved = client.put(
        "/api/v1/profile/cash",
        json={"available_cash": "0.00"},
        headers=auth_headers,
    )
    assert saved.status_code == 200
    assert saved.json()["available_cash"] == "0.00"
    assert saved.json()["is_estimate"] is False
    timestamp = datetime.fromisoformat(saved.json()["available_cash_updated_at"].replace("Z", "+00:00"))
    assert timestamp.tzinfo is not None


def test_cash_profile_can_be_cleared(client, auth_headers):
    client.put("/api/v1/profile/cash", json={"available_cash": "25.00"}, headers=auth_headers)
    cleared = client.put("/api/v1/profile/cash", json={"available_cash": None}, headers=auth_headers)
    assert cleared.status_code == 200
    assert cleared.json()["available_cash"] is None
    assert cleared.json()["available_cash_updated_at"] is None
    assert cleared.json()["is_estimate"] is True
