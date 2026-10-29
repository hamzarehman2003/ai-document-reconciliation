import type { Metadata } from "next";

import { ExportPreview } from "@/components/exports/export-preview";
import { PageHeader } from "@/components/ledger/page-header";

export const metadata: Metadata = { title: "Exports" };

export default function ExportsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Records"
        title="Exports"
        description="Approved invoices, ready to import into your accounting system. The Excel file has an Invoices sheet and a Line items sheet."
      />
      <ExportPreview />
    </>
  );
}
