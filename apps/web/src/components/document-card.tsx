"use client";

import { useState, type ReactNode } from "react";
import { ExternalLink, Loader2, TriangleAlert } from "lucide-react";

import { EditableValue } from "@/components/editable-value";
import { MatchPanel } from "@/components/match-panel";
import { PageViewer } from "@/components/page-viewer";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { DocumentDetail } from "@/lib/api";
import {
  DOC_TYPE_LABELS,
  formatDate,
  formatMoney,
  formatQuantity,
  orDash,
} from "@/lib/format";
import { cn } from "@/lib/utils";

export function DocumentCard({ document }: { document: DocumentDetail }) {
  const isWorking = document.status === "uploaded" || document.status === "processing";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="truncate">{document.filename}</CardTitle>
        <CardDescription className="flex flex-wrap items-center gap-2">
          <StatusBadge status={document.status} />
          {document.status === "processed" && (
            <Badge variant="outline">{DOC_TYPE_LABELS[document.doc_type]}</Badge>
          )}
        </CardDescription>
        <CardAction>
          <Button variant="outline" size="sm" asChild>
            <a href={`/api/documents/${document.id}/file`} target="_blank" rel="noreferrer">
              <ExternalLink />
              View file
            </a>
          </Button>
        </CardAction>
      </CardHeader>

      <CardContent>
        {isWorking && <ReadingPlaceholder />}
        {document.status === "failed" && (
          <Alert variant="destructive">
            <AlertDescription>{document.error_message ?? "Processing failed."}</AlertDescription>
          </Alert>
        )}
        {document.status === "processed" && <ExtractedData document={document} />}
      </CardContent>

      {document.status === "processed" && document.latest_extraction && (
        <CardFooter className="text-xs text-muted-foreground">
          Read by {document.latest_extraction.model}
          {document.latest_extraction.input_tokens !== null &&
            ` · ${document.latest_extraction.input_tokens} in / ${document.latest_extraction.output_tokens} out tokens`}
          {document.latest_extraction.duration_ms !== null &&
            ` · ${(document.latest_extraction.duration_ms / 1000).toFixed(1)} s`}
          {` · ${document.evidence.length} values located on the page`}
        </CardFooter>
      )}
    </Card>
  );
}

function StatusBadge({ status }: { status: DocumentDetail["status"] }) {
  if (status === "processed") {
    return (
      <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
        Extracted
      </Badge>
    );
  }
  if (status === "failed") {
    return <Badge variant="destructive">Failed</Badge>;
  }
  return (
    <Badge variant="secondary">
      <Loader2 className="animate-spin" />
      {status === "uploaded" ? "Waiting" : "Reading with AI"}
    </Badge>
  );
}

