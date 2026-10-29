"use client";

import { useEffect, useState } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const CHECK_EVERY_MS = 30_000;

type Health = "checking" | "ok" | "database" | "api";

const LABELS: Record<Health, string> = {
  checking: "Checking the system…",
  ok: "All systems running",
  database: "Database not reachable",
  api: "API not reachable",
};

/** A small live dot: green when the API and database answer. */
export function SystemStatusDot() {
  const [health, setHealth] = useState<Health>("checking");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const response = await fetch("/api/health", { cache: "no-store" });
        const body = response.ok ? await response.json() : null;
        if (!cancelled) setHealth(body === null ? "api" : body.database === "ok" ? "ok" : "database");
      } catch {
        if (!cancelled) setHealth("api");
      }
    }

    check();
    const timer = setInterval(check, CHECK_EVERY_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="flex min-w-0 items-center gap-2 px-2 text-xs text-muted-foreground">
          <span
            className={cn(
              "size-2 shrink-0 rounded-full",
              health === "ok" && "bg-success shadow-[0_0_0_3px_color-mix(in_srgb,var(--success)_18%,transparent)]",
              health === "checking" && "bg-muted-foreground/40",
              (health === "api" || health === "database") && "bg-destructive",
            )}
          />
          <span className="truncate group-data-[collapsible=icon]:hidden">{LABELS[health]}</span>
        </span>
      </TooltipTrigger>
      <TooltipContent side="right">{LABELS[health]}</TooltipContent>
    </Tooltip>
  );
}
