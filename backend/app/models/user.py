"""User model — inherits from BaseModel (soft-delete support)."""
from sqlalchemy import Column, String
from models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    openid = Column(String(128), unique=True, nullable=False, index=True)
    nickname = Column(String(64), nullable=False, default="")
    phone = Column(String(256), nullable=False, default="")
