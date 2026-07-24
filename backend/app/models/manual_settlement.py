"""Manually entered settlement amounts (replaces uploaded forecast source)."""
from sqlalchemy import Column, BigInteger, String, Date, Numeric, ForeignKey

from .base import BaseModel


class ManualSettlement(BaseModel):
    __tablename__ = "manual_settlements"

    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    agency_id = Column(BigInteger, nullable=True)
    period_type = Column(String(8), nullable=False)  # day / month
    period_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(14, 2), nullable=False)
    note = Column(String(200), nullable=True)
