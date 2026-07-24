from sqlalchemy import Column, BigInteger, Boolean, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel


class Merchant(BaseModel):
    __tablename__ = "merchants"

    agency_id = Column(BigInteger, ForeignKey("agencies.id"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    name = Column(String(64), nullable=False, default="")
    phone = Column(String(20), nullable=False, default="")
    business_type = Column(String(32), nullable=False, default="")
    is_micro = Column(Boolean, default=True)
    auto_swipe_enabled = Column(Boolean, default=False)

    onboarding_applications = relationship(
        "MerchantOnboardingApplication",
        backref="merchant",
        lazy="joined",
    )
