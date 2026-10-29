"""Compare what was read with the answer keys and add everything up.

Pure functions: results in, numbers out. Text is compared ignoring case and
extra spaces; dates and amounts must be exactly equal.
"""

import math
import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.evaluation.runner import DocumentResult, SetResult
from app.evaluation.truth import LINE_FIELDS_BY_TYPE, Value
from app.services.evidence import DATE_FIELDS, HEADER_TEXT_FIELDS, TOTAL_FIELDS

EMPTY = "—"
SEARCHED_FIELDS = {*HEADER_TEXT_FIELDS, *DATE_FIELDS, *TOTAL_FIELDS}


@dataclass
class Tally:
    """How many checks were right out of how many."""

    ok: int = 0
    total: int = 0

    def add(self, ok: bool) -> None:
        self.ok += ok
        self.total += 1

    @property
    def rate(self) -> float | None:
        return self.ok / self.total if self.total else None


@dataclass(frozen=True)
class Check:
    """One value compared with its answer."""

    set_id: str
    file: str
    doc_type: str
    scanned: bool
    field: str
    expected: str
    got: str
    ok: bool


@dataclass
class CodeCounts:
    found: int = 0  # expected and raised
    missed: int = 0  # expected but not raised (the dangerous one)
    wrong: int = 0  # raised but not expected (a false alarm)


@dataclass
class Summary:
    sets: int = 0
    documents: int = 0
    scanned_documents: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)  # (file, error)
    sources: Counter = field(default_factory=Counter)  # "ai", caches
    models: Counter = field(default_factory=Counter)
    classification: Tally = field(default_factory=Tally)
    confusion: Counter = field(default_factory=Counter)  # (expected, read) → count
    fields: dict[str, Tally] = field(default_factory=dict)
    fields_digital: Tally = field(default_factory=Tally)
    fields_scanned: Tally = field(default_factory=Tally)
    lines_found: Tally = field(default_factory=Tally)
    line_values: dict[str, Tally] = field(default_factory=dict)
    evidence_digital: Tally = field(default_factory=Tally)
    evidence_scanned: Tally = field(default_factory=Tally)
    sets_exact: Tally = field(default_factory=Tally)
    codes: dict[str, CodeCounts] = field(default_factory=dict)
    ai_seconds: list[float] = field(default_factory=list)
    input_tokens: list[int] = field(default_factory=list)
    output_tokens: list[int] = field(default_factory=list)
    scan_word_seconds: list[float] = field(default_factory=list)
    mistakes: list[Check] = field(default_factory=list)
    match_mistakes: list[tuple[str, list[str], list[str]]] = field(default_factory=list)


def summarize(results: list[SetResult]) -> Summary:
    summary = Summary(sets=len(results))
    for set_result in results:
        for document in set_result.documents:
            add_document(summary, document)
        add_match(summary, set_result)
    return summary


def add_document(summary: Summary, result: DocumentResult) -> None:
    expected = result.expected
    summary.documents += 1
    summary.scanned_documents += expected.scanned
    if result.document is None or result.reading is None:
        summary.failed.append((expected.path.name, result.error or "not read"))
        return

    reading = result.reading
    summary.sources[reading.source] += 1
    summary.models[reading.model] += 1
    if reading.duration_ms is not None:
        summary.ai_seconds.append(reading.duration_ms / 1000)
    if reading.input_tokens is not None:
        summary.input_tokens.append(reading.input_tokens)
    if reading.output_tokens is not None:
        summary.output_tokens.append(reading.output_tokens)
    if expected.scanned and result.words_seconds is not None:
        summary.scan_word_seconds.append(result.words_seconds)

    read_type = result.document.doc_type.value
    summary.classification.add(read_type == expected.doc_type)
    summary.confusion[(expected.doc_type, read_type)] += 1

    for check in field_checks(result):
        summary.fields.setdefault(check.field, Tally()).add(check.ok)
        (summary.fields_scanned if expected.scanned else summary.fields_digital).add(
            check.ok
        )
        if not check.ok:
            summary.mistakes.append(check)

    found, line_value_checks = line_checks(result)
    for ok in found:
        summary.lines_found.add(ok)
    for attribute, check in line_value_checks:
        summary.line_values.setdefault(attribute, Tally()).add(check.ok)
        if not check.ok:
            summary.mistakes.append(check)

    located = located_values(result)
    evidence = (
        summary.evidence_scanned if expected.scanned else summary.evidence_digital
    )
    for ok in located:
        evidence.add(ok)


