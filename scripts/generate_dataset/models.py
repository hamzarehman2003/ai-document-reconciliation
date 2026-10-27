"""Data shapes for the generated documents and their answer keys."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Scenario(StrEnum):
    """What, if anything, is wrong with a document set."""

    CLEAN = "CLEAN"
    QTY_EXCEEDS_RECEIVED = "QTY_EXCEEDS_RECEIVED"
    PRICE_MISMATCH = "PRICE_MISMATCH"
    TOTAL_MISMATCH = "TOTAL_MISMATCH"
    LINE_TOTAL_MISMATCH = "LINE_TOTAL_MISMATCH"
    MISSING_PO_REFERENCE = "MISSING_PO_REFERENCE"
    DUPLICATE_INVOICE = "DUPLICATE_INVOICE"
    VENDOR_MISMATCH = "VENDOR_MISMATCH"


class DocType(StrEnum):
    PURCHASE_ORDER = "purchase_order"
    GOODS_RECEIPT = "goods_receipt"
    INVOICE = "invoice"


class LayoutStyle(BaseModel):
    """How a company's documents look. Only used for drawing the PDF."""

    font: Literal["Helvetica", "Times-Roman", "Courier"]
    accent: str
    header_align: Literal["left", "right"]
    date_format: str
    number_label: str
    amount_format: Literal["us", "eu"]


class Company(BaseModel):
    name: str
    address: list[str]
    email: str
    style: LayoutStyle = Field(exclude=True)


class Vendor(Company):
    vendor_id: str
    currency: Literal["USD", "EUR", "GBP"]
    tax_rate: Decimal
    invoice_prefix: str


class CatalogItem(BaseModel):
    sku: str
    description: str
    unit_price: Decimal


class LineItem(BaseModel):
    sku: str
    description: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class ReceiptLine(BaseModel):
    sku: str
    description: str
    quantity_ordered: int
    quantity_received: int


class PurchaseOrder(BaseModel):
    number: str
    issue_date: date
    buyer: Company
    vendor: Vendor
    currency: str
    lines: list[LineItem]
    subtotal: Decimal
    tax_rate: Decimal
    tax: Decimal
    total: Decimal


class GoodsReceipt(BaseModel):
    number: str
    receipt_date: date
    po_number: str
    buyer: Company
    vendor: Vendor
    received_by: str
    lines: list[ReceiptLine]


class Invoice(BaseModel):
    number: str
    issue_date: date
    due_date: date
    po_number: str | None
    buyer: Company
    vendor: Vendor
    currency: str
    lines: list[LineItem]
    subtotal: Decimal
    tax_rate: Decimal
    tax: Decimal
    total: Decimal


class DocumentSet(BaseModel):
    """One purchase: the order, what arrived, and the bill. Also the answer key."""

    set_id: str
    scenario: Scenario
    expected_codes: list[Scenario]
    note: str
    purchase_order: PurchaseOrder
    goods_receipt: GoodsReceipt
    invoice: Invoice
