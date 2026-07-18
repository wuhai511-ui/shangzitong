"""进货推荐API — P2A: Purchase recommendation engine."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from core.database import SessionLocal
from schemas.auth import UserInfo
from api.auth import get_current_user_dependency
from models.card import Card
from algorithm.interest import calc_interest_free_days, find_optimal_swipe_date
from algorithm.risk import risk_check, apply_utilization_cap
from algorithm.models import CardInfo
from datetime import date
from decimal import Decimal

router = APIRouter(prefix="/api/v1", tags=["recommend"])


class RecommendRequest(BaseModel):
    purchase_date: str  # ISO date
    amount: float


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


def _build_single_recommendation(
    card_info: CardInfo, purchase_date: date, amount: Decimal
) -> dict | None:
    """Build a recommendation for a single card, or None if it can't handle the amount."""
    # Check available limit
    if card_info.avail_limit < amount:
        return None

    # Risk check
    if not risk_check(card_info, amount, purchase_date):
        return None

    # Calculate swipe cost
    swipe_cost = amount * card_info.swipe_fee_rate

    # Find optimal swipe date and interest-free days
    optimal_date, free_days, repayment_date = find_optimal_swipe_date(
        card_info, purchase_date
    )

    # Daily cost = swipe_cost / free_days (lower is better)
    if free_days > 0:
        daily_cost = swipe_cost / Decimal(str(free_days))
    else:
        daily_cost = swipe_cost

    return {
        "card_id": card_info.card_id,
        "bank_name": card_info.bank_name,
        "optimal_date": str(optimal_date),
        "free_days": free_days,
        "swipe_cost": str(swipe_cost),
        "daily_cost": str(daily_cost),
        "repayment_date": str(repayment_date),
        "risk_weight": 0.0,
    }


@router.post("/recommend", response_model=None)
def get_recommendation(
    request: RecommendRequest,
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    """Recommend the best card(s) for a purchase.

    Logic:
    1. Query user cards → convert to CardInfo
    2. Filter by limit + risk check
    3. Sort by daily_cost ascending, then free_days descending
    4. If single card insufficient, suggest multi-card split
    """
    purchase_date = date.fromisoformat(request.purchase_date)
    amount = Decimal(str(request.amount))

    if amount <= 0:
        raise HTTPException(status_code=400, detail="购买金额必须大于0")

    # Load user cards
    cards = db.query(Card).filter(
        Card.user_id == current_user.id,
        Card.deleted_at.is_(None),
    ).all()

    if not cards:
        return {
            "recommendations": [],
            "multi_card_split": [],
            "coverage_ratio": 0.0,
            "gap_amount": str(amount),
            "warnings": ["没有可用的信用卡"],
        }

    # Build recommendations for each card
    card_infos = [_to_card_info(c) for c in cards]
    recommendations = []

    for card_info in card_infos:
        rec = _build_single_recommendation(card_info, purchase_date, amount)
        if rec is not None:
            recommendations.append(rec)

    # Sort by daily_cost ascending (cheapest first), then free_days descending
    recommendations.sort(
        key=lambda r: (Decimal(r["daily_cost"]), -r["free_days"])
    )

    # Check coverage
    total_avail = sum(
        min(ci.avail_limit, apply_utilization_cap(ci, cap=0.85))
        for ci in card_infos
    )

    coverage_ratio = float(min(Decimal("1.0"), total_avail / amount)) if amount > 0 else 0.0
    gap_amount = amount - min(amount, total_avail)

    # Build multi-card split if needed
    multi_card_split = []
    remaining = amount

    for card_info in card_infos:
        if remaining <= 0:
            break
        # Use utilization cap for effective per-card limit
        capped = apply_utilization_cap(card_info, cap=0.85)
        effective = min(card_info.avail_limit, capped)
        if effective <= 0:
            continue
        alloc = min(remaining, effective)
        multi_card_split.append({
            "card_id": card_info.card_id,
            "bank_name": card_info.bank_name,
            "allocated": str(alloc),
        })
        remaining -= alloc

    result = {
        "recommendations": recommendations,
        "multi_card_split": multi_card_split,
        "coverage_ratio": coverage_ratio,
        "gap_amount": str(gap_amount),
        "warnings": [],
    }

    if coverage_ratio < 1.0:
        result["warnings"].append(
            f"可用额度不足，缺口 ¥{gap_amount:.2f}"
        )

    return result
