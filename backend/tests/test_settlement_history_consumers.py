from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api import forecast
from core.database import SessionLocal
from models.datasource import DataSource, Settlement


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def all(self):
        return self.rows


class _Database:
    def __init__(self, settlements):
        self.settlements = settlements

    def query(self, model):
        if model is Settlement:
            return _Query(self.settlements)
        raise AssertionError(f"Unexpected model query: {model}")


@pytest.fixture
def same_day_settlements():
    settlement_day = date(2026, 7, 1)
    return [
        SimpleNamespace(settle_date=settlement_day, amount=Decimal("100.00")),
        SimpleNamespace(settle_date=settlement_day, amount=Decimal("250.50")),
    ]


def test_forecast_passes_same_day_settlement_sum_to_build_forecast(
    monkeypatch, same_day_settlements
):
    captured = {}

    def capture_forecast(today, history, days):
        captured["history"] = history
        return []

    monkeypatch.setattr(forecast, "build_forecast", capture_forecast)

    forecast.get_forecast(
        SimpleNamespace(id=1),
        _Database(same_day_settlements),
    )

    assert captured["history"] == {date(2026, 7, 1): Decimal("350.50")}


def test_calendar_consumes_canonical_duplicate_settlement_sum():
    """Calendar should receive the service's aggregated same-day forecast."""
    from app.main import app

    client = TestClient(app)
    login = client.post(
        "/api/v1/auth/login",
        json={"code": "calendar-canonical-duplicate-history"},
    )
    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }
    user_id = login.json()["user"]["id"]
    settlement_day = date.today() - timedelta(days=7)

    db = SessionLocal()
    try:
        source = DataSource(
            user_id=user_id,
            source_type="upload",
            provider="test",
            label="calendar-duplicate-history",
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        db.add_all(
            [
                Settlement(
                    source_id=source.id,
                    user_id=user_id,
                    settle_date=settlement_day,
                    amount=Decimal("100.00"),
                ),
                Settlement(
                    source_id=source.id,
                    user_id=user_id,
                    settle_date=settlement_day,
                    amount=Decimal("250.50"),
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/calendar", headers=headers)

    assert response.status_code == 200
    assert response.json()["days"][0]["settlements"] == [
        {"amount": "350.50"}
    ]
