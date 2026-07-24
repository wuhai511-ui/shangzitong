from sqlalchemy import Column, BigInteger, String, Numeric, Integer, Time, Text, Boolean, ForeignKey
from .base import BaseModel


class AutoSwipePolicy(BaseModel):
    __tablename__ = "auto_swipe_policies"

    agency_id = Column(BigInteger, ForeignKey("agencies.id"), nullable=False, unique=True)
    max_daily_per_merchant = Column(Numeric(12, 2), nullable=True)
    max_single_amount = Column(Numeric(12, 2), nullable=True)
    min_interest_free_days = Column(Integer, default=0)
    max_parallel_transactions = Column(Integer, default=3)
    retry_strategy = Column(Text, nullable=True)
    swipe_window_start = Column(Time, nullable=True)
    swipe_window_end = Column(Time, nullable=True)
    notification_webhook = Column(String(256), nullable=True)
    is_active = Column(Boolean, default=False)
