"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Download, FileSpreadsheet } from "lucide-react";

import { EmptyState } from "@/components/ledger/empty-state";
import { MoneyTile } from "@/components/ledger/money-tile";
import { Stamp } from "@/components/ledger/stamp";
import { StatTile } from "@/components/ledger/stat-tile";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { listMatchCases, type AmountByCurrency, type MatchCase } from "@/lib/api";
import { formatAge, formatDate, formatMoney, orDash } from "@/lib/format";

type Filters = { vendor: string; dateFrom: string; dateTo: string };

/** Exactly what the export file will contain, with the same filters as the download. */
export function ExportPreview() {
  const [cases, setCases] = useState<MatchCase[] | null>(null);
  const [error, setError] = useState(false);
  const [filters, setFilters] = useState<Filters>({ vendor: "", dateFrom: "", dateTo: "" });

  useEffect(() => {
    listMatchCases()
      .then((all) => setCases(all.filter((item) => item.review_status === "approved")))
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
        Couldn&apos;t load the approved invoices. Is the API running? Reload the page to try again.
      </p>
    );
  }
  if (cases === null) {
    return <Skeleton className="h-96" />;
  }

  const shown = cases
    .filter((item) => inFile(item, filters))
    .sort((a, b) => (a.invoice_date ?? "").localeCompare(b.invoice_date ?? ""));
  const query = exportQuery(filters);
  const set = (change: Partial<Filters>) => setFilters((current) => ({ ...current, ...change }));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end gap-3 rounded-lg border bg-card p-4 shadow-paper">
        <label className="flex w-full flex-col gap-1.5 sm:w-56">
          <span className="eyebrow">Vendor</span>
          <Input
            value={filters.vendor}
            onChange={(event) => set({ vendor: event.target.value })}
            placeholder="Any vendor"
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="eyebrow">Invoice date from</span>
          <Input
            type="date"
            value={filters.dateFrom}
            onChange={(event) => set({ dateFrom: event.target.value })}
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="eyebrow">To</span>
          <Input
            type="date"
            value={filters.dateTo}
            onChange={(event) => set({ dateTo: event.target.value })}
          />
        </label>
        <div className="flex gap-2 sm:ml-auto">
          <DownloadButton href={`/api/exports/approved.xlsx${query}`} label="Excel" primary disabled={shown.length === 0} />
          <DownloadButton href={`/api/exports/approved.csv${query}`} label="CSV" disabled={shown.length === 0} />
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <StatTile label="Invoices in the file" value={shown.length} detail="Approved for payment" />
        <MoneyTile
          label="Total to pay"
          amounts={totalsByCurrency(shown)}
          tone="success"
          emptyDetail="Nothing approved yet"
        />
        <StatTile
          label="Approved despite problems"
          value={shown.filter((item) => item.discrepancies.length > 0).length}
          tone="warning"
          detail="Each one has a reviewer's note"
        />
      </div>

      {shown.length === 0 ? (
        <EmptyState
          icon={FileSpreadsheet}
          title={cases.length === 0 ? "Nothing approved yet" : "No invoices match these filters"}
          description={
            cases.length === 0
              ? "Approve invoices in the review queue and they will be ready to export here."
              : "Change the vendor or the dates to include more invoices."
          }
          action={
            cases.length === 0 && (
              <Button variant="outline" asChild>
                <Link href="/review">Open the review queue</Link>
              </Button>
            )
          }
        />
      ) : (
        <PreviewTable cases={shown} />
      )}
      <p className="text-xs text-muted-foreground">
        Each download is recorded in the activity log, with who exported which invoices.
      </p>
    </div>
  );
}

function DownloadButton({
  href,
  label,
  primary = false,
  disabled,
}: {
  href: string;
  label: string;
  primary?: boolean;
  disabled: boolean;
}) {
  if (disabled) {
    return (
      <Button variant={primary ? "default" : "outline"} disabled>
        <Download /> {label}
      </Button>
    );
  }
  return (
    <Button variant={primary ? "default" : "outline"} asChild>
      <a href={href}>
        <Download /> {label}
      </a>
    </Button>
  );
}

function PreviewTable({ cases }: { cases: MatchCase[] }) {
  return (
    <div className="rounded-lg border bg-card shadow-paper">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Invoice</TableHead>
            <TableHead>Dated</TableHead>
            <TableHead className="text-right">Total</TableHead>
            <TableHead>Approved by</TableHead>
            <TableHead>Note</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {cases.map((item) => (
            <TableRow key={item.id}>
              <TableCell>
                <Link href={`/review/${item.invoice_id}`} className="block font-medium hover:underline">
                  {orDash(item.vendor_name)}
                </Link>
                <span className="numeric text-xs text-muted-foreground">
                  {orDash(item.invoice_number)}
                </span>
              </TableCell>
              <TableCell className="numeric text-muted-foreground">
                {formatDate(item.invoice_date)}
              </TableCell>
              <TableCell className="numeric text-right">
                {formatMoney(item.total, item.currency)}
              </TableCell>
              <TableCell>
                {orDash(item.reviewed_by)}
                {item.reviewed_at && (
                  <span className="block text-xs text-muted-foreground">
                    {formatAge(item.reviewed_at)}
                  </span>
                )}
              </TableCell>
              <TableCell className="max-w-72 whitespace-normal">
                {item.discrepancies.length > 0 && (
                  <Stamp tone="warning" className="mb-1">
                    {item.discrepancies.length} problem{item.discrepancies.length === 1 ? "" : "s"}
                  </Stamp>
                )}
                <span className="block text-sm text-muted-foreground">
                  {item.review_note ?? "—"}
                </span>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** The same rules as the API export: vendor contains the text, invoice date in range. */
function inFile(item: MatchCase, filters: Filters): boolean {
  const vendor = filters.vendor.trim().toLowerCase();
  if (vendor && !item.vendor_name?.toLowerCase().includes(vendor)) return false;
  if (filters.dateFrom && !(item.invoice_date && item.invoice_date >= filters.dateFrom)) return false;
  if (filters.dateTo && !(item.invoice_date && item.invoice_date <= filters.dateTo)) return false;
  return true;
}

function exportQuery(filters: Filters): string {
  const params = new URLSearchParams();
  if (filters.vendor.trim()) params.set("vendor", filters.vendor.trim());
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  const text = params.toString();
  return text ? `?${text}` : "";
}

/** Totals per currency, added in cents so 0.1 + 0.2 stays 0.30. */
function totalsByCurrency(cases: MatchCase[]): AmountByCurrency[] {
  const totals = new Map<string, { cents: number; invoices: number }>();
  for (const item of cases) {
    if (item.total === null || item.currency === null) continue;
    const current = totals.get(item.currency) ?? { cents: 0, invoices: 0 };
    current.cents += Math.round(Number(item.total) * 100);
    current.invoices += 1;
    totals.set(item.currency, current);
  }
  return [...totals].map(([currency, { cents, invoices }]) => ({
    currency,
    amount: (cents / 100).toFixed(2),
    invoices,
  }));
}
