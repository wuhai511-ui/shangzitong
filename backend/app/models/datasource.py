"""Data source and settlement models."""
from sqlalchemy import Column, BigInteger, String, Integer, Numeric, Date, ForeignKey
from .base import BaseModel
from decimal import Decimal


class DataSource(BaseModel):
    __tablename__ = "data_sources"

    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    agency_id = Column(BigInteger, nullable=True)
    source_type = Column(String(16), nullable=False)  # oauth / sftp / email / upload
    provider = Column(String(64), nullable=True)
    label = Column(String(128), nullable=True)
    status = Column(Integer, default=1)


class Settlement(BaseModel):
    __tablename__ = "settlements"

    source_id = Column(BigInteger, ForeignKey("data_sources.id"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    agency_id = Column(BigInteger, nullable=True)
    settle_date = Column(Date, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    provider = Column(String(64), nullable=True)
    batch_hash = Column(String(128), nullable=True)
