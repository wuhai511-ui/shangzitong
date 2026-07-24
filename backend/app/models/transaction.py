from sqlalchemy import Column, BigInteger, String, Numeric, Integer, DateTime, Text, Boolean, ForeignKey, Index
from .base import BaseModel


class Transaction(BaseModel):
    __tablename__ = "transactions"

    agency_id = Column(BigInteger, nullable=False, index=True)
    merchant_id = Column(BigInteger, ForeignKey("merchants.id"), nullable=False)
    merchant_no = Column(String(64), nullable=False)
    card_id = Column(BigInteger, ForeignKey("cards.id"), nullable=True)
    provider = Column(String(16), nullable=False)
    channel_id = Column(BigInteger, ForeignKey("agency_payment_channels.id"), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    idempotency_key = Column(String(128), unique=True, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    scheduled_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    provider_txn_id = Column(String(128), nullable=True)
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    result_snapshot = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_transactions_agency_merchant_status_scheduled", "agency_id", "merchant_id", "status", "scheduled_at"),
        Index("ix_transactions_status_scheduled", "status", "scheduled_at"),
    )
