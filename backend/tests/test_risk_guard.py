import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
os.environ['JWT_SECRET'] = 'dev-test-secret-key-for-pytest-only-32bytes!'
os.environ['DATABASE_URL'] = 'sqlite:///./test_szt.db'

import pytest
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from fastapi import HTTPException

from core.database import SessionLocal
from models.transaction import Transaction
from models.auto_swipe_policy import AutoSwipePolicy
from models.auto_swipe_execution_log import AutoSwipeExecutionLog
from services.risk_guard import RiskGuard


@pytest.fixture(autouse=True)
def db_session():
    db = SessionLocal()
    try:
        yield db
        db.rollback()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    db = SessionLocal()
    try:
        db.query(Transaction).delete()
        db.query(AutoSwipePolicy).delete()
        db.query(AutoSwipeExecutionLog).delete()
        db.commit()
    finally:
        db.close()


def _make_policy(**overrides) -> AutoSwipePolicy:
    defaults = {
        "agency_id": 1,
        "max_parallel_transactions": 3,
        "max_daily_per_merchant": None,
        "max_single_amount": None,
        "retry_strategy": '{"max_retries":3}',
        "is_active": False,
    }
    defaults.update(overrides)
    return AutoSwipePolicy(**defaults)


def _make_txn(db_session, **overrides) -> Transaction:
    defaults = {
        "agency_id": 1,
        "merchant_id": 10,
        "merchant_no": "M001",
        "card_id": 1,
        "provider": "lkl",
        "channel_id": 1,
        "amount": Decimal("100.00"),
        "idempotency_key": f"test-{datetime.utcnow().timestamp()}",
        "status": "scheduled",
        "scheduled_at": datetime.utcnow(),
    }
    defaults.update(overrides)
    txn = Transaction(**defaults)
    db_session.add(txn)
    db_session.commit()
    db_session.refresh(txn)
    return txn


class TestConcurrencyLimit:
    def test_blocks_when_limit_reached(self, db_session):
        policy = _make_policy(max_parallel_transactions=2)
        _make_txn(db_session, status="executing", merchant_id=10)
        _make_txn(db_session, status="scheduled", merchant_id=10)

        with pytest.raises(HTTPException) as exc:
            RiskGuard.check_concurrency(db_session, agency_id=1, merchant_id=10, policy=policy)
        assert exc.value.status_code == 429
        assert "Concurrency limit" in exc.value.detail

    def test_allows_when_under_limit(self, db_session):
        policy = _make_policy(max_parallel_transactions=5)
        _make_txn(db_session, status="executing", merchant_id=10)

        RiskGuard.check_concurrency(db_session, agency_id=1, merchant_id=10, policy=policy)

    def test_uses_default_of_3(self, db_session):
        policy = _make_policy(max_parallel_transactions=None)
        _make_txn(db_session, status="executing", merchant_id=10)
        _make_txn(db_session, status="scheduled", merchant_id=10)
        _make_txn(db_session, status="executing", merchant_id=10)

        with pytest.raises(HTTPException) as exc:
            RiskGuard.check_concurrency(db_session, agency_id=1, merchant_id=10, policy=policy)
        assert exc.value.status_code == 429


class TestDailyLimit:
    def test_blocks_when_daily_limit_exceeded(self, db_session):
        policy = _make_policy(max_daily_per_merchant=Decimal("200.00"))
        _make_txn(db_session, amount=Decimal("150.00"), merchant_id=10)

        with pytest.raises(HTTPException) as exc:
            RiskGuard.check_daily_limit(db_session, merchant_id=10, policy=policy, amount=Decimal("100.00"))
        assert exc.value.status_code == 429

    def test_allows_when_under_daily_limit(self, db_session):
        policy = _make_policy(max_daily_per_merchant=Decimal("200.00"))
        _make_txn(db_session, amount=Decimal("50.00"), merchant_id=10)

        RiskGuard.check_daily_limit(db_session, merchant_id=10, policy=policy, amount=Decimal("100.00"))

    def test_skips_when_no_limit_set(self, db_session):
        policy = _make_policy(max_daily_per_merchant=None)
        _make_txn(db_session, amount=Decimal("500.00"), merchant_id=10)

        RiskGuard.check_daily_limit(db_session, merchant_id=10, policy=policy, amount=Decimal("500.00"))

    def test_excludes_cancelled_transactions(self, db_session):
        policy = _make_policy(max_daily_per_merchant=Decimal("100.00"))
        _make_txn(db_session, amount=Decimal("80.00"), merchant_id=10, status="cancelled")

        RiskGuard.check_daily_limit(db_session, merchant_id=10, policy=policy, amount=Decimal("50.00"))


