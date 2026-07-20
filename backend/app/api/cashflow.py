"""Canonical daily cashflow ledger API."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.auth import get_current_user_dependency
from core.database import get_db
from schemas.auth import UserInfo
from schemas.cashflow import CashflowResponse
from services.cashflow_service import build_cashflow


router = APIRouter(prefix="/api/v1/cashflow", tags=["cashflow"])


@router.get("", response_model=CashflowResponse)
def get_cashflow(
    days: int = Query(default=30, ge=1, le=90),
    current_user: UserInfo = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    return build_cashflow(
        db=db,
        user_id=current_user.id,
        start_date=date.today(),
        days=days,
    )
