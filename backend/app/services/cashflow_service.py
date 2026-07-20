from collections import defaultdict
from datetime import date, timedelta, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy.orm import Session

from algorithm.interest import next_repayment_date
from algorithm.models import CardInfo
from algorithm.settlement import build_forecast
from models.card import Card
from models.datasource import Settlement
from models.merchant_profile import MerchantProfile
from schemas.cashflow import CashflowDay, CashflowResponse, RepaymentEvent


ZERO = Decimal("0.00")


def aggregate_settlement_history(rows: Iterable) -> dict[date, Decimal]:
    totals: defaultdict[date, Decimal] = defaultdict(lambda: ZERO)
    for row in rows:
        totals[row.settle_date] += Decimal(row.amount)
    return dict(totals)


def _to_card_info(card: Card) -> CardInfo:
    return CardInfo(
        card_id=int(card.id),
        bank_name=str(card.bank_name),
        credit_limit=Decimal(card.credit_limit),
        temp_limit=Decimal(card.temp_limit),
        used_limit=Decimal(card.used_limit),
        overpayment=Decimal(card.overpayment),
        bill_day=int(card.bill_day),
        due_day=int(card.due_day),
        swipe_fee_rate=Decimal(card.swipe_fee_rate),
        interest_rate=Decimal(card.interest_rate),
        min_payment_ratio=Decimal(card.min_payment_ratio),
        installment_amount=Decimal(card.installment_amount),
        bill_day_inclusive=bool(card.bill_day_inclusive),
    )


def build_repayment_schedule(
    cards: Iterable[Card],
    start_date: date,
    days: int,
) -> dict[date, list[RepaymentEvent]]:
    repayments: dict[date, list[RepaymentEvent]] = {}
    end_date = start_date + timedelta(days=days)

    for card in cards:
        if getattr(card, "status", 1) != 1 or getattr(card, "deleted_at", None) is not None:
            continue

        repay_date = next_repayment_date(_to_card_info(card), start_date)
        if start_date <= repay_date < end_date:
            amount = Decimal(card.used_limit)
            event = RepaymentEvent(
                card_id=int(card.id),
                bank_name=str(card.bank_name),
                amount=amount,
                min_payment=amount * Decimal(card.min_payment_ratio),
            )
            repayments.setdefault(repay_date, []).append(event)

    return repayments


def roll_cashflow_days(
    start_date: date,
    days: int,
    opening_cash: Decimal,
    settlements: dict[date, Decimal],
    repayments: dict[date, list[Decimal]],
) -> list[CashflowDay]:
    balance = Decimal(opening_cash)
    result: list[CashflowDay] = []

    for offset in range(days):
        day = start_date + timedelta(days=offset)
        opening = balance
        inflow = Decimal(settlements.get(day, ZERO))
        repayment = sum(repayments.get(day, []), ZERO)
        balance = opening + inflow - repayment
        result.append(
            CashflowDay(
                date=day,
                opening_balance=opening,
                settlements=inflow,
                repayments=repayment,
                purchases=ZERO,
                other_outflows=ZERO,
                closing_balance=balance,
                funding_gap=max(ZERO, -balance),
                events=[],
            )
        )

    return result


def build_cashflow(
    db: Session,
    user_id: int,
    start_date: date,
    days: int = 30,
) -> CashflowResponse:
    profile = (
        db.query(MerchantProfile)
        .filter(MerchantProfile.user_id == user_id)
        .first()
    )
    opening_cash = (
        Decimal(profile.available_cash)
        if profile is not None and profile.available_cash is not None
        else ZERO
    )

    cutoff = start_date - timedelta(days=90)
    settlement_rows = (
        db.query(Settlement)
        .filter(
            Settlement.user_id == user_id,
            Settlement.settle_date >= cutoff,
            Settlement.deleted_at.is_(None),
        )
        .all()
    )
    history = aggregate_settlement_history(settlement_rows)
    forecasts = build_forecast(
        start_date - timedelta(days=1),
        history,
        days=days,
    )
    settlement_forecast = {
        forecast.date: Decimal(forecast.amount)
        for forecast in forecasts
    }

    cards = (
        db.query(Card)
        .filter(
            Card.user_id == user_id,
            Card.status == 1,
            Card.deleted_at.is_(None),
        )
        .all()
    )
    repayment_schedule = build_repayment_schedule(cards, start_date, days)
    repayment_amounts = {
        day: [event.amount for event in events]
        for day, events in repayment_schedule.items()
    }

    ledger_days = roll_cashflow_days(
        start_date=start_date,
        days=days,
        opening_cash=opening_cash,
        settlements=settlement_forecast,
        repayments=repayment_amounts,
    )
    for ledger_day in ledger_days:
        ledger_day.events = [
            event.model_dump()
            for event in repayment_schedule.get(ledger_day.date, [])
        ]

    updated_at = (
        profile.available_cash_updated_at
        if profile is not None
        else None
    )
    if updated_at is not None and updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)

    return CashflowResponse(
        days=ledger_days,
        is_estimate=profile is None or profile.available_cash is None,
        available_cash=(
            Decimal(profile.available_cash)
            if profile is not None and profile.available_cash is not None
            else None
        ),
        available_cash_updated_at=updated_at,
    )
