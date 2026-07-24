from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.auth_context import UserContext, get_db, get_user_context
from services.transaction_service import TransactionService
from models.transaction import Transaction

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])


def _txn_to_dict(txn: Transaction) -> dict:
    return {
        "id": txn.id,
        "agency_id": txn.agency_id,
        "merchant_id": txn.merchant_id,
        "merchant_no": txn.merchant_no,
        "card_id": txn.card_id,
        "provider": txn.provider,
        "channel_id": txn.channel_id,
        "amount": str(txn.amount) if txn.amount else None,
        "idempotency_key": txn.idempotency_key,
        "status": txn.status,
        "scheduled_at": txn.scheduled_at.isoformat() if txn.scheduled_at else None,
        "executed_at": txn.executed_at.isoformat() if txn.executed_at else None,
        "provider_txn_id": txn.provider_txn_id,
        "retry_count": txn.retry_count,
        "last_error": txn.last_error,
        "result_snapshot": txn.result_snapshot,
        "created_at": txn.created_at.isoformat() if txn.created_at else None,
        "updated_at": txn.updated_at.isoformat() if txn.updated_at else None,
    }


@router.get("/")
def list_transactions(
    agency_id: int | None = Query(None),
    status: str | None = Query(None),
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    results = TransactionService.list_by_agency(db, ctx, agency_id=agency_id, status=status)
    return [_txn_to_dict(t) for t in results]


@router.get("/{txn_id}")
def get_transaction(
    txn_id: int,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(404, "Transaction not found")
    if ctx.role != "super_admin" and ctx.agency_id != txn.agency_id:
        raise HTTPException(403, "Permission denied")
    return _txn_to_dict(txn)


@router.post("/{txn_id}/cancel")
def cancel_transaction(
    txn_id: int,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    ctx.require_agent()
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(404, "Transaction not found")
    if ctx.role != "super_admin" and ctx.agency_id != txn.agency_id:
        raise HTTPException(403, "Permission denied")
    result = TransactionService.cancel(db, txn_id)
    return _txn_to_dict(result)


@router.post("/{txn_id}/retry")
def retry_transaction(
    txn_id: int,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    ctx.require_agent()
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(404, "Transaction not found")
    if ctx.role != "super_admin" and ctx.agency_id != txn.agency_id:
        raise HTTPException(403, "Permission denied")
    result = TransactionService.retry(db, txn_id)
    return _txn_to_dict(result)
