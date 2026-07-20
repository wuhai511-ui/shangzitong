"""Typed contracts for the canonical daily cashflow ledger."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class RepaymentEvent(BaseModel):
    type: Literal["repayment"] = "repayment"
    card_id: int
    bank_name: str
    amount: Decimal
    min_payment: Decimal


class CashflowDay(BaseModel):
    date: date
    opening_balance: Decimal
    settlements: Decimal
    repayments: Decimal
    purchases: Decimal = Decimal("0.00")
    other_outflows: Decimal = Decimal("0.00")
    closing_balance: Decimal
    funding_gap: Decimal
    events: list[dict] = Field(default_factory=list)


class CashflowResponse(BaseModel):
    days: list[CashflowDay]
    is_estimate: bool
    available_cash: Decimal | None
    available_cash_updated_at: datetime | None
