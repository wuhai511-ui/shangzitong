import json
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from core.database import SessionLocal
from models.auto_swipe_policy import AutoSwipePolicy
from models.card import Card
from models.merchant import Merchant
from models.user import User
from models.agency import Agency
from models.merchant_profile import MerchantProfile
from services.decision_engine import AutoSwipeDecisionEngine, _interest_free_days

DEFAULT_RETRY = json.dumps({"max_retries": 3, "backoff_seconds": 60, "backoff_multiplier": 2})


def _create_agency(db):
    agency = Agency(name="test_agency", status=1)
    db.add(agency)
    db.commit()
    db.refresh(agency)
    return agency


def _create_user(db, agency_id):
    user = User(openid=f"decision-test-{id(db)}-{datetime.utcnow().timestamp()}", nickname="test", phone="", role="merchant", agency_id=agency_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestDecisionEngine:
    def test_no_gap_returns_empty(self):
        db = SessionLocal()
        try:
            agency = _create_agency(db)
            user = _create_user(db, agency.id)
            profile = MerchantProfile(user_id=user.id, available_cash=Decimal("100000.00"), available_cash_updated_at=datetime.utcnow())
            db.add(profile)
            db.commit()
            merchant = Merchant(agency_id=agency.id, user_id=user.id, name="test", phone="123", business_type="test", auto_swipe_enabled=True)
            db.add(merchant)
            card = Card(user_id=user.id, agency_id=agency.id, bank_name="TestBank", card_tail="1234", credit_limit=Decimal("50000.00"), bill_day=1, due_day=20, swipe_fee_rate=Decimal("0.006"))
            db.add(card)
            policy = AutoSwipePolicy(agency_id=agency.id, max_parallel_transactions=3, retry_strategy=DEFAULT_RETRY, is_active=True)
            db.add(policy)
            db.commit()

            decisions = AutoSwipeDecisionEngine.evaluate(db, agency.id, merchant.id)
            assert decisions == []
        finally:
            db.close()

    def test_gap_covered_by_single_card(self, monkeypatch):
        db = SessionLocal()
        try:
            agency = _create_agency(db)
            user = _create_user(db, agency.id)
            profile = MerchantProfile(user_id=user.id, available_cash=Decimal("1000.00"), available_cash_updated_at=datetime.utcnow())
            db.add(profile)
            db.commit()
            merchant = Merchant(agency_id=agency.id, user_id=user.id, name="test", phone="123", business_type="test", auto_swipe_enabled=True)
            db.add(merchant)
            card = Card(user_id=user.id, agency_id=agency.id, bank_name="TestBank", card_tail="1234", credit_limit=Decimal("100000.00"), bill_day=1, due_day=20, swipe_fee_rate=Decimal("0.006"))
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

            decisions = AutoSwipeDecisionEngine.evaluate(db, agency.id, merchant.id)
            assert len(decisions) >= 1
            d = decisions[0]
            assert d.merchant_id == merchant.id
            assert d.card_id == card.id
            assert d.amount == Decimal("4000.00")
            assert d.estimated_fee == Decimal("4000.00") * Decimal("0.006")
        finally:
            db.close()

    def test_multi_card_when_single_insufficient(self, monkeypatch):
        db = SessionLocal()
        try:
            agency = _create_agency(db)
            user = _create_user(db, agency.id)
            profile = MerchantProfile(user_id=user.id, available_cash=Decimal("1000.00"), available_cash_updated_at=datetime.utcnow())
            db.add(profile)
            db.commit()
            merchant = Merchant(agency_id=agency.id, user_id=user.id, name="test", phone="123", business_type="test", auto_swipe_enabled=True)
            db.add(merchant)
            card1 = Card(user_id=user.id, agency_id=agency.id, bank_name="Bank1", card_tail="1111", credit_limit=Decimal("3000.00"), bill_day=1, due_day=20, swipe_fee_rate=Decimal("0.006"))
            card2 = Card(user_id=user.id, agency_id=agency.id, bank_name="Bank2", card_tail="2222", credit_limit=Decimal("3000.00"), bill_day=1, due_day=20, swipe_fee_rate=Decimal("0.005"))
            db.add_all([card1, card2])
            policy = AutoSwipePolicy(agency_id=agency.id, max_parallel_transactions=3, retry_strategy=DEFAULT_RETRY, is_active=True)
            db.add(policy)
            db.commit()

            from schemas.cashflow import CashflowDay, CashflowResponse

            fake_cashflow = CashflowResponse(
                days=[
                    CashflowDay(date=date.today(), opening_balance=Decimal("1000.00"), settlements=Decimal("0.00"),
                                repayments=Decimal("6000.00"), purchases=Decimal("0.00"), other_outflows=Decimal("0.00"),
                                closing_balance=Decimal("-5000.00"), funding_gap=Decimal("5000.00"), events=[]),
                ],
                is_estimate=False,
                available_cash=Decimal("1000.00"),
                available_cash_updated_at=None,
            )

            def fake_build_cashflow(db, user_id, start_date, days):
                return fake_cashflow

            monkeypatch.setattr("services.cashflow_service.build_cashflow", fake_build_cashflow)

            decisions = AutoSwipeDecisionEngine.evaluate(db, agency.id, merchant.id)
            assert len(decisions) >= 2
            assert decisions[0].amount == Decimal("3000.00")
            assert decisions[1].amount == Decimal("2000.00")
            assert decisions[0].card_id != decisions[1].card_id
        finally:
            db.close()

    def test_policy_inactive_returns_empty(self, monkeypatch):
        db = SessionLocal()
        try:
            agency = _create_agency(db)
            user = _create_user(db, agency.id)
            profile = MerchantProfile(user_id=user.id, available_cash=Decimal("1000.00"), available_cash_updated_at=datetime.utcnow())
            db.add(profile)
            db.commit()
            merchant = Merchant(agency_id=agency.id, user_id=user.id, name="test", phone="123", business_type="test", auto_swipe_enabled=True)
            db.add(merchant)
            card = Card(user_id=user.id, agency_id=agency.id, bank_name="TestBank", card_tail="1234", credit_limit=Decimal("50000.00"), bill_day=1, due_day=20, swipe_fee_rate=Decimal("0.006"))
            db.add(card)
            policy = AutoSwipePolicy(agency_id=agency.id, max_parallel_transactions=3, retry_strategy=DEFAULT_RETRY, is_active=False)
            db.add(policy)
            db.commit()

            decisions = AutoSwipeDecisionEngine.evaluate(db, agency.id, merchant.id)
            assert decisions == []
        finally:
            db.close()
