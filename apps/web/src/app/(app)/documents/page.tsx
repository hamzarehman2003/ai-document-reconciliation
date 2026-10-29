import type { Metadata } from "next";
import { Files } from "lucide-react";

import { EmptyState } from "@/components/ledger/empty-state";
import { PageHeader } from "@/components/ledger/page-header";

export const metadata: Metadata = { title: "Documents" };

export default function DocumentsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Records"
        title="Documents"
        description="Every invoice, purchase order and receipt you uploaded, with what the AI read from it."
      />
      <EmptyState
        icon={Files}
        title="The document list arrives in the next step"
        description="Search and filter every uploaded file by type, status and vendor."
      />
    </>
  );
}
