"""User model — inherits from BaseModel (soft-delete support)."""
from sqlalchemy import Column, BigInteger, Boolean, Integer, String
from models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    openid = Column(String(128), unique=True, nullable=False, index=True)
    nickname = Column(String(64), nullable=False, default="")
    phone = Column(String(256), nullable=False, default="")
    agency_id = Column(BigInteger, nullable=True)
    role = Column(String(20), default="merchant")
    auth_method = Column(String(20), default="basic_auth_proxy")
    password_hash = Column(String(128), nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    status = Column(Integer, default=1)
