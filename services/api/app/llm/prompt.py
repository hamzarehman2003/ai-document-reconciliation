"""The instruction sent to the AI with every document.

Change PROMPT_VERSION whenever the instruction or schema changes: cached
results made with an older version are then ignored and extracted again.
"""

PROMPT_VERSION = "v1"
MAX_TEXT_CHARS = 15_000

INSTRUCTIONS = """\
You read business documents: invoices, purchase orders and goods receipt notes.
Fill in every field of the JSON schema from the document.

Rules:
- Copy names, document numbers and item codes exactly as printed.
- Dates: write them as YYYY-MM-DD. If a date such as 03/11/2026 is ambiguous,
  use the other dates on the page to decide (a due date is usually 30 days
  after the invoice date).
- Amounts and quantities: plain numbers, with a dot for decimals and no
  currency symbols or thousands separators. "1.234,50 €" -> 1234.50,
  "$1,234.50" -> 1234.50.
- Currency: the 3-letter ISO code (USD, EUR, GBP, ...).
- If a value is not on the document, use null. Never guess and never
  calculate a value that is not printed.
"""


def build_prompt(text_layer: str) -> str:
    """The instruction, plus the PDF's own text when it has one."""
    if not text_layer.strip():
        return INSTRUCTIONS + "\nThis is a scanned document: read it from the image."
    return (
        INSTRUCTIONS
        + "\nText found in the PDF (reading order may be wrong; the image is the "
        + "source of truth):\n"
        + text_layer[:MAX_TEXT_CHARS]
    )
