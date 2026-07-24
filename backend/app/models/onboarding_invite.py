from sqlalchemy import Column, BigInteger, DateTime, String, ForeignKey
from .base import BaseModel


class OnboardingInvite(BaseModel):
    __tablename__ = "onboarding_invites"

    agency_id = Column(BigInteger, ForeignKey("agencies.id"), nullable=False)
    channel_id = Column(BigInteger, ForeignKey("agency_payment_channels.id"), nullable=True)
    token_hash = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    consumed_at = Column(DateTime, nullable=True)
