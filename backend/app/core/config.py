"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "dev"
    JWT_SECRET: str = ""  # Must be set via env var; no default
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DATABASE_URL: str = "sqlite:///./szt.db"
    WECHAT_APPID: str = ""
    WECHAT_SECRET: str = ""
    ENABLE_EMAIL_INGEST: bool = False
    ENABLE_SFTP_INGEST: bool = False
    UPLOAD_MAX_ROWS: int = 50_000
    UPLOAD_MAX_COLUMNS: int = 100
    UPLOAD_MAX_CELLS: int = 1_000_000
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    UPLOAD_PREVIEW_TTL_SECONDS: int = 900
    PAYMENT_CREDENTIAL_KEY: str = ""
    ENABLE_ONBOARDING: bool = False
    H5_COOKIE_NAME: str = "szt_session"
    H5_TRUSTED_HEADER: str = "X-Authenticated-User"
    H5_ALLOWED_ORIGINS: str = "https://47.253.226.91"

    def validate_production(self):
        if self.ENV == "prod":
            if not self.JWT_SECRET or len(self.JWT_SECRET) < 32:
                raise RuntimeError("JWT_SECRET must be >= 32 chars in production")
            if self.JWT_SECRET == "dev-secret-change-in-production":
                raise RuntimeError("Default JWT secret forbidden in production")


settings = Settings()
