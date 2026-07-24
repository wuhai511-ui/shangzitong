import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
os.environ['JWT_SECRET'] = 'dev-test-secret-key-for-pytest-only-32bytes!'
os.environ['DATABASE_URL'] = 'sqlite:///./test_szt.db'

import pytest
import json
from datetime import date, datetime
from decimal import Decimal

from core.database import SessionLocal
from models.agency import Agency
from models.user import User
from models.merchant import Merchant
from models.merchant_profile import MerchantProfile
from models.card import Card
from models.transaction import Transaction
from models.auto_swipe_policy import AutoSwipePolicy


DEFAULT_RETRY = json.dumps({"max_retries": 3, "backoff_seconds": 60, "backoff_multiplier": 2})


def _create_agency(db):
    agency = Agency(name="test_agency", status=1)
    db.add(agency)
    db.commit()
    db.refresh(agency)
    return agency


def _create_user(db, agency_id):
    user = User(openid=f"task-test-{id(db)}-{datetime.utcnow().timestamp()}", nickname="test", phone="", role="merchant", agency_id=agency_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestEvaluateAllMerchants:
    def test_creates_transactions_for_gap_merchants(self, monkeypatch):
        db = SessionLocal()
        try:
            agency = _create_agency(db)
            user = _create_user(db, agency.id)
            profile = MerchantProfile(user_id=user.id, available_cash=Decimal("1000.00"), available_cash_updated_at=datetime.utcnow())
            db.add(profile)
            db.commit()
            merchant = Merchant(agency_id=agency.id, user_id=user.id, name="test-merchant", phone="123", business_type="test", auto_swipe_enabled=True)
            db.add(merchant)
            card = Card(user_id=user.id, agency_id=agency.id, bank_name="TestBank", card_tail="1234", credit_limit=Decimal("50000.00"), bill_day=1, due_day=20, swipe_fee_rate=Decimal("0.006"))
            db.add(card)
            policy = AutoSwipePolicy(agency_id=agency.id, max_parallel_transactions=3, retry_strategy=DEFAULT_RETRY, is_active=True)
            db.add(policy)
            db.commit()

            from schemas.cashflow import CashflowDay, CashflowResponse
            fake_cashflow = CashflowResponse(
                days=[
                    CashflowDay(date=date.today(), opening_balance=Decimal("1000.00"), settlements=Decimal("0.00"),
                                repayments=Decimal("5000.00"), purchases=Decimal("0.00"), other_outflows=Decimal("0.00"),
                                closing_balance=Decimal("-4000.00"), funding_gap=Decimal("4000.00"), events=[]),
                ],
                is_estimate=False,
                available_cash=Decimal("1000.00"),
                available_cash_updated_at=None,
            )

            def fake_build_cashflow(db, user_id, start_date, days):
                return fake_cashflow

            monkeypatch.setattr("services.cashflow_service.build_cashflow", fake_build_cashflow)

            from tasks.auto_swipe_tasks import evaluate_all_merchants_task
            result = evaluate_all_merchants_task()
            assert result["decisions_created"] >= 1

            db.expire_all()
            txns = db.query(Transaction).filter(Transaction.merchant_id == merchant.id).all()
            assert len(txns) >= 1
            assert txns[0].amount == Decimal("4000.00")
            assert txns[0].status == "pending"
        finally:
            db.close()


class TestExecuteScheduledTransactions:
    def test_processes_scheduled_transactions(self):
        db = SessionLocal()
        try:
            agency = _create_agency(db)
            user = _create_user(db, agency.id)
            merchant = Merchant(agency_id=agency.id, user_id=user.id, name="sched-merchant", phone="123", business_type="test")
            db.add(merchant)
            db.commit()

            txn = Transaction(
                agency_id=agency.id, merchant_id=merchant.id, merchant_no="M001",
                card_id=None, provider="lkl",
                amount=Decimal("500.00"), idempotency_key="test-sched-key-001",
                status="scheduled", scheduled_at=datetime.utcnow(),
            )
            db.add(txn)
            db.commit()
            txn_id = txn.id
        finally:
            db.close()

        from tasks.auto_swipe_tasks import execute_scheduled_transactions_task
        result = execute_scheduled_transactions_task()
        assert result["executed"] >= 1

        db2 = SessionLocal()
        try:
            updated = db2.query(Transaction).filter(Transaction.id == txn_id).first()
            assert updated is not None
            assert updated.status == "success"
            assert updated.provider_txn_id is not None
        finally:
            db2.close()


class TestRetryFailedTransactions:
    def test_retries_failed_under_max(self):
        db = SessionLocal()
        try:
            agency = _create_agency(db)
            user = _create_user(db, agency.id)
            merchant = Merchant(agency_id=agency.id, user_id=user.id, name="retry-merchant", phone="123", business_type="test")
            db.add(merchant)
            db.commit()

            txn = Transaction(
                agency_id=agency.id, merchant_id=merchant.id, merchant_no="M002",
                card_id=None, provider="lkl",
                amount=Decimal("300.00"), idempotency_key="test-retry-key-001",
                status="failed", retry_count=1, last_error="network timeout",
            )
            db.add(txn)
            db.commit()
            txn_id = txn.id
        finally:
            db.close()

        from tasks.auto_swipe_tasks import retry_failed_transactions_task
        result = retry_failed_transactions_task()
        assert result["retried"] >= 1

        db2 = SessionLocal()
        try:
            updated = db2.query(Transaction).filter(Transaction.id == txn_id).first()
            assert updated is not None
            assert updated.status == "scheduled"
        finally:
            db2.close()

    def test_skips_failed_at_max_retries(self):
        db = SessionLocal()
        try:
            agency = _create_agency(db)
            user = _create_user(db, agency.id)
            merchant = Merchant(agency_id=agency.id, user_id=user.id, name="max-retry-merchant", phone="123", business_type="test")
            db.add(merchant)
            db.commit()

            txn = Transaction(
                agency_id=agency.id, merchant_id=merchant.id, merchant_no="M003",
                card_id=None, provider="lkl",
                amount=Decimal("200.00"), idempotency_key="test-max-retry-key-001",
                status="failed", retry_count=3, last_error="persistent failure",
            )
            db.add(txn)
            db.commit()
            txn_id = txn.id
        finally:
            db.close()

        from tasks.auto_swipe_tasks import retry_failed_transactions_task
        result = retry_failed_transactions_task()
        assert result["retried"] == 0

        db2 = SessionLocal()
        try:
            updated = db2.query(Transaction).filter(Transaction.id == txn_id).first()
            assert updated is not None
            assert updated.status == "failed"
        finally:
            db2.close()
