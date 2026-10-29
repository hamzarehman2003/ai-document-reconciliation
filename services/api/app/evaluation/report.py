"""Write the evaluation as a Markdown report."""

from datetime import date

from app.evaluation.scoring import Summary, Tally, median, percentile
from app.llm.prompt import PROMPT_VERSION

FIELD_LABELS = {
    "document_number": "Document number",
    "vendor_name": "Vendor",
    "buyer_name": "Buyer",
    "issue_date": "Date",
    "due_date": "Due date",
    "po_reference": "PO reference",
    "currency": "Currency",
    "subtotal": "Subtotal",
    "tax": "Tax",
    "total": "Total",
}
LINE_LABELS = {
    "quantity": "Quantity (billed / ordered / received)",
    "quantity_ordered": "Quantity ordered (receipts)",
    "unit_price": "Unit price",
    "line_total": "Line total",
}
TYPES = ["invoice", "purchase_order", "goods_receipt", "unknown"]


def render(summary: Summary, split: str, today: date) -> str:
    model = summary.models.most_common(1)[0][0] if summary.models else "—"
    lines = [
        "# Evaluation report",
        "",
        f"Generated {today.isoformat()} · model `{model}` · "
        f"prompt `{PROMPT_VERSION}` · "
        f"split `{split}`: {summary.sets} sets, {summary.documents} documents "
        f"({summary.scanned_documents} scanned, with no text layer).",
        "",
        "Produced by `python -m app.evaluation` (services/api). "
        "Every number below comes "
        "from that run; the documents are generated, so the right answers are known.",
        "",
        "## Summary",
        "",
        f"- **Document type:** {pct(summary.classification)}",
        f"- **Header fields read exactly right:** {pct(overall(summary.fields))} "
        f"(digital {pct(summary.fields_digital)}, "
        f"scanned {pct(summary.fields_scanned)})",
        f"- **Line items found:** {pct(summary.lines_found)}; "
        f"**line values right:** {pct(overall(summary.line_values))}",
        f"- **Values located on the page:** digital {pct(summary.evidence_digital)}, "
        f"scanned {pct(summary.evidence_scanned)}",
        f"- **3-way match, sets with exactly the expected problems:** "
        f"{pct(summary.sets_exact)}",
        f"- **Documents that could not be read:** {len(summary.failed)}",
        "",
    ]
    lines += _classification(summary)
    lines += _fields(summary)
    lines += _line_items(summary)
    lines += _matching(summary)
    lines += _speed(summary)
    lines += _mistakes(summary)
    lines += _limits()
    return "\n".join(lines) + "\n"


def pct(tally: Tally) -> str:
    if tally.rate is None:
        return "n/a"
    return f"{tally.rate * 100:.1f}% ({tally.ok}/{tally.total})"


def overall(tallies: dict[str, Tally]) -> Tally:
    return Tally(
        ok=sum(t.ok for t in tallies.values()),
        total=sum(t.total for t in tallies.values()),
    )


def _classification(summary: Summary) -> list[str]:
    rows = [
        "## Document type",
        "",
        "Rows: the real type. Columns: what the AI said.",
        "",
        "| Real type | " + " | ".join(TYPES) + " |",
        "|---|" + "---|" * len(TYPES),
    ]
    for real in TYPES[:3]:
        counts = [str(summary.confusion.get((real, read), 0)) for read in TYPES]
        rows.append(f"| {real} | " + " | ".join(counts) + " |")
    return [*rows, ""]


def _fields(summary: Summary) -> list[str]:
    rows = [
        "## Header fields",
        "",
        "Text is compared ignoring case and extra spaces; "
        "dates and amounts must be exact. "
        "An empty answer is right only where the value is really absent.",
        "",
        "| Field | Right |",
        "|---|---|",
    ]
    for name, label in FIELD_LABELS.items():
        if name in summary.fields:
            rows.append(f"| {label} | {pct(summary.fields[name])} |")
    rows += [
        f"| **All fields** | **{pct(overall(summary.fields))}** |",
        "",
        f"Digital documents: {pct(summary.fields_digital)} · "
        f"scanned documents: {pct(summary.fields_scanned)}",
        "",
    ]
    return rows


