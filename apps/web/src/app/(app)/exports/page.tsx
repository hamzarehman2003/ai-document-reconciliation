import type { Metadata } from "next";
import { Download, FileSpreadsheet } from "lucide-react";

import { EmptyState } from "@/components/ledger/empty-state";
import { PageHeader } from "@/components/ledger/page-header";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "Exports" };

export default function ExportsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Records"
        title="Exports"
        description="Approved invoices, ready to import into your accounting system."
        actions={
          <Button variant="outline" asChild>
            <a href="/api/exports/approved.xlsx">
              <Download /> Excel
            </a>
          </Button>
        }
      />
      <EmptyState
        icon={FileSpreadsheet}
        title="The export preview arrives in the next step"
        description="See exactly which invoices and lines go into the file before you download it."
      />
    </>
  );
}
