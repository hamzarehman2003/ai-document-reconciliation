"""People correcting values the AI misread.

Every correction is stored, and corrections are put back after any new AI
read of the document, so a human fix is never lost to reprocessing.
"""

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum

from sqlalchemy.orm import Session

from app.models import AuditAction, AuditObject, Document, FieldCorrection, LineItem
from app.services.audit import record

CENT = Decimal("0.01")
THOUSANDTH = Decimal("0.001")


class Kind(StrEnum):
    TEXT = "text"
    MONEY = "money"
    QUANTITY = "quantity"
    DATE = "date"
    CURRENCY = "currency"


HEADER_FIELDS: dict[str, Kind] = {
    "document_number": Kind.TEXT,
    "vendor_name": Kind.TEXT,
    "buyer_name": Kind.TEXT,
    "po_reference": Kind.TEXT,
    "issue_date": Kind.DATE,
    "due_date": Kind.DATE,
    "currency": Kind.CURRENCY,
    "subtotal": Kind.MONEY,
    "tax": Kind.MONEY,
    "total": Kind.MONEY,
}
LINE_FIELDS: dict[str, Kind] = {
    "sku": Kind.TEXT,
    "description": Kind.TEXT,
    "quantity": Kind.QUANTITY,
    "quantity_ordered": Kind.QUANTITY,
    "unit_price": Kind.MONEY,
    "line_total": Kind.MONEY,
}
LINE_FIELD_PATTERN = re.compile(r"line_items\.(\d+)\.(\w+)")
MAX_TEXT = 200

FieldValue = str | Decimal | date | None


class CorrectionError(ValueError):
    """The field or value is not valid; the message is shown to the user."""


def correct_field(
    session: Session,
    document: Document,
    field: str,
    raw_value: str | None,
    reviewer: str,
    note: str | None = None,
) -> FieldCorrection:
    """Set a new value, remember the old one, and log it. Does not commit."""
    target, attribute, kind = resolve(document, field)
    new_value = parse_value(kind, raw_value)
    if attribute == "description" and new_value is None:
        new_value = ""  # a line item always has a description
    old_value = getattr(target, attribute)
    setattr(target, attribute, new_value)

    correction = FieldCorrection(
        document=document,
        field=field,
        old_value=as_text(old_value),
        new_value=as_text(new_value),
        corrected_by=reviewer,
        note=note,
    )
    session.add(correction)
    record(
        session,
        reviewer,
        AuditAction.FIELD_CORRECTED,
        AuditObject.DOCUMENT,
        document.id,
        {"field": field, "old": as_text(old_value), "new": as_text(new_value)},
    )
    return correction


def reapply_corrections(document: Document) -> None:
    """After a new AI read, put the people's fixes back (the latest per field wins)."""
    latest = {correction.field: correction for correction in document.corrections}
    for field, correction in latest.items():
        try:
            target, attribute, kind = resolve(document, field)
        except CorrectionError:
            continue  # e.g. that line item no longer exists in the new read
        value = parse_value(kind, correction.new_value)
        setattr(
            target,
            attribute,
            "" if attribute == "description" and value is None else value,
        )


def resolve(document: Document, field: str) -> tuple[Document | LineItem, str, Kind]:
    """Which object and attribute a field name points to, and its kind of value."""
    if field in HEADER_FIELDS:
        return document, field, HEADER_FIELDS[field]
    match = LINE_FIELD_PATTERN.fullmatch(field)
    if match is None or match.group(2) not in LINE_FIELDS:
        raise CorrectionError(f"'{field}' can't be corrected.")
    position, attribute = int(match.group(1)), match.group(2)
    for item in document.line_items:
        if item.position == position:
            return item, attribute, LINE_FIELDS[attribute]
    raise CorrectionError(f"The document has no line item {position}.")


def parse_value(kind: Kind, raw: str | None) -> FieldValue:
    """Check and convert typed text. Empty means "not on the document"."""
    text = (raw or "").strip()
    if not text:
        return None
    match kind:
        case Kind.MONEY:
            return _decimal(text, CENT, "Enter an amount like 1234.50.")
        case Kind.QUANTITY:
            value = _decimal(text, THOUSANDTH, "Enter a quantity like 10 or 2.5.")
            if value < 0:
                raise CorrectionError("A quantity can't be negative.")
            return value
        case Kind.DATE:
            try:
                return date.fromisoformat(text)
            except ValueError:
                raise CorrectionError("Enter a date as YYYY-MM-DD.") from None
        case Kind.CURRENCY:
            if len(text) != 3 or not text.isalpha():
                raise CorrectionError("Enter a 3-letter currency code like EUR.")
            return text.upper()
        case Kind.TEXT:
            return text[:MAX_TEXT]


def as_text(value: FieldValue) -> str | None:
    """How a value is stored in a correction: "1333.26", "2026-01-23", ..."""
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _decimal(text: str, step: Decimal, message: str) -> Decimal:
    try:
        return Decimal(text.replace(",", "")).quantize(step, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise CorrectionError(message) from None
