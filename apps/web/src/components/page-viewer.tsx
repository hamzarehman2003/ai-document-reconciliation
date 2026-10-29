"use client";

import { useState } from "react";
import Image from "next/image";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Evidence } from "@/lib/api";
import { cn } from "@/lib/utils";

const PADDING = 0.004; // a little space around each box, as a fraction of the page

type Props = {
  documentId: number;
  pageCount: number;
  evidence: Evidence[];
  /** A field ("total") or a line-item prefix ("line_items.3") to highlight. */
  selected: string | null;
};

/** The document page with a box on every located value; the selected ones stand out. */
export function PageViewer({ documentId, pageCount, evidence, selected }: Props) {
  const [chosenPage, setChosenPage] = useState(1);
  const isSelected = (item: Evidence) =>
    selected !== null && (item.field === selected || item.field.startsWith(`${selected}.`));
  const selectedPage = evidence.find(isSelected)?.page;
  const page = selectedPage ?? chosenPage; // jump to the page of the selected value

  return (
    <div className="flex flex-col gap-2">
      <div className="relative overflow-hidden rounded-md border bg-white">
        <Image
          src={`/api/documents/${documentId}/pages/${page}`}
          alt={`Page ${page}`}
          width={935}
          height={1210}
          unoptimized
          className="h-auto w-full"
        />
        {evidence
          .filter((item) => item.page === page)
          .map((item) => (
            <div
              key={item.field}
              title={`${item.text} (${item.source === "ocr" ? "OCR" : "PDF text"})`}
              className={cn(
                "pointer-events-none absolute rounded-sm transition-colors",
                isSelected(item)
                  ? "border-2 border-amber-500 bg-amber-300/35"
                  : "border border-sky-500/25",
              )}
              style={{
                left: `${(item.x0 - PADDING) * 100}%`,
                top: `${(item.y0 - PADDING) * 100}%`,
                width: `${(item.x1 - item.x0 + 2 * PADDING) * 100}%`,
                height: `${(item.y1 - item.y0 + 2 * PADDING) * 100}%`,
              }}
            />
          ))}
      </div>

      {pageCount > 1 && (
        <div className="flex items-center justify-center gap-2 text-sm">
          <Button
            variant="outline"
            size="icon-sm"
            disabled={page <= 1}
            onClick={() => setChosenPage(page - 1)}
            aria-label="Previous page"
          >
            <ChevronLeft />
          </Button>
          Page {page} of {pageCount}
          <Button
            variant="outline"
            size="icon-sm"
            disabled={page >= pageCount}
            onClick={() => setChosenPage(page + 1)}
            aria-label="Next page"
          >
            <ChevronRight />
          </Button>
        </div>
      )}
    </div>
  );
}
