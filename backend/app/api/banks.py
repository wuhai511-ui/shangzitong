"""Bank dictionary API — list common banks."""
from fastapi import APIRouter, Depends
from models.bank import Bank

router = APIRouter(prefix="/api/v1/banks", tags=["banks"])


@router.get("")
def list_banks():
    """Return all bank names for card selection dropdown."""
    from core.database import SessionLocal
    db = SessionLocal()
    try:
        banks = db.query(Bank).order_by(Bank.sort_order, Bank.id).all()
        return [{"id": b.id, "name": b.name, "code": b.code} for b in banks]
    finally:
        db.close()
