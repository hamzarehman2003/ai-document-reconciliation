"""Application settings, loaded from the .env file in the project root."""

from decimal import Decimal
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

    # Login (Supabase Auth): the project URL, e.g. https://abcd.supabase.co.
    # Tokens are checked with the project's public keys, so no secret is needed.
    supabase_url: str = ""

    # AI extraction
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-flash-lite-latest"
    max_pages: int = 5

    # Uploads
    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    max_upload_mb: int = 15
    max_files_per_batch: int = 20

    # 3-way matching: how much difference is still accepted
    price_tolerance_percent: Decimal = Decimal("0")
    quantity_tolerance_percent: Decimal = Decimal("0")
    amount_tolerance: Decimal = Decimal("0.01")

    # Background worker
    worker_poll_seconds: float = 1.0
    job_retry_base_seconds: int = 30
    stale_job_minutes: int = 10


settings = Settings()
