"""Typed contracts for the canonical daily cashflow ledger."""
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Literal

from pydantic import BaseModel, Field, PlainSerializer, field_serializer


MONEY_QUANTUM = Decimal("0.01")


def serialize_money(value: Decimal) -> str:
    return format(
        Decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP),
        ".2f",
    )


Money = Annotated[
    Decimal,
    PlainSerializer(serialize_money, return_type=str, when_used="json"),
]


class RepaymentEvent(BaseModel):
    type: Literal["repayment"] = "repayment"
    card_id: int
    bank_name: str
    amount: Money
    min_payment: Money


class CashflowDay(BaseModel):
    date: date
    opening_balance: Money
    settlements: Money
    repayments: Money
    purchases: Money = Decimal("0.00")
    other_outflows: Money = Decimal("0.00")
    closing_balance: Money
    funding_gap: Money
    events: list[dict] = Field(default_factory=list)

    @field_serializer("events", when_used="json")
    def serialize_event_money(self, events: list[dict]) -> list[dict]:
        serialized = []
        for event in events:
            data = dict(event)
            for field in ("amount", "min_payment"):
                if field in data:
                    data[field] = serialize_money(data[field])
            serialized.append(data)
        return serialized


class CashflowResponse(BaseModel):
    days: list[CashflowDay]
    is_estimate: bool
    available_cash: Money | None
    available_cash_updated_at: datetime | None
