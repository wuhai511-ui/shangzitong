from celery import shared_task


@shared_task
def evaluate_all_merchants_task():
    """Periodic task: scan all merchants with auto_swipe_enabled and generate decisions."""
    from core.database import SessionLocal
    from services.decision_engine import AutoSwipeDecisionEngine
    from services.transaction_service import TransactionService
    from models.merchant import Merchant
    from datetime import date

    db = SessionLocal()
    try:
        merchants = db.query(Merchant).filter(Merchant.auto_swipe_enabled == True).all()
        decisions_created = 0
        for merchant in merchants:
            decisions = AutoSwipeDecisionEngine.evaluate(db, merchant.agency_id, merchant.id)
            for dec in decisions:
                try:
                    idem_key = TransactionService.generate_idempotency_key(
                        dec.merchant_id, dec.card_id, dec.swipe_date, seq=1
                    )
                    from models.transaction import Transaction
                    existing = db.query(Transaction).filter(Transaction.idempotency_key == idem_key).first()
                    if existing:
                        continue
                    txn = Transaction(
                        agency_id=merchant.agency_id, merchant_id=dec.merchant_id,
                        merchant_no="", card_id=dec.card_id, provider="",
                        amount=dec.amount, idempotency_key=idem_key,
                        status="pending", scheduled_at=dec.swipe_date,
                    )
                    db.add(txn)
                    decisions_created += 1
                except Exception:
                    continue
        db.commit()
        return {"decisions_created": decisions_created}
    finally:
        db.close()


@shared_task
def execute_scheduled_transactions_task():
    """Periodic task: execute transactions in 'scheduled' status that are ready."""
    from core.database import SessionLocal
    from services.transaction_service import TransactionService
    from payment import PaymentProviderFactory

    db = SessionLocal()
    try:
        txns = TransactionService.get_pending_scheduled(db)
        executed = 0
        for txn in txns:
            try:
                TransactionService.mark_executing(db, txn.id)
                TransactionService.mark_success(db, txn.id, f"MOCK-TXN-{txn.id}", {"simulated": True})
                executed += 1
            except Exception as e:
                TransactionService.mark_failed(db, txn.id, str(e))
        db.commit()
        return {"executed": executed}
    finally:
        db.close()


@shared_task
def retry_failed_transactions_task():
    """Periodic task: retry failed transactions that haven't exceeded max retries."""
    from core.database import SessionLocal
    from models.transaction import Transaction

    db = SessionLocal()
    try:
        failed = db.query(Transaction).filter(
            Transaction.status == "failed",
            Transaction.retry_count < 3
        ).all()
        retried = 0
        for txn in failed:
            txn.status = "scheduled"
            retried += 1
        db.commit()
        return {"retried": retried}
    finally:
        db.close()
