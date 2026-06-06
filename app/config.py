from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./tiramisu.db"

    jwt_secret: str = "dev-only-change-me-dev-only-change-me"  # 36 chars; override in prod via JWT_SECRET env
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 30  # 30 days

    dev_mode: bool = True
    dev_otp: str = "123456"

    sms_gateway: str = "stub"  # 'stub' | 'msg91' | 'twilio'


@lru_cache
def get_settings() -> Settings:
    return Settings()
