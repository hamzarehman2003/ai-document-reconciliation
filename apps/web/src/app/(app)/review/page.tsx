import type { Metadata } from "next";
import { ClipboardCheck } from "lucide-react";

import { EmptyState } from "@/components/ledger/empty-state";
import { PageHeader } from "@/components/ledger/page-header";

export const metadata: Metadata = { title: "Review" };

export default function ReviewPage() {
  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Review"
        description="Invoices that did not match their order or receipt, waiting for you to approve or reject."
      />
      <EmptyState
        icon={ClipboardCheck}
        title="The review queue arrives in the next step"
        description="Each exception will show what differs, side by side, with one-click decisions."
      />
    </>
  );
}
