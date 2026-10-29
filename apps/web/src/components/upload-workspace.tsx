"use client";

import { useState } from "react";

import { DocumentResults } from "@/components/document-results";
import { Stamp } from "@/components/ledger/stamp";
import { UploadForm } from "@/components/upload-form";
import type { UploadResponse, UploadResult } from "@/lib/api";

/** Upload on top, then what happened to each file, then the extracted data. */
export function UploadWorkspace() {
  const [results, setResults] = useState<UploadResult[]>([]);
  const [documentIds, setDocumentIds] = useState<number[]>([]);

  function handleUploaded(response: UploadResponse) {
    setResults(response.results);
    // New files and duplicates both point to a document we can show.
    setDocumentIds(
      response.results
        .map((result) => result.document_id ?? result.existing_document_id)
        .filter((id): id is number => id !== null),
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <UploadForm onUploaded={handleUploaded} />

      {results.length > 0 && (
        <ul className="flex flex-col gap-2.5 rounded-lg border bg-card p-4 text-sm shadow-paper">
          {results.map((result, index) => (
            <li key={index} className="flex flex-wrap items-center gap-2">
              <OutcomeStamp outcome={result.outcome} />
              <span className="font-medium">{result.filename}</span>
              {result.detail && <span className="text-muted-foreground">{result.detail}</span>}
            </li>
          ))}
        </ul>
      )}

      {documentIds.length > 0 && <DocumentResults documentIds={documentIds} />}
    </div>
  );
}

function OutcomeStamp({ outcome }: { outcome: UploadResult["outcome"] }) {
  if (outcome === "accepted") {
    return <Stamp tone="success">Accepted</Stamp>;
  }
  if (outcome === "duplicate") {
    return <Stamp>Already uploaded</Stamp>;
  }
  return <Stamp tone="danger">Rejected</Stamp>;
}
