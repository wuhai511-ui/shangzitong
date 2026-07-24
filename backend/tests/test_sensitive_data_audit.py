import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
os.environ['JWT_SECRET'] = 'dev-test-secret-key-for-pytest-only-32bytes!'
os.environ['DATABASE_URL'] = 'sqlite:///./test_szt.db'

import pytest

from core.database import SessionLocal
from models.sensitive_data_audit import SensitiveDataAudit
from services.sensitive_data_audit import SensitiveDataAuditService


@pytest.fixture(autouse=True)
def db_session():
    db = SessionLocal()
    try:
        db.query(SensitiveDataAudit).delete()
        db.commit()
    except Exception:
        db.rollback()
    try:
        yield db
        db.rollback()
    finally:
        db.close()


def test_create_audit_entry(db_session):
    SensitiveDataAuditService.log(
        db_session,
        actor_user_id=1,
        action="view",
        resource_type="onboarding",
        resource_id=100,
        agency_id=5,
    )
    entries = db_session.query(SensitiveDataAudit).all()
    assert len(entries) == 1
    assert entries[0].actor_user_id == 1
    assert entries[0].action == "view"
    assert entries[0].resource_type == "onboarding"
    assert entries[0].resource_id == 100
    assert entries[0].agency_id == 5
    assert entries[0].reason is None


def test_audit_with_reason(db_session):
    SensitiveDataAuditService.log(
        db_session,
        actor_user_id=2,
        action="export",
        resource_type="merchant",
        resource_id=200,
        agency_id=3,
        reason="Compliance review",
    )
    entries = db_session.query(SensitiveDataAudit).all()
    assert len(entries) == 1
    assert entries[0].reason == "Compliance review"


def test_audit_gateway_call_action(db_session):
    SensitiveDataAuditService.log(
        db_session,
        actor_user_id=0,
        action="gateway_call",
        resource_type="transaction",
        resource_id=42,
        agency_id=1,
    )
    entries = db_session.query(SensitiveDataAudit).all()
    assert len(entries) == 1
    assert entries[0].action == "gateway_call"


def test_audit_decrypt_action(db_session):
    SensitiveDataAuditService.log(
        db_session,
        actor_user_id=10,
        action="decrypt",
        resource_type="channel",
        resource_id=5,
        agency_id=1,
    )
    entries = db_session.query(SensitiveDataAudit).all()
    assert len(entries) == 1
    assert entries[0].action == "decrypt"


def test_multiple_entries(db_session):
    SensitiveDataAuditService.log(db_session, actor_user_id=1, action="view", resource_type="X", resource_id=1, agency_id=1)
    SensitiveDataAuditService.log(db_session, actor_user_id=1, action="modify", resource_type="X", resource_id=1, agency_id=1)
    SensitiveDataAuditService.log(db_session, actor_user_id=1, action="delete", resource_type="X", resource_id=1, agency_id=1)
    assert len(db_session.query(SensitiveDataAudit).all()) == 3
