import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestOnboardingInviteModel:

    def test_create_invite(self):
        from models.onboarding_invite import OnboardingInvite
        from core.database import SessionLocal
        from datetime import datetime, timezone, timedelta

        with SessionLocal() as session:
            expires = datetime.now(timezone.utc) + timedelta(hours=72)
            invite = OnboardingInvite(
                agency_id=1,
                channel_id=1,
                token_hash="a" * 64,
                expires_at=expires,
            )
            session.add(invite)
            session.commit()
            session.refresh(invite)

            assert invite.id is not None
            assert invite.agency_id == 1
            assert invite.channel_id == 1
            assert invite.token_hash == "a" * 64
            assert invite.verified_at is None
            assert invite.consumed_at is None
            assert invite.created_at is not None
            assert invite.deleted_at is None

    def test_invite_token_hash_unique(self):
        from models.onboarding_invite import OnboardingInvite
        from core.database import SessionLocal
        from datetime import datetime, timezone, timedelta
        import pytest
        from sqlalchemy.exc import IntegrityError

        with SessionLocal() as session:
            expires = datetime.now(timezone.utc) + timedelta(hours=72)
            invite1 = OnboardingInvite(
                agency_id=1,
                channel_id=1,
                token_hash="unique_token_hash_64_chars_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                expires_at=expires,
            )
            session.add(invite1)
            session.commit()

            invite2 = OnboardingInvite(
                agency_id=1,
                channel_id=1,
                token_hash="unique_token_hash_64_chars_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                expires_at=expires,
            )
            session.add(invite2)
            with pytest.raises((IntegrityError, Exception)):
                session.commit()
            session.rollback()


class TestOnboardingSessionModel:

    def test_create_session(self):
        from models.onboarding_session import OnboardingSession, SessionStatus
        from core.database import SessionLocal
        from datetime import datetime, timezone, timedelta

        with SessionLocal() as session:
            expires = datetime.now(timezone.utc) + timedelta(hours=24)
            s = OnboardingSession(
                invite_id=1,
                agency_id=1,
                session_hash="s" * 64,
                csrf_hash="c" * 64,
                status=SessionStatus.active,
                expires_at=expires,
            )
            session.add(s)
            session.commit()
            session.refresh(s)

            assert s.id is not None
            assert s.invite_id == 1
            assert s.agency_id == 1
            assert s.session_hash == "s" * 64
            assert s.csrf_hash == "c" * 64
            assert s.status == SessionStatus.active
            assert s.ip_address is None
            assert s.revoked_at is None
            assert s.completed_at is None
            assert s.created_at is not None
            assert s.deleted_at is None

    def test_session_status_enum(self):
        from models.onboarding_session import SessionStatus

        assert SessionStatus.active.value == "active"
        assert SessionStatus.revoked.value == "revoked"
        assert SessionStatus.expired.value == "expired"
        assert SessionStatus.completed.value == "completed"

    def test_session_hash_unique(self):
        from models.onboarding_session import OnboardingSession, SessionStatus
        from core.database import SessionLocal
        from datetime import datetime, timezone, timedelta
        import pytest
        from sqlalchemy.exc import IntegrityError

        with SessionLocal() as session:
            expires = datetime.now(timezone.utc) + timedelta(hours=24)
            s1 = OnboardingSession(
                invite_id=1,
                agency_id=1,
                session_hash="unique_session_hash_64_chars_xxxxxxxxxxxxxxxxxxxxxxxxx",
                csrf_hash="c" * 64,
                expires_at=expires,
            )
            session.add(s1)
            session.commit()

            s2 = OnboardingSession(
                invite_id=1,
                agency_id=1,
                session_hash="unique_session_hash_64_chars_xxxxxxxxxxxxxxxxxxxxxxxxx",
                csrf_hash="c2" * 32,
                expires_at=expires,
            )
            session.add(s2)
            with pytest.raises((IntegrityError, Exception)):
                session.commit()
            session.rollback()


class TestOnboardingService:

    def test_token_flow(self):
        import secrets
        import hashlib
        from models.onboarding_invite import OnboardingInvite
        from models.onboarding_session import OnboardingSession, SessionStatus
        from services.onboarding_service import OnboardingService
        from core.database import SessionLocal
        from datetime import datetime, timezone, timedelta

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        with SessionLocal() as session:
            expires = datetime.now(timezone.utc) + timedelta(hours=72)
            invite = OnboardingInvite(
                agency_id=1,
                channel_id=1,
                token_hash=token_hash,
                expires_at=expires,
            )
            session.add(invite)
            session.commit()

            result = OnboardingService.verify_token(session, raw_token)

            assert "session_token" in result
            assert "csrf_token" in result
            assert "agency" in result

            session.refresh(invite)
            assert invite.verified_at is not None

    def test_service_token_verification_logic(self):
        import secrets
        import hashlib
        from models.onboarding_invite import OnboardingInvite
        from services.onboarding_service import OnboardingService
        from core.database import SessionLocal
        from datetime import datetime, timezone, timedelta

        with SessionLocal() as session:
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            expires = datetime.now(timezone.utc) + timedelta(hours=0)
            invite = OnboardingInvite(
                agency_id=1,
                channel_id=1,
                token_hash=token_hash,
                expires_at=expires,
            )
            session.add(invite)
            session.commit()

            import time
            time.sleep(0.01)

            import pytest
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                OnboardingService.verify_token(session, raw_token)
            assert "expired" in str(exc.value.detail).lower()
