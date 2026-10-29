"""Run the real pipeline on the generated documents. Nothing is saved to the database.

The same code as the app is used: page preparation, the Gemini extractor, value
cleaning, evidence finding and the matching rules.
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.evaluation.truth import ExpectedDocument, ExpectedSet, earlier_invoices
from app.llm.base import (
    ExtractionResult,
    Extractor,
    PermanentExtractionError,
    PreparedDocument,
)
from app.llm.prompt import PROMPT_VERSION
from app.llm.schema import DocumentExtraction
from app.models import Document, FieldEvidence
from app.rules import Finding, check_invoice
from app.services.evidence import find_evidence
from app.services.extraction import apply_extraction, find_cached_extraction
from app.services.matching import to_rules_data
from app.services.page_text import read_page_lines
from app.services.pages import prepare_document
from app.services.uploads import detect_file_type, sha256

RETRIES = 4
RETRY_SECONDS = 30
FIRST_DOCUMENT_ID = 1_000_000  # in-memory ids that can't clash with set numbers


@dataclass(frozen=True)
class Reading:
    """What the AI read, and where the answer came from."""

    data: DocumentExtraction
    source: str  # "ai", "file cache" or "database cache"
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int | None = None


Reader = Callable[[Path, str], Reading]  # (file, content type) → reading


@dataclass
class DocumentResult:
    expected: ExpectedDocument
    document: Document | None = None  # what was read, in memory only
    reading: Reading | None = None
    evidence: list[FieldEvidence] = field(default_factory=list)
    words_seconds: float | None = None  # time to read the words (OCR for scans)
    error: str | None = None


@dataclass
class SetResult:
    expected: ExpectedSet
    documents: list[DocumentResult]
    found_codes: list[str]
    messages: list[str]


class CachedReader:
    """Reads with Gemini, but reuses any earlier read of the same file.

    Looks in a local file cache first, then in the app's `extractions` table,
    so re-running the evaluation costs no quota.
    """

    def __init__(
        self,
        cache_dir: Path,
        extractor: Extractor | None,
        session: Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.cache_dir = cache_dir
        self.extractor = extractor
        self.session = session
        self.sleep = sleep
        self.ai_calls = 0

    def __call__(self, path: Path, content_type: str) -> Reading:
        checksum = sha256(path.read_bytes())
        cache_file = self.cache_dir / f"{checksum}-{PROMPT_VERSION}.json"
        if cache_file.exists():
            return _reading_from_json(cache_file, "file cache")

        if self.session is not None:
            cached = find_cached_extraction(self.session, checksum)
            if cached is not None:
                reading = Reading(
                    DocumentExtraction.model_validate(cached.data),
                    "database cache",
                    cached.model,
                    cached.input_tokens,
                    cached.output_tokens,
                    cached.duration_ms,
                )
                _save(cache_file, reading)
                return reading

        if self.extractor is None:
            raise LookupError("Not read before, and AI calls are turned off.")
        prepared = prepare_document(path, content_type, settings.max_pages)
        result = self._extract_with_retries(prepared)
        reading = Reading(
            result.data,
            "ai",
            result.model,
            result.input_tokens,
            result.output_tokens,
            result.duration_ms,
        )
        _save(cache_file, reading)
        return reading

    def _extract_with_retries(self, prepared: PreparedDocument) -> ExtractionResult:
        attempt = 1
        while True:
            self.ai_calls += 1
            try:
                return self.extractor.extract(prepared)
            except PermanentExtractionError:
                raise
            except Exception as error:  # busy, network, odd answer: try again later
                if attempt >= RETRIES:
                    raise
                print(f"    {error} Trying again in {RETRY_SECONDS} s.")
                self.sleep(RETRY_SECONDS)
                attempt += 1


def evaluate(
    root: Path,
    sets: list[ExpectedSet],
    read: Reader,
    locate: bool = True,
    progress: Callable[[str], None] = print,
) -> list[SetResult]:
    """Read every document of every set, then run the 3-way match per set."""
    results = []
    next_id = FIRST_DOCUMENT_ID
    for expected_set in sets:
        documents = []
        for expected in expected_set.documents:
            progress(f"  {expected_set.set_id}  {expected.path.name}")
            documents.append(read_document(expected, read, next_id, locate))
            next_id += 1
        findings = match_set(root, expected_set, documents)
        results.append(
            SetResult(
                expected=expected_set,
                documents=documents,
                found_codes=sorted({finding.code.value for finding in findings}),
                messages=[finding.message for finding in findings],
            )
        )
    return results


def read_document(
    expected: ExpectedDocument, read: Reader, document_id: int, locate: bool
) -> DocumentResult:
    result = DocumentResult(expected)
    content_type = detect_file_type(expected.path.read_bytes()) or "application/pdf"
    try:
        reading = read(expected.path, content_type)
    except Exception as error:
        result.error = str(error) or type(error).__name__
        return result

    document = Document(
        id=document_id,
        filename=expected.path.name,
        content_type=content_type,
        size_bytes=0,
        checksum="",
        storage_key="",
    )
    apply_extraction(document, reading.data)
    result.document = document
    result.reading = reading

    if locate:
        started = time.monotonic()
        lines = read_page_lines(expected.path, content_type, settings.max_pages)
        result.words_seconds = time.monotonic() - started
        result.evidence = find_evidence(document, lines)
    return result


def match_set(
    root: Path, expected_set: ExpectedSet, documents: list[DocumentResult]
) -> list[Finding]:
    """Run the rules as the app would: documents are linked by the PO number the AI
    read, so a misread type or number breaks the link, just like in the app."""
    read_as = {
        result.document.doc_type.value: result.document
        for result in documents
        if result.document is not None
    }
    invoice = read_as.get("invoice")
    if invoice is None:
        return []
    order = read_as.get("purchase_order")
    receipt = read_as.get("goods_receipt")
    if order is not None and not _same_number(
        order.document_number, invoice.po_reference
    ):
        order = None
    if receipt is not None and not _same_number(
        receipt.po_reference, invoice.po_reference
    ):
        receipt = None
    return check_invoice(
        to_rules_data(invoice),
        to_rules_data(order) if order else None,
        [to_rules_data(receipt)] if receipt else [],
        earlier_invoices(root, expected_set.set_id),
    )


def _same_number(first: str | None, second: str | None) -> bool:
    return bool(first and second) and first.strip().upper() == second.strip().upper()


def _save(cache_file: Path, reading: Reading) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    content = {
        "data": reading.data.model_dump(mode="json"),
        "model": reading.model,
        "input_tokens": reading.input_tokens,
        "output_tokens": reading.output_tokens,
        "duration_ms": reading.duration_ms,
    }
    cache_file.write_text(json.dumps(content, indent=2), encoding="utf-8")


def _reading_from_json(cache_file: Path, source: str) -> Reading:
    content = json.loads(cache_file.read_text(encoding="utf-8"))
    return Reading(
        DocumentExtraction.model_validate(content["data"]),
        source,
        content["model"],
        content["input_tokens"],
        content["output_tokens"],
        content["duration_ms"],
    )
