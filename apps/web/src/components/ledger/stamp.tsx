import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type StampTone = "neutral" | "accent" | "success" | "warning" | "danger";

const TONES: Record<StampTone, string> = {
  neutral: "border-border bg-muted text-muted-foreground",
  accent: "border-primary/25 bg-primary/8 text-primary",
  success: "border-success/30 bg-success/10 text-success",
  // Ochre text is darkened a little so small letters stay readable.
  warning:
    "border-warning/35 bg-warning/10 text-[color-mix(in_srgb,var(--warning),var(--foreground)_30%)]",
  danger: "border-destructive/30 bg-destructive/8 text-destructive",
};

type Props = {
  tone?: StampTone;
  /** A softly pulsing dot, for work in progress. */
  pulse?: boolean;
  children: ReactNode;
  className?: string;
};

/** A small-caps status label, like an ink stamp on a ledger: MATCHED, NEEDS REVIEW... */
export function Stamp({ tone = "neutral", pulse = false, children, className }: Props) {
  return (
    <span
      className={cn(
        "inline-flex h-[22px] items-center gap-1.5 rounded-sm border px-2 text-[0.6875rem] font-medium tracking-[0.08em] whitespace-nowrap uppercase",
        TONES[tone],
        className,
      )}
    >
      {pulse && (
        <span className="relative flex size-1.5">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-current opacity-50" />
          <span className="relative inline-flex size-1.5 rounded-full bg-current" />
        </span>
      )}
      {children}
    </span>
  );
}
