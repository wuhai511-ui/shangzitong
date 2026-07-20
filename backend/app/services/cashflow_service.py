from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Iterable


def aggregate_settlement_history(rows: Iterable) -> dict[date, Decimal]:
    totals: defaultdict[date, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for row in rows:
        totals[row.settle_date] += Decimal(row.amount)
    return dict(totals)
