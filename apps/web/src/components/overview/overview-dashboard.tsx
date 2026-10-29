"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Inbox } from "lucide-react";

import { EmptyState } from "@/components/ledger/empty-state";
import { StatTile } from "@/components/ledger/stat-tile";
import { DailyChart } from "@/components/overview/daily-chart";
import { TopProblems } from "@/components/overview/top-problems";
import { CaseStamp, ProblemSummary, needsDecision } from "@/components/review/case-row-parts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getDashboard,
  listMatchCases,
  type AmountByCurrency,
  type Dashboard,
  type MatchCase,
} from "@/lib/api";
import { formatAge, formatMoney, orDash } from "@/lib/format";

type Loaded = { dashboard: Dashboard; cases: MatchCase[] };

/** The Overview screen: key numbers, activity, common problems, what to open next. */
export function OverviewDashboard() {
  const [data, setData] = useState<Loaded | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    Promise.all([getDashboard(), listMatchCases()])
      .then(([dashboard, cases]) => setData({ dashboard, cases }))
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
        Couldn&apos;t load the numbers. Is the API running? Reload the page to try again.
      </p>
    );
  }
  if (data === null) {
    return <OverviewSkeleton />;
  }

  const { dashboard, cases } = data;
  const { invoices } = dashboard;
  const matched = invoices.by_match_status.matched ?? 0;
  const withProblems = invoices.by_match_status.needs_review ?? 0;
  const pending = invoices.by_review_status.pending ?? 0;
  const next = needsDecision(cases).slice(0, 5);

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Invoices checked"
          value={invoices.total}
          detail={`${dashboard.documents.processed} documents read by AI`}
        />
        <StatTile
          label="Matched on their own"
          value={invoices.match_rate === null ? "—" : `${Math.round(invoices.match_rate * 100)}%`}
          tone="success"
          detail={`${matched} of ${matched + withProblems} invoices`}
        />
        <StatTile
          label="Waiting for a decision"
          value={pending}
          tone={pending > 0 ? "warning" : "default"}
          detail={`${withProblems} with problems`}
        />
        <MoneyTile label="Money at risk" amounts={dashboard.money_at_risk} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <p className="eyebrow">Last 14 days</p>
            <CardTitle>Activity</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-8 sm:grid-cols-2">
            <DailyChart title="Documents uploaded" data={dashboard.daily} metric="uploaded" />
            <DailyChart title="Invoices approved" data={dashboard.daily} metric="approved" />
          </CardContent>
          <CardFooter className="numeric text-xs text-muted-foreground">
            AI read {dashboard.ai.documents_read} documents
            {dashboard.ai.average_seconds !== null &&
              ` · ${dashboard.ai.average_seconds.toFixed(1)} s on average`}
            {` · ${dashboard.corrections} values corrected by people`}
          </CardFooter>
        </Card>

        <Card>
          <CardHeader>
            <p className="eyebrow">3-way match</p>
            <CardTitle>Most common problems</CardTitle>
          </CardHeader>
          <CardContent>
            <TopProblems problems={dashboard.top_problems} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <p className="eyebrow">Oldest first</p>
          <CardTitle>Needs your decision</CardTitle>
        </CardHeader>
        <CardContent>
          {next.length === 0 ? (
            <EmptyState
              icon={Inbox}
              title="Nothing waiting"
              description="Every invoice with a problem has been decided."
            />
          ) : (
            <ul className="-mx-2 divide-y divide-border/70">
              {next.map((item) => (
                <li key={item.id}>
                  <AttentionRow matchCase={item} />
                </li>
              ))}
            </ul>
          )}
        </CardContent>
        <CardFooter className="justify-end">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/review">
              Open the review queue <ArrowRight />
            </Link>
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}

/** Money is never added across currencies: the largest one big, the others underneath. */
function MoneyTile({ label, amounts }: { label: string; amounts: AmountByCurrency[] }) {
  const [first, ...others] = [...amounts].sort((a, b) => b.invoices - a.invoices);
  if (!first) {
    return <StatTile label={label} value={formatMoney("0", null)} detail="No open problems" />;
  }
  const invoices = amounts.reduce((sum, item) => sum + item.invoices, 0);
  return (
    <StatTile
      label={label}
      value={formatMoney(first.amount, first.currency)}
      tone="danger"
      detail={
        others.length > 0
          ? `and ${others.map((item) => formatMoney(item.amount, item.currency)).join(", ")} · ${invoices} invoices`
          : `${invoices} invoice${invoices === 1 ? "" : "s"}`
      }
    />
  );
}

function AttentionRow({ matchCase }: { matchCase: MatchCase }) {
  return (
    <Link
      href={`/review/${matchCase.invoice_id}`}
      className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md px-2 py-3 transition-colors hover:bg-accent/60"
    >
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium">{orDash(matchCase.vendor_name)}</span>
        <span className="numeric block text-xs text-muted-foreground">
          {orDash(matchCase.invoice_number)} · {formatAge(matchCase.updated_at)}
        </span>
      </span>
      <span className="hidden min-w-0 flex-1 truncate text-sm md:block">
        <ProblemSummary matchCase={matchCase} />
      </span>
      <span className="numeric w-28 text-right text-sm">
        {formatMoney(matchCase.total, matchCase.currency)}
      </span>
      <CaseStamp matchCase={matchCase} />
    </Link>
  );
}

function OverviewSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((key) => (
          <Skeleton key={key} className="h-[122px]" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}
