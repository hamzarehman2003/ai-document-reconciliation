"use client";

import { useEffect, useState } from "react";
import { CircleAlert, Clock, TriangleAlert } from "lucide-react";

import { Stamp } from "@/components/ledger/stamp";
import { MatchStamp } from "@/components/ledger/status-stamps";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  decideMatchCase,
  getHistory,
  getMatchCaseForInvoice,
  type AuditEvent,
  type MatchCase,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const POLL_MS = 3000;
const MAX_CHECKS_WITHOUT_CASE = 20; // the match normally appears within seconds
const CHECKS_AFTER_A_CORRECTION = 4; // the re-check runs in the background

const MISSING_LABELS = {
  purchase_order: "the purchase order",
  goods_receipt: "the goods receipt",
} as const;

const STATUS_LABELS: Record<string, string> = {
  matched: "matched",
  needs_review: "needs review",
  waiting: "waiting for documents",
};

type Props = {
  invoiceId: number;
  /** Highlight a field of this invoice on the page. */
  onSelectField: (field: string) => void;
  /** Changes after a value was corrected: check the match again. */
  refreshKey: number;
};

/** The invoice checked against its purchase order and goods receipts, and the decision. */
export function MatchPanel({ invoiceId, onSelectField, refreshKey }: Props) {
  const [matchCase, setMatchCase] = useState<MatchCase | null>(null);
  const [history, setHistory] = useState<AuditEvent[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let checksWithoutCase = 0;
    let extraChecks = refreshKey > 0 ? CHECKS_AFTER_A_CORRECTION : 0;

    async function refresh() {
      let found: MatchCase | null;
      let events: AuditEvent[];
      try {
        [found, events] = await Promise.all([
          getMatchCaseForInvoice(invoiceId),
          getHistory(invoiceId),
        ]);
      } catch {
        if (!cancelled) setError(true); // show it and stop: no endless retrying
        return;
      }
      if (cancelled) return;
      setError(false);
      setMatchCase(found);
      setHistory(events);

      // Keep checking while documents are missing (the invoice is checked again
      // when they arrive) and for a moment after a correction.
      if (found === null) checksWithoutCase += 1;
      const missing = found === null || found.waiting_for.length > 0;
      const keepChecking =
        (missing && checksWithoutCase < MAX_CHECKS_WITHOUT_CASE) || extraChecks-- > 0;
      if (keepChecking) timer = setTimeout(refresh, POLL_MS);
    }

    refresh();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [invoiceId, refreshKey]);

  async function handleDecided(updated: MatchCase) {
    setMatchCase(updated);
    setHistory(await getHistory(invoiceId).catch(() => history));
  }

  if (error) {
    return (
      <p className="rounded-lg border p-4 text-sm text-muted-foreground">
        Couldn&apos;t load the 3-way match result. Reload the page to try again.
      </p>
    );
  }
  if (matchCase === null) {
    return null;
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-muted/30 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="eyebrow">3-way match</span>
        <MatchCaseStamp matchCase={matchCase} />
      </div>

      {matchCase.waiting_for.length > 0 && (
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <Clock className="mt-0.5 size-4 shrink-0" />
          <span>
            Not uploaded yet:{" "}
            {matchCase.waiting_for.map((item) => MISSING_LABELS[item]).join(" and ")} for{" "}
            {matchCase.po_number}. Upload it and this invoice is checked again automatically.
          </span>
        </p>
      )}

      {matchCase.status === "matched" && (
        <p className="text-sm text-muted-foreground">
          Quantities, prices and totals agree with purchase order {matchCase.po_number} and its
          goods receipt{matchCase.goods_receipt_ids.length > 1 ? "s" : ""}.
        </p>
      )}

      {matchCase.discrepancies.length > 0 && (
        <ul className="flex flex-col gap-2">
          {matchCase.discrepancies.map((problem, index) => {
            const onThisInvoice = problem.refs.find((ref) => ref.document_id === invoiceId);
            return (
              <li key={index}>
                <button
                  type="button"
                  disabled={!onThisInvoice}
                  onClick={() => onThisInvoice && onSelectField(onThisInvoice.field)}
                  className={cn(
                    "flex w-full items-start gap-2 rounded-md p-2 text-left text-sm transition-colors",
                    onThisInvoice && "hover:bg-accent",
                  )}
                >
                  {problem.severity === "error" ? (
                    <CircleAlert className="mt-0.5 size-4 shrink-0 text-destructive" />
                  ) : (
                    <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warning" />
                  )}
                  <span>
                    {problem.message}
                    <span className="mt-0.5 block font-mono text-[0.6875rem] tracking-wide text-muted-foreground">
                      {problem.code}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <ReviewControls matchCase={matchCase} onDecided={handleDecided} />
      <History events={history} />
    </div>
  );
}

function ReviewControls({
  matchCase,
  onDecided,
}: {
  matchCase: MatchCase;
  onDecided: (updated: MatchCase) => void;
}) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(decision: "approve" | "reject" | "reopen") {
    setBusy(true);
    setError(null);
    try {
      onDecided(await decideMatchCase(matchCase.id, decision, note));
      setNote("");
    } catch (decisionError) {
      setError(decisionError instanceof Error ? decisionError.message : "That didn't work.");
    } finally {
      setBusy(false);
    }
  }

  if (matchCase.review_status !== "pending") {
    const approved = matchCase.review_status === "approved";
    return (
      <div className="flex flex-col gap-2 border-t pt-3 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Stamp tone={approved ? "success" : "danger"}>
            {approved ? "Approved for payment" : "Rejected"}
          </Stamp>
          <Button size="sm" variant="outline" onClick={() => send("reopen")} disabled={busy}>
            Reopen
          </Button>
        </div>
        <p className="text-muted-foreground">
          by {matchCase.reviewed_by}
          {matchCase.reviewed_at && ` · ${formatTime(matchCase.reviewed_at)}`}
          {matchCase.review_note && ` · “${matchCase.review_note}”`}
        </p>
      </div>
    );
  }

  const blocked = matchCase.waiting_for.length > 0;
  return (
    <div className="flex flex-col gap-2 border-t pt-3">
      <Textarea
        value={note}
        onChange={(event) => setNote(event.target.value)}
        placeholder={
          matchCase.discrepancies.length > 0
            ? "Note (required): why approve or reject this invoice?"
            : "Note (optional for approving, required for rejecting)"
        }
        className="min-h-16 text-sm"
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="flex gap-2">
        <Button
          size="sm"
          onClick={() => send("approve")}
          disabled={busy || blocked}
          title={blocked ? "Wait for the purchase order and goods receipt" : undefined}
        >
          Approve
        </Button>
        <Button size="sm" variant="outline" onClick={() => send("reject")} disabled={busy}>
          Reject
        </Button>
      </div>
    </div>
  );
}

function History({ events }: { events: AuditEvent[] }) {
  if (events.length === 0) return null;
  return (
    <details className="border-t pt-3 text-sm">
      <summary className="cursor-pointer text-muted-foreground">
        History ({events.length})
      </summary>
      <ol className="mt-2 flex flex-col gap-1.5">
        {events.map((event) => (
          <li key={event.id} className="flex gap-2">
            <span className="numeric w-24 shrink-0 text-xs text-muted-foreground">
              {formatTime(event.created_at)}
            </span>
            <span>
              {describe(event)}
              <span className="text-muted-foreground"> · {event.actor}</span>
            </span>
          </li>
        ))}
      </ol>
    </details>
  );
}

function describe(event: AuditEvent): string {
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
    default:
      return event.action;
  }
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function MatchCaseStamp({ matchCase }: { matchCase: MatchCase }) {
  if (matchCase.status !== "needs_review") {
    return <MatchStamp status={matchCase.status} />;
  }
  const count = matchCase.discrepancies.length;
  return (
    <Stamp tone="warning">
      Needs review · {count} problem{count === 1 ? "" : "s"}
    </Stamp>
  );
}