def add_match(summary: Summary, result: SetResult) -> None:
    expected = set(result.expected.expected_codes)
    found = set(result.found_codes)
    summary.sets_exact.add(expected == found)
    if expected != found:
        summary.match_mistakes.append(
            (result.expected.set_id, sorted(expected), sorted(found))
        )
    for code in expected | found:
        counts = summary.codes.setdefault(code, CodeCounts())
        if code in expected and code in found:
            counts.found += 1
        elif code in expected:
            counts.missed += 1
        else:
            counts.wrong += 1


def field_checks(result: DocumentResult) -> list[Check]:
    expected = result.expected
    return [
        _check(result, name, value, getattr(result.document, name))
        for name, value in expected.fields.items()
    ]


def line_checks(result: DocumentResult) -> tuple[list[bool], list[tuple[str, Check]]]:
    """Lines are matched by SKU. Returns (found per expected line, value checks)."""
    expected = result.expected
    read_lines = {
        _text(item.sku): item for item in result.document.line_items if item.sku
    }
    found = []
    checks = []
    for sku, values in expected.lines.items():
        item = read_lines.get(_text(sku))
        found.append(item is not None)
        for attribute in LINE_FIELDS_BY_TYPE[expected.doc_type]:
            got = getattr(item, attribute) if item is not None else None
            check = _check(result, f"line {sku}: {attribute}", values[attribute], got)
            checks.append((attribute, check))
    return found, checks


def located_values(result: DocumentResult) -> list[bool]:
    """For every value the AI read that the app looks for: was it found on the page?

    The currency is not looked for (it's printed as a symbol like £), so it
    isn't counted.
    """
    located = {evidence.field for evidence in result.evidence}
    document = result.document
    checks = [
        name in located
        for name in result.expected.fields
        if name in SEARCHED_FIELDS and getattr(document, name) is not None
    ]
    for item in document.line_items:
        for attribute in LINE_FIELDS_BY_TYPE[result.expected.doc_type]:
            if getattr(item, attribute) is not None:
                checks.append(f"line_items.{item.position}.{attribute}" in located)
    return checks


def same(expected: Value, got: Value) -> bool:
    """Equal answers: text ignoring case and spaces; dates and amounts exactly."""
    if expected is None or got is None:
        return expected is None and got in (None, "")
    if isinstance(expected, str):
        return _text(expected) == _text(str(got))
    if isinstance(expected, Decimal):
        return isinstance(got, Decimal) and expected == got
    if isinstance(expected, date):
        return isinstance(got, date) and expected == got
    return expected == got


def percentile(values: list[float], share: float) -> float | None:
    """Nearest-rank percentile: share=0.95 → 95% of the values are at or below it."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(share * len(ordered)) - 1)]


def median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def show(value: Value) -> str:
    if value is None or value == "":
        return EMPTY
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _check(result: DocumentResult, name: str, expected: Value, got: Value) -> Check:
    return Check(
        set_id=result.expected.set_id,
        file=result.expected.path.name,
        doc_type=result.expected.doc_type,
        scanned=result.expected.scanned,
        field=name,
        expected=show(expected),
        got=show(got),
        ok=same(expected, got),
    )


def _text(value: str) -> str:
    return " ".join(value.casefold().split())
