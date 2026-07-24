from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import SessionLocal
from core.auth_context import UserContext, get_current_user
from services.decision_engine import AutoSwipeDecisionEngine
from services.transaction_service import TransactionService

router = APIRouter(prefix="/api/v1/merchants", tags=["auto-swipe"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/{merchant_id}/trigger-auto-swipe")
def trigger_auto_swipe(
    merchant_id: int,
    ctx: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx.require_agent()
    from models.merchant import Merchant
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(404, "Merchant not found")
    if not merchant.auto_swipe_enabled:
        raise HTTPException(400, "Auto-swipe not enabled for this merchant")
    decisions = AutoSwipeDecisionEngine.evaluate(db, merchant.agency_id, merchant.id)
    created = 0
    for dec in decisions:
        idem_key = TransactionService.generate_idempotency_key(dec.merchant_id, dec.card_id, dec.swipe_date, 1)
        from models.transaction import Transaction
        existing = db.query(Transaction).filter(Transaction.idempotency_key == idem_key).first()
        if existing:
            continue
        txn = Transaction(
            agency_id=merchant.agency_id, merchant_id=dec.merchant_id,
            merchant_no="", card_id=dec.card_id, provider="",
            amount=dec.amount, idempotency_key=idem_key,
            status="scheduled", scheduled_at=dec.swipe_date,
        )
        db.add(txn)
        created += 1
    db.commit()
    return {"decisions_generated": len(decisions), "transactions_created": created}
