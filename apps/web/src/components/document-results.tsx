"use client";

import { useEffect, useState } from "react";

import { DocumentCard } from "@/components/document-card";
import { Skeleton } from "@/components/ui/skeleton";
import { getDocument, type DocumentDetail } from "@/lib/api";

const POLL_MS = 2000;

/** Shows each document and keeps checking until every one is processed or failed. */
export function DocumentResults({ documentIds }: { documentIds: number[] }) {
  const [documents, setDocuments] = useState<Record<number, DocumentDetail>>({});

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function refresh() {
      const loaded = await Promise.all(
        documentIds.map((id) => getDocument(id).catch(() => null)),
      );
      if (cancelled) return;

      const byId: Record<number, DocumentDetail> = {};
      for (const document of loaded) {
        if (document) byId[document.id] = document;
      }
      setDocuments(byId);

      const finished = loaded.every(
        (document) => document && (document.status === "processed" || document.status === "failed"),
      );
      if (!finished) timer = setTimeout(refresh, POLL_MS);
    }

    refresh();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [documentIds]);

  return (
    <div className="flex flex-col gap-4">
      {documentIds.map((id) =>
        documents[id] ? (
          <DocumentCard key={id} document={documents[id]} />
        ) : (
          <Skeleton key={id} className="h-40 w-full" />
        ),
      )}
    </div>
  );
}
