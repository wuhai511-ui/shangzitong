import hashlib
import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from models.transaction import Transaction
from core.auth_context import UserContext
from fastapi import HTTPException
from services.execution_log_service import ExecutionLogService

VALID_STATUSES = {"pending", "scheduled", "executing", "success", "failed", "dead_letter", "cancelled"}


class TransactionService:
    @staticmethod
    def generate_idempotency_key(merchant_id: int, card_id: int, swipe_date: date, seq: int) -> str:
        raw = f"{merchant_id}|{card_id}|{swipe_date.isoformat()}|{seq}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def create_transaction(
        db: Session,
        ctx: UserContext,
        *,
        merchant_id: int,
        merchant_no: str,
        card_id: int,
        provider: str,
        channel_id: int,
        amount: Decimal,
        swipe_date: date,
        seq: int = 1,
    ) -> Transaction:
        ctx.require_agent()
        idem_key = TransactionService.generate_idempotency_key(merchant_id, card_id, swipe_date, seq)
        existing = db.query(Transaction).filter(Transaction.idempotency_key == idem_key).first()
        if existing:
            raise HTTPException(409, f"Duplicate transaction: {idem_key}")
        txn = Transaction(
            agency_id=ctx.agency_id,
            merchant_id=merchant_id,
            merchant_no=merchant_no,
            card_id=card_id,
            provider=provider,
            channel_id=channel_id,
            amount=amount,
            idempotency_key=idem_key,
            status="pending",
            scheduled_at=datetime.utcnow(),
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return txn

    @staticmethod
    def transition(
        db: Session,
        txn_id: int,
        to_status: str,
        *,
        provider_txn_id: str | None = None,
        error: str | None = None,
        result_data: dict | None = None,
    ) -> Transaction:
        if to_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {to_status}")
        txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
        if not txn:
            raise HTTPException(404, "Transaction not found")
        txn.status = to_status
        if to_status == "executing":
            txn.executed_at = datetime.utcnow()
        if provider_txn_id:
            txn.provider_txn_id = provider_txn_id
        if error:
            txn.last_error = error
        if result_data:
            txn.result_snapshot = json.dumps(result_data, default=str)
        if to_status == "failed":
            txn.retry_count = (txn.retry_count or 0) + 1
        db.commit()
        db.refresh(txn)
        return txn

    @staticmethod
    def schedule(db: Session, txn_id: int) -> Transaction:
        return TransactionService.transition(db, txn_id, "scheduled")

    @staticmethod
    def mark_executing(db: Session, txn_id: int) -> Transaction:
        return TransactionService.transition(db, txn_id, "executing")

    @staticmethod
    def mark_success(db: Session, txn_id: int, provider_txn_id: str, result_data: dict) -> Transaction:
        txn = TransactionService.transition(db, txn_id, "success", provider_txn_id=provider_txn_id, result_data=result_data)
        ExecutionLogService.log(db, transaction_id=txn_id, agency_id=txn.agency_id, event_type="success", event_data=result_data)
        return txn

    @staticmethod
    def mark_failed(db: Session, txn_id: int, error: str) -> Transaction:
        txn = TransactionService.transition(db, txn_id, "failed", error=error)
        ExecutionLogService.log(db, transaction_id=txn_id, agency_id=txn.agency_id, event_type="failed", event_data={"error": error}, severity="error")
        return txn

    @staticmethod
    def mark_dead_letter(db: Session, txn_id: int) -> Transaction:
        return TransactionService.transition(db, txn_id, "dead_letter")

    @staticmethod
    def cancel(db: Session, txn_id: int) -> Transaction:
        txn = TransactionService.transition(db, txn_id, "cancelled")
        ExecutionLogService.log(db, transaction_id=txn_id, agency_id=txn.agency_id, event_type="cancelled")
        return txn

    @staticmethod
    def retry(db: Session, txn_id: int) -> Transaction:
        txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
        if not txn:
            raise HTTPException(404, "Transaction not found")
        if txn.status not in ("failed", "dead_letter"):
            raise HTTPException(400, f"Cannot retry transaction in '{txn.status}' status")
        txn.status = "scheduled"
        txn.last_error = None
        db.commit()
        db.refresh(txn)
        ExecutionLogService.log(db, transaction_id=txn_id, agency_id=txn.agency_id, event_type="retry_scheduled")
        return txn

    @staticmethod
    def list_by_agency(
        db: Session,
        ctx: UserContext,
        agency_id: int | None = None,
        status: str | None = None,
    ) -> list[Transaction]:
        q = db.query(Transaction)
        if not ctx.role == "super_admin":
            q = q.filter(Transaction.agency_id == ctx.agency_id)
        elif agency_id:
            q = q.filter(Transaction.agency_id == agency_id)
        if status:
            q = q.filter(Transaction.status == status)
        return q.order_by(Transaction.created_at.desc()).all()

    @staticmethod
    def get_pending_scheduled(db: Session) -> list[Transaction]:
        return db.query(Transaction).filter(
            Transaction.status.in_(["scheduled"])
        ).order_by(Transaction.scheduled_at.asc()).all()
