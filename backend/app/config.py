from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/pos_system"
    SECRET_KEY: str = "dev-secret-key-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    UPLOAD_DIR: str = "uploads"
    AUTH_REGISTER_RATE_LIMIT: str = "5/minute"
    AUTH_LOGIN_RATE_LIMIT: str = "10/minute"
    # IANA zone that defines the sellers' business day ("today", daily buckets, weekday patterns).
    BUSINESS_TIMEZONE: str = "Asia/Manila"


settings = Settings()
