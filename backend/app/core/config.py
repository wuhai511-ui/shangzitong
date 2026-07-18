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

    def validate_production(self):
        if self.ENV == "prod":
            if not self.JWT_SECRET or len(self.JWT_SECRET) < 32:
                raise RuntimeError("JWT_SECRET must be >= 32 chars in production")
            if self.JWT_SECRET == "dev-secret-change-in-production":
                raise RuntimeError("Default JWT secret forbidden in production")


settings = Settings()
