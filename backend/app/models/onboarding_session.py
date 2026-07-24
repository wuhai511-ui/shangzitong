import enum
from sqlalchemy import Column, BigInteger, DateTime, String, Enum, ForeignKey
from .base import BaseModel


class SessionStatus(str, enum.Enum):
    active = "active"
    revoked = "revoked"
    expired = "expired"
    completed = "completed"


class OnboardingSession(BaseModel):
    __tablename__ = "onboarding_sessions"

    invite_id = Column(BigInteger, ForeignKey("onboarding_invites.id"), nullable=False)
    agency_id = Column(BigInteger, nullable=False)
    session_hash = Column(String(64), unique=True, nullable=False)
    csrf_hash = Column(String(64), nullable=False)
    status = Column(Enum(SessionStatus), default=SessionStatus.active)
    ip_address = Column(String(45), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
