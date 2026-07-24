"""SFTP data source configuration model."""
from sqlalchemy import Column, BigInteger, String, Integer, Boolean, DateTime, ForeignKey
from .base import BaseModel


class SftpConfig(BaseModel):
    __tablename__ = "sftp_configs"

    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    agency_id = Column(BigInteger, nullable=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, default=22, nullable=False)
    username = Column(String(128), nullable=False)
    password = Column(String(255), nullable=True)
    remote_path = Column(String(512), default="/", nullable=False)
    file_pattern = Column(String(64), default="*.csv", nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    last_poll_at = Column(DateTime, nullable=True)
