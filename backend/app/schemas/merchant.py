from datetime import datetime
from pydantic import BaseModel, Field


class MerchantCreate(BaseModel):
    name: str = Field(..., max_length=64)
    phone: str = Field(default="", max_length=20)
    business_type: str = Field(default="", max_length=32)
    is_micro: bool = True
    channel_id: int


class MerchantResponse(BaseModel):
    id: int
    agency_id: int
    user_id: int | None
    name: str
    phone: str
    business_type: str
    is_micro: bool
    auto_swipe_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MerchantOnboardingAppResponse(BaseModel):
    id: int
    agency_id: int
    merchant_id: int
    agency_payment_channel_id: int
    provider: str
    provider_application_id: str | None
    external_merchant_no: str | None
    status: str
    is_simulated: bool
    request_snapshot: str | None
    response_snapshot: str | None
    submitted_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MerchantDetailResponse(MerchantResponse):
    onboarding_applications: list[MerchantOnboardingAppResponse] = []
