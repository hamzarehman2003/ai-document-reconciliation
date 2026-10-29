"""Everything that talks to an AI model.

The rest of the app only calls get_extractor().extract(...), so the provider
can be changed here without touching anything else. Tests replace it with a fake.
"""

from functools import lru_cache

from app.config import settings
from app.llm.base import Extractor
from app.llm.gemini import GeminiExtractor


@lru_cache
def get_extractor() -> Extractor:
    """The extractor the app uses (created once, then reused)."""
    return GeminiExtractor(
        api_key=settings.gemini_api_key.get_secret_value(),
        model=settings.gemini_model,
    )
