from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.cashflow_service import aggregate_settlement_history


def test_aggregate_settlement_history_sums_same_day():
    rows = [
        SimpleNamespace(settle_date=date(2026, 7, 1), amount=Decimal("100.00")),
        SimpleNamespace(settle_date=date(2026, 7, 1), amount=Decimal("250.50")),
    ]

    assert aggregate_settlement_history(rows) == {
        date(2026, 7, 1): Decimal("350.50")
    }
