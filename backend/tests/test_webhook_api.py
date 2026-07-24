import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
os.environ['JWT_SECRET'] = 'dev-test-secret-key-for-pytest-only-32bytes!'
os.environ['DATABASE_URL'] = 'sqlite:///./test_szt.db'

import pytest
from fastapi.testclient import TestClient

from core.database import SessionLocal
from models.payment_webhook_event import PaymentWebhookEvent
from models.agency_payment_channel import AgencyPaymentChannel, PaymentProvider
from main import app


@pytest.fixture(autouse=True)
def db_session():
    db = SessionLocal()
    try:
        yield db
        db.rollback()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_db():
    yield
    db = SessionLocal()
    try:
        db.query(PaymentWebhookEvent).delete()
        db.query(AgencyPaymentChannel).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


def _create_channel(db, provider="lkl", agency_id=1, org_no="ORG001"):
    channel = AgencyPaymentChannel(
        agency_id=agency_id,
        provider=provider,
        org_no=org_no,
        api_key_cipher="encrypted_key",
        api_secret_cipher="encrypted_secret",
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


class TestWebhookReceive:
    def test_receive_webhook_success(self, db_session, client):
        _create_channel(db_session, provider="lkl")
        payload = {"event_id": "evt-001", "event_type": "payment.success"}
        resp = client.post("/webhooks/payment/lkl", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "received"
        assert body["event_id"] == "evt-001"

    def test_receive_webhook_no_channel(self, client):
        resp = client.post("/webhooks/payment/nonexistent", json={"event_id": "x"})
        assert resp.status_code == 404

    def test_receive_webhook_invalid_json(self, client):
        resp = client.post("/webhooks/payment/lkl", content=b"not-json")
        assert resp.status_code == 400

    def test_receive_webhook_duplicate_event_id(self, db_session, client):
        _create_channel(db_session, provider="lkl")
        payload = {"event_id": "evt-dup", "event_type": "test"}
        resp1 = client.post("/webhooks/payment/lkl", json=payload)
        assert resp1.status_code == 200
        resp2 = client.post("/webhooks/payment/lkl", json=payload)
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "duplicate"

    def test_receive_webhook_fallback_event_id(self, db_session, client):
        _create_channel(db_session, provider="huifu")
        payload = {"application_id": "app-123", "event_type": "settlement.done"}
        resp = client.post("/webhooks/payment/huifu", json=payload)
        assert resp.status_code == 200
        assert resp.json()["event_id"] == "app-123"


class TestPaymentWebhookEventModel:
    def test_create_event(self, db_session):
        channel = _create_channel(db_session)
        event = PaymentWebhookEvent(
            agency_id=channel.agency_id,
            channel_id=channel.id,
            provider="lkl",
            provider_event_type="payment.success",
            provider_event_id="evt-model-001",
            raw_body='{"event_id": "evt-model-001"}',
            status="received",
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)
        assert event.id is not None
        assert event.provider_event_id == "evt-model-001"
        assert event.attempt_count == 1
        assert event.status == "received"

    def test_event_unique_event_id(self, db_session):
        channel = _create_channel(db_session)
        event1 = PaymentWebhookEvent(
            agency_id=channel.agency_id, channel_id=channel.id,
            provider="lkl", provider_event_type="test",
            provider_event_id="unique-ev-1", raw_body="{}",
        )
        db_session.add(event1)
        db_session.commit()
        event2 = PaymentWebhookEvent(
            agency_id=channel.agency_id, channel_id=channel.id,
            provider="lkl", provider_event_type="test",
            provider_event_id="unique-ev-1", raw_body="{}",
        )
        db_session.add(event2)
        with pytest.raises(Exception):
            db_session.commit()
