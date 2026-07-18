"""诊断报告API — P3B: Monthly diagnostic report endpoint.

Computes a health score from user card and settlement data
and returns a structured diagnostic report with suggestions.
"""

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import SessionLocal
from schemas.auth import UserInfo
from api.auth import get_current_user_dependency
from models.card import Card
from models.datasource import Settlement
from algorithm.health import calculate_health_score

router = APIRouter(prefix="/api/v1", tags=["report"])


def get_db():
    """FastAPI dependency: yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _compute_metrics(db: Session, user_id: int) -> dict:
    """Compute health metrics from user card and settlement data."""
    cards = db.query(Card).filter(
        Card.user_id == user_id,
        Card.deleted_at.is_(None),
    ).all()

    card_count = len(cards)

    if card_count == 0:
        return {
            "free_days_utilization": 0.0,
            "overdue_count": 0.0,
            "gap_frequency": 0.0,
            "card_utilization": 0.0,
            "card_count": 0,
            "total_limit": 0.0,
            "avg_utilization": 0.0,
        }

    # Card-level metrics
    total_limit = Decimal("0")
    total_used = Decimal("0")
    total_free_days = 0

    for card in cards:
        total_limit += card.credit_limit
        total_used += card.used_limit

        # Interest-free days: days from bill_day to due_day
        if card.due_day > card.bill_day:
            free_days = card.due_day - card.bill_day
        else:
            free_days = card.due_day + 30 - card.bill_day
        total_free_days += free_days

    card_utilization = float(total_used / total_limit) if total_limit > 0 else 0.0
    avg_free_days = total_free_days / card_count
    free_days_utilization = min(1.0, avg_free_days / 50.0)

    # Settlement-based metrics (past 30 days)
    thirty_days_ago = date.today() - timedelta(days=30)
    settlements = db.query(Settlement).filter(
        Settlement.user_id == user_id,
        Settlement.settle_date >= thirty_days_ago,
        Settlement.deleted_at.is_(None),
    ).all()

    # overdue_count: ratio of settlements that might indicate issues
    # For now, treat negative or zero amounts as potential flags
    overdue_count = 0.0
    if settlements:
        flagged = sum(1 for s in settlements if s.amount <= 0)
        overdue_count = flagged / len(settlements)

    # gap_frequency: count of days with gaps in settlement coverage
    gap_frequency = 0.0
    if settlements and len(settlements) >= 2:
        sorted_dates = sorted(s.settle_date for s in settlements)
        gaps = 0
        for i in range(1, len(sorted_dates)):
            diff = (sorted_dates[i] - sorted_dates[i - 1]).days
            if diff > 7:  # more than a week gap
                gaps += 1
        gap_frequency = gaps / (len(sorted_dates) - 1)

    return {
        "free_days_utilization": free_days_utilization,
        "overdue_count": overdue_count,
        "gap_frequency": gap_frequency,
        "card_utilization": card_utilization,
        "card_count": card_count,
        "total_limit": float(total_limit),
        "avg_utilization": round(card_utilization * 100, 1),
    }


def _generate_suggestions(score: float, dimensions: dict, card_count: int) -> list:
    """Generate actionable suggestions based on health score and dimensions."""
    suggestions = []

    if card_count == 0:
        suggestions.append("您还没有添加信用卡，请先添加卡片以获取完整分析")
        return suggestions

    dim_free = dimensions.get("免息期利用率", 0)
    dim_repay = dimensions.get("还款准时率", 0)
    dim_stability = dimensions.get("资金稳定性", 0)
    dim_health = dimensions.get("额度健康度", 0)

    if dim_free < 60:
        suggestions.append("建议优化刷卡日期，充分利用账单日后的免息期")
    if dim_repay < 60:
        suggestions.append("还款准时率偏低，建议设置自动还款避免逾期")
    if dim_stability < 60:
        suggestions.append("资金稳定性不足，建议预留应急资金避免资金缺口")
    if dim_health < 60:
        suggestions.append("信用卡使用率偏高，建议降低额度占用比例")

    if score >= 80:
        suggestions.append("经营状况优秀，继续保持当前策略")
    elif not suggestions:
        suggestions.append("各项指标正常，继续保持")

    return suggestions


@router.get("/report/monthly", response_model=None)
def get_monthly_report(
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    """Generate a monthly diagnostic report with health score and suggestions."""
    metrics = _compute_metrics(db, current_user.id)

    health_result = calculate_health_score(metrics)

    suggestions = _generate_suggestions(
        health_result["score"],
        health_result["dimensions"],
        metrics["card_count"],
    )

    return {
        "score": health_result["score"],
        "grade": health_result["grade"],
        "dimensions": health_result["dimensions"],
        "card_count": metrics["card_count"],
        "total_limit": metrics["total_limit"],
        "avg_utilization": metrics["avg_utilization"],
        "suggestions": suggestions,
    }