class TestSingleAmount:
    def test_blocks_when_exceeds_max_single(self, db_session):
        policy = _make_policy(max_single_amount=Decimal("500.00"))
        with pytest.raises(HTTPException) as exc:
            RiskGuard.check_single_amount(Decimal("1000.00"), policy)
        assert exc.value.status_code == 400

    def test_allows_when_under_max_single(self, db_session):
        policy = _make_policy(max_single_amount=Decimal("500.00"))
        RiskGuard.check_single_amount(Decimal("200.00"), policy)

    def test_skips_when_no_limit_set(self, db_session):
        policy = _make_policy(max_single_amount=None)
        RiskGuard.check_single_amount(Decimal("99999.00"), policy)


class TestTimeWindow:
    def test_allows_within_window(self, db_session):
        policy = _make_policy(
            swipe_window_start=time(6, 0, 0),
            swipe_window_end=time(22, 0, 0),
        )
        assert RiskGuard.check_time_window(policy) is True

    def test_rejects_outside_window(self, db_session):
        policy = _make_policy(
            swipe_window_start=time(22, 0, 0),
            swipe_window_end=time(6, 0, 0),
        )
        result = RiskGuard.check_time_window(policy)
        now = datetime.now().time()
        in_window = time(22, 0, 0) <= now <= time(23, 59, 59) or time(0, 0, 0) <= now <= time(6, 0, 0)
        assert result == in_window

    def test_allows_when_no_window_set(self, db_session):
        policy = _make_policy(swipe_window_start=None, swipe_window_end=None)
        assert RiskGuard.check_time_window(policy) is True


class TestCircuitBreaker:
    def test_blocks_when_success_rate_below_50_percent(self, db_session):
        for i in range(8):
            _make_txn(db_session, status="failed", idempotency_key=f"cb-fail-{i}")
        for i in range(2):
            _make_txn(db_session, status="success", idempotency_key=f"cb-success-{i}")

        result = RiskGuard.check_circuit_breaker(db_session, agency_id=1)
        assert result is False

    def test_allows_when_success_rate_above_50_percent(self, db_session):
        for i in range(8):
            _make_txn(db_session, status="success", idempotency_key=f"cb-s-{i}")
        for i in range(2):
            _make_txn(db_session, status="failed", idempotency_key=f"cb-f-{i}")

        result = RiskGuard.check_circuit_breaker(db_session, agency_id=1)
        assert result is True

    def test_allows_when_not_enough_data(self, db_session):
        for i in range(3):
            _make_txn(db_session, status="failed", idempotency_key=f"cb-low-{i}")

        result = RiskGuard.check_circuit_breaker(db_session, agency_id=1)
        assert result is True

    def test_scoped_by_agency(self, db_session):
        for i in range(10):
            _make_txn(db_session, status="success", agency_id=2, idempotency_key=f"cb-a2-{i}")

        result = RiskGuard.check_circuit_breaker(db_session, agency_id=1)
        assert result is True


class TestConsecutiveFailures:
    def test_blocks_after_3_consecutive_failures(self, db_session):
        _make_txn(db_session, status="failed", merchant_id=10, idempotency_key="cf-1")
        _make_txn(db_session, status="failed", merchant_id=10, idempotency_key="cf-2")
        _make_txn(db_session, status="dead_letter", merchant_id=10, idempotency_key="cf-3")

        with pytest.raises(HTTPException) as exc:
            RiskGuard.check_merchant_consecutive_failures(db_session, merchant_id=10)
        assert exc.value.status_code == 429
        assert "consecutive failures" in exc.value.detail

    def test_allows_after_success_breaks_streak(self, db_session):
        _make_txn(db_session, status="failed", merchant_id=10, idempotency_key="cs-1")
        _make_txn(db_session, status="success", merchant_id=10, idempotency_key="cs-2")
        _make_txn(db_session, status="failed", merchant_id=10, idempotency_key="cs-3")

        RiskGuard.check_merchant_consecutive_failures(db_session, merchant_id=10)

    def test_allows_with_less_than_3_failures(self, db_session):
        _make_txn(db_session, status="failed", merchant_id=10, idempotency_key="cl-1")
        _make_txn(db_session, status="failed", merchant_id=10, idempotency_key="cl-2")

        RiskGuard.check_merchant_consecutive_failures(db_session, merchant_id=10)

    def test_scoped_by_merchant(self, db_session):
        _make_txn(db_session, status="failed", merchant_id=20, idempotency_key="cm-1")
        _make_txn(db_session, status="failed", merchant_id=20, idempotency_key="cm-2")
        _make_txn(db_session, status="failed", merchant_id=20, idempotency_key="cm-3")

        RiskGuard.check_merchant_consecutive_failures(db_session, merchant_id=10)
