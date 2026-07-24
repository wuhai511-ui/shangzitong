from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChannelCreate(BaseModel):
    provider: Literal["lkl", "huifu"]
    org_no: str = Field(..., max_length=64)
    api_key: str = Field(..., max_length=512)
    api_secret: str = Field(..., max_length=512)


class ChannelResponse(BaseModel):
    id: int
    agency_id: int
    provider: str
    org_no: str
    api_key_masked: str
    api_secret_masked: str
    key_version: int
    status: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
