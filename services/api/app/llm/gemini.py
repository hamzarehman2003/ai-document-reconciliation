"""Read documents with Google Gemini, using the official google-genai SDK."""

import time

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from app.llm.base import ExtractionResult, PermanentExtractionError, PreparedDocument
from app.llm.prompt import build_prompt
from app.llm.schema import DocumentExtraction

REQUEST_TIMEOUT_MS = 120_000
# Busy, rate-limited or a server hiccup: worth trying again later.
RETRYABLE_CODES = {408, 429, 500, 502, 503, 504}


class GeminiExtractor:
    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self._client = (
            genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
            )
            if api_key
            else None
        )

    def extract(self, document: PreparedDocument) -> ExtractionResult:
        """Send the page images (and any PDF text) and get validated data back."""
        if self._client is None:
            raise PermanentExtractionError("GEMINI_API_KEY is not set in .env.")

        parts = [
            types.Part.from_bytes(data=image.data, mime_type=image.mime_type)
            for image in document.images
        ]
        parts.append(types.Part.from_text(text=build_prompt(document.text)))
        config = types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=DocumentExtraction.model_json_schema(),
        )

        started = time.monotonic()
        try:
            response = self._client.models.generate_content(
                model=self.model, contents=parts, config=config
            )
        except errors.APIError as error:
            if error.code in RETRYABLE_CODES:
                # A normal exception: the worker retries with backoff.
                raise RuntimeError(
                    f"Gemini is temporarily unavailable ({error.code} {error.status})."
                ) from error
            raise PermanentExtractionError(
                f"Gemini rejected the request ({error.code} {error.status})."
            ) from error
        except Exception as error:
            # Timeouts, no internet, DNS failures...: temporary, so retried.
            raise RuntimeError(
                "Could not reach Gemini (network problem or timeout)."
            ) from error
        duration_ms = int((time.monotonic() - started) * 1000)

        try:
            data = DocumentExtraction.model_validate_json(response.text or "")
        except ValidationError as error:
            # Rare; usually fine on the next try, so let the worker retry.
            raise ValueError("Gemini's answer did not match the schema.") from error

        usage = response.usage_metadata
        return ExtractionResult(
            data=data,
            model=response.model_version or self.model,
            input_tokens=usage.prompt_token_count if usage else None,
            output_tokens=usage.candidates_token_count if usage else None,
            duration_ms=duration_ms,
        )
