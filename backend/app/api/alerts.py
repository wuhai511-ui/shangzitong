"""还款提醒推送API — upcoming repayments and daily summary with gap warnings."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import SessionLocal
from schemas.auth import UserInfo
from api.auth import get_current_user_dependency
from models.card import Card
from models.datasource import Settlement
from algorithm.settlement import build_forecast
from algorithm.interest import next_repayment_date
from algorithm.models import CardInfo
from datetime import date, timedelta
from decimal import Decimal

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


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


def _compute_cash_pool_at_date(
    forecasts: list, repayments_map: dict[date, list[dict]], target_date: date
) -> Decimal:
    """Compute cumulative cash pool at target_date considering inflows and outflows."""
    cash = Decimal("0")
    for f in forecasts:
        if f.date > target_date:
            break
        cash += f.amount
    # Subtract all repayments up to and including target_date
    for rdate in sorted(repayments_map.keys()):
        if rdate > target_date:
            break
        for r in repayments_map[rdate]:
            cash -= Decimal(r["amount"])
    return cash


def _build_upcoming_repayments(db, current_user, today, days=7):
    """Build list of upcoming repayments with gap warnings."""
    end_date = today + timedelta(days=days)

    # Load cards
    cards = db.query(Card).filter(
        Card.user_id == current_user.id,
        Card.deleted_at.is_(None),
    ).all()

    # Load settlement history and forecast
    cutoff = today - timedelta(days=90)
    rows = db.query(Settlement).filter(
        Settlement.user_id == current_user.id,
        Settlement.settle_date >= cutoff,
        Settlement.deleted_at.is_(None),
    ).all()
    history = {r.settle_date: r.amount for r in rows}
    forecasts = build_forecast(today, history, days=days)

    # Build repayment map
    repayments_map: dict[date, list[dict]] = {}
    all_repayments: list[dict] = []

    for card in cards:
        card_info = _to_card_info(card)
        repay_date = next_repayment_date(card_info, today)
        if today <= repay_date <= end_date:
            min_payment = card.used_limit * card.min_payment_ratio
            entry = {
                "card_id": int(card.id),
                "bank_name": str(card.bank_name),
                "due_date": str(repay_date),
                "amount": str(card.used_limit),
                "min_payment": str(min_payment),
                "gap_warning": False,
                "recommended_action": "",
            }
            repayments_map.setdefault(repay_date, []).append(entry)
            all_repayments.append(entry)

    # Check for cash gaps
    for r in all_repayments:
        due_date = date.fromisoformat(r["due_date"])
        cash_pool = _compute_cash_pool_at_date(forecasts, repayments_map, due_date)
        total_due_that_day = sum(
            Decimal(r2["amount"]) for r2 in repayments_map.get(due_date, [])
        )
        if cash_pool < total_due_that_day:
            r["gap_warning"] = True
            gap = total_due_that_day - cash_pool
            r["recommended_action"] = f"建议提前补充资金 ¥{gap:.2f}，或使用分期/最低还款"

    return all_repayments


@router.get("/upcoming", response_model=None)
def get_upcoming(current_user: UserInfo = Depends(get_current_user_dependency),
                 db=Depends(get_db)):
    """Return upcoming repayments in next 7 days with gap warnings."""
    today = date.today()
    repayments = _build_upcoming_repayments(db, current_user, today, days=7)
    return {"repayments": repayments}


@router.get("/daily-summary", response_model=None)
def get_daily_summary(current_user: UserInfo = Depends(get_current_user_dependency),
                      db=Depends(get_db)):
    """Return today's summary: total due, forecasted settlements, gap."""
    today = date.today()
    repayments = _build_upcoming_repayments(db, current_user, today, days=0)

    # Filter repayments due today
    today_repayments = [r for r in repayments if r["due_date"] == str(today)]
    total_due = sum(Decimal(r["amount"]) for r in today_repayments)

    # Forecasted settlements for today
    rows = db.query(Settlement).filter(
        Settlement.user_id == current_user.id,
        Settlement.settle_date == today,
        Settlement.deleted_at.is_(None),
    ).all()
    today_settlements = sum(r.amount for r in rows)

    gap = max(Decimal("0"), total_due - today_settlements)

    return {
        "date": str(today),
        "total_due": str(total_due),
        "forecasted_settlements": str(today_settlements),
        "gap": str(gap),
        "repayments": today_repayments,
    }
