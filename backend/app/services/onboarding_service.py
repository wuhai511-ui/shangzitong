import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models.onboarding_invite import OnboardingInvite
from models.onboarding_session import OnboardingSession, SessionStatus
from models.merchant import Merchant
from models.merchant_onboarding import MerchantOnboardingApplication, OnboardingStatus
from models.agency import Agency
from models.agency_payment_channel import AgencyPaymentChannel
from core.auth_context import UserContext


class OnboardingService:
    SESSION_TTL_HOURS = 24
    ONBOARDING_COOKIE = "szt_onboarding"
    CSRF_COOKIE = "szt_onboarding_csrf"

    @staticmethod
    def generate_invite(
        db: Session, ctx: UserContext, channel_id: int, expires_in_hours: int = 72
    ) -> dict:
        if ctx.role not in ("super_admin", "agent_admin"):
            raise HTTPException(403, "Permission denied")

        agency_id = ctx.agency_id if ctx.role == "agent_admin" else 0

        channel = db.query(AgencyPaymentChannel).filter(
            AgencyPaymentChannel.id == channel_id,
            AgencyPaymentChannel.deleted_at.is_(None),
        ).first()
        if not channel:
            raise HTTPException(404, "Payment channel not found")
        if ctx.role == "agent_admin" and channel.agency_id != agency_id:
            raise HTTPException(404, "Payment channel not found")

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

        invite = OnboardingInvite(
            agency_id=channel.agency_id,
            channel_id=channel_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(invite)
        db.commit()
        db.refresh(invite)

        return {
            "invite_id": invite.id,
            "token": raw_token,
            "expires_at": expires_at.isoformat(),
        }

    @staticmethod
    def verify_token(db: Session, token: str) -> dict:
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        invite = db.query(OnboardingInvite).filter(
            OnboardingInvite.token_hash == token_hash,
            OnboardingInvite.deleted_at.is_(None),
        ).first()

        if not invite:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired invite token")

        now = datetime.now(timezone.utc)
        if invite.expires_at and invite.expires_at.replace(tzinfo=timezone.utc) < now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite token has expired")

        if invite.consumed_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite token has already been used")

        if invite.verified_at is None:
            invite.verified_at = now

        session_token = secrets.token_urlsafe(32)
        session_hash = hashlib.sha256(session_token.encode()).hexdigest()
        csrf_token = secrets.token_urlsafe(32)
        csrf_hash = hashlib.sha256(csrf_token.encode()).hexdigest()
        session_expires = now + timedelta(hours=OnboardingService.SESSION_TTL_HOURS)

        session = OnboardingSession(
            invite_id=invite.id,
            agency_id=invite.agency_id,
            session_hash=session_hash,
            csrf_hash=csrf_hash,
            status=SessionStatus.active,
            expires_at=session_expires,
        )
        db.add(session)
        db.commit()

        agency = db.query(Agency).filter(Agency.id == invite.agency_id).first()

        return {
            "session_token": session_token,
            "csrf_token": csrf_token,
            "session_expires_at": session_expires.isoformat(),
            "agency": {
                "id": agency.id if agency else invite.agency_id,
                "name": agency.name if agency else "",
            },
        }

    @staticmethod
    def get_session(db: Session, session_token: str) -> OnboardingSession:
        session_hash = hashlib.sha256(session_token.encode()).hexdigest()

        session = db.query(OnboardingSession).filter(
            OnboardingSession.session_hash == session_hash,
            OnboardingSession.deleted_at.is_(None),
        ).first()

        if not session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid onboarding session")

        if session.status != SessionStatus.active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Onboarding session is no longer active")

        now = datetime.now(timezone.utc)
        if session.expires_at and session.expires_at.replace(tzinfo=timezone.utc) < now:
            session.status = SessionStatus.expired
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Onboarding session has expired")

        return session

    @staticmethod
    def validate_csrf(session: OnboardingSession, csrf_token: str) -> None:
        csrf_hash = hashlib.sha256(csrf_token.encode()).hexdigest()
        if csrf_hash != session.csrf_hash:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")

    @staticmethod
    def submit_onboarding(
        db: Session,
        session: OnboardingSession,
        name: str,
        phone: str,
        business_type: str,
        is_micro: bool,
    ) -> dict:
        invite = db.query(OnboardingInvite).filter(
            OnboardingInvite.id == session.invite_id,
            OnboardingInvite.deleted_at.is_(None),
        ).first()
        if not invite:
            raise HTTPException(400, "Invite not found")

        channel = db.query(AgencyPaymentChannel).filter(
            AgencyPaymentChannel.id == invite.channel_id,
        ).first()
        provider = channel.provider.value if channel else ""

        merchant = Merchant(
            agency_id=invite.agency_id,
            name=name,
            phone=phone,
            business_type=business_type,
            is_micro=is_micro,
            auto_swipe_enabled=False,
        )
        db.add(merchant)
        db.flush()

        application = MerchantOnboardingApplication(
            agency_id=invite.agency_id,
            merchant_id=merchant.id,
            agency_payment_channel_id=invite.channel_id,
            provider=provider,
            status=OnboardingStatus.submitted,
            is_simulated=False,
            submitted_at=datetime.now(timezone.utc),
        )
        db.add(application)

        invite.consumed_at = datetime.now(timezone.utc)
        session.status = SessionStatus.completed
        session.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(application)

        return {
            "application_id": application.id,
            "merchant_id": merchant.id,
            "status": application.status.value,
        }