function ReadingPlaceholder() {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        The AI is reading this document. This usually takes 10–30 seconds.
      </p>
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-4 w-1/2" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}

/** Extracted values next to the page. Click a value to see where it is on the page;
 * use its pencil to correct it. */
function ExtractedData({ document: initial }: { document: DocumentDetail }) {
  const [document, setDocument] = useState(initial);
  const [selected, setSelected] = useState<string | null>(null);
  const [matchRefresh, setMatchRefresh] = useState(0);
  const located = new Set(document.evidence.map((item) => item.field));
  // Later corrections overwrite earlier ones: the latest per field is in effect.
  const corrections = new Map(document.corrections.map((item) => [item.field, item]));
  const isReceipt = document.doc_type === "goods_receipt";

  function handleSaved(updated: DocumentDetail) {
    setDocument(updated);
    setMatchRefresh((count) => count + 1); // the 3-way match is checked again
  }

  function select(field: string) {
    setSelected((current) => (current === field ? null : field));
  }

  function editable(field: string, display: string, raw: string | null) {
    return (
      <EditableValue
        documentId={document.id}
        field={field}
        display={display}
        raw={raw}
        correction={corrections.get(field)}
        onSaved={handleSaved}
      />
    );
  }

  /** Extracted but not found on the page, and not corrected by a person yet. */
  function unconfirmed(field: string, raw: string | null): boolean {
    return raw !== null && !located.has(field) && !corrections.has(field);
  }

  // [label, field key, shown value, raw value (null = nothing extracted)]
  const fields: [string, string, string, string | null][] = [
    ["Document number", "document_number", orDash(document.document_number), document.document_number],
    ["Vendor", "vendor_name", orDash(document.vendor_name), document.vendor_name],
    ["Buyer", "buyer_name", orDash(document.buyer_name), document.buyer_name],
    ["Date", "issue_date", formatDate(document.issue_date), document.issue_date],
    ["Due date", "due_date", formatDate(document.due_date), document.due_date],
    ["PO reference", "po_reference", orDash(document.po_reference), document.po_reference],
  ];
  const totals: [string, string, string | null][] = [
    ["Subtotal", "subtotal", document.subtotal],
    ["Tax", "tax", document.tax],
    ["Total", "total", document.total],
  ];

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <div className="lg:sticky lg:top-4 lg:self-start">
        <PageViewer
          documentId={document.id}
          pageCount={document.page_count ?? 1}
          evidence={document.evidence}
          selected={selected}
        />
      </div>

      <div className="flex min-w-0 flex-col gap-6">
        {document.doc_type === "invoice" && (
          <MatchPanel
            invoiceId={document.id}
            onSelectField={setSelected}
            refreshKey={matchRefresh}
          />
        )}

        <p className="text-xs text-muted-foreground">
          Click a value to see where it is on the page. Use the pencil to correct it.
        </p>

        <div className="grid grid-cols-2 gap-2">
          {fields.map(([label, field, shown, raw]) => (
            <Selectable
              key={field}
              active={selected === field}
              onSelect={() => select(field)}
              className="rounded-md border px-3 py-2"
            >
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                {label}
                {unconfirmed(field, raw) && <MissingMark />}
              </span>
              <span className="block truncate text-sm">{editable(field, shown, raw)}</span>
            </Selectable>
          ))}
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>SKU</TableHead>
              <TableHead>Description</TableHead>
              {isReceipt && <TableHead className="text-right">Ordered</TableHead>}
              <TableHead className="text-right">{isReceipt ? "Received" : "Qty"}</TableHead>
              {!isReceipt && <TableHead className="text-right">Unit price</TableHead>}
              {!isReceipt && <TableHead className="text-right">Amount</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {document.line_items.map((item) => {
              const row = `line_items.${item.position}`;
              const quantity = (value: string | null) =>
                value === null ? null : formatQuantity(value);
              return (
                <TableRow
                  key={item.position}
                  onClick={() => select(row)}
                  className={cn(
                    "cursor-pointer",
                    selected === row && "bg-amber-100/60 dark:bg-amber-500/15",
                  )}
                >
                  <TableCell className="font-mono text-xs">
                    <span className="inline-flex items-center gap-1">
                      {orDash(item.sku)}
                      {!located.has(`${row}.sku`) && <MissingMark />}
                    </span>
                  </TableCell>
                  <TableCell className="whitespace-normal">{item.description}</TableCell>
                  {isReceipt && (
                    <TableCell className="text-right">
                      {editable(
                        `${row}.quantity_ordered`,
                        formatQuantity(item.quantity_ordered),
                        quantity(item.quantity_ordered),
                      )}
                    </TableCell>
                  )}
                  <TableCell className="text-right">
                    {editable(`${row}.quantity`, formatQuantity(item.quantity), quantity(item.quantity))}
                  </TableCell>
                  {!isReceipt && (
                    <TableCell className="text-right">
                      {editable(
                        `${row}.unit_price`,
                        formatMoney(item.unit_price, document.currency),
                        item.unit_price,
                      )}
                    </TableCell>
                  )}
                  {!isReceipt && (
                    <TableCell className="text-right">
                      {editable(
                        `${row}.line_total`,
                        formatMoney(item.line_total, document.currency),
                        item.line_total,
                      )}
                    </TableCell>
                  )}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>

        {!isReceipt && (
          <div className="ml-auto flex w-full max-w-xs flex-col gap-1 text-sm">
            {totals.map(([label, field, value], index) => (
              <div key={field}>
                {index === totals.length - 1 && <Separator className="my-1" />}
                <Selectable
                  active={selected === field}
                  onSelect={() => select(field)}
                  className={cn(
                    "flex justify-between rounded px-2 py-0.5",
                    field === "total" ? "font-semibold" : "text-muted-foreground",
                  )}
                >
                  <span className="inline-flex items-center gap-1">
                    {label}
                    {unconfirmed(field, value) && <MissingMark />}
                  </span>
                  {editable(field, formatMoney(value, document.currency), value)}
                </Selectable>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** A box you can click (or press Enter on) to highlight its value on the page. */
function Selectable({
  active,
  onSelect,
  className,
  children,
}: {
  active: boolean;
  onSelect: () => void;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }}
      className={cn(
        "cursor-pointer text-left transition-colors hover:bg-muted",
        active && "border-amber-500 bg-amber-100/60 dark:bg-amber-500/15",
        className,
      )}
    >
      {children}
    </div>
  );
}

function MissingMark() {
  return (
    <span title="Not found on the page: check this value" className="text-amber-600">
      <TriangleAlert className="size-3.5" />
    </span>
  );
}
