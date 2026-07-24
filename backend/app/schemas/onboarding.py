from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    token: str = Field(..., max_length=256)


class AgencyInfo(BaseModel):
    id: int
    name: str


class VerifyResponse(BaseModel):
    agency: AgencyInfo
    message: str = ""


class OnboardingSubmitRequest(BaseModel):
    name: str = Field(..., max_length=64)
    phone: str = Field(default="", max_length=20)
    business_type: str = Field(default="", max_length=32)
    is_micro: bool = True


class OnboardingSubmitResponse(BaseModel):
    application_id: int
    merchant_id: int
    status: str
