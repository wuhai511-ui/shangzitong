from sqlalchemy import Column, BigInteger, Boolean, DateTime, String, Text, ForeignKey
from .base import BaseModel


class MerchantOnboardingApplication(BaseModel):
    __tablename__ = "merchant_onboarding_applications"

    agency_id = Column(BigInteger, nullable=False)
    merchant_id = Column(BigInteger, ForeignKey("merchants.id"), nullable=True)
    agency_payment_channel_id = Column(BigInteger, ForeignKey("agency_payment_channels.id"), nullable=True)
    provider = Column(String(16), nullable=False, default="")
    provider_application_id = Column(String(128), nullable=True)
    external_merchant_no = Column(String(64), nullable=True)
    status = Column(String(20), default="pending")
    is_simulated = Column(Boolean, default=False)
    request_snapshot = Column(Text, nullable=True)
    response_snapshot = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
