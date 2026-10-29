import { Stamp, type StampTone } from "@/components/ledger/stamp";
import type { DocumentStatus, MatchCase, MatchStatus } from "@/lib/api";

/** One place that decides how every status looks, so it's the same on every screen. */

const DOCUMENT: Record<DocumentStatus, [string, StampTone]> = {
  uploaded: ["Waiting", "neutral"],
  processing: ["Reading", "accent"],
  processed: ["Extracted", "success"],
  failed: ["Failed", "danger"],
};

const MATCH: Record<MatchStatus, [string, StampTone]> = {
  matched: ["Matched", "success"],
  needs_review: ["Needs review", "warning"],
  waiting: ["Waiting for documents", "neutral"],
};

const REVIEW: Record<MatchCase["review_status"], [string, StampTone]> = {
  pending: ["Pending", "neutral"],
  approved: ["Approved", "success"],
  rejected: ["Rejected", "danger"],
};

export function DocumentStatusStamp({ status }: { status: DocumentStatus }) {
  const [label, tone] = DOCUMENT[status];
  const working = status === "uploaded" || status === "processing";
  return (
    <Stamp tone={tone} pulse={working}>
      {label}
    </Stamp>
  );
}

export function MatchStamp({ status }: { status: MatchStatus }) {
  const [label, tone] = MATCH[status];
  return <Stamp tone={tone}>{label}</Stamp>;
}

export function ReviewStamp({ status }: { status: MatchCase["review_status"] }) {
  const [label, tone] = REVIEW[status];
  return <Stamp tone={tone}>{label}</Stamp>;
}
