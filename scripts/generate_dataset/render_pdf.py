"""Draw purchase orders, goods receipts and invoices as PDFs with ReportLab.

Invoices use the vendor's style. Purchase orders and goods receipts are the
buyer's own documents, so they use the buyer's style.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from scripts.generate_dataset.models import (
    Company,
    GoodsReceipt,
    Invoice,
    LayoutStyle,
    PurchaseOrder,
)

MARGIN = 20 * mm
CONTENT_WIDTH = A4[0] - 2 * MARGIN
BOLD_FONTS = {
    "Helvetica": "Helvetica-Bold",
    "Times-Roman": "Times-Bold",
    "Courier": "Courier-Bold",
}
CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£"}
ROW_SHADE = colors.HexColor("#f4f4f5")
GRID = colors.HexColor("#d4d4d8")


def format_amount(amount: Decimal, currency: str, style: LayoutStyle) -> str:
    """Format money as "$1,234.50" (us) or "1.234,50 €" (eu)."""
    symbol = CURRENCY_SYMBOLS[currency]
    text = f"{amount:,.2f}"
    if style.amount_format == "eu":
        text = text.replace(",", " ").replace(".", ",").replace(" ", ".")
        return f"{text} {symbol}"
    return f"{symbol}{text}"


def format_date(value: date, style: LayoutStyle) -> str:
    return value.strftime(style.date_format)


def render_invoice(invoice: Invoice, path: Path) -> None:
    style = invoice.vendor.style
    details = [
        (style.number_label, invoice.number),
        ("Invoice date", format_date(invoice.issue_date, style)),
        ("Due date", format_date(invoice.due_date, style)),
    ]
    if invoice.po_number:
        details.append(("PO reference", invoice.po_number))

    rows = [
        [
            line.sku,
            line.description,
            str(line.quantity),
            format_amount(line.unit_price, invoice.currency, style),
            format_amount(line.line_total, invoice.currency, style),
        ]
        for line in invoice.lines
    ]
    tax_label = f"Tax ({invoice.tax_rate * 100:.0f}%)"
    totals = [
        ("Subtotal", format_amount(invoice.subtotal, invoice.currency, style)),
        (tax_label, format_amount(invoice.tax, invoice.currency, style)),
        ("Total due", format_amount(invoice.total, invoice.currency, style)),
    ]
    story = [
        _header(invoice.vendor, "INVOICE", details, style),
        _party_block("Bill to", invoice.buyer, style),
        _items_table(
            ["SKU", "Description", "Qty", "Unit price", "Amount"], rows, style
        ),
        _totals_table(totals, style),
        _note(
            f"Payment due within 30 days. Please quote {escape(invoice.number)} "
            "with your payment.",
            style,
        ),
    ]
    _build_pdf(path, f"Invoice {invoice.number}", invoice.vendor.name, story)


def render_purchase_order(order: PurchaseOrder, path: Path) -> None:
    style = order.buyer.style
    details = [
        (style.number_label, order.number),
        ("Order date", format_date(order.issue_date, style)),
        ("Currency", order.currency),
    ]
    rows = [
        [
            line.sku,
            line.description,
            str(line.quantity),
            format_amount(line.unit_price, order.currency, style),
            format_amount(line.line_total, order.currency, style),
        ]
        for line in order.lines
    ]
    totals = [
        ("Subtotal", format_amount(order.subtotal, order.currency, style)),
        (
            f"Tax ({order.tax_rate * 100:.0f}%)",
            format_amount(order.tax, order.currency, style),
        ),
        ("Order total", format_amount(order.total, order.currency, style)),
    ]
    story = [
        _header(order.buyer, "PURCHASE ORDER", details, style),
        _party_block("Supplier", order.vendor, style),
        _items_table(
            ["SKU", "Description", "Qty", "Unit price", "Amount"], rows, style
        ),
        _totals_table(totals, style),
        _note("Please quote this PO number on your invoice.", style),
    ]
    _build_pdf(path, f"Purchase order {order.number}", order.buyer.name, story)


def render_goods_receipt(receipt: GoodsReceipt, path: Path) -> None:
    style = receipt.buyer.style
    details = [
        ("GRN Number", receipt.number),
        ("Received on", format_date(receipt.receipt_date, style)),
        ("PO Number", receipt.po_number),
    ]
    rows = [
        [
            line.sku,
            line.description,
            str(line.quantity_ordered),
            str(line.quantity_received),
        ]
        for line in receipt.lines
    ]
    story = [
        _header(receipt.buyer, "GOODS RECEIPT NOTE", details, style),
        _party_block("Supplier", receipt.vendor, style),
        _items_table(["SKU", "Description", "Ordered", "Received"], rows, style),
        _note(
            f"Received and checked by: {escape(receipt.received_by)}"
            "<br/><br/>Signature: ______________________",
            style,
        ),
    ]
    _build_pdf(path, f"Goods receipt {receipt.number}", receipt.buyer.name, story)


def _text_style(
    style: LayoutStyle, size: float = 9, bold: bool = False, **extra: object
) -> ParagraphStyle:
    font = BOLD_FONTS[style.font] if bold else style.font
    return ParagraphStyle(
        "text", fontName=font, fontSize=size, leading=size * 1.35, **extra
    )


def _header(
    company: Company,
    title: str,
    details: list[tuple[str, str]],
    style: LayoutStyle,
) -> Table:
    accent = colors.HexColor(style.accent)
    company_lines = [
        Paragraph(escape(company.name), _text_style(style, 14, True, textColor=accent)),
        *[Paragraph(escape(line), _text_style(style)) for line in company.address],
        Paragraph(escape(company.email), _text_style(style)),
    ]
    detail_rows = [
        [
            Paragraph(escape(label), _text_style(style, bold=True)),
            Paragraph(escape(value), _text_style(style)),
        ]
        for label, value in details
    ]
    detail_table = Table(detail_rows, colWidths=[32 * mm, 38 * mm])
    detail_table.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    title_block = [
        Paragraph(escape(title), _text_style(style, 18, True, textColor=accent)),
        Spacer(1, 3 * mm),
        detail_table,
    ]

    cells = [company_lines, title_block]
    if style.header_align == "right":
        cells.reverse()
    header = Table([cells], colWidths=[CONTENT_WIDTH / 2] * 2)
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 0), (-1, 0), 1.5, accent),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6 * mm),
            ]
        )
    )
    return header


def _party_block(label: str, company: Company, style: LayoutStyle) -> Table:
    lines = [
        Paragraph(escape(label.upper()), _text_style(style, 8, True)),
        Paragraph(escape(company.name), _text_style(style, 10, True)),
        *[Paragraph(escape(line), _text_style(style)) for line in company.address],
    ]
    block = Table([[lines]], colWidths=[CONTENT_WIDTH])
    block.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm),
            ]
        )
    )
    return block


def _items_table(
    headers: list[str], rows: list[list[str]], style: LayoutStyle
) -> Table:
    number_columns = len(headers) - 2
    number_width = 26 * mm
    sku_width = 24 * mm
    description_width = CONTENT_WIDTH - sku_width - number_columns * number_width

    description_style = _text_style(style)
    body = [
        [row[0], Paragraph(escape(row[1]), description_style), *row[2:]] for row in rows
    ]
    table = Table(
        [headers, *body],
        colWidths=[sku_width, description_width, *[number_width] * number_columns],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(style.accent)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), BOLD_FONTS[style.font]),
                ("FONTNAME", (0, 1), (-1, -1), style.font),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_SHADE]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, GRID),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _totals_table(rows: list[tuple[str, str]], style: LayoutStyle) -> Table:
    right = _text_style(style, alignment=TA_RIGHT)
    right_bold = _text_style(style, 11, True, alignment=TA_RIGHT)
    cells = []
    for index, (label, value) in enumerate(rows):
        cell_style = right_bold if index == len(rows) - 1 else right
        cells.append(
            [Paragraph(escape(label), cell_style), Paragraph(escape(value), cell_style)]
        )
    table = Table(cells, colWidths=[CONTENT_WIDTH - 40 * mm, 40 * mm])
    table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, 0), 4 * mm),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor(style.accent)),
            ]
        )
    )
    return table


def _note(text: str, style: LayoutStyle) -> Paragraph:
    return Paragraph(
        text,
        _text_style(
            style, 8, textColor=colors.HexColor("#52525b"), spaceBefore=10 * mm
        ),
    )


def _build_pdf(path: Path, title: str, author: str, story: list[Flowable]) -> None:
    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=title,
        author=author,
        invariant=True,
    )
    document.build(story)
