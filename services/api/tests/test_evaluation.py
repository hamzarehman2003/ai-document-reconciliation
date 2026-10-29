"""The evaluation itself, on a generated set with a fake reader (no AI calls)."""

import json
import random
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from faker import Faker

from app.evaluation.report import render
from app.evaluation.runner import CachedReader, Reading, evaluate
from app.evaluation.scoring import percentile, same, summarize
from app.evaluation.truth import load_sets
from app.llm.base import ExtractionResult, PreparedDocument
from app.llm.schema import DocumentExtraction, ExtractedLineItem
from scripts.generate_dataset.__main__ import write_set
from scripts.generate_dataset.models import Scenario
from scripts.generate_dataset.scenarios import build_document_set
from scripts.generate_dataset.vendors import (
    build_buyer,
    build_receiving_staff,
    build_vendors,
)


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    """One clean generated set (digital PDFs) with its answer key."""
    fake = Faker("en_GB")
    fake.seed_instance(3)
    document_set = build_document_set(
        1,
        Scenario.CLEAN,
        random.Random(3),
        build_buyer(fake),
        build_vendors(fake),
        build_receiving_staff(fake),
        [],
    )
    entries = write_set(document_set, tmp_path, random.Random(1), 0.0, "test")
    (tmp_path / "manifest.json").write_text(json.dumps(entries), encoding="utf-8")
    return tmp_path


def answer_key(path: Path) -> DocumentExtraction:
    """What a perfect AI would read from this generated file."""
    truth = json.loads((path.parent / "truth.json").read_text(encoding="utf-8"))
    kind = {"PO": "purchase_order", "GRN": "goods_receipt"}.get(
        path.name.split("-")[0], "invoice"
    )
    source = truth[kind]

    def number(value: str | None) -> float | None:
        return None if value is None else float(value)

    lines = [
        ExtractedLineItem(
            sku=line["sku"],
            description=line["description"],
            quantity=line.get("quantity_received", line.get("quantity")),
            quantity_ordered=line.get("quantity_ordered"),
            unit_price=number(line.get("unit_price")),
            line_total=number(line.get("line_total")),
        )
        for line in source["lines"]
    ]
    return DocumentExtraction(
        doc_type=kind,
        document_number=source["number"],
        vendor_name=source["vendor"]["name"],
        buyer_name=source["buyer"]["name"],
        issue_date=source.get("issue_date") or source.get("receipt_date"),
        due_date=source.get("due_date"),
        po_reference=source.get("po_number"),
        currency=source.get("currency"),
        subtotal=number(source.get("subtotal")),
        tax=number(source.get("tax")),
        total=number(source.get("total")),
        line_items=lines,
    )


def perfect_reader(path: Path, content_type: str) -> Reading:
    return Reading(answer_key(path), "ai", "fake-model", 1000, 200, 1500)


def test_a_perfect_reader_scores_100_percent(dataset: Path) -> None:
    sets = load_sets(dataset, "test")

    summary = summarize(
        evaluate(dataset, sets, perfect_reader, progress=lambda _: None)
    )

    assert summary.documents == 3
    assert summary.classification.rate == 1
    assert all(tally.rate == 1 for tally in summary.fields.values())
    assert summary.lines_found.rate == 1
    assert all(tally.rate == 1 for tally in summary.line_values.values())
    assert summary.evidence_digital.rate == 1  # every value found on the page
    assert summary.sets_exact.rate == 1  # clean set: no problems found
    assert summary.mistakes == []


def test_one_misread_total_is_reported_exactly(dataset: Path) -> None:
    def misreads_total(path: Path, content_type: str) -> Reading:
        reading = perfect_reader(path, content_type)
        if reading.data.doc_type == "invoice":
            wrong = reading.data.model_copy(update={"total": reading.data.total + 1})
            return Reading(wrong, "ai", "fake-model")
        return reading

    sets = load_sets(dataset, "test")
    summary = summarize(
        evaluate(dataset, sets, misreads_total, progress=lambda _: None)
    )

    [mistake] = summary.mistakes
    assert (mistake.doc_type, mistake.field) == ("invoice", "total")
    # The rules then see subtotal + tax ≠ total: a false alarm on a clean set.
    assert summary.sets_exact.rate == 0
    assert summary.codes["TOTAL_MISMATCH"].wrong == 1


def test_a_document_that_cannot_be_read_is_reported(dataset: Path) -> None:
    def broken(path: Path, content_type: str) -> Reading:
        raise LookupError("Not read before, and AI calls are turned off.")

    summary = summarize(
        evaluate(dataset, load_sets(dataset, "test"), broken, False, lambda _: None)
    )

    assert len(summary.failed) == 3
    assert "AI calls are turned off" in summary.failed[0][1]


def test_cached_reader_reuses_answers_and_retries(
    dataset: Path, tmp_path: Path
) -> None:
    pdf = next((dataset / "sets").glob("*/PO-*.pdf"))

    class FlakyExtractor:
        calls = 0

        def extract(self, document: PreparedDocument) -> ExtractionResult:
            self.calls += 1
            if self.calls < 3:
                raise RuntimeError("Gemini is temporarily unavailable (503).")
            return ExtractionResult(answer_key(pdf), "fake-model", 10, 5, 100)

    extractor = FlakyExtractor()
    reader = CachedReader(tmp_path / "cache", extractor, sleep=lambda _: None)

    first = reader(pdf, "application/pdf")
    second = reader(pdf, "application/pdf")

    assert first.source == "ai"
    assert second.source == "file cache"
    assert second.data == first.data
    assert extractor.calls == 3  # two retries, then the cached answer is reused


def test_comparison_rules() -> None:
    assert same("Apex  Office Supplies", "apex office supplies")
    assert same(Decimal("40.00"), Decimal("40"))
    assert not same(Decimal("40.00"), Decimal("40.01"))
    assert same(date(2026, 3, 2), date(2026, 3, 2))
    assert same(None, None)
    assert not same(None, "PO-1")  # an invented value is wrong
    assert not same("PO-1", None)
    assert percentile([5, 1, 3, 2, 4], 0.95) == 5
    assert percentile([], 0.5) is None


def test_report_has_every_section(dataset: Path) -> None:
    summary = summarize(
        evaluate(
            dataset, load_sets(dataset, "test"), perfect_reader, progress=lambda _: None
        )
    )

    report = render(summary, "test", date(2026, 10, 29))

    for heading in [
        "# Evaluation report",
        "## Summary",
        "## Document type",
        "## Header fields",
        "## Line items",
        "## Evidence",
        "## 3-way match",
        "## Speed and usage",
        "## Every mistake",
        "## Limits of this test",
    ]:
        assert heading in report
    assert "100.0%" in report
