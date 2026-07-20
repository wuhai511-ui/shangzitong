"""Monthly diagnostic report API."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from algorithm.health import calculate_health_score
from api.auth import get_current_user_dependency
from core.database import SessionLocal
from models.card import Card
from schemas.auth import UserInfo
from schemas.cashflow import serialize_money
from services.cashflow_service import build_cashflow

router = APIRouter(prefix="/api/v1", tags=["report"])


def get_db():
    """FastAPI dependency: yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _compute_metrics(db: Session, user_id: int) -> dict:
    """Compute measured card metrics and canonical cashflow stability."""
    cards = db.query(Card).filter(
        Card.user_id == user_id,
        Card.deleted_at.is_(None),
    ).all()
    card_count = len(cards)

    total_limit = Decimal("0.00")
    total_used = Decimal("0.00")
    total_free_days = 0
    for card in cards:
        total_limit += Decimal(card.credit_limit)
        total_used += Decimal(card.used_limit)
        if card.due_day > card.bill_day:
            free_days = card.due_day - card.bill_day
        else:
            free_days = card.due_day + 30 - card.bill_day
        total_free_days += free_days

    card_utilization = (
        float(total_used / total_limit)
        if total_limit > Decimal("0.00")
        else 0.0
    )
    free_days_utilization = (
        min(1.0, (total_free_days / card_count) / 50.0)
        if card_count
        else 0.0
    )

    ledger_days = build_cashflow(
        db,
        user_id,
        date.today(),
        days=30,
    ).days
    gap_frequency = (
        sum(day.funding_gap > Decimal("0.00") for day in ledger_days)
        / len(ledger_days)
        if ledger_days
        else 0.0
    )

    return {
        "free_days_utilization": free_days_utilization,
        "overdue_count": None,
        "gap_frequency": gap_frequency,
        "card_utilization": card_utilization,
        "card_count": card_count,
        "total_limit": total_limit,
        "avg_utilization": round(card_utilization * 100, 1),
    }


def _generate_suggestions(score: float, dimensions: dict, card_count: int) -> list:
    """Generate suggestions only for measured health dimensions."""
    suggestions = []

    if card_count == 0:
        suggestions.append("您还没有添加信用卡，请先添加卡片以获取完整分析")
        return suggestions

    dim_free = dimensions.get("免息期利用率", 0)
    dim_stability = dimensions.get("资金稳定性", 0)
    dim_health = dimensions.get("额度健康度", 0)

    if dim_free < 60:
        suggestions.append("建议优化刷卡日期，充分利用账单日后的免息期")
    if (
        "还款准时率" in dimensions
        and dimensions["还款准时率"] < 60
    ):
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
    """Generate a monthly diagnostic report from measured data."""
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
        "total_limit": serialize_money(metrics["total_limit"]),
        "avg_utilization": metrics["avg_utilization"],
        "suggestions": suggestions,
        "repayment_data_status": "unavailable",
    }
