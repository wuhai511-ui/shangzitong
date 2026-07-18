"""Card SQLAlchemy model."""
from decimal import Decimal
from sqlalchemy import Column, BigInteger, String, Integer, Numeric, Enum, ForeignKey
from .base import BaseModel


class Card(BaseModel):
    __tablename__ = "cards"

    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    bank_name = Column(String(32), nullable=False)
    card_tail = Column(String(4), nullable=True)
    credit_limit = Column(Numeric(12, 2), nullable=False)
    temp_limit = Column(Numeric(12, 2), default=Decimal("0"))
    used_limit = Column(Numeric(12, 2), default=Decimal("0"))
    overpayment = Column(Numeric(12, 2), default=Decimal("0"))
    bill_day = Column(Integer, nullable=False)
    due_day = Column(Integer, nullable=False)
    swipe_fee_rate = Column(Numeric(6, 4), default=Decimal("0.006"))
    interest_rate = Column(Numeric(8, 6), default=Decimal("0.0005"))
    min_payment_ratio = Column(Numeric(4, 2), default=Decimal("0.10"))
    installment_amount = Column(Numeric(12, 2), default=Decimal("0"))
    bill_day_inclusive = Column(Integer, default=0)  # 0=当期, 1=下期
    status = Column(Integer, default=1)

    @property
    def avail_limit(self) -> Decimal:
        return self.credit_limit + self.temp_limit - self.used_limit + self.overpayment
