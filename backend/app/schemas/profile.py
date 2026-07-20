"""Schemas for merchant profile endpoints."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CashProfileUpdate(BaseModel):
    available_cash: Decimal | None = Field(default=None, ge=0)


class CashProfileResponse(BaseModel):
    available_cash: Decimal | None
    available_cash_updated_at: datetime | None
    is_estimate: bool
