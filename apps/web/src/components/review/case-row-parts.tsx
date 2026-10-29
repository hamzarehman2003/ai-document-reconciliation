import { MatchStamp, ReviewStamp } from "@/components/ledger/status-stamps";
import type { MatchCase } from "@/lib/api";
import { PROBLEM_LABELS } from "@/lib/format";

/** Small pieces shared by the Overview list and the Review table. */

export function CaseStamp({ matchCase }: { matchCase: MatchCase }) {
  return matchCase.review_status === "pending" ? (
    <MatchStamp status={matchCase.status} />
  ) : (
    <ReviewStamp status={matchCase.review_status} />
  );
}

/** "Price differs from the order +1 more", or a quiet dash. */
export function ProblemSummary({ matchCase }: { matchCase: MatchCase }) {
  const [first, ...rest] = matchCase.discrepancies;
  if (!first) return <span className="text-muted-foreground">—</span>;
  return (
    <span>
      {PROBLEM_LABELS[first.code] ?? first.code}
      {rest.length > 0 && <span className="text-muted-foreground"> +{rest.length} more</span>}
    </span>
  );
}

/** Undecided invoices with problems, oldest first: what a reviewer should open next. */
export function needsDecision(cases: MatchCase[]): MatchCase[] {
  return cases
    .filter((item) => item.status === "needs_review" && item.review_status === "pending")
    .sort((a, b) => a.updated_at.localeCompare(b.updated_at));
}
