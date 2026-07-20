"""Email data source configuration model."""
from sqlalchemy import Column, BigInteger, String, Integer, Boolean, DateTime, ForeignKey
from .base import BaseModel


class EmailConfig(BaseModel):
    __tablename__ = "email_configs"

    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    imap_host = Column(String(255), nullable=False)
    imap_port = Column(Integer, default=993, nullable=False)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    use_ssl = Column(Boolean, default=True, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    last_poll_at = Column(DateTime, nullable=True)
