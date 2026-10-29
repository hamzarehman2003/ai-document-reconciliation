"""Find where each extracted value appears on the page.

The same value can be printed in many ways (30706.76 → "€30,706.76" or
"30.706,76 €"; 2026-01-23 → "23/01/2026" or "January 23, 2026"), so we
search for every common way of writing it. A value found nowhere on the
page gets no evidence, which the app shows as a warning.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models import Document, FieldEvidence
from app.services.page_text import TextLine, Word

HEADER_TEXT_FIELDS = ("document_number", "vendor_name", "buyer_name", "po_reference")
DATE_FIELDS = ("issue_date", "due_date")
TOTAL_FIELDS = ("subtotal", "tax", "total")  # printed at the bottom: use the last match
IGNORED_CHARACTERS = str.maketrans("", "", " ,;:#")
EDGE_MARKS = ".'\"`()[]|_*"


@dataclass(frozen=True)
class Match:
    page: int
    words: list[Word]
    source: str

    def to_evidence(self, field: str) -> FieldEvidence:
        scores = [w.confidence for w in self.words if w.confidence is not None]
        return FieldEvidence(
            field=field,
            page=self.page,
            x0=min(w.x0 for w in self.words),
            y0=min(w.y0 for w in self.words),
            x1=max(w.x1 for w in self.words),
            y1=max(w.y1 for w in self.words),
            text=" ".join(w.text for w in self.words)[:300],
            source=self.source,
            confidence=min(scores) if scores else None,
        )


def find_evidence(document: Document, lines: list[TextLine]) -> list[FieldEvidence]:
    """Evidence for every extracted value that can be found on the page."""
    evidence: list[FieldEvidence] = []

    def add(field: str, match: Match | None) -> None:
        if match is not None:
            evidence.append(match.to_evidence(field))

    for field in HEADER_TEXT_FIELDS:
        add(field, first(find_phrase(lines, text_variants(getattr(document, field)))))
    for field in DATE_FIELDS:
        add(field, first(find_phrase(lines, date_variants(getattr(document, field)))))
    for field in TOTAL_FIELDS:
        add(field, last(find_number(lines, amount_variants(getattr(document, field)))))

    for item in document.line_items:
        prefix = f"line_items.{item.position}"
        anchor = first(find_phrase(lines, text_variants(item.sku)))
        add(f"{prefix}.sku", anchor)
        if anchor is None:
            continue  # without the SKU we can't tell which row is this item's
        row = row_of(anchor, lines)
        received = last(find_number(row, quantity_variants(item.quantity)))
        add(f"{prefix}.quantity", received)
        ordered = [
            match
            for match in find_number(row, quantity_variants(item.quantity_ordered))
            if match != received  # same value in two columns: take the other one
        ]
        add(f"{prefix}.quantity_ordered", last(ordered))
        add(
            f"{prefix}.unit_price",
            last(find_number(row, amount_variants(item.unit_price))),
        )
        add(
            f"{prefix}.line_total",
            last(find_number(row, amount_variants(item.line_total))),
        )
    return evidence


# --- Searching ---


def find_phrase(lines: list[TextLine], variants: set[str]) -> list[Match]:
    """Runs of whole words that spell one of the variants (spaces ignored)."""
    if not variants:
        return []
    longest = max(len(variant) for variant in variants)
    matches = []
    for line in lines:
        for start in range(len(line.words)):
            text = ""
            for end in range(start, len(line.words)):
                text += normalize(line.words[end].text)
                if text in variants:
                    matches.append(
                        Match(line.page, line.words[start : end + 1], line.source)
                    )
                    break
                if len(text) >= longest:
                    break
    return matches


def find_number(lines: list[TextLine], variants: set[str]) -> list[Match]:
    """Single words that are one of the number variants ("$1,234.50" → "1,234.50")."""
    if not variants:
        return []
    return [
        Match(line.page, [word], line.source)
        for line in lines
        for word in line.words
        if number_part(word.text) in variants
    ]


def row_of(anchor: Match, lines: list[TextLine]) -> list[TextLine]:
    """All words at the same height as the anchor: the rest of its table row."""
    top = min(w.y0 for w in anchor.words)
    bottom = max(w.y1 for w in anchor.words)
    margin = (bottom - top) * 0.5
    return [
        TextLine(line.page, [word], line.source)
        for line in lines
        if line.page == anchor.page
        for word in line.words
        if top - margin <= (word.y0 + word.y1) / 2 <= bottom + margin
    ]


def first(matches: list[Match]) -> Match | None:
    return matches[0] if matches else None


def last(matches: list[Match]) -> Match | None:
    return matches[-1] if matches else None


# --- Ways a value can be written ---


def normalize(text: str) -> str:
    """Lowercase, no spaces, and no stray marks at the edges (OCR reads specks
    of dust as dots: ".AOS-1002")."""
    return text.casefold().translate(IGNORED_CHARACTERS).strip(EDGE_MARKS)


def number_part(text: str) -> str:
    """Keep only digits and separators: "€30,706.76" → "30,706.76"."""
    return "".join(ch for ch in text if ch.isdigit() or ch in ".,-").strip(".,")


def text_variants(value: str | None) -> set[str]:
    return {normalize(value)} if value and normalize(value) else set()


def date_variants(value: date | None) -> set[str]:
    if value is None:
        return set()
    day, month, year = value.day, value.month, value.year
    written = {
        value.isoformat(),
        f"{day:02}/{month:02}/{year}",
        f"{month:02}/{day:02}/{year}",
        f"{day:02}.{month:02}.{year}",
        f"{day}/{month}/{year}",
        f"{month}/{day}/{year}",
        f"{day:02} {value:%B} {year}",
        f"{day} {value:%B} {year}",
        f"{day:02} {value:%b} {year}",
        f"{day} {value:%b} {year}",
        f"{value:%B} {day:02}, {year}",
        f"{value:%B} {day}, {year}",
        f"{value:%b} {day}, {year}",
    }
    return {normalize(text) for text in written}


def amount_variants(value: Decimal | None) -> set[str]:
    """1234.5 → {"1234.50", "1,234.50", "1234,50", "1.234,50"}"""
    if value is None:
        return set()
    us = f"{value:,.2f}"
    eu = us.replace(",", " ").replace(".", ",").replace(" ", ".")
    return {us, us.replace(",", ""), eu, eu.replace(".", "")}


def quantity_variants(value: Decimal | None) -> set[str]:
    """Decimal("16.250") → {"16.25", "16,25"}; Decimal("10.000") → {"10"}"""
    if value is None:
        return set()
    text = format(value.normalize(), "f")
    return {text, text.replace(".", ",")}
