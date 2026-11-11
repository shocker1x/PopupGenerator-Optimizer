from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: SecretStr
    jwt_expire_minutes: int = 60
    gemini_api_key: SecretStr | None = None
    gemini_model: str | None = None
    media_dir: Path = PROJECT_ROOT / "media"
    public_api_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()