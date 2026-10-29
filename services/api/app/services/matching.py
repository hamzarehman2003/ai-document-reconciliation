"""Link each invoice to its PO and goods receipts, run the rules, save the case.

Matching runs as its own job ("match_document"), queued in the same
transaction that saves a processed (or failed) document. So it only ever sees
committed documents, and a matching error never undoes an extraction.
A database lock lets only one matching run at a time, so two workers can't
each miss the other's document, or overwrite each other's case.
"""

from typing import Any

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.config import settings
from app.models import (
    AuditAction,
    AuditObject,
    Discrepancy,
    Document,
    DocumentStatus,
    DocumentType,
    Job,
    MatchCase,
    MatchStatus,
    ReviewStatus,
)
from app.models.match_case import match_case_receipts
from app.rules import DocumentData, Finding, LineData, Tolerances, check_invoice
from app.services.audit import SYSTEM, record
from app.storage import LocalStorage

MATCH_DOCUMENT_JOB = "match_document"
MATCHING_LOCK_ID = 7301  # any fixed number, shared by everything that matches


def run_match_job(
    session: Session, storage: LocalStorage, payload: dict[str, Any]
) -> None:
    """Handler for 'match_document' jobs: re-check what this document affects."""
    lock_matching(session)
    document = session.get(Document, payload["document_id"])
    if document is not None:
        update_matches(session, document)
    session.commit()


def queue_matching(session: Session, document: Document) -> None:
    """Queue a re-check; saved in the same commit as the change that needs it."""
    session.add(Job(kind=MATCH_DOCUMENT_JOB, payload={"document_id": document.id}))


def lock_matching(session: Session) -> None:
    """Wait until no other matching runs; released when the transaction ends."""
    session.execute(select(func.pg_advisory_xact_lock(MATCHING_LOCK_ID)))


def update_matches(session: Session, document: Document) -> None:
    """Re-check every invoice this document's change could affect."""
    affected: dict[int, Document] = {}
    is_processed = document.status is DocumentStatus.PROCESSED

    if is_processed and document.doc_type is DocumentType.INVOICE:
        affected[document.id] = document
        # Earlier and later invoices with the same number: who is the duplicate?
        for other in same_number_invoices(session, document.document_number):
            affected[other.id] = other
    elif document.match_case is not None:
        document.match_case = None  # no longer a processed invoice

    if is_processed and document.doc_type is DocumentType.PURCHASE_ORDER:
        po_number = document.document_number
    elif is_processed and document.doc_type is DocumentType.GOODS_RECEIPT:
        po_number = document.po_reference
    else:
        po_number = None
    for invoice in invoices_for_po(session, po_number):
        affected[invoice.id] = invoice

    # Cases that point at this document under its old number or type.
    for invoice in invoices_referencing(session, document.id):
        affected[invoice.id] = invoice

    for invoice in sorted(affected.values(), key=lambda doc: doc.id):
        if (
            invoice.status is DocumentStatus.PROCESSED
            and invoice.doc_type is DocumentType.INVOICE
        ):
            match_invoice(session, invoice)


def match_all(session: Session) -> dict[MatchStatus, int]:
    """Check every processed invoice again. Returns how many ended in each status."""
    counts = dict.fromkeys(MatchStatus, 0)
    for invoice in session.scalars(
        processed(DocumentType.INVOICE).order_by(Document.id)
    ):
        counts[match_invoice(session, invoice).status] += 1
    return counts


def match_invoice(session: Session, invoice: Document) -> MatchCase:
    """Find the invoice's PO and receipts, run the rules, and save the result."""
    purchase_order = find_purchase_order(session, invoice.po_reference)
    receipts = find_goods_receipts(session, invoice.po_reference)
    earlier = [
        other
        for other in same_number_invoices(session, invoice.document_number)
        if other.id < invoice.id
    ]

    findings = check_invoice(
        to_rules_data(invoice),
        to_rules_data(purchase_order) if purchase_order else None,
        [to_rules_data(receipt) for receipt in receipts],
        [to_rules_data(other) for other in earlier],
        Tolerances(
            price_percent=settings.price_tolerance_percent,
            quantity_percent=settings.quantity_tolerance_percent,
            amount=settings.amount_tolerance,
        ),
    )

    case = invoice.match_case
    is_new = case is None
    if case is None:
        case = MatchCase(invoice=invoice)
    old_status = None if is_new else case.status
    old_result = None if is_new else result_key_of_case(case)

    case.purchase_order = purchase_order
    case.goods_receipts = receipts
    case.discrepancies = [to_discrepancy(finding) for finding in findings]
    if findings:
        case.status = MatchStatus.NEEDS_REVIEW
    elif purchase_order is None or not receipts:
        case.status = MatchStatus.WAITING
    else:
        case.status = MatchStatus.MATCHED
    # Set by hand: replacing only the problems doesn't touch this row,
    # so the database wouldn't update the time by itself.
    case.updated_at = func.now()
    session.add(case)
    session.flush()

    result_changed = old_result != result_key(purchase_order, receipts, findings)
    if not is_new and result_changed and case.review_status is not ReviewStatus.PENDING:
        reset_decision(session, case)
    if case.status != old_status:
        record(
            session,
            SYSTEM,
            AuditAction.MATCH_STATUS_CHANGED,
            AuditObject.MATCH_CASE,
            case.id,
            {"from": old_status.value if old_status else None, "to": case.status.value},
        )
    return case


