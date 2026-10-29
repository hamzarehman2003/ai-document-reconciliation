"""The Gemini connector, tested with a fake client (no network, no quota)."""

from types import SimpleNamespace

import pytest
from google.genai import errors

from app.llm.base import PageImage, PermanentExtractionError, PreparedDocument
from app.llm.gemini import GeminiExtractor
from fakes import sample_extraction

DOCUMENT = PreparedDocument(images=[PageImage(b"\x89PNG...", "image/png")], text="")


def extractor_that(answer: object) -> GeminiExtractor:
    """A GeminiExtractor whose client returns (or raises) `answer`."""

    def generate_content(**kwargs: object) -> object:
        if isinstance(answer, Exception):
            raise answer
        return answer

    extractor = GeminiExtractor(api_key="test-key", model="gemini-test")
    extractor._client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )
    return extractor


def api_error(code: int, status: str) -> errors.APIError:
    return errors.APIError(code, {"error": {"code": code, "status": status}})


def test_valid_answer_is_parsed() -> None:
    response = SimpleNamespace(
        text=sample_extraction().model_dump_json(),
        model_version="gemini-test-001",
        usage_metadata=SimpleNamespace(
            prompt_token_count=1500, candidates_token_count=300
        ),
    )

    result = extractor_that(response).extract(DOCUMENT)

    assert result.data == sample_extraction()
    assert result.model == "gemini-test-001"
    assert (result.input_tokens, result.output_tokens) == (1500, 300)


def test_busy_gemini_is_temporary() -> None:
    with pytest.raises(RuntimeError, match="temporarily unavailable"):
        extractor_that(api_error(503, "UNAVAILABLE")).extract(DOCUMENT)


def test_rejected_request_is_permanent() -> None:
    with pytest.raises(PermanentExtractionError, match="rejected"):
        extractor_that(api_error(400, "INVALID_ARGUMENT")).extract(DOCUMENT)


def test_network_problem_is_temporary_with_a_clear_message() -> None:
    with pytest.raises(RuntimeError, match="Could not reach Gemini"):
        extractor_that(OSError("[Errno 11001] getaddrinfo failed")).extract(DOCUMENT)


def test_answer_in_the_wrong_shape_is_retried() -> None:
    response = SimpleNamespace(
        text='{"doc_type": "letter"}', model_version=None, usage_metadata=None
    )
    with pytest.raises(ValueError, match="did not match the schema"):
        extractor_that(response).extract(DOCUMENT)


def test_missing_api_key_is_permanent() -> None:
    with pytest.raises(PermanentExtractionError, match="GEMINI_API_KEY"):
        GeminiExtractor(api_key="", model="gemini-test").extract(DOCUMENT)
