import { cn } from "@/lib/utils";

type Props = {
  /** The monogram only. */
  compact?: boolean;
  /** "inverse" for the deep green login panel. */
  tone?: "default" | "inverse";
  className?: string;
};

/** The ink-stamp monogram plus the wordmark. */
export function Logo({ compact = false, tone = "default", className }: Props) {
  const inverse = tone === "inverse";
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <span
        aria-hidden
        className={cn(
          "flex size-7 shrink-0 items-center justify-center rounded-[5px] font-heading text-[15px] leading-none font-medium italic",
          inverse
            ? "bg-brand-panel-foreground text-brand-panel"
            : "bg-primary text-primary-foreground shadow-[inset_0_0_0_1px_rgb(255_255_255/0.14)]",
        )}
      >
        iq
      </span>
      {!compact && (
        <span className="font-heading text-[17px] font-medium tracking-[-0.015em]">
          Invoice
          <span className={inverse ? "text-brand-panel-foreground/65" : "text-primary"}>IQ</span>
        </span>
      )}
    </span>
  );
}
