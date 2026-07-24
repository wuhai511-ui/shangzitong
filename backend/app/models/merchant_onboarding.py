import enum
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Enum, ForeignKey, Text
from .base import BaseModel

class OnboardingStatus(str, enum.Enum):
    pending = "pending"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"

class MerchantOnboardingApplication(BaseModel):
    __tablename__ = "merchant_onboarding_applications"
    agency_id = Column(BigInteger, nullable=False, index=True)
    merchant_id = Column(BigInteger, ForeignKey("merchants.id"), nullable=False)
    agency_payment_channel_id = Column(BigInteger, ForeignKey("agency_payment_channels.id"), nullable=False)
    provider = Column(String(16), nullable=False)
    provider_application_id = Column(String(128), nullable=True)
    external_merchant_no = Column(String(64), nullable=True)
    status = Column(Enum(OnboardingStatus), default=OnboardingStatus.pending)
    is_simulated = Column(Boolean, default=False)
    request_snapshot = Column(Text, nullable=True)
    response_snapshot = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
