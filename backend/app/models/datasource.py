"""DataSource model — represents an external data source connection."""
from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey
from .base import BaseModel


class DataSource(BaseModel):
    __tablename__ = "data_sources"

    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    source_type = Column(String(16), nullable=False)  # oauth / sftp / email / upload
    provider = Column(String(64), nullable=True)
    label = Column(String(128), nullable=True)
    status = Column(Integer, default=1)
