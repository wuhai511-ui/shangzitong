from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from api import forecast
from models.datasource import Settlement


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
