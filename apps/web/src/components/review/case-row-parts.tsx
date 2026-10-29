import { MatchStamp, ReviewStamp } from "@/components/ledger/status-stamps";
import type { MatchCase } from "@/lib/api";

/** Small pieces shared by the Overview list and the Review table. */

export function CaseStamp({ matchCase }: { matchCase: MatchCase }) {
  return matchCase.review_status === "pending" ? (
    <MatchStamp status={matchCase.status} />
  ) : (
    <ReviewStamp status={matchCase.review_status} />
  );
}

/** The case's one-line summary, cut to one line; the full sentence shows on hover. */
export function CaseSummary({ matchCase }: { matchCase: MatchCase }) {
  return (
    <span title={matchCase.summary} className="block truncate">
      {matchCase.summary}
    </span>
  );
}

/** Undecided invoices with problems, oldest first: what a reviewer should open next. */
export function needsDecision(cases: MatchCase[]): MatchCase[] {
  return cases
    .filter((item) => item.status === "needs_review" && item.review_status === "pending")
    .sort((a, b) => a.updated_at.localeCompare(b.updated_at));
}
