"""Pydantic schemas for manual settlement CRUD."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from schemas.cashflow import Money


PERIOD_TYPES = ("day", "month")


class ManualSettlementCreate(BaseModel):
    period_type: Literal["day", "month"]
    period_date: date
    amount: Decimal = Field(..., ge=0)
    note: str | None = Field(default=None, max_length=200)


class ManualSettlementResponse(BaseModel):
    id: int
    period_type: str
    period_date: date
    amount: Money
    note: str | None
    created_at: datetime

    class Config:
        from_attributes = True
