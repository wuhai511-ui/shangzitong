"""Pydantic schemas for Card CRUD."""
from decimal import Decimal
from datetime import date
from pydantic import BaseModel, Field, model_validator


class CardCreate(BaseModel):
    bank_name: str = Field(..., min_length=1, max_length=32)
    card_tail: str = Field(default="", max_length=4)
    credit_limit: Decimal = Field(..., gt=0)
    used_limit: Decimal = Field(default=Decimal("0"), ge=0)
    temp_limit: Decimal = Field(default=Decimal("0"), ge=0)
    overpayment: Decimal = Field(default=Decimal("0"), ge=0)
    bill_day: int = Field(..., ge=1, le=28)
    due_day: int = Field(..., ge=1, le=31)
    swipe_fee_rate: Decimal = Field(default=Decimal("0.006"), ge=0, le=Decimal("1"))
    interest_rate: Decimal = Field(default=Decimal("0.0005"), ge=0)
    min_payment_ratio: Decimal = Field(default=Decimal("0.10"), ge=0, le=Decimal("1"))
    installment_amount: Decimal = Field(default=Decimal("0"), ge=0)
    bill_day_inclusive: int = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def validate_limits(self):
        if self.used_limit > self.credit_limit:
            raise ValueError("已用额度不能超过总额度")
        return self


class CardUpdate(BaseModel):
    bank_name: str | None = None
    card_tail: str | None = None
    credit_limit: Decimal | None = None
    used_limit: Decimal | None = None
    temp_limit: Decimal | None = None
    overpayment: Decimal | None = None
    bill_day: int | None = None
    due_day: int | None = None
    swipe_fee_rate: Decimal | None = None
    interest_rate: Decimal | None = None
    min_payment_ratio: Decimal | None = None
    installment_amount: Decimal | None = None
    bill_day_inclusive: int | None = None


class CardResponse(BaseModel):
    id: int
    user_id: int
    bank_name: str
    card_tail: str
    credit_limit: Decimal
    temp_limit: Decimal
    used_limit: Decimal
    overpayment: Decimal
    avail_limit: Decimal
    bill_day: int
    due_day: int
    swipe_fee_rate: Decimal
    interest_rate: Decimal
    min_payment_ratio: Decimal
    installment_amount: Decimal
    bill_day_inclusive: int
    status: int

    class Config:
        from_attributes = True


class InterestFreeInfo(BaseModel):
    free_days: int
    repayment_date: date
    bill_date: date
