from sqlalchemy import Column, BigInteger, String, Integer, Text, ForeignKey
from .base import BaseModel


class SensitiveDataAudit(BaseModel):
    __tablename__ = "sensitive_data_audits"
    actor_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    action = Column(String(32), nullable=False)
    resource_type = Column(String(32), nullable=False)
    resource_id = Column(BigInteger, nullable=False)
    agency_id = Column(BigInteger, nullable=False)
    reason = Column(String(128), nullable=True)
