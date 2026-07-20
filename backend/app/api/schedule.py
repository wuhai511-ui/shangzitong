"""Global schedule API backed by the canonical daily cashflow ledger."""
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends

from api.auth import get_current_user_dependency
from core.database import SessionLocal
from schemas.auth import UserInfo
from schemas.cashflow import CashflowDay, serialize_money
from services.cashflow_service import build_cashflow

router = APIRouter(prefix="/api/v1", tags=["schedule"])


def get_db():
    """FastAPI dependency: yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _gap_alert(day: CashflowDay) -> list[dict]:
    if day.funding_gap <= Decimal("0.00"):
        return []
    return [
        {
            "type": "funding_gap",
            "message": f"资金缺口 ¥{serialize_money(day.funding_gap)}",
        }
    ]


def _schedule_entry(day: CashflowDay) -> dict:
    payload = day.model_dump(mode="json")
    return {
        "date": payload["date"],
        "cash_pool": payload["closing_balance"],
        "funding_gap": payload["funding_gap"],
        "settlements": [{"amount": payload["settlements"]}],
        "repayments": [
            event
            for event in payload["events"]
            if event.get("type") == "repayment"
        ],
        "alerts": _gap_alert(day),
    }


@router.get("/schedule", response_model=None)
def get_schedule(
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    """Return a 30-day global schedule with the canonical cash trend."""
    ledger = build_cashflow(db, current_user.id, date.today(), days=30)
    return {"days": [_schedule_entry(day) for day in ledger.days]}
