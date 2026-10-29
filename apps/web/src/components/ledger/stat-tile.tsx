import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type Props = {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "default" | "success" | "warning" | "danger";
  className?: string;
};

const VALUE_TONES = {
  default: "text-foreground",
  success: "text-success",
  warning: "text-[color-mix(in_srgb,var(--warning),var(--foreground)_25%)]",
  danger: "text-destructive",
};

/** A key number: small-caps label, big serif figure, a quiet line underneath. */
export function StatTile({ label, value, detail, tone = "default", className }: Props) {
  return (
    <div className={cn("rounded-lg border bg-card p-5 shadow-paper", className)}>
      <p className="eyebrow">{label}</p>
      <p
        className={cn(
          "mt-3 font-heading text-[2rem] leading-none font-medium tracking-[-0.02em] tabular-nums",
          VALUE_TONES[tone],
        )}
      >
        {value}
      </p>
      {detail && <p className="mt-2.5 text-sm text-muted-foreground">{detail}</p>}
    </div>
  );
}
