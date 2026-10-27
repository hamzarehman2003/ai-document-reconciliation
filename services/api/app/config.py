"""Application settings, loaded from the .env file in the project root."""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        extra="ignore",
    )

    database_url: str
    gemini_api_key: SecretStr = SecretStr("")

    # Uploads
    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    max_upload_mb: int = 15
    max_files_per_batch: int = 20


settings = Settings()
