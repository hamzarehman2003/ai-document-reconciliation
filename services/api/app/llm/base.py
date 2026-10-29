"""What every AI extractor takes in and gives back.

Code outside this package only uses these types, so the AI provider
(Gemini today) can be swapped without touching the rest of the app.
"""

from dataclasses import dataclass
from typing import Protocol

from app.llm.schema import DocumentExtraction


@dataclass(frozen=True)
class PageImage:
    data: bytes
    mime_type: str


@dataclass(frozen=True)
class PreparedDocument:
    """What we send to the AI: page images plus the PDF's text (if any)."""

    images: list[PageImage]
    text: str = ""


@dataclass(frozen=True)
class ExtractionResult:
    data: DocumentExtraction
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int | None = None


class PermanentExtractionError(Exception):
    """The AI request can never succeed as is (bad key, rejected input...)."""


class Extractor(Protocol):
    def extract(self, document: PreparedDocument) -> ExtractionResult: ...
