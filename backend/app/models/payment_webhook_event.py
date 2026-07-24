from sqlalchemy import Column, BigInteger, String, Integer, DateTime, Text, ForeignKey
from .base import BaseModel


class PaymentWebhookEvent(BaseModel):
    __tablename__ = "payment_webhook_events"
    agency_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, ForeignKey("agency_payment_channels.id"), nullable=False)
    provider = Column(String(16), nullable=False)
    provider_event_type = Column(String(64), nullable=False)
    provider_event_id = Column(String(128), unique=True, nullable=False)
    raw_body = Column(Text, nullable=False)
    application_id = Column(BigInteger, nullable=True)
    status = Column(String(20), default="received")
    attempt_count = Column(Integer, default=1)
    last_error = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
