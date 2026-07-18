"""Pydantic schemas for upload / datasource API."""
from pydantic import BaseModel


class UploadPreviewResponse(BaseModel):
    mappings: dict
    preview_rows: list
    total_rows: int


class UploadConfirmRequest(BaseModel):
    mappings: dict
    provider: str