def _line_items(summary: Summary) -> list[str]:
    rows = [
        "## Line items",
        "",
        f"Lines found (matched by SKU): {pct(summary.lines_found)}",
        "",
        "| Value | Right |",
        "|---|---|",
    ]
    for name, label in LINE_LABELS.items():
        if name in summary.line_values:
            rows.append(f"| {label} | {pct(summary.line_values[name])} |")
    rows += [
        "",
        "## Evidence (where each value is on the page)",
        "",
        "Share of the values the AI read that were found on the page, so the app can "
        "highlight them. Digital pages use the PDF's own words; scans use OCR.",
        "",
        f"- Digital documents: {pct(summary.evidence_digital)}",
        f"- Scanned documents: {pct(summary.evidence_scanned)}",
        "",
    ]
    return rows


def _matching(summary: Summary) -> list[str]:
    rows = [
        "## 3-way match",
        "",
        "The matching rules run on what the AI read. A set is right when the problems "
        "found are exactly the injected ones (none for clean sets).",
        "",
        f"Sets with exactly the expected problems: **{pct(summary.sets_exact)}**",
        "",
        "| Problem | Found | Missed | False alarm |",
        "|---|---|---|---|",
    ]
    for code in sorted(summary.codes):
        counts = summary.codes[code]
        rows.append(f"| `{code}` | {counts.found} | {counts.missed} | {counts.wrong} |")
    if not summary.codes:
        rows.append("| (no problems expected or found) | 0 | 0 | 0 |")
    return [*rows, ""]


def _speed(summary: Summary) -> list[str]:
    def seconds(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.1f} s"

    def average(values: list[int]) -> str:
        return f"{sum(values) / len(values):,.0f}" if values else "n/a"

    sources = ", ".join(
        f"{count} from {name}" for name, count in summary.sources.items()
    )
    return [
        "## Speed and usage",
        "",
        f"- AI reading time per document: "
        f"median {seconds(median(summary.ai_seconds))}, "
        f"95th percentile {seconds(percentile(summary.ai_seconds, 0.95))}",
        f"- Tokens per document: {average(summary.input_tokens)} in, "
        f"{average(summary.output_tokens)} out",
        f"- OCR time per scanned document (CPU): median "
        f"{seconds(median(summary.scan_word_seconds))}",
        f"- Answers used in this run: {sources or 'none'} "
        "(cached answers are reused, so re-running costs no AI quota)",
        "",
    ]


def _mistakes(summary: Summary) -> list[str]:
    rows = ["## Every mistake", ""]
    if not summary.mistakes and not summary.match_mistakes and not summary.failed:
        return [*rows, "None.", ""]
    for file, error in summary.failed:
        rows.append(f"- **{file}**: could not be read ({error})")
    if summary.failed:
        rows.append("")
    if summary.mistakes:
        rows += [
            "| Set | File | Field | Expected | Read |",
            "|---|---|---|---|---|",
        ]
        for check in summary.mistakes:
            rows.append(
                f"| {check.set_id} | {check.file} | {check.field} | "
                f"{check.expected} | {check.got} |"
            )
    for set_id, expected, found in summary.match_mistakes:
        rows.append(
            f"- **{set_id}** 3-way match: "
            f"expected {', '.join(expected) or 'no problems'}, "
            f"found {', '.join(found) or 'no problems'}"
        )
    return [*rows, ""]


def _limits() -> list[str]:
    return [
        "## Limits of this test",
        "",
        "- The documents are generated: realistic layouts, fonts, currencies and noisy "
        "scans, but cleaner than many real-world invoices.",
        "- The sample is small, and this split may not contain every kind of problem "
        "(see the 3-way match table for what was tested).",
        "- Accuracy on a client's own documents should be measured on a sample of them "
        "before relying on these numbers.",
    ]
