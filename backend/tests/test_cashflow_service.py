from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import app.services.cashflow_service as cashflow_service
from core.database import SessionLocal
from models.datasource import DataSource, Settlement
from models.merchant_profile import MerchantProfile
from models.user import User
from schemas.cashflow import CashflowDay, CashflowResponse, RepaymentEvent
from app.services.cashflow_service import (
    aggregate_settlement_history,
    build_cashflow,
    build_repayment_schedule,
    roll_cashflow_days,
)


def _card(**overrides):
    values = {
        "id": 7,
        "bank_name": "Test Bank",
        "credit_limit": Decimal("1000.00"),
        "temp_limit": Decimal("0.00"),
        "used_limit": Decimal("200.00"),
        "overpayment": Decimal("0.00"),
        "bill_day": 1,
        "due_day": 10,
        "swipe_fee_rate": Decimal("0.006"),
        "interest_rate": Decimal("0.0005"),
        "min_payment_ratio": Decimal("0.10"),
        "installment_amount": Decimal("0.00"),
        "bill_day_inclusive": 0,
        "status": 1,
        "deleted_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _create_user(db, prefix):
    user = User(openid=f"{prefix}-{uuid4()}", nickname="", phone="")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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


def test_next_day_opening_equals_previous_day_closing():
    result = roll_cashflow_days(
        start_date=date(2026, 7, 1),
        days=2,
        opening_cash=Decimal("100.00"),
        settlements={date(2026, 7, 1): Decimal("25.00")},
        repayments={date(2026, 7, 1): [Decimal("150.00")]},
    )

    assert result[0].closing_balance == Decimal("-25.00")
    assert result[1].opening_balance == result[0].closing_balance


def test_repayment_schedule_returns_typed_events():
    schedule = build_repayment_schedule(
        cards=[_card()],
        start_date=date(2026, 7, 1),
        days=30,
    )

    event = schedule[date(2026, 7, 10)][0]
    assert isinstance(event, RepaymentEvent)
    assert event.card_id == 7
    assert event.bank_name == "Test Bank"
    assert event.amount == Decimal("200.00")
    assert event.min_payment == Decimal("20.0000")


def test_repayment_schedule_includes_due_date_on_start_boundary():
    schedule = build_repayment_schedule(
        cards=[_card(bill_day=1, due_day=1)],
        start_date=date(2026, 7, 1),
        days=30,
    )

    assert schedule[date(2026, 7, 1)][0].amount == Decimal("200.00")


def test_money_fields_serialize_as_two_decimal_strings():
    event = RepaymentEvent(
        card_id=7,
        bank_name="Test Bank",
        amount=Decimal("200"),
        min_payment=Decimal("20.0000"),
    )
    day = CashflowDay(
        date=date(2026, 7, 1),
        opening_balance=Decimal("1"),
        settlements=Decimal("2.345"),
        repayments=Decimal("3"),
        purchases=Decimal("4"),
        other_outflows=Decimal("5"),
        closing_balance=Decimal("-1.234"),
        funding_gap=Decimal("1.234"),
        events=[event.model_dump()],
    )
    response = CashflowResponse(
        days=[day],
        is_estimate=False,
        available_cash=Decimal("10"),
        available_cash_updated_at=None,
    )

    payload = response.model_dump(mode="json")
    assert payload["available_cash"] == "10.00"
    assert payload["days"][0] == {
        "date": "2026-07-01",
        "opening_balance": "1.00",
        "settlements": "2.35",
        "repayments": "3.00",
        "purchases": "4.00",
        "other_outflows": "5.00",
        "closing_balance": "-1.23",
        "funding_gap": "1.23",
        "events": [
            {
                "type": "repayment",
                "card_id": 7,
                "bank_name": "Test Bank",
                "amount": "200.00",
                "min_payment": "20.00",
            }
        ],
    }


def test_build_cashflow_excludes_on_or_after_start_settlements(monkeypatch):
    db = SessionLocal()
    start_date = date(2026, 7, 10)
    captured_dates = []
    try:
        user = _create_user(db, "cashflow-history")
        source = DataSource(
            user_id=user.id,
            source_type="upload",
            provider="test",
            label="history-boundary",
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        db.add_all(
            [
                Settlement(
                    source_id=source.id,
                    user_id=user.id,
                    settle_date=start_date.replace(day=9),
                    amount=Decimal("10.00"),
                ),
                Settlement(
                    source_id=source.id,
                    user_id=user.id,
                    settle_date=start_date,
                    amount=Decimal("20.00"),
                ),
                Settlement(
                    source_id=source.id,
                    user_id=user.id,
                    settle_date=start_date.replace(day=11),
                    amount=Decimal("30.00"),
                ),
            ]
        )
        db.commit()

        def capture_history(rows):
            captured_dates.extend(row.settle_date for row in rows)
            return {}

        monkeypatch.setattr(
            cashflow_service,
            "aggregate_settlement_history",
            capture_history,
        )

        build_cashflow(db, user.id, start_date, days=1)

        assert captured_dates == [date(2026, 7, 9)]
    finally:
        db.close()


def test_build_cashflow_ignores_soft_deleted_cash_profile():
    db = SessionLocal()
    try:
        user = _create_user(db, "cashflow-deleted-profile")
        db.add(
            MerchantProfile(
                user_id=user.id,
                available_cash=Decimal("75.00"),
                available_cash_updated_at=datetime(2026, 7, 1),
                deleted_at=datetime(2026, 7, 2),
            )
        )
        db.commit()

        result = build_cashflow(
            db=db,
            user_id=user.id,
            start_date=date(2026, 7, 10),
            days=1,
        )

        assert result.available_cash is None
        assert result.is_estimate is True
        assert result.days[0].opening_balance == Decimal("0.00")
    finally:
        db.close()
