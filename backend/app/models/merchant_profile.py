"""Per-merchant optional financial profile data."""
from sqlalchemy import Column, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship

from models.base import BaseModel


class MerchantProfile(BaseModel):
    __tablename__ = "merchant_profiles"

    user_id = Column(ForeignKey("users.id"), unique=True, nullable=False, index=True)
    available_cash = Column(Numeric(14, 2), nullable=True)
    available_cash_updated_at = Column(DateTime, nullable=True)
    user = relationship("User")
