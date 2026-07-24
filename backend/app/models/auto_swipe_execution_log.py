from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, ForeignKey, func
from .base import Base


class AutoSwipeExecutionLog(Base):
    __tablename__ = "auto_swipe_execution_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(BigInteger, ForeignKey("transactions.id"), nullable=True)
    agency_id = Column(BigInteger, nullable=False)
    event_type = Column(String(32), nullable=False)
    event_data = Column(Text, nullable=True)
    severity = Column(String(10), default="info")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