def reset_decision(session: Session, case: MatchCase) -> None:
    """The match changed after a decision: the person must look again."""
    record(
        session,
        SYSTEM,
        AuditAction.DECISION_RESET,
        AuditObject.MATCH_CASE,
        case.id,
        {
            "previous_decision": case.review_status.value,
            "reason": "The 3-way match result changed after the decision.",
        },
    )
    case.review_status = ReviewStatus.PENDING
    case.reviewed_by = None
    case.reviewed_at = None
    case.review_note = None


ResultKey = tuple[int | None, tuple[int, ...], tuple[tuple[str, str], ...]]


def result_key(
    purchase_order: Document | None, receipts: list[Document], findings: list[Finding]
) -> ResultKey:
    """What a reviewer saw: the linked documents and the problems."""
    return (
        purchase_order.id if purchase_order else None,
        tuple(receipt.id for receipt in receipts),
        tuple(sorted((f.code.value, f.message) for f in findings)),
    )


def result_key_of_case(case: MatchCase) -> ResultKey:
    return (
        case.purchase_order_id,
        tuple(receipt.id for receipt in case.goods_receipts),
        tuple(sorted((d.code.value, d.message) for d in case.discrepancies)),
    )


def find_purchase_order(session: Session, po_number: str | None) -> Document | None:
    if not po_number:
        return None
    return session.scalars(
        processed(DocumentType.PURCHASE_ORDER)
        .where(same_text(Document.document_number, po_number))
        .order_by(Document.id.desc())
    ).first()


def find_goods_receipts(session: Session, po_number: str | None) -> list[Document]:
    """Every receipt for the order: a delivery can be split over several."""
    if not po_number:
        return []
    return list(
        session.scalars(
            processed(DocumentType.GOODS_RECEIPT)
            .where(same_text(Document.po_reference, po_number))
            .order_by(Document.id)
        )
    )


def invoices_for_po(session: Session, po_number: str | None) -> list[Document]:
    if not po_number:
        return []
    return list(
        session.scalars(
            processed(DocumentType.INVOICE).where(
                same_text(Document.po_reference, po_number)
            )
        )
    )


def same_number_invoices(session: Session, number: str | None) -> list[Document]:
    if not number:
        return []
    return list(
        session.scalars(
            processed(DocumentType.INVOICE)
            .where(same_text(Document.document_number, number))
            .order_by(Document.id)
        )
    )


def invoices_referencing(session: Session, document_id: int) -> list[Document]:
    """Invoices whose case uses this document as PO, receipt or in a problem."""
    as_receipt = select(match_case_receipts.c.case_id).where(
        match_case_receipts.c.document_id == document_id
    )
    in_a_problem = select(Discrepancy.case_id).where(
        Discrepancy.refs.contains([{"document_id": document_id}])
    )
    return list(
        session.scalars(
            select(Document)
            .join(MatchCase, MatchCase.invoice_id == Document.id)
            .where(
                or_(
                    MatchCase.purchase_order_id == document_id,
                    MatchCase.id.in_(as_receipt),
                    MatchCase.id.in_(in_a_problem),
                )
            )
        )
    )


def processed(doc_type: DocumentType) -> Select[tuple[Document]]:
    """A query for processed documents of one type."""
    return select(Document).where(
        Document.doc_type == doc_type, Document.status == DocumentStatus.PROCESSED
    )


def same_text(
    column: InstrumentedAttribute[str | None], value: str | None
) -> ColumnElement[bool]:
    """Compare document numbers ignoring case and surrounding spaces."""
    return func.upper(func.trim(column)) == (value or "").strip().upper()


def to_rules_data(document: Document) -> DocumentData:
    return DocumentData(
        document_id=document.id,
        number=document.document_number,
        vendor_name=document.vendor_name,
        po_reference=document.po_reference,
        subtotal=document.subtotal,
        tax=document.tax,
        total=document.total,
        lines=[
            LineData(
                item.position,
                item.sku,
                item.description,
                item.quantity,
                item.unit_price,
                item.line_total,
            )
            for item in document.line_items
        ],
    )


def to_discrepancy(finding: Finding) -> Discrepancy:
    return Discrepancy(
        code=finding.code,
        severity=finding.severity,
        message=finding.message,
        details=finding.details,
        refs=[
            {"document_id": ref.document_id, "field": ref.field}
            for ref in finding.references
        ],
    )
