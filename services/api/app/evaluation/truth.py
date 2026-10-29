"""Read the answer keys written by the dataset generator (manifest.json, truth.json)."""

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.rules import DocumentData

Value = str | Decimal | date | None

# Which fields each kind of document has (the rest are not on that document).
FIELDS_BY_TYPE = {
    "invoice": [
        "document_number",
        "vendor_name",
        "buyer_name",
        "issue_date",
        "due_date",
        "po_reference",
        "currency",
        "subtotal",
        "tax",
        "total",
    ],
    "purchase_order": [
        "document_number",
        "vendor_name",
        "buyer_name",
        "issue_date",
        "currency",
        "subtotal",
        "tax",
        "total",
    ],
    "goods_receipt": [
        "document_number",
        "vendor_name",
        "buyer_name",
        "issue_date",
        "po_reference",
    ],
}
LINE_FIELDS_BY_TYPE = {
    "invoice": ["quantity", "unit_price", "line_total"],
    "purchase_order": ["quantity", "unit_price", "line_total"],
    "goods_receipt": ["quantity", "quantity_ordered"],
}


@dataclass(frozen=True)
class ExpectedDocument:
    set_id: str
    path: Path
    doc_type: str  # "invoice", "purchase_order" or "goods_receipt"
    scanned: bool
    fields: dict[str, Value]
    lines: dict[str, dict[str, Value]]  # SKU → {"quantity": ..., ...}


@dataclass(frozen=True)
class ExpectedSet:
    set_id: str
    scenario: str
    expected_codes: list[str]
    documents: list[ExpectedDocument] = field(default_factory=list)


def load_sets(root: Path, split: str) -> list[ExpectedSet]:
    """The sets in a split ("test", "train" or "all"), in set order."""
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    by_set: dict[str, list[dict[str, Any]]] = {}
    for entry in manifest:
        if split == "all" or entry["split"] == split:
            by_set.setdefault(entry["set_id"], []).append(entry)

    sets = []
    for set_id in sorted(by_set):
        truth = load_truth(root, set_id)
        documents = [expected_document(root, entry, truth) for entry in by_set[set_id]]
        sets.append(
            ExpectedSet(
                set_id=set_id,
                scenario=truth["scenario"],
                expected_codes=sorted(truth["expected_codes"]),
                documents=documents,
            )
        )
    return sets


def earlier_invoices(root: Path, set_id: str) -> list[DocumentData]:
    """The answer-key invoices of every earlier set (for the duplicate check)."""
    number = set_number(set_id)
    invoices = []
    for path in sorted((root / "sets").glob("SET-*/truth.json")):
        earlier_id = path.parent.name
        if set_number(earlier_id) >= number:
            continue
        invoice = json.loads(path.read_text(encoding="utf-8"))["invoice"]
        invoices.append(
            DocumentData(
                document_id=set_number(earlier_id),
                number=invoice["number"],
                vendor_name=invoice["vendor"]["name"],
                po_reference=invoice["po_number"],
            )
        )
    return invoices


def expected_document(
    root: Path, entry: dict[str, Any], truth: dict[str, Any]
) -> ExpectedDocument:
    doc_type = entry["doc_type"]
    source = truth[doc_type]
    values: dict[str, Value] = {
        "document_number": source["number"],
        "vendor_name": source["vendor"]["name"],
        "buyer_name": source["buyer"]["name"],
        "issue_date": day(source.get("issue_date") or source.get("receipt_date")),
        "due_date": day(source.get("due_date")),
        "po_reference": source.get("po_number"),
        "currency": source.get("currency"),
        "subtotal": money(source.get("subtotal")),
        "tax": money(source.get("tax")),
        "total": money(source.get("total")),
    }
    if doc_type == "goods_receipt":
        lines = {
            line["sku"]: {
                "quantity": money(line["quantity_received"]),
                "quantity_ordered": money(line["quantity_ordered"]),
            }
            for line in source["lines"]
        }
    else:
        lines = {
            line["sku"]: {
                "quantity": money(line["quantity"]),
                "unit_price": money(line["unit_price"]),
                "line_total": money(line["line_total"]),
            }
            for line in source["lines"]
        }
    return ExpectedDocument(
        set_id=entry["set_id"],
        path=root / entry["file"],
        doc_type=doc_type,
        scanned=entry["scanned"],
        fields={name: values[name] for name in FIELDS_BY_TYPE[doc_type]},
        lines=lines,
    )


def load_truth(root: Path, set_id: str) -> dict[str, Any]:
    return json.loads(
        (root / "sets" / set_id / "truth.json").read_text(encoding="utf-8")
    )


def set_number(set_id: str) -> int:
    return int(set_id.removeprefix("SET-"))


def money(value: str | int | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def day(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None
