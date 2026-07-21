"""Manual settlement entry API routes."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.manual_settlement import ManualSettlement
from schemas.auth import UserInfo
from schemas.manual_settlement import ManualSettlementCreate, ManualSettlementResponse
from api.auth import get_current_user_dependency

router = APIRouter(prefix="/api/v1/manual-settlement", tags=["manual-settlement"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _normalize_period_date(period_type: str, period_date: date) -> date:
    if period_type == "month":
        return period_date.replace(day=1)
    return period_date


def _to_response(row: ManualSettlement) -> dict:
    return {
        "id": int(row.id),
        "period_type": str(row.period_type),
        "period_date": row.period_date,
        "amount": row.amount,
        "note": row.note,
        "created_at": row.created_at,
    }


@router.get("", response_model=list[ManualSettlementResponse])
def list_manual_settlements(
    current_user: UserInfo = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ManualSettlement)
        .filter(
            ManualSettlement.user_id == current_user.id,
            ManualSettlement.deleted_at.is_(None),
        )
        .order_by(ManualSettlement.period_date.desc())
        .all()
    )
    return [_to_response(r) for r in rows]


@router.post("", response_model=ManualSettlementResponse, status_code=201)
def create_manual_settlement(
    data: ManualSettlementCreate,
    current_user: UserInfo = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    row = ManualSettlement(
        user_id=current_user.id,
        period_type=data.period_type,
        period_date=_normalize_period_date(data.period_type, data.period_date),
        amount=data.amount,
        note=data.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.delete("/{entry_id}", response_model=None)
def delete_manual_settlement(
    entry_id: int,
    current_user: UserInfo = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    row = (
        db.query(ManualSettlement)
        .filter(
            ManualSettlement.id == entry_id,
            ManualSettlement.user_id == current_user.id,
            ManualSettlement.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    row.soft_delete()
    db.commit()
    return {"status": "ok"}
