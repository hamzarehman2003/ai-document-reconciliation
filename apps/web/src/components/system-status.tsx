"use client";

import { useEffect, useState } from "react";
import { Database, RefreshCw, Server, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type ServiceState = "checking" | "connected" | "error";

type SystemState = {
  api: ServiceState;
  database: ServiceState;
};

type HealthResponse = {
  status: "ok";
  database: "ok" | "error";
};

const CHECKING: SystemState = { api: "checking", database: "checking" };
const ALL_DOWN: SystemState = { api: "error", database: "error" };

async function fetchSystemState(): Promise<SystemState> {
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    if (!response.ok) {
      return ALL_DOWN;
    }
    const health = (await response.json()) as HealthResponse;
    return {
      api: "connected",
      database: health.database === "ok" ? "connected" : "error",
    };
  } catch {
    return ALL_DOWN;
  }
}

function StateBadge({ state }: { state: ServiceState }) {
  if (state === "connected") {
    return (
      <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
        Connected
      </Badge>
    );
  }
  if (state === "error") {
    return <Badge variant="destructive">Not reachable</Badge>;
  }
  return <Badge variant="secondary">Checking…</Badge>;
}

function ServiceRow({
  icon: Icon,
  name,
  detail,
  state,
}: {
  icon: LucideIcon;
  name: string;
  detail: string;
  state: ServiceState;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border p-3">
      <div className="flex items-center gap-3">
        <Icon className="size-5 text-muted-foreground" />
        <div>
          <p className="text-sm font-medium">{name}</p>
          <p className="font-mono text-xs text-muted-foreground">{detail}</p>
        </div>
      </div>
      <StateBadge state={state} />
    </div>
  );
}

export function SystemStatus() {
  const [system, setSystem] = useState<SystemState>(CHECKING);

  useEffect(() => {
    let ignore = false;
    fetchSystemState().then((state) => {
      if (!ignore) {
        setSystem(state);
      }
    });
    return () => {
      ignore = true;
    };
  }, []);

  async function handleRetry() {
    setSystem(CHECKING);
    setSystem(await fetchSystemState());
  }

  const isChecking = system.api === "checking";

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>System status</CardTitle>
        <CardDescription>
          Checks that every part of InvoiceIQ can talk to each other.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <ServiceRow
          icon={Server}
          name="Backend API"
          detail="FastAPI · /api/health"
          state={system.api}
        />
        <ServiceRow
          icon={Database}
          name="Database"
          detail="PostgreSQL 16"
          state={system.database}
        />
      </CardContent>
      <CardFooter>
        <Button variant="outline" onClick={handleRetry} disabled={isChecking}>
          <RefreshCw className={isChecking ? "animate-spin" : undefined} />
          Check again
        </Button>
      </CardFooter>
    </Card>
  );
}
