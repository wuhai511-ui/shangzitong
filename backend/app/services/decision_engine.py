from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session


@dataclass
class AutoSwipeDecision:
    merchant_id: int
    card_id: int
    amount: Decimal
    purpose: str = "repayment"
    interest_free_days: int = 0
    swipe_date: date = field(default_factory=date.today)
    estimated_fee: Decimal = Decimal("0.00")
    gap_date: date = field(default_factory=date.today)
    gap_amount_remaining: Decimal = Decimal("0.00")
    priority: int = 0


class AutoSwipeDecisionEngine:
    @staticmethod
    def evaluate(db: Session, agency_id: int, merchant_id: int) -> list[AutoSwipeDecision]:
        from models.merchant import Merchant
        from models.card import Card
        from models.auto_swipe_policy import AutoSwipePolicy
        from services.cashflow_service import build_cashflow

        merchant = db.query(Merchant).filter(Merchant.id == merchant_id, Merchant.agency_id == agency_id).first()
        if not merchant or not merchant.auto_swipe_enabled:
            return []

        policy = db.query(AutoSwipePolicy).filter(
            AutoSwipePolicy.agency_id == agency_id, AutoSwipePolicy.is_active == True
        ).first()
        if not policy:
            return []

        cashflow = build_cashflow(db, merchant.user_id, date.today(), days=30)
        if not cashflow or not cashflow.days:
            return []

        decisions = []
        cards = db.query(Card).filter(
            Card.agency_id == agency_id, Card.user_id == merchant.user_id, Card.status == 1
        ).all()

        cards = sorted(cards, key=lambda c: _interest_free_days(c), reverse=True)
        if policy.min_interest_free_days and policy.min_interest_free_days > 0:
            cards = [c for c in cards if _interest_free_days(c) >= policy.min_interest_free_days]

        for i, day in enumerate(cashflow.days):
            if day.funding_gap <= Decimal("0"):
                continue
            gap = day.funding_gap
            for card in cards:
                if gap <= Decimal("0"):
                    break
                avail = card.avail_limit
                if avail <= Decimal("0"):
                    continue
                swipe_amount = min(gap, avail)
                if policy.max_single_amount and swipe_amount > policy.max_single_amount:
                    swipe_amount = policy.max_single_amount
                decisions.append(AutoSwipeDecision(
                    merchant_id=merchant_id, card_id=card.id,
                    amount=swipe_amount,
                    purpose=f"cover_gap_{day.date.isoformat()}",
                    interest_free_days=_interest_free_days(card),
                    swipe_date=date.today(),
                    estimated_fee=swipe_amount * (card.swipe_fee_rate or Decimal("0.006")),
                    gap_date=day.date,
                    gap_amount_remaining=gap - swipe_amount,
                    priority=i,
                ))
                gap -= swipe_amount

        return decisions


def _interest_free_days(card) -> int:
    today = date.today()
    if not card.bill_day or not card.due_day:
        return 20
    if today.day <= card.bill_day:
        return (card.due_day - card.bill_day) + (card.bill_day - today.day)
    return (card.due_day - today.day) if card.due_day > today.day else (card.due_day + 30 - today.day)
