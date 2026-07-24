import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
os.environ['JWT_SECRET'] = 'dev-test-secret-key-for-pytest-only-32bytes!'
os.environ['DATABASE_URL'] = 'sqlite:///./test_szt.db'

import pytest
from datetime import date, datetime
from decimal import Decimal
from fastapi import HTTPException

from core.database import SessionLocal
from core.auth_context import UserContext
from models.transaction import Transaction
from services.transaction_service import TransactionService, VALID_STATUSES


@pytest.fixture(autouse=True)
def db_session():
    db = SessionLocal()
    try:
        yield db
        db.rollback()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_transactions():
    yield
    db = SessionLocal()
    try:
        db.query(Transaction).delete()
        db.commit()
    finally:
        db.close()


def _agent_ctx(agency_id=1):
    return UserContext(role="agent_admin", agency_id=agency_id, user_id=10)


def _superadmin_ctx():
    return UserContext(role="super_admin", agency_id=None, user_id=1)


def _merchant_ctx(user_id=100):
    return UserContext(role="merchant", agency_id=5, user_id=user_id)


class TestCreateTransaction:
    def test_create_transaction_success(self, db_session):
        ctx = _agent_ctx()
        txn = TransactionService.create_transaction(
            db_session,
            ctx,
            merchant_id=42,
            merchant_no="M001",
            card_id=7,
            provider="lkl",
            channel_id=1,
            amount=Decimal("100.00"),
            swipe_date=date(2026, 7, 20),
        )
        assert txn.id is not None
        assert txn.agency_id == 1
        assert txn.status == "pending"
        assert txn.amount == Decimal("100.00")
        assert txn.idempotency_key is not None

    def test_create_transaction_requires_agent(self, db_session):
        ctx = _merchant_ctx()
        with pytest.raises(HTTPException) as exc:
            TransactionService.create_transaction(
                db_session,
                ctx,
                merchant_id=42,
                merchant_no="M001",
                card_id=7,
                provider="lkl",
                channel_id=1,
                amount=Decimal("100.00"),
                swipe_date=date(2026, 7, 20),
            )
        assert exc.value.status_code == 403

    def test_generate_idempotency_key_deterministic(self):
        k1 = TransactionService.generate_idempotency_key(42, 7, date(2026, 7, 20), 1)
        k2 = TransactionService.generate_idempotency_key(42, 7, date(2026, 7, 20), 1)
        assert k1 == k2

    def test_generate_idempotency_key_differs_on_seq(self):
        k1 = TransactionService.generate_idempotency_key(42, 7, date(2026, 7, 20), 1)
        k2 = TransactionService.generate_idempotency_key(42, 7, date(2026, 7, 20), 2)
        assert k1 != k2

    def test_duplicate_idempotency_raises_409(self, db_session):
        ctx = _agent_ctx()
        TransactionService.create_transaction(
            db_session,
            ctx,
            merchant_id=42,
            merchant_no="M001",
            card_id=7,
            provider="lkl",
            channel_id=1,
            amount=Decimal("100.00"),
            swipe_date=date(2026, 7, 20),
        )
        with pytest.raises(HTTPException) as exc:
            TransactionService.create_transaction(
                db_session,
                ctx,
                merchant_id=42,
                merchant_no="M001",
                card_id=7,
                provider="lkl",
                channel_id=1,
                amount=Decimal("200.00"),
                swipe_date=date(2026, 7, 20),
            )
        assert exc.value.status_code == 409
        assert "Duplicate" in exc.value.detail


