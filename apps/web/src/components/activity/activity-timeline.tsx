"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  CircleCheck,
  CircleX,
  FileSpreadsheet,
  FileText,
  FileX,
  GitCompareArrows,
  History,
  PencilLine,
  RotateCcw,
  ScanText,
  UserRound,
  type LucideIcon,
} from "lucide-react";

import { EmptyState } from "@/components/ledger/empty-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { listAuditEvents, type AuditEvent } from "@/lib/api";
import { describe } from "@/lib/audit";
import { cn } from "@/lib/utils";

/** How each kind of event looks, and which tab it belongs to. */
const KINDS: Record<string, { icon: LucideIcon; group: GroupKey; className?: string }> = {
  document_uploaded: { icon: FileText, group: "documents" },
  document_processed: { icon: ScanText, group: "documents" },
  document_failed: { icon: FileX, group: "documents", className: "text-destructive" },
  match_status_changed: { icon: GitCompareArrows, group: "matching" },
  decision_reset: { icon: RotateCcw, group: "matching", className: "text-warning" },
  case_approved: { icon: CircleCheck, group: "decisions", className: "text-success" },
  case_rejected: { icon: CircleX, group: "decisions", className: "text-destructive" },
  case_reopened: { icon: RotateCcw, group: "decisions" },
  field_corrected: { icon: PencilLine, group: "corrections", className: "text-primary" },
  case_exported: { icon: FileSpreadsheet, group: "exports" },
};

const GROUPS = [
  { key: "all", label: "All" },
  { key: "decisions", label: "Decisions" },
  { key: "corrections", label: "Corrections" },
  { key: "documents", label: "Documents" },
  { key: "matching", label: "Matching" },
  { key: "exports", label: "Exports" },
] as const;

type GroupKey = (typeof GROUPS)[number]["key"];

/** An event, or several identical ones from the same moment (one export = one event per invoice). */
type Row = { event: AuditEvent; count: number };

/** The audit log as a timeline, grouped by day, newest first. */
export function ActivityTimeline() {
  const router = useRouter();
  // "Only mine" lives in the URL (?mine=1), so it can be linked to from the user menu.
  const mine = useSearchParams().get("mine") === "1";
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState(false);
  const [group, setGroup] = useState<GroupKey>("all");

  useEffect(() => {
    listAuditEvents(mine)
      .then(setEvents)
      .catch(() => setError(true));
  }, [mine]);

  if (error) {
    return (
      <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
        Couldn&apos;t load the activity log. Is the API running? Reload the page to try again.
      </p>
    );
  }
  if (events === null) {
    return <Skeleton className="h-96" />;
  }

  const inGroup = (event: AuditEvent) => group === "all" || KINDS[event.action]?.group === group;
  const days = byDay(combineExports(events.filter(inGroup)));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs value={group} onValueChange={(value) => setGroup(value as GroupKey)}>
          <TabsList variant="line" className="flex-wrap">
            {GROUPS.map((item) => (
              <TabsTrigger key={item.key} value={item.key} className="px-2">
                {item.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <Button
          variant={mine ? "default" : "outline"}
          size="sm"
          aria-pressed={mine}
          onClick={() => router.replace(mine ? "/activity" : "/activity?mine=1")}
        >
          <UserRound /> Only mine
        </Button>
      </div>

      {days.length === 0 ? (
        <EmptyState
          icon={History}
          title="Nothing here yet"
          description={
            mine
              ? "Things you upload, correct, approve or export will appear here."
              : "Uploads, corrections, decisions and exports will appear here as they happen."
          }
        />
      ) : (
        days.map(([day, rows]) => (
          <section key={day} className="rounded-lg border bg-card shadow-paper">
            <h2 className="eyebrow border-b px-4 py-2.5">{dayLabel(day)}</h2>
            <ol className="divide-y divide-border/70">
              {rows.map((row) => (
                <li key={row.event.id}>
                  <EventRow row={row} />
                </li>
              ))}
            </ol>
          </section>
        ))
      )}
      <p className="text-xs text-muted-foreground">Showing the latest 300 events.</p>
    </div>
  );
}

function EventRow({ row: { event, count } }: { row: Row }) {
  const kind = KINDS[event.action] ?? { icon: History };
  const Icon = kind.icon;
  const link =
    event.document_id === null
      ? null
      : event.object_type === "match_case"
        ? `/review/${event.document_id}`
        : `/documents/${event.document_id}`;

  return (
    <div className="flex items-start gap-3 px-4 py-3">
      <time className="numeric w-12 shrink-0 pt-1 text-xs text-muted-foreground">
        {new Date(event.created_at).toLocaleTimeString("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
        })}
      </time>
      <span className="flex size-7 shrink-0 items-center justify-center rounded-full border bg-background">
        <Icon className={cn("size-3.5 text-muted-foreground", kind.className)} strokeWidth={1.75} />
      </span>
      <div className="min-w-0 flex-1 pt-0.5">
        <p className="text-sm">{describe(event, count)}</p>
        <p className="mt-0.5 truncate text-xs text-muted-foreground">
          {/* A combined export is about many invoices, so it names none of them. */}
          {count === 1 && (
            <>
              {link && event.subject ? (
                <Link href={link} className="text-foreground/80 hover:underline">
                  {event.subject}
                </Link>
              ) : (
                (event.subject ?? "Removed document")
              )}
              {" · "}
            </>
          )}
          {event.actor}
        </p>
      </div>
    </div>
  );
}

/** Folds export events from the same moment and person into one row. */
function combineExports(events: AuditEvent[]): Row[] {
  const rows: Row[] = [];
  for (const event of events) {
    const last = rows.at(-1);
    const same =
      last !== undefined &&
      event.action === "case_exported" &&
      last.event.action === "case_exported" &&
      last.event.created_at === event.created_at &&
      last.event.actor === event.actor;
    if (same) last.count += 1;
    else rows.push({ event, count: 1 });
  }
  return rows;
}

/** [["2026-10-29", rows], ...] in the viewer's own time zone, newest day first. */
function byDay(rows: Row[]): [string, Row[]][] {
  const days = new Map<string, Row[]>();
  for (const row of rows) {
    const day = localDay(new Date(row.event.created_at));
    days.set(day, [...(days.get(day) ?? []), row]);
  }
  return [...days];
}

function localDay(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function dayLabel(day: string): string {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (day === localDay(today)) return "Today";
  if (day === localDay(yesterday)) return "Yesterday";
  return new Date(`${day}T00:00:00`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
