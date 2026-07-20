from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from api import alerts, calendar, forecast, schedule
from models.card import Card
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
        if model is Card:
            return _Query([])
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


@pytest.mark.parametrize(
    ("consumer", "invoke"),
    [
        (forecast, lambda module, db, user: module.get_forecast(user, db)),
        (calendar, lambda module, db, user: module.get_calendar(user, db)),
        (schedule, lambda module, db, user: module.get_schedule(user, db)),
        (
            alerts,
            lambda module, db, user: module._build_upcoming_repayments(
                db, user, date.today(), days=7
            ),
        ),
    ],
    ids=["forecast", "calendar", "schedule", "alerts"],
)
def test_consumers_pass_same_day_settlement_sum_to_build_forecast(
    monkeypatch, same_day_settlements, consumer, invoke
):
    captured = {}

    def capture_forecast(today, history, days):
        captured["history"] = history
        return []

    monkeypatch.setattr(consumer, "build_forecast", capture_forecast)

    invoke(consumer, _Database(same_day_settlements), SimpleNamespace(id=1))

    assert captured["history"] == {date(2026, 7, 1): Decimal("350.50")}
