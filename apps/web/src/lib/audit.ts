import type { AuditEvent } from "@/lib/api";

const STATUS_LABELS: Record<string, string> = {
  matched: "matched",
  needs_review: "needs review",
  waiting: "waiting for documents",
};

const FORMATS: Record<string, string> = { xlsx: "Excel", csv: "CSV" };

/** One sentence for an audit event, used in the invoice history and the Activity page.
 * `count` > 1 means several identical export events shown as one. */
export function describe(event: AuditEvent, count = 1): string {
  const details = event.details;
  switch (event.action) {
    case "document_uploaded":
      return "Uploaded";
    case "document_processed":
      return "Read by AI";
    case "document_failed":
      return `Processing failed: ${String(details.error ?? "")}`;
    case "field_corrected":
      return `Corrected ${String(details.field)}: ${String(details.old ?? "empty")} → ${String(details.new ?? "empty")}`;
    case "match_status_changed":
      return `3-way match: ${STATUS_LABELS[String(details.to)] ?? String(details.to)}`;
    case "case_approved":
      return "Approved for payment";
    case "case_rejected":
      return "Rejected";
    case "case_reopened":
      return "Reopened";
    case "decision_reset":
      return "Decision reset: the match result changed";
    case "case_exported":
      return `Exported ${count > 1 ? `${count} invoices ` : ""}to ${FORMATS[String(details.format)] ?? "a file"}`;
    default:
      return event.action;
  }
}
