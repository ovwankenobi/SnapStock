from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/pos_system"
    SECRET_KEY: str = "dev-secret-key-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    # "local" keeps uploads on disk (development); "s3" stores them in S3_BUCKET (production).
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    UPLOAD_DIR: str = "uploads"
    # Payment screenshots in local mode. Kept outside UPLOAD_DIR, which is served publicly.
    PRIVATE_UPLOAD_DIR: str = "uploads_private"
    S3_BUCKET: str | None = None
    AWS_REGION: str = "ap-southeast-1"
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024
    PRIVATE_URL_TTL_SECONDS: int = 15 * 60
    PUBLIC_URL_TTL_SECONDS: int = 60 * 60
    AUTH_REGISTER_RATE_LIMIT: str = "5/minute"
    AUTH_LOGIN_RATE_LIMIT: str = "10/minute"
    AUTH_FORGOT_PASSWORD_RATE_LIMIT: str = "3/minute"
    AUTH_RESET_PASSWORD_RATE_LIMIT: str = "10/minute"
    AUTH_CHANGE_PASSWORD_RATE_LIMIT: str = "3/minute"
    AUTH_QR_LOGIN_RATE_LIMIT: str = "10/minute"
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    # Base URL of the web app, used to build links in emails (e.g. the password reset link).
    FRONTEND_URL: str = "http://localhost:5173"
    # Outgoing mail. With SMTP_HOST unset (local dev), emails are logged instead of sent.
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    SMTP_USE_TLS: bool = True
    # IANA zone that defines the sellers' business day ("today", daily buckets, weekday patterns).
    BUSINESS_TIMEZONE: str = "Asia/Manila"

    @model_validator(mode="after")
    def _check_s3_bucket(self):
        if self.STORAGE_BACKEND == "s3" and not self.S3_BUCKET:
            raise ValueError("S3_BUCKET is required when STORAGE_BACKEND is s3")
        return self


settings = Settings()
