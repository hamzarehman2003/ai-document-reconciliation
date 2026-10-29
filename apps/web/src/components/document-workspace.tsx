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
import { DOC_TYPE_LABELS, formatDate, formatMoney, orDash } from "@/lib/format";

const POLL_MS = 2000;

type Props = {
  documentId: number;
  backHref: string;
  backLabel: string;
};

/** One document on its own page: what the AI read, and for an invoice its 3-way match. */
export function DocumentWorkspace({ documentId, backHref, backLabel }: Props) {
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function load() {
      try {
        const loaded = await getDocument(documentId);
        if (cancelled) return;
        setDocument(loaded);
        // Still being read: check again until the AI is done.
        if (loaded.status === "uploaded" || loaded.status === "processing") {
          timer = setTimeout(load, POLL_MS);
        }
      } catch {
        if (!cancelled) setMissing(true);
      }
    }

    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [documentId]);

  const back = (
    <Button variant="outline" asChild>
      <Link href={backHref}>
        <ArrowLeft /> {backLabel}
      </Link>
    </Button>
  );

  if (missing) {
    return (
      <EmptyState
        icon={FileQuestion}
        title="Document not found"
        description="It may have been removed, or the link is wrong."
        action={back}
      />
    );
  }
  if (document === null) {
    return <Skeleton className="h-[32rem]" />;
  }

  const isReceipt = document.doc_type === "goods_receipt";
  return (
    <>
      <PageHeader
        eyebrow={DOC_TYPE_LABELS[document.doc_type]}
        title={document.vendor_name ?? document.filename}
        description={
          <span className="numeric">
            {orDash(document.document_number)} · {formatDate(document.issue_date)}
            {!isReceipt && ` · ${formatMoney(document.total, document.currency)}`}
          </span>
        }
        actions={back}
      />
      {/* A new key after each reload, so the card shows the finished document. */}
      <DocumentCard key={document.status} document={document} />
    </>
  );
}
