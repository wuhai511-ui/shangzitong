from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    merchant_id: int
    merchant_no: str = Field(..., max_length=64)
    card_id: int
    provider: str = Field(..., max_length=16)
    channel_id: int
    amount: Decimal = Field(..., max_digits=12, decimal_places=2)
    swipe_date: date
    seq: int = 1


class TransactionResponse(BaseModel):
    id: int
    agency_id: int
    merchant_id: int
    merchant_no: str
    card_id: int | None
    provider: str
    channel_id: int | None
    amount: Decimal
    idempotency_key: str
    status: str
    scheduled_at: datetime | None
    executed_at: datetime | None
    provider_txn_id: str | None
    retry_count: int
    last_error: str | None
    result_snapshot: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
