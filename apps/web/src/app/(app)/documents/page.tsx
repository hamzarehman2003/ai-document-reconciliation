import type { Metadata } from "next";

import { DocumentList } from "@/components/documents/document-list";
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
      <DocumentList />
    </>
  );
}