class TestStateTransitions:
    @pytest.fixture(autouse=True)
    def setup_txn(self, db_session):
        ctx = _agent_ctx()
        self.txn = TransactionService.create_transaction(
            db_session,
            ctx,
            merchant_id=42,
            merchant_no="M001",
            card_id=7,
            provider="lkl",
            channel_id=1,
            amount=Decimal("100.00"),
            swipe_date=date(2026, 7, 20),
        )
        self.db = db_session

    def test_full_lifecycle_pending_to_success(self):
        txn_id = self.txn.id

        txn = TransactionService.schedule(self.db, txn_id)
        assert txn.status == "scheduled"

        txn = TransactionService.mark_executing(self.db, txn_id)
        assert txn.status == "executing"
        assert txn.executed_at is not None

        txn = TransactionService.mark_success(self.db, txn_id, "LKL-ABC123", {"ref": "pay-001"})
        assert txn.status == "success"
        assert txn.provider_txn_id == "LKL-ABC123"
        assert txn.result_snapshot is not None

    def test_failed_retry_then_dead_letter(self):
        txn_id = self.txn.id
        TransactionService.schedule(self.db, txn_id)

        TransactionService.mark_failed(self.db, txn_id, "network timeout")
        txn = self.db.query(Transaction).filter(Transaction.id == txn_id).first()
        assert txn.status == "failed"
        assert txn.retry_count == 1
        assert txn.last_error == "network timeout"

        TransactionService.schedule(self.db, txn_id)
        TransactionService.mark_failed(self.db, txn_id, "timeout again")
        txn = self.db.query(Transaction).filter(Transaction.id == txn_id).first()
        assert txn.retry_count == 2

        TransactionService.mark_dead_letter(self.db, txn_id)
        txn = self.db.query(Transaction).filter(Transaction.id == txn_id).first()
        assert txn.status == "dead_letter"

    def test_cancel_from_pending(self):
        txn = TransactionService.cancel(self.db, self.txn.id)
        assert txn.status == "cancelled"

    def test_cancel_from_scheduled(self):
        TransactionService.schedule(self.db, self.txn.id)
        txn = TransactionService.cancel(self.db, self.txn.id)
        assert txn.status == "cancelled"

    def test_transition_invalid_status_raises(self):
        with pytest.raises(ValueError) as exc:
            TransactionService.transition(self.db, self.txn.id, "bogus")
        assert "Invalid status" in str(exc.value)

    def test_transition_nonexistent_txn_raises(self):
        with pytest.raises(HTTPException) as exc:
            TransactionService.transition(self.db, 99999, "scheduled")
        assert exc.value.status_code == 404


class TestListByAgency:
    def test_super_admin_sees_all(self, db_session):
        ctx1 = _agent_ctx(agency_id=1)
        ctx2 = _agent_ctx(agency_id=2)
        TransactionService.create_transaction(
            db_session, ctx1,
            merchant_id=1, merchant_no="A", card_id=7, provider="lkl",
            channel_id=1, amount=Decimal("10.00"),
            swipe_date=date(2026, 7, 20),
        )
        TransactionService.create_transaction(
            db_session, ctx2,
            merchant_id=2, merchant_no="B", card_id=8, provider="lkl",
            channel_id=1, amount=Decimal("20.00"),
            swipe_date=date(2026, 7, 21),
        )

        results = TransactionService.list_by_agency(db_session, _superadmin_ctx())
        assert len(results) == 2

    def test_agent_sees_own_agency_only(self, db_session):
        ctx1 = _agent_ctx(agency_id=1)
        ctx2 = _agent_ctx(agency_id=2)
        TransactionService.create_transaction(
            db_session, ctx1,
            merchant_id=1, merchant_no="A", card_id=7, provider="lkl",
            channel_id=1, amount=Decimal("10.00"),
            swipe_date=date(2026, 7, 20),
        )
        TransactionService.create_transaction(
            db_session, ctx2,
            merchant_id=2, merchant_no="B", card_id=8, provider="lkl",
            channel_id=1, amount=Decimal("20.00"),
            swipe_date=date(2026, 7, 21),
        )

        results = TransactionService.list_by_agency(db_session, _agent_ctx(agency_id=1))
        assert len(results) == 1
        assert results[0].merchant_id == 1


class TestGetPendingScheduled:
    def test_returns_scheduled_only(self, db_session):
        ctx = _agent_ctx()
        txn = TransactionService.create_transaction(
            db_session, ctx,
            merchant_id=1, merchant_no="A", card_id=7, provider="lkl",
            channel_id=1, amount=Decimal("10.00"),
            swipe_date=date(2026, 7, 20),
        )
        TransactionService.schedule(db_session, txn.id)

        pending = TransactionService.get_pending_scheduled(db_session)
        assert len(pending) == 1
        assert pending[0].id == txn.id
        assert pending[0].status == "scheduled"

    def test_excludes_pending(self, db_session):
        ctx = _agent_ctx()
        TransactionService.create_transaction(
            db_session, ctx,
            merchant_id=1, merchant_no="A", card_id=7, provider="lkl",
            channel_id=1, amount=Decimal("10.00"),
            swipe_date=date(2026, 7, 20),
        )

        pending = TransactionService.get_pending_scheduled(db_session)
        assert len(pending) == 0


class TestValidStatuses:
    def test_valid_statuses_set(self):
        assert VALID_STATUSES == {"pending", "scheduled", "executing", "success", "failed", "dead_letter", "cancelled"}
