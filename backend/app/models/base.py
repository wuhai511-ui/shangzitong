"""
SQLAlchemy base model with soft-delete support.

All business tables inherit from BaseModel.
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, DateTime, func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    """Abstract base with id, timestamps, and soft-delete."""
    __abstract__ = True

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)

    def soft_delete(self):
        """Mark record as deleted without physical removal."""
        self.deleted_at = datetime.utcnow()

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
