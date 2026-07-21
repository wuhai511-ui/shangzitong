"""Pydantic schemas for upload / datasource API."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UploadPreviewResponse(BaseModel):
    preview_id: str
    mappings: dict
    preview_rows: list
    total_rows: int
    expires_at: datetime


class UploadConfirmRequest(BaseModel):
    preview_id: Optional[str] = None
    mappings: dict
    provider: str


class SftpConfigureRequest(BaseModel):
    host: str
    port: int = 22
    username: str
    password: Optional[str] = None
    remote_path: str = "/"
    file_pattern: str = "*.csv"


class SftpStatusResponse(BaseModel):
    connected: bool
    message: str
    host: str
    remote_path: str
    file_pattern: str
    files_found: int = 0
    last_poll_at: Optional[datetime] = None


class SftpTriggerResponse(BaseModel):
    message: str
    files_processed: int = 0
    settlements_imported: int = 0
    errors: list[str] = []


class EmailConfigureRequest(BaseModel):
    email: str
    imap_host: str
    imap_port: int = 993
    username: str
    password: str
    use_ssl: bool = True


class EmailStatusResponse(BaseModel):
    enabled: bool
    message: str
    email: str
    imap_host: str
    last_poll_at: Optional[datetime] = None


class EmailTriggerResponse(BaseModel):
    message: str
    emails_processed: int = 0
    settlements_imported: int = 0
    errors: list[str] = []
