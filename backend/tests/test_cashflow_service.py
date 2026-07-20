from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from schemas.cashflow import RepaymentEvent
from app.services.cashflow_service import (
    aggregate_settlement_history,
    build_repayment_schedule,
    roll_cashflow_days,
)


def test_aggregate_settlement_history_sums_same_day():
    rows = [
        SimpleNamespace(settle_date=date(2026, 7, 1), amount=Decimal("100.00")),
        SimpleNamespace(settle_date=date(2026, 7, 1), amount=Decimal("250.50")),
    ]

    assert aggregate_settlement_history(rows) == {
        date(2026, 7, 1): Decimal("350.50")
    }


def test_daily_gap_uses_post_transaction_negative_balance():
    result = roll_cashflow_days(
        start_date=date(2026, 7, 1),
        days=1,
        opening_cash=Decimal("100.00"),
        settlements={date(2026, 7, 1): Decimal("50.00")},
        repayments={date(2026, 7, 1): [Decimal("200.00")]},
    )

    assert result[0].closing_balance == Decimal("-50.00")
    assert result[0].funding_gap == Decimal("50.00")
    assert result[0].purchases == Decimal("0.00")
    assert result[0].other_outflows == Decimal("0.00")


def test_repayment_schedule_returns_typed_events():
    card = SimpleNamespace(
        id=7,
        bank_name="测试银行",
        credit_limit=Decimal("1000.00"),
        temp_limit=Decimal("0.00"),
        used_limit=Decimal("200.00"),
        overpayment=Decimal("0.00"),
        bill_day=1,
        due_day=10,
        swipe_fee_rate=Decimal("0.006"),
        interest_rate=Decimal("0.0005"),
        min_payment_ratio=Decimal("0.10"),
        installment_amount=Decimal("0.00"),
        bill_day_inclusive=0,
        status=1,
        deleted_at=None,
    )

    schedule = build_repayment_schedule(
        cards=[card],
        start_date=date(2026, 7, 1),
        days=30,
    )

    event = schedule[date(2026, 7, 10)][0]
    assert isinstance(event, RepaymentEvent)
    assert event.card_id == 7
    assert event.bank_name == "测试银行"
    assert event.amount == Decimal("200.00")
    assert event.min_payment == Decimal("20.0000")
