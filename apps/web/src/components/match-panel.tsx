"use client";

import { useEffect, useState } from "react";
import { CircleAlert, CircleCheck, Clock, TriangleAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { getMatchCaseForInvoice, type MatchCase } from "@/lib/api";
import { cn } from "@/lib/utils";

const POLL_MS = 3000;
const MAX_CHECKS_WITHOUT_CASE = 20; // the match normally appears within seconds

const MISSING_LABELS = {
  purchase_order: "the purchase order",
  goods_receipt: "the goods receipt",
} as const;

type Props = {
  invoiceId: number;
  /** Highlight a field of this invoice on the page. */
  onSelectField: (field: string) => void;
};

/** The invoice checked against its purchase order and goods receipts. */
export function MatchPanel({ invoiceId, onSelectField }: Props) {
  const [matchCase, setMatchCase] = useState<MatchCase | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let checksWithoutCase = 0;

    async function refresh() {
      let found: MatchCase | null;
      try {
        found = await getMatchCaseForInvoice(invoiceId);
      } catch {
        if (!cancelled) setError(true); // show it and stop: no endless retrying
        return;
      }
      if (cancelled) return;
      setError(false);
      setMatchCase(found);

      // Keep checking while documents are missing: when they arrive the invoice is
      // checked again (also when it already has problems).
      const missing = found === null || found.waiting_for.length > 0;
      if (found === null) checksWithoutCase += 1;
      if (missing && checksWithoutCase < MAX_CHECKS_WITHOUT_CASE) {
        timer = setTimeout(refresh, POLL_MS);
      }
    }

    refresh();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [invoiceId]);

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
    <div className="flex flex-col gap-3 rounded-lg border p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium">3-way match</span>
        <StatusBadge matchCase={matchCase} />
      </div>

      {matchCase.waiting_for.length > 0 && (
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <Clock className="mt-0.5 size-4 shrink-0" />
          <span>
            Not uploaded yet: {matchCase.waiting_for.map((item) => MISSING_LABELS[item]).join(" and ")}{" "}
            for {matchCase.po_number}. Upload it and this invoice is checked again automatically.
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
                    "flex w-full items-start gap-2 rounded-md p-2 text-left text-sm",
                    onThisInvoice && "hover:bg-muted",
                  )}
                >
                  {problem.severity === "error" ? (
                    <CircleAlert className="mt-0.5 size-4 shrink-0 text-destructive" />
                  ) : (
                    <TriangleAlert className="mt-0.5 size-4 shrink-0 text-amber-600" />
                  )}
                  <span>
                    {problem.message}
                    <span className="block font-mono text-xs text-muted-foreground">
                      {problem.code}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function StatusBadge({ matchCase }: { matchCase: MatchCase }) {
  if (matchCase.status === "matched") {
    return (
      <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
        <CircleCheck />
        Matched
      </Badge>
    );
  }
  if (matchCase.status === "waiting") {
    return (
      <Badge variant="secondary">
        <Clock />
        Waiting for documents
      </Badge>
    );
  }
  const count = matchCase.discrepancies.length;
  return (
    <Badge variant="destructive">
      <CircleAlert />
      Needs review · {count} problem{count === 1 ? "" : "s"}
    </Badge>
  );
}
