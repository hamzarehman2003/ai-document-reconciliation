"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Inbox, Search } from "lucide-react";

import { EmptyState } from "@/components/ledger/empty-state";
import { CaseStamp, ProblemSummary } from "@/components/review/case-row-parts";
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
import { listMatchCases, type MatchCase } from "@/lib/api";
import { formatAge, formatDate, formatMoney, orDash } from "@/lib/format";

/** The queue's tabs: which invoices each one shows. */
const VIEWS = [
  {
    key: "problems",
    label: "Needs review",
    empty: "No invoices with problems are waiting for a decision.",
    show: (c: MatchCase) => c.status === "needs_review" && c.review_status === "pending",
  },
  {
    key: "ready",
    label: "Ready to approve",
    empty: "No matched invoices are waiting for approval.",
    show: (c: MatchCase) => c.status === "matched" && c.review_status === "pending",
  },
  {
    key: "waiting",
    label: "Waiting for documents",
    empty: "Every invoice has its purchase order and goods receipt.",
    show: (c: MatchCase) => c.status === "waiting" && c.review_status === "pending",
  },
  {
    key: "decided",
    label: "Decided",
    empty: "Nothing has been approved or rejected yet.",
    show: (c: MatchCase) => c.review_status !== "pending",
  },
  { key: "all", label: "All", empty: "No invoices have been checked yet.", show: () => true },
] as const;

type ViewKey = (typeof VIEWS)[number]["key"];

/** Every checked invoice, split into tabs, with a search over vendor and numbers. */
export function ReviewQueue() {
  const [cases, setCases] = useState<MatchCase[] | null>(null);
  const [error, setError] = useState(false);
  const [view, setView] = useState<ViewKey>("problems");
  const [query, setQuery] = useState("");

  useEffect(() => {
    listMatchCases()
      .then(setCases)
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
        Couldn&apos;t load the review queue. Is the API running? Reload the page to try again.
      </p>
    );
  }
  if (cases === null) {
    return <Skeleton className="h-96" />;
  }

  const current = VIEWS.find((item) => item.key === view) ?? VIEWS[0];
  const shown = cases.filter((item) => current.show(item) && matches(item, query));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs value={view} onValueChange={(value) => setView(value as ViewKey)}>
          <TabsList variant="line" className="flex-wrap">
            {VIEWS.map((item) => (
              <TabsTrigger key={item.key} value={item.key} className="px-2">
                {item.label}
                <span className="numeric text-xs text-muted-foreground">
                  {cases.filter(item.show).length}
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
            placeholder="Vendor, invoice or PO number"
            aria-label="Search invoices"
          />
        </InputGroup>
      </div>

      {shown.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title={query ? "No invoices match your search" : "Nothing here"}
          description={query ? "Try another vendor name or number." : current.empty}
        />
      ) : (
        <CaseTable cases={shown} />
      )}
    </div>
  );
}

function CaseTable({ cases }: { cases: MatchCase[] }) {
  const router = useRouter();

  return (
    <div className="rounded-lg border bg-card shadow-paper">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Invoice</TableHead>
            <TableHead>Dated</TableHead>
            <TableHead>Problems</TableHead>
            <TableHead className="text-right">Total</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Updated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {cases.map((item) => (
            <TableRow
              key={item.id}
              onClick={() => router.push(`/review/${item.invoice_id}`)}
              className="cursor-pointer"
            >
              <TableCell>
                <Link
                  href={`/review/${item.invoice_id}`}
                  className="block font-medium hover:underline"
                  onClick={(event) => event.stopPropagation()}
                >
                  {orDash(item.vendor_name)}
                </Link>
                <span className="numeric text-xs text-muted-foreground">
                  {orDash(item.invoice_number)}
                  {item.po_number && ` · ${item.po_number}`}
                </span>
              </TableCell>
              <TableCell className="numeric text-muted-foreground">
                {formatDate(item.invoice_date)}
              </TableCell>
              <TableCell className="max-w-64 truncate">
                <ProblemSummary matchCase={item} />
              </TableCell>
              <TableCell className="numeric text-right">
                {formatMoney(item.total, item.currency)}
              </TableCell>
              <TableCell>
                <CaseStamp matchCase={item} />
              </TableCell>
              <TableCell className="text-right text-muted-foreground">
                {formatAge(item.updated_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function matches(item: MatchCase, query: string): boolean {
  const text = query.trim().toLowerCase();
  if (!text) return true;
  return [item.vendor_name, item.invoice_number, item.po_number].some((value) =>
    value?.toLowerCase().includes(text),
  );
}
