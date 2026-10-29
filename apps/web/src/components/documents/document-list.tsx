"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Files, Search, Upload } from "lucide-react";

import { EmptyState } from "@/components/ledger/empty-state";
import { Stamp } from "@/components/ledger/stamp";
import { DocumentStatusStamp } from "@/components/ledger/status-stamps";
import { Button } from "@/components/ui/button";
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { listDocuments, type DocumentRow } from "@/lib/api";
import { DOC_TYPE_LABELS, formatAge, formatDate, formatMoney, orDash } from "@/lib/format";

const VIEWS = [
  { key: "all", label: "All", show: () => true },
  { key: "invoices", label: "Invoices", show: (d: DocumentRow) => d.doc_type === "invoice" },
  {
    key: "orders",
    label: "Purchase orders",
    show: (d: DocumentRow) => d.doc_type === "purchase_order",
  },
  {
    key: "receipts",
    label: "Goods receipts",
    show: (d: DocumentRow) => d.doc_type === "goods_receipt",
  },
  {
    key: "attention",
    label: "Needs attention",
    show: (d: DocumentRow) => d.status === "failed" || d.doc_type === "unknown",
  },
] as const;

type ViewKey = (typeof VIEWS)[number]["key"];

/** Every uploaded document, newest first, with tabs per type and a search. */
export function DocumentList() {
  const [documents, setDocuments] = useState<DocumentRow[] | null>(null);
  const [error, setError] = useState(false);
  const [view, setView] = useState<ViewKey>("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
        Couldn&apos;t load the documents. Is the API running? Reload the page to try again.
      </p>
    );
  }
  if (documents === null) {
    return <Skeleton className="h-96" />;
  }
  if (documents.length === 0) {
    return (
      <EmptyState
        icon={Files}
        title="No documents yet"
        description="Upload invoices, purchase orders and goods receipts to see them here."
        action={
          <Button asChild>
            <Link href="/upload">
              <Upload /> Upload documents
            </Link>
          </Button>
        }
      />
    );
  }

  const current = VIEWS.find((item) => item.key === view) ?? VIEWS[0];
  const shown = documents.filter((item) => current.show(item) && matches(item, query));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs value={view} onValueChange={(value) => setView(value as ViewKey)}>
          <TabsList variant="line" className="flex-wrap">
            {VIEWS.map((item) => (
              <TabsTrigger key={item.key} value={item.key} className="px-2">
                {item.label}
                <span className="numeric text-xs text-muted-foreground">
                  {documents.filter(item.show).length}
                </span>
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <InputGroup className="w-full sm:w-64">
          <InputGroupAddon>
            <Search />
          </InputGroupAddon>
          <InputGroupInput
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="File name, number or vendor"
            aria-label="Search documents"
          />
        </InputGroup>
      </div>

      {shown.length === 0 ? (
        <EmptyState
          icon={Files}
          title="No documents here"
          description={query ? "Try another file name, number or vendor." : "Nothing in this tab yet."}
        />
      ) : (
        <DocumentTable documents={shown} />
      )}
    </div>
  );
}

function DocumentTable({ documents }: { documents: DocumentRow[] }) {
  const router = useRouter();

  return (
    <div className="rounded-lg border bg-card shadow-paper">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Document</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Vendor</TableHead>
            <TableHead>Dated</TableHead>
            <TableHead className="text-right">Total</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Uploaded</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((item) => (
            <TableRow
              key={item.id}
              onClick={() => router.push(`/documents/${item.id}`)}
              className="cursor-pointer"
            >
              <TableCell className="max-w-64">
                <Link
                  href={`/documents/${item.id}`}
                  className="block truncate font-medium hover:underline"
                  onClick={(event) => event.stopPropagation()}
                >
                  {item.filename}
                </Link>
                <span className="numeric text-xs text-muted-foreground">
                  {orDash(item.document_number)}
                </span>
              </TableCell>
              <TableCell>
                {item.status === "processed" ? <Stamp>{DOC_TYPE_LABELS[item.doc_type]}</Stamp> : "—"}
              </TableCell>
              <TableCell className="max-w-48 truncate">{orDash(item.vendor_name)}</TableCell>
              <TableCell className="numeric text-muted-foreground">
                {formatDate(item.issue_date)}
              </TableCell>
              <TableCell className="numeric text-right">
                {item.doc_type === "goods_receipt" ? "—" : formatMoney(item.total, item.currency)}
              </TableCell>
              <TableCell>
                <DocumentStatusStamp status={item.status} />
              </TableCell>
              <TableCell className="text-right text-muted-foreground">
                {formatAge(item.created_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function matches(item: DocumentRow, query: string): boolean {
  const text = query.trim().toLowerCase();
  if (!text) return true;
  return [item.filename, item.document_number, item.vendor_name].some((value) =>
    value?.toLowerCase().includes(text),
  );
}
