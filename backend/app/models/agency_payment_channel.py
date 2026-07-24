import enum
from sqlalchemy import Column, BigInteger, String, Integer, Enum, ForeignKey, UniqueConstraint
from .base import BaseModel

class PaymentProvider(str, enum.Enum):
    lkl = "lkl"
    huifu = "huifu"

class AgencyPaymentChannel(BaseModel):
    __tablename__ = "agency_payment_channels"
    __table_args__ = (UniqueConstraint("agency_id", "provider", "org_no", name="uq_agency_provider_org"),)
    agency_id = Column(BigInteger, ForeignKey("agencies.id"), nullable=False)
    provider = Column(Enum(PaymentProvider), nullable=False)
    org_no = Column(String(64), nullable=False)
    api_key_cipher = Column(String(512), nullable=False, default="")
    api_secret_cipher = Column(String(512), nullable=False, default="")
    key_version = Column(Integer, default=1)
    status = Column(Integer, default=0)
