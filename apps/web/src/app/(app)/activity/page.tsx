import type { Metadata } from "next";
import { History } from "lucide-react";

import { EmptyState } from "@/components/ledger/empty-state";
import { PageHeader } from "@/components/ledger/page-header";

export const metadata: Metadata = { title: "Activity" };

export default function ActivityPage() {
  return (
    <>
      <PageHeader
        eyebrow="Records"
        title="Activity"
        description="Every upload, correction and decision, with who made it and when."
      />
      <EmptyState
        icon={History}
        title="The audit log arrives in the next step"
        description="A timeline of everything that happened to every document."
      />
    </>
  );
}
