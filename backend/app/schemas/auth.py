"""Pydantic schemas for auth API."""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    code: str


class UserInfo(BaseModel):
    id: int
    openid: str
    nickname: str

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo
