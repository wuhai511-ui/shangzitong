from datetime import date, datetime, time, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from models.transaction import Transaction
from models.auto_swipe_policy import AutoSwipePolicy
from fastapi import HTTPException


class RiskGuard:
    @staticmethod
    def check_concurrency(db: Session, agency_id: int, merchant_id: int, policy: AutoSwipePolicy) -> None:
        active = db.query(Transaction).filter(
            Transaction.agency_id == agency_id,
            Transaction.merchant_id == merchant_id,
            Transaction.status.in_(["executing", "scheduled"])
        ).count()
        limit = policy.max_parallel_transactions or 3
        if active >= limit:
            raise HTTPException(429, f"Concurrency limit: {limit}")

    @staticmethod
    def check_daily_limit(db: Session, merchant_id: int, policy: AutoSwipePolicy, amount: Decimal) -> None:
        if not policy.max_daily_per_merchant:
            return
        today = date.today()
        daily_txns = db.query(Transaction).filter(
            Transaction.merchant_id == merchant_id,
            Transaction.created_at >= today,
            Transaction.status != "cancelled"
        ).all()
        total = sum((t.amount for t in daily_txns if t.amount), Decimal("0"))
        if total + amount > policy.max_daily_per_merchant:
            raise HTTPException(429, f"Daily limit exceeded: {policy.max_daily_per_merchant}")

    @staticmethod
    def check_single_amount(amount: Decimal, policy: AutoSwipePolicy) -> None:
        if policy.max_single_amount and amount > policy.max_single_amount:
            raise HTTPException(400, f"Single amount limit: {policy.max_single_amount}")

    @staticmethod
    def check_time_window(policy: AutoSwipePolicy) -> bool:
        if not policy.swipe_window_start or not policy.swipe_window_end:
            return True
        now = datetime.now().time()
        return policy.swipe_window_start <= now <= policy.swipe_window_end

    @staticmethod
    def check_circuit_breaker(db: Session, agency_id: int) -> bool:
        """Global meltdown: if last hour success rate < 50%, block auto-trigger."""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent = db.query(Transaction).filter(
            Transaction.agency_id == agency_id,
            Transaction.created_at >= one_hour_ago,
            Transaction.status.in_(["success", "failed"])
        ).all()
        if len(recent) < 10:
            return True
        success_count = sum(1 for t in recent if t.status == "success")
        return (success_count / len(recent)) >= 0.5

    @staticmethod
    def check_merchant_consecutive_failures(db: Session, merchant_id: int) -> None:
        recent = db.query(Transaction).filter(
            Transaction.merchant_id == merchant_id,
            Transaction.status.in_(["failed", "dead_letter"])
        ).order_by(Transaction.created_at.desc()).limit(3).all()
        if len(recent) >= 3 and all(t.status in ("failed", "dead_letter") for t in recent):
            raise HTTPException(429, "Merchant has 3 consecutive failures — auto-swipe paused")
