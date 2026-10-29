"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, FileQuestion } from "lucide-react";

import { DocumentCard } from "@/components/document-card";
import { EmptyState } from "@/components/ledger/empty-state";
import { PageHeader } from "@/components/ledger/page-header";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { getDocument, type DocumentDetail } from "@/lib/api";
import { formatDate, formatMoney, orDash } from "@/lib/format";

const backButton = (
  <Button variant="outline" asChild>
    <Link href="/review">
      <ArrowLeft /> Review queue
    </Link>
  </Button>
);

/** One invoice: what the AI read, its 3-way match, and the decision. */
export function InvoiceWorkspace({ invoiceId }: { invoiceId: number }) {
  const [invoice, setInvoice] = useState<DocumentDetail | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    getDocument(invoiceId)
      .then(setInvoice)
      .catch(() => setMissing(true));
  }, [invoiceId]);

  if (missing) {
    return (
      <EmptyState
        icon={FileQuestion}
        title="Invoice not found"
        description="It may have been removed, or the link is wrong."
        action={backButton}
      />
    );
  }
  if (invoice === null) {
    return <Skeleton className="h-[32rem]" />;
  }

  return (
    <>
      <PageHeader
        eyebrow="Invoice"
        title={orDash(invoice.vendor_name)}
        description={
          <span className="numeric">
            {orDash(invoice.document_number)} · {formatDate(invoice.issue_date)} ·{" "}
            {formatMoney(invoice.total, invoice.currency)}
          </span>
        }
        actions={backButton}
      />
      <DocumentCard document={invoice} />
    </>
  );
}
