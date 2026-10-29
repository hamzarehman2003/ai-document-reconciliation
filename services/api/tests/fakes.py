"""Test stand-ins for outside services (no network, no quota, known answers)."""

from app.llm.base import ExtractionResult, PreparedDocument
from app.llm.schema import DocumentExtraction, ExtractedLineItem


def sample_extraction() -> DocumentExtraction:
    """What a correct AI answer for a small invoice looks like."""
    return DocumentExtraction(
        doc_type="invoice",
        document_number="AOS-68878",
        vendor_name="Apex Office Supplies",
        buyer_name="Brightline Retail Ltd",
        issue_date="2026-01-12",
        due_date="2026-02-11",
        po_reference="PO-2026-0001",
        currency="usd",
        subtotal=1234.5,
        tax=98.76,
        total=1333.26,
        line_items=[
            ExtractedLineItem(
                sku="AOS-1001",
                description="A4 copy paper, 80gsm (box of 5 reams)",
                quantity=5,
                quantity_ordered=None,
                unit_price=24.5,
                line_total=122.5,
            ),
            ExtractedLineItem(
                sku="AOS-1008",
                description="Printer toner, black XL",
                quantity=16.25,
                quantity_ordered=None,
                unit_price=68,
                line_total=1105,
            ),
        ],
    )


class FakeExtractor:
    """Stands in for Gemini. Set `error` to make it fail."""

    def __init__(self) -> None:
        self.calls = 0
        self.data = sample_extraction()
        self.error: Exception | None = None

    def extract(self, document: PreparedDocument) -> ExtractionResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return ExtractionResult(
            data=self.data,
            model="fake-model",
            input_tokens=1000,
            output_tokens=200,
            duration_ms=5,
        )
