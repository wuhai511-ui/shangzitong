from datetime import datetime

from pydantic import BaseModel, Field


class AgencyCreate(BaseModel):
    name: str = Field(..., max_length=64)
    contact_name: str = Field(default="", max_length=32)
    contact_phone: str = Field(default="", max_length=20)


class AgencyUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    contact_name: str | None = Field(default=None, max_length=32)
    contact_phone: str | None = Field(default=None, max_length=20)
    status: int | None = None


class AgencyResponse(BaseModel):
    id: int
    name: str
    contact_name: str
    contact_phone: str
    status: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
