import { BadgeCheck, CircleCheck, CircleX, Clock, TriangleAlert, type LucideIcon } from "lucide-react";

import type { MatchCase, Verdict } from "@/lib/api";
import { cn } from "@/lib/utils";

const LOOKS: Record<Verdict, { icon: LucideIcon; className: string; iconClass: string }> = {
  clear: {
    icon: CircleCheck,
    className: "border-success/30 bg-success/8",
    iconClass: "text-success",
  },
  approved: {
    icon: BadgeCheck,
    className: "border-success/30 bg-success/8",
    iconClass: "text-success",
  },
  needs_review: {
    icon: TriangleAlert,
    className: "border-warning/35 bg-warning/8",
    iconClass: "text-warning",
  },
  waiting: { icon: Clock, className: "border-border bg-muted/60", iconClass: "text-muted-foreground" },
  rejected: {
    icon: CircleX,
    className: "border-destructive/30 bg-destructive/8",
    iconClass: "text-destructive",
  },
};

/** The one-line answer at the top of an invoice: is everything OK, or what isn't? */
export function VerdictBanner({ matchCase }: { matchCase: MatchCase }) {
  const look = LOOKS[matchCase.verdict];
  const Icon = look.icon;
  return (
    <div
      role="status"
      className={cn("flex items-start gap-3 rounded-md border px-3.5 py-3 text-sm leading-relaxed", look.className)}
    >
      <Icon className={cn("mt-0.5 size-4 shrink-0", look.iconClass)} />
      <p>{matchCase.summary}</p>
    </div>
  );
}
