"""The exact JSON shape the AI must return. Also used to validate its answer.

Every field is required but may be null, so the model always answers every
field and says "null" when a value is not on the document.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ExtractedLineItem(BaseModel):
    sku: str | None = Field(description="Item code or SKU exactly as printed.")
    description: str = Field(description="Item description exactly as printed.")
    quantity: float | None = Field(
        description=(
            "Invoice: quantity billed. Purchase order: quantity ordered. "
            "Goods receipt: quantity received."
        )
    )
    quantity_ordered: float | None = Field(
        description="Goods receipts only: quantity ordered. Null otherwise."
    )
    unit_price: float | None = Field(description="Price per unit.")
    line_total: float | None = Field(description="Amount for this line.")


class DocumentExtraction(BaseModel):
    doc_type: Literal["invoice", "purchase_order", "goods_receipt", "unknown"]
    document_number: str | None = Field(
        description="This document's own number: invoice, PO or receipt number."
    )
    vendor_name: str | None = Field(description="The supplier (seller) company.")
    buyer_name: str | None = Field(description="The customer (buyer) company.")
    issue_date: str | None = Field(
        description="Invoice date, order date or receipt date, as YYYY-MM-DD."
    )
    due_date: str | None = Field(description="Payment due date, as YYYY-MM-DD.")
    po_reference: str | None = Field(
        description=(
            "The purchase order number this document refers to (on invoices and "
            "goods receipts). Null on the purchase order itself."
        )
    )
    currency: str | None = Field(description="3-letter ISO code, e.g. USD, EUR.")
    subtotal: float | None = Field(description="Total before tax.")
    tax: float | None = Field(description="Tax amount.")
    total: float | None = Field(description="Final total including tax.")
    line_items: list[ExtractedLineItem]
