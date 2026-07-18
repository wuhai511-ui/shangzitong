"""Stop-loss recommendation API — compare three repayment strategies."""
from fastapi import APIRouter, Depends, HTTPException
from core.database import SessionLocal
from schemas.auth import UserInfo
from api.auth import get_current_user_dependency
from models.card import Card
from decimal import Decimal

router = APIRouter(prefix="/api/v1/stoploss", tags=["stoploss"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=None)
def get_stoploss(data: dict, current_user: UserInfo = Depends(get_current_user_dependency),
                 db=Depends(get_db)):
    """Compare three repayment strategies for a cash gap."""
    card_id = data.get("card_id")
    gap = Decimal(str(data.get("gap_amount", 0)))

    card = db.query(Card).filter(
        Card.id == card_id,
        Card.user_id == current_user.id,
        Card.deleted_at.is_(None)
    ).first()
    if not card:
        raise HTTPException(status_code=404, detail="信用卡不存在")

    interest_rate = card.interest_rate
    min_ratio = card.min_payment_ratio
    swipe_rate = card.swipe_fee_rate

    # Plan A: Full repayment via temporary loan (assume 7-day bridge loan at 0.05% daily)
    loan_days = 7
    plan_a_cost = gap * Decimal("0.0005") * loan_days

    # Plan B: Minimum payment + daily interest on remainder for 30 days
    min_pay = gap * min_ratio
    remaining = gap - min_pay
    plan_b_cost = remaining * interest_rate * 30

    # Plan C: Installment (assume 6 periods)
    plan_c_cost = gap * swipe_rate * 6

    # Recommend cheapest
    costs = {"plan_a": plan_a_cost, "plan_b": plan_b_cost, "plan_c": plan_c_cost}
    recommendation = min(costs, key=costs.get)

    return {
        "plan_a": {
            "name": "全额还款(临时借款)",
            "description": f"借款{gap}元，{loan_days}天后归还",
            "cost": str(plan_a_cost),
            "total": str(gap + plan_a_cost),
        },
        "plan_b": {
            "name": "最低还款",
            "description": f"最低还款{min_pay}元，剩余按日计息30天",
            "cost": str(plan_b_cost),
            "total": str(gap + plan_b_cost),
        },
        "plan_c": {
            "name": "账单分期(6期)",
            "description": f"分6期，每期手续费率{float(swipe_rate)*100}%",
            "cost": str(plan_c_cost),
            "total": str(gap + plan_c_cost),
        },
        "recommendation": recommendation,
        "recommendation_reason": f"方案{recommendation[-1].upper()}总成本最低",
    }
