from sqlalchemy import Column, BigInteger, Integer, String, ForeignKey, UniqueConstraint
from .base import BaseModel


class AgencyPaymentChannel(BaseModel):
    __tablename__ = "agency_payment_channels"

    agency_id = Column(BigInteger, ForeignKey("agencies.id"), nullable=False)
    provider = Column(String(16), nullable=False)
    org_no = Column(String(64), nullable=False)
    api_key_cipher = Column(String(512), default="")
    api_secret_cipher = Column(String(512), default="")
    key_version = Column(Integer, default=1)
    status = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("agency_id", "provider", "org_no"),
    )
