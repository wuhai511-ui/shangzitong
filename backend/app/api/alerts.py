"""Repayment alert API backed by the canonical daily cashflow ledger."""
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends

from api.auth import get_current_user_dependency
from core.database import SessionLocal
from schemas.auth import UserInfo
from schemas.cashflow import CashflowDay, serialize_money
from services.cashflow_service import build_cashflow

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


def get_db():
    """FastAPI dependency: yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _repayment_entries(day: CashflowDay) -> list[dict]:
    payload = day.model_dump(mode="json")
    gap_warning = day.funding_gap > Decimal("0.00")
    recommended_action = ""
    if gap_warning:
        recommended_action = (
            f"建议提前补充资金 ¥{payload['funding_gap']}，或使用分期/最低还款"
        )

    return [
        {
            **event,
            "due_date": payload["date"],
            "funding_gap": payload["funding_gap"],
            "gap_warning": gap_warning,
            "recommended_action": recommended_action,
        }
        for event in payload["events"]
        if event.get("type") == "repayment"
    ]


def _build_upcoming_repayments(db, current_user, today, days=7):
    """Adapt canonical ledger repayment events within the inclusive window."""
    ledger = build_cashflow(
        db,
        current_user.id,
        today,
        days=days + 1,
    )
    return [
        repayment
        for day in ledger.days
        for repayment in _repayment_entries(day)
    ]


@router.get("/upcoming", response_model=None)
def get_upcoming(
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    """Return upcoming repayments in the next seven days with gap warnings."""
    repayments = _build_upcoming_repayments(
        db,
        current_user,
        date.today(),
        days=7,
    )
    return {"repayments": repayments}


@router.get("/daily-summary", response_model=None)
def get_daily_summary(
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    """Return today's canonical settlements, repayments, and funding gap."""
    today = date.today()
    day = build_cashflow(db, current_user.id, today, days=1).days[0]

    return {
        "date": str(today),
        "total_due": serialize_money(day.repayments),
        "forecasted_settlements": serialize_money(day.settlements),
        "gap": serialize_money(day.funding_gap),
        "repayments": _repayment_entries(day),
    }
