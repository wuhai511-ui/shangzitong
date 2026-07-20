"""全局调度引擎API — P2B: 30-day global scheduling engine.

Combines settlement forecast + repayment tracking + purchase recommendations
into a day-by-day 30-day operational plan.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import SessionLocal
from schemas.auth import UserInfo
from api.auth import get_current_user_dependency
from models.card import Card
from models.datasource import Settlement
from algorithm.settlement import build_forecast
from services.cashflow_service import aggregate_settlement_history
from algorithm.interest import next_repayment_date
from algorithm.models import CardInfo
from datetime import date, timedelta
from decimal import Decimal

router = APIRouter(prefix="/api/v1", tags=["schedule"])


def get_db():
    """FastAPI dependency: yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _to_card_info(card: Card) -> CardInfo:
    return CardInfo(
        card_id=int(card.id) if card.id else 0,
        bank_name=str(card.bank_name),
        credit_limit=card.credit_limit,
        temp_limit=card.temp_limit,
        used_limit=card.used_limit,
        overpayment=card.overpayment,
        bill_day=int(card.bill_day),
        due_day=int(card.due_day),
        swipe_fee_rate=card.swipe_fee_rate,
        interest_rate=card.interest_rate,
        min_payment_ratio=card.min_payment_ratio,
        installment_amount=card.installment_amount,
        bill_day_inclusive=bool(card.bill_day_inclusive),
    )


def _build_repayment_map(cards: list[Card], today: date, days: int) -> dict[date, list[dict]]:
    """Build a map of date → list of repayment entries for the given cards."""
    repayments: dict[date, list[dict]] = {}
    end_date = today + timedelta(days=days)

    for card in cards:
        card_info = _to_card_info(card)
        repay_date = next_repayment_date(card_info, today)
        if today <= repay_date <= end_date:
            min_payment = card.used_limit * card.min_payment_ratio
            entry = {
                "card_id": int(card.id),
                "bank_name": str(card.bank_name),
                "amount": str(card.used_limit),
                "min_payment": str(min_payment),
            }
            repayments.setdefault(repay_date, []).append(entry)

    return repayments


@router.get("/schedule", response_model=None)
def get_schedule(current_user: UserInfo = Depends(get_current_user_dependency),
                 db=Depends(get_db)):
    """Return 30-day global schedule with cash_pool trend.

    Reuses calendar logic (settlement forecast + repayment tracking)
    and runs a day-by-day simulation for 30 days.
    """
    today = date.today()
    days = 30

    # Load user cards
    cards = db.query(Card).filter(
        Card.user_id == current_user.id,
        Card.deleted_at.is_(None),
    ).all()

    # Load historical settlements for forecast
    cutoff = today - timedelta(days=90)
    rows = db.query(Settlement).filter(
        Settlement.user_id == current_user.id,
        Settlement.settle_date >= cutoff,
        Settlement.deleted_at.is_(None),
    ).all()
    history = aggregate_settlement_history(rows)

    # Build settlement forecast
    forecasts = build_forecast(today, history, days=days)

    # Build repayment map
    repayments = _build_repayment_map(cards, today, days)

    # Build daily schedule with cumulative cash_pool
    cash_pool = Decimal("0")
    daily_entries = []

    for forecast in forecasts:
        daily_date = forecast.date
        # Add forecast settlement amount to cash pool
        cash_pool += forecast.amount

        # Get repayments for this day
        day_repayments = repayments.get(daily_date, [])
        # Subtract repayment amounts from cash pool
        for r in day_repayments:
            cash_pool -= Decimal(r["amount"])

        # Build alerts for this day
        alerts = []
        total_due = sum(Decimal(r["amount"]) for r in day_repayments)
        if total_due > Decimal("0") and cash_pool < total_due:
            gap = total_due - cash_pool
            alerts.append({
                "type": "funding_gap",
                "message": f"资金缺口 ¥{gap:.2f}，当日应还 ¥{total_due:.2f}",
            })

        day_entry = {
            "date": str(daily_date),
            "cash_pool": str(cash_pool),
            "settlements": [{"amount": str(forecast.amount)}],
            "repayments": day_repayments,
            "alerts": alerts,
        }
        daily_entries.append(day_entry)

    return {"days": daily_entries}
