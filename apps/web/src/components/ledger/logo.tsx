import { cn } from "@/lib/utils";

/** The ink-stamp monogram plus the wordmark. Pass `compact` for the monogram only. */
export function Logo({ compact = false, className }: { compact?: boolean; className?: string }) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <span
        aria-hidden
        className="flex size-7 shrink-0 items-center justify-center rounded-[5px] bg-primary font-heading text-[15px] leading-none font-medium text-primary-foreground italic shadow-[inset_0_0_0_1px_rgb(255_255_255/0.14)]"
      >
        iq
      </span>
      {!compact && (
        <span className="font-heading text-[17px] font-medium tracking-[-0.015em]">
          Invoice<span className="text-primary">IQ</span>
        </span>
      )}
    </span>
  );
}
