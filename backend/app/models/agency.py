from sqlalchemy import Column, Integer, String
from .base import BaseModel


class Agency(BaseModel):
    __tablename__ = "agencies"

    name = Column(String(64), nullable=False)
    contact_name = Column(String(32), nullable=False, default="")
    contact_phone = Column(String(20), nullable=False, default="")
    status = Column(Integer, default=0)
