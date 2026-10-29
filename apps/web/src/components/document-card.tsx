import { ExternalLink, Loader2 } from "lucide-react";

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

function ExtractedData({ document }: { document: DocumentDetail }) {
  const isReceipt = document.doc_type === "goods_receipt";
  const fields: [string, string][] = [
    ["Document number", orDash(document.document_number)],
    ["Vendor", orDash(document.vendor_name)],
    ["Buyer", orDash(document.buyer_name)],
    ["Date", formatDate(document.issue_date)],
    ["Due date", formatDate(document.due_date)],
    ["PO reference", orDash(document.po_reference)],
    ["Currency", orDash(document.currency)],
  ];

  return (
    <div className="flex flex-col gap-6">
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
        {fields.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs text-muted-foreground">{label}</dt>
            <dd className="font-mono text-sm">{value}</dd>
          </div>
        ))}
      </dl>

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
          {document.line_items.map((item) => (
            <TableRow key={item.position}>
              <TableCell className="font-mono text-xs">{orDash(item.sku)}</TableCell>
              <TableCell className="whitespace-normal">{item.description}</TableCell>
              {isReceipt && (
                <TableCell className="text-right font-mono">
                  {formatQuantity(item.quantity_ordered)}
                </TableCell>
              )}
              <TableCell className="text-right font-mono">{formatQuantity(item.quantity)}</TableCell>
              {!isReceipt && (
                <TableCell className="text-right font-mono">
                  {formatMoney(item.unit_price, document.currency)}
                </TableCell>
              )}
              {!isReceipt && (
                <TableCell className="text-right font-mono">
                  {formatMoney(item.line_total, document.currency)}
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {!isReceipt && (
        <div className="ml-auto flex w-full max-w-xs flex-col gap-1 text-sm">
          <TotalRow label="Subtotal" value={formatMoney(document.subtotal, document.currency)} />
          <TotalRow label="Tax" value={formatMoney(document.tax, document.currency)} />
          <Separator className="my-1" />
          <TotalRow label="Total" value={formatMoney(document.total, document.currency)} bold />
        </div>
      )}
    </div>
  );
}

function TotalRow({ label, value, bold = false }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className={`flex justify-between ${bold ? "font-semibold" : "text-muted-foreground"}`}>
      <span>{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  );
}
